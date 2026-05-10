"""Кастомные стилизованные виджеты — индустриальный CNC-look.

Каждый виджет рисует свой фон/рамку через canvas.before, а дефолтные
текстуры Kivy отключены (background_normal=''). Это даёт тонкий контроль
над цветом в hover/pressed/disabled и убирает Material-style градиенты.

Эквивалентны QSS-хелперам из PySide6 theme.py:
  industrial_button_qss → IndustrialButton (+ ToggleIndustrialButton)
  combobox_qss          → IndustrialSpinner
  lineedit_qss          → IndustrialTextInput
  textedit_qss          → IndustrialTextArea
  spinbox_qss           → IndustrialSpinBox  (Stage 2)
  slider_qss            → IndustrialSlider   (Stage 2)
"""

from __future__ import annotations

from kivy.clock import Clock
from kivy.graphics import Color, Ellipse, Line, RoundedRectangle
from kivy.properties import BooleanProperty
from kivy.uix.behaviors import ToggleButtonBehavior
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

from .theme import (
    BTN_RADIUS, INPUT_RADIUS,
    RGBA_BG_INSET, RGBA_BORDER_DIS, RGBA_BTN_BG, RGBA_BTN_BG_DIS,
    RGBA_DIGITAL, RGBA_DIGITAL_DIM, RGBA_INPUT_BG,
    RGBA_PANEL_EDGE, RGBA_TEXT, RGBA_TEXT_DIM,
)


# ---------------------------------------------------------------------------
#  Кнопка
# ---------------------------------------------------------------------------

class IndustrialButton(Button):
    """Прямоугольная индустриальная кнопка с состояниями idle/hover/pressed/disabled.

    `hover` в Kivy не идёт штатно — определяем через mouse_pos на главном
    окне (опционально, если мышь есть). Для тач-устройств hover не нужен.
    """

    hovered = BooleanProperty(False)

    def __init__(self, **kwargs) -> None:
        # Отключаем дефолтные текстуры — рисуем сами.
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down",   "")
        kwargs.setdefault("background_disabled_normal", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))   # прозрачный tint
        kwargs.setdefault("color",  RGBA_TEXT)
        kwargs.setdefault("bold",   True)
        kwargs.setdefault("font_size", "13sp")
        super().__init__(**kwargs)

        self._radius = BTN_RADIUS

        with self.canvas.before:
            self._bg_color   = Color(*RGBA_BTN_BG)
            self._bg_rect    = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[self._radius],
            )
            self._edge_color = Color(*RGBA_PANEL_EDGE)
            self._edge_line  = Line(
                rounded_rectangle=(*self.pos, *self.size, self._radius),
                width=1.0,
            )

        self.bind(pos=self._update_canvas, size=self._update_canvas,
                  state=self._update_state, disabled=self._update_state,
                  hovered=self._update_state)

        # Подписка на mouse-pos главного окна (для hover-эффекта на десктопе)
        from kivy.core.window import Window
        Window.bind(mouse_pos=self._on_mouse_pos)

    # ---- canvas update ------------------------------------------------

    def _update_canvas(self, *_a) -> None:
        self._bg_rect.pos  = self.pos
        self._bg_rect.size = self.size
        self._edge_line.rounded_rectangle = (*self.pos, *self.size, self._radius)

    def _update_state(self, *_a) -> None:
        if self.disabled:
            self._bg_color.rgba   = RGBA_BTN_BG_DIS
            self._edge_color.rgba = RGBA_BORDER_DIS
            self.color            = (0.29, 0.33, 0.36, 1.0)   # #4a545d
            return
        if self.state == "down":
            self._bg_color.rgba   = RGBA_DIGITAL_DIM
            self._edge_color.rgba = RGBA_DIGITAL
            self.color            = RGBA_DIGITAL
            return
        if self.hovered:
            self._bg_color.rgba   = RGBA_BTN_BG
            self._edge_color.rgba = RGBA_DIGITAL
            self.color            = RGBA_DIGITAL
            return
        self._bg_color.rgba   = RGBA_BTN_BG
        self._edge_color.rgba = RGBA_PANEL_EDGE
        self.color            = RGBA_TEXT

    def _on_mouse_pos(self, _win, pos) -> None:
        # parent может быть не прорисован → collide_point может упасть.
        if not self.get_root_window():
            return
        x, y = self.to_widget(*pos)
        self.hovered = self.collide_point(x, y)


