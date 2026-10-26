import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import pytest


@pytest.fixture
def runtime_server():
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            status=200
            if self.headers.get("Authorization") != "Bearer unit-http-only":
                status=401;body=b"private-response-sentinel"
            else:
                body=json.dumps({"data":[{"id":"meterless/local"}]}).encode()
            if self.path in {"/forbidden","/error"}:
                status=403 if self.path == "/forbidden" else 500
                body=b"private-response-sentinel"
            if self.path in {"/bad-json","/list","/nan"}:
                body={"/bad-json":b"private-response-sentinel","/list":b"[]","/nan":b'{"x":NaN}'}[self.path]
            if self.path == "/large":body=b'{"data":"'+b'x'*4096+b'"}'
            if self.path.startswith("/redirect?"):status=302
            self.send_response(status)
            if status == 302:
                from urllib.parse import unquote
                self.send_header("Location",unquote(self.path.split("target=",1)[1]))
            self.send_header("Content-Type","application/json")
            if self.path != "/drip":self.send_header("Content-Length",str(len(body)))
            self.end_headers()
            try:
                if self.path == "/drip":
                    for _ in range(300):
                        self.wfile.write(b" ");self.wfile.flush();time.sleep(0.02)
                else:self.wfile.write(body)
            except OSError:pass
    server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
    server.daemon_threads=True
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:yield "http://127.0.0.1:"+str(server.server_port)
    finally:
        server.shutdown();server.server_close();thread.join(timeout=2)


def test_real_http_discovery_and_wrong_token(runtime_server):
    from app.providers.meterless_transport import request_json
    from app.providers.meterless_settings import MeterlessError
    result=request_json("GET",runtime_server+"/v1/models",headers={"Authorization":"Bearer unit-http-only"},
                        payload=None,timeout_s=3)
    assert result == {"data":[{"id":"meterless/local"}]}
    with pytest.raises(MeterlessError) as caught:
        request_json("GET",runtime_server+"/v1/models",headers={"Authorization":"Bearer wrong-unit-token"},
                     payload=None,timeout_s=3)
    assert caught.value.category == "unauthorized"
    assert "wrong-unit-token" not in str(caught.value)


@pytest.mark.parametrize("path,category",[("/forbidden","unauthorized"),("/error","transport")])
def test_http_error_classification_exposes_no_response_body(runtime_server,path,category):
    from app.providers.meterless_transport import request_json
    from app.providers.meterless_settings import MeterlessError
    with pytest.raises(MeterlessError) as caught:
        request_json("GET",runtime_server+path,headers={"Authorization":"Bearer unit-http-only"},payload=None,timeout_s=3)
    assert caught.value.category == category
    assert "private-response-sentinel" not in str(caught.value)


@pytest.mark.parametrize("path",["/bad-json","/list","/nan"])
def test_invalid_structured_http_body_is_schema_error(runtime_server,path):
    from app.providers.meterless_transport import request_json
    from app.providers.meterless_settings import MeterlessError
    with pytest.raises(MeterlessError) as caught:
        request_json("GET",runtime_server+path,headers={"Authorization":"Bearer unit-http-only"},payload=None,timeout_s=3)
    assert caught.value.category == "schema"


def test_response_overflow_is_bounded_before_json_decode(runtime_server):
    from app.providers.meterless_transport import request_json
    from app.providers.meterless_settings import MeterlessError
    with pytest.raises(MeterlessError) as caught:
        request_json("GET",runtime_server+"/large",headers={"Authorization":"Bearer unit-http-only"},
                     payload=None,timeout_s=3,max_response_bytes=64)
    assert caught.value.category == "transport"


def test_slow_body_cannot_extend_total_budget_or_leave_child(runtime_server):
    import multiprocessing
    from app.providers.meterless_transport import request_json
    from app.providers.meterless_settings import MeterlessError
    before={p.pid for p in multiprocessing.active_children()}
    started=time.monotonic()
    with pytest.raises(MeterlessError) as caught:
        request_json("GET",runtime_server+"/drip",headers={"Authorization":"Bearer unit-http-only"},
                     payload=None,timeout_s=0.75)
    assert caught.value.category == "timeout"
    assert time.monotonic()-started < 3.5
    assert {p.pid for p in multiprocessing.active_children()} <= before


def test_expired_budget_starts_no_process(monkeypatch):
    import multiprocessing
    from app.providers.meterless_transport import request_json
    from app.providers.meterless_settings import MeterlessError
    def forbidden(*a,**k):raise AssertionError("expired budget created worker")
    monkeypatch.setattr(multiprocessing,"get_context",forbidden)
    with pytest.raises(MeterlessError) as caught:
        request_json("GET","http://127.0.0.1:1/",headers={},payload=None,timeout_s=0)
    assert caught.value.category == "timeout"


