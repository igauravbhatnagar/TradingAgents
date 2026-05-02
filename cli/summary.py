from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class BatchTickerResult:
    ticker: str
    analysis_date: str
    status: str
    rating: str = "n/a"
    key_points: str = ""
    portfolio_manager_decision: str = ""
    report_path: str | None = None
    error: str | None = None


def _extract_markdown_field(text: str, label: str) -> str:
    prefix = f"**{label}**:"
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix):].strip()
    return ""


def summarize_final_decision(final_trade_decision: str) -> tuple[str, str, str]:
    rating = _extract_markdown_field(final_trade_decision, "Rating") or "Hold"
    key_points = _extract_markdown_field(final_trade_decision, "Executive Summary")
    pm_decision = _extract_markdown_field(final_trade_decision, "Investment Thesis")
    return rating, key_points, pm_decision


def build_summary_table(results: Iterable[BatchTickerResult]) -> str:
    rows = [["Ticker", "Status", "Rating"]]
    for result in results:
        rows.append([result.ticker, result.status.upper(), result.rating])

    widths = [max(len(row[index]) for row in rows) for index in range(len(rows[0]))]
    rendered_rows = []
    for row in rows:
        rendered_rows.append(" | ".join(value.ljust(widths[index]) for index, value in enumerate(row)))
    return "\n".join(rendered_rows)


def _truncate(text: str, limit: int = 280) -> str:
    cleaned = " ".join(text.split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 3].rstrip() + "..."


def build_result_details(results: Iterable[BatchTickerResult]) -> str:
    lines: list[str] = []
    for result in results:
        if result.status != "success":
            error_text = _truncate(result.error or "Unknown error", limit=220)
            lines.append(f"- {result.ticker}: FAILED - {error_text}")
            continue
        key_points = _truncate(result.key_points or "n/a")
        pm_decision = _truncate(result.portfolio_manager_decision or "n/a")
        lines.append(f"- {result.ticker} ({result.rating})")
        lines.append(f"  Summary of Key Points: {key_points}")
        lines.append(f"  Portfolio Manager Decision: {pm_decision}")
    return "\n".join(lines)


def report_path_text(path: Path | None) -> str:
    if path is None:
        return "n/a"
    return str(path)