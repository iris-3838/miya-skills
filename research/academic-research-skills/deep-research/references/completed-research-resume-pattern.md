# Resuming a Completed Deep Research Project

When the user says "resume [research topic] deep research session" and the project's Kanban board shows **all phases complete**, the task is **not** to re-run the pipeline. The goal is to re-engage the user with what was produced and offer concrete next steps.

## Workflow

1. **Find the session** via `session_search(query="topic keywords", limit=5)`. Use multiple queries if the first attempt misses:
   - Topic-specific terms (e.g. "Bates Hjørland information concept")
   - Zotero collection names (e.g. "deep-research/bates-vs-hjrland")
   - Board slug patterns (e.g. "ars-marcia-j-batesbirger-hjrland-2000")

2. **Check Kanban board status** — `hermes kanban --board <slug> list`. If the board has 6 phases all `done`, the pipeline itself is complete.

3. **Check llm-kb deliverables** — list files under `llm-kb.miya-lis.net/concepts/<project-slug>/`. Key files to inspect:
   - `phase-4-composition.md` (main paper draft, usually largest)
   - `phase-3-analysis.md` (analytical synthesis)
   - `presentation-*.md` (if generated, often the most polished summary)
   - `critique-*.md`, `supplementary-*.md` (optional deep-dives)

4. **Report status concisely** — show a table of phases/deliverables with file sizes, then offer 3–4 concrete options:
   - Review/improve the main composition
   - Export findings as presentation/slides
   - Extend research (new angle, Floridi, additional sources)
   - Read a specific phase to decide next

## Pitfalls

- **"Resume" ≠ "the work was paused"** — the project may be fully complete; treat it as re-engagement, not continuation.
- **Don't re-run the pipeline** — the user wants to see what was done, not repeat it.
- **llm-kb may have stale counts** — verify Zotero collection item count via API `Total-Results` header if needed.
- **Phase 2-1 may have 0 records in llm-kb** if a later agent overwrote the phase doc with expanded data; check actual workspace JSON files.
- **Kanban board may show done but llm-kb may be outdated** — the two are written by different agents at different times; cross-check.

## Example Options Table

| フェーズ | ファイル | サイズ | 内容 |
|---------|---------|-------|------|
| Phase 4 | 本論 | 22KB | 主要ドラフト |
| Presentation | Critical Analysis | 24KB | プレゼン/QA用 |
| Phase 3 | 分析 | 12KB | 統合・ギャップ分析 |

Choices:
1. Phase 4 を改善・拡張
2. Presentation をスライド化
3. 新たな方向性で追加研究
4. 特定のフェーズを読み直して判断
