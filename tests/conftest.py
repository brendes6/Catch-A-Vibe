"""Shared pytest configuration.

Adds the backend and data-processing directories to sys.path so the
pure modules under test can be imported without a package install.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

for subdir in ("backend", "data-processing"):
    path = str(ROOT / subdir)
    if path not in sys.path:
        sys.path.insert(0, path)
