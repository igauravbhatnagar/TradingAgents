import datetime
from pathlib import Path

import pytest

from cli.main import build_batch_run_folder_name, chunk_tickers, run_batch_analysis
from cli.summary import BatchTickerResult, build_result_details, build_summary_table, summarize_final_decision
from cli.telegram import build_completion_message, build_start_message


@pytest.mark.unit
class TestBatchSummary:
    def test_summarize_final_decision_extracts_expected_sections(self):
        final_decision = "\n".join(
            [
                "**Rating**: Buy",
                "",
                "**Executive Summary**: Scale in gradually with a 3 month horizon.",
                "",
                "**Investment Thesis**: Demand remains durable and valuation is still supported.",
            ]
        )

        rating, key_points, pm_decision = summarize_final_decision(final_decision)

        assert rating == "Buy"
        assert key_points == "Scale in gradually with a 3 month horizon."
        assert pm_decision == "Demand remains durable and valuation is still supported."

    def test_build_summary_table_renders_fixed_columns(self):
        results = [
            BatchTickerResult(ticker="AAPL", analysis_date="2026-05-02", status="success", rating="Buy"),
            BatchTickerResult(ticker="MSFT", analysis_date="2026-05-02", status="failed", rating="n/a"),
        ]

        table = build_summary_table(results)

        assert "Ticker" in table
        assert "AAPL" in table
        assert "FAILED" in table

    def test_build_result_details_includes_success_and_failure(self):
        results = [
            BatchTickerResult(
                ticker="AAPL",
                analysis_date="2026-05-02",
                status="success",
                rating="Buy",
                key_points="Strong earnings momentum.",
                portfolio_manager_decision="Add on weakness.",
            ),
            BatchTickerResult(
                ticker="MSFT",
                analysis_date="2026-05-02",
                status="failed",
                error="Upstream provider timeout",
            ),
        ]

        details = build_result_details(results)

        assert "Summary of Key Points" in details
        assert "Portfolio Manager Decision" in details
        assert "FAILED" in details

    def test_build_start_message_contains_run_metadata(self):
        message = build_start_message(
            input_path="Output/Tradesetups_finder/us/csv_data",
            input_files=["C:/tmp/one.csv", "C:/tmp/two.csv"],
            input_mode="file",
            country="us",
            start_time="2026-05-02 09:00:00",
            tickers=["AAPL", "MSFT"],
        )

        assert "TradingAgents batch run started" in message
        assert "🚀" in message
        assert "Country: us" in message
        assert "Input files: one.csv, two.csv" in message
        assert "AAPL, MSFT" in message

    def test_build_completion_message_contains_summary_sections(self):
        message = build_completion_message(
            status="SUCCESS",
            input_path="Output/Tradesetups_finder/us/csv_data",
            input_files=["C:/tmp/tickers.csv"],
            input_mode="file",
            country="us",
            start_time="2026-05-02 09:00:00",
            end_time="2026-05-02 09:15:00",
            run_time="00:15:00",
            summary_table="Ticker | Status | Rating\nAAPL   | SUCCESS | Buy",
            details="- AAPL (Buy)\n  Summary of Key Points: Strong setup\n  Portfolio Manager Decision: Build position",
        )

        assert "TradingAgents batch run SUCCESS" in message
        assert "✅" in message
        assert "Summary Table" in message
        assert "Results" in message
        assert "Input files: tickers.csv" in message
        assert "View complete_report.md" not in message
        assert "Download" not in message

    def test_build_batch_run_folder_name_is_bounded(self):
        started_at = datetime.datetime(2026, 5, 2, 9, 15, 0)

        folder_name = build_batch_run_folder_name(started_at, "United States / Equities", 123)

        assert folder_name.startswith("20260502_091500_")
        assert "123tickers" in folder_name
        assert len(folder_name) <= 50

    def test_chunk_tickers_splits_large_basket(self):
        assert chunk_tickers(["AAPL", "MSFT", "NVDA", "TSLA", "META"], chunk_size=2) == [
            ["AAPL", "MSFT"],
            ["NVDA", "TSLA"],
            ["META"],
        ]

    def test_run_batch_analysis_dispatches_single_basket_run(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        selections = {
            "analysis_date": "2026-05-02",
            "research_depth": 1,
            "llm_provider": "google",
            "backend_url": None,
            "shallow_thinker": "gemini-2.5-flash",
            "deep_thinker": "gemini-3.1-pro-preview",
            "analysts": [],
            "output_language": "English",
            "results_dir": str(tmp_path),
            "telegram_enabled": False,
        }
        calls: list[dict] = []

        monkeypatch.setattr("cli.main.resolve_input_path", lambda country, input_path: Path("resolved.csv"))
        monkeypatch.setattr(
            "cli.main.load_tickers_from_source",
            lambda country, input_path, latest_files=1, min_mcap=None: (
                Path("resolved.csv"),
                [Path("tickers.csv")],
                ["AAPL", "MSFT", "NVDA"],
            ),
        )

        def fake_run_single_background_analysis(run_selections, *, checkpoint=False):
            calls.append(dict(run_selections))
            return BatchTickerResult(
                ticker=run_selections["result_label"],
                analysis_date=run_selections["analysis_date"],
                status="success",
                rating="Buy",
            )

        monkeypatch.setattr(
            "cli.main.run_single_background_analysis",
            fake_run_single_background_analysis,
        )

        results = run_batch_analysis(
            selections,
            country="US",
            input_path="tickers.csv",
            latest_files=1,
            min_mcap="1B",
            checkpoint=False,
        )

        assert len(calls) == 1
        assert calls[0]["ticker"] == "AAPL, MSFT, NVDA"
        assert calls[0]["run_label"] == "basket_us_3"
        assert calls[0]["result_label"] == "US basket (3 tickers)"
        assert len(results) == 1
        assert results[0].ticker == "US basket (3 tickers)"

    def test_run_batch_analysis_splits_large_basket_into_chunks(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        selections = {
            "analysis_date": "2026-05-02",
            "research_depth": 1,
            "llm_provider": "google",
            "backend_url": None,
            "shallow_thinker": "gemini-2.5-flash",
            "deep_thinker": "gemini-3.1-pro-preview",
            "analysts": [],
            "output_language": "English",
            "results_dir": str(tmp_path),
            "telegram_enabled": False,
        }
        calls: list[dict] = []

        monkeypatch.setattr("cli.main.resolve_input_path", lambda country, input_path: Path("resolved.csv"))
        monkeypatch.setattr(
            "cli.main.load_tickers_from_source",
            lambda country, input_path, latest_files=1, min_mcap=None: (
                Path("resolved.csv"),
                [Path("tickers.csv")],
                ["AAPL", "MSFT", "NVDA", "TSLA", "META", "AMD", "INTC", "AVGO", "ORCL"],
            ),
        )
        monkeypatch.setattr(
            "cli.main.chunk_tickers",
            lambda tickers, chunk_size=8: [tickers[:4], tickers[4:8], tickers[8:]],
        )

        def fake_run_single_background_analysis(run_selections, *, checkpoint=False):
            calls.append(dict(run_selections))
            return BatchTickerResult(
                ticker=run_selections["result_label"],
                analysis_date=run_selections["analysis_date"],
                status="success",
                rating="Buy",
            )

        monkeypatch.setattr(
            "cli.main.run_single_background_analysis",
            fake_run_single_background_analysis,
        )

        results = run_batch_analysis(
            selections,
            country="US",
            input_path="tickers.csv",
            latest_files=1,
            checkpoint=False,
        )

        assert [call["ticker"] for call in calls] == [
            "AAPL, MSFT, NVDA, TSLA",
            "META, AMD, INTC, AVGO",
            "ORCL",
        ]
        assert [call["run_label"] for call in calls] == [
            "basket_us_9_chunk_1_of_3",
            "basket_us_9_chunk_2_of_3",
            "basket_us_9_chunk_3_of_3",
        ]
        assert [call["result_label"] for call in calls] == [
            "US basket chunk 1/3 (4 tickers)",
            "US basket chunk 2/3 (4 tickers)",
            "US basket chunk 3/3 (1 tickers)",
        ]
        assert len(results) == 3