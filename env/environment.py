"""
Core OpenEnv environment class for the Email Triage Agent Environment.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from env.email_generator import EmailGenerator
from env.models import (
    Action,
    AgentAction,
    EpisodeState,
    Observation,
    Reward,
    StepResult,
    EmailWithContext,
)
from env.reward import RewardFunction
from env.tasks import TaskConfig, TASK_REGISTRY, TaskGrader


class EmailTriageEnv:
    """
    OpenEnv-compliant environment for email triage tasks.
    
    Implements the standard OpenEnv interface:
    - reset(task_id, seed) -> Observation
    - step(action) -> StepResult  
    - state() -> EpisodeState
    
    Three tasks available:
    - "priority_triage": Easy - set priorities on 10 emails
    - "smart_categorization": Medium - categorize + prioritize 15 emails
    - "executive_assistant": Hard - full EA workflow on 20 emails
    """

    TASKS = TASK_REGISTRY

    def __init__(self):
        self._state: Optional[EpisodeState] = None
        self._email_generator = EmailGenerator()
        self._reward_fn: Optional[RewardFunction] = None
        self._grader: Optional[TaskGrader] = None
        self._step_rewards: List[Reward] = []

    def reset(
        self,
        task_id: str = "priority_triage",
        seed: int = 42,
        n_emails: Optional[int] = None,
    ) -> Observation:
        """
        Reset the environment for a new episode.
        
        Args:
            task_id: Which task to run
            seed: Random seed for reproducibility
            n_emails: Optional override for inbox size
        
        Returns:
            Initial observation with first email in inbox
        
        Raises:
            ValueError: If task_id is not recognized
        """
        if task_id not in self.TASKS:
            raise ValueError(f"Unknown task {task_id}")

        task: TaskConfig = self.TASKS[task_id]
        self._grader = task.grader_class()
        self._reward_fn = RewardFunction(task_config=task)

        n = n_emails if n_emails is not None else task.n_emails
        self._email_generator = EmailGenerator(seed=seed)
        inbox, _ = self._email_generator.generate_inbox(
            n_emails=n,
            task_config=task.generator_config,
        )
        
        ground_truth = self._grader.generate_ground_truth(inbox)

        self._state = EpisodeState(
            task_id=task_id,
            step=0,
            max_steps=task.max_steps,
            inbox=inbox,
            processed=[],
            current_email_idx=0,
            score=0.0,
            done=False,
            ground_truth=ground_truth,
            episode_metadata={
                "seed": seed,
                "n_emails": n,
                "task_description": task.description,
            },
        )
        self._step_rewards = []

        return self._build_observation()

    def step(self, action: Action) -> StepResult:
        """
        Take one action in the environment.
        
        Args:
            action: Agent's Action (must include valid email_id)
        
        Returns:
            StepResult with new observation, reward, done flag, and info dict
        
        Raises:
            RuntimeError: If reset() has not been called or episode is done
            ValueError: If action.email_id not in current inbox
        """
        if self._state is None:
            raise RuntimeError("Call reset() before step().")
        if self._state.done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")

        state = self._state
        current_email = self._current_email()
        
        if current_email is None:
            # Failsafe if inbox is empty
            state.done = True
            obs = self._build_observation()
            obs.episode_done = True
            return StepResult(observation=obs, reward=Reward(total=0.0, explanation="Inbox empty"), done=True)

        # Ensure action targets a valid email in the inbox (specs require ValueError)
        valid_email_ids = {e.id for e in state.inbox}
        if action.email_id not in valid_email_ids:
            raise ValueError(f"Email ID {action.email_id} not in current inbox.")

        # If it targets the wrong email, we can treat it as a skip on the CURRENT email or penalize
        # Wait, spec says: "ValueError: If action.email_id not in current inbox" (checked above).
        # We assume the action is operating on the targeted email. 
        # But if it targets a valid email that is NOT the current one, it might be out of order.
        # We will retrieve the targeted email for grading purposes.
        targeted_email = next((e for e in state.inbox if e.id == action.email_id), current_email)

        # 1. Compute reward via reward function
        reward = self._reward_fn.compute_step_reward(
            action=action, 
            email=targeted_email, 
            ground_truth=state.ground_truth,
            step=state.step,
            max_steps=state.max_steps,
            grader=self._grader
        )
        self._step_rewards.append(reward)

        state.processed.append({
            "email_id": targeted_email.id,
            "action_type": action.action_type.value,
            "priority_set": action.priority.value if action.priority else None,
            "category_set": action.category.value if action.category else None,
            "reply_draft": action.reply_draft,
            "escalation_reason": action.escalation_reason,
            "snooze_hours": action.snooze_hours,
            "reasoning": action.reasoning,
            "reward_total": reward.total,
            "reward_correctness": reward.correctness,
            "reward_efficiency": reward.efficiency,
            "reward_quality": reward.quality,
            "reward_penalty": reward.penalty,
            "is_vip_sender": targeted_email.is_vip_sender,
            "step": state.step,
        })

        state.score += reward.total
        state.step += 1

        # 2. Advance to next email
        # If the agent operated on the current email, we advance. 
        # If they operated on another one, we still advance the global pointer to keep flow simple.
        state.current_email_idx += 1

        # 3. Check termination conditions:
        state.done = self._check_done()

        if state.done:
            bonus = self._reward_fn.efficiency_bonus(
                state.step, state.max_steps, len(state.processed)
            )
            if bonus > 0:
                reward.total += bonus
                reward.efficiency += bonus
                reward.explanation += " [+Efficiency Bonus]"
                state.score += bonus

        # 4. If done: compute final grade and add to info dict
        obs = self._build_observation()
        obs.episode_done = state.done

        info: Dict[str, Any] = {
            "step": state.step,
            "score": state.score,
            "emails_processed": len(state.processed),
            "emails_remaining": max(0, len(state.inbox) - state.current_email_idx),
            "reward_breakdown": reward.model_dump(),
        }

        if state.done:
            summary = self.get_episode_summary()
            if summary:
                info["episode_summary"] = summary

        return StepResult(observation=obs, reward=reward, done=state.done, info=info)

    def state(self) -> EpisodeState:
        """Return current internal state (for debugging/logging)."""
        if self._state is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")
        return self._state

    def _build_observation(self) -> Observation:
        """Build Observation from current EpisodeState."""
        state = self._state
        task: TaskConfig = self.TASKS[state.task_id]
        
        inbox_summary = {
            "total": len(state.inbox),
            "remaining": max(0, len(state.inbox) - state.current_email_idx),
            "processed": len(state.processed),
        }
        
        return Observation(
            current_email=self._current_email(),
            inbox_summary=inbox_summary,
            step_number=state.step,
            emails_processed=len(state.processed),
            emails_remaining=max(0, len(state.inbox) - state.current_email_idx),
            task_id=state.task_id,
            task_description=task.description,
            available_actions=list(AgentAction),
            context=dict(task.context),
            episode_done=state.done,
        )

    def _check_done(self) -> bool:
        """Check if episode is complete."""
        if self._state is None:
            return True
        all_processed = self._state.current_email_idx >= len(self._state.inbox)
        max_reached   = self._state.step >= self._state.max_steps
        return all_processed or max_reached

    def render(self) -> str:
        if self._state is None:
            return "Environment not initialized. Call reset()."
        state = self._state
        current = self._current_email()
        lines = [
            f"Task: {state.task_id} | Step {state.step}/{state.max_steps}",
            f"Score: {state.score:.3f} | Processed: {len(state.processed)}/{len(state.inbox)}",
        ]
        if current:
            lines += [
                f"\nCurrent email [{current.inbox_position}]:",
                f"  From:    {current.sender}",
                f"  Subject: {current.subject}",
                f"  VIP: {current.is_vip_sender}",
                f"  Body: {current.body[:80]}...",
            ]
        else:
            lines.append("\nInbox empty.")
        return "\n".join(lines)

    def close(self) -> None:
        self._state = None
        self._grader = None
        self._reward_fn = None
        self._step_rewards = []

    def _current_email(self) -> Optional[EmailWithContext]:
        if self._state is None or self._state.current_email_idx >= len(self._state.inbox):
            return None
        return self._state.inbox[self._state.current_email_idx]

    def list_tasks(self) -> List[str]:
        return list(self.TASKS.keys())

    def get_episode_summary(self) -> Optional[Dict[str, Any]]:
        if self._state is None or not self._state.done:
            return None
        
        task_score = self._grader.grade_episode(
            self._state.processed,
            self._state.ground_truth,
            self._state.inbox
        )
        
        return {
            "n_steps": self._state.step,
            "total_score": self._state.score,
            "task_score": task_score,
            "n_emails": len(self._state.inbox)
        }
