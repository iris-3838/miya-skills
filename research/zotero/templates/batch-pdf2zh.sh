#!/usr/bin/env bash
# Batch translate Zotero items to bilingual EN→JA PDF using pdf2zh-next
#
# Usage:
#   1. Edit ITEMS array below with your Zotero parent item keys
#   2. Optionally change ENGINE_ARGS (default: openaicompatible / deepseek-v4-flash)
#   3. Run: bash templates/batch-pdf2zh.sh
#
# Monitor progress: each item prints start/completion lines.
# Output goes to: /opt/data/workspace/llm-kb.miya-lis.net/raw/papers/zotero_pdf2zh/<title>__<key>/translated/
#
set -euo pipefail

# ─── Configuration ────────────────────────────────────────────────────────────

SCRIPT_DIR="/opt/data/workspace/miya-skills/research/zotero"
SCRIPT="$SCRIPT_DIR/.venv/bin/python $SCRIPT_DIR/scripts/zotero_pdf2zh.py"

ENGINE_ARGS="--engine openaicompatible \
  --openai-compatible-model deepseek-v4-flash \
  --openai-compatible-base-url https://opencode.ai/zen/go/v1 \
  --openai-compatible-api-key-env OPENCODE_GO_API_KEY \
  --lang-in en --lang-out ja"

# Override with --bing for free tier (no API key needed):
# ENGINE_ARGS="--lang-in en --lang-out ja"

# ─── Items to translate ──────────────────────────────────────────────────────
# Fill with Zotero parent item keys. Check PDF attachment availability first:
#   python3 -c "
#   from pyzotero.zotero import Zotero; import json
#   c=json.load(open('/opt/data/workspace/.skills/zotero_credentials.json'))
#   z=Zotero(c['user_id'],'user',c['api_key'])
#   for item in z.collection_items_top('COLLECTION_KEY'):
#     k=item['data']['key']
#     pdfs=[x for x in z.children(k) if x['data'].get('contentType')=='application/pdf']
#     print(f'{k}: {len(pdfs)} PDF(s)')
#   "

declare -a ITEMS=(
  # "YYYYYYYY"  # Author (Year) - Title
)

# ─── Run ──────────────────────────────────────────────────────────────────────

source /opt/data/.env

if [ -z "${OPENCODE_GO_API_KEY:-}" ]; then
  echo "ERROR: OPENCODE_GO_API_KEY not set. Check /opt/data/.env"
  exit 1
fi

cd "$SCRIPT_DIR"
TOTAL=${#ITEMS[@]}

for i in "${!ITEMS[@]}"; do
  ITEM="${ITEMS[$i]}"
  NUM=$((i+1))
  echo ""
  echo "========================================="
  echo "[$NUM/$TOTAL] Translating: $ITEM"
  echo "========================================="
  $SCRIPT --item "$ITEM" $ENGINE_ARGS 2>&1 && \
    echo "✅ [$NUM/$TOTAL] Done: $ITEM" || \
    echo "❌ [$NUM/$TOTAL] Failed (exit=$?): $ITEM"
done

echo ""
echo "Done — $TOTAL items processed."
echo "Output: /opt/data/workspace/llm-kb.miya-lis.net/raw/papers/zotero_pdf2zh/"
