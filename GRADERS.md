# Graders Documentation

This environment includes automated graders for all 3 tasks.

## Task 1: Priority Triage (Easy)
- **Grader Class**: `PriorityTriageGrader`
- **Location**: `env/tasks.py`
- **Metrics**: Accuracy, Precision, Recall, F1 Score
- **Score Range**: (0.01, 0.99)
- **Method**: Compares predicted priority with ground truth priority

## Task 2: Smart Categorization (Medium)
- **Grader Class**: `SmartCategorizationGrader`
- **Location**: `env/tasks.py`
- **Metrics**: Accuracy, Category Distribution, Consistency
- **Score Range**: (0.01, 0.99)
- **Method**: Evaluates both priority and category assignments

## Task 3: Executive Assistant (Hard)
- **Grader Class**: `ExecutiveAssistantGrader`
- **Location**: `env/tasks.py`
- **Metrics**: Prioritization F1, Reply Quality, Escalation Accuracy, Inbox Hygiene
- **Score Range**: (0.01, 0.99)
- **Method**: Multi-component evaluation of EA workflow

## Grader Implementation

All graders implement the `TaskGrader` abstract base class with two methods:

1. `step_reward(action, email, ground_truth)` - Returns immediate step reward
2. `grade_episode(processed, ground_truth, inbox)` - Returns final episode score

Scores are guaranteed to be strictly between 0 and 1 (not 0.0 or 1.0) as required by OpenEnv competition.
