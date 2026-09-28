# tests/test_mask_ocids.py
"""The masking tool is the guarantee behind "no real OCID is committed", so it gets tested too."""
from pathlib import Path

from scripts.mask_ocids import mask_text

LONG = "ocid1.instance.oc1.ap-singapore-1.anxhiljq6mzqzjxqwvqgpxkwu7nfhvkvbemyh5qxh7wnnrmgvaj7qxzq"
# A short, hand-written identifier is the case the review found slipping through: it looks like an
# OCID and a reader cannot tell it is not real.
SHORT = "ocid1.instance.oc1.ap-singapore-1.an9hxljr3f2a"


def test_a_real_shaped_ocid_is_masked_but_stays_readable():
    masked, count = mask_text(LONG)
    assert count == 1
    assert masked == "ocid1.instance.oc1.ap-singapore-1..\u2022\u2022\u2022\u2022qxzq"


def test_a_short_identifier_is_masked_too():
    masked, count = mask_text(SHORT)
    assert count == 1
    assert "an9hxljr3f2a" not in masked
    assert masked.startswith("ocid1.instance.oc1.ap-singapore-1..")


def test_masking_is_idempotent():
    once, _ = mask_text(LONG)
    twice, count = mask_text(once)
    assert count == 0
    assert twice == once


def test_an_already_masked_fixture_id_is_left_alone():
    fixture = "ocid1.instance.oc1..\u2022\u2022\u2022\u2022bbb2"
    masked, count = mask_text(fixture)
    assert count == 0 and masked == fixture


def test_the_env_example_placeholder_is_not_touched():
    placeholder = "OCID_TENANCY=ocid1.tenancy.oc1..replace-me"
    masked, count = mask_text(placeholder)
    assert count == 0 and masked == placeholder


def test_no_unmasked_ocid_is_committed_anywhere_in_the_repository():
    """The whole-repo check, run as a test so a future commit cannot quietly reintroduce one.

    It scans exactly what git tracks (or would track: `git ls-files --cached --others
    --exclude-standard`), which honours the guard's contract — "committed, anywhere" — and
    keeps a developer's live-run scratch under logs/ from failing the suite on their own
    machine. .env files are the designed home of real identifiers and are skipped; every
    other tracked file is checked."""
    import subprocess
    from scripts.mask_ocids import OCID
    listing = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        capture_output=True, text=True, check=True).stdout.splitlines()
    offenders = []
    for entry in listing:
        path = Path(entry)
        if not path.is_file():
            continue
        if path.name == Path(__file__).name:      # this file must contain example ids to test with
            continue
        if path.suffix not in {".py", ".json", ".jsonl", ".md", ".txt", ".log", ".example", ".yml", ".yaml", ".sh", ".toml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for match in OCID.finditer(text):
            offenders.append(f"{path}: {match.group(0)[:60]}")
    assert offenders == []
