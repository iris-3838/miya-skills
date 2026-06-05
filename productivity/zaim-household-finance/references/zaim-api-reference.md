# Zaim API v2 Reference

Base URL: `https://api.zaim.net/v2`

Discovered from the `hiromu2000/zaim` Python library source code and API docs portal (dev.zaim.net).

## Authentication (OAuth 1.0a)

Zaim uses 3-legged OAuth 1.0a. Full flow:

### Step 1: Get Consumer Key/Secret
- Register at https://dev.zaim.net → create an application
- You receive `consumer_key` and `consumer_secret`

### Step 2: Get Request Token & Authorize
```http
POST /v2/auth/request
```
Parameters: `oauth_callback` (URL-encoded callback URI)

Response: `oauth_token=xxx&oauth_token_secret=xxx&oauth_callback_confirmed=true`

User must then visit the authorization URL:
```
https://auth.zaim.net/users/auth?oauth_token={request_token}
```

After authorizing, the callback URL contains `oauth_verifier=xxx`.

### Step 3: Get Access Token
```http
POST /v2/auth/access
```
Parameters: `oauth_verifier` (from the callback after user authorizes)

Response: `oauth_token=xxx&oauth_token_secret=xxx`

### Step 4: Verify Connection
```http
GET /v2/home/user/verify
```
With OAuth 1.0 auth header using all 4 tokens. Returns user name/email on success.

### Interactive Setup Script
A ready-to-use script exists at `/opt/data/workspace/scripts/zaim/zaim_token_setup.py`. Run it, input Consumer Key/Secret, and it walks through the full OAuth flow interactively:

```bash
python3 /opt/data/workspace/scripts/zaim/zaim_token_setup.py
```

### Python Implementation
```python
from requests_oauthlib import OAuth1
import requests
from urllib.parse import parse_qsl

# Step 2
auth = OAuth1(consumer_key, consumer_secret, callback_uri='...')
r = requests.post('https://api.zaim.net/v2/auth/request', auth=auth)
token = dict(parse_qsl(r.text))

# Step 3
auth = OAuth1(consumer_key, consumer_secret,
              token['oauth_token'], token['oauth_token_secret'],
              verifier=oauth_verifier)
r = requests.post('https://api.zaim.net/v2/auth/access', auth=auth)
access = dict(parse_qsl(r.text))
```

Simpler: use `pip install zaim` and the `zaim.Api` class.

## Endpoints

### GET /home/user/verify
Verify authentication status. Returns user info.

### GET /home/money
List transactions with optional filters.

Parameters:
- `mapping` (int, default 1)
- `category_id` (int) — filter by category
- `genre_id` (int) — filter by genre (subcategory)
- `mode` (str) — `payment`, `income`, or `transfer`
- `order` (str) — sort order (e.g. `date`)
- `start_date` (str) — `YYYY-MM-DD`
- `end_date` (str) — `YYYY-MM-DD`
- `page` (int) — pagination
- `limit` (int) — results per page
- `group_by` (str) — group results

Response shape:
```json
{
  "money": [
    {
      "id": 12345,
      "user_id": 1,
      "date": "YYYY-MM-DD",
      "mode": "payment",
      "category_id": 101,
      "genre_id": 10101,
      "amount": 980,
      "from_account_id": 0,
      "to_account_id": null,
      "name": "店舗名",
      "place": "場所",
      "comment": "メモ",
      "active": 1,
      "receipt_id": null,
      "currency_code": "JPY",
      "created": "YYYY-MM-DD HH:MM:SS",
      "updated": "YYYY-MM-DD HH:MM:SS"
    }
  ],
  "request": "..."
}
```

### POST /home/money/payment
Register a payment (expense).

Parameters:
- `mapping` (int, default 1) **required**
- `category_id` (int) **required**
- `genre_id` (int) **required** (some categories require it)
- `amount` (int) **required** — amount in yen (positive integer)
- `date` (str) **required** — `YYYY-MM-DD`
- `from_account_id` (int) **required** — account to draw from (0 = cash)
- `comment` (str) — memo/notes
- `name` (str) — transaction name
- `place` (str) — location/store name