class ToggleIndustrialButton(ToggleButtonBehavior, IndustrialButton):
    """Та же кнопка, но `state='down'` залипает (как QPushButton.checkable)."""

    def _update_state(self, *_a) -> None:
        # `state == 'down'` означает либо сейчас нажата, либо checked.
        # Для toggle-кнопки оба случая хотим показать как checked-style.
        super()._update_state()


# ---------------------------------------------------------------------------
#  Spinner (combo-list)
# ---------------------------------------------------------------------------

class IndustrialSpinner(Spinner):
    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down",   "")
        kwargs.setdefault("background_color",  (0, 0, 0, 0))
        kwargs.setdefault("color",  RGBA_TEXT)
        kwargs.setdefault("font_size", "13sp")
        super().__init__(**kwargs)

        self._radius = INPUT_RADIUS

        with self.canvas.before:
            self._bg_color   = Color(*RGBA_INPUT_BG)
            self._bg_rect    = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[self._radius],
            )
            self._edge_color = Color(*RGBA_PANEL_EDGE)
            self._edge_line  = Line(
                rounded_rectangle=(*self.pos, *self.size, self._radius),
                width=1.0,
            )

        self.bind(pos=self._update_canvas, size=self._update_canvas,
                  disabled=self._update_state, is_open=self._update_state)

    def _update_canvas(self, *_a) -> None:
        self._bg_rect.pos  = self.pos
        self._bg_rect.size = self.size
        self._edge_line.rounded_rectangle = (*self.pos, *self.size, self._radius)

    def _update_state(self, *_a) -> None:
        if self.disabled:
            self._bg_color.rgba   = RGBA_INPUT_BG
            self._edge_color.rgba = RGBA_BORDER_DIS
            self.color            = RGBA_TEXT_DIM
            return
        if self.is_open:
            self._edge_color.rgba = RGBA_DIGITAL
        else:
            self._edge_color.rgba = RGBA_PANEL_EDGE
        self.color = RGBA_TEXT


# ---------------------------------------------------------------------------
#  TextInput
# ---------------------------------------------------------------------------

class IndustrialTextInput(TextInput):
    """Однострочный input команды. multiline=False по умолчанию."""

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("multiline", False)
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_active", "")
        kwargs.setdefault("background_color",  (0, 0, 0, 0))
        kwargs.setdefault("foreground_color",  RGBA_TEXT)
        kwargs.setdefault("cursor_color",      RGBA_DIGITAL)
        kwargs.setdefault("selection_color",   (*RGBA_DIGITAL_DIM[:3], 0.8))
        kwargs.setdefault("hint_text_color",   RGBA_TEXT_DIM)
        kwargs.setdefault("font_size", "14sp")
        kwargs.setdefault("padding", (10, 8, 10, 8))
        super().__init__(**kwargs)

        self._radius = INPUT_RADIUS

        with self.canvas.before:
            self._bg_color   = Color(*RGBA_INPUT_BG)
            self._bg_rect    = RoundedRectangle(
                pos=self.pos, size=self.size, radius=[self._radius],
            )
            self._edge_color = Color(*RGBA_PANEL_EDGE)
            self._edge_line  = Line(
                rounded_rectangle=(*self.pos, *self.size, self._radius),
                width=1.0,
            )

        self.bind(pos=self._update_canvas, size=self._update_canvas,
                  focus=self._update_state, disabled=self._update_state)

    def _update_canvas(self, *_a) -> None:
        self._bg_rect.pos  = self.pos
        self._bg_rect.size = self.size
        self._edge_line.rounded_rectangle = (*self.pos, *self.size, self._radius)

    def _update_state(self, *_a) -> None:
        if self.disabled:
            self._edge_color.rgba = RGBA_BORDER_DIS
            self.foreground_color = RGBA_TEXT_DIM
            return
        self.foreground_color = RGBA_TEXT
        self._edge_color.rgba = RGBA_DIGITAL if self.focus else RGBA_PANEL_EDGE


