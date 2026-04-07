"""
Tests corresponding to Section 12 for graders.
"""

import pytest
from env.tasks import PriorityTriageGrader, SmartCategorizationGrader, ExecutiveAssistantGrader
from env.reward import RewardFunction
from env.models import Action, AgentAction, EmailPriority, EmailCategory, EmailWithContext, Reward
import random


def build_mock_email(uid="1", priority=EmailPriority.URGENT, subj="URGENT test"):
    e = EmailWithContext(
        id=uid,
        subject=subj,
        sender="boss@company.com",
        sender_domain="company.com",
        recipient="me@company.com",
        body="test",
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
    return e


def test_priority_grader_perfect_score():
    grader = PriorityTriageGrader()
    e = build_mock_email(priority=EmailPriority.URGENT)
    gt = grader.generate_ground_truth([e])
    processed = [{"email_id": e.id, "action_type": "set_priority", "priority_set": EmailPriority.URGENT.value, "category_set": None, "reward_given": 0}]
    grade = grader.grade_episode(processed, gt, [e])
    assert grade == 1.0


def test_priority_grader_partial_credit():
    grader = PriorityTriageGrader()
    e = build_mock_email(priority=EmailPriority.URGENT)
    gt = grader.generate_ground_truth([e])
    # Give it HIGH instead of URGENT
    processed = [{"email_id": e.id, "action_type": "set_priority", "priority_set": EmailPriority.HIGH.value, "category_set": None, "reward_given": 0}]
    grade = grader.grade_episode(processed, gt, [e])
    assert grade == 0.5


def test_priority_grader_all_wrong():
    grader = PriorityTriageGrader()
    e = build_mock_email(priority=EmailPriority.URGENT)
    gt = grader.generate_ground_truth([e])
    processed = [{"email_id": e.id, "action_type": "set_priority", "priority_set": EmailPriority.LOW.value, "category_set": None, "reward_given": 0}]
    grade = grader.grade_episode(processed, gt, [e])
    assert grade == 0.0


def test_categorization_grader_both_actions():
    grader = SmartCategorizationGrader()
    e = build_mock_email(subj="invoice overdue")
    gt = grader.generate_ground_truth([e])
    processed = [
        {"email_id": e.id, "action_type": "set_priority", "priority_set": gt[e.id]["priority"].value, "category_set": None, "reward_given": 0},
        {"email_id": e.id, "action_type": "categorize", "category_set": gt[e.id]["category"].value, "priority_set": None, "reward_given": 0}
    ]
    grade = grader.grade_episode(processed, gt, [e])
    assert grade > 0.9


def test_categorization_grader_missing_action_penalty():
    grader = SmartCategorizationGrader()
    e = build_mock_email()
    gt = grader.generate_ground_truth([e])
    processed = [{"email_id": e.id, "action_type": "set_priority", "priority_set": gt[e.id]["priority"].value, "category_set": None, "reward_given": 0}]
    grade1 = grader.grade_episode(processed, gt, [e])
    assert grade1 < 1.0


def test_executive_grader_reply_quality():
    grader = ExecutiveAssistantGrader()
    e = build_mock_email(subj="[REPLY_NEEDED] Please review")
    gt = grader.generate_ground_truth([e])
    # Provide a perfect reply matching guidelines and length tracking
    processed = [{"email_id": e.id, "action_type": "draft_reply", "priority_set": None, "category_set": None, "reply_draft": "I have received this document and will review it fully today.", "is_vip_sender": True}]
    grade = grader.grade_episode(processed, gt, [e])
    assert grade > 0.1 # Ensure it tracks reply credit properly


def test_executive_grader_vip_penalty():
    grader = ExecutiveAssistantGrader()
    e = build_mock_email(subj="Newsletter")
    e.is_vip_sender = True
    gt = grader.generate_ground_truth([e])
    processed = [{"email_id": e.id, "action_type": "archive", "priority_set": None, "category_set": None, "is_vip_sender": True}]
    grade = grader.grade_episode(processed, gt, [e])
    assert grade < 1.0 # Due to hygiene penalty


def test_graders_deterministic():
    grader1 = PriorityTriageGrader()
    grader2 = PriorityTriageGrader()
    e = build_mock_email()
    gt1 = grader1.generate_ground_truth([e])
    gt2 = grader2.generate_ground_truth([e])
    assert gt1 == gt2


def test_loop_detection_triggers_penalty():
    reward_fn = RewardFunction(task_config=None)
    grader = PriorityTriageGrader()
    e = build_mock_email()
    gt = grader.generate_ground_truth([e])
    action = Action(email_id=e.id, action_type=AgentAction.SKIP)
    
    # 4 identical actions (loop criteria)
    reward_fn.compute_step_reward(action, e, gt, 1, 10, grader)
    reward_fn.compute_step_reward(action, e, gt, 2, 10, grader)
    reward_fn.compute_step_reward(action, e, gt, 3, 10, grader)
    res = reward_fn.compute_step_reward(action, e, gt, 4, 10, grader)
    
    assert res.total < -0.4 # Loop penalty drops it heavily