### POST /home/money/income
Register income.

Parameters:
- `mapping`, `category_id`, `amount`, `date`, `to_account_id`, `comment`, `place`

### POST /home/money/transfer
Register transfer between accounts.

Parameters:
- `mapping`, `amount`, `date`, `from_account_id`, `to_account_id`, `comment`

### DELETE /home/money/{mode}/{id}
Delete a transaction.

`mode` is one of: `payment`, `income`, `transfer`
`id` is the transaction's numeric ID.

### PUT /home/money/{mode}/{id}
Update a transaction.

**⚠ CRITICAL: Partial updates not supported.** Zaim's PUT replaces the entire record. Any field omitted from the request body is **reset to its default value** (amount → 0, name → blank, etc.). You must send ALL fields you want to preserve:

```python
data = {
    "category_id": tx["category_id"],
    "genre_id": tx["genre_id"],
    "amount": tx["amount"],           # ← required, otherwise 0
    "date": tx["date"],
    "name": tx["name"] or "",
    "place": tx["place"] or "",
    "comment": tx["comment"] or "",
    "from_account_id": tx["from_account_id"],
    "to_account_id": tx["to_account_id"],
    "currency_code": tx["currency_code"],
}
r = api_put(url, auth=auth, data=data)
```

The `zaim` library's `api.update()` handles this internally. Only custom `requests.put()` calls are affected.

Supports updating: `amount`, `place`, `name`, `date`, `from_account_id`, `to_account_id`, `genre_id`, `category_id`, `comment`, `mapping`.

### GET /home/category
List all categories. Returns:
```json
{
  "categories": [
    {"id": 101, "name": "食費", "mode": "payment", "sort": 1, "active": 1, "parent_category_id": null, "modified": "..."}
  ]
}
```

### GET /home/genre
List all genres (subcategories). Each genre belongs to a category.

### GET /home/account
List all accounts. Returns:
```json
{
  "accounts": [
    {"id": 0, "name": "現金", "mode": "payment", "sort": 0, "active": 1, "parent_account_id": null, "modified": "..."}
  ]
}
```

### GET /home/currency
List available currencies (no auth required).

### Public Endpoints (No Auth)
- `GET /v2/account`
- `GET /v2/category`
- `GET /v2/genre`
- `GET /v2/currency`

These return default/master data without authentication.

## Terms of Service (dev.zaim.net/portal/tos)

Effective: January 1, 2025 (last revised). Provider: Kufu Company Inc.

Key clauses for personal use:
- **Article 3**: Developer registration required — 1 application per registration
- **Article 5**: Non-exclusive license for providing the registered service
- **Article 6**: Must clearly explain how user's financial data is used
- **Article 13**: Member authentication tokens must be strictly managed
- **Article 14**: Household financial data obtained via API can only be used for the registered service — no third-party sharing
- **Article 16**: Prohibited acts — includes reverse engineering, excessive load, competing with Zaim
- **Article 22**: Zaim disclaims liability for API errors or service interruptions
- **Article 25**: Governed by Japanese law, Tokyo District Court jurisdiction

## Python Library

`pip install zaim requests_oauthlib --break-system-packages` (by hiromu2000, 3 stars on GitHub)

Note: `--break-system-packages` is required on Debian-based systems with PEP 668 restrictions. Install works to user-site (`~/.local/bin`).

Features:
- `zaim.Api` — core CRUD operations
- `zaim.ExtendedApi` — adds client-side search filtering for transactions, categories, genres, accounts
- CLI tool (`zaim` command) with env var config

Note: The official API docs at dev.zaim.net require login to view.

## Rate Limiting

No official rate limit documented. Practical recommendation: at least 1 second between API calls. For batch imports, use a small delay or track `X-RateLimit-*` response headers if present.

## API Docs Availability

The official API documentation at `https://dev.zaim.net/home/api/overview` requires **login** — it redirects to a login form. The only publicly accessible page is the terms of service at `/portal/tos`. No other doc pages (reference, endpoints, guide, faq, auth, oauth) are publicly available. Endpoint information was reconstructed from open-source Python wrapper libraries (`hiromu2000/zaim`, `konomae/zaimpy`).
