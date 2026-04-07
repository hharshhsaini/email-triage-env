"""
Pydantic typed models for the Email Triage Agent Environment.

These models define the full data contract between the environment
and the agent, including emails, actions, observations, and rewards.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class EmailPriority(str, Enum):
    """Priority levels that can be assigned to an email."""
    URGENT = "urgent"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    SPAM = "spam"


class EmailCategory(str, Enum):
    """Business categories for classifying emails."""
    ACTION_REQUIRED = "action_required"
    FYI = "fyi"
    MEETING = "meeting"
    BILLING = "billing"
    HR = "hr"
    CUSTOMER = "customer"
    INTERNAL = "internal"
    SPAM = "spam"
    NEWSLETTER = "newsletter"


class AgentAction(str, Enum):
    """All valid actions an agent can take on an email."""
    SET_PRIORITY = "set_priority"
    CATEGORIZE = "categorize"
    DRAFT_REPLY = "draft_reply"
    ESCALATE = "escalate"
    ARCHIVE = "archive"
    MARK_SPAM = "mark_spam"
    SNOOZE = "snooze"
    FLAG_FOR_REVIEW = "flag_for_review"
    SKIP = "skip"


class Email(BaseModel):
    """A single email in the inbox."""

    id: str = Field(..., description="Unique email identifier")
    subject: str = Field(..., description="Email subject line")
    sender: str = Field(..., description="Full email address of sender")
    sender_domain: str = Field(..., description="Domain portion of sender email")
    recipient: str = Field(..., description="Recipient email address")
    body: str = Field(..., description="Full email body text")
    timestamp: datetime = Field(..., description="When the email was received")
    thread_id: Optional[str] = Field(None, description="Thread ID for grouping replies")
    has_attachments: bool = Field(False, description="Whether email has file attachments")
    attachment_names: List[str] = Field(default_factory=list, description="Names of attached files")
    cc: List[str] = Field(default_factory=list, description="CC'd recipients")
    is_reply: bool = Field(False, description="Whether this email is a reply in a thread")
    original_email_id: Optional[str] = Field(None, description="ID of the original email if this is a reply")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary extra metadata")


class EmailWithContext(Email):
    """Email plus inbox context enriched for agent decision-making."""

    inbox_position: int = Field(..., description="Position in inbox (0 = newest)")
    thread_length: int = Field(1, description="How many emails are in this thread")
    sender_history: int = Field(0, description="How many prior emails from this sender")
    is_vip_sender: bool = Field(False, description="True if sender is in the VIP list")


class Action(BaseModel):
    """An action taken by the agent on an email."""

    email_id: str = Field(..., description="ID of email being acted upon")
    action_type: AgentAction = Field(..., description="Type of action to take")
    priority: Optional[EmailPriority] = Field(
        None, description="Priority to set (required for SET_PRIORITY)"
    )
    category: Optional[EmailCategory] = Field(
        None, description="Category to assign (required for CATEGORIZE)"
    )
    reply_draft: Optional[str] = Field(
        None, description="Draft reply text (required for DRAFT_REPLY)"
    )
    escalation_reason: Optional[str] = Field(
        None, description="Reason for escalation (required for ESCALATE)"
    )
    snooze_hours: Optional[int] = Field(
        None, description="Hours to snooze (required for SNOOZE)", ge=1, le=168
    )
    reasoning: Optional[str] = Field(
        None, description="Agent's reasoning for this action (for interpretability)"
    )


class Observation(BaseModel):
    """What the agent observes at each step of the episode."""

    current_email: Optional[EmailWithContext] = Field(
        None, description="The email currently requiring attention. None if inbox is empty."
    )
    inbox_summary: Dict[str, int] = Field(
        default_factory=dict,
        description="Summary counts: total, unread, urgent, by_category"
    )
    step_number: int = Field(..., description="Current step in the episode")
    emails_processed: int = Field(0, description="Emails handled so far this episode")
    emails_remaining: int = Field(..., description="Emails left to process")
    task_id: str = Field(..., description="Current task identifier")
    task_description: str = Field(..., description="Natural language task objective")
    available_actions: List[AgentAction] = Field(
        default_factory=list,
        description="Actions valid for the current email"
    )
    context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Task-specific context (e.g., VIP list, company info)"
    )
    episode_done: bool = Field(False, description="True if the episode has finished")


class Reward(BaseModel):
    """
    Reward signal with component breakdown for interpretability.

    Total reward is bounded in [-1.0, 1.0]. Individual components
    are summed and clipped to produce the final total.
    """

    total: float = Field(..., description="Total reward for this step", ge=-1.0, le=1.0)
    correctness: float = Field(0.0, description="Was the action correct?", ge=-1.0, le=1.0)
    efficiency: float = Field(0.0, description="Was the action efficient?", ge=0.0, le=1.0)
    quality: float = Field(0.0, description="Quality of reply/categorization", ge=0.0, le=1.0)
    penalty: float = Field(0.0, description="Penalties incurred", ge=-1.0, le=0.0)
    explanation: str = Field("", description="Human-readable reward explanation")


class StepResult(BaseModel):
    """Complete result returned from environment.step()."""

    observation: Observation = Field(..., description="New observation after the action")
    reward: Reward = Field(..., description="Reward signal for the action taken")
    done: bool = Field(..., description="Whether the episode is complete")
    info: Dict[str, Any] = Field(default_factory=dict, description="Auxiliary diagnostics")


class EpisodeState(BaseModel):
    """
    Full internal state of the environment (not directly exposed to agent).

    This is the ground-truth state used internally by the environment
    to compute rewards and track progress.
    """

    task_id: str = Field(..., description="Task identifier for this episode")
    step: int = Field(0, description="Current step count")
    max_steps: int = Field(..., description="Maximum steps before forced termination")
    inbox: List[EmailWithContext] = Field(default_factory=list, description="All emails in the inbox")
    processed: List[Dict[str, Any]] = Field(default_factory=list, description="Log of processed emails and actions")
    current_email_idx: int = Field(0, description="Index of the current email being processed")
    score: float = Field(0.0, description="Cumulative episode score")
    done: bool = Field(False, description="Whether the episode is complete")
    ground_truth: Dict[str, Any] = Field(default_factory=dict, description="Hidden correct labels for grading")
    episode_metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata about this episode")
