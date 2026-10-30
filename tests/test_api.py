"""Tests for API client."""

import time
from unittest.mock import Mock, patch

import pytest

from visa_pipeline.api import WikiClient, WikiAPIError


class FakeResponse:
    """Fake requests.Response."""

    def __init__(self, json_data, status_code=200, headers=None):
        self.json_data = json_data
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return self.json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def test_client_user_agent():
    """Test User-Agent header."""
    session = Mock()
    WikiClient(session=session)

    assert "VisaApp-DataPipeline" in session.headers.update.call_args[0][0]["User-Agent"]


def test_client_custom_contact(monkeypatch):
    """Test custom contact in User-Agent."""
    monkeypatch.setenv("VISA_PIPELINE_CONTACT", "test@example.com")

    session = Mock()
    WikiClient(session=session)

    ua = session.headers.update.call_args[0][0]["User-Agent"]
    assert "test@example.com" in ua


def test_category_members():
    """Test category members fetching."""
    session = Mock()
    session.get.return_value = FakeResponse({
        "query": {
            "categorymembers": [
                {"title": "Page 1"},
                {"title": "Page 2"}
            ]
        }
    })

    client = WikiClient(min_interval=0.0, session=session)
    members = client.category_members("Test Category")

    assert members == ["Page 1", "Page 2"]
    assert session.get.call_count == 1


def test_category_members_with_continuation():
    """Test category members with continuation."""
    session = Mock()
    session.get.side_effect = [
        FakeResponse({
            "query": {
                "categorymembers": [{"title": "Page 1"}]
            },
            "continue": {"cmcontinue": "token1"}
        }),
        FakeResponse({
            "query": {
                "categorymembers": [{"title": "Page 2"}]
            }
        })
    ]

    client = WikiClient(min_interval=0.0, session=session)
    members = client.category_members("Test Category")

    assert members == ["Page 1", "Page 2"]
    assert session.get.call_count == 2


def test_revisions():
    """Test revisions fetching."""
    session = Mock()
    session.get.return_value = FakeResponse({
        "query": {
            "pages": [
                {
                    "title": "Page 1",
                    "revisions": [
                        {"revid": 123, "timestamp": "2024-01-01T00:00:00Z"}
                    ]
                }
            ]
        }
    })

    client = WikiClient(min_interval=0.0, session=session)
    revs = client.revisions(["Page 1"])

    assert revs == {
        "Page 1": {"revid": 123, "timestamp": "2024-01-01T00:00:00Z"}
    }


def test_revisions_with_redirect():
    """Test revisions with redirect normalization."""
    session = Mock()
    session.get.return_value = FakeResponse({
        "query": {
            "redirects": [
                {"from": "Page 1", "to": "Page 1 Redirect"}
            ],
            "pages": [
                {
                    "title": "Page 1 Redirect",
                    "revisions": [
                        {"revid": 123, "timestamp": "2024-01-01T00:00:00Z"}
                    ]
                }
            ]
        }
    })

    client = WikiClient(min_interval=0.0, session=session)
    revs = client.revisions(["Page 1"])

    assert "Page 1" in revs
    assert revs["Page 1"]["revid"] == 123


def test_revisions_batching():
    """Test revisions are batched by 50."""
    session = Mock()
    session.get.return_value = FakeResponse({
        "query": {
            "pages": []
        }
    })

    client = WikiClient(min_interval=0.0, session=session)

    # 75 titles should result in 2 calls
    titles = [f"Page {i}" for i in range(75)]
    client.revisions(titles)

    assert session.get.call_count == 2


def test_page_wikitext():
    """Test page wikitext fetching."""
    session = Mock()
    session.get.return_value = FakeResponse({
        "parse": {
            "wikitext": "== Section ==\nContent",
            "revid": 123
        }
    })

    client = WikiClient(min_interval=0.0, session=session)
    wikitext, revid = client.page_wikitext("Test Page")

    assert wikitext == "== Section ==\nContent"
    assert revid == 123


def test_page_wikitext_not_found():
    """Test page wikitext with missing page."""
    session = Mock()
    session.get.return_value = FakeResponse({})

    client = WikiClient(min_interval=0.0, session=session)

    with pytest.raises(WikiAPIError, match="not found"):
        client.page_wikitext("Missing Page")


@patch("time.sleep")
def test_retry_on_429(mock_sleep):
    """Test retry on 429 with Retry-After."""
    session = Mock()
    session.get.side_effect = [
        FakeResponse({}, status_code=429, headers={"Retry-After": "2"}),
        FakeResponse({"query": {"categorymembers": []}})
    ]

    client = WikiClient(min_interval=0.0, session=session)
    client.category_members("Test")

    assert session.get.call_count == 2
    mock_sleep.assert_called()


@patch("time.sleep")
def test_retry_on_500(mock_sleep):
    """Test retry on 5xx with exponential backoff."""
    session = Mock()
    session.get.side_effect = [
        FakeResponse({}, status_code=503),
        FakeResponse({"query": {"categorymembers": []}})
    ]

    client = WikiClient(min_interval=0.0, session=session)
    client.category_members("Test")

    assert session.get.call_count == 2
    mock_sleep.assert_called()


@patch("time.sleep")
def test_retry_on_maxlag(mock_sleep):
    """Test retry on maxlag error with Retry-After."""
    session = Mock()
    session.get.side_effect = [
        FakeResponse({
            "error": {
                "code": "maxlag",
                "info": "Max lag exceeded",
                "lag": 10
            }
        }, headers={"Retry-After": "5"}),
        FakeResponse({"query": {"categorymembers": []}})
    ]

    client = WikiClient(min_interval=0.0, session=session)
    client.category_members("Test")

    assert session.get.call_count == 2
    mock_sleep.assert_called_with(5)


@patch("time.sleep")
def test_max_retries_exhausted(mock_sleep):
    """Test failure after max retries."""
    session = Mock()
    session.get.return_value = FakeResponse({}, status_code=503)

    client = WikiClient(min_interval=0.0, session=session)

    with pytest.raises(WikiAPIError, match="after 5 attempts"):
        client.category_members("Test")

    assert session.get.call_count == 5


def test_rate_limiting():
    """Test rate limiting enforces minimum interval."""
    session = Mock()
    session.get.return_value = FakeResponse({
        "query": {"categorymembers": []}
    })

    client = WikiClient(min_interval=0.1, session=session)

    start = time.time()
    client.category_members("Test1")
    client.category_members("Test2")
    elapsed = time.time() - start

    # Should take at least 0.1 seconds
    assert elapsed >= 0.1
