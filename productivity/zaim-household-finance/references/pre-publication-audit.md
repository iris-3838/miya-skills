# Pre-Publication Security Audit Checklist

Use this checklist when preparing any part of the Hermes skills repo (or any Git repo containing Hermes skill files) for public GitHub release. Followed during the May 2026 repo restructure audit.

## Scan Scope

Scan ALL non-gitignored files under the repo root. Exclude:
- `.skills/` (known private directory)
- `.git/`
- Files listed in `.gitignore`

## Audit Checklist (grep + manual review)

### 1. Usernames & Personal Identifiers

```bash
grep -rnP '(realname|username|handle|nickname|email@example\.com)' . --include='*.md' --include='*.py' --include='*.yaml' --include='*.yml' --include='*.json' --include='*.toml' --include='*.cfg' --include='*.ini'
```

Check for:
- Real names / nicknames / online handles
- Email addresses (`@domain`)
- GitHub usernames that link accounts

**Action**: Replace with generic terms (`user`, `owner`, `[handle]`).

### 2. Domain Names & Project Identifiers

Check for private domain names, internal project codenames, or subdomain patterns that could identify the user's infrastructure.

**Action**: Redact if the domain is not already public.

### 3. Hardcoded Credentials

```bash
grep -rnP '(api.?key|secret|token|password|credential|bearer|jwt)' --include='*.py' . | grep -v 'os.environ' | grep -v '.git/'
```

**Pass condition**: Every credential reference reads from `os.environ[...]` or similar env-variable mechanism. No string literals containing real keys/tokens/secrets.

### 4. Transaction IDs / Financial Data

Look for numeric patterns that look like real transaction IDs, account numbers, or monetary amounts that could be linked to specific purchases.

**Action**: Mask with `xxxx` placeholders or remove specific values.

### 5. Absolute Paths

```bash
grep -rnP '(/\w+){4,}' --include='*.md' --include='*.py' . | grep -v '.git/' | grep -v 'http' | grep -v 'localhost'
```

Check for: `/opt/data/workspace/skills/productivity/zaim-household-finance/scripts/...` etc.

**Action**: Replace with relative paths where possible (e.g., `scripts/foo.py` instead of `/opt/data/workspace/skills/.../scripts/foo.py`).

### 6. API Endpoint References

- Check if API URLs (OAuth endpoints, base URLs) are public documentation or internal-facing
- Zaim dev.zaim.net endpoints are public — OK
- Internal/mock/staging endpoints should be redacted

### 7. Localhost References

`localhost:PORT` references in skill docs are generally OK (they describe local developer workflows). But verify:
- No hardcoded passwords in localhost URLs
- No internal-only service names

## Publishing Decision Guide

| Finding | Action |
|---------|--------|
| Hardcoded API key/token | 🔴 **Blocking** — fix before any push |
| Username / real name | 🟡 Recommend redact |
| Private domain name | 🟡 Recommend redact or move to `.skills/` |
| Absolute paths | 🟢 Fix if trivial, otherwise OK |
| Transaction IDs | 🟡 Redact or verify mock |
| Email address | 🔴 **Blocking** — remove before push |
| EBSCO customer ID | 🟡 Redact |
| Nothing sensitive found | ✅ Safe to push |
