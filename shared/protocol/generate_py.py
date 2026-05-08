"""Генерация Python-модуля messages.py по protocol.yaml.

Использование:
    python generate_py.py protocol.yaml \\
        ../../software/src/controller_app/protocol/messages.py
"""
from __future__ import annotations
import sys


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(__doc__)
        return 2
    # TODO: реализовать кодогенерацию dataclass-сообщений и кодеков.
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))