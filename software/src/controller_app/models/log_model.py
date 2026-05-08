"""QAbstractListModel для отображения лога."""
from __future__ import annotations

from PyQt6.QtCore import QAbstractListModel, QModelIndex, Qt


class LogModel(QAbstractListModel):
    def __init__(self) -> None:
        super().__init__()
        self._rows: list[str] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._rows)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if role == Qt.ItemDataRole.DisplayRole and index.isValid():
            return self._rows[index.row()]
        return None

    def append(self, line: str) -> None:
        self.beginInsertRows(QModelIndex(), len(self._rows), len(self._rows))
        self._rows.append(line)
        self.endInsertRows()