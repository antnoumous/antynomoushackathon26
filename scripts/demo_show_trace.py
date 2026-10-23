# scripts/demo_show_trace.py
"""Print the agent narrative of a trace file: one line per handoff.

Used by the demo recording and handy in review: it reads the newest logs/trace-*.jsonl
(or a given path) and shows which named agent did what, in order.
"""
import glob
import json
import sys
from pathlib import Path

LIMIT = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 12


def latest() -> Path:
    files = sorted(glob.glob("logs/trace-*.jsonl"), key=lambda p: Path(p).stat().st_mtime)
    if not files:
        print("no traces in logs/ yet — run `python run.py` first")
        raise SystemExit(1)
    return Path(files[-1])


def provenance(path: Path) -> int:
    """Print the sponsor snapshot provenance exactly as the run recorded it."""
    shown = 0
    for line in path.read_text().splitlines():
        e = json.loads(line)
        if e["action"] != "source_snapshot":
            continue
        p = json.loads(e["output_summary"])
        print(f"{e['agent_name']:<8} source_snapshot [{p['provider']}] {p['object_name']}")
        print(f"          snapshot={p['snapshot_id']} rows={p['row_count']}/{p['expected_count']}"
              f" digest={p['content_sha256'][:16]}… scope={p['requested_scope_hash'][:12]}…")
        shown += 1
    if not shown:
        print("no source_snapshot events in this trace (file-mode run?)")
    return 0


def main() -> int:
    if len(sys.argv) > 2 and sys.argv[1] == "--prov":
        return provenance(Path(sys.argv[2]))
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    path = Path(arg) if arg and not arg.isdigit() else latest()
    print(f"── {path.name} ──")
    rows = []
    for line in path.read_text().splitlines():
        e = json.loads(line)
        rows.append(f"{e['agent_name']:<8} {e['action']:<20} {e['status']:<9} "
                    f"{e['input_summary'][:34]:<34} → {e['output_summary'][:40]}")
    for r in rows[:LIMIT]:
        print(r)
    if len(rows) > LIMIT:
        print(f"… {len(rows) - LIMIT} more events in the file")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
