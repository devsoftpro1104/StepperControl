"""One-shot осциллограф для PROBE DUMP — визуально как ScopeChart.

Та же тёмная коробка с цианистым фосфорным трейсом, сеткой и большим
readout'ом, что и в `ScopeChart`. Но вместо rolling-окна по wall-clock
здесь жёстко-длинный снимок: ось X = время от 0 до n/sample_hz.

Большой readout — измеренная частота STEP-импульсов: ищем восходящие
фронты по пересечению средней линии (амплитуда / 2), считаем средний
период между ними и выводим Hz + T в µs.
"""

from __future__ import annotations

import math
from typing import Optional

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen,
    QRadialGradient,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from .theme import (
    COL_BG_INSET, COL_DIGITAL, COL_DIGITAL_DIM, COL_LABEL, COL_PANEL_EDGE,
    COL_TEXT_DIM,
)


class DumpChart(QWidget):
    VREF_V   = 3.3
    ADC_FULL = 4095.0

    def __init__(
        self,
        *,
        y_min: float = 0.0,
        y_max: float = 3.3,
        y_step_major: float = 0.5,
        y_step_minor: float = 0.1,
        axis_label: str = "V",
        tick_fmt: str  = "{:+.1f}",
        zero_line: bool = False,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._y_min      = float(y_min)
        self._y_max      = float(y_max)
        self._step_major = float(y_step_major)
        self._step_minor = float(y_step_minor)
        self._axis_label = axis_label
        self._tick_fmt   = tick_fmt
        self._zero_line  = zero_line and y_min <= 0 <= y_max

        self._t_us: Optional[np.ndarray] = None
        self._v:    Optional[np.ndarray] = None
        self._t_max_us:  float = 0.0
        self._freq_hz:   float = 0.0
        self._period_us: float = 0.0
        self._has_data: bool = False

        self.setMinimumSize(560, 140)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding,
        )

    # ---- публичный API ------------------------------------------------

    def show_dump(self, samples: np.ndarray, sample_hz: int) -> None:
        n = int(samples.shape[0]) if samples is not None else 0
        if n == 0 or sample_hz <= 0:
            self.clear()
            return
        t_us = np.arange(n, dtype=np.float64) * (1_000_000.0 / sample_hz)
        v    = samples.astype(np.float64) * (self.VREF_V / self.ADC_FULL)
        self._t_us = t_us
        self._v    = v
        self._t_max_us = float(t_us[-1]) if n > 1 else 1.0
        self._freq_hz, self._period_us = self._measure_freq(samples, sample_hz)
        self._has_data = True
        self.update()

    def clear(self) -> None:
        self._t_us = None
        self._v    = None
        self._t_max_us = 0.0
        self._freq_hz   = 0.0
        self._period_us = 0.0
        self._has_data = False
        self.update()

    @staticmethod
    def _measure_freq(samples: np.ndarray, sample_hz: int) -> tuple[float, float]:
        """Восходящие фронты по midpoint-порогу → средний период → freq.

        Возвращает (freq_hz, period_us). Нули — если амплитуда слишком мала
        (signal flat) или фронтов меньше двух."""
        n = int(samples.shape[0])
        if n < 4 or sample_hz <= 0:
            return 0.0, 0.0
        s_min = float(samples.min())
        s_max = float(samples.max())
        # Шум-флор: <5% от 12-бит → считаем сигнал плоским.
        if s_max - s_min < 200:
            return 0.0, 0.0
        mid = (s_min + s_max) * 0.5
        above = samples >= mid
        rising = np.where(np.diff(above.astype(np.int8)) > 0)[0]
        if rising.size < 2:
            return 0.0, 0.0
        period_samples = (rising[-1] - rising[0]) / (rising.size - 1)
        if period_samples <= 0:
            return 0.0, 0.0
        period_us = period_samples * 1_000_000.0 / sample_hz
        freq_hz   = sample_hz / period_samples
        return freq_hz, period_us

    def reset(self) -> None:
        self.clear()

    # ---- helpers ------------------------------------------------------

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

    def _nice_time_step(self, span_us: float) -> tuple[float, str]:
        """Подобрать «красивый» шаг сетки по X и unit ('µs' или 'ms')."""
        if span_us <= 0:
            return 1.0, "µs"
        target = span_us / 8.0
        unit = "µs"
        scale = 1.0
        if target >= 1000.0:
            unit = "ms"
            scale = 1000.0
            target = target / scale
        # «1-2-5» округление
        exp = math.floor(math.log10(target)) if target > 0 else 0
        base = 10 ** exp
        for m in (1, 2, 5, 10):
            if m * base >= target:
                step_unit = m * base
                return step_unit * scale, unit
        return 10 * base * scale, unit

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

        # ---- ось времени ----
        t_span = self._t_max_us if self._has_data and self._t_max_us > 0 else 1000.0
        t_step_us, t_unit = self._nice_time_step(t_span)
        t_scale = 1000.0 if t_unit == "ms" else 1.0

        def t_to_x(t_us: float) -> float:
            return plot.left() + (t_us / t_span) * plot.width()

        # вертикальная сетка по времени
        p.setPen(major_pen)
        t = 0.0
        while t <= t_span + 1e-6:
            x = t_to_x(t)
            if plot.left() - 0.5 <= x <= plot.right() + 0.5:
                p.drawLine(QPointF(x, plot.top()), QPointF(x, plot.bottom()))
            t += t_step_us

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

        # ---- подписи X (от 0) ----
        t = 0.0
        while t <= t_span + 1e-6:
            x = t_to_x(t)
            if plot.left() - 30 <= x <= plot.right() + 30:
                rect = QRectF(x - 30, plot.bottom() + 6, 60, 18)
                p.drawText(
                    rect,
                    Qt.AlignmentFlag.AlignCenter,
                    f"{t / t_scale:g}{t_unit}",
                )
            t += t_step_us

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
        if self._has_data and self._t_us is not None and self._v is not None \
                and self._t_us.shape[0] >= 2:
            path = QPainterPath()
            first = True
            for ts, rv in zip(self._t_us, self._v):
                x = t_to_x(float(ts))
                rv_clip = max(y_min, min(y_max, float(rv)))
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

        # ---- большой readout: измеренная частота ----
        has_freq = self._has_data and self._freq_hz > 0
        f_big = QFont("Consolas"); f_big.setPointSize(28); f_big.setBold(True)
        f_big.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 3)
        p.setFont(f_big)
        p.setPen(QPen(QColor(COL_DIGITAL if has_freq else COL_DIGITAL_DIM)))
        readout_w = 260
        rect = QRectF(plot.right() - readout_w - 14, plot.top() + 10, readout_w, 50)
        readout_text = f"{self._freq_hz:,.0f} Hz" if has_freq else "— — —"
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
        if has_freq:
            unit_text = (f"T = {self._period_us:.1f} µs"
                         if self._period_us < 1000.0
                         else f"T = {self._period_us / 1000.0:.2f} ms")
        else:
            unit_text = "STEP FREQ"
        p.drawText(
            rect2,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
            unit_text,
        )
