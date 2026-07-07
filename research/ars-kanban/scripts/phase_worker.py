#!/usr/bin/env python3
"""ARS Kanban phase worker.

This module is intentionally small and testable. The default CLI adapters use
Hermes Kanban CLI commands, while tests inject fake kanban/delegator objects.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Union

HERMES = "/opt/hermes/bin/hermes"

_SKILLS_CREDENTIALS = Path("/opt/data/workspace/.skills")
_SEMANTIC_SCHOLAR_CREDENTIALS = _SKILLS_CREDENTIALS / "semantic_scholar_credentials.json"


def _load_skill_credentials() -> None:
    """Load API keys from workspace/.skills/ into environment variables.

    Follows the hermes-skill-credential-patterns convention: credential files
    live in /opt/data/workspace/.skills/ (git-ignored, chmod 600).
    Currently loads Semantic Scholar API key.
    """
    # Semantic Scholar
    if not os.environ.get("SEMANTIC_SCHOLAR_API_KEY"):
        if _SEMANTIC_SCHOLAR_CREDENTIALS.exists():
            try:
                data = json.loads(_SEMANTIC_SCHOLAR_CREDENTIALS.read_text())
                key = data.get("api_key")
                if key:
                    os.environ["SEMANTIC_SCHOLAR_API_KEY"] = key
            except (json.JSONDecodeError, OSError):
                pass


# Load credentials at import time so they're available to all consumers
_load_skill_credentials()

# Ensure sibling modules (passport_layer, kb_sync, socratic_phase) are importable
_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# Import passport layer (Phase 5) — optional; worker works without it
try:
    import passport_layer as pp  # type: ignore[import-untyped]
except ImportError:
    pp = None  # type: ignore[assignment]


PhaseKey = Union[int, str]

PHASE_SPECS: Dict[PhaseKey, Dict[str, Any]] = {
    1: {
        "name": "Scoping",
        "agents": [
            "research_question_agent",
            "research_architect_agent",
            "devils_advocate_agent",
        ],
        "skills": ["deep-research"],
    },
    2: {
        "name": "Investigation",
        "agents": ["bibliography_agent", "source_verification_agent"],
        "skills": ["deep-research"],
    },
    "2-1": {
        "name": "Literature Acquisition",
        "parent_phase": 2,
        "agents": ["bibliography_agent", "source_verification_agent"],
        "skills": ["deep-research", "zotero", "lis-journal"],
    },
    "2-2": {
        "name": "Investigation (Zotero Corpus)",
        "parent_phase": 2,
        "agents": ["bibliography_agent", "source_verification_agent", "synthesis_agent"],
        "skills": ["deep-research", "zotero", "lis-journal"],
    },
    3: {
        "name": "Analysis",
        "agents": ["synthesis_agent", "devils_advocate_agent"],
        "skills": ["deep-research"],
    },
    4: {
        "name": "Composition",
        "agents": ["report_compiler_agent"],
        "skills": ["deep-research"],
    },
    5: {
        "name": "Review",
        "agents": ["editor_in_chief_agent", "ethics_review_agent", "devils_advocate_agent"],
        "skills": ["academic-paper-reviewer", "deep-research"],
    },
    6: {
        "name": "Revision",
        "agents": ["report_compiler_agent"],
        "skills": ["deep-research", "academic-paper"],
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


def extract_task_body(context_text: str) -> Dict[str, Any]:
    """Extract and parse the JSON body from `hermes kanban context` output."""
    marker = "## Body"
    start = context_text.find(marker)
    if start < 0:
        raise ValueError("Body section not found in kanban context")
    body_start = start + len(marker)
    rest = context_text[body_start:].lstrip("\n")
    next_section = rest.find("\n## ")
    body_text = rest[:next_section].strip() if next_section >= 0 else rest.strip()
    if not body_text:
        raise ValueError("Body section is empty")
    try:
        parsed = json.loads(body_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Body section is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError("Body JSON must be an object")
    return parsed


def phase_spec(phase: PhaseKey) -> Dict[str, Any]:
    """Return the configured ARS phase spec."""
    key: PhaseKey = int(phase) if isinstance(phase, str) and phase.isdigit() else phase
    try:
        return PHASE_SPECS[key]
    except KeyError as exc:
        raise ValueError(f"Unsupported ARS phase: {phase!r}") from exc


def extract_workspace_path(context_text: str) -> Optional[str]:
    """Extract workspace path from `Workspace: <kind> @ <path>` line."""
    for line in context_text.splitlines():
        if not line.startswith("Workspace:") or " @ " not in line:
            continue
        path = line.split(" @ ", 1)[1].strip()
        if path and path != "(unresolved)":
            return path
    return None


def write_phase_result(workspace_path: str, payload: Dict[str, Any]) -> str:
    """Write phase_result.json to workspace and return the file path."""
    path = Path(workspace_path) / "phase_result.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def build_phase_goal(task_id: str, phase: PhaseKey, spec: Dict[str, Any], mode: str) -> str:
    return f"Run ARS Phase {phase} ({spec['name']}) for kanban task {task_id} in {mode} mode"


def phase_version_label_for_worker(phase: PhaseKey, mode: str = "full") -> str:
    """Return a version label for int or hierarchical phase keys."""
    if mode == "c":
        return f"phase{phase}-v0"
    if pp is not None and isinstance(phase, int):
        return pp.PHASE_VERSION_LABELS.get(phase, f"phase{phase}-v0")
    return f"phase{phase}-v0"


def previous_phase_dependency_label(phase: PhaseKey, mode: str = "full") -> Optional[str]:
    """Return the upstream dependency label for a phase, if known."""
    if mode == "c":
        if phase == "2-1":
            return "phase1-v0"
        if phase == "2-2":
            return "phase2-1-v0"
        if phase == 3:
            return "phase2-2-v0"
        if isinstance(phase, int) and phase > 3:
            return f"phase{phase - 1}-v0"
        return None
    if pp is not None and isinstance(phase, int) and phase > 1:
        return pp.PHASE_VERSION_LABELS.get(phase - 1)
    return None


def _format_c_mode_context(kanban_context: str) -> str:
    """Return C mode source-policy instructions for Phase 2-1/2-2 prompts."""
    return (
        "\n\nC MODE DEEP RESEARCH POLICY:\n"
        "- Phase 2-1 Literature Acquisition collects metadata and OA full texts first.\n"
        "- International sources: OpenAlex primary; CrossRef DOI metadata/abstract fallback.\n"
        "- Japanese sources: J-STAGE primary for Diamond OA PDFs; CiNii Research supplement for domestic metadata and repository links.\n"
        "- Semantic Scholar is optional and should be used only when SEMANTIC_SCHOLAR_API_KEY is available; use it for citation graph, references, citations, TLDR, and author metadata.\n"
        "- Paywalled full texts must NOT be bypassed. Register metadata in Zotero and block for human full-text acquisition.\n"
        "- Target Zotero collection: read c_mode.zotero_collection_path from the task body (usually deep-research/<project>).\n"
        "- After human full-text acquisition, Phase 2-2 analyzes the Zotero corpus and may request a loop back to Phase 2-1 if gaps remain.\n"
    )


def build_phase_context(task_id: str, phase: PhaseKey, mode: str, spec: Dict[str, Any], kanban_context: str) -> str:
    agents = ", ".join(spec["agents"])
    skills = ", ".join(spec["skills"])
    base_context = (
        f"You are executing ARS Phase {phase}: {spec['name']}.\n"
        f"Mode: {mode}\n"
        f"Required agents: {agents}\n"
        f"Relevant skills: {skills}\n\n"
        "Use the kanban context below as the authoritative handoff from upstream phases. "
        "Produce a concise structured result with a summary and artifacts.\n\n"
        f"KANBAN TASK ID: {task_id}\n\n"
        f"KANBAN CONTEXT:\n{kanban_context}"
    )
    if mode == "c" and phase in ("2-1", "2-2"):
        return base_context + _format_c_mode_context(kanban_context)
    return base_context


class KanbanCli:
    def __init__(self, board: Optional[str] = None, hermes: str = HERMES):
        self.board = board
        self.hermes = hermes

    def _cmd(self, *args: str) -> list[str]:
        cmd = [self.hermes, "kanban"]
        if self.board:
            cmd.extend(["--board", self.board])
        cmd.extend(args)
        return cmd

    def context(self, task_id: str) -> str:
        return subprocess.run(self._cmd("context", task_id), check=True, capture_output=True, text=True).stdout

    def complete(self, task_id: str, summary: str, metadata: Dict[str, Any]) -> None:
        subprocess.run(
            self._cmd("complete", task_id, "--summary", summary, "--metadata", json.dumps(metadata, ensure_ascii=False)),
            check=True,
        )

    def block(self, task_id: str, reason: str) -> None:
        subprocess.run(self._cmd("block", task_id, reason), check=True)

    def comment(self, task_id: str, body: str) -> None:
        subprocess.run(self._cmd("comment", task_id, "--body", body), check=True)


class DryRunDelegator:
    def run(self, goal: str, context: str, toolsets: Iterable[str]) -> Dict[str, Any]:
        return {
            "summary": f"dry-run: {goal}",
            "artifacts": {
                "mode": "dry-run",
                "toolsets": list(toolsets),
                "context_excerpt": context[:500],
            },
        }


class HermesCliDelegator:
    def __init__(self, hermes: str = HERMES):
        self.hermes = hermes

    def run(self, goal: str, context: str, toolsets: Iterable[str]) -> Dict[str, Any]:
        # CLI fallback: run a fresh Hermes chat with the phase prompt. In agent
        # sessions, tests can inject a delegator backed by delegate_task instead.
        prompt = f"{goal}\n\n{context}\n\nReturn JSON with keys: summary, artifacts."
        proc = subprocess.run(
            [self.hermes, "chat", "-q", prompt, "--skills", "deep-research"],
            capture_output=True,
            text=True,
            check=True,
        )
        return {"summary": proc.stdout.strip() or goal, "artifacts": {}}


def run_phase_task(task_id: str, *, kanban: Any, delegator: Any) -> Dict[str, Any]:
    """Run one ARS phase task, completing or blocking the kanban card."""
    kanban_context = kanban.context(task_id)
    body = extract_task_body(kanban_context)
    raw_phase = body.get("phase", 0)
    phase: PhaseKey = int(raw_phase) if isinstance(raw_phase, str) and raw_phase.isdigit() else raw_phase
    mode = str(body.get("mode", "full"))
    spec = phase_spec(phase)

    # Extract workspace path once and reuse
    workspace_path = extract_workspace_path(kanban_context)

    # Phase 1 Socratic mode: interactive dialogue via block/unblock
    socratic_converged = False
    summary = None
    artifacts = None
    if mode == "socratic" and phase == 1:
        from socratic_phase import run_socratic_phase  # type: ignore[import-untyped]

        soc_result = run_socratic_phase(
            task_id,
            kanban=kanban,
            delegator=delegator,
            body=body,
            workspace_path=workspace_path,
        )
        if soc_result.get("status") == "converged":
            # Socratic dialogue complete — skip delegate_task, go to completion
            socratic_converged = True
            mode = "socratic"
            summary = soc_result["summary"]
            artifacts = soc_result.get("artifacts", {})
        else:
            # Blocked — return early, don't complete
            return soc_result

    if not socratic_converged:
        # Standard phase: build goal and context, run delegate
        goal = build_phase_goal(task_id, phase, spec, mode)
        delegate_context = build_phase_context(task_id, phase, mode, spec, kanban_context)

    # Phase 5: Validate Material Passport before execution (non-blocking)
    passport = body.get("material_passport")
    if pp is not None and passport:
        violations = pp.validate_passport(passport, strict=False)
        if violations:
            kanban.comment(
                task_id,
                f"Passport validation warnings ({len(violations)}):\n"
                + "\n".join(violations),
            )

    if not socratic_converged:
        # C mode Phase 2-1: two-phase flow (preview → user selection → Zotero export)
        if mode == "c" and phase == "2-1":
            try:
                from c_literature_acquisition import (
                    collect_records_for_preview, format_records_for_preview,
                    parse_selection, export_selected_to_zotero,
                )
                from socratic_phase import extract_last_user_comment  # type: ignore[import-untyped]
                from c_literature_acquisition import PREVIEW_RECORDS_FILE, ZOTERO_EXPORT_FILE

                ws = Path(workspace_path) if workspace_path else None
                records_file = (ws / PREVIEW_RECORDS_FILE) if ws else None
                export_file = (ws / ZOTERO_EXPORT_FILE) if ws else None

                if not workspace_path or not records_file or not records_file.exists():
                    # === Phase 1: Preview → block ===
                    records = collect_records_for_preview(body, workspace_path=workspace_path)
                    if not records:
                        summary = f"No literature records found for {body.get('topic', '')!r}. Phase 2-1 complete."
                        artifacts = {"record_count": 0, "records": []}
                    else:
                        preview = format_records_for_preview(records)
                        kanban.comment(task_id, f"## 📚 Literature Acquisition: {len(records)} records found\n\n{preview}")
                        kanban.block(task_id, f"Select records to export to Zotero ({len(records)} available). Reply with numbers (e.g. `1,3,5-8`) or `all`.")
                        return {"status": "blocked", "phase": phase, "reason": "awaiting_selection"}
                else:
                    # === Phase 2: Resume — parse user selection, export to Zotero ===
                    user_reply = extract_last_user_comment(kanban_context) or ""
                    selection = parse_selection(user_reply, len(json.loads(records_file.read_text())))
                    collection_path = (body.get("c_mode") or {}).get("zotero_collection_path") or f"deep-research/{body.get('topic', 'research')}"
                    export_result = export_selected_to_zotero(
                        workspace_path, selection, collection_path=collection_path,
                    )
                    summary = (
                        f"Exported {export_result['selected']} of {export_result['total']} "
                        f"records to Zotero collection `{collection_path}`. "
                        "Manually add paywalled PDFs to Zotero, then proceed to Phase 2-2."
                    )
                    artifacts = {
                        "record_count": export_result["total"],
                        "selected_count": export_result["selected"],
                        "zotero_collection_path": collection_path,
                        "zotero_export": export_result,
                        "sources_used": ["openalex", "crossref"],
                    }
            except Exception as exc:  # noqa: BLE001 - surfaced to kanban block
                message = f"C mode Phase 2-1 literature acquisition failed: {exc}"
                kanban.comment(task_id, f"Phase worker error for task {task_id}: {exc}")
                kanban.block(task_id, message)
                return {"status": "blocked", "error": str(exc), "phase": phase}
        else:
            try:
                result = delegator.run(goal=goal, context=delegate_context, toolsets=["file", "web", "terminal"])
            except Exception as exc:  # noqa: BLE001 - surfaced to kanban block
                message = f"phase-worker failed: {exc}"
                kanban.comment(task_id, f"Phase worker error for task {task_id}: {exc}")
                kanban.block(task_id, message)
                return {"status": "blocked", "error": str(exc), "phase": phase}

            summary = str(result.get("summary") or f"Phase {phase} complete")
            artifacts = result.get("artifacts") or {}
    else:
        # Socratic converged: summary and artifacts already set
        pass
    phase_result = {
        "task_id": task_id,
        "phase": phase,
        "mode": mode,
        "summary": summary,
        "artifacts": artifacts,
    }
    result_path = write_phase_result(workspace_path, phase_result) if workspace_path else None
    metadata: Dict[str, Any] = {"phase": phase, "mode": mode, "artifacts": artifacts}

    # Phase 5: Upgrade passport with execution result
    if pp is not None and passport:
        version_label = phase_version_label_for_worker(phase, mode)
        upstream_label = previous_phase_dependency_label(phase, mode)
        upgraded = pp.upgrade_passport(
            passport,
            new_status="UNVERIFIED",
            new_version_suffix=version_label,
            downstream_dependency=upstream_label,
        )
        # content_hash covers the delegate result (summary + artifacts only, not all workspace files)
        upgraded["content_hash"] = pp.compute_content_hash(
            {"summary": summary, "artifacts": artifacts}
        )
        metadata["material_passport"] = upgraded
        # Write passport.json to workspace for cross-phase reference
        if workspace_path:
            passport_path = Path(workspace_path) / "passport.json"
            passport_path.write_text(
                json.dumps(upgraded, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    else:
        # Include an empty passport marker so downstream phases can distinguish
        # "intentionally empty" from "pre-upgrade" state
        metadata.setdefault("material_passport", {})

    # Phase 6: Save to llm-kb wiki (best-effort, does not block phase completion)
    topic = body.get("topic", "")
    phase_name = spec["name"]
    try:
        from kb_sync import save_and_push as _kb_save  # type: ignore[import-untyped]

        kb_result = _kb_save(
            topic=topic,
            phase=phase,
            phase_name=phase_name,
            summary=summary,
            artifacts=artifacts,
            workspace_path=workspace_path,
            skip_push=True,
        )
        if kb_result.get("kb_path"):
            metadata["kb_path"] = kb_result["kb_path"]
        else:
            kanban.comment(task_id, f"KB sync skipped: KB directory not available for topic {topic!r}")
    except Exception as exc:
        kanban.comment(task_id, f"KB sync failed for task {task_id}: {exc}")

    kanban.complete(task_id, summary, metadata)
    return {"status": "completed", "phase": phase, "summary": summary, "metadata": metadata}


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run an ARS kanban phase task")
    parser.add_argument("task_id")
    parser.add_argument("--board", default=None)
    parser.add_argument("--dry-run", action="store_true", help="Use a deterministic local delegator instead of spawning Hermes chat")
    args = parser.parse_args(argv)
    delegator = DryRunDelegator() if args.dry_run else HermesCliDelegator()
    result = run_phase_task(args.task_id, kanban=KanbanCli(board=args.board), delegator=delegator)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("status") == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
