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
from typing import Any, Dict, Iterable, Optional, Union

HERMES = "/opt/hermes/bin/hermes"
DEFAULT_WORKSPACE_ROOT = Path("/opt/data/workspace/ars-kanban-runs")

PhaseKey = Union[int, str]

PHASE_SPECS: Dict[PhaseKey, Dict[str, Any]] = {
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
    "2-1": {
        "name": "Literature Acquisition",
        "parent_phase": 2,
        "agents": ["bibliography_agent", "source_verification_agent"],
    },
    "2-2": {
        "name": "Investigation (Zotero Corpus)",
        "parent_phase": 2,
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
    "2.5": {
        "name": "Integrity",
        "parent_phase": 2,
        "agents": ["integrity_verification_agent", "state_tracker_agent"],
        "skills": ["academic-pipeline"],
        "gate": True,
    },
    "3'": {
        "name": "Re-Review",
        "parent_phase": 3,
        "agents": ["field_analyst_agent", "eic_agent", "editorial_synthesizer_agent"],
        "skills": ["academic-paper-reviewer"],
    },
    "4.5": {
        "name": "Final Integrity",
        "parent_phase": 4,
        "agents": ["integrity_verification_agent", "state_tracker_agent"],
        "skills": ["academic-pipeline"],
        "gate": True,
    },
    "5.5": {
        "name": "Process Summary",
        "parent_phase": 5,
        "agents": ["state_tracker_agent", "pipeline_orchestrator_agent"],
        "skills": ["academic-pipeline"],
    },
}

C_MODE_LITERATURE_SOURCES = [
    {
        "id": "openalex",
        "role": "primary-international",
        "api_key_required": False,
        "coverage": "International LIS journals: metadata, abstracts, OA status, OA URLs",
    },
    {
        "id": "crossref",
        "role": "doi-metadata-abstract-fallback",
        "api_key_required": False,
        "coverage": "DOI metadata and abstract fallback when OpenAlex abstracts are empty",
    },
    {
        "id": "jstage",
        "role": "primary-japanese-diamond-oa",
        "api_key_required": False,
        "coverage": "Japanese LIS journals on J-STAGE: metadata, abstracts, Diamond OA PDFs",
    },
    {
        "id": "cinii_research",
        "role": "japanese-supplement",
        "api_key_required": False,
        "coverage": "Japanese literature not covered by J-STAGE: metadata and repository links",
    },
    {
        "id": "semantic_scholar",
        "role": "citation-network-supplement",
        "api_key_required": True,
        "api_key_env": "SEMANTIC_SCHOLAR_API_KEY",
        "optional": True,
        "coverage": "Citation graph, references, citations, TLDR, author metadata",
    },
]


def phase_sequence_for_mode(mode: str) -> list[PhaseKey]:
    """Return the task phase sequence for an ARS mode."""
    if mode == "c":
        return [1, "2-1", "2-2", "2.5", 3, "3'", 4, "4.5", 5, "5.5", 6]
    return [1, 2, "2.5", 3, "3'", 4, "4.5", 5, "5.5", 6]


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


def phase_version_label(phase: PhaseKey) -> str:
    """Return the Material Passport version label for a phase key."""
    return f"phase{phase}-v0"


def build_material_passport(
    *,
    topic: str,
    mode: str,
    phase: PhaseKey,
    origin_date: str,
    previous_phase: Optional[PhaseKey] = None,
) -> Dict[str, Any]:
    """Build Schema 9-compatible Material Passport metadata for a phase task."""
    upstream_dependencies = [phase_version_label(previous_phase)] if previous_phase is not None else []
    return {
        "origin_skill": "deep-research",
        "origin_mode": mode,
        "origin_date": origin_date,
        "verification_status": "UNVERIFIED",
        "version_label": phase_version_label(phase),
        "integrity_pass_date": None,
        "content_hash": None,
        "upstream_dependencies": upstream_dependencies,
        # Schema 9 v3.3.5 says repro_lock must exist; null is an honest opt-out.
        "repro_lock": None,
        "reset_boundary": [],
        "topic": topic,
        "phase": phase,
    }


def build_c_mode_state(*, topic: str, loop_count: int = 0, max_loops: int = 3) -> Dict[str, Any]:
    """Return C mode deep-research loop state embedded in Phase 2-x tasks."""
    return {
        "loop_count": loop_count,
        "max_loops": max_loops,
        "zotero_collection_path": f"deep-research/{slugify_topic(topic)}",
        "literature_sources": list(C_MODE_LITERATURE_SOURCES),
        "manual_fulltext_required": True,
        "human_handoff": (
            "After Phase 2-1, manually add paywalled full texts to the Zotero "
            "deep-research project collection, then unblock Phase 2-2."
        ),
    }


def build_task_body(
    *,
    topic: str,
    board_slug: str,
    phase: PhaseKey,
    mode: str,
    origin_date: str,
    previous_phase: Optional[PhaseKey] = None,
) -> Dict[str, Any]:
    spec = PHASE_SPECS[phase]
    body = {
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
            previous_phase=previous_phase,
        ),
    }
    if "parent_phase" in spec:
        body["parent_phase"] = spec["parent_phase"]
    if mode == "c" and phase in ("2-1", "2-2"):
        body["c_mode"] = build_c_mode_state(topic=topic)
    return body


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

    task_ids: Dict[PhaseKey, str] = {}
    tasks: list[Dict[str, Any]] = []
    phase_sequence = phase_sequence_for_mode(mode)
    previous_phase: Optional[PhaseKey] = None
    for phase in phase_sequence:
        spec = PHASE_SPECS[phase]
        body = build_task_body(
            topic=topic,
            board_slug=board_slug,
            phase=phase,
            mode=mode,
            origin_date=origin_date,
            previous_phase=previous_phase,
        )
        parent_ids = [task_ids[previous_phase]] if previous_phase is not None else []
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
        previous_phase = phase

    return {
        "board_slug": board_slug,
        "workspace": str(run_workspace),
        "phase_sequence": phase_sequence,
        "task_ids": [task_ids[phase] for phase in phase_sequence],
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
