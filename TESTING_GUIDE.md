# Testing Guide for Email Triage OpenEnv

## 📋 Requirements

### System Requirements
- **Operating System**: macOS, Linux, or Windows (with WSL recommended)
- **Python**: Version 3.11 or higher
- **RAM**: Minimum 2GB available
- **Disk Space**: ~500MB for dependencies and environment

### Software Requirements
1. **Python 3.11+** - [Download here](https://www.python.org/downloads/)
2. **pip** - Python package manager (comes with Python)
3. **Git** - For cloning the repository
4. **curl** - For testing API endpoints (usually pre-installed)

### Optional Requirements
- **Docker** - For containerized testing (optional)
- **OpenAI API Key** - Only needed for baseline.py testing (costs ~$0.10-0.50 per run)

---

## 🚀 Quick Testing (5 minutes)

### Step 1: Verify Python Installation
```bash
python --version  # Should show 3.11 or higher
pip --version     # Should show pip version
```

### Step 2: Navigate to Project
```bash
cd email-triage-env
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```
**Expected time**: 1-2 minutes  
**What it installs**: FastAPI, Pydantic, pytest, and other dependencies

### Step 4: Run Tests
```bash
pytest tests/ -v
```
**Expected output**: All 19 tests should pass ✓  
**Expected time**: ~5 seconds

### Step 5: Start the Server
```bash
uvicorn app:app --reload
```
**Expected output**: 
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

### Step 6: Test the API (in a new terminal)
```bash
# Health check
curl http://localhost:8000/health

# Get available tasks
curl http://localhost:8000/tasks

# Run demo
curl http://localhost:8000/demo
```

---

## 🧪 Comprehensive Testing

### 1. Environment Testing (No API Key Needed)

#### Test All Tasks
```bash
python -c "
from env.environment import EmailTriageEnv
from env.models import Action, AgentAction, EmailPriority

# Test each task
for task_id in ['priority_triage', 'smart_categorization', 'executive_assistant']:
    env = EmailTriageEnv()
    obs = env.reset(task_id, seed=42)
    print(f'✓ {task_id}: {obs.emails_remaining} emails loaded')
"
```

#### Test Deterministic Generation
```bash
python -c "
from env.environment import EmailTriageEnv

env1 = EmailTriageEnv()
obs1 = env1.reset('priority_triage', seed=42)

env2 = EmailTriageEnv()
obs2 = env2.reset('priority_triage', seed=42)

print(f'Same email? {obs1.current_email.id == obs2.current_email.id}')
print(f'Email ID: {obs1.current_email.id}')
"
```

#### Test Reward System
```bash
python -c "
from env.environment import EmailTriageEnv
from env.models import Action, AgentAction, EmailPriority

env = EmailTriageEnv()
obs = env.reset('priority_triage', seed=42)

# Take an action
action = Action(
    email_id=obs.current_email.id,
    action_type=AgentAction.SET_PRIORITY,
    priority=EmailPriority.HIGH
)

result = env.step(action)
print(f'Reward: {result.reward.total}')
print(f'Explanation: {result.reward.explanation}')
print(f'Done: {result.done}')
"
```

### 2. API Testing (No API Key Needed)

Start the server first:
```bash
uvicorn app:app --reload
```

Then in another terminal:

#### Test All Endpoints
```bash
# 1. Health check
echo "Testing /health..."
curl -s http://localhost:8000/health | python -m json.tool

# 2. Root endpoint
echo -e "\nTesting /..."
curl -s http://localhost:8000/ | python -m json.tool

# 3. Tasks list
echo -e "\nTesting /tasks..."
curl -s http://localhost:8000/tasks | python -m json.tool

# 4. Reset environment
echo -e "\nTesting /reset..."
curl -s -X POST http://localhost:8000/reset \
  -H 'Content-Type: application/json' \
  -d '{"task_id": "priority_triage", "seed": 42}' \
  | python -m json.tool | head -30

# 5. Take a step
echo -e "\nTesting /step..."
curl -s -X POST http://localhost:8000/step \
  -H 'Content-Type: application/json' \
  -d '{"email_id": "email_0000_executive_briefing_board", "action_type": "set_priority", "priority": "high"}' \
  | python -m json.tool | head -20

# 6. Get state
echo -e "\nTesting /state..."
curl -s http://localhost:8000/state | python -m json.tool | head -20

# 7. Run demo
echo -e "\nTesting /demo..."
curl -s http://localhost:8000/demo | python -m json.tool | head -30

# 8. Validate
echo -e "\nTesting /validate..."
curl -s -X POST http://localhost:8000/validate | python -m json.tool
```

#### Interactive Testing Script
```bash
python -c "
import requests
import json

base_url = 'http://localhost:8000'

print('🧪 Interactive API Testing\n')

# Reset
print('1. Resetting environment...')
r = requests.post(f'{base_url}/reset', json={'task_id': 'priority_triage', 'seed': 42})
obs = r.json()
print(f'   ✓ Got {obs[\"emails_remaining\"]} emails')
print(f'   ✓ Current email: {obs[\"current_email\"][\"subject\"][:50]}...')

# Take 3 actions
print('\n2. Taking 3 actions...')
for i in range(3):
    email_id = obs['current_email']['id']
    r = requests.post(f'{base_url}/step', json={
        'email_id': email_id,
        'action_type': 'set_priority',
        'priority': 'normal'
    })
    result = r.json()
    print(f'   Step {i+1}: Reward = {result[\"reward\"][\"total\"]:.2f}')
    obs = result['observation']
    if result['done']:
        print('   ✓ Episode complete!')
        break

print('\n✅ All tests passed!')
"
```

### 3. Baseline Testing (Requires OpenAI API Key)

#### Setup OpenAI API Key
```bash
export OPENAI_API_KEY="sk-your-key-here"
```

**Cost Estimate**: 
- Priority Triage: ~$0.05 per run
- Smart Categorization: ~$0.10 per run
- Executive Assistant: ~$0.20 per run

#### Run Baseline on One Task
```bash
python baseline.py --task priority_triage --seed 42
```

#### Run All Tasks
```bash
python baseline.py
```
**Expected time**: 2-5 minutes  
**Expected output**: Scores for all 3 tasks

---

## 🐳 Docker Testing (Optional)

### Build Docker Image
```bash
docker build -t email-triage-env .
```
**Expected time**: 3-5 minutes

### Run Container
```bash
docker run -p 7860:7860 email-triage-env
```

### Test Docker Container
```bash
# In another terminal
curl http://localhost:7860/health
curl http://localhost:7860/demo
```

---

## 📊 Performance Testing

### Test Episode Completion Time
```bash
python -c "
import time
from env.environment import EmailTriageEnv
from env.models import Action, AgentAction

env = EmailTriageEnv()
obs = env.reset('priority_triage', seed=42)

start = time.time()
while not obs.episode_done:
    action = Action(
        email_id=obs.current_email.id,
        action_type=AgentAction.SKIP
    )
    result = env.step(action)
    obs = result.observation

elapsed = time.time() - start
print(f'Episode completed in {elapsed:.3f} seconds')
print(f'Average time per step: {elapsed/10:.3f} seconds')
"
```

### Test API Response Time
```bash
python -c "
import requests
import time

base_url = 'http://localhost:8000'

# Test reset endpoint
times = []
for i in range(10):
    start = time.time()
    r = requests.post(f'{base_url}/reset', json={'task_id': 'priority_triage', 'seed': 42})
    times.append(time.time() - start)

print(f'Average reset time: {sum(times)/len(times)*1000:.2f}ms')
print(f'Min: {min(times)*1000:.2f}ms, Max: {max(times)*1000:.2f}ms')
"
```

---

## 🔍 Troubleshooting

### Issue: "Module not found"
**Solution**: Make sure you're in the project directory and dependencies are installed
```bash
cd email-triage-env
pip install -r requirements.txt
```

### Issue: "Port already in use"
**Solution**: Use a different port
```bash
uvicorn app:app --port 8001
```

### Issue: "Tests failing"
**Solution**: Check Python version and reinstall dependencies
```bash
python --version  # Should be 3.11+
pip install --upgrade -r requirements.txt
pytest tests/ -v
```

### Issue: "OpenAI API errors"
**Solution**: Verify API key is set correctly
```bash
echo $OPENAI_API_KEY  # Should show your key
# If empty, set it:
export OPENAI_API_KEY="sk-your-key-here"
```

---

## ✅ Testing Checklist

Use this checklist to verify everything works:

- [ ] Python 3.11+ installed
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] All 19 tests pass (`pytest tests/ -v`)
- [ ] Server starts without errors (`uvicorn app:app --reload`)
- [ ] Health endpoint returns OK (`curl http://localhost:8000/health`)
- [ ] Demo endpoint works (`curl http://localhost:8000/demo`)
- [ ] Can reset environment via API
- [ ] Can take actions via API
- [ ] Deterministic generation works (same seed = same emails)
- [ ] Rewards are in valid range [-1.0, 1.0]
- [ ] (Optional) Baseline script runs with OpenAI key
- [ ] (Optional) Docker build succeeds

