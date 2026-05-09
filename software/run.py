"""Entry point хост-приложения StepperControl.

Открой этот файл и жми кнопку «Run Python File» (▷) в правом верхнем
углу редактора — она запускает текущий файл напрямую, минуя launch.json
(в котором по F5 висит отладка прошивки).

Эквивалент из терминала:
    cd software && .venv\\Scripts\\python.exe -m controller_app
"""

from controller_app.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
