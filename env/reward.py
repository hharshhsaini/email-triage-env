"""
Reward calculation and shaping logic for the Email Triage Environment.
"""

from typing import Dict, List, Any
from env.models import Action, AgentAction, EmailWithContext, Reward, EmailPriority
from env.tasks import TaskGrader


class RewardFunction:
    """
    Rich reward function applying partial progress, shaping, penalties, 
    and bonuses over the base task grader logic.
    """

    def __init__(self, task_config: Any):
        # Allow passing the dataclass or dict
        self.task_config = task_config
        self.action_history: Dict[str, List[AgentAction]] = {}
        
        # Additional state for consistency checks
        self.assigned_priorities: Dict[str, EmailPriority] = {}
        self.num_skips = 0

    def compute_step_reward(
        self,
        action: Action,
        email: EmailWithContext,
        ground_truth: Dict[str, Any],
        step: int,
        max_steps: int,
        grader: TaskGrader
    ) -> Reward:
        """
        Compute reward for a single step.
        Returns Reward model with all components filled.
        """
        # Base reward from the specialized grader
        base_reward: Reward = grader.step_reward(action, email, ground_truth)
        
        total = base_reward.total
        explanation = base_reward.explanation
        correctness = base_reward.correctness or 0.0
        efficiency = base_reward.efficiency or 0.0
        quality = base_reward.quality or 0.0
        penalty = base_reward.penalty or 0.0

        # State tracking setup
        if email.id not in self.action_history:
            self.action_history[email.id] = []
        
        # ----------------------------------------------------
        # 3. BEHAVIORAL PENALTIES
        # ----------------------------------------------------
        
        # Loop detection
        if self.detect_loop(email.id, action.action_type):
            total -= 0.5
            penalty -= 0.5
            explanation += " [Penalty: Loop detected]"
            
        self.action_history[email.id].append(action.action_type)

        # Skips
        if action.action_type == AgentAction.SKIP:
            self.num_skips += 1
            if self.num_skips > 2:
                total -= 0.1
                penalty -= 0.1
                explanation += " [Penalty: Excessive skipping]"

        # Wasted action (DRAFT_REPLY when unneeded)
        gt_email = ground_truth.get(email.id, {})
        # Not all tasks mandate replies. If "reply_needed" exists and is false, or doesn't exist and task doesn't use it.
        # However, for safety, if reply_needed is explicitly False, penalize. 
        if action.action_type == AgentAction.DRAFT_REPLY:
            if "reply_needed" in gt_email and not gt_email["reply_needed"]:
                total -= 0.02
                penalty -= 0.02
                explanation += " [Penalty: Wasted draft]"

        # ----------------------------------------------------
        # 5. CONSISTENCY REWARD
        # ----------------------------------------------------
        
        if action.action_type == AgentAction.SET_PRIORITY and action.priority:
            self.assigned_priorities[email.id] = action.priority
            
        current_priority = self.assigned_priorities.get(email.id)

        # Consistency: Urgent + Escalate
        if action.action_type == AgentAction.ESCALATE and current_priority == EmailPriority.URGENT:
            total += 0.03
            correctness += 0.03
            explanation += " [Bonus: Consistent escalation]"

        # Inconsistency: Low + Draft Reply
        if action.action_type == AgentAction.DRAFT_REPLY and current_priority == EmailPriority.LOW:
            total -= 0.02
            penalty -= 0.02
            explanation += " [Penalty: Inconsistent reply to LOW priority]"
            
        # Optional: efficiency bonus applied at step-level is tricky. 
        # Typically handled outside if the episode ends, but we can return it.
        
        return Reward(
            total=round(total, 3),
            correctness=round(correctness, 3),
            efficiency=round(efficiency, 3),
            quality=round(quality, 3),
            penalty=round(penalty, 3),
            explanation=explanation
        )

    def detect_loop(self, email_id: str, action: AgentAction) -> bool:
        """Return True if agent is stuck in a loop on this email."""
        actions = self.action_history.get(email_id, [])
        # If the same action has been taken >3 times already (4 or more occurrences of THIS action)
        count = sum(1 for a in actions if a == action)
        return count >= 3

    def efficiency_bonus(self, step: int, max_steps: int, emails_processed: int) -> float:
        """Bonus for completing task efficiently."""
        if emails_processed == 0:
            return 0.0
            
        # Target efficiency: 0.6 * max_steps
        target_steps = 0.6 * max_steps
        
        # If we completed or made good progress efficiently
        if step <= target_steps:
            return 0.05
            
        return 0.0  # Optional continuous shaping could be added here
