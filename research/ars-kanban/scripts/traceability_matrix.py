#!/usr/bin/env python3
"""ARS R&R Traceability Matrix (Schema 11).

Tracks author revision claims against reviewer comments during the Stage 3'
re-review phase. Emits a verification matrix plus a new editorial decision
(Accept / Minor / Major) and enforces the hard revision-loop cap.

Upstream reference: academic-pipeline Stage 3' (RE-REVIEW) and Schema 11.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

Decision = Literal["Accept", "Minor", "Major"]


@dataclass
class TraceabilityRow:
    """One row of the Schema 11 traceability matrix."""

    reviewer_comment_id: str
    author_claim: str          # what the author says they changed
    verified: bool              # did the revision actually address it?
    evidence: str               # delta report / file reference
    residual_issue: Optional[str] = None  # if not fully resolved

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reviewer_comment_id": self.reviewer_comment_id,
            "author_claim": self.author_claim,
            "verified": self.verified,
            "evidence": self.evidence,
            "residual_issue": self.residual_issue,
        }


@dataclass
class TraceabilityMatrix:
    """Schema 11 matrix plus editorial decision for Stage 3'."""

    rows: List[TraceabilityRow] = field(default_factory=list)
    new_decision: Decision = "Accept"
    revision_loop_count: int = 0  # total across Stage 4 + 4'; max 2

    # Hard cap from upstream: max 2 revision loops total across Stages 4 + 4'.
    MAX_REVISION_LOOPS: int = field(default=2, init=False, repr=False)

    @property
    def verified_count(self) -> int:
        return sum(1 for row in self.rows if row.verified)

    @property
    def residual_count(self) -> int:
        return sum(1 for row in self.rows if row.residual_issue is not None)

    @property
    def can_revise_again(self) -> bool:
        """Return True if another revision loop is still allowed."""
        return self.revision_loop_count < self.MAX_REVISION_LOOPS

    def add_row(
        self,
        *,
        reviewer_comment_id: str,
        author_claim: str,
        verified: bool,
        evidence: str,
        residual_issue: Optional[str] = None,
    ) -> TraceabilityRow:
        row = TraceabilityRow(
            reviewer_comment_id=reviewer_comment_id,
            author_claim=author_claim,
            verified=verified,
            evidence=evidence,
            residual_issue=residual_issue,
        )
        self.rows.append(row)
        return row

    def compute_decision(self, default: Decision = "Accept") -> Decision:
        """Compute editorial decision from verification state.

        Logic:
        - Any unverified row with a residual issue → Major
        - Any unverified row without residual issue → Minor
        - All verified → Accept
        """
        for row in self.rows:
            if not row.verified:
                if row.residual_issue:
                    self.new_decision = "Major"
                else:
                    self.new_decision = "Minor"
                return self.new_decision
        self.new_decision = default
        return self.new_decision

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rows": [row.to_dict() for row in self.rows],
            "new_decision": self.new_decision,
            "revision_loop_count": self.revision_loop_count,
            "max_revision_loops": self.MAX_REVISION_LOOPS,
            "can_revise_again": self.can_revise_again,
            "verified_count": self.verified_count,
            "residual_count": self.residual_count,
        }


def build_traceability_matrix(
    review_report: Dict[str, Any],
    revision_delta: Dict[str, Any],
    current_loop_count: int = 0,
) -> TraceabilityMatrix:
    """Build a Schema 11 matrix by pairing reviewer comments with author claims.

    Args:
        review_report: Stage 3 review package (must contain reviewer comments).
        revision_delta: Stage 4 revision output (must map comment IDs to claims).
        current_loop_count: How many revision loops have already occurred.

    Returns:
        TraceabilityMatrix populated with verification rows.
    """
    matrix = TraceabilityMatrix(revision_loop_count=current_loop_count)

    comments = review_report.get("reviewer_comments", [])
    claims_by_id = {
        str(cid): claim for cid, claim in revision_delta.get("claims", {}).items()
    }

    for comment in comments:
        cid = str(comment.get("id", ""))
        author_claim = claims_by_id.get(cid, "")
        verified = bool(author_claim) and comment.get("addressed", False)
        evidence = revision_delta.get("delta_report_path", "")
        residual = None if verified else comment.get("residual_issue")

        matrix.add_row(
            reviewer_comment_id=cid,
            author_claim=author_claim or "[NO RESPONSE]",
            verified=verified,
            evidence=evidence,
            residual_issue=residual,
        )

    matrix.compute_decision()
    return matrix


if __name__ == "__main__":
    import json

    demo = TraceabilityMatrix(revision_loop_count=1)
    demo.add_row(
        reviewer_comment_id="R1-1",
        author_claim="Added effect-size reporting in Table 3.",
        verified=True,
        evidence="delta_report.md#L42",
    )
    demo.add_row(
        reviewer_comment_id="R2-3",
        author_claim="Clarified sampling frame in Methods.",
        verified=False,
        evidence="delta_report.md#L88",
        residual_issue="Sampling exclusion criteria still ambiguous.",
    )
    demo.compute_decision()
    print(json.dumps(demo.to_dict(), ensure_ascii=False, indent=2))
