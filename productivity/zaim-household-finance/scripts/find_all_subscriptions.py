#!/usr/bin/env python3
"""
find_all_subscriptions.py — Detect recurring subscription patterns across ALL Zaim categories.

Key features:
1. Deduplicates same-date + same-amount + same-store transactions (PayPay CSV × card duplicates)
2. Scans ALL categories (not just service-related ones)
3. Detects monthly continuity (2+ months for services, 3+ for non-service)
4. Detects price changes at same store (plan changes, price hikes)

Output sections:
  - サブスクリプション（確実）: Confirmed subscriptions
  - 要確認: 2-month patterns needing more data
  - 参考: Irregular patterns
  - 同一店舗・金額違い: Price/plan change candidates

Usage:
    source /workspace/.zaim_env
    python3 /workspace/find_all_subscriptions.py

Requires: local SQLite cache at ~/.zaim_cache/zaim.db (populated by zaim.py sync)
"""
import os
import sqlite3
from collections import defaultdict

DB = os.path.expanduser("~/.zaim_cache/zaim.db")
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT t.place, t.name, t.amount, t.date, t.id,
           c.name as cat_name, t.category_id, t.comment
    FROM transactions t
    LEFT JOIN categories c ON t.category_id = c.id
    WHERE t.mode = 'payment'
      AND t.amount > 0
    ORDER BY COALESCE(NULLIF(t.place,''), t.name), t.amount, t.date
""").fetchall()

# ── Dedup: same date + same amount + same store → 1 entry ──
seen = set()
deduped = []
for r in rows:
    store = (r["place"] or r["name"] or "").strip()
    if not store:
        continue
    key = (r["date"], r["amount"], store)
    if key in seen:
        continue
    seen.add(key)
    deduped.append(r)

print(f"総取引: {len(rows)}件 → 重複除去後: {len(deduped)}件 ({len(rows)-len(deduped)}件除去)")

# ── Group by (store, amount) ──
candidates = defaultdict(lambda: {
    "dates": [], "months": set(), "amounts": [],
    "display_name": "", "cat_name": "", "category_id": 0
})

for r in deduped:
    store = (r["place"] or r["name"] or "").strip()
    key = (store, r["amount"])
    e = candidates[key]
    e["dates"].append(r["date"])
    e["months"].add(r["date"][:7])
    e["amounts"].append(r["amount"])
    e["display_name"] = store
    e["cat_name"] = r["cat_name"] or ""
    e["category_id"] = r["category_id"]

def is_subscription_name(name):
    """Check if store name suggests a subscription service."""
    kw = [
        "Google", "Apple", "iCloud", "Prime", "Netflix", "Spotify",
        "YouTube", "PayPayほけん", "PayPay保険", "Adobe",
        "Microsoft", "OneDrive", "Dropbox", "Notion", "ChatGPT",
        "GitHub", "Slack", "Zoom", "Canva", "Figma", "LINE",
        "dカード", "d払い", "povo", "UQ", "au", "SoftBank",
        "楽天モバイル", "ドコモ", "NHK", "水道", "ガス", "東京電力",
        "家賃", "駐車場", "サブスク",
    ]
    return any(k.lower() in name.lower() for k in kw)

# ── Analysis ──
subs = []
monthly_dues = []
irregular = []

for key, entry in candidates.items():
    store, amount = key
    months = sorted(entry["months"])
    dates = entry["dates"]
    span = len(months)
    total_occurrences = len(dates)
    is_svc = is_subscription_name(store)

    month_counts = defaultdict(int)
    for d in dates:
        month_counts[d[:7]] += 1
    max_per_month = max(month_counts.values())
    mostly_monthly = max_per_month <= 1

    info = {
        "name": store,
        "amount": amount,
        "months": months,
        "total": total_occurrences,
        "span_months": span,
        "cat": entry["cat_name"],
        "cat_id": entry["category_id"],
        "is_svc": is_svc,
        "max_mo": max_per_month,
    }

    if span >= 2 and is_svc and amount >= 100:
        subs.append(info)
    elif span >= 3 and amount >= 300 and mostly_monthly:
        subs.append(info)
    elif span >= 2 and amount >= 300 and mostly_monthly:
        monthly_dues.append(info)
    elif span >= 2 and amount >= 500:
        irregular.append(info)

# ── Display ──
subs.sort(key=lambda x: (-x["amount"], x["name"]))
monthly_dues.sort(key=lambda x: (-x["amount"], x["name"]))
irregular.sort(key=lambda x: (-x["span_months"], -x["amount"]))

def fmt(info):
    svc_mark = " ⚙️" if info["is_svc"] else ""
    cat_tag = f" [{info['cat']}]" if info["cat"] else ""
    month_str = f"{info['months'][0]}〜{info['months'][-1]}"
    freq = f" {info['total']}回/{info['span_months']}ヶ月"
    return f"  ¥{info['amount']:>7,}/月{svc_mark}{cat_tag}  {info['name']}\n    └ {month_str}（{freq}）"

print("\n" + "=" * 80)
print("  ■ サブスクリプション（確実）")
print("=" * 80)
total = 0
prev_cat = None
for e in subs:
    if e["cat"] != prev_cat:
        print(f"\n  ── {e['cat'] or '未分類'} ──")
        prev_cat = e["cat"]
    print(fmt(e))
    total += e["amount"]

print(f"\n  ────────────────────")
print(f"  推定月額合計: ¥{total:,}/月")

if monthly_dues:
    print(f"\n\n" + "=" * 80)
    print(f"  ■ 要確認：2ヶ月のみ出現（継続調査）")
    print("=" * 80)
    for e in monthly_dues[:15]:
        print(fmt(e))

if irregular:
    print(f"\n\n" + "=" * 80)
    print(f"  ■ 参考：同額パターン（各月複数回あり等）")
    print("=" * 80)
    for e in irregular[:15]:
        print(fmt(e))

# ── Price change detection ──
print(f"\n\n" + "=" * 80)
print("  ■ 同一店舗・金額違い（価格改定・プラン変更の可能性）")
print("=" * 80)

store_amounts = defaultdict(list)
for key, entry in candidates.items():
    store, amount = key
    store_amounts[store].append((amount, entry["months"], len(entry["dates"])))

for store, amounts in sorted(store_amounts.items()):
    if len(amounts) >= 2 and any(cnt >= 3 for _, _, cnt in amounts):
        amt_strs = []
        for amt, mons, cnt in sorted(amounts, reverse=True):
            amt_strs.append(f"¥{amt:,}×{cnt}")
        print(f"  {store}: {', '.join(amt_strs)}")

conn.close()
