"""Entry point — `python -m controller_app` или `python software/run.py`.

Здесь и только здесь связываются Model / View / Controller. Дальше
расширение идёт точечно: добавили новый сигнал в model — подписали view;
добавили новую панель в view — подписали её сигнал на слот контроллера.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .controllers import DeviceController
from .models import DeviceModel
from .views import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("StepperControl")
    # Fusion — единый кросс-платформенный стиль; Windows-native рендерер
    # на некоторых машинах подтягивает Fixedsys и роняется в DirectWrite.
    app.setStyle("Fusion")

    model      = DeviceModel()
    view       = MainWindow()
    controller = DeviceController(model)

    # ---- model -> view ----
    model.connection_changed.connect(view.set_connected)
    model.log_appended.connect(view.append_log)
    model.dump_completed.connect(view.show_dump)
    model.motor_sample_received.connect(view.on_motor_sample)
    model.temp_sample_received.connect(view.on_temp_sample)
    model.hall_sample_received.connect(view.on_hall_sample)

    # ---- view -> controller ----
    view.connect_requested.connect(controller.connect_to)
    view.disconnect_requested.connect(controller.disconnect)
    view.command_submitted.connect(controller.send_command)

    # ---- shutdown ----
    app.aboutToQuit.connect(controller.shutdown)

    view.showFullScreen()
    view.raise_()
    view.activateWindow()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
