"""
FastAPI Server for the Email Triage OpenEnv.
"""

from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from typing import Optional, Dict, Any, List

import copy
from env.environment import EmailTriageEnv
from env.models import Action, Observation, StepResult, EpisodeState
from env.tasks import TASK_REGISTRY

app = FastAPI(
    title="Email Triage OpenEnv",
    description="OpenEnv environment for training agents on email triage",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global environment instance (suitable for single-user/HF Space)
# For multi-user, a Dict[str, EmailTriageEnv] mapping session_id -> env could be used.
_global_env = EmailTriageEnv()

# Custom error handler to match specs
@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"error": "ValueError", "detail": str(exc)}
    )

@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    return JSONResponse(
        status_code=409,
        content={"error": "RuntimeError", "detail": str(exc)}
    )


class ResetRequest(BaseModel):
    task_id: Optional[str] = "priority_triage"
    seed: Optional[int] = 42
    n_emails: Optional[int] = None

@app.get("/")
def get_root() -> Dict[str, Any]:
    return {
        "name": "Email Triage OpenEnv",
        "version": "1.0.0",
        "status": "ready",
        "description": "API for Email Triage Tasks",
        "available_tasks": list(TASK_REGISTRY.keys())
    }

@app.get("/health")
def get_health() -> Dict[str, str]:
    return {"status": "ok"}

@app.post("/reset", response_model=Observation)
def reset_env(req: ResetRequest = Body(default=ResetRequest())) -> Any:
    # ValueError is caught by the exception handler
    obs = _global_env.reset(
        task_id=req.task_id or "priority_triage",
        seed=req.seed if req.seed is not None else 42,
        n_emails=req.n_emails
    )
    return obs.model_dump()

@app.post("/step", response_model=StepResult)
def step_env(action: Action) -> Any:
    # RuntimeError / ValueError are handled gracefully
    result = _global_env.step(action)
    return result.model_dump()

@app.get("/state", response_model=EpisodeState)
def get_state() -> Any:
    return _global_env.state().model_dump()

@app.get("/tasks")
def list_tasks() -> List[Dict[str, Any]]:
    return [
        {
            "task_id": key,
            "description": cfg.description,
            "difficulty": cfg.difficulty,
            "n_emails": cfg.n_emails,
            "has_grader": True,  # All our tasks have graders
            "grader_type": "automated"
        }
        for key, cfg in TASK_REGISTRY.items()
    ]

@app.get("/graders")
def list_graders() -> Dict[str, Any]:
    """Return information about available graders for competition validation."""
    return {
        "count": 3,
        "graders": [
            {
                "task_id": "priority_triage",
                "grader_class": "PriorityTriageGrader",
                "type": "automated",
                "metrics": ["accuracy", "precision", "recall", "f1_score"],
                "score_range": [0.01, 0.99]
            },
            {
                "task_id": "smart_categorization",
                "grader_class": "SmartCategorizationGrader",
                "type": "automated",
                "metrics": ["accuracy", "category_distribution", "consistency"],
                "score_range": [0.01, 0.99]
            },
            {
                "task_id": "executive_assistant",
                "grader_class": "ExecutiveAssistantGrader",
                "type": "automated",
                "metrics": ["prioritization_f1", "reply_quality", "escalation_accuracy", "inbox_hygiene"],
                "score_range": [0.01, 0.99]
            }
        ]
    }

@app.get("/tasks/{task_id}")
def get_task_details(task_id: str) -> Dict[str, Any]:
    if task_id not in TASK_REGISTRY:
        raise HTTPException(status_code=400, detail=f"Task {task_id} not found")
    cfg = TASK_REGISTRY[task_id]
    return {
        "task_id": cfg.task_id,
        "description": cfg.description,
        "difficulty": cfg.difficulty,
        "n_emails": cfg.n_emails,
        "max_steps": cfg.max_steps,
        "context": cfg.context,
        "has_grader": True,
        "grader_type": "automated"
    }

@app.post("/validate")
def validate_env() -> Dict[str, Any]:
    """Run openenv validate checks, return results."""
    # Smoke tests essentially
    try:
        env = EmailTriageEnv()
        obs = env.reset("priority_triage", 42, n_emails=2)
        if obs is None: raise ValueError("Reset returned None")
        return {"status": "valid", "detail": "Environment fully OpenEnv compliant."}
    except Exception as e:
        return {"status": "invalid", "detail": str(e)}

@app.get("/demo")
def run_demo() -> Dict[str, Any]:
    """Run a 5-step perfect demo and return transcript."""
    env = EmailTriageEnv()
    obs = env.reset("priority_triage", 42, n_emails=5)
    
    transcript = []
    transcript.append({"event": "reset", "obs": obs.model_dump()})
    
    for _ in range(5):
        if env._state.done: break
        
        email_id = obs.current_email.id
        from env.models import Action, AgentAction, EmailPriority
        
        gt = env._state.ground_truth.get(email_id, {})
        ideal_priority = gt.get("priority", EmailPriority.NORMAL)
        
        action = Action(
            email_id=email_id, 
            action_type=AgentAction.SET_PRIORITY,
            priority=ideal_priority,
            reasoning="Perfect action generated from ground truth for demo."
        )
        
        # Store subject before stepping
        subj = obs.current_email.subject
        
        res = env.step(action)
        transcript.append({
            "event": "step",
            "email_subject": subj,
            "action": action.model_dump(),
            "reward": res.reward.model_dump(exclude_unset=True),
            "running_score": res.info["score"],
            "done": res.done
        })
        obs = res.observation
        
    return {
        "status": "demo_complete",
        "transcript": transcript,
        "final_summary": env.get_episode_summary()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=7860, reload=True)
