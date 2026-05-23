#!/usr/bin/env python3
"""
Zotero API credentials setup.
Stores credentials outside SKILL.md in .private/ directory.
"""
from __future__ import annotations

import json
import sys
import getpass
from pathlib import Path

PRIVATE_DIR = Path("/workspace/.private")
CRED_FILE = PRIVATE_DIR / "zotero_credentials.json"


def probe_api_key(user_id: str, api_key: str) -> bool:
    """Verify API key by hitting the /keys/current endpoint."""
    import httpx
    try:
        resp = httpx.get(
            "https://api.zotero.org/keys/current",
            headers={"Zotero-API-Key": api_key, "Zotero-API-Version": "3"},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            actual_user = str(data.get("userID", ""))
            if actual_user != user_id:
                print(f"⚠ Warning: Provided userID ({user_id}) differs from key's owner ({actual_user})")
                print(f"  Using userID from key: {actual_user}")
            return True
        print(f"✗ API key verification failed: HTTP {resp.status_code}")
        print(f"  Response: {resp.text[:200]}")
        return False
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False


def main() -> int:
    PRIVATE_DIR.mkdir(parents=True, exist_ok=True)
    CRED_FILE.parent.mkdir(parents=True, exist_ok=True)

    print("=== Zotero API Credentials Setup ===\n")

    if CRED_FILE.exists():
        existing = json.loads(CRED_FILE.read_text())
        print(f"Existing credentials found for userID: {existing.get('user_id', '?')}")
        overwrite = input("Overwrite? [y/N] ").strip().lower()
        if overwrite != "y":
            print("Keeping existing credentials.")
            return 0

    user_id = input("Zotero Web API User ID: ").strip()
    if not user_id.isdigit():
        print("Error: User ID must be numeric.")
        return 2

    api_key = getpass.getpass("Zotero Web API Key (input hidden): ").strip()
    if not api_key:
        print("Error: API key cannot be empty.")
        return 2

    print("\nVerifying API key...")
    if not probe_api_key(user_id, api_key):
        retry = input("Verification failed. Save anyway? [y/N] ").strip().lower()
        if retry != "y":
            return 2

    credentials = {"user_id": user_id, "api_key": api_key}
    CRED_FILE.write_text(json.dumps(credentials, indent=2) + "\n")
    CRED_FILE.chmod(0o600)  # owner-read/write only
    print(f"\n✓ Credentials saved to {CRED_FILE}")
    print("  Note: This file is git-ignored and permission-restricted (0600).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
