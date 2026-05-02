from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

from cli.utils import normalize_ticker_symbol


DEFAULT_INPUT_ROOT = Path("Output") / "Tradesetups_finder"


class InputLoadError(ValueError):
    """Raised when a ticker input source cannot be parsed."""


def default_input_path(country: str) -> Path:
    return DEFAULT_INPUT_ROOT / country / "csv_data"


def resolve_input_path(country: str, input_path: str | None) -> Path:
    if input_path:
        return Path(input_path)
    return default_input_path(country)


def _dedupe_tickers(values: Iterable[str]) -> list[str]:
    tickers: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        normalized = normalize_ticker_symbol(cleaned)
        if normalized not in seen:
            seen.add(normalized)
            tickers.append(normalized)
    return tickers


def _load_symbol_column(file_path: Path) -> list[str]:
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise InputLoadError(f"CSV file is empty: {file_path}")
        if "Symbol" not in reader.fieldnames:
            raise InputLoadError(
                f"CSV file does not contain required 'Symbol' column: {file_path}"
            )
        return _dedupe_tickers(row.get("Symbol", "") for row in reader)


def _load_delimited_text(file_path: Path) -> list[str]:
    raw_text = file_path.read_text(encoding="utf-8-sig")
    values = [part for chunk in raw_text.splitlines() for part in chunk.split(",")]
    tickers = _dedupe_tickers(values)
    if not tickers:
        raise InputLoadError(f"No tickers found in input file: {file_path}")
    return tickers


def load_tickers_from_file(file_path: Path) -> list[str]:
    if not file_path.exists() or not file_path.is_file():
        raise InputLoadError(f"Input file does not exist: {file_path}")

    if file_path.suffix.lower() == ".csv":
        try:
            tickers = _load_symbol_column(file_path)
            if tickers:
                return tickers
        except InputLoadError:
            # Allow a plain comma-separated ticker file even when the extension is .csv.
            pass

    return _load_delimited_text(file_path)


def _csv_files_sorted(folder_path: Path) -> list[Path]:
    return sorted(
        (path for path in folder_path.iterdir() if path.is_file() and path.suffix.lower() == ".csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def load_tickers_from_folder(folder_path: Path, latest_files: int = 1) -> tuple[list[Path], list[str]]:
    if latest_files < 1:
        raise InputLoadError("latest_files must be at least 1")
    if not folder_path.exists() or not folder_path.is_dir():
        raise InputLoadError(f"Input folder does not exist: {folder_path}")

    csv_files = _csv_files_sorted(folder_path)
    if not csv_files:
        raise InputLoadError(f"No CSV files found in input folder: {folder_path}")

    selected_files = csv_files[:latest_files]
    tickers: list[str] = []
    for file_path in selected_files:
        tickers.extend(_load_symbol_column(file_path))

    deduped = _dedupe_tickers(tickers)
    if not deduped:
        raise InputLoadError(f"No tickers found across selected CSV files in: {folder_path}")
    return selected_files, deduped


def load_tickers_from_source(
    country: str,
    input_path: str | None,
    latest_files: int = 1,
) -> tuple[Path, list[Path], list[str]]:
    resolved_path = resolve_input_path(country, input_path)
    if resolved_path.is_dir() or (not resolved_path.exists() and input_path is None):
        selected_files, tickers = load_tickers_from_folder(resolved_path, latest_files=latest_files)
        return resolved_path, selected_files, tickers
    tickers = load_tickers_from_file(resolved_path)
    return resolved_path, [resolved_path], tickers