"""Палитра и QSS-хелперы для CNC-стилистики.

Один первоисточник для цветов и стилей виджетов. Все view-файлы
импортируют только отсюда — менять стилистику теперь нужно в одном месте.
"""

from __future__ import annotations


# ---- палитра ---------------------------------------------------------------

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


# ---- QSS-хелперы (вызываются как функции, чтобы f-строки рендерились) -----

def app_qss() -> str:
    """Глобальный стиль центрального QWidget — фон + базовый шрифт."""
    return f"""
        QWidget {{
            background: {COL_BG_OUT};
            color: {COL_TEXT};
            font-family: Consolas, "Cascadia Mono", monospace;
        }}
        QLabel {{
            background: transparent;
        }}
        QStatusBar {{
            background: {COL_BG_IN};
            color: {COL_TEXT_DIM};
            border-top: 1px solid {COL_PANEL_EDGE};
        }}
    """


def industrial_button_qss() -> str:
    """Прямоугольная кнопка (Connect / Send / Clear / DUMP)."""
    return f"""
        QPushButton {{
            background: #1a2027;
            color: {COL_TEXT};
            border: 1px solid {COL_PANEL_EDGE};
            border-radius: 4px;
            font-weight: bold;
            letter-spacing: 2px;
            padding: 6px 14px;
        }}
        QPushButton:hover {{
            border: 1px solid {COL_DIGITAL};
            color: {COL_DIGITAL};
        }}
        QPushButton:pressed {{
            background: {COL_DIGITAL_DIM};
        }}
        QPushButton:checked {{
            background: {COL_DIGITAL_DIM};
            color: {COL_DIGITAL};
            border: 1px solid {COL_DIGITAL};
        }}
        QPushButton:disabled {{
            color: #4a545d;
            border: 1px solid #1a1f23;
            background: #0e1216;
        }}
    """


def combobox_qss() -> str:
    return f"""
        QComboBox {{
            background: #0c1014;
            color: {COL_TEXT};
            border: 1px solid {COL_PANEL_EDGE};
            border-radius: 4px;
            padding: 6px 10px;
        }}
        QComboBox:hover {{ border: 1px solid {COL_DIGITAL}; }}
        QComboBox::drop-down {{ border: 0; width: 22px; }}
        QComboBox::down-arrow {{ image: none; width: 0; height: 0; }}
        QComboBox QAbstractItemView {{
            background: #0c1014;
            color: {COL_TEXT};
            selection-background-color: {COL_DIGITAL_DIM};
            selection-color: {COL_DIGITAL};
            border: 1px solid {COL_PANEL_EDGE};
        }}
    """


def lineedit_qss() -> str:
    return f"""
        QLineEdit {{
            background: #0c1014;
            color: {COL_TEXT};
            border: 1px solid {COL_PANEL_EDGE};
            border-radius: 4px;
            padding: 6px 10px;
            selection-background-color: {COL_DIGITAL_DIM};
            selection-color: {COL_DIGITAL};
        }}
        QLineEdit:focus {{ border: 1px solid {COL_DIGITAL}; }}
        QLineEdit:disabled {{
            color: #4a545d;
            border: 1px solid #1a1f23;
            background: #0a0d10;
        }}
    """


def textedit_qss() -> str:
    return f"""
        QTextEdit {{
            background: {COL_BG_INSET};
            color: {COL_TEXT};
            border: 1px solid {COL_PANEL_EDGE};
            border-radius: 4px;
            padding: 8px;
            selection-background-color: {COL_DIGITAL_DIM};
            selection-color: {COL_DIGITAL};
        }}
    """


def slider_qss() -> str:
    return f"""
        QSlider::groove:horizontal {{
            background: #0c1014;
            border: 1px solid {COL_PANEL_EDGE};
            height: 6px;
            border-radius: 3px;
        }}
        QSlider::sub-page:horizontal {{
            background: {COL_DIGITAL_DIM};
            border: 1px solid {COL_PANEL_EDGE};
            height: 6px;
            border-radius: 3px;
        }}
        QSlider::handle:horizontal {{
            background: {COL_DIGITAL};
            border: 2px solid {COL_BG_INSET};
            width: 16px;
            margin: -7px 0;
            border-radius: 8px;
        }}
        QSlider::handle:horizontal:disabled {{
            background: #2a3138;
            border: 2px solid {COL_BG_INSET};
        }}
    """


def spinbox_qss() -> str:
    return f"""
        QSpinBox {{
            background: #0c1014;
            color: {COL_DIGITAL};
            border: 1px solid {COL_PANEL_EDGE};
            border-radius: 4px;
            padding: 4px 8px;
            font-family: Consolas;
            font-weight: bold;
        }}
        QSpinBox:focus {{ border: 1px solid {COL_DIGITAL}; }}
        QSpinBox::up-button, QSpinBox::down-button {{
            background: #1a2027;
            border: 1px solid {COL_PANEL_EDGE};
            width: 16px;
        }}
        QSpinBox::up-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 5px solid {COL_DIGITAL};
            width: 0; height: 0;
        }}
        QSpinBox::down-arrow {{
            image: none;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid {COL_DIGITAL};
            width: 0; height: 0;
        }}
    """


def tab_qss() -> str:
    return f"""
        QTabWidget::pane {{
            border: 0;
            background: transparent;
            top: 0;
        }}
        QTabBar {{
            background: transparent;
            border: 0;
            qproperty-drawBase: 0;
        }}
        QTabBar::tab {{
            background: #11171c;
            color: {COL_TEXT_DIM};
            border: 1px solid {COL_PANEL_EDGE};
            border-bottom: 0;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 8px 22px;
            margin-right: 2px;
            font-weight: bold;
            letter-spacing: 3px;
        }}
        QTabBar::tab:hover {{
            color: {COL_DIGITAL};
        }}
        QTabBar::tab:selected {{
            background: {COL_DIGITAL_DIM};
            color: {COL_DIGITAL};
            border: 1px solid {COL_DIGITAL};
            border-bottom: 0;
        }}
    """
