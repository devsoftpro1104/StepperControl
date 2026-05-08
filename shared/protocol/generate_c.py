"""Генерация C-заголовка по protocol.yaml.

Использование:
    python generate_c.py protocol.yaml \\
        ../../firmware/src/middleware/protocol/inc/protocol_gen.h
"""
from __future__ import annotations
import sys


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    # TODO: реализовать парсер YAML и шаблонизацию C-заголовка.
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))