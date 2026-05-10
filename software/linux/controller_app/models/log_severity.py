"""Severity-теги логирования. Строки — model нейтральна к UI;
маппинг в цвет живёт во views/theme.py."""

from __future__ import annotations


class LogSeverity:
    OK     = "ok"
    ERR    = "err"
    EVENT  = "event"
    STREAM = "stream"
    CMT    = "cmt"
    RAW    = "raw"
    TX     = "tx"
