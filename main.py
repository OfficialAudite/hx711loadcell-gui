"""
Entry point for the HX711 app (Qt Quick / PySide6).

Run with `python main.py` or add `--demo` to preview without HX711 hardware.
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional


def _run_qt(demo: bool) -> int:
    """Launch the Qt Quick UI."""
    try:
        from lib.qt_app import run_qt_app
    except ImportError:
        msg = "PySide6 is required. Install with `pip install PySide6`."
        print(msg, file=sys.stderr)
        return 1
    return run_qt_app(demo=demo)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="HX711 Load Cell UI")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run with simulated readings (no HX711 hardware required, Qt UI only)",
    )
    args = parser.parse_args(argv)

    return _run_qt(demo=args.demo)


if __name__ == "__main__":
    sys.exit(main())
