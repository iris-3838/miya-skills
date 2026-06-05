#!/usr/bin/env python3
"""
delete_duplicates.py — Detect and bulk-delete duplicate Zaim transactions.

Detects duplicate pairs (same date + same amount + same place, different IDs)
and deletes the newer copy (higher ID) — typically the PayPay CSV import that
was double-imported alongside the PayPayカード statement.

Usage:
    source /opt/data/workspace/.zaim_env
    python3 /opt/data/workspace/skills/productivity/zaim-household-finance/scripts/delete_duplicates.py --dry-run    # preview only
    python3 /opt/data/workspace/skills/productivity/zaim-household-finance/scripts/delete_duplicates.py               # delete duplicates

Options:
    --dry-run           Preview only (no API calls)
    --min-amount N      Only consider transactions >= N yen (default: 100)
    --max-delete N      Stop after N deletions (default: unlimited)
    --only-store X      Only process transactions containing X in place name
    --keep-older        Delete the OLDER (lower ID) duplicate instead of newer

The script:
  1. Queries local SQLite DB at ~/.zaim_cache/zaim.db
  2. Groups transactions by (date, amount, place) — exact matches
  3. For groups with 2+ entries, identifies the duplicates
  4. By default deletes the HIGHER-ID copy (newer import)
  5. Adds 1-second delay between API DELETE calls

Requires Zaim OAuth tokens in environment variables:
    ZAIM_CONSUMER_KEY
    ZAIM_CONSUMER_SECRET
    ZAIM_ACCESS_TOKEN
    ZAIM_ACCESS_TOKEN_SECRET

Or: source /opt/data/workspace/.zaim_env (sets these vars).
"""

import os
import sys
import sqlite3
import time
from collections import defaultdict
from requests_oauthlib import OAuth1
import requests

# ── Config ──────────────────────────────────────────────────────────
DB = os.path.expanduser("~/.zaim_cache/zaim.db")
DRY_RUN = "--dry-run" in sys.argv
MIN_AMOUNT = 100
KEEP_OLDER = "--keep-older" in sys.argv
MAX_DELETE = None
STORE_FILTER = None

# Parse optional flags
args = sys.argv[1:]
for i, arg in enumerate(args):
    if arg == "--min-amount" and i + 1 < len(args):
        try:
            MIN_AMOUNT = int(args[i + 1])
        except ValueError:
            pass
    elif arg == "--max-delete" and i + 1 < len(args):
        try:
            MAX_DELETE = int(args[i + 1])
        except ValueError:
            pass
    elif arg == "--only-store" and i + 1 < len(args):
        STORE_FILTER = args[i + 1]

# ── Auth ────────────────────────────────────────────────────────────
CK = os.environ.get("ZAIM_CONSUMER_KEY")
CS = os.environ.get("ZAIM_CONSUMER_SECRET")
AT = os.environ.get("ZAIM_ACCESS_TOKEN")
ASEC = os.environ.get("ZAIM_ACCESS_TOKEN_SECRET")

if not all([CK, CS, AT, ASEC]):
    print(
        "Error: Zaim credentials not found.\n"
        "Source the env file first:\n"
        "  source /opt/data/workspace/.zaim_env\n"
        "Or set these environment variables:\n"
        "  ZAIM_CONSUMER_KEY\n"
        "  ZAIM_CONSUMER_SECRET\n"
        "  ZAIM_ACCESS_TOKEN\n"
        "  ZAIM_ACCESS_TOKEN_SECRET",
        file=sys.stderr,
    )
    sys.exit(1)

auth = OAuth1(CK, CS, AT, ASEC)
API_BASE = "https://api.zaim.net/v2"

# ── Detect Duplicates ──────────────────────────────────────────────
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

rows = conn.execute(
    """
    SELECT id, date, amount, name, place, comment,
           category_id, genre_id, mode
    FROM transactions
    WHERE mode = 'payment'
      AND amount > 0
    ORDER BY date, place, amount, id
"""
).fetchall()

print(f"総取引数: {len(rows)}件")

# Group by (date, amount, place)
groups = defaultdict(list)
for r in rows:
    place = (r["place"] or "").strip()
    name = (r["name"] or "").strip()
    store = place or name
    if not store:
        continue

    # Apply store filter
    if STORE_FILTER and STORE_FILTER.lower() not in store.lower():
        continue

    # Apply min amount filter
    if r["amount"] < MIN_AMOUNT:
        continue

    key = (r["date"], r["amount"], store)
    groups[key].append(r)

# Find duplicate groups
dup_groups = {k: v for k, v in groups.items() if len(v) >= 2}
dup_groups = dict(sorted(dup_groups.items(), key=lambda x: x[0]))  # sort by date

total_duplicate_pairs = sum(len(v) - 1 for v in dup_groups.values())
total_duplicate_ids = sum(len(v) for v in dup_groups.values())

