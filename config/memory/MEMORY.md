seimiya's task management: Always use Super Productivity (SP) REST API (localhost:3876) for all task operations — add, modify, complete, etc. Do NOT use the todo tool for user-facing task management. SP is the canonical task source.
§
PayPay→Zaim: filter_csv excludes rows where 取引方法 contains クレジット/PayPayカード. Script: /workspace/scripts/zaim/filter_paypay_csv.py
§
Zotero翻訳運用: 基本はオンデマンド（ユーザー「この論文を処理して」→私が実行）。Zotero Connectorで登録→合図→pdf2zh-next翻訳→llm-kb保存+git push の流れ。操作の都度git remoteと同期する.
§
Skills repo: /workspace/skills/ → git@github.com:iris-3838/miya-skills.git (SSH). /workspace/ 777 perms, Hermes uid 10000 can r/w all subdirs. Public skills scan for secrets before push.
§
KB (llm-kb.miya-lis.net): Karpathy-style — Agent Zone (concepts/comparisons/entities/queries/index.md/log.md) agent-managed, Human Zone (raw/) human-placed. Write: direct (o+w). Location: /workspace/llm-kb.miya-lis.net/. Git: ryoryoryo3838/llm-kb.miya-lis.net (GitHub). Obsidian未接続。Design philosophy encoded in llm-kb-wiki skill.
§
OpenCode Go: key at /workspace/.private/opencode_api.json. ep=https://opencode.ai/zen/go/v1. Use qwen3.5-plus for stable translation. deepseek-v4-flash needs small chunks due to reasoning content issue. Full model list in pdf-to-bilingual-kb/references/opencode-api-models.md.
§
seimiya prefers enhancing existing systems over building parallel components. When adding new behavior to an existing UI pattern, modify the existing system (e.g., data-expand-col on cards) rather than creating a separate component that duplicates functionality.
§
Demo site ExpandableGrid: sub-cards use flat (shadowless, no hover lift) styling — not inverted (rejected), not accent-border (rejected). Group visual distinction via shadow removal only. FLIP stagger direction reverses based on movement: items moving UP animate bottom→first, items moving DOWN animate top→first.
§
PDF翻訳: seimiyaの既定はpdf2zh-next（レイアウト保持）。長文書籍(150p)は3h+かかるが待つ。CIDフォント問題:babeldoc拒否→pymupdfでHelvetica標準フォント再保存で回避、レイアウト犠牲だが通る。markitdown+LLM翻訳はpdf2zhが遅すぎる場合のフォールバック。pdf-to-kbはバッチ処理専用。