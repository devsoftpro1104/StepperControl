"""Простой Popup file picker для CSV-файлов с командами.

Заводится в `TerminalTab._on_add` через `CsvFilePicker.open_for(...)`.
Эквивалент `QFileDialog.getOpenFileName` из PySide6-версии.
"""

from __future__ import annotations

from typing import Callable, Optional

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.popup import Popup

from .widgets import IndustrialButton


class CsvFilePicker(Popup):
    """Popup со списком файлов. По OK эмитит callback(path); по Cancel — callback(None)."""

    def __init__(
        self,
        on_pick: Callable[[Optional[str]], None],
        start_path: str = ".",
        **kwargs,
    ) -> None:
        kwargs.setdefault("title", "Выбери .csv файл с командами")
        kwargs.setdefault("size_hint", (0.85, 0.85))
        super().__init__(**kwargs)

        self._on_pick = on_pick

        root = BoxLayout(orientation="vertical", spacing=8, padding=8)

        self._chooser = FileChooserListView(
            path=start_path,
            filters=["*.csv", "*.CSV"],
            size_hint_y=1,
        )
        root.add_widget(self._chooser)

        btn_row = BoxLayout(
            orientation="horizontal",
            size_hint_y=None, height="40dp", spacing=8,
        )
        btn_cancel = IndustrialButton(text="CANCEL", size_hint_x=1)
        btn_open   = IndustrialButton(text="OPEN",   size_hint_x=1)
        btn_cancel.bind(on_release=lambda _b: self._finish(None))
        btn_open.bind(on_release=lambda _b: self._finish_with_selection())
        btn_row.add_widget(btn_cancel)
        btn_row.add_widget(btn_open)
        root.add_widget(btn_row)

        self.content = root

    def _finish_with_selection(self) -> None:
        sel = self._chooser.selection
        path = sel[0] if sel else None
        self._finish(path)

    def _finish(self, path: Optional[str]) -> None:
        self.dismiss()
        self._on_pick(path)

    @classmethod
    def open_for(
        cls,
        on_pick: Callable[[Optional[str]], None],
        start_path: str = ".",
    ) -> "CsvFilePicker":
        p = cls(on_pick=on_pick, start_path=start_path)
        p.open()
        return p
