"""Анимированный круглый ротор: «торец двигателя» с риской.

Принимает (freq_hz, dir_sign) — крутится непрерывно с угловой скоростью
freq * 360°/STEPS_PER_REV. Все детали (алюминиевый корпус, винтики, шкала
градусов, светящаяся риска, conical-tail след) рисуются в paintEvent.
"""

from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QBrush, QColor, QConicalGradient, QFont, QLinearGradient, QPainter,
    QPainterPath, QPen, QRadialGradient,
)
from PySide6.QtWidgets import QSizePolicy, QWidget

from .theme import COL_DIGITAL, COL_DIGITAL_DIM, COL_TEXT_DIM


STEPS_PER_REV = 200      # NEMA-23 без микрошага; для визуала достаточно


class RotorView(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(280, 280)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._angle:    float = 0.0
        self._freq_hz:  float = 0.0
        self._dir_sign: int   = 0
        self._running:  bool  = False

        # 60 fps ровный таймер.
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)
        self._timer.start()

    # ---- публичный API ------------------------------------------------

    def reset(self) -> None:
        self._angle    = 0.0
        self._freq_hz  = 0.0
        self._dir_sign = 0
        self._running  = False
        self.update()

    def set_freq_dir(self, freq_hz: float, dir_sign: int) -> None:
        """freq_hz — модуль; dir_sign — −1 / 0 / +1."""
        self._freq_hz  = float(abs(freq_hz))
        self._dir_sign = 1 if dir_sign > 0 else (-1 if dir_sign < 0 else 0)
        self._running  = (self._freq_hz > 0 and self._dir_sign != 0)

    # ---- интерполяция -------------------------------------------------

    def _tick(self) -> None:
        if not self._running:
            return
        # Угловая скорость = freq * 360°/STEPS_PER_REV; dt — период таймера.
        dt  = self._timer.interval() / 1000.0
        deg = self._freq_hz * self._dir_sign * 360.0 / STEPS_PER_REV * dt
        self._angle = (self._angle + deg) % 360.0
        self.update()

    # ---- рисование ----------------------------------------------------

    def paintEvent(self, _event) -> None:
        side = min(self.width(), self.height())
        cx, cy = self.width() / 2, self.height() / 2
        r_outer = side / 2 - 8
        r_body  = r_outer * 0.92
        r_disk  = r_outer * 0.78
        r_hub   = r_outer * 0.18

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # ------- внешнее «алюминиевое» кольцо -------
        body_grad = QRadialGradient(cx - side * 0.18, cy - side * 0.22, side)
        body_grad.setColorAt(0.0, QColor("#5a6670"))
        body_grad.setColorAt(0.5, QColor("#2c3238"))
        body_grad.setColorAt(1.0, QColor("#0e1216"))
        p.setBrush(QBrush(body_grad))
        p.setPen(QPen(QColor("#0a0d10"), 2))
        p.drawEllipse(QPointF(cx, cy), r_outer, r_outer)

        # винтики по углам
        for ang_deg in (45, 135, 225, 315):
            a = math.radians(ang_deg)
            sx = cx + math.cos(a) * (r_outer - 10)
            sy = cy + math.sin(a) * (r_outer - 10)
            sg = QRadialGradient(sx - 1, sy - 1, 6)
            sg.setColorAt(0, QColor("#a3afb9"))
            sg.setColorAt(1, QColor("#222a31"))
            p.setBrush(QBrush(sg))
            p.setPen(QPen(QColor("#0a0d10"), 1))
            p.drawEllipse(QPointF(sx, sy), 4.5, 4.5)
            p.setPen(QPen(QColor("#0a0d10"), 1.2))
            p.drawLine(QPointF(sx - 3, sy), QPointF(sx + 3, sy))

        # ------- шкала градусов под диском -------
        p.save()
        p.translate(cx, cy)
        for i in range(36):
            ang = i * 10
            p.save()
            p.rotate(ang - 90)
            major = (i % 9 == 0)
            length = 10 if major else 5
            p.setPen(QPen(
                QColor("#3c4750") if not major else QColor(COL_DIGITAL),
                1.5 if major else 1,
            ))
            p.drawLine(QPointF(0, -r_body), QPointF(0, -r_body + length))
            p.restore()
        p.restore()

        # ------- сам диск -------
        disk_grad = QRadialGradient(cx - r_disk * 0.3, cy - r_disk * 0.3, r_disk * 1.6)
        disk_grad.setColorAt(0.0, QColor("#262e36"))
        disk_grad.setColorAt(0.7, QColor("#161b20"))
        disk_grad.setColorAt(1.0, QColor("#080a0c"))
        p.setBrush(QBrush(disk_grad))
        p.setPen(QPen(QColor("#0a0d10"), 1.5))
        p.drawEllipse(QPointF(cx, cy), r_disk, r_disk)

        # ------- conical-«след» при вращении -------
        if self._running and self._dir_sign != 0:
            cg = QConicalGradient(cx, cy, -90 - self._angle)
            tail_col    = QColor(COL_DIGITAL); tail_col.setAlpha(110)
            transparent = QColor(COL_DIGITAL); transparent.setAlpha(0)
            if self._dir_sign > 0:
                cg.setColorAt(0.00, tail_col)
                cg.setColorAt(0.35, transparent)
                cg.setColorAt(1.00, transparent)
            else:
                cg.setColorAt(0.00, tail_col)
                cg.setColorAt(0.65, transparent)
                cg.setColorAt(1.00, tail_col)
            p.setBrush(QBrush(cg))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawEllipse(QPointF(cx, cy), r_disk - 2, r_disk - 2)
            # вырез в центре, чтобы след был кольцом
            p.setBrush(QBrush(disk_grad))
            p.drawEllipse(QPointF(cx, cy), r_disk * 0.55, r_disk * 0.55)

        # ------- индикаторная риска -------
        p.save()
        p.translate(cx, cy)
        p.rotate(self._angle - 90)              # 0° => вверх; +угол => CW
        mark_len   = r_disk * 0.78
        mark_inner = r_disk * 0.22
        mark_w     = max(6, int(side * 0.022))

        glow = QLinearGradient(0, -mark_len, 0, -mark_inner)
        glow.setColorAt(0.0, QColor(COL_DIGITAL))
        glow.setColorAt(1.0, QColor(COL_DIGITAL_DIM))
        path = QPainterPath()
        path.addRoundedRect(
            QRectF(-mark_w / 2, -mark_len, mark_w, mark_len - mark_inner),
            mark_w / 2, mark_w / 2,
        )
        p.setBrush(QBrush(glow))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawPath(path)

        glow2 = QColor(COL_DIGITAL); glow2.setAlpha(120)
        p.setPen(QPen(glow2, 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawPath(path)
        p.restore()

        # ------- ступица -------
        hub_grad = QRadialGradient(cx - r_hub * 0.4, cy - r_hub * 0.4, r_hub * 1.5)
        hub_grad.setColorAt(0.0, QColor("#4a5560"))
        hub_grad.setColorAt(0.6, QColor("#1c2329"))
        hub_grad.setColorAt(1.0, QColor("#0a0d10"))
        p.setBrush(QBrush(hub_grad))
        p.setPen(QPen(QColor("#0a0d10"), 1.5))
        p.drawEllipse(QPointF(cx, cy), r_hub, r_hub)
        p.setBrush(QBrush(QColor("#1a2128")))
        p.setPen(QPen(QColor("#0a0d10"), 1))
        p.drawEllipse(QPointF(cx, cy), r_hub * 0.35, r_hub * 0.35)

        # ------- надписи 0/90/180/270 -------
        f = QFont("Consolas")
        f.setBold(True)
        f.setPointSizeF(max(8.0, side * 0.035))
        p.setFont(f)
        p.setPen(QPen(QColor(COL_TEXT_DIM)))
        for ang_deg, txt in ((-90, "0"), (0, "90"), (90, "180"), (180, "270")):
            a = math.radians(ang_deg)
            tx = cx + math.cos(a) * (r_outer - 22)
            ty = cy + math.sin(a) * (r_outer - 22)
            rect = QRectF(tx - 18, ty - 10, 36, 20)
            p.drawText(rect, Qt.AlignmentFlag.AlignCenter, txt)
