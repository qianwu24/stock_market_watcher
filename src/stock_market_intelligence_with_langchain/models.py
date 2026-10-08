"""Contracts shared by the CLI, storage, and future agent tools."""

import re
from datetime import date
from typing import Any

from pydantic import AwareDatetime, BaseModel, Field, HttpUrl, field_validator


def normalize_symbol(value: str) -> str:
    symbol = value.strip().upper()
    if not re.fullmatch(r"[A-Z]{1,5}(?:[.-][A-Z]{1,2})?", symbol):
        raise ValueError("Use a US stock ticker such as AAPL or BRK-B.")
    return symbol


class Stock(BaseModel):
    symbol: str
    company_name: str | None = None
    exchange: str | None = None
    verified_at: AwareDatetime | None = None

    _symbol = field_validator("symbol")(normalize_symbol)


class SourceSnapshot(BaseModel):
    """Retrieval time is not publication time or a financial reporting period."""

    provider: str
    symbol: str
    source_url: HttpUrl
    retrieved_at: AwareDatetime
    published_on: date | None = None
    payload: dict[str, Any]


class WatchlistInput(BaseModel):
    symbols: list[str] = Field(min_length=5)

    @field_validator("symbols", mode="before")
    @classmethod
    def distinct_symbols(cls, values: list[str]) -> list[str]:
        symbols = [normalize_symbol(value) for value in values]
        if len(set(symbols)) != len(symbols):
            raise ValueError("Select at least five distinct stocks; duplicates found.")
        return symbols
