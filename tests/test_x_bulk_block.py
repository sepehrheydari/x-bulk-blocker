"""
Integration tests for fetch_tweet_authors and bulk_block.
HTTP is mocked via respx so no real network calls are made.
"""
import json
import time
from typing import Optional
from unittest.mock import patch

import httpx
import pytest
import respx

from x_bulk_block import (
    _LIST_TIMELINE_URL,
    bulk_block,
    fetch_tweet_authors,
    run_job,
)

_BLOCK_URL = "https://x.com/i/api/1.1/blocks/create.json"
_COOKIE_STR = "auth_token=faketoken; ct0=fakect0"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_entry(username: str, user_id: str) -> dict:
    """Build a minimal GraphQL tweet-entry matching the parser's expected shape."""
    return {
        "entryId": f"tweet-{user_id}",
        "content": {
            "itemContent": {
                "tweet_results": {
                    "result": {
                        "core": {
                            "user_results": {
                                "result": {
                                    "rest_id": user_id,
                                    "legacy": {
                                        "screen_name": username,
                                        "id_str": user_id,
                                    },
                                }
                            }
                        }
                    }
                }
            }
        },
    }


def _make_cursor_entry(cursor_id: str, position: str = "bottom") -> dict:
    return {
        "entryId": f"cursor-{position}-{cursor_id}",
        "content": {"value": cursor_id},
    }


def _make_timeline_response(entries: list, cursor: Optional[str] = None) -> dict:
    all_entries = list(entries)
    if cursor:
        all_entries.append(_make_cursor_entry(cursor))
    return {
        "data": {
            "list": {
                "tweets_timeline": {
                    "timeline": {
                        "instructions": [{"entries": all_entries}]
                    }
                }
            }
        }
    }


def _make_client(cookie_str: str = _COOKIE_STR) -> httpx.Client:
    from x_bulk_block import _parse_cookies, _BEARER
    cookies = _parse_cookies(cookie_str)
    ct0 = cookies.get("ct0", "")
    return httpx.Client(
        headers={"Authorization": _BEARER, "x-csrf-token": ct0},
        cookies=cookies,
        verify=True,
    )


# ── fetch_tweet_authors ────────────────────────────────────────────────────────

class TestFetchTweetAuthors:
    @respx.mock
    def test_single_page_returns_authors(self):
        entries = [_make_entry("alice", "111"), _make_entry("bob", "222")]
        respx.get(_LIST_TIMELINE_URL).mock(
            return_value=httpx.Response(200, json=_make_timeline_response(entries))
        )
        logs = []
        with _make_client() as client:
            result = fetch_tweet_authors("123", client, log=logs.append)

        assert result == {"alice": "111", "bob": "222"}
        assert any("2 new author" in m for m in logs)

    @respx.mock
    def test_duplicate_users_deduplicated(self):
        entries = [_make_entry("alice", "111"), _make_entry("alice", "111")]
        respx.get(_LIST_TIMELINE_URL).mock(
            return_value=httpx.Response(200, json=_make_timeline_response(entries))
        )
        with _make_client() as client:
            result = fetch_tweet_authors("123", client)

        assert len(result) == 1
        assert result["alice"] == "111"

    @respx.mock
    def test_pagination_follows_cursor(self):
        page1_entries = [_make_entry("alice", "111")]
        page2_entries = [_make_entry("bob", "222")]

        route = respx.get(_LIST_TIMELINE_URL)
        route.side_effect = [
            httpx.Response(200, json=_make_timeline_response(page1_entries, cursor="next_cursor_abc")),
            httpx.Response(200, json=_make_timeline_response(page2_entries)),
        ]

        with _make_client() as client:
            result = fetch_tweet_authors("123", client)

        assert "alice" in result
        assert "bob" in result
        assert route.call_count == 2

    @respx.mock
    def test_stops_when_cursor_repeats(self):
        entries = [_make_entry("alice", "111")]
        route = respx.get(_LIST_TIMELINE_URL)
        # Second page returns the same cursor — should stop after 2 calls
        route.side_effect = [
            httpx.Response(200, json=_make_timeline_response(entries, cursor="repeat")),
            httpx.Response(200, json=_make_timeline_response([], cursor="repeat")),
        ]
        with _make_client() as client:
            result = fetch_tweet_authors("123", client)

        assert result == {"alice": "111"}

    @respx.mock
    def test_empty_list_returns_empty_dict(self):
        respx.get(_LIST_TIMELINE_URL).mock(
            return_value=httpx.Response(200, json=_make_timeline_response([]))
        )
        with _make_client() as client:
            result = fetch_tweet_authors("123", client)

        assert result == {}

    @respx.mock
    def test_401_raises_runtime_error(self):
        respx.get(_LIST_TIMELINE_URL).mock(return_value=httpx.Response(401))
        with _make_client() as client:
            with pytest.raises(RuntimeError, match="HTTP 401"):
                fetch_tweet_authors("123", client)

    @respx.mock
    def test_rate_limit_then_success_retries(self):
        entries = [_make_entry("alice", "111")]
        route = respx.get(_LIST_TIMELINE_URL)
        route.side_effect = [
            httpx.Response(429),
            httpx.Response(200, json=_make_timeline_response(entries)),
        ]
        logs = []
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                result = fetch_tweet_authors("123", client, log=logs.append)

        assert result == {"alice": "111"}
        assert any("rate limit" in m.lower() for m in logs)

    @respx.mock
    def test_rate_limit_then_error_raises(self):
        route = respx.get(_LIST_TIMELINE_URL)
        route.side_effect = [httpx.Response(429), httpx.Response(403)]
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                with pytest.raises(RuntimeError, match="HTTP 403"):
                    fetch_tweet_authors("123", client)

    @respx.mock
    def test_usernames_lowercased(self):
        entries = [_make_entry("MixedCase", "999")]
        respx.get(_LIST_TIMELINE_URL).mock(
            return_value=httpx.Response(200, json=_make_timeline_response(entries))
        )
        with _make_client() as client:
            result = fetch_tweet_authors("123", client)

        assert "mixedcase" in result


