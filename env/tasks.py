"""
Task definitions and graders for the Email Triage Agent Environment.

Implements the three core tasks: priority_triage, smart_categorization,
and executive_assistant. Each has its own ground truth generator, 
step reward logic, and episode grader.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import re

from env.models import (
    Action,
    AgentAction,
    EmailCategory,
    EmailPriority,
    EmailWithContext,
    Reward,
)

# ---------------------------------------------------------------------------
# Base Interfaces
# ---------------------------------------------------------------------------

@dataclass
class TaskConfig:
    """Configuration for a specific evaluation task."""
    task_id: str
    description: str
    n_emails: int
    max_steps: int
    difficulty: str
    grader_class: type  # The TaskGrader implementation
    generator_config: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)


class TaskGrader(ABC):
    """Abstract base class for all task graders."""

    @abstractmethod
    def generate_ground_truth(self, inbox: List[EmailWithContext]) -> Dict[str, Any]:
        """Generate the correct answers for this inbox."""
        pass

    @abstractmethod
    def grade_episode(
        self,
        processed: List[Dict[str, Any]],  # log of {email, action, reward}
        ground_truth: Dict[str, Any],
        inbox: List[EmailWithContext]
    ) -> float:
        """Final episode grade 0.0-1.0"""
        pass

    @abstractmethod
    def step_reward(
        self,
        action: Action,
        email: EmailWithContext,
        ground_truth: Dict[str, Any]
    ) -> Reward:
        """Per-step reward signal"""
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PRIORITY_TIERS = {
    EmailPriority.URGENT: 4,
    EmailPriority.HIGH: 3,
    EmailPriority.NORMAL: 2,
    EmailPriority.LOW: 1,
    EmailPriority.SPAM: 0,
}

def _priority_distance(pred: EmailPriority, true: EmailPriority) -> int:
    """Priority tier difference. If either is spam and they don't match, distance is large."""
    if pred == true:
        return 0
    if pred == EmailPriority.SPAM or true == EmailPriority.SPAM:
        return 99 # Spam mismatch is completely wrong
    return abs(PRIORITY_TIERS[pred] - PRIORITY_TIERS[true])

def _base_priority_rules(email: EmailWithContext) -> EmailPriority:
    """Shared priority rules for Task 1 and 2."""
    subject = email.subject.lower()
    sender = email.sender.lower()

    if "boss@" in sender or "ceo@" in sender or "cto@" in sender:
        return EmailPriority.URGENT if "urgent" in subject else EmailPriority.HIGH
    
    if any(k in subject for k in ["urgent", "critical", "down", "outage"]):
        return EmailPriority.URGENT
    
    if any(k in subject for k in ["invoice", "payment", "overdue"]):
        return EmailPriority.HIGH
        
    if "invite" in subject or "meeting" in subject:
        return EmailPriority.NORMAL
        
    if "noreply" in sender or "newsletter" in subject.lower():
        return EmailPriority.LOW
        
    if any(k in subject for k in ["prize", "offer", "guarantee", "seo", "$1,000,000"]):
        return EmailPriority.SPAM
        
    return EmailPriority.NORMAL


# ---------------------------------------------------------------------------
# Task 1: Priority Triage (EASY)
# ---------------------------------------------------------------------------

class PriorityTriageGrader(TaskGrader):
    def generate_ground_truth(self, inbox: List[EmailWithContext]) -> Dict[str, Any]:
        gt = {}
        for email in inbox:
            gt[email.id] = {"priority": _base_priority_rules(email)}
        return gt

    def grade_episode(self, processed: List[Dict], ground_truth: Dict, inbox: List[EmailWithContext]) -> float:
        if not inbox: return 0.0
        
        # We need the final SET_PRIORITY action per email
        email_to_pred = {}
        for p in processed:
            if p["action_type"] == AgentAction.SET_PRIORITY.value and p["priority_set"]:
                email_to_pred[p["email_id"]] = EmailPriority(p["priority_set"])
                
        scores = []
        for email in inbox:
            pred = email_to_pred.get(email.id)
            true = ground_truth[email.id]["priority"]
            
            if not pred:
                scores.append(0.0)
                continue
                
            dist = _priority_distance(pred, true)
            if dist == 0:
                scores.append(1.0)
            elif dist == 1:
                scores.append(0.5)
            else:
                scores.append(0.0)
                
        return sum(scores) / len(scores)

    def step_reward(self, action: Action, email: EmailWithContext, ground_truth: Dict) -> Reward:
        if action.action_type != AgentAction.SET_PRIORITY:
            return Reward(total=-0.0, explanation="Should use SET_PRIORITY")
            
        true_prio = ground_truth[email.id]["priority"]
        if not action.priority:
            return Reward(total=-0.05, explanation="Missing priority value")
            
        dist = _priority_distance(action.priority, true_prio)
        if dist == 0:
            return Reward(total=0.1, correctness=1.0, quality=1.0, explanation="Correct priority")
        elif dist == 1:
            return Reward(total=0.0, correctness=0.5, quality=0.5, explanation="Off by one tier")
        else:
            return Reward(total=-0.1, correctness=0.0, penalty=-0.1, explanation="Major prioritization error")


