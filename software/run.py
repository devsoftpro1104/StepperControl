"""Запуск GUI: `python run.py` из папки software/ или F5 в VS Code."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from controller_app.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
