# Stock Market Intelligence with LangChain

A local US stock research CLI and a hands-on agentic engineering project.
M0 foundations are implemented: watchlist storage, configuration checks, and
Yahoo/SEC source probes. Reports and agents are not implemented yet.
See [the implementation plan](IMPLEMENTATION_PLAN.md) for the planned features.

## Environment

Use Python 3.12 and uv. Install the locked runtime and development dependencies:

```sh
uv sync --locked
```

Run commands with `uv run`; manual virtual-environment activation is unnecessary.
`pyproject.toml` declares dependencies, `uv.lock` records resolved versions, and
`.venv` holds the local installation.

Installed runtime dependencies:

- pydantic and pydantic-settings: schemas and configuration
- httpx and yfinance: source access and prototype market data
- typer and rich: CLI commands and terminal presentation
- langchain and langchain-deepseek: model/tool integration
- langgraph and langgraph-checkpoint-sqlite: workflows and local checkpoints

Development tools: pytest and ruff. SQLite is available through Python.
Retrieval/embedding and ingestion extras will be selected at their milestones.

## Credentials

Copy `.env` to `.env` and enter keys locally when live integration begins.
Settings load from `.env` or environment variables. Both `.env` and local data are
ignored by Git. API keys are not required for installation or import checks.

## Development commands

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
```

## M0 commands

Run these from the project root (or set an absolute `MARKET_DATA_DIR`):

```sh
uv run market init INTC NVDA TSLA PLTR MU
uv run market watchlist list
uv run market doctor
uv run market probe
uv run market probe-sec
```

`init` accepts at least five distinct symbols and is additive: it never removes
existing selections. New symbols remain unverified until the Yahoo identity
check succeeds. Formatting validation alone does not establish that a stock exists.
The initial provider supports major US exchanges; other listings are flagged.

`probe` caches successful Yahoo samples and writes `data/coverage.md`. A failed
source request is **unknown coverage**, not an assertion that a metric is absent.
Yahoo may rate-limit requests; do not repeatedly retry a blocked source.

`probe-sec` requires `SEC_USER_AGENT` containing the app name and your contact
email. It resolves tickers to SEC issuers, saves raw Company Facts, and writes
`data/sec-coverage.md`. It audits raw tags, not fully normalized financial metrics
or current exchange listings. SEC provides public data without an API key.

`doctor` reports missing configuration without exposing credentials. It does not
test credential validity. DeepSeek and FRED keys are for subsequent milestones.

Watchlist records live in `data/market.sqlite3`; source samples live in
`data/samples`. These files are ignored by Git. See
[M0 learning notes](docs/M0_LEARNING.md) for the design and current limitations.
