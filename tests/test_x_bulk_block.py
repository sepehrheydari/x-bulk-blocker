"""
Integration tests for fetch_tweet_authors, fetch_list_members, and bulk_block.
HTTP is mocked via respx so no real network calls are made.
"""
import json
import time
from typing import Optional
from unittest.mock import patch

import httpx
import pytest
import respx

import x_bulk_block
from x_bulk_block import (
    _LIST_TIMELINE_URL,
    bulk_block,
    fetch_list_members,
    fetch_tweet_authors,
    run_job,
)


@pytest.fixture(autouse=True)
def clear_query_id_cache():
    """Reset the in-memory query ID cache between tests."""
    x_bulk_block._query_id_cache.clear()
    yield
    x_bulk_block._query_id_cache.clear()

_BLOCK_URL = "https://x.com/i/api/1.1/blocks/create.json"
_BLOCKS_IDS_URL = "https://x.com/i/api/1.1/blocks/ids.json"

# Patch _fetch_blocked_ids to return empty set in all bulk_block tests
# (dedicated test below covers the pre-filter branch separately)
_no_existing_blocks = patch("x_bulk_block._fetch_blocked_ids", return_value=set())
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
    @_no_existing_blocks
    @respx.mock
    def test_successful_blocks_logged(self, _mock_fetch):
        respx.post(_BLOCK_URL).mock(return_value=httpx.Response(200, json={}))
        logs = []
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                bulk_block(client, {"alice": "111", "bob": "222"}, log=logs.append)

        assert any("BLOCKED" in m and "alice" in m for m in logs)
        assert any("BLOCKED" in m and "bob" in m for m in logs)
        assert any("2 blocked" in m for m in logs)

    @_no_existing_blocks
    @respx.mock
    def test_already_blocked_skipped(self, _mock_fetch):
        respx.post(_BLOCK_URL).mock(return_value=httpx.Response(403, json={}))
        logs = []
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                bulk_block(client, {"alice": "111"}, log=logs.append)

        assert any("SKIPPED" in m for m in logs)
        assert any("0 blocked" in m and "1 skipped" in m for m in logs)

    @_no_existing_blocks
    @respx.mock
    def test_404_skipped(self, _mock_fetch):
        respx.post(_BLOCK_URL).mock(return_value=httpx.Response(404, json={}))
        logs = []
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                bulk_block(client, {"ghost": "404"}, log=logs.append)

        assert any("SKIPPED" in m for m in logs)

    @_no_existing_blocks
    @respx.mock
    def test_server_error_counted_as_failed(self, _mock_fetch):
        respx.post(_BLOCK_URL).mock(return_value=httpx.Response(500, json={}))
        logs = []
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                bulk_block(client, {"baduser": "500"}, log=logs.append)

        assert any("FAILED" in m for m in logs)
        assert any("1 failed" in m for m in logs)

    @_no_existing_blocks
    @respx.mock
    def test_rate_limit_retries_and_succeeds(self, _mock_fetch):
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
        assert any("BLOCKED" in m for m in logs)

    @_no_existing_blocks
    @respx.mock
    def test_rate_limit_retry_fails_counted(self, _mock_fetch):
        route = respx.post(_BLOCK_URL)
        route.side_effect = [
            httpx.Response(429, json={}),
            httpx.Response(500, json={}),
        ]
        logs = []
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                bulk_block(client, {"alice": "111"}, log=logs.append)

        assert any("FAILED" in m for m in logs)

    @_no_existing_blocks
    @respx.mock
    def test_401_mid_run_aborts_with_resume_hint(self, _mock_fetch):
        route = respx.post(_BLOCK_URL)
        route.side_effect = [
            httpx.Response(200, json={}),
            httpx.Response(401, json={}),
        ]
        logs = []
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                bulk_block(client, {"alice": "111", "bob": "222"}, log=logs.append)

        assert any("SESSION EXPIRED" in m for m in logs)
        assert any("Refresh your cookies" in m for m in logs)
        # summary still emitted
        assert any("[DONE]" in m for m in logs)

    @_no_existing_blocks
    @respx.mock
    def test_network_error_counted_as_failed(self, _mock_fetch):
        respx.post(_BLOCK_URL).mock(side_effect=httpx.ConnectError("timeout"))
        logs = []
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                bulk_block(client, {"alice": "111"}, log=logs.append)

        assert any("FAILED (network" in m for m in logs)

    @_no_existing_blocks
    @respx.mock
    def test_done_summary_line_always_emitted(self, _mock_fetch):
        respx.post(_BLOCK_URL).mock(return_value=httpx.Response(200, json={}))
        logs = []
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                bulk_block(client, {"alice": "111"}, log=logs.append)

        assert any("[DONE]" in m for m in logs)