class IndustrialTextArea(IndustrialTextInput):
    """Многострочный read-only терминал-вид (тёмный фон, моноширинный)."""

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("multiline", True)
        kwargs.setdefault("readonly",  True)
        kwargs.setdefault("font_name", "RobotoMono-Regular")
        kwargs.setdefault("font_size", "13sp")
        super().__init__(**kwargs)
        # Чуть глубже, чем обычный input — соответствует BG_INSET в QSS.
        self._bg_color.rgba = RGBA_BG_INSET


# ---------------------------------------------------------------------------
#  SpinBox (число с +/-)
# ---------------------------------------------------------------------------

class IndustrialSpinBox(BoxLayout):
    """Числовой ввод: TextInput + кнопки `−` / `+`.

    API похож на QSpinBox: `value` (int property), `set_value`, `value_min/max`,
    `suffix` (например, " Hz"). Подсветка значения — COL_DIGITAL.
    """

    def __init__(
        self,
        value: int = 0, value_min: int = -1_000_000, value_max: int = 1_000_000,
        step: int = 1, suffix: str = "",
        **kwargs,
    ) -> None:
        kwargs.setdefault("orientation", "horizontal")
        kwargs.setdefault("spacing", 0)
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", "32dp")
        super().__init__(**kwargs)

        self.value_min = int(value_min)
        self.value_max = int(value_max)
        self.step      = int(step)
        self.suffix    = suffix
        self._value    = int(value)

        # ---- text input ----
        self._ti = IndustrialTextInput(
            multiline=False, halign="right",
            size_hint_x=1,
            font_name="RobotoMono-Regular", font_size="14sp",
            foreground_color=RGBA_DIGITAL,
            input_filter=lambda s, fr: s if (s in "+-" or s.isdigit()) else "",
        )
        self._ti.bind(focus=self._on_focus)
        self._ti.bind(on_text_validate=lambda *_: self._commit_text())

        # ---- кнопки -/+ ----
        self.btn_dn = IndustrialButton(
            text="−", size_hint_x=None, width="32dp",
            font_size="18sp",
        )
        self.btn_up = IndustrialButton(
            text="+", size_hint_x=None, width="32dp",
            font_size="18sp",
        )
        self.btn_dn.bind(on_release=lambda _b: self.set_value(self._value - self.step))
        self.btn_up.bind(on_release=lambda _b: self.set_value(self._value + self.step))

        self.add_widget(self._ti)
        self.add_widget(self.btn_dn)
        self.add_widget(self.btn_up)

        self._refresh_text()

    # ---- API ----------------------------------------------------------

    @property
    def value(self) -> int:
        return self._value

    def set_value(self, v: int) -> None:
        v = max(self.value_min, min(self.value_max, int(v)))
        if v != self._value:
            self._value = v
        self._refresh_text()

    # ---- internals ----------------------------------------------------

    def _refresh_text(self) -> None:
        text = f"{self._value}{self.suffix}"
        if not self._ti.focus:
            self._ti.text = text

    def _commit_text(self) -> None:
        raw = self._ti.text.strip()
        if self.suffix and raw.endswith(self.suffix):
            raw = raw[: -len(self.suffix)].strip()
        try:
            self.set_value(int(raw))
        except ValueError:
            self._refresh_text()

    def _on_focus(self, _ti, focused: bool) -> None:
        if focused:
            # На фокусе показываем без суффикса — чтобы редактировать число.
            self._ti.text = str(self._value)
        else:
            self._commit_text()


# ---------------------------------------------------------------------------
#  Slider
# ---------------------------------------------------------------------------

