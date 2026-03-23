"""
X (Twitter) Bulk Block — Block all authors who tweeted in an X List
====================================================================
No developer account or API keys needed — uses your browser cookies only.

SETUP
-----
1. Install dependencies (requires Python 3.10+):
       python3.12 -m pip install httpx python-dotenv --break-system-packages

2. Get your browser cookies from x.com:
   - Open x.com in Chrome/Firefox and make sure you are logged in.
   - Press F12 → Application tab → Cookies → https://x.com
   - Copy the values of:  auth_token   and   ct0

3. Create a .env file in the same directory with one line:
       X_COOKIES=auth_token=PASTE_HERE; ct0=PASTE_HERE

USAGE
-----
    # Dry-run: preview who would be blocked without actually blocking
    python3.12 x_bulk_block.py --list https://x.com/i/lists/1992639069235695952 --dry-run

    # Block every tweet author in the list (~4 minutes for 400 users)
    python3.12 x_bulk_block.py --list https://x.com/i/lists/1992639069235695952

    # You can also pass just the numeric list ID
    python3.12 x_bulk_block.py --list 1992639069235695952
"""

import argparse
import json
import os
import re
import sys
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

# Delay between block requests (seconds).
# 0.5s → ~4 min for 400 users using the internal web API.
BLOCK_DELAY = 0.5


def parse_list_id(list_arg: str) -> str:
    """
    Accept either a full X list URL or a bare numeric list ID.
    https://x.com/i/lists/1992639069235695952  →  "1992639069235695952"
    """
    match = re.search(r"lists/(\d+)", list_arg)
    if match:
        return match.group(1)
    if re.fullmatch(r"\d+", list_arg.strip()):
        return list_arg.strip()
    raise ValueError(
        "Could not parse a list ID from the provided input. "
        "Provide a URL like https://x.com/i/lists/123456 or just the numeric ID."
    )



# ── X internal GraphQL constants ─────────────────────────────────────────────
_BEARER = (
    "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D"
    "1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
)
_LIST_TIMELINE_URL = (
    "https://x.com/i/api/graphql/BkauSnPUDQTeeJsxq17opA/ListLatestTweetsTimeline"
)
_FEATURES = json.dumps({
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "responsive_web_twitter_article_tweet_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
}, separators=(",", ":"))


def _parse_cookies(cookie_str: str) -> dict[str, str]:
    """Parse 'auth_token=XX; ct0=YY' into a dict."""
    result = {}
    for part in cookie_str.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            result[k.strip()] = v.strip()
    return result


def fetch_tweet_authors(list_id: str, client: httpx.Client, log=print) -> dict[str, str]:
    """
    Page through list timeline via X's internal GraphQL API.
    Returns {username_lower: user_id}.
    """
    authors: dict[str, str] = {}
    cursor: str | None = None
    page = 0

    while True:
        page += 1
        variables = json.dumps({
            "listId": list_id,
            "count": 100,
            **({"cursor": cursor} if cursor else {}),
        }, separators=(",", ":"))

        params = {"variables": variables, "features": _FEATURES}

        resp = client.get(_LIST_TIMELINE_URL, params=params)
        if resp.status_code == 429:
            log("[INFO] Read rate limit hit — waiting 60s …")
            time.sleep(60)
            resp = client.get(_LIST_TIMELINE_URL, params=params)
        if resp.status_code != 200:
            raise RuntimeError(
                f"X API returned HTTP {resp.status_code}. "
                "Your cookies may have expired — refresh them from the browser."
            )

        data = resp.json()

        instructions = (
            data.get("data", {})
                .get("list", {})
                .get("tweets_timeline", {})
                .get("timeline", {})
                .get("instructions", [])
        )

        next_cursor = None
        entries_found = 0

        for instruction in instructions:
            for entry in instruction.get("entries", []):
                entry_id = entry.get("entryId", "")

                if "cursor-bottom" in entry_id or "cursor-top" in entry_id:
                    val = (
                        entry.get("content", {}).get("value")
                        or entry.get("content", {}).get("itemContent", {}).get("value")
                    )
                    if "cursor-bottom" in entry_id and val:
                        next_cursor = val
                    continue

                user = (
                    entry.get("content", {})
                         .get("itemContent", {})
                         .get("tweet_results", {})
                         .get("result", {})
                         .get("core", {})
                         .get("user_results", {})
                         .get("result", {})
                         .get("legacy", {})
                )
                uid = user.get("id_str") or (
                    entry.get("content", {})
                         .get("itemContent", {})
                         .get("tweet_results", {})
                         .get("result", {})
                         .get("core", {})
                         .get("user_results", {})
                         .get("result", {})
                         .get("rest_id")
                )
                uname = user.get("screen_name", "").lower()
                if uid and uname and uid not in authors.values():
                    authors[uname] = uid
                    entries_found += 1

        log(
            f"[INFO] Page {page}: {entries_found} new author(s), "
            f"total unique so far: {len(authors)}"
        )

        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor

    return authors




