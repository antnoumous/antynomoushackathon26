#!/usr/bin/env python3
"""Mask OCIDs in files before they are committed or shown on camera.

A real OCID ends in a long opaque identifier; this replaces that identifier with a masked form
that keeps the resource type, the region and the last four characters, so a reader can still
follow a finding.

    python scripts/mask_ocids.py logs/trace-run-abc.jsonl output_examples/example_1.json

Idempotent: an already-masked OCID does not match, so running it twice changes nothing.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

MASK = "\u2022\u2022\u2022\u2022"
USAGE = ("usage: python scripts/mask_ocids.py FILE [FILE ...]\n"
         "Masks OCIDs in place. Idempotent.")
# A real OCID ends in a long opaque suffix, but the threshold is deliberately low (8) so a short
# or hand-written identifier is still caught — an unmasked example token in a document is exactly
# the kind of leak this tool exists to prevent. Already-masked ids contain bullets, so they cannot
# match, which is what makes the tool idempotent.
OCID = re.compile(r"\bocid1\.([a-z0-9_]+)\.([a-z0-9]+)\.([a-z0-9-]*)\.[A-Za-z0-9]{8,}\b")


def mask_text(text: str) -> tuple[str, int]:
    def replace(match: re.Match) -> str:
        kind, realm_region, region = match.group(1), match.group(2), match.group(3)
        suffix = match.group(0)[-4:]
        parts = [part for part in (realm_region, region) if part]
        return f"ocid1.{kind}.{'.'.join(parts)}..{MASK}{suffix}"

    return OCID.subn(replace, text)


def mask_file(path: Path) -> int:
    original = path.read_text(encoding="utf-8")
    masked, count = mask_text(original)
    if count:
        path.write_text(masked, encoding="utf-8")
    return count


def main(argv: list[str]) -> int:
    if not argv:
        print(USAGE)
        return 2
    total = 0
    for name in argv:
        path = Path(name)
        if not path.is_file():
            print(f"not a file: {path}")
            continue
        count = mask_file(path)
        total += count
        print(f"{path}: {count} ocid(s) masked")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
