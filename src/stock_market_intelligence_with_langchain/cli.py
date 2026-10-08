"""M0 commands. No model calls or autonomous actions are performed here."""

import hashlib
from typing import Annotated

import httpx
import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from .config import Settings
from .models import Stock, WatchlistInput
from .providers import ProviderError, YahooProvider
from .sec import SecProvider, available_tags
from .storage import WatchlistRepository

app = typer.Typer(no_args_is_help=True)
watchlist = typer.Typer(no_args_is_help=True)
app.add_typer(watchlist, name="watchlist")
console = Console()


def repository() -> WatchlistRepository:
    return WatchlistRepository(Settings().database_path)


def fail(message: str) -> None:
    console.print(f"Error: {message}", markup=False)
    raise typer.Exit(1)


@app.command()
def init(symbols: Annotated[list[str] | None, typer.Argument()] = None) -> None:
    """Save five or more distinct tickers; run probe to verify their identities."""
    if not symbols:
        symbols = typer.prompt(
            "Enter at least five US stock tickers, separated by spaces"
        ).split()
    try:
        selection = WatchlistInput(symbols=symbols)
    except ValidationError as exc:
        fail(str(exc))
    repository().add([Stock(symbol=symbol) for symbol in selection.symbols])
    console.print("Watchlist saved. New symbols are unverified; run market probe.")


@watchlist.command("add")
def add(symbol: str) -> None:
    """Add a symbol without guessing its identity or changing existing entries."""
    try:
        stock = Stock(symbol=symbol)
    except ValidationError as exc:
        fail(str(exc))
    repository().add([stock])
    console.print(f"Saved {stock.symbol}. Run market probe to verify new entries.")


@watchlist.command("list")
def list_stocks() -> None:
    """Show saved stocks and distinguish syntax checks from verified identity."""
    stocks = repository().list()
    table = Table("Ticker", "Company", "Exchange", "Identity checked (UTC)")
    for stock in stocks:
        table.add_row(
            stock.symbol,
            stock.company_name or "Unverified",
            stock.exchange or "—",
            stock.verified_at.isoformat() if stock.verified_at else "Not yet",
        )
    console.print(table)
    if len(stocks) < 5:
        console.print(
            f"Add {5 - len(stocks)} more distinct stocks to reach the MVP minimum."
        )


@app.command()
def doctor() -> None:
    """Check configuration presence without revealing keys or making requests."""
    settings = Settings()
    checks = [
        (
            "DeepSeek",
            bool(settings.deepseek_api_key.get_secret_value()),
            "DEEPSEEK_API_KEY",
            "LLM reports",
        ),
        (
            "FRED",
            bool(settings.fred_api_key.get_secret_value()),
            "FRED_API_KEY",
            "macro API access",
        ),
        (
            "SEC",
            bool(settings.sec_user_agent.strip()),
            "SEC_USER_AGENT",
            "SEC requests: app name and contact email",
        ),
    ]
    console.print(f"Local database: {settings.database_path.resolve()}", markup=False)
    for name, configured, variable, purpose in checks:
        console.print(
            f"{name}: configured (not tested)"
            if configured
            else f"{name}: set {variable} in .env for {purpose}.",
            markup=False,
        )
    console.print("No credentials are required for the Yahoo coverage probe.")


@app.command()
def probe() -> None:
    """Fetch Yahoo samples and audit field availability; this is not a report."""
    settings = Settings()
    repo = repository()
    stocks = repo.list()
    if len(stocks) < 5:
        fail("Select at least five distinct stocks with market init before probing.")
    cache = settings.market_data_dir / "samples"
    cache.mkdir(parents=True, exist_ok=True)
    fields = {
        "Revenue growth": "revenueGrowth",
        "Operating margin": "operatingMargins",
        "Operating cash flow": "operatingCashflow",
        "Debt": "totalDebt",
        "Trailing P/E": "trailingPE",
    }
    lines = [
        "# Initial Yahoo field coverage",
        "",
        "Presence is not verified accuracy, freshness, or period comparability.",
        "Source publication dates and metric periods are not yet normalized.",
        "Guidance, SEC comparison, industry news, and macro coverage remain unchecked.",
        "",
        "| Ticker | Identity / source status | " + " | ".join(fields) + " |",
        "|---|---|" + "---|" * len(fields),
    ]
    failures = 0
    for stock in stocks:
        console.print(f"Checking {stock.symbol}…")
        try:
            verified, snapshot = YahooProvider().fetch(stock.symbol)
        except ProviderError as exc:
            failures += 1
            status = str(exc)
            cells = ["Unknown"] * len(fields)
        else:
            content = snapshot.model_dump_json(indent=2)
            digest = hashlib.sha256(content.encode()).hexdigest()[:16]
            sample_path = cache / f"{stock.symbol}-{digest}.json"
            sample_path.write_text(content + "\n")
            repo.update(verified)
            status = f"Verified; retrieved {snapshot.retrieved_at.isoformat()}"
            cells = [
                "Present" if snapshot.payload.get(field) is not None else "Missing"
                for field in fields.values()
            ]
        lines.append(f"| {stock.symbol} | {status} | " + " | ".join(cells) + " |")
    output = settings.market_data_dir / "coverage.md"
    output.write_text("\n".join(lines) + "\n")
    console.print(f"Saved {output.resolve()}", markup=False)
    if failures:
        fail(f"{failures} source checks failed; inspect the coverage file.")


@app.command("probe-sec")
def probe_sec() -> None:
    """Cache SEC Company Facts and audit raw tags, without calculating metrics."""
    settings = Settings()
    stocks = repository().list()
    if len(stocks) < 5:
        fail("Select at least five stocks with market init first.")
    failures = 0
    lines = [
        "# SEC source coverage",
        "",
        "Raw tag presence only. Period normalization and calculations are pending.",
        "Debt tags may cover only part of total debt. SEC issuer identity does not verify current exchange listing.",
        "Guidance and segment disclosures require separate filing/release extraction.",
        "",
    ]
    cache = settings.market_data_dir / "samples"
    with httpx.Client() as client:
        try:
            provider = SecProvider(settings.sec_user_agent, client)
        except ProviderError as exc:
            fail(str(exc))
        cache.mkdir(parents=True, exist_ok=True)
        for stock in stocks:
            console.print(f"Checking SEC evidence for {stock.symbol}…")
            lines.extend([f"## {stock.symbol}", ""])
            try:
                snapshot = provider.fetch(stock.symbol)
            except ProviderError as exc:
                failures += 1
                lines.extend([f"Unknown: {exc}", ""])
                continue
            content = snapshot.model_dump_json(indent=2)
            digest = hashlib.sha256(content.encode()).hexdigest()[:16]
            sample = cache / f"{stock.symbol}-sec-{digest}.json"
            sample.write_text(content + "\n")
            lines.extend(
                [
                    f"Source: {snapshot.source_url}",
                    f"Retrieved: {snapshot.retrieved_at.isoformat()}",
                    f"Cached sample: {sample.name}",
                    "",
                    "| Raw data | Coverage |",
                    "|---|---|",
                ]
            )
            lines.extend(
                f"| {key} | {value} |"
                for key, value in available_tags(snapshot).items()
            )
            lines.append("")
    output = settings.market_data_dir / "sec-coverage.md"
    output.write_text("\n".join(lines) + "\n")
    console.print(f"Saved {output.resolve()}", markup=False)
    if failures:
        fail(f"{failures} SEC checks failed; inspect the coverage file.")