# ---------------------------------------------------------------------------
# Task 2: Smart Categorization (MEDIUM)
# ---------------------------------------------------------------------------

def _base_category_rules(email: EmailWithContext) -> EmailCategory:
    subject = email.subject.lower()
    sender = email.sender.lower()
    
    if any(k in subject for k in ["invoice", "payment", "billing", "receipt"]):
        return EmailCategory.BILLING
    if "hr@" in sender or any(k in subject for k in ["benefits", "pto", "payroll", "policy"]):
        return EmailCategory.HR
    if not sender.endswith("company.com") and any(k in subject for k in ["account", "support", "ticket", "issue"]):
        return EmailCategory.CUSTOMER
    if any(k in subject for k in ["meeting", "invite", "scheduling", "calendar"]):
        return EmailCategory.MEETING
    if "deadline" in subject or "action required" in subject:
        return EmailCategory.ACTION_REQUIRED
    if "fwd:" in subject or "cc'd" in subject or "fyi" in subject:
        return EmailCategory.FYI
    if "unsubscribe" in email.body.lower() or "noreply" in sender:
        return EmailCategory.NEWSLETTER
    if _base_priority_rules(email) == EmailPriority.SPAM:
        return EmailCategory.SPAM
        
    return EmailCategory.INTERNAL

class SmartCategorizationGrader(TaskGrader):
    def generate_ground_truth(self, inbox: List[EmailWithContext]) -> Dict[str, Any]:
        gt = {}
        for email in inbox:
            gt[email.id] = {
                "priority": _base_priority_rules(email),
                "category": _base_category_rules(email)
            }
        return gt

    def grade_episode(self, processed: List[Dict], ground_truth: Dict, inbox: List[EmailWithContext]) -> float:
        if not inbox: return 0.0
        
        # Track both actions per email
        email_actions = {}
        for p in processed:
            eid = p["email_id"]
            if eid not in email_actions:
                email_actions[eid] = {"priority": None, "category": None}
            if p["action_type"] == AgentAction.SET_PRIORITY.value:
                email_actions[eid]["priority"] = EmailPriority(p["priority_set"]) if p["priority_set"] else None
            elif p["action_type"] == AgentAction.CATEGORIZE.value:
                email_actions[eid]["category"] = EmailCategory(p["category_set"]) if p["category_set"] else None
                
        scores = []
        all_complete = True
        
        for email in inbox:
            state = email_actions.get(email.id, {"priority": None, "category": None})
            true_prio = ground_truth[email.id]["priority"]
            true_cat = ground_truth[email.id]["category"]
            
            email_score = 0.0
            
            # Priority (0.4 weight)
            if state["priority"]:
                if state["priority"] == true_prio:
                    email_score += 0.4
                elif _priority_distance(state["priority"], true_prio) == 1:
                    email_score += 0.2
            else:
                all_complete = False
                
            # Category (0.6 weight)
            if state["category"]:
                if state["category"] == true_cat:
                    email_score += 0.6
            else:
                all_complete = False
                
            scores.append(email_score)
            
        final = sum(scores) / len(scores)
        if all_complete:
            final = min(1.0, final + 0.05)
            
        return final

    def step_reward(self, action: Action, email: EmailWithContext, ground_truth: Dict) -> Reward:
        if action.action_type == AgentAction.SKIP:
            return Reward(total=-0.02, penalty=-0.02, explanation="Skip penalised")
            
        if action.action_type == AgentAction.SET_PRIORITY and action.priority:
            true_prio = ground_truth[email.id]["priority"]
            dist = _priority_distance(action.priority, true_prio)
            if dist == 0: return Reward(total=0.08, correctness=0.8, explanation="Correct priority")
            if dist == 1: return Reward(total=0.03, correctness=0.3, explanation="Partial priority credit")
            return Reward(total=-0.05, penalty=-0.05, explanation="Wrong priority")
            
        if action.action_type == AgentAction.CATEGORIZE and action.category:
            true_cat = ground_truth[email.id]["category"]
            if action.category == true_cat:
                return Reward(total=0.08, correctness=0.8, explanation="Correct category")
            return Reward(total=-0.05, penalty=-0.05, explanation="Wrong category")
            
        return Reward(total=0.0, explanation="Action not evaluated")


