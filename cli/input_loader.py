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


def _normalize_for_country(value: str, country: str | None = None) -> str:
    normalized = normalize_ticker_symbol(value)
    if (country or "").strip().lower() == "india" and "." not in normalized:
        return f"{normalized}.NS"
    return normalized


def _dedupe_tickers(values: Iterable[str], country: str | None = None) -> list[str]:
    tickers: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = value.strip()
        if not cleaned:
            continue
        normalized = _normalize_for_country(cleaned, country)
        if normalized not in seen:
            seen.add(normalized)
            tickers.append(normalized)
    return tickers


def _find_fieldname(fieldnames: Iterable[str | None], expected_name: str) -> str | None:
    expected = expected_name.strip().lower()
    for fieldname in fieldnames:
        if fieldname and fieldname.strip().lower() == expected:
            return fieldname
    return None


def _parse_mcap_value(value: str | int | float) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None

    cleaned = value.strip().upper().replace(",", "").replace("$", "")
    if not cleaned:
        return None

    multipliers = {
        "T": 1_000_000_000_000,
        "B": 1_000_000_000,
        "M": 1_000_000,
        "K": 1_000,
    }
    suffix = cleaned[-1]
    multiplier = multipliers.get(suffix)
    numeric_part = cleaned[:-1] if multiplier else cleaned

    try:
        parsed = float(numeric_part)
    except ValueError:
        return None

    if multiplier:
        parsed *= multiplier
    return parsed


def _parse_numeric_value(value: str | int | float) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None

    cleaned = value.strip().upper().replace(",", "").replace("%", "")
    if not cleaned or cleaned == "N/A":
        return None

    try:
        return float(cleaned)
    except ValueError:
        return None


def _row_mcap_value(
    row: dict[str | None, str | list[str]],
    mcap_fieldname: str,
) -> str:
    base_value = row.get(mcap_fieldname, "")
    if isinstance(base_value, list):
        parts = [part.strip() for part in base_value if part and part.strip()]
    else:
        parts = [str(base_value).strip()] if str(base_value).strip() else []

    overflow = row.get(None)
    if isinstance(overflow, list):
        parts.extend(part.strip() for part in overflow if part and part.strip())

    return "".join(parts)


def _load_symbol_column(
    file_path: Path,
    country: str | None = None,
    min_mcap: str | None = None,
    max_free_float_pct: float | None = None,
    min_one_week_change_pct: float | None = None,
) -> list[str]:
    with file_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise InputLoadError(f"CSV file is empty: {file_path}")
        symbol_fieldname = _find_fieldname(reader.fieldnames, "Symbol")
        if not symbol_fieldname:
            raise InputLoadError(
                f"CSV file does not contain required 'Symbol' column: {file_path}"
            )

        threshold = None
        mcap_fieldname = None
        if min_mcap is not None:
            mcap_fieldname = _find_fieldname(reader.fieldnames, "MCAP")
            if not mcap_fieldname:
                raise InputLoadError(
                    f"CSV file does not contain required 'MCAP' column for --min-mcap: {file_path}"
                )
            threshold = _parse_mcap_value(min_mcap)
            if threshold is None:
                raise InputLoadError(
                    f"Invalid --min-mcap value: {min_mcap}. Expected formats like 1B, 750M, or 1200000000."
                )

        free_float_fieldname = None
        if max_free_float_pct is not None:
            free_float_fieldname = _find_fieldname(reader.fieldnames, "Free Float %")
            if not free_float_fieldname:
                raise InputLoadError(
                    f"CSV file does not contain required 'Free Float %' column for --max-free-float-pct: {file_path}"
                )

        one_week_change_fieldname = None
        if min_one_week_change_pct is not None:
            one_week_change_fieldname = _find_fieldname(reader.fieldnames, "1W Change %")
            if not one_week_change_fieldname:
                raise InputLoadError(
                    f"CSV file does not contain required '1W Change %' column for --min-1w-change-pct: {file_path}"
                )

        symbols: list[str] = []
        for row in reader:
            symbol = row.get(symbol_fieldname, "")
            if threshold is not None:
                mcap_value = _parse_mcap_value(_row_mcap_value(row, mcap_fieldname))
                if mcap_value is None or mcap_value <= threshold:
                    continue
            if max_free_float_pct is not None:
                free_float_value = _parse_numeric_value(str(row.get(free_float_fieldname, "")))
                if free_float_value is None or free_float_value >= max_free_float_pct:
                    continue
            if min_one_week_change_pct is not None:
                one_week_change_value = _parse_numeric_value(str(row.get(one_week_change_fieldname, "")))
                if one_week_change_value is None or one_week_change_value <= min_one_week_change_pct:
                    continue
            symbols.append(symbol)

        return _dedupe_tickers(symbols, country=country)


