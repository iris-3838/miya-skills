#!/usr/bin/env python3
"""LLM-KB integration for ARS Kanban (Phase 6).

Saves phase results to the llm-kb-wiki after task completion,
and optionally commits + pushes to the git remote.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# llm-kb wiki path — may be overridden for testing
_DEFAULT_LLM_KB_DIR = Path("/opt/data/workspace/llm-kb.miya-lis.net")


def _concepts_dir(kb_dir: Optional[Path] = None) -> Optional[Path]:
    """Return the concepts directory, or None if the KB dir doesn't exist."""
    base = kb_dir or _DEFAULT_LLM_KB_DIR
    if not base.is_dir():
        return None
    return base / "concepts"


def make_topic_slug(topic: str) -> str:
    """Create a filesystem-safe slug for a research topic."""
    import re
    import unicodedata

    normalized = unicodedata.normalize("NFKD", topic).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", normalized.lower()).strip("-")
    slug = re.sub(r"-+", "-", slug)
    return slug or "research"


def save_phase_to_kb(
    topic: str,
    phase: int,
    phase_name: str,
    summary: str,
    artifacts: Dict[str, Any],
    workspace_path: Optional[str] = None,
    kb_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Save a phase result as a Markdown document in the llm-kb wiki.

    Returns the path to the saved file, or None if the KB directory is missing.
    """
    concepts = _concepts_dir(kb_dir)
    if concepts is None:
        return None

    topic_slug = make_topic_slug(topic)
    # Create topic directory if it doesn't exist
    topic_dir = concepts / topic_slug
    topic_dir.mkdir(parents=True, exist_ok=True)

    # Phase document
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    filename = f"phase-{phase}-{phase_name.lower().replace(' ', '-')}.md"
    filepath = topic_dir / filename

    # Inherit index.html if topic dir already has one
    index_file = topic_dir / "index.md"
    if not index_file.exists():
        _write_index_file(topic, topic_slug, topic_dir)

    lines = [
        f"# Phase {phase}: {phase_name} — {topic}",
        "",
        f"**Saved**: {timestamp}",
        f"**Topic**: {topic}",
        "",
        "## Summary",
        "",
        summary,
        "",
    ]

    if artifacts:
        lines.append("## Artifacts")
        lines.append("")
        for key, value in artifacts.items():
            lines.append(f"- **{key}**: {json.dumps(value, ensure_ascii=False) if not isinstance(value, str) else value}")
        lines.append("")

    if workspace_path:
        ws = Path(workspace_path)
        if ws.is_dir():
            existing = list(ws.iterdir())
            if existing:
                lines.append("## Workspace Files")
                lines.append("")
                for f in existing:
                    if f.is_file() and f.name not in ("phase_result.json", "passport.json"):
                        rel = f.relative_to(ws)
                        lines.append(f"- [{rel.name}]({rel})")
                lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(f"_Auto-saved by ARS Kanban Phase {phase} worker_")

    content = "\n".join(lines)
    filepath.write_text(content, encoding="utf-8")

    # Register in index if not already present
    _register_in_log(topic_slug, phase, phase_name, timestamp, filename, concepts)
    return filepath


def _write_index_file(topic: str, topic_slug: str, topic_dir: Path) -> None:
    """Create a minimal index.md for the topic."""
    content = f"""# {topic}

ARS research project managed via Hermes Kanban.

## Phases

- [Phase 1: Scoping](phase-1-scoping.md)
- [Phase 2: Investigation](phase-2-investigation.md)
- [Phase 3: Analysis](phase-3-analysis.md)
- [Phase 4: Composition](phase-4-composition.md)
- [Phase 5: Review](phase-5-review.md)
- [Phase 6: Revision](phase-6-revision.md)

## Material Passport

See `passport.json` in each phase workspace for provenance tracking.

---
_Auto-created by ARS Kanban_
"""
    (topic_dir / "index.md").write_text(content, encoding="utf-8")


def _register_in_log(topic_slug: str, phase: int, phase_name: str, timestamp: str, filename: str, concepts: Path) -> None:
    """Append a log entry to the topic's log.md."""
    log_path = concepts / topic_slug / "log.md"
    entry = f"| {timestamp} | Phase {phase} ({phase_name}) | {filename} | kanban-phase-worker |\n"
    if log_path.exists():
        content = log_path.read_text(encoding="utf-8")
        # Line-based dedup: check if the exact filename already appears in any log row
        if any(filename in line for line in content.splitlines()):
            return
        # Append to table
        if "|---" in content:
            content += entry
        else:
            content += "\n## Log\n\n| Timestamp | Event | File | Source |\n|---|---|---|---|\n" + entry
    else:
        content = f"# Log — {topic_slug}\n\n| Timestamp | Event | File | Source |\n|---|---|---|---|\n" + entry
    log_path.write_text(content, encoding="utf-8")


def git_commit(message: str, kb_dir: Optional[Path] = None) -> bool:
    """Commit and push changes to the llm-kb git repo."""
    repo_dir = kb_dir or _DEFAULT_LLM_KB_DIR
    if not repo_dir.is_dir():
        return False

    try:
        subprocess.run(
            ["git", "add", "-A"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        proc = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            return True  # nothing to commit

        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            check=True,
        )
        subprocess.run(
            ["git", "push"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
            timeout=30,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def save_and_push(
    topic: str,
    phase: int,
    phase_name: str,
    summary: str,
    artifacts: Dict[str, Any],
    workspace_path: Optional[str] = None,
    *,
    skip_push: bool = False,
    kb_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Save phase result to KB and optionally commit+push."""
    kb_path = save_phase_to_kb(topic, phase, phase_name, summary, artifacts, workspace_path, kb_dir=kb_dir)
    result = {
        "kb_path": str(kb_path) if kb_path else None,
        "topic_slug": make_topic_slug(topic),
        "saved": kb_path is not None,
    }
    if kb_path and not skip_push:
        msg = f"ars-kanban: Phase {phase} ({phase_name}) — {topic}"
        result["git_committed"] = git_commit(msg, kb_dir=kb_dir)
    return result


def main() -> int:
    """CLI entry for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Save an ARS Kanban phase result to llm-kb")
    parser.add_argument("topic")
    parser.add_argument("--phase", type=int, required=True)
    parser.add_argument("--phase-name", required=True)
    parser.add_argument("--summary", default="(no summary provided)")
    parser.add_argument("--workspace-path")
    parser.add_argument("--skip-push", action="store_true")
    args = parser.parse_args()

    result = save_and_push(
        args.topic,
        args.phase,
        args.phase_name,
        args.summary,
        {},
        workspace_path=args.workspace_path,
        skip_push=args.skip_push,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["saved"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
