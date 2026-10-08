"""Provider adapters return evidence; they do not write the watchlist."""

from datetime import UTC, datetime
from typing import Protocol

import yfinance as yf

from .models import SourceSnapshot, Stock


class ProviderError(Exception):
    """An expected source access or identity verification failure."""


class StockProvider(Protocol):
    def fetch(self, symbol: str) -> tuple[Stock, SourceSnapshot]: ...


class YahooProvider:
    def fetch(self, symbol: str) -> tuple[Stock, SourceSnapshot]:
        try:
            info = yf.Ticker(symbol).get_info()
        except Exception as exc:
            # External library errors vary; preserve the cause for debugging.
            raise ProviderError(
                f"Yahoo request failed ({type(exc).__name__})."
            ) from exc
        if not isinstance(info, dict) or not info:
            raise ProviderError("Yahoo returned no company information.")
        if info.get("symbol", "").upper() != symbol:
            raise ProviderError("Provider returned a different or missing ticker.")
        if info.get("quoteType") != "EQUITY":
            raise ProviderError("Provider did not identify this symbol as an equity.")
        # Conservative initial scope: major US exchanges, including US-listed ADRs.
        if info.get("exchange") not in {
            "NMS",
            "NGM",
            "NCM",
            "NYQ",
            "ASE",
            "PCX",
            "BTS",
        }:
            raise ProviderError("Listing is not verified on a supported US exchange.")
        name = info.get("longName") or info.get("shortName")
        if not name:
            raise ProviderError("Provider returned no company name.")
        now = datetime.now(UTC)
        return (
            Stock(
                symbol=symbol,
                company_name=name,
                exchange=info["exchange"],
                verified_at=now,
            ),
            SourceSnapshot(
                provider="yahoo_via_yfinance",
                symbol=symbol,
                source_url=f"https://finance.yahoo.com/quote/{symbol}/",
                retrieved_at=now,
                payload=info,
            ),
        )