# ── fetch_list_members ───────────────────────────────────────────────────────

_MAIN_URL = "https://x.com/"
_BUNDLE_URL = "https://abs.twimg.com/responsive-web/client-web/main.abc123.js"
_TEST_QUERY_ID = "TEST_QID_MEMBERS"
_LIST_MEMBERS_URL = f"https://x.com/i/api/graphql/{_TEST_QUERY_ID}/ListMembers"
_BUNDLE_JS = f'...queryId:"{_TEST_QUERY_ID}",operationName:"ListMembers"...'


def _make_member_entry(username: str, user_id: str) -> dict:
    """Build a minimal ListMembers GraphQL entry."""
    return {
        "entryId": f"user-{user_id}",
        "content": {
            "itemContent": {
                "user_results": {
                    "result": {
                        "rest_id": user_id,
                        "legacy": {"screen_name": username, "id_str": user_id},
                    }
                }
            }
        },
    }


def _make_members_response(entries: list, cursor: Optional[str] = None) -> dict:
    all_entries = list(entries)
    if cursor:
        all_entries.append({
            "entryId": f"cursor-bottom-{cursor}",
            "content": {"value": cursor},
        })
    return {
        "data": {
            "list": {
                "members_timeline": {
                    "timeline": {
                        "instructions": [{"entries": all_entries}]
                    }
                }
            }
        }
    }


def _mock_discovery():
    """Register respx mocks for the JS bundle discovery flow."""
    respx.get(_MAIN_URL).mock(return_value=httpx.Response(
        200, text=f'<html><script src="{_BUNDLE_URL}"></script></html>'
    ))
    respx.get(_BUNDLE_URL).mock(return_value=httpx.Response(200, text=_BUNDLE_JS))


