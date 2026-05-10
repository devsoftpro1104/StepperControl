"""Анимированный круглый ротор: «торец двигателя» с риской.

Угол риски жёстко привязан к фактической позиции мотора в шагах:
один полный оборот = STEPS_PER_REV шагов. Между приходящими $M-сэмплами
(10 Hz) экстраполируем позицию по freq, чтобы анимация была плавной —
но как только пришёл новый сэмпл, угол ре-якорится по нему.

Эквивалент `views/rotor_view.py` PySide6-версии. Реализация:
  - canvas.before — статика (кольцо, винтики, шкала, диск, ступица).
                    Перерисовывается только при resize.
  - canvas — рисуется ОДИН РАЗ при resize (риска и ступица), а каждый
             кадр обновляется только `Rotate.angle`. Не делаем
             clear+rebuild каждый тик: на части GL-драйверов это даёт
             артефакты ("окружности друг на друге") и зависание матрицы.
"""

from __future__ import annotations

import math
import time

from kivy.clock import Clock
from kivy.graphics import (
    Color, Ellipse, Line, PopMatrix, PushMatrix, Rotate, RoundedRectangle,
)
from kivy.uix.label import Label
from kivy.uix.widget import Widget

from .theme import (
    COL_TEXT_DIM, RGBA_BG_OUT, RGBA_DIGITAL, RGBA_DIGITAL_DIM,
    hex_to_rgba,
)


STEPS_PER_REV = 3200     # NEMA-23 c микрошагом 1/16 (200 × 16 = 3200)


