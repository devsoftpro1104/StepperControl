"""Entry point — `python -m controller_app` (или `python linux/run.py`).

Здесь и только здесь связываются Model / View / Controller. Вид собирается
в `StepperControlApp.build()`, привязки сигналов — в `on_start()` (после
того как корневой виджет уже создан).
"""

from __future__ import annotations

import sys

from .controllers import DeviceController
from .models import DeviceModel
from .views import StepperControlApp


def main() -> int:
    model      = DeviceModel()
    controller = DeviceController(model)
    app        = StepperControlApp(model=model, controller=controller)
    app.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