# ---------------------------------------------------------------------------
# Task 3: Executive Assistant (HARD)
# ---------------------------------------------------------------------------

class ExecutiveAssistantGrader(TaskGrader):
    def generate_ground_truth(self, inbox: List[EmailWithContext]) -> Dict[str, Any]:
        # Sort inbox by natural urgency to pick top 5
        scored_emails = []
        for i, email in enumerate(inbox):
            score = 0
            subject = email.subject.lower()
            if "boss@" in email.sender or "ceo@" in email.sender: score += 10
            if "urgent" in subject or "critical" in subject: score += 8
            if email.is_vip_sender: score += 5
            if "[REPLY_NEEDED]" in subject: score += 6
            if "legal" in subject or "compliance" in subject or "security" in subject: score += 7
            scored_emails.append((score, email))
            
        scored_emails.sort(key=lambda x: x[0], reverse=True)
        top_5_ids = {e.id for _, e in scored_emails[:5]}
        
        gt = {}
        for email in inbox:
            subject = email.subject.lower()
            body = email.body.lower()
            
            is_priority = email.id in top_5_ids
            reply_needed = "[reply_needed]" in subject or "[reply needed]" in subject or "reply needed" in body
            is_legal = any(k in subject or k in body for k in ["legal", "compliance", "security", "breach", "audit"])
            is_spam_nl = _base_priority_rules(email) in (EmailPriority.SPAM, EmailPriority.LOW)
            
            # Keywords extraction for reply grading
            keywords = []
            if reply_needed:
                words = [w for w in subject.split() if len(w) > 4 and "reply" not in w]
                keywords = set(words[:3]) or {"received", "review"}
            
            gt[email.id] = {
                "must_prioritize": is_priority,
                "reply_needed": reply_needed,
                "reply_keywords": keywords,
                "is_legal": is_legal,
                "is_spam_nl": is_spam_nl,
            }
        return gt

    def grade_episode(self, processed: List[Dict], ground_truth: Dict, inbox: List[EmailWithContext]) -> float:
        pred_prio = set()
        pred_replies = {}
        pred_escalate = set()
        pred_archived_spam = set()
        vip_mistakes = 0
        
        # Extract actions
        for p in processed:
            eid = p["email_id"]
            action = p["action_type"]
            is_vip = p["is_vip_sender"]
            
            if action == AgentAction.SET_PRIORITY.value and p["priority_set"] in ("urgent", "high"):
                pred_prio.add(eid)
            if action == AgentAction.DRAFT_REPLY.value and p.get("reply_draft"):
                pred_replies[eid] = p["reply_draft"]
            if action == AgentAction.ESCALATE.value:
                pred_escalate.add(eid)
            if action in (AgentAction.ARCHIVE.value, AgentAction.MARK_SPAM.value):
                pred_archived_spam.add(eid)
                if is_vip: vip_mistakes += 1
                
        # 1. Prioritization Focus (30%)
        true_prio = {eid for eid, gt in ground_truth.items() if gt["must_prioritize"]}
        tp_prio = len(pred_prio & true_prio)
        fp_prio = len(pred_prio - true_prio)
        fn_prio = len(true_prio - pred_prio)
        f1_prio = (tp_prio) / (tp_prio + 0.5 * (fp_prio + fn_prio)) if true_prio else 1.0
        
        # 2. Reply quality (40%)
        true_replies = [eid for eid, gt in ground_truth.items() if gt["reply_needed"]]
        reply_score = 0.0
        for eid in true_replies:
            draft = pred_replies.get(eid, "")
            if not draft: continue
            
            part = 0.2 # Created
            kw = ground_truth[eid]["reply_keywords"]
            if any(k in draft.lower() for k in kw): part += 0.4
            
            length = len(draft)
            if 50 <= length <= 500: part += 0.1
            
            # Appropriate content
            if "lorem ipsum" not in draft.lower() and length > 20: part += 0.3
            
            reply_score += part
            
        avg_reply = reply_score / max(1, len(true_replies))
        
        # 3. Escalation accuracy (20%)
        true_esc = {eid for eid, gt in ground_truth.items() if gt["is_legal"]}
        tp_esc = len(pred_escalate & true_esc)
        fp_esc = len(pred_escalate - true_esc)
        fn_esc = len(true_esc - pred_escalate)
        if len(true_esc) == 0 and len(pred_escalate) == 0:
            f1_esc = 1.0
        else:
            f1_esc = (tp_esc) / (tp_esc + 0.5 * (fp_esc + fn_esc)) if (tp_esc + fp_esc + fn_esc) > 0 else 1.0
            
        # 4. Inbox hygiene (10%)
        true_spam = {eid for eid, gt in ground_truth.items() if gt["is_spam_nl"]}
        tp_spam = len(pred_archived_spam & true_spam)
        hygiene = tp_spam / len(true_spam) if true_spam else 1.0
        if vip_mistakes > 0: hygiene -= 0.1
        
        return 0.3 * f1_prio + 0.4 * avg_reply + 0.2 * f1_esc + 0.1 * hygiene

    def step_reward(self, action: Action, email: EmailWithContext, ground_truth: Dict) -> Reward:
        gt = ground_truth[email.id]
        atype = action.action_type
        
        # VIP penalty
        if email.is_vip_sender and atype in (AgentAction.ARCHIVE, AgentAction.MARK_SPAM):
            return Reward(total=-0.25, penalty=-0.25, explanation="VIP email archived/spammed")
            
        if atype == AgentAction.SET_PRIORITY and action.priority in (EmailPriority.URGENT, EmailPriority.HIGH):
            if gt["must_prioritize"]: return Reward(total=0.05, correctness=0.8, explanation="Correct high priority")
            else: return Reward(total=0.0, explanation="High priority on wrong email")
            
        if atype == AgentAction.DRAFT_REPLY and action.reply_draft:
            if not gt["reply_needed"]:
                return Reward(total=-0.05, penalty=-0.05, explanation="Drafting reply for wrong email")
            
            draft = action.reply_draft
            if len(draft) < 20: 
                return Reward(total=-0.08, penalty=-0.08, explanation="Empty or generic reply")
                
            has_kw = any(k in draft.lower() for k in gt["reply_keywords"])
            if has_kw and (50 <= len(draft) <= 500):
                return Reward(total=0.15, quality=0.9, explanation="Good reply draft")
            else:
                return Reward(total=0.05, quality=0.4, explanation="Average reply draft")
                
        if atype == AgentAction.ESCALATE:
            if gt["is_legal"]: return Reward(total=0.10, correctness=0.9, explanation="Correct escalation")
            else: return Reward(total=-0.05, explanation="False escalation")
            
        if atype in (AgentAction.ARCHIVE, AgentAction.MARK_SPAM):
            if gt["is_spam_nl"]: return Reward(total=0.03, correctness=0.5, explanation="Correct archive/spam")
            else: return Reward(total=-0.05, explanation="Wrongly archived")
            
        return Reward(total=0.0, explanation="Neutral action")

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