---

## 📈 Expected Results

### Test Suite
```
============================= test session starts ==============================
collected 19 items

tests/test_environment.py::test_reset_returns_observation PASSED         [  5%]
tests/test_environment.py::test_reset_with_each_task_id PASSED           [ 10%]
tests/test_environment.py::test_invalid_task_raises_error PASSED         [ 15%]
tests/test_environment.py::test_step_returns_step_result PASSED          [ 21%]
tests/test_environment.py::test_step_before_reset_raises PASSED          [ 26%]
tests/test_environment.py::test_episode_terminates_at_max_steps PASSED   [ 31%]
tests/test_environment.py::test_episode_terminates_when_inbox_empty PASSED [ 36%]
tests/test_environment.py::test_state_returns_episode_state PASSED       [ 42%]
tests/test_environment.py::test_seeded_reset_is_deterministic PASSED     [ 47%]
tests/test_environment.py::test_reward_is_in_valid_range PASSED          [ 52%]
tests/test_graders.py::test_priority_grader_perfect_score PASSED         [ 57%]
tests/test_graders.py::test_priority_grader_partial_credit PASSED        [ 63%]
tests/test_graders.py::test_priority_grader_all_wrong PASSED             [ 68%]
tests/test_graders.py::test_categorization_grader_both_actions PASSED    [ 73%]
tests/test_graders.py::test_categorization_grader_missing_action_penalty PASSED [ 78%]
tests/test_graders.py::test_executive_grader_reply_quality PASSED        [ 84%]
tests/test_graders.py::test_executive_grader_vip_penalty PASSED          [ 89%]
tests/test_graders.py::test_graders_deterministic PASSED                 [ 94%]
tests/test_graders.py::test_loop_detection_triggers_penalty PASSED       [100%]

============================== 19 passed in 0.10s ==============================
```

### Baseline Scores (with GPT-4o-mini)
```
Task: priority_triage
  Score: 0.82 ± 0.04

Task: smart_categorization
  Score: 0.61 ± 0.06

Task: executive_assistant
  Score: 0.43 ± 0.08
```

---

## 💡 Tips

1. **Start Simple**: Begin with the Quick Testing section
2. **No API Key Needed**: Most testing works without OpenAI API key
3. **Use Virtual Environment**: Recommended to avoid dependency conflicts
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```
4. **Check Logs**: If something fails, check the server logs for details
5. **Test Incrementally**: Test each component separately before full integration

---

## 🆘 Getting Help

If you encounter issues:
1. Check the Troubleshooting section above
2. Review server logs for error messages
3. Verify all requirements are met
4. Open an issue on GitHub with error details

---

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Pytest Documentation](https://docs.pytest.org/)
- [OpenAI API Documentation](https://platform.openai.com/docs/)
- [Docker Documentation](https://docs.docker.com/)