def bulk_block(client: httpx.Client, id_map: dict[str, str], log=print) -> None:
    """Block each user via X's internal web API."""
    _BLOCK_URL = "https://x.com/i/api/1.1/blocks/create.json"
    total = len(id_map)
    success = skipped = failed = 0

    for idx, (username, user_id) in enumerate(id_map.items(), start=1):
        try:
            resp = client.post(_BLOCK_URL, data={"user_id": user_id})
            if resp.status_code == 200:
                log(f"[{idx}/{total}] @{username} ... BLOCKED")
                success += 1
            elif resp.status_code in (403, 404):
                log(f"[{idx}/{total}] @{username} ... SKIPPED (already blocked or deleted)")
                skipped += 1
            elif resp.status_code == 429:
                log(f"[{idx}/{total}] @{username} ... RATE LIMITED — waiting 60s …")
                time.sleep(60)
                resp2 = client.post(_BLOCK_URL, data={"user_id": user_id})
                if resp2.status_code == 200:
                    log(f"[{idx}/{total}] @{username} ... BLOCKED (retry)")
                    success += 1
                else:
                    log(f"[{idx}/{total}] @{username} ... FAILED after retry ({resp2.status_code})")
                    failed += 1
            else:
                log(f"[{idx}/{total}] @{username} ... FAILED ({resp.status_code})")
                failed += 1
        except httpx.RequestError as exc:
            log(f"[{idx}/{total}] @{username} ... FAILED (network: {exc})")
            failed += 1

        if idx < total:
            time.sleep(BLOCK_DELAY)

    log(f"[DONE] {total} users processed — {success} blocked, {skipped} skipped, {failed} failed.")


def run_job(
    list_id: str,
    cookie_str: str,
    dry_run: bool = False,
    log=print,
) -> None:
    """
    Central entry point callable from both CLI and web UI.
    Raises RuntimeError on unrecoverable errors instead of calling sys.exit().
    `log` receives each progress message as a string.
    """
    cookies = _parse_cookies(cookie_str)
    ct0 = cookies.get("ct0", "")
    if not ct0:
        raise RuntimeError("ct0 missing from cookies. Check your cookie values.")

    headers = {
        "Authorization": _BEARER,
        "x-csrf-token": ct0,
        "x-twitter-active-user": "yes",
        "x-twitter-client-language": "en",
        "Content-Type": "application/x-www-form-urlencoded",
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ),
    }

    with httpx.Client(
        headers=headers, cookies=cookies, verify=True,
        follow_redirects=True, timeout=30,
    ) as client:
        log("[INFO] Fetching tweet authors from list timeline …")
        id_map = fetch_tweet_authors(list_id, client, log=log)
        log(f"[INFO] {len(id_map)} unique author(s) found.")

        if not id_map:
            log("[INFO] No tweet authors found. Nothing to do.")
            return

        if dry_run:
            log("[INFO] DRY-RUN — authors that would be blocked:")
            for username, user_id in id_map.items():
                log(f"        @{username} (id={user_id})")
            est = len(id_map) * BLOCK_DELAY
            log(f"[DONE] Would block {len(id_map)} user(s) in ~{est:.0f}s ({est/60:.1f} min).")
            return

        bulk_block(client, id_map, log=log)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Block every tweet author in an X list. Only needs browser cookies."
    )
    parser.add_argument("--list", required=True, metavar="LIST",
                        help="X list URL or bare numeric list ID.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview who would be blocked without blocking anyone.")
    args = parser.parse_args()

    try:
        list_id = parse_list_id(args.list)
    except ValueError as exc:
        sys.exit(f"[ERROR] {exc}")
    print(f"[INFO] Target list ID: {list_id}")

    cookie_str = os.getenv("X_COOKIES", "").strip()
    if not cookie_str:
        sys.exit(
            "[ERROR] X_COOKIES not set.\n"
            "        Add X_COOKIES=auth_token=XXX; ct0=YYY to your .env file."
        )

    try:
        run_job(list_id, cookie_str, dry_run=args.dry_run)
    except RuntimeError as exc:
        sys.exit(f"[ERROR] {exc}")


if __name__ == "__main__":
    main()
