from __future__ import annotations

import html
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests


@dataclass
class TelegramConfig:
    enabled: bool
    bot_token: str | None
    chat_id: str | None


class TelegramNotifier:
    MAX_MESSAGE_LENGTH = 4000

    def __init__(self, config: TelegramConfig):
        self.config = config

    @property
    def enabled(self) -> bool:
        return bool(
            self.config.enabled and self.config.bot_token and self.config.chat_id
        )

    def send_message(self, message: str) -> None:
        if not self.enabled:
            return

        trimmed = message
        if len(trimmed) > self.MAX_MESSAGE_LENGTH:
            trimmed = trimmed[: self.MAX_MESSAGE_LENGTH - 3].rstrip() + "..."

        response = requests.post(
            f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage",
            data={
                "chat_id": self.config.chat_id,
                "text": trimmed,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        response.raise_for_status()


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _status_icon(status: str) -> str:
    return {
        "SUCCESS": "✅",
        "PARTIAL FAILURE": "⚠️",
        "FAILED": "❌",
    }.get(status.upper(), "ℹ️")


def _format_input_files(input_files: list[str]) -> str:
    if not input_files:
        return "n/a"
    return ", ".join(Path(file_path).name for file_path in input_files)


def build_start_message(
    *,
    input_path: str,
    input_files: list[str],
    input_mode: str,
    country: str,
    start_time: str,
    tickers: list[str],
) -> str:
    ticker_preview = ", ".join(tickers[:10])
    if len(tickers) > 10:
        ticker_preview += f", ... (+{len(tickers) - 10} more)"
    return (
        "🚀 TradingAgents batch run started\n\n"
        f"Input mode: {_escape(input_mode)}\n"
        f"Country: {_escape(country)}\n"
        f"Input path: {_escape(input_path)}\n"
        f"Input files: {_escape(_format_input_files(input_files))}\n"
        f"Start time: {_escape(start_time)}\n"
        f"Tickers ({len(tickers)}): {_escape(ticker_preview or 'n/a')}"
    )


def build_completion_message(
    *,
    status: str,
    input_path: str,
    input_files: list[str],
    input_mode: str,
    country: str,
    start_time: str,
    end_time: str,
    run_time: str,
    summary_table: str,
    details: str,
) -> str:
    return (
        f"{_status_icon(status)} TradingAgents batch run {_escape(status)}\n\n"
        f"Input mode: {_escape(input_mode)}\n"
        f"Country: {_escape(country)}\n"
        f"Input path: {_escape(input_path)}\n"
        f"Input files: {_escape(_format_input_files(input_files))}\n"
        f"Start time: {_escape(start_time)}\n"
        f"End time: {_escape(end_time)}\n"
        f"Run time: {_escape(run_time)}\n\n"
        f"<b>Summary Table</b>\n<pre>{_escape(summary_table)}</pre>\n\n"
        f"<b>Results</b>\n<pre>{_escape(details)}</pre>"
    )