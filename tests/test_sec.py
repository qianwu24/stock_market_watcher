import httpx
import pytest

from stock_market_intelligence_with_langchain.providers import ProviderError
from stock_market_intelligence_with_langchain.sec import SecProvider, available_tags


def test_sec_resolves_identity_and_preserves_source_metadata():
    def handler(request):
        assert request.headers["User-Agent"] == "Test test@example.com"
        if request.url.path.endswith("company_tickers.json"):
            return httpx.Response(
                200, json={"0": {"ticker": "NVDA", "cik_str": 1045810}}
            )
        assert request.url.path.endswith("CIK0001045810.json")
        return httpx.Response(
            200,
            json={
                "cik": 1045810,
                "facts": {
                    "us-gaap": {
                        "OperatingIncomeLoss": {
                            "units": {
                                "USD": [
                                    {
                                        "val": 0,
                                        "end": "2025-01-31",
                                        "filed": "2025-03-01",
                                    }
                                ]
                            }
                        }
                    }
                },
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        snapshot = SecProvider("Test test@example.com", client).fetch("NVDA")
    assert snapshot.symbol == "NVDA"
    assert snapshot.published_on is None
    assert snapshot.retrieved_at.tzinfo is not None
    coverage = available_tags(snapshot)
    assert "2025-01-31" in coverage["Operating income"]
    assert coverage["Revenue"] == "No supported tag found"


def test_sec_access_denied_is_explicit():
    with (
        httpx.Client(
            transport=httpx.MockTransport(lambda request: httpx.Response(403))
        ) as client,
        pytest.raises(ProviderError, match="403"),
    ):
        SecProvider("Test test@example.com", client).fetch("NVDA")


def test_missing_sec_contact_fails_before_network():
    def unexpected(request):
        pytest.fail("Missing configuration must not make a network request")

    with (
        httpx.Client(transport=httpx.MockTransport(unexpected)) as client,
        pytest.raises(ProviderError, match="SEC_USER_AGENT"),
    ):
        SecProvider("", client)
