"""Жильной осциллограф: rolling time-series с цианистым фосфорным трейсом.

Параметризован по диапазону Y, шагам сетки и форматам подписей. Один и тот
же класс рисует TEMP (signed °C), HALL (raw 0..4095), PROBE (ADC 0..4095)
и т.п. — конкретные настройки задаёт фабрика из tab-файлов.

Использование:
    chart = ScopeChart(y_min=-10, y_max=60,
                       y_step_major=10, y_step_minor=5,
                       axis_label="°C")
    chart.push_value(temp_c)        # каждый раз когда пришёл сэмпл
"""

from __future__ import annotations

import math
import time
from collections import deque
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from .theme import (
    COL_BG_INSET, COL_DIGITAL, COL_DIGITAL_DIM, COL_LABEL, COL_PANEL_EDGE,
    COL_TEXT_DIM,
)


class ScopeChart(QWidget):
    WINDOW_S       = 30.0      # ширина окна, секунд
    SEC_STEP_MAJOR = 5         # вертикальные деления времени, с

    def __init__(
        self,
        y_min: float,
        y_max: float,
        y_step_major: float,
        y_step_minor: float,
        *,
        axis_label: str = "VALUE",
        unit_label: Optional[str] = None,
        value_fmt: str = "{:+7.1f}",
        tick_fmt: str  = "{:+.0f}",
        zero_line: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._y_min      = float(y_min)
        self._y_max      = float(y_max)
        self._step_major = float(y_step_major)
        self._step_minor = float(y_step_minor)
        self._axis_label = axis_label
        self._unit_label = unit_label if unit_label is not None else axis_label
        self._value_fmt  = value_fmt
        self._tick_fmt   = tick_fmt
        self._zero_line  = zero_line and y_min <= 0 <= y_max

        self._samples: deque[tuple[float, float]] = deque()
        self._t0: Optional[float] = None
        self._current: float = (y_min + y_max) / 2.0
        self._idle_value: float = self._current
        self._has_data: bool = False

        self.setMinimumSize(560, 140)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding,
        )

        # 20 Hz: продлеваем трассу последним значением и перерисовываем —
        # линия не «застывает» при паузе телеметрии.
        self._timer = QTimer(self)
        self._timer.setInterval(50)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ---- публичный API ------------------------------------------------

    def push_value(self, v: float) -> None:
        if self._t0 is None:
            self._t0 = time.monotonic()
        self._current = float(v)
        self._has_data = True
        self._samples.append((time.monotonic() - self._t0, float(v)))

    def reset(self) -> None:
        self._samples.clear()
        self._t0 = None
        self._current = self._idle_value
        self._has_data = False
        self.update()

    # ---- тикер --------------------------------------------------------

    def _tick(self) -> None:
        if self._t0 is not None:
            t = time.monotonic() - self._t0
            self._samples.append((t, self._current))
            cutoff = t - self.WINDOW_S - 0.5
            while len(self._samples) > 2 and self._samples[0][0] < cutoff:
                self._samples.popleft()
        self.update()

    def _iter_grid(self, step: float):
        if step <= 0:
            return
        i = 0
        while True:
            v = self._y_min + i * step
            if v > self._y_max + 1e-6:
                return
            yield v
            i += 1

    # ---- рисование ----------------------------------------------------

    def paintEvent(self, _event) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        m_left, m_right, m_top, m_bottom = 70, 28, 40, 36
        plot = QRectF(
            m_left, m_top,
            max(50.0, self.width()  - m_left - m_right),
            max(50.0, self.height() - m_top  - m_bottom),
        )

        p.fillRect(self.rect(), QColor(COL_BG_INSET))

        # коробка осциллографа
        bezel_grad = QLinearGradient(plot.topLeft(), plot.bottomLeft())
        bezel_grad.setColorAt(0.0, QColor("#02060a"))
        bezel_grad.setColorAt(1.0, QColor("#040b10"))
        p.setBrush(QBrush(bezel_grad))
        p.setPen(QPen(QColor(COL_PANEL_EDGE), 1))
        p.drawRect(plot)

        # лёгкий цианистый виньет
        digital_rgb = QColor(COL_DIGITAL)
        vg = QRadialGradient(plot.center(), max(plot.width(), plot.height()))
        vg.setColorAt(0.0, QColor(0, 0, 0, 0))
        vg.setColorAt(1.0, QColor(
            digital_rgb.red(), digital_rgb.green(), digital_rgb.blue(), 22,
        ))
        p.save()
        p.setClipRect(plot)
        p.setBrush(QBrush(vg))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(plot)
        p.restore()

        y_min, y_max = self._y_min, self._y_max
        y_range = y_max - y_min if y_max > y_min else 1.0

        def v_to_y(v: float) -> float:
            return plot.bottom() - (v - y_min) / y_range * plot.height()

        # ---- сетка по Y (мелкая + крупная) ----
        minor_color = QColor(
            digital_rgb.red(), digital_rgb.green(), digital_rgb.blue(), 22,
        )
        major_color = QColor(
            digital_rgb.red(), digital_rgb.green(), digital_rgb.blue(), 55,
        )
        minor_pen = QPen(minor_color, 1, Qt.PenStyle.DotLine)
        major_pen = QPen(major_color, 1)

        majors: list[float] = list(self._iter_grid(self._step_major))
        majors_set = {round(v / self._step_major) for v in majors}

        p.setPen(minor_pen)
        for v in self._iter_grid(self._step_minor):
            idx_major = round(v / self._step_major) if self._step_major > 0 else None
            if idx_major in majors_set and abs(v - idx_major * self._step_major) < 1e-6:
                continue
            y = v_to_y(v)
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))

        p.setPen(major_pen)
        for v in majors:
            y = v_to_y(v)
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))

        if self._zero_line:
            p.setPen(QPen(QColor(COL_DIGITAL), 1.4))
            y0 = v_to_y(0.0)
            p.drawLine(QPointF(plot.left(), y0), QPointF(plot.right(), y0))

        # ---- сетка по времени ----
        t_now  = (time.monotonic() - self._t0) if self._t0 is not None else 0.0
        t_left = t_now - self.WINDOW_S

        def t_to_x(t: float) -> float:
            return plot.left() + (t - t_left) / self.WINDOW_S * plot.width()

        sec = math.floor(t_left / self.SEC_STEP_MAJOR) * self.SEC_STEP_MAJOR
        p.setPen(major_pen)
        while sec <= t_now + 1e-6:
            x = t_to_x(sec)
            if plot.left() - 0.5 <= x <= plot.right() + 0.5:
                p.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
            sec += self.SEC_STEP_MAJOR

        # ---- подписи Y ----
        f_axis = QFont("Consolas"); f_axis.setPointSize(9); f_axis.setBold(True)
        p.setFont(f_axis)
        p.setPen(QPen(QColor(COL_TEXT_DIM)))
        for v in majors:
            y = v_to_y(v)
            rect = QRectF(0, y - 10, m_left - 8, 20)
            p.drawText(
                rect,
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                self._tick_fmt.format(v),
            )

        # ---- подписи X (отн. «сейчас») ----
        sec = math.floor(t_left / self.SEC_STEP_MAJOR) * self.SEC_STEP_MAJOR
        while sec <= t_now + 1e-6:
            x = t_to_x(sec)
            if plot.left() - 30 <= x <= plot.right() + 30:
                rel = sec - t_now
                rect = QRectF(x - 30, plot.bottom() + 6, 60, 18)
                p.drawText(
                    rect,
                    Qt.AlignmentFlag.AlignCenter,
                    f"{rel:+.0f}s" if abs(rel) > 1e-3 else "0s",
                )
            sec += self.SEC_STEP_MAJOR

        # ---- подписи осей ----
        f_label = QFont(); f_label.setPointSize(9); f_label.setBold(True)
        f_label.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4)
        p.setFont(f_label)
        p.setPen(QPen(QColor(COL_LABEL)))

        p.save()
        p.translate(18, plot.center().y())
        p.rotate(-90)
        p.drawText(
            QRectF(-80, -10, 160, 20),
            Qt.AlignmentFlag.AlignCenter, self._axis_label,
        )
        p.restore()

        p.drawText(
            QRectF(plot.left(), self.height() - 22, plot.width(), 18),
            Qt.AlignmentFlag.AlignCenter, "TIME",
        )

        # ---- трасса (3-слойная: glow + средний + резкий) ----
        if self._t0 is not None and len(self._samples) >= 2:
            path = QPainterPath()
            first = True
            for ts, rv in self._samples:
                if ts < t_left - 0.05:
                    continue
                x = t_to_x(ts)
                rv_clip = max(y_min, min(y_max, rv))
                y = v_to_y(rv_clip)
                if first:
                    path.moveTo(x, y)
                    first = False
                else:
                    path.lineTo(x, y)

            p.save()
            p.setClipRect(plot)
            for width, alpha in ((7, 55), (3.4, 140), (1.6, 255)):
                col = QColor(COL_DIGITAL); col.setAlpha(alpha)
                p.setPen(QPen(
                    col, width,
                    Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                    Qt.PenJoinStyle.RoundJoin,
                ))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(path)
            p.restore()

        # ---- курсор справа (только когда есть данные) ----
        p.setPen(QPen(QColor(COL_DIGITAL_DIM), 1, Qt.PenStyle.DashLine))
        p.drawLine(
            QPointF(plot.right(), plot.top()),
            QPointF(plot.right(), plot.bottom()),
        )
        if self._has_data:
            cur_y = v_to_y(max(y_min, min(y_max, self._current)))
            glow_dot = QColor(COL_DIGITAL); glow_dot.setAlpha(80)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(glow_dot))
            p.drawEllipse(QPointF(plot.right(), cur_y), 11, 11)
            p.setBrush(QBrush(QColor(COL_DIGITAL)))
            p.drawEllipse(QPointF(plot.right(), cur_y), 5, 5)

        # ---- большой readout текущего значения в правом верхнем углу ----
        f_big = QFont("Consolas"); f_big.setPointSize(28); f_big.setBold(True)
        f_big.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
        p.setFont(f_big)
        p.setPen(QPen(QColor(COL_DIGITAL_DIM if not self._has_data else COL_DIGITAL)))
        readout_w = 230
        rect = QRectF(plot.right() - readout_w - 14, plot.top() + 10, readout_w, 50)
        readout_text = self._value_fmt.format(self._current) if self._has_data else "— — —"
        p.drawText(
            rect,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            readout_text,
        )

        f_unit = QFont(); f_unit.setPointSize(9); f_unit.setBold(True)
        f_unit.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 4)
        p.setFont(f_unit)
        p.setPen(QPen(QColor(COL_LABEL)))
        rect2 = QRectF(plot.right() - readout_w - 14, plot.top() + 60, readout_w, 18)
        p.drawText(
            rect2,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            self._unit_label,
        )
