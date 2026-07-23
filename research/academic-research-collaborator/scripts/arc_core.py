"""Deterministic state controller for the ARC research workflow.

This module deliberately contains no Hermes-specific tool calls.  Hermes skills
can use these pure functions as the checked boundary around a project
manifest.  YAML support is explicit: the controller never silently changes
format when PyYAML is unavailable.
"""
from __future__ import annotations

import copy
import os
import tempfile
import unicodedata
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

try:  # POSIX lock for concurrent writers; ARC currently targets Linux.
    import fcntl  # type: ignore
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None  # type: ignore[assignment]

try:  # Imported lazily by the runtime, but exposed as a clear dependency error.
    import yaml  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - depends on environment
    yaml = None  # type: ignore[assignment]
    _YAML_IMPORT_ERROR = exc
else:
    _YAML_IMPORT_ERROR = None


class ArcError(Exception):
    """Base class for deterministic ARC controller errors."""


class DependencyError(ArcError):
    """Raised when the controller cannot load its required YAML dependency."""


class PathPolicyError(ArcError):
    """Raised when a project path violates the ARC path policy."""


class ManifestError(ArcError):
    """Raised when a manifest cannot be safely read or validated."""


class TransitionError(ArcError):
    """Raised when a requested phase transition is not permitted."""


class RevisionConflict(ArcError):
    """Raised when optimistic manifest revision checking fails."""


MODES = frozenset({"full", "quick-scan", "lit-review"})
PHASES = (
    "initialized",
    "design",
    "plan",
    "curate",
    "acquisition_pending",
    "reflection",
)
STATUSES = frozenset({"initialized", "active", "paused", "completed", "abandoned"})
EVIDENCE_SCOPES = frozenset(
    {
        "metadata_only",
        "abstract_only",
        "fulltext_ready",
        "acquisition_required",
        "unavailable",
    }
)
PROVIDER_STATUSES = frozenset(
    {"success", "zero_hits", "unavailable", "transient_error", "rate_limited"}
)
ACQUISITION_ENTRY_STATUSES = frozenset(
    {
        "pending",
        "not_attempted",
        "in_progress",
        "acquired",
        "failed",
        "unavailable",
        "not_needed",
    }
)

_ALLOWED_TRANSITIONS = {
    "initialized": frozenset({"design"}),
    "design": frozenset({"plan"}),
    "plan": frozenset({"curate"}),
    "curate": frozenset({"acquisition_pending", "reflection"}),
    "acquisition_pending": frozenset({"reflection"}),
    "reflection": frozenset({"design", "plan", "curate"}),
}


@dataclass(frozen=True)
class ProjectSpec:
    """Normalized, policy-checked project identity."""

    project_id: str
    resolved_path: Path
    mode: str

    @property
    def artifact_dir(self) -> Path:
        return self.resolved_path / "artifacts"


def _require_yaml() -> Any:
    if yaml is None:
        detail = str(_YAML_IMPORT_ERROR) if _YAML_IMPORT_ERROR else "unknown import error"
        raise DependencyError(
            "PyYAML is required by arc_core; run with `uv run --with pyyaml` "
            f"or install the dependency ({detail})."
        ) from _YAML_IMPORT_ERROR
    return yaml


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _is_contained(child: Path, parent: Path) -> bool:
    try:
        return os.path.commonpath((str(child), str(parent))) == str(parent)
    except ValueError:
        return False


def _validate_project_id(project_id: str) -> None:
    """Validate a project ID as one safe directory component.

    ARC permits Unicode names, including Japanese research titles.  The ID is
    still not allowed to become a path expression or a platform-reserved
    component.
    """

    if not isinstance(project_id, str) or not project_id:
        raise PathPolicyError("project_id must be a non-empty string")
    if project_id != project_id.strip() or project_id in {".", ".."}:
        raise PathPolicyError("project_id must not have boundary whitespace or be . / ..")
    if any(
        unicodedata.category(char) in {"Cc", "Cf", "Co", "Cs"}
        for char in project_id
    ):
        raise PathPolicyError("project_id must not contain control or format characters")
    if any(char in project_id for char in ("/", "\\", ":", "<", ">", '"', "|", "?", "*")):
        raise PathPolicyError("project_id must be a single safe directory component")
    if Path(project_id).is_absolute() or Path(project_id).name != project_id:
        raise PathPolicyError("project_id must be a single safe directory component")


