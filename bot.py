"""
MapTap daily leaderboard bot.

Runs once, reads yesterday's messages from a Discord channel, pulls out
MapTap "Final score: NNN" lines, posts a leaderboard, and exits.
No always-on process needed, so it's perfect for a scheduled GitHub Action.

Env flags:
  DRY_RUN=1    print the leaderboard but don't post it
  PRINT_RAW=1  also print every message read (author + content) for debugging
"""
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

TOKEN = os.environ["DISCORD_TOKEN"]
CHANNEL_ID = os.environ["CHANNEL_ID"]            # channel to read scores from
POST_CHANNEL_ID = os.environ.get("POST_CHANNEL_ID", CHANNEL_ID)  # where to post
TZ = ZoneInfo(os.environ.get("TIMEZONE", "America/New_York"))

API = "https://discord.com/api/v10"
HEADERS = {"Authorization": f"Bot {TOKEN}", "Content-Type": "application/json"}
DISCORD_EPOCH_MS = 1420070400000

SCORE_RE = re.compile(r"final\s*score\s*:?\s*(\d{1,4})", re.IGNORECASE)
MEDALS = ["🥇", "🥈", "🥉"]


def snowflake_from(dt: datetime) -> int:
    """Convert a datetime to a Discord snowflake (used for the `after` filter)."""
    ms = int(dt.timestamp() * 1000)
    return (ms - DISCORD_EPOCH_MS) << 22


def yesterday_window():
    today_local = datetime.now(TZ).date()
    start = datetime.combine(today_local - timedelta(days=1), datetime.min.time(), TZ)
    end = start + timedelta(days=1)
    return start, end


def fetch_messages(start: datetime, end: datetime):
    """Page through messages posted between start and end (oldest first)."""
    after = snowflake_from(start)
    messages = []
    while True:
        r = requests.get(
            f"{API}/channels/{CHANNEL_ID}/messages",
            headers=HEADERS,
            params={"after": after, "limit": 100},
            timeout=30,
        )
        r.raise_for_status()
        batch = r.json()
        if not batch:
            break
        batch.sort(key=lambda m: int(m["id"]))
        for m in batch:
            ts = datetime.fromisoformat(m["timestamp"])
            if ts >= end:
                return messages
            messages.append(m)
        after = int(batch[-1]["id"])
        if len(batch) < 100:
            break
    return messages


def print_raw(messages):
    print(f"--- {len(messages)} raw messages ---")
    for m in messages:
        who = m["author"].get("username", m["author"]["id"])
        bot = " [bot]" if m["author"].get("bot") else ""
        hit = "MATCH" if SCORE_RE.search(m.get("content", "")) else "no match"
        print(f"\n[{m['timestamp']}] {who}{bot} ({hit})\n{m.get('content', '')!r}")
    print("--- end raw ---\n")


def build_leaderboard(messages):
    scores = {}  # user_id -> (name, score); first post of the day counts
    for m in messages:
        if m["author"].get("bot"):
            continue
        match = SCORE_RE.search(m.get("content", ""))
        if not match:
            continue
        uid = m["author"]["id"]
        if uid in scores:
            continue
        # Renders as a clickable @mention; allowed_mentions in post() keeps it from pinging
        scores[uid] = (f"<@{uid}>", int(match.group(1)))
    return sorted(scores.values(), key=lambda x: x[1], reverse=True)


def format_post(day: datetime, board):
    header = f"🗺️ **MapTap Leaderboard — {day:%A, %B %-d}**\n"
    if not board:
        return header + "No scores posted yesterday. 😢"
    lines, prev_score, rank = [], None, 0
    for i, (name, score) in enumerate(board, start=1):
        if score != prev_score:          # ties share a rank
            rank, prev_score = i, score
        badge = MEDALS[rank - 1] if rank <= 3 else f"`{rank}.`"
        lines.append(f"{badge} {name} — {score}")
    avg = sum(s for _, s in board) / len(board)
    footer = f"\n\n{len(board)} players · avg {avg:.0f}"
    return header + "\n".join(lines) + footer


def post(content: str):
    r = requests.post(
        f"{API}/channels/{POST_CHANNEL_ID}/messages",
        headers=HEADERS,
        json={"content": content, "allowed_mentions": {"parse": []}},
        timeout=30,
    )
    r.raise_for_status()


if __name__ == "__main__":
    start, end = yesterday_window()
    messages = fetch_messages(start, end)
    if os.environ.get("PRINT_RAW") == "1":
        print_raw(messages)
    board = build_leaderboard(messages)
    msg = format_post(start, board)
    print(msg)
    if os.environ.get("DRY_RUN") != "1":
        post(msg)