print(f"重複グループ: {len(dup_groups)}組")
print(f"重複トランザクション数: {total_duplicate_ids}件（うち削除対象: {total_duplicate_pairs}件）")

if not dup_groups:
    print("\n✅ 重複は見つかりませんでした。")
    sys.exit(0)

print(f"\n{'='*80}")
print("  ■ 重複一覧")
print(f"{'='*80}")

total_amount = 0
# Collect IDs to delete (higher ID = newer import, that's the duplicate to remove)
to_delete = []  # [(id, date, amount, store, comment)]

for key, entries in dup_groups.items():
    date, amount, store = key
    sorted_entries = sorted(entries, key=lambda x: x["id"])

    # Keep the lower ID (older import), delete higher IDs
    if KEEP_OLDER:
        keep = sorted_entries[-1]
        kill = sorted_entries[:-1]
    else:
        keep = sorted_entries[0]
        kill = sorted_entries[1:]

    kills_str = ", ".join(f"#{e['id']}" for e in kill)
    fmt_amount = f"¥{amount:,}"

    # Show comment differences if any
    comments = set()
    for e in entries:
        c = (e["comment"] or "").strip()
        if c:
            comments.add(c)
    comment_info = f" ({', '.join(comments)})" if len(comments) > 1 else ""

    print(f"  {date}  {fmt_amount:>10}  {store}")
    print(f"    └ Keep: #{keep['id']}, Delete: {kills_str}{comment_info}")

    for e in kill:
        total_amount += e["amount"]
        to_delete.append((e["id"], e["date"], e["amount"], store, e.get("comment", "")))

if DRY_RUN:
    print(f"\n{'='*80}")
    print(f"  [DRY-RUN] 削除対象: {len(to_delete)}件 / ¥{total_amount:,}")
    print("  --dry-run を外して実際に削除を実行できます。")
    conn.close()
    sys.exit(0)

# ── Confirm ────────────────────────────────────────────────────────
print(f"\n{'='*80}")
print(f"  ⚠ 上記 {len(to_delete)}件 の重複トランザクションを削除します。")
print(f"  DELETE /home/money/payment/{{id}} API を呼び出します。")
print(f"{'='*80}")

# ── Execute Deletion ───────────────────────────────────────────────
success = 0
errors = 0
rate_limited = False

for idx, (tid, date, amount, store, comment) in enumerate(to_delete, 1):
    if MAX_DELETE and success >= MAX_DELETE:
        print(f"\n  ⏹ --max-delete={MAX_DELETE} に達したため停止します。")
        break

    url = f"{API_BASE}/home/money/payment/{tid}"

    try:
        r = requests.delete(url, auth=auth, timeout=15)
    except requests.exceptions.RequestException as e:
        print(f"  ⚠ #{tid} ({date} {store}): Connection error — {e}")
        errors += 1
        continue

    if r.status_code == 200:
        success += 1
        print(f"  [{idx}/{len(to_delete)}] ✅ #{tid}: {date} ¥{amount:,} {store}")
    elif r.status_code == 429:
        print(f"  ⚠ #{tid}: Rate limited (429). Waiting 5 seconds...")
        time.sleep(5)
        rate_limited = True
        # Retry once
        try:
            r = requests.delete(url, auth=auth, timeout=15)
            if r.status_code == 200:
                success += 1
                print(f"  [{idx}/{len(to_delete)}] ✅ #{tid} (retry OK): {date} ¥{amount:,} {store}")
            else:
                errors += 1
                print(f"  ⚠ #{tid}: {r.status_code} {r.text[:100]}")
        except requests.exceptions.RequestException:
            errors += 1
            print(f"  ⚠ #{tid}: Retry also failed")
    elif r.status_code == 404:
        print(f"  [{idx}/{len(to_delete)}] ❓ #{tid}: Already deleted (404)")
        success += 1  # Count as success — already removed
    else:
        errors += 1
        err_text = r.text[:120] if r.text else "(no body)"
        print(f"  ⚠ #{tid}: {r.status_code} — {err_text}")

    # Rate limit: 1 second between calls
    if not rate_limited:
        time.sleep(1)
    rate_limited = False

# ── Summary ─────────────────────────────────────────────────────────
print(f"\n{'='*80}")
print(f"  ■ 削除完了")
print(f"  {'='*40}")
print(f"  成功: {success}件")
print(f"  エラー: {errors}件")
print(f"  合計削除金額: ¥{total_amount:,}")
print(f"{'='*80}")

# ── Statistics ──────────────────────────────────────────────────────
total_in_db = len(rows)
remaining = total_in_db - success
print(f"\n  DB内取引数: {total_in_db}件 → {remaining}件（{success}件削除）")

# ── Refresh local cache ─────────────────────────────────────────────
print("\n  💡 ローカルDB（~/.zaim_cache/zaim.db）を更新するには:")
print("     source /opt/data/workspace/.zaim_env && python3 /opt/data/workspace/scripts/zaim/zaim.py sync")

conn.close()