def normalize_project(
    project_id: str,
    path: str | os.PathLike[str],
    mode: str,
    projects_root: str | os.PathLike[str] | None,
) -> ProjectSpec:
    """Validate and normalize a new project identity.

    ``projects_root`` is intentionally required.  An arbitrary absolute path
    is not an allowlist and must never be accepted as one.
    """

    if not projects_root:
        raise PathPolicyError("projects_root must be explicitly configured")
    _validate_project_id(project_id)
    if mode not in MODES:
        raise ArcError(f"unsupported mode: {mode!r}")

    root = Path(projects_root).expanduser()
    candidate = Path(path).expanduser()
    if not root.is_absolute() or not candidate.is_absolute():
        raise PathPolicyError("projects_root and project path must be absolute")

    resolved_root = root.resolve(strict=False)
    resolved_candidate = candidate.resolve(strict=False)
    if not _is_contained(resolved_candidate, resolved_root):
        raise PathPolicyError("project path escapes projects_root")
    if resolved_candidate.name != project_id:
        raise PathPolicyError("project_id must equal the final path component")
    if resolved_candidate == resolved_root:
        raise PathPolicyError("project path must be below projects_root")
    if candidate.exists() and not candidate.is_dir():
        raise PathPolicyError("project path is an existing non-directory")

    # Existing directories are only acceptable when they are already ARC
    # projects.  Initialization code must still decide whether to resume.
    if candidate.exists() and any(candidate.iterdir()):
        manifest = candidate / "research-manifest.yaml"
        if not manifest.is_file():
            raise PathPolicyError("refusing to overwrite a non-ARC directory")

    return ProjectSpec(project_id=project_id, resolved_path=resolved_candidate, mode=mode)


def create_initial_manifest(spec: ProjectSpec) -> dict[str, Any]:
    """Return a canonical, unpersisted initial manifest (revision zero)."""

    timestamp = _now()
    return {
        "manifest_version": "1.0",
        "project_id": spec.project_id,
        "project_title": "",
        "project_path": str(spec.resolved_path),
        "artifact_dir": str(spec.artifact_dir),
        "created": timestamp[:10],
        "updated": timestamp[:10],
        "revision": 0,
        "status": "initialized",
        "events": [
            {
                "id": uuid.uuid4().hex,
                "type": "init",
                "phase": "initialized",
                "from_phase": None,
                "to_phase": "initialized",
                "revision": 0,
                "timestamp": timestamp,
            }
        ],
        "state": {
            "mode": spec.mode,
            "current_phase": "initialized",
            "completed_phases": [],
            "resume_context": {"blocking_reason": "", "last_artifact": ""},
            "rq": {"core": "", "sub_questions": [], "status": "draft"},
            "route_ledger": {"completed": [], "planned_next": []},
            "decisions_pending": [],
            "blocked_items": [],
        },
    }


def initialize_project(
    spec: ProjectSpec,
    manifest_path: str | os.PathLike[str] | None = None,
) -> dict[str, Any]:
    """Create a new project directory and its revision-zero manifest once.

    Existing directories are never treated as new projects; callers must use a
    separate, explicit resume path for an existing ARC manifest.
    """

    if not isinstance(spec, ProjectSpec):
        raise ArcError("initialize_project requires a ProjectSpec")
    project_path = spec.resolved_path
    if project_path.exists():
        raise PathPolicyError("project directory already exists; use resume instead")
    canonical_manifest = project_path / "research-manifest.yaml"
    target = Path(manifest_path).expanduser() if manifest_path else canonical_manifest
    if target.resolve(strict=False) != canonical_manifest.resolve(strict=False):
        raise PathPolicyError(
            "manifest_path must be the project's canonical research-manifest.yaml"
        )
    try:
        project_path.parent.mkdir(parents=True, exist_ok=True)
        project_path.mkdir()
        spec.artifact_dir.mkdir()
        manifest = create_initial_manifest(spec)
        return write_manifest_atomic(target, manifest)
    except FileExistsError as exc:
        raise PathPolicyError("project directory was created concurrently") from exc
    except (OSError, ManifestError):
        raise


def _artifact_present(artifacts: Sequence[str] | None, required_suffix: str) -> bool:
    required = required_suffix.replace("\\", "/")
    accepted = {required, f"./{required}"}
    return any(
        str(item).replace("\\", "/") in accepted
        for item in (artifacts or ())
    )


def _require_acquisition_manifest(
    acquisition_manifest: Mapping[str, Any] | None,
    *,
    expected_status: str,
) -> Mapping[str, Any]:
    if not isinstance(acquisition_manifest, Mapping):
        raise TransitionError("acquisition_manifest is required for this transition")
    if acquisition_manifest.get("status") != expected_status:
        raise TransitionError(
            f"acquisition_manifest.status must be {expected_status!r}"
        )
    return acquisition_manifest


