"""
Standalone grader functions for the Email Triage OpenEnv.

Each function is importable as ``env.graders:grade_<task_id>`` and called by
the OpenEnv validator to confirm that graded tasks exist and produce valid
0.0-1.0 scores.

The validator passes a dict with the episode trajectory; if the dict is empty
or missing (dry-run), we still return a valid float so that schema checks pass.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from env.tasks import (
    PriorityTriageGrader,
    SmartCategorizationGrader,
    ExecutiveAssistantGrader,
)
from env.email_generator import EmailGenerator


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _make_empty_inbox(n: int = 5, seed: int = 0) -> list:
    """Return a small synthetic inbox used when no real episode state given."""
    gen = EmailGenerator(seed=seed)
    inbox, _ = gen.generate_inbox(n_emails=n, task_config={})
    return inbox


def _extract_processed(episode_state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Pull the processed-actions list from a variety of payload shapes."""
    if not episode_state:
        return []
    # Direct key
    for key in ("processed", "actions", "trajectory", "history"):
        if key in episode_state and isinstance(episode_state[key], list):
            return episode_state[key]
    return []


# ---------------------------------------------------------------------------
# Task 1  –  Priority Triage  (EASY)
# ---------------------------------------------------------------------------

def grade_priority_triage(episode_state: Optional[Dict[str, Any]] = None) -> float:
    """
    Grade a priority_triage episode.

    Args:
        episode_state: dict containing at minimum ``processed`` (list of
            action dicts) and optionally ``inbox`` / ``ground_truth``.
            May be None or empty for dry-run validation (returns 0.5).

    Returns:
        float in [0.0, 1.0]
    """
    grader = PriorityTriageGrader()

    if not episode_state:
        # Dry-run: return mid-range score so validator sees a valid float
        return 0.5

    processed = _extract_processed(episode_state)
    inbox_raw = episode_state.get("inbox", [])

    # If the caller passed serialised EmailWithContext dicts, reconstruct them
    if inbox_raw and isinstance(inbox_raw[0], dict):
        from env.models import EmailWithContext
        inbox = [EmailWithContext(**e) for e in inbox_raw]
    elif inbox_raw:
        inbox = inbox_raw
    else:
        inbox = _make_empty_inbox(n=10)

    ground_truth = episode_state.get("ground_truth") or grader.generate_ground_truth(inbox)
    score = grader.grade_episode(processed, ground_truth, inbox)
    return float(round(min(1.0, max(0.0, score)), 4))


# ---------------------------------------------------------------------------
# Task 2  –  Smart Categorization  (MEDIUM)
# ---------------------------------------------------------------------------

def grade_smart_categorization(episode_state: Optional[Dict[str, Any]] = None) -> float:
    """
    Grade a smart_categorization episode.

    Args:
        episode_state: same shape as grade_priority_triage.

    Returns:
        float in [0.0, 1.0]
    """
    grader = SmartCategorizationGrader()

    if not episode_state:
        return 0.5

    processed = _extract_processed(episode_state)
    inbox_raw = episode_state.get("inbox", [])

    if inbox_raw and isinstance(inbox_raw[0], dict):
        from env.models import EmailWithContext
        inbox = [EmailWithContext(**e) for e in inbox_raw]
    elif inbox_raw:
        inbox = inbox_raw
    else:
        inbox = _make_empty_inbox(n=15)

    ground_truth = episode_state.get("ground_truth") or grader.generate_ground_truth(inbox)
    score = grader.grade_episode(processed, ground_truth, inbox)
    return float(round(min(1.0, max(0.0, score)), 4))


# ---------------------------------------------------------------------------
# Task 3  –  Executive Assistant  (HARD)
# ---------------------------------------------------------------------------

def grade_executive_assistant(episode_state: Optional[Dict[str, Any]] = None) -> float:
    """
    Grade an executive_assistant episode.

    Args:
        episode_state: same shape as grade_priority_triage.

    Returns:
        float in [0.0, 1.0]
    """
    grader = ExecutiveAssistantGrader()

    if not episode_state:
        return 0.5

    processed = _extract_processed(episode_state)
    inbox_raw = episode_state.get("inbox", [])

    if inbox_raw and isinstance(inbox_raw[0], dict):
        from env.models import EmailWithContext
        inbox = [EmailWithContext(**e) for e in inbox_raw]
    elif inbox_raw:
        inbox = inbox_raw
    else:
        inbox = _make_empty_inbox(n=20)

    ground_truth = episode_state.get("ground_truth") or grader.generate_ground_truth(inbox)
    score = grader.grade_episode(processed, ground_truth, inbox)
    return float(round(min(1.0, max(0.0, score)), 4))


# ---------------------------------------------------------------------------
# Convenience registry  (used by /grade endpoint)
# ---------------------------------------------------------------------------

GRADER_REGISTRY = {
    "priority_triage": grade_priority_triage,
    "smart_categorization": grade_smart_categorization,
    "executive_assistant": grade_executive_assistant,
}
