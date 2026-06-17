# C-mode init/dispatch pitfalls

- Use a **short ASCII topic slug** for `scripts/init_board.py`. The board slug is derived from the topic and Hermes Kanban slugs are length-limited.
- Put the **full research question** in the Phase 1 comment/body, not in the topic string.
- After `init_board.py --mode c`, the created tasks may be **unassigned**. If you want the queue to run immediately, assign Phase 1 (and usually the whole chain) to a profile before `dispatch`.
- `hermes kanban comment <task_id> <text...>` is the safest place for the long scope statement, literature list, and inclusion/exclusion criteria.
- C mode Phase 2-1/2-2 expects the Zotero collection path in `c_mode.zotero_collection_path`; the default is `deep-research/<slugified-topic>`.

Worked example:

```bash
python scripts/init_board.py "Floridi LIS theory-practice relation" --mode c --json
/opt/hermes/bin/hermes kanban --board ars-floridi-lis-theory-practice-relation comment <phase-1-task> '...full research question...'
/opt/hermes/bin/hermes kanban --board ars-floridi-lis-theory-practice-relation assign <phase-1-task> default
/opt/hermes/bin/hermes kanban --board ars-floridi-lis-theory-practice-relation dispatch
```
