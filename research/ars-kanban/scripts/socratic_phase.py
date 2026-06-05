#!/usr/bin/env python3
"""ARS Kanban phase worker — Socratic mode support (interactive dialogue).

This module extends phase_worker.py with Socratic dialogue capabilities
using the kanban block/unblock pattern for multi-turn user interaction.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure sibling module (wording_patterns) is importable
_SCRIPTS_DIR = str(Path(__file__).resolve().parent)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

try:
    import wording_patterns as wp_mod  # type: ignore[import-untyped]
except ImportError:
    wp_mod = None  # type: ignore[assignment]

# Socratic state file name in workspace
SOCRATIC_STATE_FILE = "socratic_state.json"

# Max turns per Socratic session (mirrors ARS limits)
MAX_SOCRATIC_TURNS = 40

# Socratic Layer names
SOCRATIC_LAYERS = {
    1: "Problem Framing",
    2: "Methodology Reflection",
    3: "Evidence Design",
    4: "Critical Self-Examination",
    5: "Significance & Contribution",
}

# Default Socratic state for a fresh dialogue
DEFAULT_SOCRATIC_STATE: Dict[str, Any] = {
    "turn": 0,
    "layer": 1,
    "insights": [],
    "history": [],
    "converged": False,
    "awaiting_user": False,
    "current_question": None,
    "convergence_signals": [],
}


def socratic_state_path(workspace_path: Optional[str]) -> Optional[Path]:
    """Return the path to the socratic_state.json in the workspace."""
    if not workspace_path:
        return None
    return Path(workspace_path) / SOCRATIC_STATE_FILE


def load_socratic_state(workspace_path: Optional[str]) -> Dict[str, Any]:
    """Load Socratic dialogue state from workspace, or return defaults."""
    path = socratic_state_path(workspace_path)
    if path and path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            # Merge with defaults so new fields are populated
            state = dict(DEFAULT_SOCRATIC_STATE)
            state.update(data)
            return state
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULT_SOCRATIC_STATE)


def save_socratic_state(state: Dict[str, Any], workspace_path: Optional[str]) -> None:
    """Save Socratic dialogue state to workspace."""
    path = socratic_state_path(workspace_path)
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


def clear_socratic_state(workspace_path: Optional[str]) -> None:
    """Remove Socratic state file (called on completion)."""
    path = socratic_state_path(workspace_path)
    if path and path.exists():
        path.unlink(missing_ok=True)


def build_socratic_mentor_prompt(state: Dict[str, Any], topic: str) -> str:
    """Build the delegate_task prompt for the Socratic mentor agent."""
    layer_name = SOCRATIC_LAYERS.get(state["layer"], "Unknown")
    history_lines = []
    for entry in state["history"]:
        role_label = "User" if entry["role"] == "user" else "Mentor"
        history_lines.append(f"{role_label}: {entry['content']}")

    insights_str = "\n".join(f"- {i}" for i in state["insights"]) if state["insights"] else "(none yet)"
    history_str = "\n".join(history_lines) if history_lines else "(no prior conversation)"

    return json.dumps({
        "role": "system",
        "content": (
            "You are the Socratic Mentor Agent — a Q1 journal editor-in-chief guiding a researcher. "
            "IRON RULE: Never give direct answers. Always respond with questions that promote deeper thinking.\n\n"
            f"Research topic: {topic}\n"
            f"Current layer ({state['layer']}/5): {layer_name}\n"
            f"Dialogue turn: {state['turn']}\n"
            f"Insights collected so far:\n{insights_str}\n\n"
            "Your response must be valid JSON with these keys:\n"
            "- question: str — the Socratic question to ask the user\n"
            "- needs_user_input: bool — always true unless dialogue is complete\n"
            "- insight: str|null — extract an INSIGHT if the user expressed a mature idea\n"
            "- converged: bool — true only when S1-S4 convergence signals are met\n"
            "- convergence_signals: list[str] — list of met signals: S1 (Thesis Clarity), S2 (Counterargument Awareness), S3 (Methodology Rationale), S4 (Scope Stability)\n"
            "- layer: int — current layer number (advance when layer is complete)\n"
            "- summary: str|null — final summary when converged\n\n"
            "Convergence rules:\n"
            "- S1: User can state RQ in one clear sentence without hedging\n"
            "- S2: User can name 2+ counter-arguments unprompted\n"
            "- S3: User can justify methodology choice\n"
            "- S4: RQ stable for last 3 turns\n"
            "- Converge when 3+ signals met\n\n"
            "Layer advancement: minimum 2 dialogue turns per layer.\n"
            f"Conversation history:\n{history_str}"
        ),
    })


def extract_last_user_comment(kanban_context: str) -> Optional[str]:
    """Extract the last user comment from kanban context output.

    Kanban context includes a ## Comments section with comment bodies.
    """
    marker = "## Comments"
    start = kanban_context.find(marker)
    if start < 0:
        return None
    comments_section = kanban_context[start:]
    # Look for the most recent comment body (last line with content)
    lines = comments_section.splitlines()
    # Comments are typically formatted as:
    # ## Comments
    # - user (2026-06-05): comment text
    # Find lines with a colon after timestamp pattern
    for line in reversed(lines):
        line = line.strip()
        # Skip empty lines, headers, separators
        if not line or line.startswith("#") or line.startswith("---"):
            continue
        # Extract text after the last "): " or ": "
        if "): " in line:
            return line.split("): ", 1)[1]
        if " - " in line and ": " in line:
            return line.split(": ", 1)[1]
    return None


def run_socratic_phase(
    task_id: str,
    *,
    kanban: Any,
    delegator: Any,
    body: Dict[str, Any],
    workspace_path: Optional[str],
) -> Dict[str, Any]:
    """Run one Socratic dialogue turn, blocking for user input when needed.

    Called repeatedly (across multiple process invocations) via the kanban
    block/unblock pattern. State is persisted in socratic_state.json.
    """
    topic = body.get("topic", "")
    state = load_socratic_state(workspace_path)

    # --- Phase: Handle user response after unblock ---
    if state["awaiting_user"]:
        # User unblocked the task. Read their response from the latest comment.
        kanban_context = kanban.context(task_id)
        user_response = extract_last_user_comment(kanban_context)
        if user_response and user_response.strip():
            state["history"].append({"role": "user", "content": user_response.strip()})
        else:
            # No user response found — keep blocking
            return {
                "status": "blocked",
                "phase": 1,
                "reason": "No response found. Please reply via kanban comment.",
            }
        state["awaiting_user"] = False
        state["turn"] += 1

        # --- Wording-Pattern Advisory (Kong #257) ---
        # Check the latest user response for AI-typical research-question shells.
        # Suppressed by domain-native vocabulary. One advisory per pattern per session.
        if wp_mod is not None:
            try:
                advisory = wp_mod.detect_wording_advisory(
                    user_response, history=state["history"]
                )
                if advisory is not None:
                    # Persist advisory to state history
                    state["history"].append(
                        wp_mod.advisory_to_history_entry(advisory)
                    )
                    # Notify user via kanban comment
                    kanban.comment(task_id, advisory["message"])
            except Exception as exc:
                # Never let advisory failure break the Socratic flow
                kanban.comment(task_id, f"[advisory-check skipped: {exc}]")

    # --- Phase: Run mentor delegate ---
    mentor_prompt = build_socratic_mentor_prompt(state, topic)
    try:
        mentor_result = delegator.run(
            goal=f"Socratic dialogue turn {state['turn'] + 1}, layer {state['layer']}",
            context=mentor_prompt,
            toolsets=[],
        )
    except Exception as exc:
        kanban.comment(task_id, f"Socratic mentor failed: {exc}")
        save_socratic_state(state, workspace_path)
        kanban.block(task_id, f"Socratic mentor error: {exc}")
        return {"status": "blocked", "phase": 1, "error": str(exc)}

    # Parse mentor output
    mentor_output = _parse_mentor_output(mentor_result.get("summary", ""), mentor_result)

    # Record mentor's question in history
    if mentor_output.get("question"):
        state["history"].append({"role": "mentor", "content": mentor_output["question"]})

    # Extract insight if any
    if mentor_output.get("insight"):
        insight = mentor_output["insight"]
        if insight not in state["insights"]:
            state["insights"].append(insight)

    # Track convergence signals
    signals = mentor_output.get("convergence_signals", [])
    if signals:
        state["convergence_signals"] = list(set(state["convergence_signals"] + signals))

    # Check convergence
    if mentor_output.get("converged") or len(state.get("convergence_signals", [])) >= 3:
        state["converged"] = True

    # Layer advancement
    new_layer = mentor_output.get("layer", state["layer"])
    if new_layer > state["layer"] and state["turn"] >= 2:
        state["layer"] = new_layer

    # --- Action: Block for user input or complete ---
    if state["converged"] or state["turn"] >= MAX_SOCRATIC_TURNS:
        # Socratic dialogue complete
        summary = mentor_output.get("summary") or _compile_socratic_summary(state)
        clear_socratic_state(workspace_path)
        # Write phase_result (standard)
        if workspace_path:
            phase_result = {
                "task_id": task_id,
                "phase": 1,
                "mode": "socratic",
                "summary": summary,
                "artifacts": {
                    "insights": state["insights"],
                    "convergence_signals": state["convergence_signals"],
                    "total_turns": state["turn"],
                    "layers_completed": state["layer"],
                },
            }
            result_path = Path(workspace_path) / "phase_result.json"
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.write_text(
                json.dumps(phase_result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        # Delegate to standard completion logic for passport upgrade + KB sync
        return {
            "status": "converged",
            "phase": 1,
            "mode": "socratic",
            "summary": summary,
            "artifacts": {
                "insights": state["insights"],
                "convergence_signals": state["convergence_signals"],
                "total_turns": state["turn"],
            },
        }

    # Block for user input
    question_text = mentor_output.get("question", "What are your thoughts on this?")
    state["awaiting_user"] = True
    state["current_question"] = question_text
    save_socratic_state(state, workspace_path)

    kanban.comment(
        task_id,
        f"[SOCRATIC Layer {state['layer']}: {SOCRATIC_LAYERS.get(state['layer'], '?')}]\n\n"
        f"{question_text}\n\n"
        f"_Turn {state['turn']} | Insights: {len(state['insights'])} | Signals: {len(state.get('convergence_signals', []))}/4_",
    )
    kanban.block(
        task_id,
        f"[SOCRATIC] {question_text[:200]}"
    )
    return {"status": "blocked", "phase": 1, "reason": "awaiting_user"}


def _parse_mentor_output(summary: str, raw_result: Dict[str, Any]) -> Dict[str, Any]:
    """Parse the mentor's response. Tries JSON first, then heuristic extraction."""
    # Try parsing summary as JSON
    if summary:
        summary_clean = summary.strip()
        # Remove markdown code fences if present
        if summary_clean.startswith("```"):
            # Extract JSON from code fence
            lines = summary_clean.splitlines()
            json_lines = []
            in_code = False
            for line in lines:
                if line.strip().startswith("```"):
                    in_code = not in_code
                    continue
                if in_code:
                    json_lines.append(line)
            if json_lines:
                summary_clean = "\n".join(json_lines)
        try:
            parsed = json.loads(summary_clean)
            if isinstance(parsed, dict):
                return parsed
        except (json.JSONDecodeError, ValueError):
            pass

    # Fallback: use raw result fields
    return {
        "question": raw_result.get("question") or summary or "Could you elaborate on that?",
        "needs_user_input": True,
        "insight": raw_result.get("insight"),
        "converged": raw_result.get("converged", False),
        "convergence_signals": raw_result.get("convergence_signals", []),
        "layer": raw_result.get("layer", 1),
        "summary": raw_result.get("summary"),
    }


def _compile_socratic_summary(state: Dict[str, Any]) -> str:
    """Compile a research plan summary from Socratic dialogue state."""
    lines = [
        "# Research Plan Summary (Socratic Dialogue)",
        "",
        f"**Total turns**: {state['turn']}",
        f"**Layers explored**: {state['layer']}/5",
        f"**Convergence signals**: {', '.join(state.get('convergence_signals', ['none']))}",
        "",
        "## Insights",
        "",
    ]
    for i, insight in enumerate(state.get("insights", []), start=1):
        lines.append(f"{i}. {insight}")
    if not state.get("insights"):
        lines.append("*No mature insights extracted*")

    lines.extend([
        "",
        "## Dialogue History",
        "",
    ])
    for entry in state.get("history", []):
        prefix = "🧑 User" if entry["role"] == "user" else "🎓 Mentor"
        lines.append(f"> **{prefix}**: {entry['content']}")
        lines.append("")

    return "\n".join(lines)