class RotorView(Widget):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.size_hint = (1, 1)

        # Состояние мотора.
        self._anchor_pos:  float = 0.0
        self._anchor_time: float = time.monotonic()
        self._freq_hz:     float = 0.0
        self._dir_sign:    int   = 0
        self._running:     bool  = False

        # Tick-метки 0/90/180/270.
        self._tick_labels = {
            "0":   self._make_tick_label("0"),
            "90":  self._make_tick_label("90"),
            "180": self._make_tick_label("180"),
            "270": self._make_tick_label("270"),
        }
        for lbl in self._tick_labels.values():
            self.add_widget(lbl)

        # Долгоживущие graphics-инструкции (создаются один раз; меняем
        # только параметры). Будут заполнены в _rebuild() при первом
        # resize.
        self._rotate: Rotate | None = None

        self.bind(pos=self._rebuild, size=self._rebuild)

        # 60 fps — обновляем ТОЛЬКО угол риски. Остальное стабильно.
        Clock.schedule_interval(lambda _dt: self._update_mark_angle(), 1.0 / 60.0)

    # ---- публичный API ------------------------------------------------

    def reset(self) -> None:
        self._anchor_pos  = 0.0
        self._anchor_time = time.monotonic()
        self._freq_hz     = 0.0
        self._dir_sign    = 0
        self._running     = False

    def set_state(self, pos: int, speed_sps: int) -> None:
        """Якорь: реальная позиция в шагах + скорость (signed)."""
        self._anchor_pos  = float(pos)
        self._anchor_time = time.monotonic()
        self._freq_hz     = float(abs(speed_sps))
        self._dir_sign    = 1 if speed_sps > 0 else (-1 if speed_sps < 0 else 0)
        self._running     = self._freq_hz > 0 and self._dir_sign != 0

    # ---- helpers ------------------------------------------------------

    def _current_pos(self) -> float:
        if not self._running:
            return self._anchor_pos
        dt = time.monotonic() - self._anchor_time
        return self._anchor_pos + self._dir_sign * self._freq_hz * dt

    def _angle_deg(self) -> float:
        return (self._current_pos() / STEPS_PER_REV * 360.0) % 360.0

    def _make_tick_label(self, text: str) -> Label:
        return Label(
            text=text,
            font_name="RobotoMono-Regular",
            font_size="11sp",
            bold=True,
            color=hex_to_rgba(COL_TEXT_DIM),
            size_hint=(None, None),
            size=(36, 20),
            halign="center", valign="middle",
        )

    # ---- полная сборка canvas (resize) -------------------------------

    def _rebuild(self, *_a) -> None:
        # Сбрасываем оба слоя — собираем заново под актуальные cx/cy.
        self.canvas.before.clear()
        self.canvas.clear()

        if self.width <= 4 or self.height <= 4:
            return

        side    = min(self.width, self.height)
        cx      = self.x + self.width  / 2
        cy      = self.y + self.height / 2
        r_outer = side / 2 - 8
        r_body  = r_outer * 0.92
        r_disk  = r_outer * 0.78
        r_hub   = r_outer * 0.18

        # =============================================================
        #  Статика (canvas.before)
        # =============================================================
        with self.canvas.before:
            # Кольцо (плоский серый).
            Color(0.21, 0.24, 0.27, 1)
            Ellipse(
                pos=(cx - r_outer, cy - r_outer),
                size=(r_outer * 2, r_outer * 2),
            )
            # Тёмная «впадина» — отделяет кольцо от диска.
            Color(*RGBA_BG_OUT)
            Ellipse(
                pos=(cx - r_body, cy - r_body),
                size=(r_body * 2, r_body * 2),
            )
            # Внешняя кромка.
            Color(0.04, 0.05, 0.063, 1)
            Line(circle=(cx, cy, r_outer), width=1.6)

            # Винтики на 4 углах.
            for ang_deg in (45, 135, 225, 315):
                a = math.radians(ang_deg)
                sx = cx + math.cos(a) * (r_outer - 12)
                sy = cy + math.sin(a) * (r_outer - 12)
                Color(0.55, 0.59, 0.63, 1)
                Ellipse(pos=(sx - 5.5, sy - 5.5), size=(11, 11))
                Color(0.04, 0.05, 0.063, 1)
                Line(points=[sx - 4, sy, sx + 4, sy], width=1.4)

            # Шкала 36 делений (Kivy Y вверх → 90 - ang).
            for i in range(36):
                ang = i * 10
                major = (i % 9 == 0)
                length = 10 if major else 5
                a = math.radians(90 - ang)
                x1 = cx + math.cos(a) * r_body
                y1 = cy + math.sin(a) * r_body
                x2 = cx + math.cos(a) * (r_body - length)
                y2 = cy + math.sin(a) * (r_body - length)
                if major:
                    Color(*RGBA_DIGITAL)
                    Line(points=[x1, y1, x2, y2], width=1.6)
                else:
                    Color(0.235, 0.278, 0.314, 1)
                    Line(points=[x1, y1, x2, y2], width=1.0)

            # Сам диск.
            Color(0.087, 0.106, 0.125, 1)
            Ellipse(
                pos=(cx - r_disk, cy - r_disk),
                size=(r_disk * 2, r_disk * 2),
            )
            Color(0.04, 0.05, 0.063, 1)
            Line(circle=(cx, cy, r_disk), width=1.5)

        # Подвинуть метки 0/90/180/270.
        for tick_text, ang_deg in (
            ("0", 0), ("90", 90), ("180", 180), ("270", 270),
        ):
            a = math.radians(90 - ang_deg)
            tx = cx + math.cos(a) * (r_outer - 22)
            ty = cy + math.sin(a) * (r_outer - 22)
            lbl = self._tick_labels[tick_text]
            lbl.pos = (tx - lbl.width / 2, ty - lbl.height / 2)

        # =============================================================
        #  Риска и ступица (canvas, с долгоживущим Rotate)
        # =============================================================
        mark_len   = r_disk * 0.78
        mark_inner = r_disk * 0.22
        mark_w     = max(6.0, side * 0.022)

        with self.canvas:
            PushMatrix()
            # СОХРАНЯЕМ ССЫЛКУ — тик-функция меняет только .angle.
            self._rotate = Rotate(angle=0, axis=(0, 0, 1), origin=(cx, cy))

            # 3-слойная фосфорная риска (glow halo + outer + core).
            for w_extra, alpha in ((8.0, 0.18), (3.0, 0.45), (0.0, 1.0)):
                gw = mark_w + w_extra
                Color(*RGBA_DIGITAL[:3], alpha)
                RoundedRectangle(
                    pos=(cx - gw / 2, cy + mark_inner),
                    size=(gw, mark_len - mark_inner),
                    radius=[gw / 2],
                )
            # Тёмная подложка у основания.
            Color(*RGBA_DIGITAL_DIM[:3], 0.6)
            RoundedRectangle(
                pos=(cx - mark_w / 2, cy + mark_inner),
                size=(mark_w, (mark_len - mark_inner) * 0.45),
                radius=[mark_w / 2],
            )
            PopMatrix()

            # Ступица — ПОВЕРХ основания риски, без поворота.
            Color(0.110, 0.140, 0.169, 1)
            Ellipse(pos=(cx - r_hub, cy - r_hub), size=(r_hub * 2, r_hub * 2))
            Color(0.04, 0.05, 0.063, 1)
            Line(circle=(cx, cy, r_hub), width=1.5)
            # Центральный болтик.
            r_bolt = r_hub * 0.35
            Color(0.180, 0.211, 0.243, 1)
            Ellipse(pos=(cx - r_bolt, cy - r_bolt), size=(r_bolt * 2, r_bolt * 2))

        # Сразу применить актуальный угол.
        self._update_mark_angle()

    # ---- 60 fps tick: обновляем только угол --------------------------

    def _update_mark_angle(self) -> None:
        if self._rotate is None:
            return
        # Знак инвертирован: положительный pos → FRW → визуально поворот
        # по часовой стрелке. У Kivy положительный Rotate — против часовой.
        self._rotate.angle = -self._angle_deg()