def _load_delimited_text(
    file_path: Path,
    country: str | None = None,
    min_mcap: str | None = None,
    max_free_float_pct: float | None = None,
    min_one_week_change_pct: float | None = None,
) -> list[str]:
    if (
        min_mcap is not None
        or max_free_float_pct is not None
        or min_one_week_change_pct is not None
    ):
        raise InputLoadError(
            "CSV row filters can only be used with CSV inputs that contain the required columns: "
            f"{file_path}"
        )

    raw_text = file_path.read_text(encoding="utf-8-sig")
    values = [part for chunk in raw_text.splitlines() for part in chunk.split(",")]
    tickers = _dedupe_tickers(values, country=country)
    if not tickers:
        raise InputLoadError(f"No tickers found in input file: {file_path}")
    return tickers


def load_tickers_from_file(
    file_path: Path,
    country: str | None = None,
    min_mcap: str | None = None,
    max_free_float_pct: float | None = None,
    min_one_week_change_pct: float | None = None,
) -> list[str]:
    if not file_path.exists() or not file_path.is_file():
        raise InputLoadError(f"Input file does not exist: {file_path}")

    if file_path.suffix.lower() == ".csv":
        try:
            tickers = _load_symbol_column(
                file_path,
                country=country,
                min_mcap=min_mcap,
                max_free_float_pct=max_free_float_pct,
                min_one_week_change_pct=min_one_week_change_pct,
            )
            if tickers:
                return tickers
            if any(
                value is not None
                for value in (min_mcap, max_free_float_pct, min_one_week_change_pct)
            ):
                raise InputLoadError(
                    f"No tickers matched the configured CSV filters in input file: {file_path}"
                )
        except InputLoadError:
            if any(
                value is not None
                for value in (min_mcap, max_free_float_pct, min_one_week_change_pct)
            ):
                raise
            # Allow a plain comma-separated ticker file even when the extension is .csv.
            pass

    return _load_delimited_text(
        file_path,
        country=country,
        min_mcap=min_mcap,
        max_free_float_pct=max_free_float_pct,
        min_one_week_change_pct=min_one_week_change_pct,
    )


def _csv_files_sorted(folder_path: Path) -> list[Path]:
    return sorted(
        (path for path in folder_path.iterdir() if path.is_file() and path.suffix.lower() == ".csv"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def load_tickers_from_folder(
    folder_path: Path,
    latest_files: int = 1,
    country: str | None = None,
    min_mcap: str | None = None,
    max_free_float_pct: float | None = None,
    min_one_week_change_pct: float | None = None,
) -> tuple[list[Path], list[str]]:
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
        tickers.extend(
            _load_symbol_column(
                file_path,
                country=country,
                min_mcap=min_mcap,
                max_free_float_pct=max_free_float_pct,
                min_one_week_change_pct=min_one_week_change_pct,
            )
        )

    deduped = _dedupe_tickers(tickers, country=country)
    if not deduped:
        if any(
            value is not None
            for value in (min_mcap, max_free_float_pct, min_one_week_change_pct)
        ):
            raise InputLoadError(
                f"No tickers matched the configured CSV filters across selected CSV files in: {folder_path}"
            )
        raise InputLoadError(f"No tickers found across selected CSV files in: {folder_path}")
    return selected_files, deduped


def load_tickers_from_source(
    country: str,
    input_path: str | None,
    latest_files: int = 1,
    min_mcap: str | None = None,
    max_free_float_pct: float | None = None,
    min_one_week_change_pct: float | None = None,
) -> tuple[Path, list[Path], list[str]]:
    resolved_path = resolve_input_path(country, input_path)
    if resolved_path.is_dir() or (not resolved_path.exists() and input_path is None):
        selected_files, tickers = load_tickers_from_folder(
            resolved_path,
            latest_files=latest_files,
            country=country,
            min_mcap=min_mcap,
            max_free_float_pct=max_free_float_pct,
            min_one_week_change_pct=min_one_week_change_pct,
        )
        return resolved_path, selected_files, tickers
    tickers = load_tickers_from_file(
        resolved_path,
        country=country,
        min_mcap=min_mcap,
        max_free_float_pct=max_free_float_pct,
        min_one_week_change_pct=min_one_week_change_pct,
    )
    return resolved_path, [resolved_path], tickers