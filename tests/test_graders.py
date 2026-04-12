"""
Tests for task graders and standalone grade functions.

Covers:
  - PriorityTriageGrader, SmartCategorizationGrader, ExecutiveAssistantGrader
  - Standalone env.graders module (what the OpenEnv validator imports)
  - RewardFunction loop detection
"""

import pytest
from env.tasks import PriorityTriageGrader, SmartCategorizationGrader, ExecutiveAssistantGrader
from env.graders import grade_priority_triage, grade_smart_categorization, grade_executive_assistant
from env.reward import RewardFunction
from env.models import Action, AgentAction, EmailPriority, EmailCategory, EmailWithContext, Reward


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_mock_email(uid="1", subj="URGENT test", sender="boss@company.com", body="test"):
    return EmailWithContext(
        id=uid,
        subject=subj,
        sender=sender,
        sender_domain="company.com",
        recipient="me@company.com",
        body=body,
        timestamp="2024-01-01T12:00:00Z",
        thread_id="123",
        has_attachments=False,
        attachment_names=[],
        cc=[],
        inbox_position=0,
        thread_length=1,
        sender_history=0,
        is_vip_sender=True,
    )


# ---------------------------------------------------------------------------
# PriorityTriageGrader
# ---------------------------------------------------------------------------

def test_priority_grader_perfect_score():
    grader = PriorityTriageGrader()
    e = build_mock_email()  # sender=boss@company.com → URGENT
    gt = grader.generate_ground_truth([e])
    true_priority = gt[e.id]["priority"].value
    processed = [{"email_id": e.id, "action_type": "set_priority", "priority_set": true_priority, "category_set": None}]
    grade = grader.grade_episode(processed, gt, [e])
    # Grader caps at 0.99 to avoid exact 1.0 — check ≥ 0.9
    assert grade >= 0.9, f"Expected perfect score ≥0.9, got {grade}"


def test_priority_grader_partial_credit():
    grader = PriorityTriageGrader()
    e = build_mock_email()  # boss@ → URGENT ground truth
    gt = grader.generate_ground_truth([e])
    # Give HIGH instead of URGENT (off by 1 tier → 0.5)
    processed = [{"email_id": e.id, "action_type": "set_priority", "priority_set": EmailPriority.HIGH.value, "category_set": None}]
    grade = grader.grade_episode(processed, gt, [e])
    assert grade == 0.5, f"Expected 0.5 partial credit, got {grade}"


def test_priority_grader_all_wrong():
    grader = PriorityTriageGrader()
    e = build_mock_email()  # boss@ → URGENT
    gt = grader.generate_ground_truth([e])
    # Give LOW (distance=3 → score 0.01)
    processed = [{"email_id": e.id, "action_type": "set_priority", "priority_set": EmailPriority.LOW.value, "category_set": None}]
    grade = grader.grade_episode(processed, gt, [e])
    # Grader returns 0.01 (small non-zero) for completely wrong answer
    assert grade <= 0.1, f"Expected near-zero score, got {grade}"


def test_priority_grader_no_action():
    """Missing action gets minimum non-zero score."""
    grader = PriorityTriageGrader()
    e = build_mock_email()
    gt = grader.generate_ground_truth([e])
    grade = grader.grade_episode([], gt, [e])
    assert 0.0 <= grade <= 0.1


# ---------------------------------------------------------------------------
# SmartCategorizationGrader
# ---------------------------------------------------------------------------

def test_categorization_grader_both_actions_correct():
    grader = SmartCategorizationGrader()
    e = build_mock_email(subj="invoice overdue", sender="vendor@external.com", body="Please process invoice")
    gt = grader.generate_ground_truth([e])
    processed = [
        {"email_id": e.id, "action_type": "set_priority", "priority_set": gt[e.id]["priority"].value, "category_set": None},
        {"email_id": e.id, "action_type": "categorize", "category_set": gt[e.id]["category"].value, "priority_set": None},
    ]
    grade = grader.grade_episode(processed, gt, [e])
    assert grade > 0.9, f"Expected score >0.9 for both correct actions, got {grade}"


def test_categorization_grader_only_priority():
    grader = SmartCategorizationGrader()
    e = build_mock_email()
    gt = grader.generate_ground_truth([e])
    processed = [{"email_id": e.id, "action_type": "set_priority", "priority_set": gt[e.id]["priority"].value, "category_set": None}]
    grade = grader.grade_episode(processed, gt, [e])
    # Missing category → score < perfect
    assert grade < 0.9, f"Expected incomplete score, got {grade}"
    assert grade > 0.0


def test_categorization_grader_missing_action_penalty():
    """No actions → minimum score."""
    grader = SmartCategorizationGrader()
    e = build_mock_email()
    gt = grader.generate_ground_truth([e])
    grade = grader.grade_episode([], gt, [e])
    assert grade <= 0.1


# ---------------------------------------------------------------------------
# ExecutiveAssistantGrader
# ---------------------------------------------------------------------------

