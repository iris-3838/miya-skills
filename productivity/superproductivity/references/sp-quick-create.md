# SP Quick Task Creation (with Project + Tags)

Updated: added anonymized examples with multi-task creation and verified tag-behavior.

## Pattern: Single task, no tags

```bash
curl -s -X POST http://localhost:3876/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "タスク名",
    "projectId": "PROJECT_ID",
    "dueDay": "YYYY-MM-DD"
  }'
```

Response envelope:
```json
{"ok": true, "data": {"id": "TASK_ID", "title": "...", ...}}
```

## Pattern: Task + tags in one POST (⚠️ unreliable for some tags)

```bash
curl -s -X POST http://localhost:3876/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "タスク名",
    "projectId": "PROJECT_ID",
    "dueDay": "YYYY-MM-DD",
    "tagIds": ["EM_IMPORTANT", "EM_URGENT", "TODAY"]
  }'
```

**Result:** `TODAY` tag silently dropped — response showed only `[EM_IMPORTANT, EM_URGENT]`. This confirms the pitfall below.

## Pattern: Two-step (recommended) — POST then PATCH tags

Step 1 — Create without tags:
```bash
curl -s -X POST http://localhost:3876/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "title": "タスク名",
    "projectId": "PROJECT_ID",
    "dueDay": "YYYY-MM-DD"
  }'
# → id = "TASK_ID"
```

Step 2 — PATCH to set all tags at once:
```bash
curl -s -X PATCH http://localhost:3876/tasks/TASK_ID \
  -H "Content-Type: application/json" \
  -d '{
    "tagIds": ["EM_IMPORTANT", "EM_URGENT", "TODAY"]
  }'
```

**Result:** All 3 tags persisted correctly (`EM_IMPORTANT`, `EM_URGENT`, `TODAY`).

## Common tag IDs

| ID | Label |
|----|-------|
| `TODAY` | 📅 today |
| `EM_IMPORTANT` | 🔥 important |
| `EM_URGENT` | 🚨 urgent |
| `KANBAN_IN_PROGRESS` | 🔄 in-progress |
| `CUSTOM_TAG_ID` | user-defined tag |

## User signal: "today's urgent task, add as <project>"

When the user says something like:
```
sp タスク名 今日中の緊急タスク, project-aliasとして追加して
```

Parse this as:
- `sp` → trigger to load superproductivity skill
- `タスク名` → task title
- `今日中の緊急タスク` → due: today, tags: EM_IMPORTANT + EM_URGENT + TODAY
- `project-aliasとして追加して` → project: fuzzy-match alias to project name

**Known project aliases** are user-specific — verify via `GET /projects` rather than hardcoding them in public docs.

## Pitfalls

- **⚠️ tagIds in POST may silently drop `TODAY`.** Observed consistently: `TODAY` dropped when sent alongside `EM_IMPORTANT` and `EM_URGENT` in POST body. **Recommended: POST without tagIds, then PATCH with all desired tags.** Safer and more reliable.
- **⚠️ Tag persistence across PATCH:** PATCH replaces the entire tagIds array (not additive). Always send the full list.
- `parentId` + `tagIds`/`projectId` in the same PATCH can 400 — do in two steps.
- `dueDay` is a **string** `"YYYY-MM-DD"`, not a timestamp.
- No auth on port 3876 — localhost-only.
- Project IDs are **per-user/per-instance** — look them up via `GET /projects` or consult memory. Never hardcode; the IDs in this file are for one specific user.
