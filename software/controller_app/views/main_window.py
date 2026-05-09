"""Главное окно: header + QTabWidget с 4 вкладками.

Вкладки:
  1. СОЕДИНЕНИЕ — порт + панель CLI-команд
  2. МОТОР      — анимированный ротор + цифровой статус + waveform PROBE DUMP
  3. ДАТЧИКИ    — rolling-графики TEMP / HALL / PROBE
  4. ТЕРМИНАЛ   — лог + raw command-line

MainWindow — диспетчер. Сигналы пользователя поднимает наверх (для
DeviceController), сэмплы и лог-строки от модели прокидывает вниз
по соответствующим слотам вкладок.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QStatusBar, QTabWidget, QVBoxLayout,
    QWidget,
)

from .led import Led
from .tabs import ConnectTab, MotorTab, SensorsTab, TerminalTab
from .theme import (
    COL_DIGITAL, COL_GRN, COL_LABEL, app_qss, tab_qss,
)


class MainWindow(QMainWindow):
    # Наружу — для DeviceController
    connect_requested    = Signal(str)
    disconnect_requested = Signal()
    command_submitted    = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("STEPPER CONTROL  ·  CNC PANEL")
        self.resize(1280, 960)

        # ---- header ----
        title = QLabel("STEPPER CONTROL")
        tf = QFont("Segoe UI"); tf.setBold(True); tf.setPointSize(15)
        tf.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
        title.setFont(tf)
        title.setStyleSheet(f"color: {COL_DIGITAL}; background: transparent;")

        subtitle = QLabel("· STM32F4 host")
        sf = QFont("Segoe UI"); sf.setBold(True); sf.setPointSize(10)
        sf.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        subtitle.setFont(sf)
        subtitle.setStyleSheet(f"color: {COL_LABEL}; background: transparent;")

        self.led_link = Led(COL_GRN)
        link_lbl = QLabel("LINK")
        lf = QFont(); lf.setBold(True); lf.setPointSize(9)
        lf.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 2)
        link_lbl.setFont(lf)
        link_lbl.setStyleSheet(f"color: {COL_LABEL}; background: transparent;")

        led_box = QHBoxLayout()
        led_box.setSpacing(6)
        led_box.addWidget(self.led_link)
        led_box.addWidget(link_lbl)

        logo = QLabel()
        logo_path = Path(__file__).resolve().parent.parent / "resource" / "izto_logo.png"
        logo_pix = QPixmap(str(logo_path))
        logo.setPixmap(
            logo_pix.scaledToHeight(100, Qt.TransformationMode.SmoothTransformation)
        )
        logo.setStyleSheet("background: transparent;")

        title_box = QHBoxLayout()
        title_box.setSpacing(10)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header = QHBoxLayout()
        header.setContentsMargins(10, 6, 10, 6)
        header.addWidget(logo, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        header.addSpacing(16)
        header.addLayout(title_box)
        header.addStretch(1)
        header.addLayout(led_box)

        # ---- 4 вкладки ----
        self.connect_tab  = ConnectTab()
        self.motor_tab    = MotorTab()
        self.sensors_tab  = SensorsTab()
        self.terminal_tab = TerminalTab()

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(tab_qss())
        self.tabs.setDocumentMode(True)
        self.tabs.addTab(self.connect_tab,  "CONNECTION")
        self.tabs.addTab(self.motor_tab,    "MOTOR")
        self.tabs.addTab(self.sensors_tab,  "SENSORS")
        self.tabs.addTab(self.terminal_tab, "TERMINAL")

        # ---- общий layout ----
        root = QVBoxLayout()
        root.setContentsMargins(12, 10, 12, 12)
        root.setSpacing(10)
        root.addLayout(header)
        root.addWidget(self.tabs, 1)

        central = QWidget()
        central.setLayout(root)
        central.setStyleSheet(app_qss())
        self.setCentralWidget(central)

        # ---- status bar ----
        sb = QStatusBar()
        self.setStatusBar(sb)
        sb.showMessage("⏻  STANDBY  ·  не подключено")

        # ---- forward signals up ----
        self.connect_tab.connect_requested.connect(self.connect_requested)
        self.connect_tab.disconnect_requested.connect(self.disconnect_requested)
        self.connect_tab.command_requested.connect(self.command_submitted)
        self.terminal_tab.command_submitted.connect(self.command_submitted)

    # ===================================================================
    #  Слоты модели
    # ===================================================================

    def set_connected(self, connected: bool, port: str = "") -> None:
        self.connect_tab.set_connected(connected)
        self.led_link.set_on(connected)
        if connected:
            self.statusBar().showMessage(f"●  ONLINE  ·  {port}")
        else:
            self.statusBar().showMessage("○  OFFLINE")
            # очистить живые виджеты, чтобы старые данные не висели
            self.motor_tab.reset()
            self.sensors_tab.reset()

    def append_log(self, text: str, severity: str) -> None:
        self.terminal_tab.append_log(text, severity)

    def show_dump(self, snap) -> None:
        self.motor_tab.show_dump(snap.samples, snap.sample_hz)

    def on_motor_sample(self, sample) -> None:
        self.motor_tab.on_motor_sample(sample)

    def on_temp_sample(self, sample) -> None:
        self.sensors_tab.on_temp_sample(sample)

    def on_hall_sample(self, sample) -> None:
        self.sensors_tab.on_hall_sample(sample)

    def on_probe_sample(self, sample) -> None:
        self.sensors_tab.on_probe_sample(sample)

    # ---- shortcuts ----------------------------------------------------

    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if event.key() == Qt.Key.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)