def _acquisition_is_resolved(acquisition_manifest: Mapping[str, Any]) -> bool:
    entries = acquisition_manifest.get("entries", [])
    if not isinstance(entries, list):
        raise TransitionError("acquisition_manifest.entries must be a list")
    unresolved = {"pending", "not_attempted", "in_progress"}
    for entry in entries:
        if not isinstance(entry, Mapping):
            raise TransitionError("acquisition entry must be a mapping")
        status = entry.get("acquisition_status")
        if status not in ACQUISITION_ENTRY_STATUSES:
            raise TransitionError(f"unknown acquisition_status: {status!r}")
        if status in unresolved:
            return False
    return True


def _require_loop_artifact(to_phase: str, artifacts: Sequence[str] | None) -> None:
    required = {
        "design": "artifacts/design/rq-brief.md",
        "plan": "artifacts/plan/search-strategy.yaml",
        "curate": "artifacts/plan/search-strategy.yaml",
    }.get(to_phase)
    if required and not _artifact_present(artifacts, required):
        raise TransitionError(f"loop target artifact is required: {required}")


def transition_manifest(
    manifest: Mapping[str, Any],
    from_phase: str,
    to_phase: str,
    approved: bool,
    artifacts: Sequence[str] | None = None,
    acquisition_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply one checked phase transition without mutating ``manifest``."""

    if not isinstance(manifest, Mapping):
        raise ManifestError("manifest must be a mapping")
    state = manifest.get("state")
    if not isinstance(state, Mapping):
        raise ManifestError("manifest.state must be a mapping")
    actual_phase = state.get("current_phase")
    if actual_phase != from_phase:
        raise TransitionError(f"expected phase {from_phase!r}, found {actual_phase!r}")
    if from_phase not in PHASES or to_phase not in PHASES:
        raise TransitionError("unknown phase")
    if to_phase not in _ALLOWED_TRANSITIONS.get(from_phase, frozenset()):
        raise TransitionError(f"forbidden transition: {from_phase} -> {to_phase}")
    if not approved:
        raise TransitionError("human approval is required before phase transition")

    if from_phase == "design" and to_phase == "plan":
        if not _artifact_present(artifacts, "artifacts/design/rq-brief.md"):
            raise TransitionError("rq-brief artifact is required")
    if from_phase == "plan" and to_phase == "curate":
        if not _artifact_present(artifacts, "artifacts/plan/search-strategy.yaml"):
            raise TransitionError("search-strategy artifact is required")
    if from_phase == "curate" and to_phase == "acquisition_pending":
        _require_acquisition_manifest(acquisition_manifest, expected_status="pending")
    if to_phase == "reflection" and from_phase in {"curate", "acquisition_pending"}:
        resolved_manifest = _require_acquisition_manifest(
            acquisition_manifest,
            expected_status="resolved",
        )
        if not _acquisition_is_resolved(resolved_manifest):
            raise TransitionError("acquisition_manifest still has unresolved entries")
    if from_phase == "reflection":
        _require_loop_artifact(to_phase, artifacts)

    updated = copy.deepcopy(dict(manifest))
    updated_state = updated.setdefault("state", {})
    completed = list(updated_state.get("completed_phases") or [])
    if from_phase not in completed:
        completed.append(from_phase)
    updated_state["completed_phases"] = completed
    updated_state["current_phase"] = to_phase
    updated["status"] = "paused" if to_phase == "acquisition_pending" else "active"
    current_revision = int(updated.get("revision", 0))
    next_revision = current_revision + 1
    updated["revision"] = next_revision
    updated["updated"] = _now()[:10]
    updated.setdefault("events", []).append(
        {
            "id": uuid.uuid4().hex,
            "type": "phase_transition",
            "phase": to_phase,
            "from_phase": from_phase,
            "to_phase": to_phase,
            "revision": next_revision,
            "timestamp": _now(),
        }
    )
    return updated


def pause_manifest(manifest: Mapping[str, Any], reason: str) -> dict[str, Any]:
    """Record a Human Gate or external wait without changing the current phase."""

    if not isinstance(manifest, Mapping):
        raise ManifestError("manifest must be a mapping")
    state = manifest.get("state")
    if not isinstance(state, Mapping):
        raise ManifestError("manifest.state must be a mapping")
    updated = copy.deepcopy(dict(manifest))
    updated["status"] = "paused"
    resume_context = updated.setdefault("state", {}).setdefault("resume_context", {})
    resume_context["blocking_reason"] = str(reason)
    current_revision = int(updated.get("revision", 0))
    next_revision = current_revision + 1
    updated["revision"] = next_revision
    updated["updated"] = _now()[:10]
    updated.setdefault("events", []).append(
        {
            "id": uuid.uuid4().hex,
            "type": "human_gate_pause",
            "phase": updated["state"].get("current_phase"),
            "reason": str(reason),
            "revision": next_revision,
            "timestamp": _now(),
        }
    )
    return updated


def validate_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Validate evidence scope without inferring document content."""

    if not isinstance(candidate, Mapping):
        raise ArcError("candidate must be a mapping")
    scope = candidate.get("evidence_scope")
    if scope not in EVIDENCE_SCOPES:
        return {"valid": False, "reason": f"unknown evidence_scope: {scope!r}"}
    if scope == "fulltext_ready" and candidate.get("human_acquired") is not True:
        return {"valid": False, "reason": "fulltext_ready requires human_acquired=true"}
    return {"valid": True, "evidence_scope": scope}


def validate_provider_status(status: str) -> dict[str, Any]:
    """Validate provider status; notably, errors are not zero hits."""

    if status not in PROVIDER_STATUSES:
        return {"valid": False, "reason": f"unknown provider_status: {status!r}"}
    return {"valid": True, "provider_status": status}


def _validate_manifest_minimum(manifest: Mapping[str, Any]) -> None:
    required = {"manifest_version", "project_id", "revision", "status", "state", "events"}
    missing = sorted(required - set(manifest))
    if missing:
        raise ManifestError(f"missing manifest keys: {', '.join(missing)}")
    if not isinstance(manifest["revision"], int) or manifest["revision"] < 0:
        raise ManifestError("revision must be a non-negative integer")
    if manifest["status"] not in STATUSES:
        raise ManifestError(f"unknown manifest status: {manifest['status']!r}")
    state = manifest["state"]
    if not isinstance(state, Mapping) or state.get("current_phase") not in PHASES:
        raise ManifestError("state.current_phase is invalid")


def load_manifest(path: str | os.PathLike[str]) -> dict[str, Any]:
    """Safely load and minimally validate a YAML manifest."""

    yaml_module = _require_yaml()
    manifest_path = Path(path)
    try:
        with manifest_path.open("r", encoding="utf-8") as handle:
            data = yaml_module.safe_load(handle)
    except (OSError, yaml_module.YAMLError) as exc:
        raise ManifestError(f"cannot read manifest {manifest_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ManifestError("manifest root must be a mapping")
    try:
        _validate_manifest_minimum(data)
    except (TypeError, ValueError, KeyError) as exc:
        raise ManifestError(str(exc)) from exc
    return data


def write_manifest_atomic(
    path: str | os.PathLike[str],
    manifest: Mapping[str, Any],
    expected_revision: int | None = None,
) -> dict[str, Any]:
    """Write a manifest atomically with optimistic revision checking.

    A persistent sibling lock serializes the read/check/write sequence so two
    writers cannot both validate the same revision and then silently overwrite
    one another.
    """

    yaml_module = _require_yaml()
    if not isinstance(manifest, Mapping):
        raise ManifestError("manifest must be a mapping")
    candidate = copy.deepcopy(dict(manifest))
    _validate_manifest_minimum(candidate)
    manifest_path = Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if manifest_path.is_symlink():
        raise PathPolicyError("manifest path must not be a symlink")

    lock_path = manifest_path.with_name(manifest_path.name + ".lock")
    if lock_path.is_symlink():
        raise PathPolicyError("manifest lock path must not be a symlink")
    temp_path: Path | None = None
    try:
        with lock_path.open("a+", encoding="utf-8") as lock_handle:
            if fcntl is not None:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            try:
                if manifest_path.exists():
                    current = load_manifest(manifest_path)
                    current_revision = int(current["revision"])
                    if expected_revision != current_revision:
                        raise RevisionConflict(
                            f"expected revision {expected_revision}, found {current_revision}"
                        )
                    if int(candidate["revision"]) != current_revision + 1:
                        raise ManifestError(
                            "updated manifest revision must increment by exactly one"
                        )
                else:
                    if expected_revision not in (None, 0):
                        raise RevisionConflict("new manifest expected_revision must be None or 0")
                    if int(candidate["revision"]) != 0:
                        raise ManifestError("new manifest must start at revision zero")

                with tempfile.NamedTemporaryFile(
                    mode="w",
                    encoding="utf-8",
                    dir=manifest_path.parent,
                    prefix=f"{manifest_path.name}.tmp.",
                    delete=False,
                ) as handle:
                    temp_path = Path(handle.name)
                    yaml_module.safe_dump(
                        candidate,
                        handle,
                        allow_unicode=True,
                        sort_keys=False,
                        default_flow_style=False,
                    )
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_path, manifest_path)
                temp_path = None
                return load_manifest(manifest_path)
            finally:
                if fcntl is not None:
                    fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)
    except RevisionConflict:
        raise
    except (OSError, yaml_module.YAMLError, ManifestError) as exc:
        raise ManifestError(f"atomic manifest write failed: {exc}") from exc
    finally:
        if temp_path is not None:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
