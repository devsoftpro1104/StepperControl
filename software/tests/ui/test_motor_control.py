import pytest

from controller_app.ui.widgets.motor_control import MotorControl


@pytest.mark.ui
def test_motor_control_constructs(qtbot) -> None:
    w = MotorControl()
    qtbot.addWidget(w)