# ── bulk_block ────────────────────────────────────────────────────────────────

class TestBulkBlock:
    @respx.mock
    def test_successful_blocks_logged(self):
        respx.post(_BLOCK_URL).mock(return_value=httpx.Response(200, json={}))
        logs = []
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                bulk_block(client, {"alice": "111", "bob": "222"}, log=logs.append)

        assert any("BLOCKED" in m and "alice" in m for m in logs)
        assert any("BLOCKED" in m and "bob" in m for m in logs)
        assert any("2 blocked" in m for m in logs)

    @respx.mock
    def test_already_blocked_skipped(self):
        respx.post(_BLOCK_URL).mock(return_value=httpx.Response(403, json={}))
        logs = []
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                bulk_block(client, {"alice": "111"}, log=logs.append)

        assert any("SKIPPED" in m for m in logs)
        assert any("0 blocked" in m and "1 skipped" in m for m in logs)

    @respx.mock
    def test_404_skipped(self):
        respx.post(_BLOCK_URL).mock(return_value=httpx.Response(404, json={}))
        logs = []
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                bulk_block(client, {"ghost": "404"}, log=logs.append)

        assert any("SKIPPED" in m for m in logs)

    @respx.mock
    def test_server_error_counted_as_failed(self):
        respx.post(_BLOCK_URL).mock(return_value=httpx.Response(500, json={}))
        logs = []
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                bulk_block(client, {"baduser": "500"}, log=logs.append)

        assert any("FAILED" in m for m in logs)
        assert any("1 failed" in m for m in logs)

    @respx.mock
    def test_rate_limit_retries_and_succeeds(self):
        route = respx.post(_BLOCK_URL)
        route.side_effect = [
            httpx.Response(429, json={}),
            httpx.Response(200, json={}),
        ]
        logs = []
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                bulk_block(client, {"alice": "111"}, log=logs.append)

        assert any("RATE LIMITED" in m for m in logs)
        assert any("BLOCKED (retry)" in m for m in logs)

    @respx.mock
    def test_rate_limit_retry_fails_counted(self):
        route = respx.post(_BLOCK_URL)
        route.side_effect = [
            httpx.Response(429, json={}),
            httpx.Response(500, json={}),
        ]
        logs = []
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                bulk_block(client, {"alice": "111"}, log=logs.append)

        assert any("FAILED after retry" in m for m in logs)

    @respx.mock
    def test_network_error_counted_as_failed(self):
        respx.post(_BLOCK_URL).mock(side_effect=httpx.ConnectError("timeout"))
        logs = []
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                bulk_block(client, {"alice": "111"}, log=logs.append)

        assert any("FAILED (network" in m for m in logs)

    @respx.mock
    def test_done_summary_line_always_emitted(self):
        respx.post(_BLOCK_URL).mock(return_value=httpx.Response(200, json={}))
        logs = []
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                bulk_block(client, {"alice": "111"}, log=logs.append)

        assert any("[DONE]" in m for m in logs)


# ── run_job ───────────────────────────────────────────────────────────────────

class TestRunJob:
    def test_missing_auth_token_raises(self):
        with pytest.raises(RuntimeError, match="auth_token missing"):
            run_job("123", "ct0=xyz")

    def test_missing_ct0_raises(self):
        with pytest.raises(RuntimeError, match="ct0 missing"):
            run_job("123", "auth_token=xyz")

    @respx.mock
    def test_dry_run_does_not_call_block_url(self):
        block_route = respx.post(_BLOCK_URL)
        entries = [_make_entry("alice", "111")]
        respx.get(_LIST_TIMELINE_URL).mock(
            return_value=httpx.Response(200, json=_make_timeline_response(entries))
        )
        logs = []
        run_job("123", _COOKIE_STR, dry_run=True, log=logs.append)

        assert not block_route.called
        assert any("DRY-RUN" in m for m in logs)
        assert any("[DONE]" in m for m in logs)

    @respx.mock
    def test_empty_list_exits_early(self):
        block_route = respx.post(_BLOCK_URL)
        respx.get(_LIST_TIMELINE_URL).mock(
            return_value=httpx.Response(200, json=_make_timeline_response([]))
        )
        logs = []
        run_job("123", _COOKIE_STR, log=logs.append)

        assert not block_route.called
        assert any("Nothing to do" in m for m in logs)

    @respx.mock
    def test_full_block_run_end_to_end(self):
        entries = [_make_entry("alice", "111"), _make_entry("bob", "222")]
        respx.get(_LIST_TIMELINE_URL).mock(
            return_value=httpx.Response(200, json=_make_timeline_response(entries))
        )
        respx.post(_BLOCK_URL).mock(return_value=httpx.Response(200, json={}))

        logs = []
        with patch("x_bulk_block.time.sleep"):
            run_job("123", _COOKIE_STR, dry_run=False, log=logs.append)

        assert any("BLOCKED" in m and "alice" in m for m in logs)
        assert any("BLOCKED" in m and "bob" in m for m in logs)
        assert any("[DONE]" in m for m in logs)
