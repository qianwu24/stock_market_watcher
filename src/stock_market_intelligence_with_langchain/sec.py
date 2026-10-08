"""SEC evidence collection for the M0 coverage experiment."""

import time
from datetime import UTC, datetime

import httpx

from .models import SourceSnapshot, normalize_symbol
from .providers import ProviderError


class SecProvider:
    def __init__(self, user_agent: str, client: httpx.Client):
        if "@" not in user_agent:
            raise ProviderError(
                "Set SEC_USER_AGENT to an app name and contact email in .env."
            )
        self.client = client
        self.headers = {"User-Agent": user_agent, "Accept": "application/json"}
        self.catalog: dict | None = None
        self.last_request = 0.0

    def _get(self, url: str) -> dict:
        # Sequential M0 collector: at most five requests/second in this instance.
        time.sleep(max(0, 0.2 - (time.monotonic() - self.last_request)))
        self.last_request = time.monotonic()
        try:
            response = self.client.get(url, headers=self.headers, timeout=20)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            status = (
                exc.response.status_code
                if isinstance(exc, httpx.HTTPStatusError)
                else type(exc).__name__
            )
            raise ProviderError(f"SEC request failed ({status}).") from exc
        if not isinstance(payload, dict):
            raise ProviderError("SEC returned an unexpected response shape.")
        return payload

    def fetch(self, symbol: str) -> SourceSnapshot:
        symbol = normalize_symbol(symbol)
        if self.catalog is None:
            self.catalog = self._get("https://www.sec.gov/files/company_tickers.json")
        matches = [
            entry for entry in self.catalog.values() if entry.get("ticker") == symbol
        ]
        if len(matches) != 1:
            raise ProviderError("Ticker did not resolve uniquely in the SEC catalog.")
        cik = int(matches[0]["cik_str"])
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
        payload = self._get(url)
        if int(payload.get("cik", -1)) != cik:
            raise ProviderError("SEC response did not match the requested issuer.")
        return SourceSnapshot(
            provider="sec_companyfacts",
            symbol=symbol,
            source_url=url,
            retrieved_at=datetime.now(UTC),
            payload=payload,
        )


def available_tags(snapshot: SourceSnapshot) -> dict[str, str]:
    """Presence audit only: never imply periods or metrics are normalized."""
    facts = snapshot.payload.get("facts", {}).get("us-gaap", {})
    groups = {
        "Revenue": [
            "RevenueFromContractWithCustomerExcludingAssessedTax",
            "Revenues",
            "SalesRevenueNet",
        ],
        "Operating income": ["OperatingIncomeLoss"],
        "Operating cash flow": ["NetCashProvidedByUsedInOperatingActivities"],
        "Debt components": [
            "LongTermDebtCurrent",
            "LongTermDebtNoncurrent",
            "LongTermDebt",
            "ShortTermBorrowings",
        ],
        "EPS": ["EarningsPerShareDiluted"],
    }
    result = {}
    for label, tags in groups.items():
        dated = [
            value
            for tag in tags
            for values in facts.get(tag, {}).get("units", {}).values()
            for value in values
            if value.get("filed") and value.get("end") and value.get("val") is not None
        ]
        latest = max(
            dated, key=lambda value: (value["end"], value["filed"]), default=None
        )
        result[label] = (
            f"Found; period end {latest['end']}; filed {latest['filed']}"
            if latest
            else "No supported tag found"
        )
    return result
