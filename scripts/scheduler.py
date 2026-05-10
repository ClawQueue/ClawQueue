#!/usr/bin/env python3
"""Executable entry point for the ClawQueue scheduler."""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from clawqueue.dispatcher import main


if __name__ == "__main__":
    sys.exit(main())
