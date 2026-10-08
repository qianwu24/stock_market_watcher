"""Small SQLite repository; the CLI need not know SQL."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from .models import Stock


class WatchlistRepository:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(path)) as connection, connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS stocks "
                "(symbol TEXT PRIMARY KEY, record TEXT NOT NULL)"
            )

    def list(self) -> list[Stock]:
        with closing(sqlite3.connect(self.path)) as connection:
            rows = connection.execute("SELECT record FROM stocks ORDER BY symbol")
            return [Stock.model_validate_json(row[0]) for row in rows]

    def add(self, stocks: list[Stock]) -> None:
        # Existing verified identity must survive repeated 'add' calls.
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.executemany(
                "INSERT OR IGNORE INTO stocks (symbol, record) VALUES (?, ?)",
                [(stock.symbol, stock.model_dump_json()) for stock in stocks],
            )

    def update(self, stock: Stock) -> None:
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.execute(
                "UPDATE stocks SET record = ? WHERE symbol = ?",
                (stock.model_dump_json(), stock.symbol),
            )
