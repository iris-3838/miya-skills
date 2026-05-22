# PayPay CSV → Zaim Import Workflow

## Problem

PayPay app CSV exports contain ALL transaction types:
- **Balance payments** (PayPay残高): should be imported to Zaim
- **Point payments** (PayPayポイント): should be imported to Zaim
- **PayPay Card (クレジット VISA)**: **should NOT be imported** — these transactions are already recorded on the credit card statement which is imported separately to Zaim

Importing the raw CSV causes **double-counting** of credit card transactions.

## Solution

Filter out credit card transactions BEFORE importing to Zaim.

### Filter Logic

Exclude rows where the `取引方法` (payment method) column contains either:
- `"クレジット"` (covers "クレジット VISA ****" etc.)
- `"PayPayカード"` (covers "PayPayカード VISA ****" etc.)

Keep rows with methods like:
- `"PayPayマネーライト"` (balance)
- `"PayPayポイント"` (points)
- `"PayPayあと払い"` (postpaid — verify if this should be included)
- `"銀行口座"` (bank account)

## Filter Script

Location: `/workspace/scripts/zaim/filter_paypay_csv.py` (host: `~/workspace/scripts/zaim/filter_paypay_csv.py`)

### Usage
```bash
# Dry-run (preview what would be removed)
python3 ~/workspace/scripts/zaim/filter_paypay_csv.py PayPay.csv --dry-run

# Filter and save
python3 ~/workspace/scripts/zaim/filter_paypay_csv.py PayPay.csv -o PayPay_zaim.csv

# Custom column name (if different locale)
python3 ~/workspace/scripts/zaim/filter_paypay_csv.py PayPay.csv -o output.csv --method-col "取引方法"
```

### Script Features
- UTF-8 BOM encoding (`utf-8-sig`) — Zaim-compatible
- Preserves all columns, removes only filtered rows
- Shows summary: total rows, removed rows (with details), kept rows
- Dry-run mode: shows what would be removed without writing
- Customizable method column name via `--method-col`

## CSV Format Reference

PayPay CSV columns (verified from actual export):
```
取引日, 出金金額（円）, 入金金額（円）, 海外出金金額, 通貨, 変換レート（円）, 利用国, 取引内容, 取引先, 取引方法, 支払い区分, 利用者, 取引番号
```

| Column | Description | Zaim Mapping |
|--------|-------------|-------------|
| 取引日 | Transaction date | `date` |
| 出金金額（円） | Withdrawal amount (yen) | `amount` (payment) |
| 入金金額（円） | Deposit amount (yen) | `amount` (income) |
| 海外出金金額 | Overseas withdrawal | — |
| 通貨 | Currency | — |
| 変換レート（円） | Exchange rate | — |
| 利用国 | Country used | — |
| 取引内容 | Transaction detail | `name` |
| 取引先 | Merchant name | `place` |
| 取引方法 | Payment method | **Filter column** |
| 支払い区分 | Payment category | — |
| 利用者 | User | — |
| 取引番号 | Transaction number | — |

## Full Import Workflow

```
1. Export CSV from PayPay app
2. Run filter script → PayPay_zaim.csv
3. (Optional) Import filtered CSV to Zaim via CSV upload
4. (Recommended) Import via Zaim API with duplicate check

For API import:
  a. GET /home/money (filter by date range)
  b. For each filtered CSV row:
     - Check if (date + amount + place) exists
     - If match → skip
     - If no match → POST /home/money/payment
  c. Add 0.5-1s delay between API calls
```

## Test Verification

Testing with sample data:
- Card-payment rows were removed
- Balance/point-payment rows were kept
- All filtered rows correctly identified as card transactions

## Existing Duplicate Cleanup

If a raw (unfiltered) CSV was imported before the filter rule was added, Zaim already contains duplicate transaction pairs. These can be cleaned up via batch DELETE:

```
# 1. Sync local DB
source /workspace/.zaim_env && python3 /workspace/scripts/zaim/zaim.py sync

# 2. Preview duplicates
python3 /workspace/skills/productivity/zaim-household-finance/scripts/delete_duplicates.py --dry-run

# 3. Delete duplicates
python3 /workspace/skills/productivity/zaim-household-finance/scripts/delete_duplicates.py
```

See `scripts/delete_duplicates.py` in the skill for full documentation.

### Batch Import ID Ranges

When PayPay CSV is imported without filtering, duplicates span two ID ranges:
- **xxxxxx1xxx** — Original import (lower IDs, keep)
- **xxxxxx2xxx** — Re-import (higher IDs, ~4,000 gap, delete)

Zaim API does not expose `created_at`, so the only way to identify which is the duplicate is by ID ordering (higher = newer).

## Known Edge Cases

- **PayPayあと払い**: Verify whether this is a credit-type product or a separate payment method. If it has its own statement, exclude it too.
- **PayPayカード分割払い**: These appear as "クレジット" in the method column and are correctly filtered.
- **Empty rows**: The script handles them gracefully.
- **Encoding**: Zaim CSV upload requires BOM; the filter script outputs `utf-8-sig`.
