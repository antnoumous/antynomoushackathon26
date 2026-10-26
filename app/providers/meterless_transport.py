"""Secret-safe HTTP boundary for the optional Meterless provider."""
from __future__ import annotations
import json
import math
import multiprocessing
import os
import struct
import time
import requests
from app.providers.meterless_settings import MeterlessError


def _request(method: str,url: str,*,headers: dict[str,str],payload: dict|None,timeout_s: float,max_response_bytes: int=1024*1024) -> dict:
    with requests.Session() as session:
        session.trust_env=False
        with session.request(method,url,headers=headers,json=payload,timeout=timeout_s,allow_redirects=False,stream=True) as response:
            if response.status_code in (401,403):raise MeterlessError("unauthorized")
            if response.status_code != 200:raise MeterlessError("transport")
            chunks=[];size=0
            for chunk in response.iter_content(chunk_size=8192):
                size+=len(chunk)
                if size > max_response_bytes:raise MeterlessError("transport")
                chunks.append(chunk)
            try:
                result=json.loads(b"".join(chunks),parse_constant=lambda value:(_ for _ in ()).throw(ValueError()))
                if not isinstance(result,dict):raise ValueError()
                return result
            except (ValueError,UnicodeError):
                raise MeterlessError("schema") from None


def _worker(connection, method, url, headers, payload, timeout_s, max_response_bytes):
    try:
        try:
            result = _request(method, url, headers=headers, payload=payload,
                              timeout_s=timeout_s, max_response_bytes=max_response_bytes)
            envelope = ["ok", result]
        except MeterlessError as exc:
            envelope = ["error", exc.category]
        except requests.Timeout:
            envelope = ["error", "timeout"]
        except requests.ConnectionError:
            envelope = ["error", "offline"]
        except Exception:
            envelope = ["error", "transport"]
        connection.send_bytes(json.dumps(envelope, ensure_ascii=False, allow_nan=False,
                                         separators=(",", ":")).encode("utf-8"))
    except Exception:
        pass  # Parent may already have closed its deadline-expired pipe.
    finally:
        connection.close()


def request_json(method: str, url: str, *, headers: dict[str, str], payload: dict | None,
                 timeout_s: float, max_response_bytes: int = 1024*1024) -> dict:
    if not isinstance(timeout_s, (int, float)) or not math.isfinite(timeout_s) or timeout_s <= 0:
        raise MeterlessError("timeout")
    deadline = time.monotonic() + timeout_s
    reader = writer = process = None
    try:
        context = multiprocessing.get_context("spawn")
        reader, writer = context.Pipe(duplex=False)
        process = context.Process(target=_worker, args=(writer, method, url, headers, payload,
                                  timeout_s, max_response_bytes), daemon=True)
        process.start()
        writer.close()
        frame = bytearray()
        expected = None
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise MeterlessError("timeout")
            if reader.poll(min(0.05, remaining)):
                # poll() signals bytes, not a complete multiprocessing frame. Never call
                # blocking recv_bytes() in the supervising thread (macOS/Linux pipe FDs).
                fd = reader.fileno()
                os.set_blocking(fd, False)
                needed = (4 if expected is None else expected) - len(frame)
                try:
                    chunk = os.read(fd, min(65536, needed))
                except BlockingIOError:
                    continue
                if not chunk:
                    raise MeterlessError("transport")
                frame.extend(chunk)
                if expected is None:
                    if len(frame) == 4:
                        expected = struct.unpack("!i", frame)[0]
                        if expected <= 0 or expected > max_response_bytes + 1024:
                            raise MeterlessError("transport")
                        frame.clear()
                elif len(frame) == expected:
                    if time.monotonic() > deadline:
                        raise MeterlessError("timeout")
                    envelope = json.loads(frame)
                    if not isinstance(envelope, list) or len(envelope) != 2:
                        raise MeterlessError("transport")
                    if envelope[0] == "ok" and isinstance(envelope[1], dict):
                        return envelope[1]
                    if envelope[0] == "error":
                        raise MeterlessError(envelope[1])
                    raise MeterlessError("transport")
                continue
            if not process.is_alive():
                if reader.poll(0):
                    continue
                raise MeterlessError("transport")
    except MeterlessError:
        raise
    except Exception:
        raise MeterlessError("transport") from None
    finally:
        for pipe in (reader, writer):
            if pipe is not None:
                try:
                    pipe.close()
                except Exception:
                    pass
        if process is not None:
            try:
                if process.pid is not None:
                    if process.is_alive():
                        process.terminate()
                    process.join(timeout=0.15)
                    if process.is_alive():
                        process.kill()
                        process.join(timeout=0.15)
                if not process.is_alive():
                    process.close()
            except Exception:
                pass