def test_executive_grader_reply_quality():
    grader = ExecutiveAssistantGrader()
    e = build_mock_email(subj="[REPLY_NEEDED] Please review the proposal")
    gt = grader.generate_ground_truth([e])
    processed = [{
        "email_id": e.id,
        "action_type": "draft_reply",
        "priority_set": None,
        "category_set": None,
        "reply_draft": "I have reviewed the proposal and will follow up with my detailed comments by EOD.",
        "is_vip_sender": True,
    }]
    grade = grader.grade_episode(processed, gt, [e])
    assert grade > 0.1, f"Expected reply credit >0.1, got {grade}"


def test_executive_grader_vip_archive_penalty():
    grader = ExecutiveAssistantGrader()
    e = build_mock_email(subj="Newsletter")
    e.is_vip_sender = True
    gt = grader.generate_ground_truth([e])
    processed = [{"email_id": e.id, "action_type": "archive", "priority_set": None, "category_set": None, "is_vip_sender": True}]
    grade = grader.grade_episode(processed, gt, [e])
    # VIP archive applies hygiene penalty
    assert grade < 1.0, f"Expected score <1.0 due to VIP archive penalty, got {grade}"


def test_executive_grader_escalation_correct():
    grader = ExecutiveAssistantGrader()
    e = build_mock_email(subj="legal compliance audit required", body="We have a compliance audit.")
    gt = grader.generate_ground_truth([e])
    # Legal email should be escalated
    assert gt[e.id]["is_legal"] is True
    processed = [{"email_id": e.id, "action_type": "escalate", "priority_set": None, "category_set": None, "is_vip_sender": False}]
    grade = grader.grade_episode(processed, gt, [e])
    assert grade > 0.1


# ---------------------------------------------------------------------------
# Standalone grader functions (what openenv validate imports)
# ---------------------------------------------------------------------------

def test_standalone_grade_priority_triage_dry_run():
    """Dry-run with no state returns a valid 0.5 score."""
    score = grade_priority_triage(None)
    assert score == 0.5

def test_standalone_grade_priority_triage_empty_dict():
    score = grade_priority_triage({})
    assert score == 0.5

def test_standalone_grade_priority_triage_with_state():
    """Real episode state produces score in [0, 1]."""
    from env.email_generator import EmailGenerator
    gen = EmailGenerator(seed=42)
    inbox, _ = gen.generate_inbox(n_emails=5, task_config={})
    grader = PriorityTriageGrader()
    gt = grader.generate_ground_truth(inbox)
    processed = [
        {"email_id": e.id, "action_type": "set_priority", "priority_set": gt[e.id]["priority"].value, "category_set": None}
        for e in inbox
    ]
    score = grade_priority_triage({
        "processed": processed,
        "inbox": [e.model_dump() for e in inbox],
        "ground_truth": {k: {"priority": v["priority"]} for k, v in gt.items()},
    })
    assert 0.0 <= score <= 1.0, f"Score out of range: {score}"
    assert score > 0.5  # Perfect actions should score well


def test_standalone_grade_smart_categorization_dry_run():
    score = grade_smart_categorization(None)
    assert score == 0.5


def test_standalone_grade_executive_assistant_dry_run():
    score = grade_executive_assistant(None)
    assert score == 0.5


def test_all_standalone_graders_return_valid_range():
    """All three standalone graders return float in [0, 1] for dry-run."""
    for fn in [grade_priority_triage, grade_smart_categorization, grade_executive_assistant]:
        score = fn(None)
        assert isinstance(score, float), f"{fn.__name__} did not return float"
        assert 0.0 <= score <= 1.0, f"{fn.__name__} returned out-of-range: {score}"


# ---------------------------------------------------------------------------
# Grader determinism
# ---------------------------------------------------------------------------

def test_graders_deterministic():
    grader1 = PriorityTriageGrader()
    grader2 = PriorityTriageGrader()
    e = build_mock_email()
    gt1 = grader1.generate_ground_truth([e])
    gt2 = grader2.generate_ground_truth([e])
    assert gt1 == gt2


def test_standalone_graders_deterministic():
    """Same episode state always produces same score."""
    score_a = grade_priority_triage(None)
    score_b = grade_priority_triage(None)
    assert score_a == score_b


# ---------------------------------------------------------------------------
# RewardFunction – loop detection
# ---------------------------------------------------------------------------

def test_loop_detection_triggers_penalty():
    reward_fn = RewardFunction(task_config=None)
    grader = PriorityTriageGrader()
    e = build_mock_email()
    gt = grader.generate_ground_truth([e])
    action = Action(email_id=e.id, action_type=AgentAction.SKIP)

    # 4 identical actions on same email → loop penalty
    reward_fn.compute_step_reward(action, e, gt, 1, 10, grader)
    reward_fn.compute_step_reward(action, e, gt, 2, 10, grader)
    reward_fn.compute_step_reward(action, e, gt, 3, 10, grader)
    res = reward_fn.compute_step_reward(action, e, gt, 4, 10, grader)

    assert res.total < -0.4, f"Expected loop penalty < -0.4, got {res.total}"
