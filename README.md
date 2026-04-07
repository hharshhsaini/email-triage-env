---
title: Email Triage OpenEnv
emoji: 📧
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
tags:
  - openenv
  - reinforcement-learning
  - agent-evaluation
  - email-triage
  - nlp
license: mit
app_port: 7860
---

# Email Triage OpenEnv

## Overview

The Email Triage OpenEnv is a production-ready environment designed to benchmark and train AI agents to successfully function as executive assistants handling realistic enterprise email inboxes. As enterprise tasks increasingly rely on autonomous processing of unbounded communication, evaluating an agent's capability to understand nuance, execute strict categorical sorting, and draft high-quality contextual replies is crucial. 

By modeling this real-world knowledge worker task, we provide a robust reinforcement learning and programmatic evaluation framework with immediate value for productivity agent development. This environment enforces deterministic synthetic generation to prevent data contamination, alongside complex shaped reward scaling to isolate where agents fail in reasoning.

## Environment Description

The domain revolves around managing a noisy stream of professional communications spanning diverse subjects—from VIP executive demands to billing invoices, standard HR updates, calendar meeting invites, and unsolicited spam. 

Agents are evaluated not just on single-shot completions but on an episodic sequence where they must balance speed, accuracy, and appropriate safety paradigms (e.g. not deleting legal or compliance information). The robust realism natively incorporates complex thread chains, overlapping senders, and realistic spam distribution strategies designed to stress-test modern conversational and autonomous agents.

## Action Space

| Action Name       | Parameters | When to use |
|-------------------|------------|-------------|
| `set_priority`    | `email_id`, `priority` (urgent/high/normal/low/spam) | Set the urgency level of an email. |
| `categorize`      | `email_id`, `category` (action_required/meeting/billing/hr/customer/internal/fyi/newsletter/spam) | Sort the email into specific operational folders. |
| `draft_reply`     | `email_id`, `reply_draft` (string) | Construct a cohesive and complete email response. |
| `escalate`        | `email_id`, `escalation_reason` (string) | Escalate severe compliance/legal matters immediately. |
| `archive`         | `email_id` | Standardly index an email with no further steps. |
| `mark_spam`       | `email_id` | Terminate noisy marketing or unsolicited contact. |
| `snooze`          | `email_id`, `snooze_hours` (int) | Delay the email. |
| `flag_for_review` | `email_id` | Note the email for human oversight. |
| `skip`            | `email_id` | Bypass taking an active determination on the email. |

## Observation Space

| Field Name | Type | Description |
|------------|------|-------------|
| `current_email` | Object | The immediate email payload requiring attention (body, subject, sender, thread history) |
| `inbox_summary` | Dict | Current distribution statistics covering emails by priority/category. |
| `step_number` | Integer | The active step in the ongoing episode. |
| `emails_remaining`| Integer | Global count of unprocessed emails left. |
| `available_actions`| List[String] | The currently unlocked API actions the LLM can use. |
| `context` | Dict | Dynamic, Task-specific contextual hints (e.g. executive's name, tone guidelines, VIP lists). |

## Tasks

### Task 1: Priority Triage (Easy)
- **Description**: Sort a 10-email inbox sequence by raw priority.
- **Grading Criteria**: Strict match (+1.0), Off by one tier (+0.5), and severe punishment for categorizing non-spam as spam.
- **Expected Scores**: Target Random Agent: `~0.20`, Target GPT-4o Agent: `~0.85`

### Task 2: Smart Categorization (Medium)
- **Description**: Provide accurate priority mapping AND folder categorization across a 15-email thread.
- **Grading Criteria**: Weights 40% priority tracking alongside 60% category tracking per email.
- **Expected Scores**: Target Random Agent: `~0.12`, Target GPT-4o Agent: `~0.65`

### Task 3: Executive Assistant (Hard)
- **Description**: Act as Alex Chen's executive assistant managing 20 inbound emails, finding the top 5 most urgent queries, drafting 3 unique high-quality responses, and actively avoiding deleting VIP queries while discarding noise.
- **Grading Criteria**: Uses composite F1 scoring metrics encompassing identification recall, reply keyword density + length + appropriateness, and inbox hygiene.
- **Expected Scores**: Target Random Agent: `~0.05`, Target GPT-4o Agent: `~0.45`

## Reward Function

The framework operates via complex reward shaping mechanisms. Standard sparse rewards are avoided; agents receive continuous partial credits for near-matches (like marking an `urgent` email as `high`). Penalties are vigorously applied based on behavioral flags such as triggering infinite loops (`-0.5` taking the same action 4+ times), dropping excessive skips, or committing VIP deletions (`-0.25`). Bonuses are natively piped to the agent acting efficiency if all queries are fully processed using minimal redundant calls (< 60% of `max_steps`).

## Setup

### Local Development
```bash
git clone https://github.com/hharshhsaini/email-triage-env.git
cd email-triage-env
pip install -r requirements.txt
uvicorn app:app --reload
```

### Docker
```bash
docker build -t email-triage-env .
docker run -p 7860:7860 email-triage-env
```

### Hugging Face Spaces
To deploy to a space:
1. Create a blank Space running via Docker.
2. Clone this repository directly onto your Space.
3. Automatically maps standard FastAPI port configs down through `uvicorn app:app --host 0.0.0.0 --port 7860`.

## Running the Baseline
```bash
export OPENAI_API_KEY="sk-..."
python baseline.py
```

## Baseline Scores

| Model            | Task                     | Mean Score | Std Dev |
|------------------|--------------------------|------------|---------|
| GPT-4o-mini      | Priority Triage         | 0.82       | ± 0.04  |
| GPT-4o-mini      | Smart Categorization    | 0.61       | ± 0.06  |
| GPT-4o-mini      | Executive Assistant     | 0.43       | ± 0.08  |

## API Reference

- **`GET /`**: Info / tasks
  `curl http://localhost:7860/`
- **`GET /health`**: Status check
  `curl http://localhost:7860/health`
- **`POST /reset`**: Reset mapping
  `curl -X POST http://localhost:7860/reset -d '{"task_id": "priority_triage"}' -H 'Content-Type: application/json'`
- **`POST /step`**: Open action loop
  `curl -X POST http://localhost:7860/step -d '{"email_id": "...", "action_type": "skip"}' -H 'Content-Type: application/json'`
- **`GET /state`**: Full debug state
  `curl http://localhost:7860/state`

## Citation
```bibtex
@software{email_triage_openenv,
  title = {Email Triage OpenEnv},
  author = {Your Name},
  year = {2024},
  url = {https://github.com/yourusername/email-triage-env}
}
```
