#!/usr/bin/env python3
"""Wording-Pattern Advisory (Kong #257) — surface phrasing check.

Detects AI-typical research-question shells in user utterances. Does NOT
judge idea quality, novelty, feasibility, or whether the user is "right."
Same idea phrased in domain-native vocabulary should not trigger.

Reference: academic-research-skills/deep-research/agents/socratic_mentor_agent.md
§"Wording-Pattern Advisory (Kong #257)"
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# 20 patterns (WP01-WP20) — each is a list of regex patterns that, when matched
# with high confidence, trigger the advisory. Patterns are intentionally
# surface-level (syntactic), not semantic.
WORDING_PATTERNS: Dict[str, Dict[str, Any]] = {
    "WP01": {
        "family": "impact/effect frame",
        "examples": ["the impact of X on Y", "the effect of X on Y"],
        "patterns": [
            r"\b(?:impact|effect)\s+of\s+\w[\w\s'-]{0,40}?\s+on\s+\w[\w\s'-]{0,40}",
        ],
    },
    "WP02": {
        "family": "relationship frame",
        "examples": ["relationship between A and B"],
        "patterns": [
            r"\brelationship\s+between\s+\w[\w\s'-]{0,40}?\s+and\s+\w[\w\s'-]{0,40}",
        ],
    },
    "WP03": {
        "family": "role frame",
        "examples": ["the role of X in Y"],
        "patterns": [
            r"\b(?:role|function)\s+of\s+\w[\w\s'-]{0,40}?\s+in\s+\w[\w\s'-]{0,40}",
        ],
    },
    "WP04": {
        "family": "influence frame",
        "examples": ["how X influences Y", "how X affects Y"],
        "patterns": [
            r"\bhow\s+\w[\w\s'-]{0,40}?\s+(?:influences?|affects?|impacts?)\s+\w[\w\s'-]{0,40}",
        ],
    },
    "WP05": {
        "family": "generic factors frame",
        "examples": ["factors influencing Y", "factors affecting Y"],
        "patterns": [
            r"\bfactors\s+(?:influencing|affecting|impacting)\s+\w[\w\s'-]{0,40}",
        ],
    },
    "WP06": {
        "family": "bare study-of frame",
        "examples": ["a study of X and Y"],
        "patterns": [
            r"\b(?:a\s+)?study\s+of\s+\w[\w\s'-]{0,40}?\s+and\s+\w[\w\s'-]{0,40}",
        ],
    },
    "WP07": {
        "family": "impact case-study frame",
        "examples": ["the impact of X on Y: a case study"],
        "patterns": [
            r"\b(?:impact|effect)\s+of\s+\w[\w\s'-]{0,40}?:\s*a\s+case\s+study",
        ],
    },
    "WP08": {
        "family": "challenges/opportunities pair",
        "examples": ["challenges and opportunities of X in Y"],
        "patterns": [
            r"\bchallenges?\s+and\s+opportunities\s+of\s+\w[\w\s'-]{0,40}",
        ],
    },
    "WP09": {
        "family": "perception/attitude survey frame",
        "examples": ["perceptions/attitudes toward X"],
        "patterns": [
            r"\b(?:perceptions?|attitudes?|views?)\s+(?:of|toward|towards)\s+\w[\w\s'-]{0,40}",
        ],
    },
    "WP10": {
        "family": "performance/achievement effect frame",
        "examples": ["the effect of X on performance/achievement"],
        "patterns": [
            r"\b(?:impact|effect)\s+of\s+\w[\w\s'-]{0,40}?\s+on\s+(?:[\w\s'-]{0,20}?)(?:performance|achievement|learning)",
        ],
    },
    "WP11": {
        "family": "achievement relationship frame",
        "examples": ["relationship between X and academic achievement"],
        "patterns": [
            r"\brelationship\s+between\s+\w[\w\s'-]{0,40}?\s+and\s+(?:academic\s+)?(?:achievement|performance)",
        ],
    },
    "WP12": {
        "family": "generic use/application frame",
        "examples": ["exploring the use/application of X in Y"],
        "patterns": [
            r"\b(?:use|application|usage)\s+of\s+\w[\w\s'-]{0,40}?\s+in\s+\w[\w\s'-]{0,40}",
        ],
    },
    "WP13": {
        "family": "effectiveness frame",
        "examples": ["effectiveness of X for Y"],
        "patterns": [
            r"\beffectiveness\s+of\s+\w[\w\s'-]{0,40}?\s+(?:for|in|on)\s+\w[\w\s'-]{0,40}",
        ],
    },
    "WP14": {
        "family": "mediator/moderator template",
        "examples": ["mediating/moderating role of X"],
        "patterns": [
            r"\b(?:mediating|moderating)\s+(?:role|effect)\s+of\s+\w[\w\s'-]{0,40}",
        ],
    },
    "WP15": {
        "family": "adoption/intention/satisfaction factors",
        "examples": ["factors affecting adoption/intention/satisfaction"],
        "patterns": [
            r"\bfactors\s+(?:affecting|influencing)\s+(?:adoption|intention|satisfaction|acceptance)",
        ],
    },
    "WP16": {
        "family": "barriers/facilitators pair",
        "examples": ["barriers and facilitators to X"],
        "patterns": [
            r"\bbarriers?\s+and\s+facilitators?\s+(?:to|of)\s+\w[\w\s'-]{0,40}",
        ],
    },
    "WP17": {
        "family": "comparative-study shell",
        "examples": ["a comparative study of X and Y"],
        "patterns": [
            r"\bcomparative\s+study\s+of\s+\w[\w\s'-]{0,40}?\s+and\s+\w[\w\s'-]{0,40}",
        ],
    },
    "WP18": {
        "family": "framework/model shell",
        "examples": ["toward a framework/model for X"],
        "patterns": [
            r"\b(?:framework|model)\s+for\s+\w[\w\s'-]{0,40}",
            r"\btoward(?:s)?\s+a\s+(?:framework|model)\s+for\s+\w[\w\s'-]{0,40}",
        ],
    },
    "WP19": {
        "family": "technology-enhancement shell",
        "examples": ["role of technology/AI/digital tools in enhancing Y"],
        "patterns": [
            r"\brole\s+of\s+(?:technology|AI|artificial\s+intelligence|digital\s+tools?|ICT)\s+in\s+(?:enhancing|improving)",
        ],
    },
    "WP20": {
        "family": "experience-of frame",
        "examples": ["exploring the experiences of X in/with Y"],
        "patterns": [
            r"\bexperiences?\s+of\s+\w[\w\s'-]{0,40}?\s+(?:in|with|of)\s+\w[\w\s'-]{0,40}",
        ],
    },
}


# Domain-native vocabulary indicators — when present, suppress the advisory
# even if a surface pattern matches, because the user is already using field-
# specific terms that signal domain expertise.
DOMAIN_NATIVE_MARKERS = {
    # LIS
    "information behavior", "information seeking", "information use",
    "information practice", "information literacy", "information need",
    "domain analysis", "domain-analytic", "epistemological", "epistemic",
    "hermeneutic", "pragmatist", "pragmatism", "socio-cultural",
    "knowledge organization", "bibliographic", "cataloging", "classification",
    "thesauri", "metadata", "controlled vocabulary",
    # Common academic theory terms
    "heidegger", "bates", "hjørland", "hjorland", "foucault", "habermas",
    "kuhn", "popper", "lakatos", "bachelard", "alisedo", "feyerabend",
    "meadow", "buckland", "frohmann", "hine", "talja", "tuominen", "savolainen",
    "casey", "dervin", "belkin", "durrance", "kuhlthau", "wilson", "ellis",
    "krikelas", "mccKenzie", "johannesen",
    # Other theoretical names
    "latour", "callon", "law", "knorr-cetina", "pickering", "gerson",
    "haraway", "keller", "longino",
    # Methodology signals
    "phenomenographic", "phenomenography", "phenomenology", "grounded theory",
    "discourse analysis", "ethnography", "foucauldian", "genealogical",
    "archaeological", "interpretivist", "interpretive", "constructivist",
    "positivist", "post-positivist", "critical realism", "activity theory",
    "actor-network",
}


def extract_rq_candidates(utterance: str) -> List[str]:
    """Extract RQ-like sentence candidates from a user utterance.

    Heuristic: sentences containing question marks, or sentences starting with
    typical RQ openers ("how", "what", "why", "in what way", "to what extent"),
    or sentences that read like declarative research questions.
    """
    if not utterance:
        return []

    # Split on sentence boundaries (period, question mark, exclamation)
    raw_sentences = re.split(r"(?<=[.?!])\s+", utterance.strip())

    candidates = []
    rq_openers = (
        r"^(?:how|what|why|when|where|who|which|to what extent|in what way|"
        r"to what degree|is there|are there|does|do|did|can|could|would|"
        r"should|will|may|might)\b"
    )

    for sent in raw_sentences:
        sent = sent.strip()
        if not sent or len(sent) < 8:  # too short to be an RQ
            continue
        # Direct questions
        if sent.rstrip().endswith("?"):
            candidates.append(sent.rstrip("?").rstrip())
            continue
        # Declarative research-question-like sentences starting with RQ opener
        if re.match(rq_openers, sent, re.IGNORECASE):
            candidates.append(sent.rstrip("."))
            continue
        # "The [impact/effect/...] of X on Y" declarative patterns
        if re.match(
            r"^(?:the|this|a|an)\s+(?:impact|effect|role|influence|relationship|"
            r"study|exploration|investigation|examination|analysis|assessment|"
            r"exploring|investigating|examining|analyzing|understanding)\s+",
            sent, re.IGNORECASE,
        ):
            candidates.append(sent.rstrip("."))
            continue
        # "I want to study/investigate/explore the X" patterns
        if re.match(
            r"^i\s+(?:want|wish|would like|aim|intend|plan|propose|hypothesize|"
            r"intend|seek)\s+to\s+(?:study|investigate|explore|examine|"
            r"analyze|understand|research|assess|evaluate|compare)\s+",
            sent, re.IGNORECASE,
        ):
            candidates.append(sent.rstrip("."))
            continue
        # "Exploring/Investigating/Examining the X" gerund forms
        if re.match(
            r"^(?:exploring|investigating|examining|analyzing|studying|"
            r"researching|assessing|evaluating|comparing|understanding|"
            r"factors\s+(?:influencing|affecting|impacting))\s+",
            sent, re.IGNORECASE,
        ):
            candidates.append(sent.rstrip("."))

    return candidates


def has_domain_native_vocabulary(text: str) -> bool:
    """Return True if text contains domain-specific markers (LIS, theory names, etc.).

    When True, the wording advisory is suppressed because the user is already
    using field-native terms that signal domain expertise.
    """
    if not text:
        return False
    text_lower = text.lower()
    return any(marker in text_lower for marker in DOMAIN_NATIVE_MARKERS)


def match_wording_patterns(
    text: str,
    *,
    require_high_confidence: bool = True,
    min_patterns_matched: int = 1,
) -> List[Dict[str, str]]:
    """Match a text string against the 20 wording patterns.

    Returns a list of matched pattern dicts, each with keys:
      - id: e.g. "WP01"
      - family: pattern family name
      - matched_phrase: the specific phrase that matched
      - excerpt: the user excerpt (up to 200 chars) for advisory output

    Args:
        text: user utterance to analyze
        require_high_confidence: if True (default), only return matches where
            >= min_patterns_matched regex patterns from the same family matched
        min_patterns_matched: minimum number of patterns from a family that
            must match (default 1). For families with multiple patterns this
            acts as a confidence threshold.
    """
    if not text or not text.strip():
        return []

    matches = []
    for wp_id, spec in WORDING_PATTERNS.items():
        family_matches = []
        for pat in spec["patterns"]:
            for m in re.finditer(pat, text, re.IGNORECASE):
                family_matches.append(m.group(0))
        if not family_matches:
            continue
        # Apply confidence threshold
        unique_phrases = list(set(family_matches))
        if require_high_confidence and len(unique_phrases) < min_patterns_matched:
            continue
        for phrase in unique_phrases:
            matches.append({
                "id": wp_id,
                "family": spec["family"],
                "matched_phrase": phrase,
                "excerpt": text[:200],
            })
    return matches


def detect_wording_advisory(
    user_utterance: str,
    *,
    history: Optional[List[Dict[str, Any]]] = None,
) -> Optional[Dict[str, Any]]:
    """Detect whether a wording-pattern advisory should fire.

    Returns None if no advisory is warranted, or a dict with keys:
      - triggered: bool (always True when returned)
      - pattern_id: e.g. "WP01"
      - pattern_family: e.g. "impact/effect frame"
      - excerpt: the user excerpt (up to 200 chars)
      - message: the formatted advisory markdown
      - matches: list of all matches found

    Trigger conditions (all must hold):
      1. user_utterance is non-empty
      2. utterance contains an RQ-like candidate sentence
      3. at least one wording pattern matches with high confidence
      4. utterance does NOT contain domain-native vocabulary markers
      5. advisory has not already fired for the same pattern in this dialogue
         (checked via history; one advisory per pattern per session)
    """
    if not user_utterance or not user_utterance.strip():
        return None

    # Extract RQ candidates first — advisory is only about RQ phrasing
    candidates = extract_rq_candidates(user_utterance)
    if not candidates:
        return None

    # Combine candidates for matching
    candidate_text = " ".join(candidates)

    # Domain-native vocabulary suppresses the advisory
    if has_domain_native_vocabulary(candidate_text):
        return None

    # Match wording patterns
    matches = match_wording_patterns(candidate_text, require_high_confidence=True)
    if not matches:
        return None

    # Check history: don't repeat-fire the same pattern in one session
    if history:
        fired_patterns = {
            entry.get("wording_pattern_id")
            for entry in history
            if entry.get("role") == "advisory" and entry.get("wording_pattern_id")
        }
        new_matches = [m for m in matches if m["id"] not in fired_patterns]
        if not new_matches:
            return None
        matches = new_matches

    # Pick the first (highest-priority) match
    primary = matches[0]
    message = (
        f"[WORDING_PATTERN_ADVISORY]\n"
        f"Your phrasing \"{primary['excerpt']}\" resembles a common AI-typical "
        f"research-question shell: {primary['family']} ({primary['id']}). "
        f"I am not judging the idea; I am only flagging the wording. "
        f"What term, mechanism, site, or tension would a specialist in your "
        f"field use instead?"
    )
    return {
        "triggered": True,
        "pattern_id": primary["id"],
        "pattern_family": primary["family"],
        "excerpt": primary["excerpt"],
        "message": message,
        "matches": matches,
    }


def advisory_to_history_entry(advisory: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a triggered advisory into a history entry for persistence."""
    return {
        "role": "advisory",
        "content": advisory["message"],
        "wording_pattern_id": advisory["pattern_id"],
        "wording_pattern_family": advisory["pattern_family"],
    }
