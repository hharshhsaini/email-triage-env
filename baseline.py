#!/usr/bin/env python3
"""
Baseline inference script for Email Triage OpenEnv.

Runs GPT-4o-mini (or custom model) against all 3 tasks and reports reproducible scores.

Environment Variables (Competition Requirements):
    API_BASE_URL: Optional custom API endpoint (e.g., for HuggingFace Inference)
    MODEL_NAME: Model to use (defaults to gpt-4o-mini)
    OPENAI_API_KEY or HF_TOKEN: API authentication token
    LOCAL_IMAGE_NAME: Optional, for Docker-based inference (not used in this script)

Stdout Logging:
    Follows structured format (START/STEP/END) as JSON for competition evaluation.
    All non-structured output goes to stderr.

Usage:
    python baseline.py                    # Run all tasks, 3 seeds each
    python baseline.py --task priority_triage --seed 42
    python baseline.py --model gpt-4o    # Use different model
    python baseline.py --local           # Use local env (no HTTP)
    
    # With custom API endpoint:
    export API_BASE_URL="https://api-inference.huggingface.co/models/meta-llama/Llama-3.3-70B-Instruct"
    export MODEL_NAME="meta-llama/Llama-3.3-70B-Instruct"
    export HF_TOKEN="hf_..."
    python baseline.py
"""

import os
import json
import sys
import argparse
import requests
from typing import Dict, Any, List

from openai import OpenAI
from env.environment import EmailTriageEnv
from env.models import Action, AgentAction, StepResult, Observation
from pydantic import ValidationError


SYSTEM_PROMPT = """You are an expert executive assistant managing an email inbox.
Your job is to triage emails efficiently and accurately.

For each email you receive, you must respond with a JSON action following 
this exact schema:
{
  "email_id": "<id of the email>",
  "action_type": "<one of: set_priority, categorize, draft_reply, escalate, archive, mark_spam, snooze, flag_for_review, skip>",
  "priority": "<urgent|high|normal|low|spam — include if action_type is set_priority>",
  "category": "<action_required|fyi|meeting|billing|hr|customer|internal|spam|newsletter — include if action_type is categorize>",
  "reply_draft": "<draft text — include if action_type is draft_reply>",
  "escalation_reason": "<reason — include if action_type is escalate>",
  "reasoning": "<brief explanation of why you chose this action>"
}

PRIORITY GUIDELINES:
- urgent: Requires immediate action, business-critical
- high: Important, needs attention today
- normal: Standard business email
- low: Informational, can wait
- spam: Unsolicited/irrelevant

CATEGORIZATION GUIDELINES:
- action_required: Someone needs you to do something with a deadline
- meeting: Calendar invites, scheduling requests
- billing: Invoices, payments, financial matters
- hr: HR, benefits, payroll, company policy
- customer: External customer communications
- internal: Internal team/company communications
- fyi: Informational only, no action needed
- newsletter: Marketing emails, newsletters
- spam: Junk/unwanted email

Respond ONLY with valid JSON. No other text."""


