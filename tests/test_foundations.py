from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

from stock_market_intelligence_with_langchain.cli import app
from stock_market_intelligence_with_langchain.models import Stock, WatchlistInput
from stock_market_intelligence_with_langchain.providers import (
    ProviderError,
    YahooProvider,
)
from stock_market_intelligence_with_langchain.storage import WatchlistRepository


def test_duplicate_normalized_symbols_do_not_meet_minimum():
    with pytest.raises(ValidationError):
        WatchlistInput(symbols=["NVDA", " nvda ", "MU", "INTC", "TSLA"])


@pytest.mark.parametrize("symbol", ["../NVDA", "", "NVDA;echo", "^GSPC"])
def test_invalid_symbol_is_rejected(symbol):
    with pytest.raises(ValidationError):
        Stock(symbol=symbol)


def test_readding_stock_preserves_verified_identity(tmp_path):
    path = tmp_path / "market.sqlite3"
    repo = WatchlistRepository(path)
    verified = Stock(
        symbol="NVDA", company_name="Test company", verified_at=datetime.now(UTC)
    )
    repo.add([verified])
    repo.add([Stock(symbol=" nvda ")])
    assert WatchlistRepository(path).list() == [verified]


def test_init_invalid_selection_does_not_write(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKET_DATA_DIR", str(tmp_path))
    result = CliRunner().invoke(app, ["init", "NVDA", "MU"])
    assert result.exit_code == 1
    assert not (tmp_path / "market.sqlite3").exists()


def test_init_then_list_survives_separate_invocations(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKET_DATA_DIR", str(tmp_path))
    runner = CliRunner()
    assert (
        runner.invoke(app, ["init", "INTC", "NVDA", "TSLA", "PLTR", "MU"]).exit_code
        == 0
    )
    listing = runner.invoke(app, ["watchlist", "list"])
    assert listing.exit_code == 0
    assert "Unverified" in listing.output
    assert "PLTR" in listing.output


@pytest.mark.parametrize(
    "info",
    [
        {"symbol": "OTHER", "quoteType": "EQUITY", "exchange": "NMS"},
        {"symbol": "NVDA", "quoteType": "ETF", "exchange": "NMS"},
        {"symbol": "NVDA", "quoteType": "EQUITY", "exchange": "LSE"},
        {},
    ],
)
def test_provider_rejects_wrong_identity(monkeypatch, info):
    class FakeTicker:
        def __init__(self, symbol):
            pass

        def get_info(self):
            return info

    monkeypatch.setattr(
        "stock_market_intelligence_with_langchain.providers.yf.Ticker", FakeTicker
    )
    with pytest.raises(ProviderError):
        YahooProvider().fetch("NVDA")


def test_doctor_never_prints_credentials(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-secret-not-for-display")
    result = CliRunner().invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "configured (not tested)" in result.output
    assert "test-secret-not-for-display" not in result.output


def test_probe_records_failure_without_claiming_missing_data(tmp_path, monkeypatch):
    monkeypatch.setenv("MARKET_DATA_DIR", str(tmp_path))
    runner = CliRunner()
    runner.invoke(app, ["init", "INTC", "NVDA", "TSLA", "PLTR", "MU"])

    def unavailable(self, symbol):
        raise ProviderError("Source unavailable.")

    monkeypatch.setattr(YahooProvider, "fetch", unavailable)
    result = runner.invoke(app, ["probe"])
    assert result.exit_code == 1
    coverage = (tmp_path / "coverage.md").read_text()
    assert coverage.count("Source unavailable.") == 5
    assert "Unknown" in coverage
    assert all(
        stock.verified_at is None
        for stock in WatchlistRepository(tmp_path / "market.sqlite3").list()
    )
