#!/usr/bin/env python3
"""Assemble approved narration over genuine demo scenes without altering evidence.

Requires only Python's standard library and ffmpeg. The narration MP3s and manifest live in
docs/demo/narration/. Does not generate speech or contact a network.

Two scene kinds are supported. A `source` scene plays an interval of the recorded silent video.
A `card` scene holds a static PNG that was rendered from committed run output; the manifest
records where that card came from, and this script refuses a card without that note.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import wave


def run(args: list[str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"Command failed: {args!r}\n{result.stderr[-8000:]}")
    return result


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def clock(seconds: float) -> str:
    minutes, secs = divmod(round(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    parser.add_argument("--scratch", type=Path, default=Path(os.environ.get(
        "TMPDIR", str(Path.home() / ".hermes/cache/scratch"))) / "driftwatch-voiceover-build")
    args = parser.parse_args()
    if not args.ffmpeg:
        parser.error("ffmpeg is required; pass --ffmpeg /absolute/path/to/ffmpeg")
    root = Path(__file__).resolve().parents[1]
    narration = root / "docs/demo/narration"
    manifest = json.loads((narration / "manifest.json").read_text())
    source = root / manifest["source_video"]
    source_hash = sha256(source)
    video = root / manifest["output_video"]
    audio = root / manifest["output_audio"]
    if any(scene.get("kind") == "card" for scene in manifest["scenes"]):
        if not manifest.get("card_note", "").strip():
            raise ValueError("A card scene must document where the card came from")
    args.scratch.mkdir(parents=True, exist_ok=True)
    rows = []
    segments = []
    cursor = 0.0
    previous_end = 0.0
    seen_card = False
    prefix = [args.ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
    for scene in manifest["scenes"]:
        kind = scene.get("kind", "source")
        mp3 = narration / f"{scene['id']}.mp3"
        wav = args.scratch / f"{scene['id']}.wav"
        run(prefix + ["-i", str(mp3), "-ar", "48000", "-ac", "1", str(wav)])
        with wave.open(str(wav), "rb") as handle:
            speech_seconds = handle.getnframes() / handle.getframerate()
        if kind == "card":
            card_image = root / scene["image"] if scene.get("image") else root / manifest.get("card_image", "")
            if not card_image.is_file():
                raise ValueError(f"Card scene {scene['id']} needs an existing image")
            seen_card = True
            original_seconds = 0.0
            duration = math.ceil((speech_seconds + 1.4 - 1e-8) * 10) / 10
        elif kind == "source":
            if seen_card:
                raise ValueError("Source scenes must precede card scenes")
            start, end = float(scene["start"]), float(scene["end"])
            if not math.isclose(start, previous_end) or end <= start:
                raise ValueError(f"Scene gap, overlap or bad interval: {scene['id']}")
            previous_end = end
            original_seconds = end - start
            # Half a second before the voice and at least 0.9 seconds after it.
            duration = math.ceil((max(original_seconds, speech_seconds + 1.4) - 1e-8) * 10) / 10
        else:
            raise ValueError(f"Unknown scene kind: {kind!r}")
        padding = max(0.0, duration - original_seconds)
        output = args.scratch / f"{scene['id']}.mp4"
        audio_filters = (
            "[1:a]loudnorm=I=-18:TP=-2:LRA=7,aresample=48000,"
            f"adelay=500,apad,atrim=duration={duration:.6f},asetpts=PTS-STARTPTS[a]"
        )
        if kind == "card":
            filters = (
                f"[0:v]scale=786:560,fps=10,setsar=1,format=yuv420p,"
                f"trim=duration={duration:.6f},setpts=PTS-STARTPTS[v];" + audio_filters
            )
            run(prefix + ["-loop", "1", "-i", str(card_image), "-i", str(wav),
                "-filter_complex", filters, "-map", "[v]", "-map", "[a]", "-t", f"{duration:.6f}",
                "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "1",
                "-movflags", "+faststart", str(output)])
        else:
            filters = (
                f"[0:v]setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={padding:.6f},"
                f"trim=duration={duration:.6f},fps=10,setsar=1,format=yuv420p[v];" + audio_filters
            )
            start = float(scene["start"])
            run(prefix + ["-ss", f"{start:.6f}", "-t", f"{original_seconds:.6f}",
                "-i", str(source), "-i", str(wav), "-filter_complex", filters,
                "-map", "[v]", "-map", "[a]", "-t", f"{duration:.6f}",
                "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "1",
                "-movflags", "+faststart", str(output)])
        row = {
            "id": scene["id"], "kind": kind,
            "source_start": scene.get("start"), "source_end": scene.get("end"),
            "output_start": round(cursor, 3), "output_end": round(cursor + duration, 3),
            "speech_start": round(cursor + 0.5, 3),
            "speech_end": round(cursor + 0.5 + speech_seconds, 3),
            "speech_seconds": round(speech_seconds, 6),
            "trailing_silence_seconds": round(duration - 0.5 - speech_seconds, 6),
            "extended_hold_seconds": round(padding, 3),
            "narration_sha256": sha256(mp3), "text": scene["text"],
        }
        assert row["trailing_silence_seconds"] >= 0.89
        rows.append(row)
        segments.append(output)
        cursor += duration
        print(json.dumps(row), flush=True)
    assert 60 <= cursor <= 240, f"Outside the 1–4 minute demo range: {cursor}s"
    listing = args.scratch / "concat.txt"
    listing.write_text("".join(f"file '{p.as_posix()}'\n" for p in segments))
    run(prefix + ["-f", "concat", "-safe", "0", "-i", str(listing),
        "-c", "copy", "-map_metadata", "-1", "-metadata", "title=Driftwatch — narrated review cut",
        "-metadata", "comment=Recorded execution; synthetic data; AI narration; scene holds extended "
        "for readability. Zetaris executed live; Meterless World Model local; Nightshift implemented, "
        "no live inference.",
        "-movflags", "+faststart", str(video)])
    run(prefix + ["-i", str(video), "-vn", "-c:a", "libmp3lame", "-b:a", "128k", str(audio)])
    # Exercise the entire delivered audiovisual bitstream, not only the container header.
    run([args.ffmpeg, "-hide_banner", "-v", "error", "-xerror", "-i", str(video), "-f", "null", "-"])
    inspection = subprocess.run([args.ffmpeg, "-hide_banner", "-i", str(video)], capture_output=True, text=True)
    if "Video: h264" not in inspection.stderr or "Audio: aac" not in inspection.stderr:
        raise ValueError(f"Missing expected streams: {inspection.stderr}")
    duration_match = re.search(r"Duration: (\d+):(\d+):([\d.]+)", inspection.stderr)
    if not duration_match:
        raise ValueError("Could not read final file duration")
    measured = (int(duration_match[1]) * 3600 + int(duration_match[2]) * 60 + float(duration_match[3]))
    assert abs(measured - cursor) < 0.3, (measured, cursor)
    assert sha256(source) == source_hash, "Original silent video was changed"
    levels = run([args.ffmpeg, "-hide_banner", "-i", str(video), "-af", "volumedetect", "-f", "null", "-"])
    report = {
        "status": manifest["status"], "source_video": manifest["source_video"],
        "source_sha256_before": source_hash, "source_sha256_after": sha256(source),
        "original_preserved": True, "duration_seconds": round(measured, 3),
        "planned_timeline_seconds": round(cursor, 3), "full_decode_passed": True,
        "video_codec": "h264", "audio_codec": "aac", "speech_provider": "edge",
        "narration_voice": "same configured voice as the user-approved audition",
        "video_sha256": sha256(video), "audio_sha256": sha256(audio),
        "video_bytes": video.stat().st_size, "audio_bytes": audio.stat().st_size,
        "card_image": manifest.get("card_image"), "card_note": manifest.get("card_note"),
        "audio_levels": [line.strip() for line in levels.stderr.splitlines()
                         if "mean_volume:" in line or "max_volume:" in line],
        "scenes": rows,
        "verification_limits": "Decode, level, scene-boundary and frame checks do not prove subjective "
        "pronunciation or listening quality. No claim of a new application test run is made.",
    }
    (narration / "build-report.json").write_text(json.dumps(report, indent=2) + "\n")
    transcript = ["# Driftwatch — narrated review cut", "",
        "Synthetic narration using the voice approved by the user. The silent original is unchanged.",
        "Recorded execution with editorial scene holds; this is not an execution-time benchmark.",
        "**Sponsor status:** Zetaris executed live; the Meterless World Model is implemented and consumed "
        "locally; the Nightshift provider is implemented and contract-tested but has served no live "
        "request, because the vendor's Mac installer fails macOS Gatekeeper.", "",
        f"Duration: {clock(measured)} ({measured:.2f} seconds).", "",
        "Rebuild from the stored MP3 segments: `python3.11 scripts/assemble_demo_voiceover.py`.", "",
        "## Narration", ""]
    for row in rows:
        transcript += [f"### {clock(row['output_start'])}–{clock(row['output_end'])} · {row['id']}",
                       "", row["text"], ""]
    (narration / "transcript.md").write_text("\n".join(transcript))
    print(json.dumps({k: v for k, v in report.items() if k != "scenes"}, indent=2))


if __name__ == "__main__":
    main()