TASK_REGISTRY: Dict[str, TaskConfig] = {
    "priority_triage": TaskConfig(
        task_id="priority_triage",
        description="EASY: Sort a 10-email inbox by priority using SET_PRIORITY actions.",
        n_emails=10,
        max_steps=15,
        difficulty="easy",
        grader_class=PriorityTriageGrader,
        generator_config={"urgency_level": 0.5},
    ),
    "smart_categorization": TaskConfig(
        task_id="smart_categorization",
        description="MEDIUM: Correctly categorize 15 emails AND set priority, using both CATEGORIZE and SET_PRIORITY on each email.",
        n_emails=15,
        max_steps=35,
        difficulty="medium",
        grader_class=SmartCategorizationGrader,
        generator_config={"urgency_level": 0.5, "email_types": {"billing": 0.15, "hr": 0.15, "customer": 0.2}},
    ),
    "executive_assistant": TaskConfig(
        task_id="executive_assistant",
        description="HARD: Act as an executive assistant. Prioritize, draft replies, escalate compliance issues, and archive noise.",
        n_emails=20,
        max_steps=50,
        difficulty="hard",
        grader_class=ExecutiveAssistantGrader,
        generator_config={
            "include_vip_senders": ["ceo@company.com", "chairman@boardroom.com"],
            "domain": "company.com"
        },
        context={
            "executive_name": "Alex Chen, VP of Engineering",
            "company_context": "B2B SaaS startup, 150 employees",
            "tone_guidelines": "professional but warm, concise",
        }
    )
}

def get_task(task_id: str) -> TaskConfig:
    if task_id not in TASK_REGISTRY:
        raise KeyError(f"Unknown task {task_id}")
    return TASK_REGISTRY[task_id]
