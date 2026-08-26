"""Launcher so the tool runs as `python paper_download.py ...` from anywhere, without -m."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paper_download.cli import main

if __name__ == "__main__":
    main()