class IndustrialSlider(Slider):
    """Горизонтальный слайдер с грубом-pill, sub-page DIGITAL_DIM и круглым
    handle цвета DIGITAL.

    Дефолтные текстуры Kivy скрыты (`background_horizontal=''`,
    `cursor_image=''` не работают — пути обязательны), поэтому мы их не
    трогаем, а рисуем поверх через `canvas.after`. Это надёжный способ.
    """

    GROOVE_HEIGHT = 6
    HANDLE_RADIUS = 8

    def __init__(self, **kwargs) -> None:
        kwargs.setdefault("orientation", "horizontal")
        # Скрыть дефолтный value_track Kivy: рисуем сами.
        kwargs.setdefault("value_track", False)
        super().__init__(**kwargs)

        # Поверх дефолтного фона/курсора. canvas.after — чтобы перекрыть
        # стоковый PNG-курсор.
        with self.canvas.after:
            self._groove_bg_color   = Color(*RGBA_INPUT_BG)
            self._groove_bg         = RoundedRectangle(
                pos=(0, 0), size=(0, 0), radius=[self.GROOVE_HEIGHT / 2],
            )
            self._groove_edge_color = Color(*RGBA_PANEL_EDGE)
            self._groove_edge       = Line(
                rounded_rectangle=(0, 0, 0, 0, self.GROOVE_HEIGHT / 2),
                width=1.0,
            )
            self._sub_color         = Color(*RGBA_DIGITAL_DIM)
            self._sub_rect          = RoundedRectangle(
                pos=(0, 0), size=(0, 0), radius=[self.GROOVE_HEIGHT / 2],
            )
            self._handle_glow_color = Color(*RGBA_DIGITAL, 0.0)   # alpha из update
            self._handle_glow       = Ellipse(pos=(0, 0), size=(0, 0))
            self._handle_color      = Color(*RGBA_DIGITAL)
            self._handle            = Ellipse(pos=(0, 0), size=(0, 0))

        self.bind(
            pos=self._update_canvas, size=self._update_canvas,
            value=self._update_canvas, value_pos=self._update_canvas,
            disabled=self._update_canvas,
        )
        Clock.schedule_once(lambda *_: self._update_canvas(), 0)

    def _update_canvas(self, *_a) -> None:
        # Желоб шириной = self.width - 2*HANDLE_RADIUS, по центру по вертикали.
        gh = self.GROOVE_HEIGHT
        hr = self.HANDLE_RADIUS
        gx = self.x + hr
        gw = max(1, self.width - 2 * hr)
        gy = self.center_y - gh / 2

        self._groove_bg.pos          = (gx, gy)
        self._groove_bg.size         = (gw, gh)
        self._groove_edge.rounded_rectangle = (gx, gy, gw, gh, gh / 2)

        # Sub-page (от left до handle).
        try:
            v_norm = (self.value - self.min) / max(1e-9, (self.max - self.min))
        except ZeroDivisionError:
            v_norm = 0.0
        v_norm = max(0.0, min(1.0, v_norm))
        sub_w = gw * v_norm
        self._sub_rect.pos  = (gx, gy)
        self._sub_rect.size = (sub_w, gh)

        # Handle: круг по центру по вертикали, x = gx + sub_w.
        hx = gx + sub_w - hr
        hy = self.center_y - hr
        self._handle.pos  = (hx, hy)
        self._handle.size = (hr * 2, hr * 2)

        # Halo вокруг handle.
        halo_r = hr * 1.8
        self._handle_glow.pos  = (hx + hr - halo_r, hy + hr - halo_r)
        self._handle_glow.size = (halo_r * 2, halo_r * 2)

        if self.disabled:
            self._handle_color.rgba      = (*RGBA_PANEL_EDGE[:3], 1.0)
            self._sub_color.rgba         = (0, 0, 0, 0)
            self._handle_glow_color.rgba = (0, 0, 0, 0)
        else:
            self._handle_color.rgba      = RGBA_DIGITAL
            self._sub_color.rgba         = RGBA_DIGITAL_DIM
            self._handle_glow_color.rgba = (*RGBA_DIGITAL[:3], 0.18)
