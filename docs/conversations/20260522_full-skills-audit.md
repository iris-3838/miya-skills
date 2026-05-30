# Conversation: untitled

- **Date**: 2026-05-22 07:55 UTC
- **Source**: discord
- **Model**: deepseek-v4-flash
- **Total messages**: 36 (user: 1, assistant: 11)
- **Session ID**: `20260522_075508_4584381f`
- **Extracted**: 2026-05-30 15:09 UTC

---

> **User**
>
> 今まで自分で作ったskills一覧とそのディレクトリを教えて

_(ツール: execute_code, read_file, search_files, skill_view, skills_list, terminal)_

Slills はすべて `/opt/data/skills/` 以下にカテゴリごとに保存されています。
自分（seimiya）が作った（または作ってもらった）skills は以下の通り：

### research 系（論文調査・辞書）
| Skill | Path |
|---|---|
| `jstage-jslis-daily-summary` | `/opt/data/skills/research/jstage-jslis-daily-summary/SKILL.md` |
| `lis-word-dict` | `/opt/data/skills/research/lis-word-dict/SKILL.md` |
| `openalex-literature-survey` | `/opt/data/skills/research/openalex-literature-survey/SKILL.md` |
| `llm-kb-wiki` / `llm-wiki` | `/opt/data/skills/research/llm-kb-wiki/SKILL.md` |
| `web-fact-check` | `/opt/data/skills/research/web-fact-check/SKILL.md` |
| `zotero-pdf-translation` | `/opt/data/skills/research/zotero-pdf-translation/SKILL.md` |

### productivity 系（タスク管理・家計簿）
| Skill | Path |
|---|---|
| `zaim-household-finance` | `/opt/data/skills/productivity/zaim-household-finance/SKILL.md` |
| `superproductivity` | `/opt/data/skills/superproductivity/SKILL.md` |
| `super-productivity` | `/opt/data/skills/productivity/super-productivity/SKILL.md` |
| `sp` | `/opt/data/skills/productivity/sp/SKILL.md` |
| `pomo` | `/opt/data/skills/productivity/pomo/SKILL.md` |
| `gws-calendar` | `/opt/data/skills/gws-calendar/SKILL.md` |
| `dogfood` | `/opt/data/skills/dogfood/SKILL.md` |

### devops 系
| Skill | Path |
|---|---|
| `cron-operations` | `/opt/data/skills/devops/cron-operations/SKILL.md` |
| `systemd-user-services` | `/opt/data/skills/devops/systemd-user-services/SKILL.md` |

### その他
| Skill | Path |
|---|---|
| `opencode-go-quota` | `/opt/data/skills/opencode-go-quota/SKILL.md` |
| `session-tui` | `/opt/data/skills/session-tui/SKILL.md` |
| `xitter` | `/opt/data/skills/social-media/xitter/SKILL.md` |
| `systematic-debugging` | `/opt/data/skills/software-development/systematic-debugging/SKILL.md` |

ベースディレクトリ: **`/opt/data/skills/`**（カテゴリ別サブディレクトリに SKILL.md + 付随ファイル）

合計で自分作は **18〜20個程度**。（これ以外は Hermes Agent の bundled skill か hub 由来のものです）

---
*Extracted from session `20260522_075508_4584381f`*
