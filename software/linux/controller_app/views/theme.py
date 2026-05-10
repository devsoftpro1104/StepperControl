"""Палитра и helpers для CNC-стилистики (Kivy).

Один первоисточник для цветов. Все view-файлы импортируют только отсюда.
Цвета — копия PySide6-варианта из software/controller_app/views/theme.py.

Каждый цвет доступен в двух формах:
  - hex-строка (для Label markup: '[color=#xxxxxx]…[/color]')
  - RGBA-кортеж (для kivy.graphics: Color(*RGBA_XXX))
"""

from __future__ import annotations


# ---- палитра (hex) -------------------------------------------------------

COL_BG_OUT      = "#0a0d10"     # внешний фон окна
COL_BG_IN       = "#13181d"     # фон Panel-а
COL_BG_INSET    = "#050708"     # глубокий чёрный для readout/console/plot
COL_PANEL_EDGE  = "#2a3138"     # рамка панелей
COL_TEXT        = "#cfd6dd"
COL_TEXT_DIM    = "#6f7a82"
COL_LABEL       = "#8d9aa3"
COL_DIGITAL     = "#6dcfe6"     # светлый голубой — основной акцент
COL_DIGITAL_DIM = "#0f3a4a"     # согласованный тёмный (фон под digital)
COL_GRN         = "#1ee05a"
COL_GRN_DARK    = "#053b15"
COL_RED         = "#ff2c2c"
COL_RED_DARK    = "#480000"
COL_AMBER       = "#ffae00"
COL_AMBER_DARK  = "#3d2700"
COL_LED_OFF     = "#1a1f23"

# Дополнительные служебные цвета (используются только в этом файле и в
# styled-виджетах: фон кнопки в idle, фон поля ввода и т.п.).
COL_BTN_BG      = "#1a2027"
COL_BTN_BG_DIS  = "#0e1216"
COL_INPUT_BG    = "#0c1014"
COL_BORDER_DIS  = "#1a1f23"
COL_TAB_BG      = "#11171c"


# ---- маппинг severity -> hex для Label markup --------------------------

SEVERITY_COLOR = {
    "ok":     COL_GRN,
    "err":    COL_RED,
    "event":  COL_AMBER,
    "stream": COL_DIGITAL,
    "cmt":    COL_TEXT_DIM,
    "raw":    COL_TEXT,
    "tx":     "#ffffff",
}


# ---- hex -> rgba конвертер -----------------------------------------------

def hex_to_rgba(h: str, a: float = 1.0) -> tuple[float, float, float, float]:
    h = h.lstrip("#")
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return (r, g, b, a)


# ---- готовые RGBA-константы для kivy.graphics ----------------------------

RGBA_BG_OUT      = hex_to_rgba(COL_BG_OUT)
RGBA_BG_IN       = hex_to_rgba(COL_BG_IN)
RGBA_BG_INSET    = hex_to_rgba(COL_BG_INSET)
RGBA_PANEL_EDGE  = hex_to_rgba(COL_PANEL_EDGE)
RGBA_TEXT        = hex_to_rgba(COL_TEXT)
RGBA_TEXT_DIM    = hex_to_rgba(COL_TEXT_DIM)
RGBA_LABEL       = hex_to_rgba(COL_LABEL)
RGBA_DIGITAL     = hex_to_rgba(COL_DIGITAL)
RGBA_DIGITAL_DIM = hex_to_rgba(COL_DIGITAL_DIM)
RGBA_GRN         = hex_to_rgba(COL_GRN)
RGBA_RED         = hex_to_rgba(COL_RED)
RGBA_AMBER       = hex_to_rgba(COL_AMBER)
RGBA_LED_OFF     = hex_to_rgba(COL_LED_OFF)
RGBA_BTN_BG      = hex_to_rgba(COL_BTN_BG)
RGBA_BTN_BG_DIS  = hex_to_rgba(COL_BTN_BG_DIS)
RGBA_INPUT_BG    = hex_to_rgba(COL_INPUT_BG)
RGBA_BORDER_DIS  = hex_to_rgba(COL_BORDER_DIS)
RGBA_TAB_BG      = hex_to_rgba(COL_TAB_BG)


# ---- константы шрифтов и метрик ------------------------------------------

FONT_MONO       = "RobotoMono-Regular"   # моноширинный (входит в Kivy)
FONT_REGULAR    = "Roboto"               # дефолтный
FONT_BOLD       = "Roboto-Bold"

PANEL_RADIUS    = 8                      # px, радиус скругления Panel-а
BTN_RADIUS      = 4
INPUT_RADIUS    = 4
