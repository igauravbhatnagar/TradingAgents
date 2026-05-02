from pathlib import Path

import pandas as pd
import pytest

from tradingagents.dataflows.stockstats_utils import _read_cached_ohlcv, load_ohlcv


@pytest.mark.unit
class TestStockstatsUtils:
    def test_read_cached_ohlcv_discards_empty_file(self, tmp_path: Path):
        cache_file = tmp_path / "empty.csv"
        cache_file.write_text("", encoding="utf-8")

        data = _read_cached_ohlcv(str(cache_file))

        assert data is None
        assert not cache_file.exists()

    def test_load_ohlcv_recovers_from_empty_cache(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        cache_file = tmp_path / "AAPL-YFin-data-2021-01-01-2026-01-01.csv"
        cache_file.write_text("", encoding="utf-8")

        sample = pd.DataFrame(
            {
                "Date": ["2026-05-01", "2026-05-02"],
                "Open": [1.0, 2.0],
                "High": [1.1, 2.1],
                "Low": [0.9, 1.9],
                "Close": [1.05, 2.05],
                "Volume": [100, 200],
            }
        )

        monkeypatch.setattr(
            "tradingagents.dataflows.stockstats_utils.get_config",
            lambda: {"data_cache_dir": str(tmp_path)},
        )
        monkeypatch.setattr(
            "tradingagents.dataflows.stockstats_utils.safe_ticker_component",
            lambda symbol: symbol,
        )
        monkeypatch.setattr(
            "tradingagents.dataflows.stockstats_utils.pd.Timestamp.today",
            classmethod(lambda cls: pd.Timestamp("2026-01-01")),
        )
        monkeypatch.setattr(
            "tradingagents.dataflows.stockstats_utils._download_ohlcv",
            lambda symbol, start_str, end_str: sample.copy(),
        )

        data = load_ohlcv("AAPL", "2026-05-02")

        assert list(data["Close"]) == [1.05, 2.05]
        assert cache_file.exists()