# Super Productivity API Endpoint Reference

Base URL: `http://localhost:3876`
Envelope: `{"ok": true/false, "data": ..., "error": {"code": "...", "message": "..."}}`

## GET /tasks
Returns all active (non-done) tasks. No pagination.

```json
{
  "ok": true,
  "data": [
    {
      "id": "base64_or_uuid",
      "title": "Task title",
      "projectId": "INBOX_PROJECT or base64",
      "tagIds": ["TODAY", "KANBAN_IN_PROGRESS", "EM_IMPORTANT", "EM_URGENT", "..."],
      "parentId": null,
      "subTaskIds": [],
      "isDone": false,
      "dueDay": "YYYY-MM-DD",
      "timeSpent": 0,
      "timeEstimate": 0,
      "timeSpentOnDay": {},
      "notes": "",
      "created": 1700000000000,
      "modified": 1700000000000
    }
  ]
}
```

## POST /tasks
Create a new task.

```json
{
  "title": "Task name",
  "projectId": "INBOX_PROJECT",
  "tagIds": ["EM_IMPORTANT"],
  "parentId": null,
  "dueDay": "YYYY-MM-DD"
}
```

## PATCH /tasks/:id
Update task fields. Only include changed fields.

```json
{
  "isDone": true,
  "tagIds": ["TODAY", "EM_IMPORTANT"]
}
```

## GET /projects
Read-only project list.

```json
{
  "ok": true,
  "data": [
    {"id": "INBOX_PROJECT", "title": "Inbox", "taskIds": ["id1", "id2", ...]},
    {"id": "PROJECT_ID", "title": "Project name", "taskIds": [...]},
    ...
  ]
}
```

## GET /tags
Read-only tag list.

```json
{
  "ok": true,
  "data": [
    {"id": "TODAY", "title": "Today", "taskIds": [...]},
    {"id": "KANBAN_IN_PROGRESS", "title": "in-progress", "taskIds": [...]},
    {"id": "EM_IMPORTANT", "title": "important", "taskIds": [...]},
    {"id": "EM_URGENT", "title": "urgent", "taskIds": [...]},
    ...
  ]
}
```

## GET /status
General system status.

```json
{
  "ok": true,
  "data": {
    "currentTask": null,
    "currentTaskId": null,
    "taskCount": 55
  }
}
```

## GET /task-control/current
Current time tracking state.

## POST /task-control/stop
Stop active time tracking.
