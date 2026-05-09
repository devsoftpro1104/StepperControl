"""Entry point — `python -m controller_app`.

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

    model      = DeviceModel()
    view       = MainWindow()
    controller = DeviceController(model)

    # ---- model -> view ----
    model.connection_changed.connect(lambda connected, _port: view.set_connected(connected))
    model.log_appended.connect(view.log.append_line)
    model.dump_completed.connect(lambda snap: view.plot.show_dump(snap.samples, snap.sample_hz))

    # ---- view -> controller ----
    view.connect_requested.connect(controller.connect_to)
    view.disconnect_requested.connect(controller.disconnect)
    view.dump_requested.connect(controller.request_probe_dump)
    view.command_submitted.connect(controller.send_command)

    # ---- shutdown ----
    app.aboutToQuit.connect(controller.shutdown)

    view.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
