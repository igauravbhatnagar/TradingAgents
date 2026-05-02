from __future__ import annotations

import html
from dataclasses import dataclass
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

        escaped = html.escape(trimmed)
        response = requests.post(
            f"https://api.telegram.org/bot{self.config.bot_token}/sendMessage",
            data={
                "chat_id": self.config.chat_id,
                "text": escaped,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        response.raise_for_status()


def build_start_message(*, input_path: str, input_mode: str, country: str, start_time: str, tickers: list[str]) -> str:
    ticker_preview = ", ".join(tickers[:10])
    if len(tickers) > 10:
        ticker_preview += f", ... (+{len(tickers) - 10} more)"
    return (
        "TradingAgents batch run started\n\n"
        f"Input mode: {input_mode}\n"
        f"Country: {country}\n"
        f"Input path: {input_path}\n"
        f"Start time: {start_time}\n"
        f"Tickers ({len(tickers)}): {ticker_preview or 'n/a'}"
    )


def build_completion_message(
    *,
    status: str,
    input_path: str,
    input_mode: str,
    country: str,
    start_time: str,
    end_time: str,
    run_time: str,
    summary_table: str,
    details: str,
) -> str:
    return (
        f"TradingAgents batch run {status}\n\n"
        f"Input mode: {input_mode}\n"
        f"Country: {country}\n"
        f"Input path: {input_path}\n"
        f"Start time: {start_time}\n"
        f"End time: {end_time}\n"
        f"Run time: {run_time}\n\n"
        "Summary Table\n"
        f"{summary_table}\n\n"
        "Results\n"
        f"{details}"
    )