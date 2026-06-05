---
name: zaim-household-finance
title: Zaim Household Finance
description: Manage household finances via Zaim API — PayPay CSV import with duplicate detection, transaction CRUD, category/genre/account master data.
tags:
  - zaim
  - paypay
  - household-accounting
  - kakeibo
  - csv-import
  - oauth1
triggers:
  - user mentions Zaim, PayPay CSV, 家計簿, household accounting, kakeibo
  - user wants to import transactions or automate expense tracking
---

# Zaim Household Finance Skill

Household account book management via [Zaim API](https://dev.zaim.net) (v2). Handles OAuth 1.0a authentication, CSV import with duplicate prevention, and transaction CRUD operations.

## Authentication Setup

Zaim uses **OAuth 1.0a** (3-legged). You need four tokens:

1. **Consumer Key / Consumer Secret** — obtained by registering an app at [dev.zaim.net](https://dev.zaim.net) (requires a Zaim account)
2. **Access Token / Access Token Secret** — obtained via OAuth authorization flow

### OAuth Flow Steps

```python
import zaim
api = zaim.Api(consumer_key='...', consumer_secret='...')

# Step 1: Get request token
request_token = api.get_request_token('https://example.com/callback')
# → User opens the authorization URL in browser

# Step 2: After user authorizes, get access token
access_token = api.get_access_token(oauth_verifier='...')
# → Now api has full auth. Save all 4 tokens securely.
```

**Security**: Store tokens in environment variables (`ZAIM_CONSUMER_KEY`, `ZAIM_CONSUMER_SECRET`, `ZAIM_ACCESS_TOKEN`, `ZAIM_ACCESS_TOKEN_SECRET`). Never hardcode in scripts.

## API Endpoint Summary

Base URL: `https://api.zaim.net/v2`

| Method | Endpoint | Purpose |
|--------|----------|---------|
| `GET` | `/home/user/verify` | Verify authentication |
| `GET` | `/home/money` | List transactions (with filters) |
| `POST` | `/home/money/payment` | Register payment (expense) |
| `POST` | `/home/money/income` | Register income |
| `POST` | `/home/money/transfer` | Register transfer |
| `PUT` | `/home/money/{mode}/{id}` | Update transaction |
| `DELETE` | `/home/money/{mode}/{id}` | Delete transaction |
| `GET` | `/home/category` | List categories |
| `GET` | `/home/genre` | List genres (subcategories) |
| `GET` | `/home/account` | List accounts |
| `GET` | `/home/currency` | List currencies |

**Python library**: Use `pip install zaim requests_oauthlib --break-system-packages` (user-site install, since root access unavailable). Also supports `ExtendedApi` with client-side search filtering.

**OAuth Token Setup Script**: `/opt/data/workspace/scripts/zaim/zaim_token_setup.py` — interactive script that walks through the OAuth 1.0a flow (request token → user authorization → access token). Run with `python3 /opt/data/workspace/scripts/zaim/zaim_token_setup.py` and enter Consumer Key/Secret when prompted.

**Note**: The official API docs at dev.zaim.net require login — the overview page redirects to a login form. Publicly accessible: terms of service at `/portal/tos`. No other doc pages are public.

## Automatic Category Classification

A store-name-based classifier (`/opt/data/workspace/scripts/zaim/categorize_and_subs.py`) automatically assigns Zaim category/genre to uncategorized transactions. Supports 50+ Japanese stores/chains with category rules mapped to Zaim's official category IDs.

### Store Categories Supported

| Store Pattern | Zaim Category | Genre |
|--------------|---------------|-------|
| カスミ, ベルク, ザ・ビッグ, Costco | 食費 (101) | 食料品 (10101) |
| 山岡家, 一蘭, てっしょう, 超人, 豚男爵, ロマノフ, etc. | 食費 (101) | 晩ご飯 (10105) |
| 松屋, やよい軒, モスバーガー, はなまる | 食費 (101) | 昼ご飯 (10104) |
| ファミリーマート, セブンイレブン, ローソン | 食費 (101) | 食料品 (10101) |
| ドトールコーヒー, Cafe Pic & Nic's | 食費 (101) | カフェ (10102) |
| Google, Appleサービス | 通信 (104) | 携帯電話料金 (10401) |
| PayPayほけん | 医療・保険 (110) | その他保険 (11099) |
| BOOKOFF, くまざわ書店, 丸善, コーチャンフォー | エンタメ (108) | 書籍 (10806) |
| PayPayカード請求 | その他 (199) | カードの引落 (19907) |
| ウエルシア, カインズ, キャンドゥ | 日用雑貨 (102) | 消耗品 (10201) |
| 東横INN | 大型出費 (114) | 旅行 (11401) |
| ラウンドワン, 喜楽里, 湯楽の里, 常総ONSEN | エンタメ (108) | レジャー (10801) |
| JINS | 美容・衣服 (111) | アクセサリー小物 (11102) |
| ファミリーレンタリース (学生宿舎) | 住まい (106) | 家賃 (10601) |
| 三井のリパーク | 交通 (103) | 駐車場 (10399) |
| クリーニング専科 | 美容・衣服 (111) | クリーニング (11108) |
| Amazon.co.jp | 日用雑貨 (102) | 消耗品 (10201) |
| ウェルビー (bar) | 交際費 (107) | 飲み会 (10701) |

Rules are evaluated by keyword length (longest first) to prevent short keyword false matches.

### Usage

```bash
# Dry run (preview only)
source /.skills/zaim.env
python3 /opt/data/workspace/scripts/zaim/categorize_and_subs.py --dry-run

# Full run (updates local DB + Zaim API)
python3 /opt/data/workspace/scripts/zaim/categorize_and_subs.py

# Subscription detection only
source /.skills/zaim.env
python3 /opt/data/workspace/scripts/zaim/categorize_and_subs.py --subscriptions-only
```

Workflow:
1. Queries local SQLite DB (`~/.zaim_cache/zaim.db`) for uncategorized transactions
2. Classifies each by place/name using keyword rules (50+ store patterns)
3. Updates local DB with category/genre IDs
4. Syncs to Zaim API via **full-field PUT requests** (sends ALL fields — see Pitfalls for why this matters)
5. Detects recurring subscription patterns

### Categorization Example

Example of auto-categorized transactions grouped by category:

- 食費 (101): スーパー、コンビニ、外食チェーンなど
- 日用雑貨 (102): ホームセンター、100円ショップ、Amazon.co.jp
- 通信 (104): Google, Appleサービス
- 医療・保険 (110): 保険サービス
- エンタメ (108): 書店、レジャー施設
- その他 (199): カード請求

_Categorization is a one-time batch operation. Actual transaction counts depend on your data._

### Subscription Detection Example

| Service | Monthly | Category | Period |
|---------|:-------:|----------|--------|
| Google | ¥xxx | 通信 | 継続中 |
| Appleサービス | ¥xx | 通信 | 継続中 |
| 保険サービス (old) | ¥xx | 医療・保険 | 終了 |
| 保険サービス (new) | ¥xx | 医療・保険 | 継続中 |

_Actual amounts and services will vary. Run the subscription detection script on your data._

### Recovery

If a previous partial-PUT batch zeroed your transaction amounts, use the recovery script at `scripts/recover_amount.py` (skill directory):

```bash
SKILL_SCRIPTS="/opt/data/workspace/skills/productivity/zaim-household-finance/scripts"

source /.skills/zaim.env
python3 "$SKILL_SCRIPTS/recover_amount.py" --dry-run  # preview
python3 "$SKILL_SCRIPTS/recover_amount.py"             # fix
```

### Subscription Detection

Analyzes ALL transaction history to identify recurring subscriptions across every category. Uses a comprehensive approach:

1. **Duplicate dedup first**: Merges same-date + same-amount + same-store transactions (PayPay CSV × PayPayカード double registration can significantly inflate counts)
2. **Cross-category scan**: Analyzes ALL categories, not just service-related ones
3. **Service keyword matching**: Google, Apple, PayPayほけん, etc.
4. **Monthly continuity check**: Minimum 2-month span for services, 3-month for non-service patterns
5. **Price-change detection**: Same store with multiple amounts (plan changes, price hikes)

### Subscription Detection Script

```bash
SKILL_SCRIPTS="/opt/data/workspace/skills/productivity/zaim-household-finance/scripts"

source /.skills/zaim.env
python3 "$SKILL_SCRIPTS/find_all_subscriptions.py"
```

Outputs:
- **確定サブスク** (confirmed subscriptions with monthly pattern)
- **要確認** (2-month patterns needing more data)
- **価格改定候補** (same store, different amounts — plan/price changes)

See `scripts/find_all_subscriptions.py` for the full analysis script and `references/subscription-detection.md` for the approach documentation.

## SQLite Local DB

The script `zaim.py` syncs all transaction history to a local SQLite cache at `~/.zaim_cache/zaim.db`:

```bash
source /.skills/zaim.env
python3 /opt/data/workspace/scripts/zaim/zaim.py sync
```

Schema (`transactions` table — via `sqlite3 ~/.zaim_cache/zaim.db`):

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER | Zaim transaction ID (higher = newer) |
| `date` | TEXT | Transaction date (YYYY-MM-DD) |
| `mode` | TEXT | `payment` (支出), `income` (収入), `transfer` (振替) |
| `amount` | INTEGER | Amount in JPY (positive for income, negative for payment) |
| `name` | TEXT | Store/transaction name |
| `place` | TEXT | Location text |
| `category_id` | INTEGER | FK → categories table |
| `genre_id` | INTEGER | FK → genres table |
| `from_account_id` | INTEGER | Source account (0 = 現金) |
| `to_account_id` | INTEGER | Destination account (for income: which account received) |
| `comment` | TEXT | User comment (e.g. "クレジット", "PayPayカード") |
| `active` | INTEGER | 1 = active, 0 = deleted |
| `receipt_id` | INTEGER? | Linked receipt |
| `currency_code` | TEXT | e.g. "JPY" |

Key query patterns:
- Find income entries (incl. credit card statements): `WHERE mode='income'`
- Find card or transfer account entries: `WHERE to_account_id = <card_account_id>`
- See all account IDs: `SELECT * FROM accounts`

Other tables: `categories`, `genres`, `accounts`, `meta` (last sync timestamp).

The DB is used for offline analysis before deciding which API calls to make.

PayPay app's CSV contains ALL transactions including those paid via PayPay Card (credit VISA). These card transactions are **also recorded on the card statement** separately, causing duplicates in Zaim if imported raw.

### Filter Rule
Remove rows where the **取引方法** (payment method) column contains:
- `"クレジット"` (credit)
- `"PayPayカード"`

These are handled by the card statement import separately.

### Workflow
```bash
# Step 1: Filter out card transactions from PayPay CSV
python3 ~/opt/data/workspace/scripts/zaim/filter_paypay_csv.py PayPay.csv -o PayPay_zaim.csv

# Step 2: Import filtered CSV to Zaim via API
# (see references/paypay-csv-import.md for full workflow)
```

### CSV Column Reference
CSV exported from PayPay app has these columns:
`取引日, 出金金額（円）, 入金金額（円）, 海外出金金額, 通貨, 変換レート（円）, 利用国, 取引内容, 取引先, 取引方法, 支払い区分, 利用者, 取引番号`

Key columns for import:
- `取引日` → Zaim `date`
- `出金金額（円）` → Zaim `amount` (negative = payment)
- `取引内容` / `取引先` → Zaim `name` / `place`
- `取引方法` → used for filtering only

## Checking Credit Card Bills (End-of-Month Payments)

Zaim models credit card statements as **income** transactions: the card company pays on your behalf (income into the card account), and the card bill due is the sum of those income entries for the statement period.

### Complete Billing Overview Workflow

When the user asks about monthly card payments, always produce a **complete overview of ALL active card accounts**, showing which have statement entries and which are missing. Card statement amounts in Zaim are often manually entered or from Zaim's aggregation feature and **may be inaccurate** — always present them with a caveat and ask the user to verify.

```python
import sqlite3, os

db = sqlite3.connect(os.path.expanduser('~/.zaim_cache/zaim.db'))
db.row_factory = sqlite3.Row

# 1. Find ALL active card/credit accounts (not just ones with entries)
#    active=1 = active account, active=-1 = inactive/old
card_accounts = db.execute('''
    SELECT * FROM accounts 
    WHERE (name LIKE '%カード%' OR name LIKE '%Olive%')
      AND active = 1
    ORDER BY name
''').fetchall()

# 2. Get this month's billing month (e.g. '2026-05')
month = '2026-05'  # or use strftime for 'now'

# 3. For each card, check if there's a statement entry this month
for acct in card_accounts:
    rows = db.execute('''
        SELECT t.date, t.amount, t.name, t.id
        FROM transactions t
        WHERE t.mode = 'income'
          AND t.to_account_id = ?
          AND strftime('%%Y-%%m', t.date) = ?
        ORDER BY t.date
    ''', (acct['id'], month)).fetchall()
    
    total = sum(r['amount'] for r in rows)
    status = f"¥{total:,}" if rows else "**未登録**"
    print(f"  {acct['name']}: {status}")
    for r in rows:
        print(f"    {r['date']} ¥{r['amount']:,}")

# 4. Also check payment-side entries (actual withdrawal from bank)
#    category 199/19907 = カードの引落
card_payments_monthly = db.execute('''
    SELECT t.date, t.amount, t.name, t.place
    FROM transactions t
    WHERE t.mode = 'payment'
      AND t.category_id = 199 AND t.genre_id = 19907
      AND strftime('%%Y-%%m', t.date) = ?
    ORDER BY t.date
''', (month,)).fetchall()
```

**Presentation format** (table view, markdown):

```
| カード | 請求額 | 備考 |
|-------|-------|------|
| カードA | ¥xx,xxx | ← 要確認 |
| カードB | ¥x,xxx | ← 要確認 |
| カードC | 未登録 | ← データなし |
| カードD | 未登録 | ← データなし |
```

### Accuracy Caveats

- **⚠ Card statement amounts in Zaim may be wrong.** They are often entered manually by the user or auto-imported via Zaim's aggregation feature (which may be unreliable). Always flag discrepancies and ask the user to confirm from their actual card statement.
- **⚠ Not all cards may have entries.** The user may have 4+ active cards but only some show in Zaim. Always query ALL active card accounts and flag missing ones.
- **⚠ The same ¥ amount appearing for two different card accounts** (one active, one inactive) suggests a duplicate entry on the old account.

### Heuristics

- **Income to card account** = card statement amount (the card issuer records what they paid)
- **Payment with category 199/19907 (カードの引落)** = the actual withdrawal from your cash account when you pay the bill
- **Comment field** often contains "クレジット" or "PayPayカード" — useful for filtering
- These amounts may appear 1–2 days before the actual withdrawal date (Zaim records the statement issue date, not the debit date)
- If the same ¥ amount appears under both an inactive and an active card account, the inactive entry is likely a stale duplicate

## Duplicate Detection Strategy (API-level)

After CSV filtering, add a second layer of protection when importing via API:

1. Fetch existing transactions for the date range via SQLite DB or OAuth1Session (see Pitfalls — `api.money()` may 401)
2. For each CSV row, check if a transaction with matching `(date + amount + place/name)` already exists
3. Skip if match found, insert if not

This prevents re-importing the same CSV accidentally.

## Duplicate Cleanup & Deletion

If duplicates already exist in Zaim (e.g., from an earlier un-filtered CSV import), bulk-delete them using the `scripts/delete_duplicates.py` tool.

### How It Works

The script connects to the local SQLite cache (`~/.zaim_cache/zaim.db`), finds transaction pairs with identical `(date, amount, place)` across different Zaim IDs, and **deletes the higher-ID copy** (the newer import — typically the duplicate).

### Usage

The script lives in this skill's `scripts/` directory:

```bash
SKILL_SCRIPTS="/opt/data/workspace/skills/productivity/zaim-household-finance/scripts"

# Step 0: Ensure local DB is up-to-date
source /.skills/zaim.env && python3 /opt/data/workspace/scripts/zaim/zaim.py sync

# Step 1: Preview duplicates
python3 "$SKILL_SCRIPTS/delete_duplicates.py" --dry-run

# Step 2: Delete (with confirmation summary)
python3 "$SKILL_SCRIPTS/delete_duplicates.py"

# Filters:
python3 "$SKILL_SCRIPTS/delete_duplicates.py" --min-amount 500          # only ¥500+
python3 "$SKILL_SCRIPTS/delete_duplicates.py" --only-store "カスミ"     # only specific store
python3 "$SKILL_SCRIPTS/delete_duplicates.py" --max-delete 50           # stop after 50 deletes
python3 "$SKILL_SCRIPTS/delete_duplicates.py" --keep-older               # delete lower ID instead
```

### Real-world Example

When investigating duplicate transactions at scale:

1. **Duplication rate**: A significant portion of transactions may be duplicates (PayPay CSV × card statement double registration)
2. **ID range analysis**: Two distinct ID ranges can indicate batch import artifacts (original import vs re-import)
3. **Cause**: CSV imported without the filter rule, then card statement imported separately
4. **No reliable timestamp sorting**: Zaim API does NOT expose `created_at` or `updated_at` in its transaction response. The only way to identify the duplicate copy is by ID ordering (higher ID = newer import). The script deletes higher IDs by default.
5. **Rate limiting**: Zaim API returns 429 if called too fast. The script enforces 1-second delays between DELETE calls.

### Verification After Deletion

```bash
SKILL_SCRIPTS="/opt/data/workspace/skills/productivity/zaim-household-finance/scripts"

# Re-sync local DB
source /.skills/zaim.env && python3 /opt/data/workspace/scripts/zaim/zaim.py sync

# Verify duplicate count dropped
python3 "$SKILL_SCRIPTS/delete_duplicates.py" --dry-run

# Also re-run subscription detection to see clean counts
python3 "$SKILL_SCRIPTS/find_all_subscriptions.py"
```

### Duplicate Detection Heuristics

| Signal | Meaning |
|--------|---------|
| Same `(date, amount, place)` across multiple IDs | Definite duplicate |
| ID gap of 2,000–5,000 between pairs | Batch import artifact (CSV re-import) |
| One has `comment` "クレジット" / "PayPayカード", other has "PayPayマネーライト" | Card vs balance split |
| Same date, same store, different amounts | NOT a duplicate — likely separate purchases |
| Different date, same amount, same store | NOT a duplicate — likely subscription |

## Useful Python Patterns

```python
import zaim
from datetime import datetime, timedelta

# Initialize
api = zaim.Api(
    consumer_key='...',
    consumer_secret='...',
    access_token='...',
    access_token_secret='...'
)

# Verify
user = api.verify()

# List categories (to find IDs)
cats = api.category()
for c in cats['categories']:
    print(f"{c['id']}: {c['name']}")

# Add a payment
result = api.payment(
    category_id='101',        # 食費
    genre_id='10101',         # 食費 > 食料品
    amount=980,
    date='YYYY-MM-DD',
    comment='スーパーでの買い物',
    name='店舗名',
    place='場所',
    from_account_id=0          # 0 = 現金, or account ID
)

# ⚠ api.money() may return 401 (see Pitfalls). Fallback:
from requests_oauthlib import OAuth1Session
import os
s = OAuth1Session(
    os.environ['ZAIM_CONSUMER_KEY'],
    client_secret=os.environ['ZAIM_CONSUMER_SECRET'],
    resource_owner_key=os.environ['ZAIM_ACCESS_TOKEN'],
    resource_owner_secret=os.environ['ZAIM_ACCESS_TOKEN_SECRET']
)
resp = s.get('https://api.zaim.net/v2/home/money', params={
    'mode': 'payment', 'start_date': 'YYYY-MM-01', 'end_date': 'YYYY-MM-31', 'limit': 500
})
money = resp.json()  # ← use this instead of api.money()

# Delete a transaction (e.g. after detecting duplicate)
api.delete(mode='payment', money_id=12345)

# Update a transaction
api.update(mode='payment', money_id=12345, amount=1500, comment='訂正')
```

## Category Audit (カテゴリ監査)

データ品質を保つため、食費カテゴリ外の取引に外食店名が含まれていないか、また食費内のジャンル割り当てが適切かを定期的にチェックする。

監査用のSQLクエリ・キーワードリスト・修正手順は `references/category-audit.md` を参照。

よくある誤検出パターン:
- 「ざわ」→ くまざわ書店（書店）に誤マッチするので注意
- モスバーガー等のファストフードが交際費/飲み会に分類されていないか確認
- ウエルシアやAmazonでの食品購入は、一般的に日用雑貨として扱う（何を買ったか確認できない場合）

## Important Notes

- **Rate limits**: Apply reasonable delays between API calls (at least 1 second)
- **Encoding**: Zaim import expects UTF-8 with BOM (`utf-8-sig`) for CSV
- **Account ID**: `from_account_id=0` means 現金 (cash). Get actual account IDs via `api.account()`
- **Mapping**: Always pass `mapping=1` for the default mapping
- **模式（mode）**: `payment` = expense, `income` = revenue, `transfer` = transfer
- **Terms of Service reminder**: API data can only be used for the registered app's purpose. No sharing with third parties.

## Pitfalls

- **⚠ Public release audit**: Before pushing skill files to a public GitHub repo, run the security audit checklist in `references/pre-publication-audit.md`. This skill directory contains references to real transaction IDs, absolute paths, and credential patterns that must be sanitized before public exposure. The audit covers: hardcoded credentials, usernames, domain names, absolute paths, transaction IDs, and API endpoint references.
- **⚠ Never hardcode API credentials in scripts**: `scripts/recover_amount.py` previously had Consumer Key, Consumer Secret, Access Token, and Access Token Secret hardcoded as Python string literals. This is a **security risk** — anyone with read access to the file can impersonate your Zaim account. Always store credentials in `/opt/data/workspace/.zaim_credentials` and read them from environment variables (`os.environ[...]`). All scripts in this skill now follow this pattern — never revert to hardcoded values.
- **⚠ PUT overwrites ALL fields**: When calling `PUT /home/money/{mode}/{id}` with `requests.put()` directly, Zaim's API **resets any omitted field to its default** (amount → 0, name → blank). You MUST send the complete transaction payload including `amount`, `date`, `name`, `place`, `comment`, `from_account_id`, `to_account_id`, `currency_code` — not just the fields you're changing. The `zaim` Python library's `api.update()` handles this internally; only raw `requests.put()` calls need manual full-field construction.
- **⚠ `api.money()` may return 401**: The `zaim` Python library's `api.money()` method can return HTTP 401 Unauthorized even when other methods (`api.account()`, `api.category()`, `api.payment()`) work fine with the same credentials. Cause is unclear — possibly the `mapping` parameter or a library bug. **Workaround**: Use raw `requests_oauthlib.OAuth1Session` to call `GET https://api.zaim.net/v2/home/money` directly (see Useful Python Patterns for the exact code pattern). This workaround is reliable for all filter combinations (mode, start_date, end_date, limit).
- **⚠ Duplicate inflation skews analysis**: A significant portion of transactions may be duplicates (PayPay CSV × PayPayカード double registration). Always dedup by (date + amount + place) before any analysis — especially subscription detection, where duplicates make counts appear higher than reality.
- **⚠ Cross-category subscription scan**: Don't limit subscription detection to service categories (通信・エンタメ・医療保険). Services like Amazon定期便 appear in 日用雑貨. Always scan ALL categories.
- **Duplicate imports**: Always filter PayPay CSV first; even then, check for existing transactions by date+amount+place before inserting
- **OAuth token expiry**: Access tokens currently don't expire for Zaim, but store them securely
- **Missing genre IDs**: Some categories require a genre_id. Always check `api.genre()` to find valid combinations
- **Date format**: Use `YYYY-MM-DD` format for all date parameters
- **place vs name**: Zaim has both `name` (transaction name) and `place` (location). PayPay's `取引内容` maps better to `name`, `取引先` maps to `place`
