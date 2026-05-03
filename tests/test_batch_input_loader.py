import os
from pathlib import Path

import pytest

from cli.input_loader import (
    InputLoadError,
    default_input_path,
    load_tickers_from_file,
    load_tickers_from_folder,
    load_tickers_from_source,
)


@pytest.mark.unit
class TestBatchInputLoader:
    def test_default_input_path_uses_country(self):
        assert default_input_path("india") == Path("Output") / "Tradesetups_finder" / "india" / "csv_data"

    def test_load_tickers_from_symbol_column(self, tmp_path: Path):
        file_path = tmp_path / "setup.csv"
        file_path.write_text(
            "Symbol,Other\nAAPL,1\n msft ,2\nAAPL,3\n",
            encoding="utf-8",
        )

        assert load_tickers_from_file(file_path) == ["AAPL", "MSFT"]

    def test_load_tickers_from_comma_separated_file(self, tmp_path: Path):
        file_path = tmp_path / "tickers.txt"
        file_path.write_text("aapl, msft\nnvda", encoding="utf-8")

        assert load_tickers_from_file(file_path) == ["AAPL", "MSFT", "NVDA"]

    def test_load_tickers_from_file_adds_ns_suffix_for_india(self, tmp_path: Path):
        file_path = tmp_path / "india.csv"
        file_path.write_text("Symbol\nRELIANCE\nTCS.NS\nINFY\n", encoding="utf-8")

        assert load_tickers_from_file(file_path, country="INDIA") == [
            "RELIANCE.NS",
            "TCS.NS",
            "INFY.NS",
        ]

    def test_load_tickers_from_file_filters_by_mcap_strictly_greater_than_threshold(self, tmp_path: Path):
        file_path = tmp_path / "setup.csv"
        file_path.write_text(
            "Symbol,MCAP\nAAPL,2B\nMSFT,1B\nNVDA,$1,500,000,000\nSMALL,750M\n",
            encoding="utf-8",
        )

        assert load_tickers_from_file(file_path, min_mcap="1B") == ["AAPL", "NVDA"]

    def test_load_tickers_from_file_accepts_mixed_case_mcap_header(self, tmp_path: Path):
        file_path = tmp_path / "setup.csv"
        file_path.write_text(
            "Symbol,MCap\nAAPL,2B\nMSFT,1B\nSMALL,750M\n",
            encoding="utf-8",
        )

        assert load_tickers_from_file(file_path, min_mcap="1B") == ["AAPL"]

    def test_load_tickers_from_file_requires_mcap_column_when_filter_is_used(self, tmp_path: Path):
        file_path = tmp_path / "setup.csv"
        file_path.write_text("Symbol,Other\nAAPL,1\n", encoding="utf-8")

        with pytest.raises(InputLoadError, match="MCAP"):
            load_tickers_from_file(file_path, min_mcap="1B")

    def test_load_tickers_from_file_rejects_min_mcap_for_non_csv_input(self, tmp_path: Path):
        file_path = tmp_path / "tickers.txt"
        file_path.write_text("aapl, msft", encoding="utf-8")

        with pytest.raises(InputLoadError, match="--min-mcap"):
            load_tickers_from_file(file_path, min_mcap="1B")

    def test_folder_mode_reads_latest_files(self, tmp_path: Path):
        older = tmp_path / "older.csv"
        newer = tmp_path / "newer.csv"
        older.write_text("Symbol\nAAPL\n", encoding="utf-8")
        newer.write_text("Symbol\nMSFT\nNVDA\n", encoding="utf-8")
        os.utime(older, (1_700_000_000, 1_700_000_000))
        os.utime(newer, (1_800_000_000, 1_800_000_000))

        selected_files, tickers = load_tickers_from_folder(tmp_path, latest_files=1)

        assert selected_files == [newer]
        assert tickers == ["MSFT", "NVDA"]

    def test_folder_mode_combines_latest_n_files(self, tmp_path: Path):
        oldest = tmp_path / "oldest.csv"
        middle = tmp_path / "middle.csv"
        newest = tmp_path / "newest.csv"
        oldest.write_text("Symbol\nIBM\n", encoding="utf-8")
        middle.write_text("Symbol\nAAPL\n", encoding="utf-8")
        newest.write_text("Symbol\nMSFT\n", encoding="utf-8")
        os.utime(oldest, (1_600_000_000, 1_600_000_000))
        os.utime(middle, (1_700_000_000, 1_700_000_000))
        os.utime(newest, (1_800_000_000, 1_800_000_000))

        selected_files, tickers = load_tickers_from_folder(tmp_path, latest_files=2)

        assert selected_files == [newest, middle]
        assert tickers == ["MSFT", "AAPL"]

    def test_folder_mode_requires_symbol_column(self, tmp_path: Path):
        file_path = tmp_path / "bad.csv"
        file_path.write_text("Ticker\nAAPL\n", encoding="utf-8")

        with pytest.raises(InputLoadError):
            load_tickers_from_folder(tmp_path)

    def test_load_tickers_from_source_defaults_to_folder(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        default_dir = tmp_path / "Output" / "Tradesetups_finder" / "us" / "csv_data"
        default_dir.mkdir(parents=True)
        csv_file = default_dir / "tickers.csv"
        csv_file.write_text("Symbol\nTSLA\n", encoding="utf-8")
        monkeypatch.chdir(tmp_path)

        resolved_path, selected_files, tickers = load_tickers_from_source("us", None)

        assert resolved_path == default_dir
        assert selected_files == [csv_file]
        assert tickers == ["TSLA"]

    def test_load_tickers_from_source_applies_india_suffix(self, tmp_path: Path):
        csv_file = tmp_path / "tickers.csv"
        csv_file.write_text("Symbol\nSBIN\nHDFCBANK\n", encoding="utf-8")

        resolved_path, selected_files, tickers = load_tickers_from_source(
            "INDIA", str(csv_file)
        )

        assert resolved_path == csv_file
        assert selected_files == [csv_file]
        assert tickers == ["SBIN.NS", "HDFCBANK.NS"]

    def test_load_tickers_from_source_applies_mcap_filter(self, tmp_path: Path):
        csv_file = tmp_path / "tickers.csv"
        csv_file.write_text(
            "Symbol,MCAP\nLARGE,5B\nMID,1.2B\nSMALL,500M\n",
            encoding="utf-8",
        )

        resolved_path, selected_files, tickers = load_tickers_from_source(
            "US", str(csv_file), min_mcap="1B"
        )

        assert resolved_path == csv_file
        assert selected_files == [csv_file]
        assert tickers == ["LARGE", "MID"]