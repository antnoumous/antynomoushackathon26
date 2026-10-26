"""Driftwatch — an OCI tenancy auditor that argues with itself.

The interpreter check below exists so that an unsupported Python produces one actionable line
instead of a wall of annotation errors raised from inside pydantic: the domain models use
`X | None` annotations, which are evaluated at runtime and only parse from 3.10, while the
project targets 3.11.

There is an upper bound as well as a floor. `requirements.txt` pins pydantic 2.9.2, whose
compiled core (pydantic-core 2.23.4) ships wheels for CPython 3.8–3.13 only. On 3.14 pip falls
back to building pydantic-core from source, which needs a Rust toolchain and fails with a
compiler traceback that says nothing about the real cause. Verified on this machine: a 3.11
install succeeds, a 3.14 install of the same file fails building pydantic-core.
"""
from __future__ import annotations

import sys

MINIMUM_PYTHON = (3, 11)
# pydantic-core 2.23.4 publishes wheels up to cp313; 3.14 has none, so pip tries a Rust build.
MAXIMUM_PYTHON_EXCLUSIVE = (3, 14)


def check_python(version_info: tuple[int, ...]) -> None:
    """Raise one actionable error for an interpreter this project cannot install on."""
    current = tuple(version_info[:2])
    if current < MINIMUM_PYTHON:
        raise RuntimeError(
            "Driftwatch needs Python {}.{} or newer; this interpreter is {}.{}.\n"
            "Build the virtualenv with a supported interpreter, for example:\n"
            "    python3.11 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt\n"
            "Or run the container: docker build -t driftwatch . && docker run --rm -p 8000:8000 driftwatch"
            .format(*MINIMUM_PYTHON, *current)
        )
    if current >= MAXIMUM_PYTHON_EXCLUSIVE:
        raise RuntimeError(
            "Driftwatch is tested on Python {}.{} through 3.13; this interpreter is {}.{}.\n"
            "Python 3.14 has no pydantic-core wheel for the pinned pydantic, so pip would try to\n"
            "compile it from source and fail. Use 3.11, 3.12 or 3.13:\n"
            "    python3.11 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt\n"
            "Or run the container: docker build -t driftwatch . && docker run --rm -p 8000:8000 driftwatch"
            .format(*MINIMUM_PYTHON, *current)
        )


check_python(tuple(sys.version_info[:2]))

__all__ = ["MINIMUM_PYTHON", "MAXIMUM_PYTHON_EXCLUSIVE", "check_python"]
