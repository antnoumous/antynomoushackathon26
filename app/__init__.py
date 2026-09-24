"""Driftwatch — an OCI tenancy auditor that argues with itself.

The interpreter check below exists so that an unsupported Python produces one actionable line
instead of a wall of annotation errors raised from inside pydantic: the domain models use
`X | None` annotations, which are evaluated at runtime and only parse from 3.10, while the
project targets 3.11.
"""
from __future__ import annotations

import sys

MINIMUM_PYTHON = (3, 11)

if sys.version_info < MINIMUM_PYTHON:
    raise RuntimeError(
        "Driftwatch needs Python {}.{} or newer; this interpreter is {}.{}.\n"
        "Build the virtualenv with a supported interpreter, for example:\n"
        "    python3.11 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt\n"
        "Or run the container: docker build -t driftwatch . && docker run --rm -p 8000:8000 driftwatch"
        .format(*MINIMUM_PYTHON, *sys.version_info[:2])
    )

__all__ = ["MINIMUM_PYTHON"]
