"""Wikipedia MediaWiki API client."""

import os
import time
import random
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any

import requests


class WikiAPIError(Exception):
    """Wikipedia API error."""
    pass


MAX_RETRY_DELAY = 120.0


def parse_retry_after(value: str | None, default: float = 0.0) -> float:
    """Parse a Retry-After header (delta-seconds or HTTP-date), capped at MAX_RETRY_DELAY.

    Unparseable or missing values give ``default`` (also capped).
    """
    delay = default
    if value is not None:
        value = str(value).strip()
        try:
            delay = float(value)
        except ValueError:
            try:
                when = parsedate_to_datetime(value)
                if when.tzinfo is None:
                    when = when.replace(tzinfo=timezone.utc)
                delay = (when - datetime.now(timezone.utc)).total_seconds()
            except (TypeError, ValueError):
                delay = default
    return max(0.0, min(delay, MAX_RETRY_DELAY))


class WikiClient:
    """MediaWiki API client with rate limiting and retry logic."""

    API_URL = "https://en.wikipedia.org/w/api.php"
    MAX_RETRIES = 5

    def __init__(self, min_interval: float = 1.0, session: requests.Session | None = None):
        """
        Initialize the client.

        Args:
            min_interval: Minimum seconds between requests
            session: Optional requests.Session (for testing)
        """
        self.min_interval = min_interval
        self.session = session or requests.Session()
        self.last_request_time = 0.0

        # Set User-Agent
        contact = os.environ.get(
            "VISA_PIPELINE_CONTACT",
            "https://github.com/Riedel-David/Visa-requirements"
        )
        self.session.headers.update({
            "User-Agent": f"VisaApp-DataPipeline/0.1.0 ({contact})",
            "Accept-Encoding": "gzip"
        })

    def _wait_for_rate_limit(self) -> None:
        """Enforce minimum interval between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_time = time.time()

    def _request(self, params: dict[str, Any]) -> dict[str, Any]:
        """
        Make an API request with retry logic.

        Args:
            params: API parameters

        Returns:
            API response dict

        Raises:
            WikiAPIError: After all retries exhausted
        """
        params = {
            **params,
            "format": "json",
            "formatversion": "2",
            "maxlag": "5"
        }

        for attempt in range(self.MAX_RETRIES):
            self._wait_for_rate_limit()

            try:
                response = self.session.get(self.API_URL, params=params, timeout=30)

                # Check for rate limiting
                if response.status_code == 429:
                    retry_after = parse_retry_after(response.headers.get("Retry-After"), 60)
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(retry_after)
                        continue
                    raise WikiAPIError(f"Rate limited after {self.MAX_RETRIES} attempts")

                # Check for server errors
                if response.status_code >= 500:
                    retry_after = parse_retry_after(response.headers.get("Retry-After"), 0)
                    if attempt < self.MAX_RETRIES - 1:
                        delay = retry_after if retry_after > 0 else (2 ** attempt + random.uniform(0, 1))
                        time.sleep(delay)
                        continue
                    raise WikiAPIError(f"Server error {response.status_code} after {self.MAX_RETRIES} attempts")

                response.raise_for_status()
                try:
                    data = response.json()
                except ValueError:
                    # 200 with a non-JSON body (proxy/error page): retry, bounded
                    if attempt < self.MAX_RETRIES - 1:
                        time.sleep(2 ** attempt + random.uniform(0, 1))
                        continue
                    raise WikiAPIError(
                        f"Non-JSON response after {self.MAX_RETRIES} attempts")

                # Check for maxlag error
                if "error" in data:
                    if data["error"].get("code") == "maxlag":
                        if attempt < self.MAX_RETRIES - 1:
                            # Calculate delay based on lag if provided
                            lag = data["error"].get("lag", 5)
                            retry_after = parse_retry_after(response.headers.get("Retry-After"), lag)
                            time.sleep(retry_after)
                            continue
                        raise WikiAPIError(f"Max lag exceeded after {self.MAX_RETRIES} attempts")
                    raise WikiAPIError(f"API error: {data['error'].get('info', data['error'])}")

                return data

            except (requests.ConnectionError, requests.Timeout) as e:
                if attempt < self.MAX_RETRIES - 1:
                    delay = 2 ** attempt + random.uniform(0, 1)
                    time.sleep(delay)
                    continue
                raise WikiAPIError(f"Connection failed after {self.MAX_RETRIES} attempts: {e}")

        raise WikiAPIError(f"Request failed after {self.MAX_RETRIES} attempts")

    def category_members(
        self,
        category: str,
        namespace: int = 0
    ) -> list[str]:
        """
        Get all members of a category, following continuation.

        Args:
            category: Category name (with or without "Category:" prefix)
            namespace: Namespace filter (0=articles, 14=categories)

        Returns:
            List of page titles
        """
        if not category.startswith("Category:"):
            category = f"Category:{category}"

        members = []
        params: dict[str, Any] = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category,
            "cmnamespace": namespace,
            "cmlimit": "max"
        }

        while True:
            data = self._request(params)

            if "query" not in data or "categorymembers" not in data["query"]:
                break

            members.extend([m["title"] for m in data["query"]["categorymembers"]])

            if "continue" not in data:
                break

            params.update(data["continue"])

        return members

    def revisions(self, titles: list[str]) -> dict[str, dict[str, Any]]:
        """
        Get latest revision info for pages, batched by 50.

        Args:
            titles: List of page titles

        Returns:
            Dict mapping title to {revid, timestamp}, with redirect normalization
        """
        result = {}

        # Process in batches of 50
        for i in range(0, len(titles), 50):
            batch = titles[i:i+50]

            params = {
                "action": "query",
                "titles": "|".join(batch),
                "prop": "revisions",
                "rvprop": "ids|timestamp",
                "rvslots": "main",
                "redirects": "1"
            }

            data = self._request(params)

            if "query" not in data:
                continue

            # Handle normalized titles
            normalized = {}
            if "normalized" in data["query"]:
                for norm in data["query"]["normalized"]:
                    normalized[norm["from"]] = norm["to"]

            # Handle redirects
            redirects = {}
            if "redirects" in data["query"]:
                for redir in data["query"]["redirects"]:
                    redirects[redir["from"]] = redir["to"]

            # Process pages
            if "pages" in data["query"]:
                for page in data["query"]["pages"]:
                    if "missing" in page:
                        continue

                    if "revisions" not in page or not page["revisions"]:
                        continue

                    rev = page["revisions"][0]
                    info = {
                        "revid": rev["revid"],
                        "timestamp": rev["timestamp"]
                    }

                    # Map back through redirects and normalizations
                    title = page["title"]

                    # Find original titles that map to this page
                    for orig_title in batch:
                        final_title = orig_title

                        # Apply normalization
                        if final_title in normalized:
                            final_title = normalized[final_title]

                        # Apply redirect
                        if final_title in redirects:
                            final_title = redirects[final_title]

                        if final_title == title:
                            result[orig_title] = info

        return result

    def page_wikitext(self, title: str) -> tuple[str, int]:
        """
        Get page wikitext and revision ID.

        Args:
            title: Page title

        Returns:
            Tuple of (wikitext, revid)

        Raises:
            WikiAPIError: If page not found or parse fails
        """
        params = {
            "action": "parse",
            "page": title,
            "prop": "wikitext|revid"
        }

        data = self._request(params)

        if "parse" not in data:
            raise WikiAPIError(f"Page not found: {title}")

        parse = data["parse"]
        wikitext = parse["wikitext"]
        revid = parse["revid"]

        return wikitext, revid
