import pytest

from controller_app.ui.main_window import MainWindow


@pytest.mark.ui
def test_main_window_shows(qtbot) -> None:
    w = MainWindow()
    qtbot.addWidget(w)
    assert w.windowTitle() == "Stepper Controller"