def test_process_construction_failure_is_secret_safe(monkeypatch,capsys):
    from types import SimpleNamespace
    import app.providers.meterless_transport as module
    from app.providers.meterless_settings import MeterlessError
    class Pipe:
        def close(self):pass
    def fail(**kwargs):raise RuntimeError("private-start-token")
    context=SimpleNamespace(Pipe=lambda **k:(Pipe(),Pipe()),Process=fail)
    monkeypatch.setattr(module,"multiprocessing",SimpleNamespace(get_context=lambda mode:context))
    with pytest.raises(MeterlessError) as caught:
        module.request_json("GET","http://127.0.0.1:1/",headers={},payload=None,timeout_s=1)
    assert caught.value.category == "transport"
    assert "private-start-token" not in str(caught.value)+capsys.readouterr().err


class _FakePipe:
    def __init__(self,waits):self.waits=waits;self.closed=False
    def poll(self,timeout):self.waits.append(timeout);return False
    def close(self):self.closed=True


class _FakeProcess:
    pid=101
    def __init__(self,start_error=False):self.alive=True;self.joined=[];self.start_error=start_error
    def start(self):
        if self.start_error:raise RuntimeError("private-start-token")
    def is_alive(self):return self.alive
    def terminate(self):self.alive=False
    def kill(self):self.alive=False
    def join(self,timeout):self.joined.append(timeout)
    def close(self):pass


def test_parent_recomputes_remaining_budget_before_every_wait(monkeypatch):
    from types import SimpleNamespace
    import app.providers.meterless_transport as module
    from app.providers.meterless_settings import MeterlessError
    waits=[];reader=_FakePipe(waits);writer=_FakePipe([]);process=_FakeProcess()
    ticks=iter([0,0.90,0.97,1.1])
    monkeypatch.setattr(module,"time",SimpleNamespace(monotonic=lambda:next(ticks)))
    context=SimpleNamespace(Pipe=lambda **k:(reader,writer),Process=lambda **k:process)
    monkeypatch.setattr(module,"multiprocessing",SimpleNamespace(get_context=lambda mode:context))
    with pytest.raises(MeterlessError) as caught:
        module.request_json("GET","http://127.0.0.1:1/",headers={},payload=None,timeout_s=1)
    assert caught.value.category == "timeout"
    assert waits == pytest.approx([0.05,0.03])
    assert not process.alive and process.joined and reader.closed and writer.closed


def test_partial_start_is_joined_without_exposing_failure(monkeypatch):
    from types import SimpleNamespace
    import app.providers.meterless_transport as module
    from app.providers.meterless_settings import MeterlessError
    process=_FakeProcess(start_error=True)
    context=SimpleNamespace(Pipe=lambda **k:(_FakePipe([]),_FakePipe([])),Process=lambda **k:process)
    monkeypatch.setattr(module,"multiprocessing",SimpleNamespace(get_context=lambda mode:context))
    with pytest.raises(MeterlessError) as caught:
        module.request_json("GET","http://127.0.0.1:1/",headers={},payload=None,timeout_s=1)
    assert caught.value.category == "transport" and "private-start-token" not in str(caught.value)
    assert not process.alive and process.joined


def _closed_pipe_worker(connection,*args):connection.close()


def test_worker_closing_pipe_is_classified_and_reaped(runtime_server,monkeypatch):
    import multiprocessing
    import app.providers.meterless_transport as module
    from app.providers.meterless_settings import MeterlessError
    before={p.pid for p in multiprocessing.active_children()}
    monkeypatch.setattr(module,"_worker",_closed_pipe_worker)
    with pytest.raises(MeterlessError) as caught:
        module.request_json("GET",runtime_server,headers={},payload=None,timeout_s=2)
    assert caught.value.category == "transport"
    assert {p.pid for p in multiprocessing.active_children()} <= before


def test_redirect_does_not_transmit_bearer_to_other_server(runtime_server):
    from urllib.parse import quote
    from app.providers.meterless_transport import request_json
    from app.providers.meterless_settings import MeterlessError
    seen=[]
    class Sink(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def do_GET(self):
            seen.append(dict(self.headers));self.send_response(200);self.send_header("Content-Length","0");self.end_headers()
    sink=ThreadingHTTPServer(("127.0.0.1",0),Sink)
    thread=threading.Thread(target=sink.serve_forever,daemon=True);thread.start()
    try:
        target="http://127.0.0.1:"+str(sink.server_port)+"/sink"
        with pytest.raises(MeterlessError) as caught:
            request_json("GET",runtime_server+"/redirect?target="+quote(target,safe=""),
                headers={"Authorization":"Bearer unit-http-only"},payload=None,timeout_s=3)
        assert caught.value.category == "transport" and seen == []
    finally:sink.shutdown();sink.server_close();thread.join(timeout=2)
