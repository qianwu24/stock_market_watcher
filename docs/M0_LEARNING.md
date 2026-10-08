# M0: foundations and source feasibility

## What to learn here

Before an agent chooses a tool, its inputs and outputs need reliable contracts.
This milestone makes those boundaries concrete without calling an LLM.

1. **Schemas:** `models.py` uses Pydantic to reject invalid symbols and duplicate
   onboarding selections. Valid syntax does not establish company identity.
2. **Separation of responsibilities:** `cli.py` handles terminal interaction;
   `storage.py` owns SQLite; `providers.py` and `sec.py` own external-source access.
   A future agent tool can reuse provider behavior without invoking the CLI.
3. **Provider interfaces:** `StockProvider` describes a capability with a Python
   Protocol. Yahoo implements it structurally; SEC has a different evidence
   contract because issuer filings do not establish current exchange membership.
4. **Provenance:** `SourceSnapshot` keeps raw evidence, provider, URL, and an aware
   retrieval timestamp. Publication date stays unknown when the source does not
   provide one. Retrieval time must never stand in for a reporting period.
5. **Persistence:** SQLite retains user selections across CLI processes. A unique
   symbol prevents duplicates, and adding again preserves verified identity.
6. **Operational uncertainty:** A rate limit means “we could not check,” not “the
   company has no debt.” Missing, unknown, and present are different states.
7. **Testing external boundaries:** Mock sources to test wrong identities, source
   outages, and access denials without spending tokens or hitting live endpoints.

## Current live result

On 8 October 2026, the user selected INTC, NVDA, TSLA, PLTR, and MU. All five
Yahoo source requests returned YFRateLimitError in this environment. The watchlist
is saved, but Yahoo company identity remains unverified. See the local coverage
artifact for actual results; offline passing tests do not prove live access.

The SEC collector is implemented and tested with mock HTTP responses. Its live
check requires the user's configured SEC contact header. The Yahoo-versus-filing
comparison remains pending until both sets of evidence are available. We have
not completed the M0 exit criteria or started M1 report generation.

## Try it yourself

- Run `uv run market watchlist list` and locate the verification status.
- Run `uv run market init NVDA nvda MU INTC TSLA`. Explain why it fails even though
  there are five arguments. Confirm the existing watchlist was not changed.
- Read `SourceSnapshot`: why are `published_on` and `retrieved_at` separate?
- Inspect the mocked SEC test. A numeric value of zero still counts as present;
  explain why checking `if value` would be a bug.

## First report contract (M1 example, not real research)

```text
As of: <cutoff and timezone>
New developments: <dated observations with source IDs>
Company: <verified issuer and ticker>
Revenue growth: <value, formula, comparable periods, source IDs or unavailable>
Margins / cash flow / debt / valuation: <same explicit evidence requirements>
Guidance: <management statement and publication date or unavailable>
Industry and macro context: <evidence plus separately labeled interpretation>
Coverage gaps: <missing, stale, or inaccessible sources>
References: <source IDs, URLs, publication/retrieval dates>
```

## Initial evaluation questions

These need evidence-backed answer keys after collection, not model guesses:

1. What is each company's latest available revenue reporting period?
2. Are two revenue figures comparable in duration, currency, and publication cutoff?
3. Can operating cash flow be compared directly across these source records?
4. Which debt components are included, and what is still missing?
5. Does the corpus contain management guidance, or just analyst estimates?
6. Does an unavailable Yahoo response justify saying a metric is absent? (No.)
7. Can a source published after a report cutoff support that historical report? (No.)
8. Can today's retrieved data answer a question about tomorrow's price? (No.)

## Remaining M0 work

- Configure SEC contact, run live collection, and inspect raw source samples.
- Resolve accessible pricing/fundamental snapshot coverage if Yahoo remains blocked.
- Compare one matching reported metric across sources with dates and units.
- Complete the five-stock coverage matrix, including explicit guidance/news/macro
  gaps; prepare reusable cached demonstration inputs and answer keys.

Sources: [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces),
[SEC access guidelines](https://www.sec.gov/about/developer-resources),
[yfinance Ticker reference](https://ranaroussi.github.io/yfinance/reference/api/yfinance.Ticker.html).
