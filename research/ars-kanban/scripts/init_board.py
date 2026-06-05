#!/usr/bin/env python3
"""Create an ARS six-phase Kanban board for cross-session research runs.

The module is testable through an injected kanban adapter. The default CLI
adapter shells out to the Hermes Kanban CLI and uses persistent ``dir:``
workspaces so phase artifacts survive task completion.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

HERMES = "/opt/hermes/bin/hermes"
DEFAULT_WORKSPACE_ROOT = Path("/opt/data/workspace/ars-kanban-runs")

PHASE_SPECS: Dict[int, Dict[str, Any]] = {
    1: {
        "name": "Scoping",
        "agents": [
            "research_question_agent",
            "research_architect_agent",
            "devils_advocate_agent",
        ],
    },
    2: {
        "name": "Investigation",
        "agents": ["bibliography_agent", "source_verification_agent"],
    },
    3: {
        "name": "Analysis",
        "agents": ["synthesis_agent", "devils_advocate_agent"],
    },
    4: {
        "name": "Composition",
        "agents": ["report_compiler_agent"],
    },
    5: {
        "name": "Review",
        "agents": ["editor_in_chief_agent", "ethics_review_agent", "devils_advocate_agent"],
    },
    6: {
        "name": "Revision",
        "agents": ["report_compiler_agent"],
    },
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify_topic(topic: str) -> str:
    """Return a stable kebab-case ASCII slug for a research topic."""
    normalized = unicodedata.normalize("NFKD", topic).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug or "research"


def board_slug_for_topic(topic: str) -> str:
    return f"ars-{slugify_topic(topic)}"


def build_material_passport(*, topic: str, mode: str, phase: int, origin_date: str) -> Dict[str, Any]:
    """Build Schema 9-compatible Material Passport metadata for a phase task."""
    return {
        "origin_skill": "deep-research",
        "origin_mode": mode,
        "origin_date": origin_date,
        "verification_status": "UNVERIFIED",
        "version_label": f"phase{phase}-v0",
        "integrity_pass_date": None,
        "content_hash": None,
        "upstream_dependencies": [f"phase{phase - 1}-v0"] if phase > 1 else [],
        # Schema 9 v3.3.5 says repro_lock must exist; null is an honest opt-out.
        "repro_lock": None,
        "reset_boundary": [],
        "topic": topic,
        "phase": phase,
    }


def build_task_body(*, topic: str, board_slug: str, phase: int, mode: str, origin_date: str) -> Dict[str, Any]:
    spec = PHASE_SPECS[phase]
    return {
        "workflow": "ars-kanban",
        "board_slug": board_slug,
        "topic": topic,
        "phase": phase,
        "phase_name": spec["name"],
        "mode": mode,
        "agents": list(spec["agents"]),
        "material_passport": build_material_passport(
            topic=topic,
            mode=mode,
            phase=phase,
            origin_date=origin_date,
        ),
    }


class KanbanCli:
    def __init__(self, hermes: str = HERMES):
        self.hermes = hermes

    def _run(self, args: Iterable[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run([self.hermes, "kanban", *args], capture_output=True, text=True, check=check)

    def ensure_board(self, board_slug: str, *, name: str, description: str, default_workdir: Optional[str] = None) -> Dict[str, Any]:
        cmd = ["boards", "create", board_slug, "--name", name, "--description", description]
        if default_workdir:
            cmd.extend(["--default-workdir", default_workdir])
        proc = self._run(cmd, check=False)
        if proc.returncode not in (0,):
            # Board creation is intended to be idempotent at this layer. If the
            # board already exists, keep going; otherwise surface the error.
            err = (proc.stderr + proc.stdout).lower()
            if "exist" not in err and "already" not in err:
                raise subprocess.CalledProcessError(proc.returncode, [self.hermes, "kanban", *cmd], proc.stdout, proc.stderr)
        return {"slug": board_slug, "name": name}

    def create_task(
        self,
        *,
        board_slug: str,
        title: str,
        body: str,
        assignee: Optional[str],
        workspace: str,
        idempotency_key: str,
        parent_ids: Optional[list[str]] = None,
    ) -> Dict[str, Any]:
        cmd = [
            "--board", board_slug,
            "create", title,
            "--body", body,
            "--workspace", workspace,
            "--idempotency-key", idempotency_key,
            "--created-by", "ars-kanban-init-board",
            "--skill", "deep-research",
            "--json",
        ]
        if assignee:
            cmd.extend(["--assignee", assignee])
        for parent_id in parent_ids or []:
            cmd.extend(["--parent", parent_id])
        proc = self._run(cmd)
        task = json.loads(proc.stdout)
        return task

def init_board(
    topic: str,
    *,
    kanban: Any,
    workspace_root: Path = DEFAULT_WORKSPACE_ROOT,
    assignee: Optional[str] = None,
    mode: str = "full",
    origin_date: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a six-phase ARS Kanban DAG and return the board/task IDs."""
    topic = topic.strip()
    if not topic:
        raise ValueError("topic must not be empty")
    origin_date = origin_date or utc_now_iso()
    board_slug = board_slug_for_topic(topic)
    run_workspace = Path(workspace_root) / board_slug
    run_workspace.mkdir(parents=True, exist_ok=True)

    kanban.ensure_board(
        board_slug,
        name=f"ARS: {topic}",
        description=f"ARS cross-session research workflow for {topic}",
        default_workdir=str(run_workspace),
    )

    task_ids: Dict[int, str] = {}
    tasks: list[Dict[str, Any]] = []
    for phase in sorted(PHASE_SPECS):
        spec = PHASE_SPECS[phase]
        body = build_task_body(topic=topic, board_slug=board_slug, phase=phase, mode=mode, origin_date=origin_date)
        parent_ids = [task_ids[phase - 1]] if phase > 1 else []
        phase_workspace = run_workspace / f"phase-{phase}"
        phase_workspace.mkdir(parents=True, exist_ok=True)
        task = kanban.create_task(
            board_slug=board_slug,
            title=f"Phase {phase}: {spec['name']} — {topic}",
            body=json.dumps(body, ensure_ascii=False),
            assignee=assignee,
            workspace=f"dir:{phase_workspace}",
            idempotency_key=f"{board_slug}:phase:{phase}",
            parent_ids=parent_ids,
        )
        task_id = task["id"]
        task_ids[phase] = task_id
        tasks.append(task)

    return {
        "board_slug": board_slug,
        "workspace": str(run_workspace),
        "task_ids": [task_ids[phase] for phase in sorted(task_ids)],
        "tasks": tasks,
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Create an ARS six-phase Kanban board")
    parser.add_argument("topic", help="Research topic, e.g. 'Bates vs Hjørland'")
    parser.add_argument("--assignee", default=None, help="Hermes profile assigned to phase tasks. Omit to create the DAG without auto-dispatching.")
    parser.add_argument("--mode", default="full", help="ARS mode stored in task body, default: full")
    parser.add_argument("--workspace-root", default=str(DEFAULT_WORKSPACE_ROOT), help="Root directory for persistent phase workspaces")
    parser.add_argument("--json", action="store_true", help="Emit JSON only")
    args = parser.parse_args(argv)

    result = init_board(
        args.topic,
        kanban=KanbanCli(),
        workspace_root=Path(args.workspace_root),
        assignee=args.assignee,
        mode=args.mode,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Board: {result['board_slug']}")
        print(f"Workspace: {result['workspace']}")
        print("Tasks:")
        for idx, task_id in enumerate(result["task_ids"], start=1):
            print(f"  Phase {idx}: {task_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