class EmailTriageAgent:
    def __init__(self, model: str = None, env_url: str = None, local: bool = False):
        # Competition requirements: support API_BASE_URL, MODEL_NAME, HF_TOKEN
        self.model = model or os.getenv("MODEL_NAME", "gpt-4o-mini")
        self.env_url = env_url
        self.local = local
        self.local_env = EmailTriageEnv() if local else None
        
        # Get API credentials from environment
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("HF_TOKEN")
        api_base = os.getenv("API_BASE_URL")
        
        if not api_key:
            print("WARNING: OPENAI_API_KEY or HF_TOKEN environment variable not set. LLM calls will fail.", file=sys.stderr)
            # Use dummy key for testing (will fail on actual API calls)
            api_key = "dummy-key-for-testing"
        
        # Initialize OpenAI client with optional base_url for custom endpoints
        client_kwargs = {"api_key": api_key}
        if api_base:
            client_kwargs["base_url"] = api_base
            
        self.client = OpenAI(**client_kwargs)

    def _get_action(self, observation: dict) -> dict:
        """Get next action from LLM given current observation."""
        obs_str = json.dumps(observation, indent=2)
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Current observation:\n{obs_str}\nProvide your action in JSON."}
                ],
                response_format={"type": "json_object"},
                temperature=0.0
            )
            raw_action = json.loads(response.choices[0].message.content)
            return raw_action
        except Exception as e:
            # Fallback to skip if API fails
            print(f"  [!] OpenAI Error: {e}")
            if "current_email" in observation and observation["current_email"]:
                return {
                    "email_id": observation["current_email"]["id"],
                    "action_type": "skip",
                    "reasoning": f"Fallback action due to exception: {e}"
                }
            return {}

    def _reset_env(self, task_id: str, seed: int) -> dict:
        if self.local:
            obs = self.local_env.reset(task_id=task_id, seed=seed)
            return obs.model_dump()
        else:
            url = f"{self.env_url}/reset"
            resp = requests.post(url, json={"task_id": task_id, "seed": seed})
            resp.raise_for_status()
            return resp.json()

    def _step_env(self, action_dict: dict) -> dict:
        if self.local:
            try:
                action = Action(**action_dict)
            except ValidationError as e:
                # If model hallucinates, we force skip
                action = Action(
                    email_id=action_dict.get("email_id", ""),
                    action_type=AgentAction.SKIP,
                    reasoning="LLM payload schema failure"
                )
            res = self.local_env.step(action)
            return res.model_dump()
        else:
            url = f"{self.env_url}/step"
            resp = requests.post(url, json=action_dict)
            resp.raise_for_status()
            return resp.json()

    def run_episode(self, task_id: str, seed: int = 42, verbose: bool = False) -> dict:
        """Run one full episode. Returns {score, steps, actions, final_reward}."""
        # Competition requirement: Structured stdout logging with [START]/[STEP]/[END] format
        print(f"[START] task={task_id} seed={seed} model={self.model}", flush=True)
        
        obs = self._reset_env(task_id, seed)
        done = obs.get("episode_done", False)
        
        steps = 0
        actions_taken = []
        final_summary = {}

        while not done:
            action_payload = self._get_action(obs)
            res = self._step_env(action_payload)
            
            steps += 1
            reward_info = res["info"].get("reward_breakdown", {})
            done = res["done"]
            
            # Competition requirement: Log each step with [STEP] format
            reward_val = reward_info.get("total", 0)
            print(f"[STEP] step={steps} reward={reward_val:.3f}", flush=True)
            
            actions_taken.append({
                "step": steps,
                "action": action_payload,
                "reward": reward_info
            })
            
            if verbose:
                atype = action_payload.get("action_type")
                reason = action_payload.get("reasoning", "")[:50]
                total_rew = reward_info.get("total", 0)
                print(f"[VERBOSE] Step {steps}: {atype} | Reward: {total_rew} | {reason}...", file=sys.stderr)
                
            if done:
                final_summary = res["info"].get("episode_summary", {})
                break
                
            obs = res["observation"]

        # Competition requirement: Log episode end with [END] format
        final_score = final_summary.get("task_score", 0.0)
        print(f"[END] task={task_id} score={final_score:.3f} steps={steps}", flush=True)

        return {
            "score": final_score,
            "total_score": final_summary.get("total_score", 0.0),
            "steps": steps,
            "actions": actions_taken,
            "summary": final_summary
        }


def run_all_tasks(agent: EmailTriageAgent):
    tasks = ["priority_triage", "smart_categorization", "executive_assistant"]
    seeds = [42, 43, 44]
    
    results = {}
    print("\n" + "="*50, file=sys.stderr)
    print("Running All Tasks Formulation", file=sys.stderr)
    print("="*50, file=sys.stderr)
    
    for task in tasks:
        task_scores = []
        for seed in seeds:
            print(f"Running {task} (seed {seed})...", file=sys.stderr)
            res = agent.run_episode(task_id=task, seed=seed, verbose=False)
            task_scores.append(res["score"])
        
        avg = sum(task_scores) / len(task_scores)
        variance = sum((x - avg) ** 2 for x in task_scores) / len(task_scores)
        std_dev = variance ** 0.5
        
        results[task] = {
            "scores": task_scores,
            "average": avg,
            "std_dev": std_dev
        }
    
    print("\n" + "="*50, file=sys.stderr)
    print("Baseline scores (GPT-4o-mini, seeds 42/43/44):", file=sys.stderr)
    for task, data in results.items():
        print(f"  {task:<25}: {data['average']:.2f} ± {data['std_dev']:.2f}", file=sys.stderr)
    print("="*50, file=sys.stderr)
    
    with open("baseline_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("Saved results to baseline_results.json", file=sys.stderr)
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Email Triage Baseline Test")
    parser.add_argument("--task", type=str, help="Specific task ID to run")
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    parser.add_argument("--model", type=str, help="OpenAI Model (defaults to MODEL_NAME env var or gpt-4o-mini)")
    parser.add_argument("--local", action="store_true", help="Run env locally without requests")
    parser.add_argument("--url", type=str, default="http://localhost:7860", help="Env URL if remote")
    parser.add_argument("--all", action="store_true", help="Run all tasks with multiple seeds")
    args = parser.parse_args()
    
    agent = EmailTriageAgent(model=args.model, env_url=args.url, local=args.local)
    
    if args.all:
        # Run all tasks with multiple seeds (for benchmarking)
        if not args.local:
            print("Running in remote mode. Make sure the server is up!", file=sys.stderr)
        run_all_tasks(agent)
    elif args.task:
        # Run specific task
        res = agent.run_episode(task_id=args.task, seed=args.seed, verbose=True)
        print(f"\nFinal Summary: {json.dumps(res['summary'], indent=2)}", file=sys.stderr)
    else:
        # Default: Run priority_triage task once (for competition validation)
        print("No task specified. Running default task: priority_triage with seed 42", file=sys.stderr)
        res = agent.run_episode(task_id="priority_triage", seed=42, verbose=False)


if __name__ == "__main__":
    main()
