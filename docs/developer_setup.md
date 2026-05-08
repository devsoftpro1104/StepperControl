# Установка окружения разработчика

## Прошивка
1. ARM GNU Toolchain (≥ 13.x): `arm-none-eabi-gcc`.
2. CMake ≥ 3.22, Ninja.
3. ST-Link / OpenOCD / pyOCD для прошивки.
4. Сборка:
   ```
   cmake --preset firmware-debug
   cmake --build --preset firmware-debug
   ```

## Хост
1. Python 3.11+.
2. `cd software && python -m venv .venv && .venv\Scripts\activate`.
3. `pip install -r requirements-dev.txt`.
4. Запуск: `python -m controller_app`.
5. Тесты: `pytest`.

## Кодстайл
- C: `clang-format` (LLVM-based, см. .clang-format).
- Python: `ruff format`, `ruff check`, `mypy`.