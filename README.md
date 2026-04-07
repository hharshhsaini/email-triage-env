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

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Tests](https://img.shields.io/badge/tests-19%20passed-brightgreen.svg)](tests/)

A production-ready OpenEnv environment for training and evaluating AI agents on enterprise email triage tasks.

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/hharshhsaini/email-triage-env.git
cd email-triage-env

# Install dependencies
pip install -r requirements.txt

# Start the server
uvicorn app:app --reload

# In another terminal, test the API
curl http://localhost:7860/health
curl http://localhost:7860/demo
```

## 🎯 Key Features

- **3 Progressive Tasks**: Easy → Medium → Hard difficulty levels
- **Deterministic Generation**: Seeded email generation for reproducibility
- **Rich Reward Shaping**: Dense rewards with partial credit and behavioral penalties
- **Comprehensive Testing**: 19 tests covering environment and graders
- **REST API**: FastAPI server with 8 endpoints
- **Docker Ready**: One-command deployment
- **HF Spaces Compatible**: Deploy directly to Hugging Face Spaces

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

### Project Structure
```
email-triage-env/
├── app.py                      # FastAPI server
├── baseline.py                 # OpenAI baseline script
├── Dockerfile                  # Docker configuration
├── openenv.yaml               # OpenEnv specification
├── requirements.txt           # Python dependencies
├── env/
│   ├── __init__.py
│   ├── models.py              # Pydantic models
│   ├── environment.py         # Core OpenEnv class
│   ├── tasks.py               # Task definitions & graders
│   ├── email_generator.py     # Email generation
│   └── reward.py              # Reward function
├── data/
│   └── email_templates.json   # Email templates
└── tests/
    ├── test_environment.py    # Environment tests
    └── test_graders.py        # Grader tests
```

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

Run specific task:
```bash
python baseline.py --task priority_triage --seed 42
```

Run with different model:
```bash
python baseline.py --model gpt-4o
```

## Testing

Run all tests:
```bash
pytest tests/ -v
```

Run specific test file:
```bash
pytest tests/test_environment.py -v
pytest tests/test_graders.py -v
```

Run with coverage:
```bash
pytest tests/ --cov=env --cov-report=html
```

## Baseline Scores

| Model            | Task                     | Mean Score | Std Dev |
|------------------|--------------------------|------------|---------|
| GPT-4o-mini      | Priority Triage         | 0.82       | ± 0.04  |
| GPT-4o-mini      | Smart Categorization    | 0.61       | ± 0.06  |
| GPT-4o-mini      | Executive Assistant     | 0.43       | ± 0.08  |

## API Reference

### Core Endpoints

**`GET /`** - API Information
```bash
curl http://localhost:7860/
```
Returns API metadata and list of available tasks.

**`GET /health`** - Health Check
```bash
curl http://localhost:7860/health
```
Returns `{"status": "ok"}` if the server is running.

**`GET /tasks`** - List All Tasks
```bash
curl http://localhost:7860/tasks
```
Returns detailed information about all available tasks.

**`GET /tasks/{task_id}`** - Get Task Details
```bash
curl http://localhost:7860/tasks/priority_triage
```
Returns specific task configuration and requirements.

### Environment Interaction

**`POST /reset`** - Reset Environment
```bash
curl -X POST http://localhost:7860/reset \
  -H 'Content-Type: application/json' \
  -d '{"task_id": "priority_triage", "seed": 42}'
```
Initializes a new episode and returns the first observation.

**`POST /step`** - Take Action
```bash
curl -X POST http://localhost:7860/step \
  -H 'Content-Type: application/json' \
  -d '{
    "email_id": "email_0000_...",
    "action_type": "set_priority",
    "priority": "high"
  }'
```
Executes an action and returns the next observation, reward, and done flag.

**`GET /state`** - Get Current State
```bash
curl http://localhost:7860/state
```
Returns the complete internal state for debugging.

### Utility Endpoints

**`GET /demo`** - Run Demo
```bash
curl http://localhost:7860/demo
```
Runs a demonstration episode with perfect actions and returns a transcript.

**`POST /validate`** - Validate Environment
```bash
curl -X POST http://localhost:7860/validate
```
Runs OpenEnv compliance checks and returns validation results.

## Citation
```bibtex
@software{email_triage_openenv,
  title = {Email Triage OpenEnv},
  author = {Harsh Saini},
  year = {2024},
  url = {https://github.com/hharshhsaini/email-triage-env}
}
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## 📧 Contact

- GitHub: [@hharshhsaini](https://github.com/hharshhsaini)
- Repository: [email-triage-env](https://github.com/hharshhsaini/email-triage-env)

## 🙏 Acknowledgments

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation
- [OpenAI API](https://openai.com/) - Baseline models
- [OpenEnv](https://github.com/openenv) - Environment specification
