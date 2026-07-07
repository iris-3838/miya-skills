#!/usr/bin/env python3
"""ARS Integrity Check — 7-mode AI failure checklist (Lu 2026).

Two gate modes:
- pre_review (Stage 2.5): 30% claim sampling, min 10 claims
- final_check (Stage 4.5): 100% claim verification, zero-tolerance

Failure modes (canonical order per ai_research_failure_modes.md):
  M1: Implementation bug passing AI self-review
  M2: Hallucinated citation
  M3: Hallucinated experimental result
  M4: Shortcut reliance
  M5: Implementation bug reframed as novel insight
  M6: Methodology fabrication
  M7: Frame-lock at early pipeline stage
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

# 7 failure modes in canonical order
FAILURE_MODES = ["M1", "M2", "M3", "M4", "M5", "M6", "M7"]

FAILURE_MODE_DESCRIPTIONS: Dict[str, str] = {
    "M1": "Implementation bug passing AI self-review",
    "M2": "Hallucinated citation",
    "M3": "Hallucinated experimental result",
    "M4": "Shortcut reliance",
    "M5": "Implementation bug reframed as novel insight",
    "M6": "Methodology fabrication",
    "M7": "Frame-lock at early pipeline stage",
}

CheckResult = Literal["CLEAR", "SUSPECTED", "OVERRIDDEN"]
GateMode = Literal["pre_review", "final_check"]


@dataclass
class IntegrityReport:
    """Result of a 7-mode AI failure checklist run."""

    mode: GateMode
    results: Dict[str, CheckResult] = field(default_factory=dict)
    claim_sample_count: int = 0
    claim_total: int = 0
    max_rounds: int = 3
    round_num: int = 1
    notes: Dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """Return True if no mode is SUSPECTED (OVERRIDDEN is acceptable)."""
        return all(r in ("CLEAR", "OVERRIDDEN") for r in self.results.values())

    @property
    def suspected_modes(self) -> List[str]:
        return [mode for mode, result in self.results.items() if result == "SUSPECTED"]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "results": dict(self.results),
            "claim_sample_count": self.claim_sample_count,
            "claim_total": self.claim_total,
            "passed": self.passed,
            "round_num": self.round_num,
            "max_rounds": self.max_rounds,
            "suspected_modes": self.suspected_modes,
            "notes": dict(self.notes),
        }


def _default_results(overrides: Optional[Dict[str, CheckResult]] = None) -> Dict[str, CheckResult]:
    """Return default CLEAR results, applying overrides where provided."""
    overrides = overrides or {}
    return {mode: overrides.get(mode, "CLEAR") for mode in FAILURE_MODES}


def _sample_size(mode: GateMode, total: int) -> int:
    """Return the number of claims to inspect for the gate mode."""
    if mode == "final_check":
        return total
    # pre_review: 30% with a minimum of 10, capped at total
    return min(total, max(10, int(total * 0.3)))


def run_integrity_check(
    mode: GateMode,
    claims: List[Dict[str, Any]],
    passport: Optional[Dict[str, Any]] = None,
    overrides: Optional[Dict[str, CheckResult]] = None,
    round_num: int = 1,
    max_rounds: int = 3,
) -> IntegrityReport:
    """Run the 7-mode failure checklist.

    Args:
        mode: "pre_review" or "final_check".
        claims: List of claim dicts to verify. Each should have at least a
                "text" key; other metadata is preserved but not inspected here.
        passport: Material Passport dict (optional; reserved for provenance).
        overrides: User-provided override results for specific failure modes.
        round_num: Current verification round (1-indexed).
        max_rounds: Maximum allowed re-verification rounds before hard block.

    Returns:
        IntegrityReport with sampled claim counts and per-mode results.
    """
    total = len(claims)
    sample_size = _sample_size(mode, total)

    report = IntegrityReport(
        mode=mode,
        results=_default_results(overrides),
        claim_sample_count=sample_size,
        claim_total=total,
        round_num=round_num,
        max_rounds=max_rounds,
    )

    # Placeholder: detailed per-claim analysis is delegated to the
    # integrity_verification_agent at runtime. This module provides the
    # structural contract, sampling policy, and result shape.
    if passport:
        report.notes["passport_version_label"] = passport.get("version_label", "unknown")

    return report


def next_round_report(report: IntegrityReport) -> IntegrityReport:
    """Return a fresh report for the next verification round, if allowed."""
    if report.round_num >= report.max_rounds:
        raise ValueError(
            f"Cannot advance beyond max_rounds ({report.max_rounds}); "
            "fix underlying issues before re-running the gate."
        )
    return IntegrityReport(
        mode=report.mode,
        results=_default_results(),
        claim_sample_count=report.claim_sample_count,
        claim_total=report.claim_total,
        max_rounds=report.max_rounds,
        round_num=report.round_num + 1,
    )


if __name__ == "__main__":
    import json

    demo_claims = [{"text": "placeholder claim"} for _ in range(25)]
    pre = run_integrity_check("pre_review", demo_claims)
    final = run_integrity_check("final_check", demo_claims)
    print("pre_review:", json.dumps(pre.to_dict(), ensure_ascii=False, indent=2))
    print("final_check:", json.dumps(final.to_dict(), ensure_ascii=False, indent=2))
