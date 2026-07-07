#!/usr/bin/env python3
"""ARS Collaboration Depth Observer (v3.5.0, advisory only).

Scores user-AI collaboration on four dimensions at every FULL/SLIM
checkpoint and at pipeline completion. The observer is advisory only and
never blocks. MANDATORY integrity gates (2.5 / 4.5) explicitly skip the
observer to prevent dilution.

Upstream reference: shared/collaboration_depth_rubric.md
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

Dimension = Literal[
    "delegation_intensity",
    "cognitive_vigilance",
    "cognitive_reallocation",
    "zone_classification",
]

DIMENSION_DESCRIPTIONS: Dict[Dimension, str] = {
    "delegation_intensity": "How much the user delegates to AI vs does themselves",
    "cognitive_vigilance": "User catches AI errors and challenges output",
    "cognitive_reallocation": "User reallocates freed cognition to higher-order work",
    "zone_classification": "Delegation Zone / Vigilance Zone / Reallocation Zone",
}

Zone = Literal["Delegation", "Vigilance", "Reallocation", "Mixed"]


@dataclass
class CollaborationDepthScore:
    """Score for one dimension (1-100, advisory)."""

    dimension: str
    score: int
    rationale: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dimension": self.dimension,
            "score": self.score,
            "rationale": self.rationale,
        }


@dataclass
class CollaborationDepthReport:
    """Full observer report for one checkpoint or pipeline completion."""

    checkpoint: str
    scores: List[CollaborationDepthScore] = field(default_factory=list)
    overall_score: int = 0
    zone: Zone = "Mixed"
    advisory_only: bool = True

    def compute_overall(self) -> int:
        if not self.scores:
            self.overall_score = 0
            return 0
        total = sum(s.score for s in self.scores)
        self.overall_score = int(total / len(self.scores))
        return self.overall_score

    def classify_zone(self) -> Zone:
        """Classify the dominant zone from the four dimension scores."""
        if not self.scores:
            self.zone = "Mixed"
            return self.zone
        dim_scores = {s.dimension: s.score for s in self.scores}
        delegation = dim_scores.get("delegation_intensity", 0)
        vigilance = dim_scores.get("cognitive_vigilance", 0)
        reallocation = dim_scores.get("cognitive_reallocation", 0)
        best = max(delegation, vigilance, reallocation)
        if best == delegation:
            self.zone = "Delegation"
        elif best == vigilance:
            self.zone = "Vigilance"
        elif best == reallocation:
            self.zone = "Reallocation"
        else:
            self.zone = "Mixed"
        return self.zone

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint": self.checkpoint,
            "scores": [s.to_dict() for s in self.scores],
            "overall_score": self.overall_score,
            "zone": self.zone,
            "advisory_only": self.advisory_only,
        }


def observe_checkpoint(
    checkpoint: str,
    *,
    user_turns: int = 0,
    ai_turns: int = 0,
    user_challenges: int = 0,
    user_edits: int = 0,
    high_order_user_contributions: int = 0,
) -> CollaborationDepthReport:
    """Generate an advisory collaboration-depth report for a checkpoint.

    Args:
        checkpoint: Identifier for the checkpoint (e.g. "stage-3-review").
        user_turns: Number of meaningful user turns in the checkpoint.
        ai_turns: Number of AI turns in the checkpoint.
        user_challenges: Times the user caught/challenged AI output.
        user_edits: Times the user edited AI-generated content.
        high_order_user_contributions: User contributions to framing, RQ, method, interpretation.

    Returns:
        CollaborationDepthReport with 4 dimension scores.
    """
    total_turns = user_turns + ai_turns

    # If no interaction data provided, return an empty advisory report.
    if total_turns == 0 and user_challenges == 0 and user_edits == 0 and high_order_user_contributions == 0:
        return CollaborationDepthReport(checkpoint=checkpoint)

    total_turns = max(total_turns, 1)

    # Delegation intensity: higher when user lets AI run but stays engaged
    delegation_pct = ai_turns / total_turns
    delegation_score = int(50 + 50 * delegation_pct)

    # Cognitive vigilance: higher when user challenges more
    challenge_rate = min(user_challenges / max(ai_turns, 1), 1.0)
    vigilance_score = int(30 + 70 * challenge_rate)

    # Cognitive reallocation: higher when user edits / reframes rather than just accepts
    reallocation_score = int(
        40
        + 30 * min(user_edits / max(ai_turns, 1), 1.0)
        + 30 * min(high_order_user_contributions / max(user_turns, 1), 1.0)
    )
    reallocation_score = min(reallocation_score, 100)

    # Zone classification is derived from the above three, not scored independently
    zone_score = int((delegation_score + vigilance_score + reallocation_score) / 3)

    report = CollaborationDepthReport(checkpoint=checkpoint)
    report.scores = [
        CollaborationDepthScore(
            dimension="delegation_intensity",
            score=delegation_score,
            rationale=f"{int(delegation_pct * 100)}% of turns driven by AI",
        ),
        CollaborationDepthScore(
            dimension="cognitive_vigilance",
            score=vigilance_score,
            rationale=f"{user_challenges} user challenge(s) across {ai_turns} AI turn(s)",
        ),
        CollaborationDepthScore(
            dimension="cognitive_reallocation",
            score=reallocation_score,
            rationale=f"{user_edits} edit(s) and {high_order_user_contributions} high-order contribution(s)",
        ),
        CollaborationDepthScore(
            dimension="zone_classification",
            score=zone_score,
            rationale="Derived from delegation/vigilance/reallocation balance",
        ),
    ]
    report.compute_overall()
    report.classify_zone()
    return report


def should_skip_observer(phase: Any) -> bool:
    """MANDATORY integrity gates skip the observer to prevent dilution."""
    return phase in ("2.5", "4.5")


if __name__ == "__main__":
    import json

    demo = observe_checkpoint(
        "stage-3-review",
        user_turns=3,
        ai_turns=5,
        user_challenges=2,
        user_edits=1,
        high_order_user_contributions=1,
    )
    print(json.dumps(demo.to_dict(), ensure_ascii=False, indent=2))
