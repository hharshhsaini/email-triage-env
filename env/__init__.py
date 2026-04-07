"""
Email Triage Agent Environment Package.

A production-grade OpenEnv environment for training and evaluating
AI agents on enterprise email inbox management tasks.
"""
from env.models import (
    Email, EmailWithContext, Action, Observation, Reward,
    StepResult, EpisodeState, EmailPriority, EmailCategory, AgentAction
)
from env.environment import EmailTriageEnv
from env.email_generator import EmailGenerator
from env.tasks import TASK_REGISTRY, get_task
from env.reward import RewardFunction

__all__ = [
    "Email", "EmailWithContext", "Action", "Observation", "Reward",
    "StepResult", "EpisodeState", "EmailPriority", "EmailCategory", "AgentAction",
    "EmailTriageEnv", "EmailGenerator", "TASK_REGISTRY", "get_task",
    "RewardFunction",
]
