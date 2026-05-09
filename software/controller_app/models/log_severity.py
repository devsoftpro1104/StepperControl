"""Severity-теги логирования. Строки, не QColor — model нейтральна к Qt.GUI;
маппинг в цвет живёт в views/log_panel.py."""

from __future__ import annotations


class LogSeverity:
    OK     = "ok"
    ERR    = "err"
    EVENT  = "event"
    STREAM = "stream"
    CMT    = "cmt"
    RAW    = "raw"
    TX     = "tx"
