# Bulk Zotero Sync Patterns (1,000+ Items)

Patterns discovered during large-corpus literature-acquisition syncs (1,700+
items) to Zotero via the Web API.

## No-op Update Skipping

Zotero `PATCH` is slow (≈600–1,200 ms per item). When re-running a sync
where most items are already correct, compare current state before PATCHing
to avoid redundant API calls:

```python
def should_update(item_data, new_collections, new_tags, new_issue):
    current_tags = {t.get('tag') for t in (item_data.get('tags') or [])
                    if isinstance(t, dict)}
    desired_tags = {t.get('tag') for t in new_tags}
    collections_ok = set(item_data.get('collections') or []) == set(new_collections)
    tags_ok = current_tags == desired_tags
    issue_ok = str(item_data.get('issue') or '') == str(new_issue)
    return not (collections_ok and tags_ok and issue_ok)
```

This reduced a 1,700-item re-sync from ≈1,200 PATCH calls to ≈25 actual
changes, cutting runtime from ~10 minutes to ~30 seconds.

## API Timeout for Bulk Operations

Zotero API can be slow under load. Use **120-second timeout** for `GET /items/top`
and `PATCH` calls, not the default 60 seconds:

```python
resp = session.request(method, url, timeout=120)
```

Without this, large `GET /items/top` calls (fetching the whole library for
DOI/title matching) time out at 60 seconds.

## `firstName` Required When `lastName` Is Set

Zotero rejects creator objects where `lastName` is present but `firstName` is
missing. For single-name authors (e.g., "Plato", institutional authors), use an
empty string:

```python
# ❌ WRONG — Zotero returns 400
{'creatorType': 'author', 'lastName': 'Plato'}

# ✅ CORRECT
{'creatorType': 'author', 'firstName': '', 'lastName': 'Plato'}
```

## `issue` Field Type Restriction

The `issue` field (Japanese UI: 「番号」) is only valid for item types that
support it, primarily `journalArticle`. Patching `issue` on `book`,
`bookSection`, `conferencePaper`, etc. returns **400**:

```python
# ❌ WRONG — 400 on non-journalArticle types
patch = {'issue': '42'}

# ✅ CORRECT — guard by item type
patch = {}
if item_data.get('itemType') == 'journalArticle':
    patch['issue'] = '42'
```

When using `issue` for relevance scores, store the score in tags as a fallback
(`relevance:42`) so non-article items still carry the score.

## Background Processing for Large Syncs

For syncs with 500+ create operations, use `terminal(background=True)` with
`notify_on_complete=True` and a 600-second timeout. Each item creation takes
~200–500 ms; 1,000 items ≈ 5–10 minutes.

If the foreground times out at 600s, the script is idempotent — re-run it and
no-op skipping will pick up where it left off.
