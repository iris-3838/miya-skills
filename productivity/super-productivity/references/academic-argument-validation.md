# Academic Argument Validation via Daily Deep Research + SP Tasks

Academics preparing conference presentations often need to validate their arguments against the latest literature. This pattern combines Hermes cron + academic-deep-research skill + SP task management.

## Pattern Overview

```
cron job (daily, agent-driven)
  └─ academic-deep-research: literature search on research question
  └─ Summarize findings → validate/refine arguments
  └─ SP task check: relevant SP tasks get progress notes
```

## When to Use

- Preparing academic presentations where argument validity is critical
- Need to stay current with literature on a specific theoretical debate
- Want systematic daily validation rather than ad-hoc searches
- Have SP tasks tracking the presentation preparation

## Setup Steps

### 1. Create SP Tasks

Break the presentation preparation into logical subtasks under the appropriate project:

```bash
PROJECT_ID="<project_id>"
SP="http://localhost:3876"

TASKS=(
  "【定期検証】Deep Researchで<テーマ>の文献を毎日探索・議論の妥当性検証"
  "理論Aの整理：論点・引用・批判ポイントのまとめ"
  "理論Bの整理：ドメイン分析的アプローチの論点整理"
  "理論A vs 理論B 対立点マッピング"
  "自己の議論の位置づけと批判的検証"
  "発表資料（スライド）作成：骨子→肉付け→レビュー"
)

for TITLE in "${TASKS[@]}"; do
  curl -s -X POST "$SP/tasks" \
    -H "Content-Type: application/json" \
    -d "{\"title\":\"$TITLE\",\"projectId\":\"$PROJECT_ID\",\"dueDay\":null}"
done
```

**⚠️ dueDay 注意:** `POST /tasks` は `dueDay` を省略すると自動で今日付がセットされる。期限のないタスクは `"dueDay": null` を明示的に指定すること。

### 2. Create Daily Deep Research Cron

```python
cronjob(
    action="create",
    name="daily-argument-validation-<topic>",
    schedule="0 9 * * *",  # 毎日9時（要調整）
    prompt="""# 学術議論の妥当性検証

The user is preparing a presentation on [TOPIC]. Today, run academic-deep-research on:

Research question: [RESEARCH_QUESTION]

Specifically look for:
1. New literature supporting or contradicting the user's position
2. Counterarguments or critiques that should be addressed
3. Recent developments that change the landscape

Format the output as:
📚 **Daily Argument Validation — YYYY/MM/DD**

**New Findings:**
- [Paper/title]: key argument, relevance

**Validation Result:**
✅ Supported / ⚠️ Needs refinement / ❌ Contradicted

**Action Items:**
- What to adjust in the presentation
- What to add to SP task notes

Then update the SP task "[task_title]" notes with the findings.
""",
    skills=["academic-deep-research", "super-productivity"],
    deliver="origin",
)
```

### 3. User Feedback Loop

- User reviews daily report
- Updates SP task notes or adjusts schedule
- Cron job automatically incorporates corrections in subsequent runs

## Example: VH (Bates) vs YARAN (Hjørland) Validation

**SP Tasks (under CONFERENCE_VH_YARAN or appropriate project):**
1. 【定期検証】Deep ResearchでVH/YARAN情報概念の文献を毎日探索・議論の妥当性検証
2. VH（Bates）情報概念の整理：論点・引用・批判ポイントのまとめ
3. YARAN（Hjørland）情報概念の整理：ドメイン分析的アプローチの論点整理
4. VH vs YARAN 対立点マッピング
5. 自己の議論（informed pluralism）の位置づけと批判的検証
6. 発表資料（スライド）作成：骨子→肉付け→レビュー

**Cron prompt example:**
```
Research question: Compare Bates' physical/tangible view of information (VH)
with Hjørland's domain-analytic approach (YARAN). The user's proposed position
is "informed pluralism" — that theoretical differences shape research practice.
Today find:
1. Papers directly comparing Bates and Hjørland
2. Critiques of either position published recently
3. Empirical studies that test which framework better predicts outcomes
4. Any reference to Floridi's PI that bridges or challenges these views
```