class TestFetchListMembers:
    @respx.mock
    def test_returns_all_members_single_page(self):
        _mock_discovery()
        entries = [_make_member_entry("Alice", "111"), _make_member_entry("Bob", "222")]
        respx.get(_LIST_MEMBERS_URL).mock(
            return_value=httpx.Response(200, json=_make_members_response(entries))
        )
        with _make_client() as client:
            result = fetch_list_members("123", client)
        assert result == {"alice": "111", "bob": "222"}

    @respx.mock
    def test_paginates_to_second_page(self):
        _mock_discovery()
        route = respx.get(_LIST_MEMBERS_URL)
        route.side_effect = [
            httpx.Response(200, json=_make_members_response(
                [_make_member_entry("alice", "111")], cursor="next"
            )),
            httpx.Response(200, json=_make_members_response(
                [_make_member_entry("bob", "222")]
            )),
        ]
        with _make_client() as client:
            result = fetch_list_members("123", client)
        assert result == {"alice": "111", "bob": "222"}
        assert route.call_count == 2

    @respx.mock
    def test_deduplicates_members(self):
        _mock_discovery()
        entries = [_make_member_entry("alice", "111"), _make_member_entry("Alice", "111")]
        respx.get(_LIST_MEMBERS_URL).mock(
            return_value=httpx.Response(200, json=_make_members_response(entries))
        )
        with _make_client() as client:
            result = fetch_list_members("123", client)
        assert len(result) == 1

    @respx.mock
    def test_uses_cached_query_id_on_second_call(self):
        _mock_discovery()
        respx.get(_LIST_MEMBERS_URL).mock(
            return_value=httpx.Response(200, json=_make_members_response(
                [_make_member_entry("alice", "111")]
            ))
        )
        with _make_client() as client:
            fetch_list_members("123", client)
            fetch_list_members("456", client)
        # main page and bundle each fetched only once (cached after first call)
        assert respx.calls.call_count == 4  # discovery×2 + members×2

    @respx.mock
    def test_401_raises_runtime_error(self):
        _mock_discovery()
        respx.get(_LIST_MEMBERS_URL).mock(return_value=httpx.Response(401, json={}))
        with pytest.raises(RuntimeError, match="401"):
            with _make_client() as client:
                fetch_list_members("123", client)

    @respx.mock
    def test_rate_limit_then_success_retries(self):
        _mock_discovery()
        route = respx.get(_LIST_MEMBERS_URL)
        route.side_effect = [
            httpx.Response(429, json={}),
            httpx.Response(200, json=_make_members_response(
                [_make_member_entry("alice", "111")]
            )),
        ]
        logs = []
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                result = fetch_list_members("123", client, log=logs.append)
        assert result == {"alice": "111"}
        assert any("rate limit" in m.lower() for m in logs)


    @respx.mock
    def test_pre_filter_skips_already_blocked(self):
        respx.get(_BLOCKS_IDS_URL).mock(
            return_value=httpx.Response(200, json={"ids": ["111"], "next_cursor": 0})
        )
        respx.post(_BLOCK_URL).mock(return_value=httpx.Response(200, json={}))
        logs = []
        with patch("x_bulk_block.time.sleep"):
            with _make_client() as client:
                bulk_block(client, {"alice": "111", "bob": "222"}, log=logs.append)

        assert not any("alice" in m and "BLOCKED" in m for m in logs)
        assert any("bob" in m and "BLOCKED" in m for m in logs)
        assert any("1 skipped" in m for m in logs)


# ── run_job ───────────────────────────────────────────────────────────────────

class TestRunJob:
    def test_missing_auth_token_raises(self):
        with pytest.raises(RuntimeError, match="auth_token missing"):
            run_job("123", "ct0=xyz")

    def test_missing_ct0_raises(self):
        with pytest.raises(RuntimeError, match="ct0 missing"):
            run_job("123", "auth_token=xyz")

    @patch("x_bulk_block.fetch_list_members")
    def test_run_job_always_blocks(self, mock_fetch):
        """dry_run was removed — run_job always proceeds to bulk_block."""
        mock_fetch.return_value = {"alice": "111"}
        logs = []
        with respx.mock:
            respx.post("https://x.com/i/api/1.1/blocks/ids.json").respond(200, json={"ids": [], "next_cursor": 0})
            respx.get("https://x.com/i/api/1.1/blocks/ids.json").respond(200, json={"ids": [], "next_cursor": 0})
            respx.post("https://x.com/i/api/1.1/blocks/create.json").respond(200, json={})
            run_job("123", _COOKIE_STR, log=logs.append)

        mock_fetch.assert_called_once()
        assert any("BLOCKED" in m for m in logs)

    @patch("x_bulk_block.fetch_list_members")
    def test_empty_list_exits_early(self, mock_fetch):
        mock_fetch.return_value = {}
        logs = []
        run_job("123", _COOKIE_STR, log=logs.append)

        assert any("Nothing to do" in m for m in logs)

    @respx.mock
    @patch("x_bulk_block.fetch_list_members")
    def test_full_block_run_end_to_end(self, mock_fetch):
        mock_fetch.return_value = {"alice": "111", "bob": "222"}
        respx.post(_BLOCK_URL).mock(return_value=httpx.Response(200, json={}))

        logs = []
        with patch("x_bulk_block.time.sleep"):
            run_job("123", _COOKIE_STR, dry_run=False, log=logs.append)

        assert any("BLOCKED" in m and "alice" in m for m in logs)
        assert any("BLOCKED" in m and "bob" in m for m in logs)
        assert any("[DONE]" in m for m in logs)
