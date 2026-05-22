#!/usr/bin/env python3
"""
recover_amount.py — Recover Zaim transactions whose amount was zeroed by a partial PUT.

Zaim's PUT /home/money/{mode}/{id} endpoint RESETS any omitted field to its default.
If you previously sent only {category_id, genre_id} in a PUT request, all other fields
(amount, name, place) were set to 0/blank.

Usage:
    source /workspace/.zaim_env
    python3 /workspace/recover_zaim_amounts.py --dry-run   # preview only
    python3 /workspace/recover_zaim_amounts.py              # fix everything

The script reads the local SQLite DB at ~/.zaim_cache/zaim.db (which preserves the
correct original amounts) and re-PUTs each affected transaction with ALL fields.
"""
import os
import sys
import sqlite3
from requests_oauthlib import OAuth1
from requests import get, put

DB = os.path.expanduser("~/.zaim_cache/zaim.db")

# ── Credentials from environment variables ───────────────────────
CK = os.environ.get("ZAIM_CONSUMER_KEY")
CS = os.environ.get("ZAIM_CONSUMER_SECRET")
AT = os.environ.get("ZAIM_ACCESS_TOKEN")
ASEC = os.environ.get("ZAIM_ACCESS_TOKEN_SECRET")

if not all([CK, CS, AT, ASEC]):
    print(
        "Error: Zaim credentials not found.\n"
        "Source the env file first:\n"
        "  source /workspace/.zaim_env\n"
        "Or set these environment variables:\n"
        "  ZAIM_CONSUMER_KEY\n"
        "  ZAIM_CONSUMER_SECRET\n"
        "  ZAIM_ACCESS_TOKEN\n"
        "  ZAIM_ACCESS_TOKEN_SECRET",
        file=sys.stderr,
    )
    sys.exit(1)

auth = OAuth1(CK, CS, AT, ASEC)
DRY_RUN = "--dry-run" in sys.argv

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

targets = conn.execute("""
    SELECT id, amount, date, name, place, comment,
           category_id, genre_id, from_account_id, to_account_id,
           currency_code, mode
    FROM transactions
    WHERE mode = 'payment'
      AND amount > 0
      AND category_id IS NOT NULL
      AND category_id != 199
    ORDER BY id
""").fetchall()

print(f"Restoration targets: {len(targets)} transactions")
if not targets:
    print("Nothing to restore.")
    sys.exit(0)

success = 0
for tx in targets:
    data = {
        "category_id": tx["category_id"],
        "genre_id": tx["genre_id"],
        "amount": tx["amount"],
        "date": tx["date"],
        "name": tx["name"] or "",
        "place": tx["place"] or "",
        "comment": tx["comment"] or "",
        "from_account_id": tx["from_account_id"],
        "to_account_id": tx["to_account_id"],
        "currency_code": tx["currency_code"],
    }
    if DRY_RUN:
        print(f"  #{tx['id']}: amount={tx['amount']} → would fix")
        continue
    url = f"https://api.zaim.net/v2/home/money/{tx['mode']}/{tx['id']}"
    r = put(url, auth=auth, data=data, timeout=15)
    if r.status_code == 200:
        success += 1
    else:
        err = r.json() if r.text else {}
        print(f"  ⚠ #{tx['id']}: {r.status_code} {err.get('error', r.text[:100])}")
    if success > 0 and success % 50 == 0:
        print(f"  ...{success}/{len(targets)}")

if not DRY_RUN:
    print(f"\n✅ {success}/{len(targets)} restored")
else:
    print(f"\n🔍 Dry-run: {len(targets)} would be restored")

conn.close()
