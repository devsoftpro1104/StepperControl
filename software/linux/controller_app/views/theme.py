"""Цветовая палитра и helpers для Kivy-виджетов.

Цвета — копия PySide6-варианта (industrial / "панель ЧПУ"). Все значения
в RGBA float (Kivy native), плюс hex-строки для разметки Label.
"""

from __future__ import annotations


# ---- hex-строки (для Label markup, '[color=#xxxxxx]…[/color]') -----------

COL_BG       = "#1a1d20"     # фон приложения
COL_PANEL    = "#22262a"     # фон панели
COL_BORDER   = "#3a4148"     # окантовка
COL_TEXT     = "#d0d4d8"     # обычный текст
COL_TEXT_DIM = "#7a838c"     # серый комментарий
COL_LABEL    = "#9aa3ac"     # подпись
COL_DIGITAL  = "#62d0ff"     # цифровой readout / акцент
COL_GRN      = "#5fd964"     # OK / link
COL_RED      = "#ff5f5f"     # ERR
COL_AMBER    = "#ffb13e"     # event


# ---- RGBA для kivy.graphics / canvas ------------------------------------

def hex_to_rgba(h: str, a: float = 1.0) -> tuple[float, float, float, float]:
    h = h.lstrip("#")
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return (r, g, b, a)


RGBA_BG     = hex_to_rgba(COL_BG)
RGBA_PANEL  = hex_to_rgba(COL_PANEL)
RGBA_BORDER = hex_to_rgba(COL_BORDER)
RGBA_TEXT   = hex_to_rgba(COL_TEXT)


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
