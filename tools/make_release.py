"""Сборка релизного артефакта: прошивка + хост + чексуммы.

Использование:
    python tools/make_release.py --version 0.1.0
"""
from __future__ import annotations

import argparse
import sys


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--version", required=True)
    args = p.parse_args(argv)
    print(f"Build release {args.version} (TODO)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))