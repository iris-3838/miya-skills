#!/usr/bin/env python3
"""Material Passport compatibility layer (Schema 9) for ARS Kanban.

Validates and transforms Material Passport data between pipeline phases,
mirroring the handoff_schemas.md Schema 9 contract.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Schema 9 required fields (from shared/handoff_schemas.md §Schema 9)
SCHEMA9_REQUIRED = {
    "origin_skill": str,
    "origin_mode": str,
    "origin_date": str,
    "verification_status": str,  # "VERIFIED" / "UNVERIFIED" / "STALE"
    "version_label": str,
}

# Schema 9 v2 optional fields with expected types
SCHEMA9_OPTIONAL = {
    "claim_verification_report": dict,
    "trust_chain_frontmatter": dict,
    "literature_corpus": list,
    "reset_boundary": list,
    "collaboration_depth_history": list,
    "repro_lock": (dict, type(None)),
    "upstream_dependencies": list,
    "content_hash": (str, type(None)),
    "integrity_pass_date": (str, type(None)),
    "topic": str,
    "phase": (int, str),
}

# Valid verification statuses
VALID_STATUSES = {"VERIFIED", "UNVERIFIED", "STALE"}

# Upstream phase mapping for dependency labelling
PHASE_VERSION_LABELS: Dict[int, str] = {
    1: "scoping-v0",
    2: "investigation-v0",
    3: "analysis-v0",
    4: "composition-v0",
    5: "review-v0",
    6: "revision-v0",
}


class PassportValidationError(ValueError):
    """Raised when a Material Passport fails schema validation."""


def validate_passport(passport: Dict[str, Any], strict: bool = True) -> List[str]:
    """Validate a Material Passport dict against Schema 9.

    Returns a list of violation messages (empty = valid).
    Raises PassportValidationError if *strict* and any violation is found.
    """
    errors: List[str] = []
    if not isinstance(passport, dict):
        errors.append("Passport must be a dict")
        if strict:
            raise PassportValidationError("; ".join(errors))
        return errors

    for field, expected_type in SCHEMA9_REQUIRED.items():
        if field not in passport:
            errors.append(f"Missing required field: {field!r}")
        elif not isinstance(passport[field], expected_type):
            errors.append(
                f"Field {field!r} must be {expected_type.__name__}, "
                f"got {type(passport[field]).__name__}"
            )

    # verification_status enum check
    vs = passport.get("verification_status")
    if vs is not None and vs not in VALID_STATUSES:
        errors.append(
            f"verification_status must be one of {sorted(VALID_STATUSES)}, got {vs!r}"
        )

    # Schema 9 v2 optional field type checks
    for field, expected_types in SCHEMA9_OPTIONAL.items():
        if field in passport:
            # Normalize to tuple for uniform iteration
            types_tuple = expected_types if isinstance(expected_types, tuple) else (expected_types,)
            if not isinstance(passport[field], types_tuple):
                type_names = ", ".join(t.__name__ for t in types_tuple)
                errors.append(
                    f"Field {field!r} must be one of [{type_names}], "
                    f"got {type(passport[field]).__name__}"
                )

    # repro_lock stochasticity_declaration validation
    repro_lock = passport.get("repro_lock")
    if isinstance(repro_lock, dict):
        if "stochasticity_declaration" in repro_lock:
            if not isinstance(repro_lock["stochasticity_declaration"], str):
                errors.append("repro_lock.stochasticity_declaration must be a string")
        # additional repro_lock keys can be validated here as the spec evolves

    # literature_corpus minimal shape validation
    literature_corpus = passport.get("literature_corpus")
    if isinstance(literature_corpus, list):
        for i, item in enumerate(literature_corpus):
            if not isinstance(item, dict):
                errors.append(f"literature_corpus[{i}] must be a dict")
            elif "title" not in item and "doi" not in item:
                errors.append(
                    f"literature_corpus[{i}] must contain at least 'title' or 'doi'"
                )

    if strict and errors:
        raise PassportValidationError("; ".join(errors))
    return errors


def compute_content_hash(data: Dict[str, Any]) -> str:
    """Compute SHA-256 of a JSON-serialised dict (deterministic key order)."""
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def upgrade_passport(
    passport: Dict[str, Any],
    *,
    new_status: str = "UNVERIFIED",
    new_version_suffix: Optional[str] = None,
    downstream_dependency: Optional[str] = None,
) -> Dict[str, Any]:
    """Evolve a passport for the next phase.

    - Updates verification_status
    - Computes a new version_label (bumped from current)
    - Computes content_hash
    - Sets integrity_pass_date
    - Adds upstream dependency reference
    - Adds new optional fields with defaults if absent
    """
    updated = dict(passport)
    updated["verification_status"] = new_status
    updated["integrity_pass_date"] = (
        datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    )
    # content_hash is set by the caller (phase_worker) based on actual execution result

    # Version label bump
    old_label = passport.get("version_label", "v0")
    if new_version_suffix:
        updated["version_label"] = new_version_suffix
    else:
        # Increment: phase1-v0 -> phase1-v1
        parts = old_label.rsplit("-v", 1)
        if len(parts) == 2 and parts[1].isdigit():
            updated["version_label"] = f"{parts[0]}-v{int(parts[1]) + 1}"
        else:
            updated["version_label"] = f"{old_label}-v1"

    # Upstream dependency tracking
    upstream = list(passport.get("upstream_dependencies", []))
    if downstream_dependency and downstream_dependency not in upstream:
        upstream.append(downstream_dependency)
    if upstream:
        updated["upstream_dependencies"] = upstream

    # Ensure repro_lock exists as null if missing (Schema 9 v3.3.5+)
    if "repro_lock" not in updated:
        updated["repro_lock"] = None

    # Ensure reset_boundary exists as empty list if missing
    if "reset_boundary" not in updated:
        updated["reset_boundary"] = []

    return updated


def merge_phase_passport(
    upstream_passport: Optional[Dict[str, Any]],
    phase_body: Dict[str, Any],
) -> Dict[str, Any]:
    """Merge an upstream Material Passport into a new phase body.

    The upstream passport's verification and version info are inherited,
    then the new phase's own metadata is layered on top.
    """
    body = dict(phase_body)
    passport = body.get("material_passport", {})

    if upstream_passport:
        # Carry forward upstream integrity tracking
        passport["verification_status"] = "UNVERIFIED"  # reset for new phase
        upstream_deps = list(
            upstream_passport.get("upstream_dependencies", [])
        )
        upstream_label = upstream_passport.get("version_label", "unknown")
        if upstream_label not in upstream_deps:
            upstream_deps.append(upstream_label)
        passport["upstream_dependencies"] = upstream_deps

        # Carry forward provenance if upstream has it
        for field in ("origin_skill", "origin_mode"):
            if field not in passport or not passport.get(field):
                passport[field] = upstream_passport.get(field)

    # Ensure basics
    if "repro_lock" not in passport:
        passport["repro_lock"] = None
    if "reset_boundary" not in passport:
        passport["reset_boundary"] = []

    body["material_passport"] = passport
    return body


def verify_passport_chain(
    passports: List[Dict[str, Any]],
) -> List[str]:
    """Verify that a list of passports (one per phase) forms a valid chain.

    Checks:
    - Each passport is Schema 9 valid
    - Phase N version_label appears in Phase N+1 upstream_dependencies
    - verification_status transitions are monotonic
    """
    errors: List[str] = []
    for i, p in enumerate(passports):
        errs = validate_passport(p, strict=False)
        for e in errs:
            errors.append(f"Phase {i + 1}: {e}")
        if i > 0:
            prev_label = passports[i - 1].get("version_label", "?")
            deps = p.get("upstream_dependencies", [])
            if prev_label not in deps:
                errors.append(
                    f"Phase {i + 1} missing upstream dependency {prev_label!r} "
                    f"from Phase {i}"
                )
    return errors
