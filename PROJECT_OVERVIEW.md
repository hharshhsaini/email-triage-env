# Email Triage OpenEnv - Project Overview

## 🎯 What Is This Project?

**In one sentence:** A training environment where AI agents learn to manage email inboxes like a human executive assistant.

Think of it as a "gym" for AI models to practice email management skills.

---

## 📧 The Real-World Problem

Every day, busy professionals face this challenge:

**The Inbox Problem:**
- 100+ emails per day
- Mix of urgent, important, spam, and noise
- Need to prioritize, categorize, and respond
- Time-consuming and mentally draining

**What a Human Assistant Does:**
1. ✅ Sort by priority (urgent first)
2. ✅ Categorize (billing, HR, customer, etc.)
3. ✅ Draft replies for important emails
4. ✅ Escalate legal/compliance issues
5. ✅ Archive spam and newsletters

**This project teaches AI to do exactly that!**

---

## 🤖 How It Works (Simple Explanation)

### Step 1: Environment Creates Realistic Emails
```
📧 "URGENT: Production down - customer X cannot login"
📧 "Invoice #12345 - $10,000 due"
📧 "Meeting invite: Q4 Planning"
📧 "Get rich quick! Click here!"
```

### Step 2: AI Agent Takes Actions
```
Agent sees: "URGENT: Production down..."
Agent thinks: This is urgent + customer issue
Agent does: 
  - Set priority: URGENT ✓
  - Category: CUSTOMER ✓
  - Action: ESCALATE ✓
```

### Step 3: Environment Gives Feedback
```
✓ Correct priority: +0.1 reward
✓ Correct category: +0.1 reward
✓ Correct escalation: +0.1 reward
Total: +0.3 reward
```

### Step 4: AI Learns
```
AI remembers: "Urgent + customer = escalate"
Next time: Makes better decisions
Over time: Becomes a skilled assistant
```

---

## 🎮 Three Difficulty Levels

### 🟢 TASK 1: Priority Triage (EASY)
**Goal:** Sort 10 emails by priority

**Example:**
- "URGENT: Server down" → Mark as URGENT ✓
- "Newsletter from Medium" → Mark as LOW ✓
- "Invoice due today" → Mark as HIGH ✓

**Success:** 70%+ accuracy

---

### 🟡 TASK 2: Smart Categorization (MEDIUM)
**Goal:** Sort 15 emails by priority AND category

**Example:**
- "Invoice #12345" → HIGH priority + BILLING category ✓
- "Meeting: All-hands" → NORMAL priority + MEETING category ✓
- "Spam offer" → SPAM priority + SPAM category ✓

**Success:** 60%+ accuracy

---

### 🔴 TASK 3: Executive Assistant (HARD)
**Goal:** Full EA workflow on 20 emails

**Must do:**
1. Find 5 most urgent emails
2. Draft 3 professional replies
3. Escalate legal/compliance issues
4. Archive spam and newsletters
5. Never delete VIP emails

**Success:** 45%+ accuracy

---

## 💡 Why This Matters

### 1. **Practical Business Value**
- Saves hours daily for professionals
- Reduces email overload stress
- Improves response times
- Catches important emails

### 2. **AI Research**
- Tests AI reasoning abilities
- Evaluates context understanding
- Benchmarks different models
- Advances AI capabilities

### 3. **Product Development**
- Foundation for AI email assistants
- Training for productivity copilots
- Evaluation for new features
- Quality assurance for AI products

---

## 🏗️ What You Built

### 1. **Email Generator** (`env/email_generator.py`)
- Creates realistic emails
- 10 different types (urgent, spam, billing, etc.)
- 50+ unique templates
- Deterministic (same seed = same emails)

### 2. **Environment** (`env/environment.py`)
- Manages inbox state
- Processes agent actions
- Calculates rewards
- Tracks episode progress

### 3. **Graders** (`env/tasks.py`)
- Evaluates agent performance
- Scores accuracy
- Provides detailed feedback
- Compares to ground truth

### 4. **API Server** (`app.py`)
- REST API with 8 endpoints
- Easy integration for AI agents
- Can be deployed to cloud
- Supports remote testing

### 5. **Baseline** (`baseline.py`)
- Tests GPT-4 on tasks
- Provides benchmark scores
- Shows what's achievable
- Validates environment

---

## 📊 Real Example Walkthrough

### Email Arrives:
```
From: ceo@company.com
Subject: Board presentation prep - RSVP required
Body: Please RSVP for the board presentation prep session 
      happening next Wednesday at 3 PM. Your attendance is 
      mandatory as you will be presenting the engineering section.
```

### AI Agent Analysis:
```
🔍 Analyzing...
  • From: CEO (VIP sender)
  • Keywords: "mandatory", "board", "presentation"
  • Type: Meeting request
  • Urgency: High (mandatory attendance)
```

### AI Agent Decision:
```
✅ Priority: HIGH
✅ Category: MEETING
✅ Action: FLAG_FOR_REVIEW (important meeting)
```

### Environment Feedback:
```
✓ Correct priority: +0.1
✓ Correct category: +0.1
✓ Appropriate action: +0.05
Total reward: +0.25
```

---

## 🎯 Real-World Use Cases

### 1. **Email Assistant Products**
Companies like:
- Gmail (Smart Reply, Priority Inbox)
- Outlook (Focused Inbox)
- Superhuman (AI triage)
- Spark (Smart Inbox)

### 2. **AI Model Benchmarking**
Compare performance:
- GPT-4 vs Claude vs Gemini
- Which understands emails better?
- Which makes better decisions?

### 3. **Research Applications**
- Study AI decision-making
- Test reinforcement learning
- Evaluate language understanding
- Improve AI reasoning

### 4. **Enterprise Solutions**
- Corporate email management
- Customer support automation
- Executive assistant tools
- Productivity enhancement

---

## 🔬 Technical Innovation

### 1. **Deterministic Generation**
```python
# Same seed always produces same emails
env.reset(seed=42)  # Always gets same inbox
env.reset(seed=42)  # Identical to above
```
**Why it matters:** Fair comparisons, reproducible experiments

### 2. **Rich Reward Shaping**
```python
# Not just right/wrong
Correct: +1.0
Close (urgent→high): +0.5
Wrong: -0.1
Serious mistake: -0.25
```
**Why it matters:** AI learns nuance, not just binary decisions

### 3. **Realistic Complexity**
- Email threads (replies to previous emails)
- VIP senders (must never ignore)
- Spam detection (tricky patterns)
- Reply quality (not just keywords)

**Why it matters:** Prepares AI for real-world scenarios

---

## 📈 Performance Benchmarks

### GPT-4o-mini Results:
| Task | Score | Interpretation |
|------|-------|----------------|
| Priority Triage | 82% | Very good at basic sorting |
| Smart Categorization | 61% | Decent at multi-action tasks |
| Executive Assistant | 43% | Struggles with complex workflows |

### What This Tells Us:
- ✅ AI is good at simple prioritization
- ⚠️ AI needs improvement on complex tasks
- 🎯 Room for better models and training

---

## 🚀 How You Can Use It

### For Developers:
```bash
# Test your own AI agent
python your_agent.py

# Benchmark against GPT-4
python baseline.py

# Deploy to production
docker build -t email-triage .
docker run -p 7860:7860 email-triage
```

### For Researchers:
```python
# Train reinforcement learning agent
from env.environment import EmailTriageEnv

env = EmailTriageEnv()
obs = env.reset('priority_triage')

for episode in range(1000):
    action = your_rl_agent.get_action(obs)
    obs, reward, done, info = env.step(action)
    your_rl_agent.learn(reward)
```

### For Companies:
```bash
# Deploy as API service
uvicorn app:app --host 0.0.0.0 --port 7860

# Integrate with your AI
curl -X POST http://your-server:7860/step \
  -d '{"email_id": "...", "action_type": "set_priority", ...}'
```

---

## 🎓 What You Learn From This Project

### Technical Skills:
- ✅ Building AI training environments
- ✅ Designing reward functions
- ✅ Creating evaluation metrics
- ✅ REST API development
- ✅ Testing and validation

### AI Concepts:
- ✅ Reinforcement learning
- ✅ Agent-environment interaction
- ✅ Reward shaping
- ✅ Evaluation and benchmarking
- ✅ Deterministic generation

### Software Engineering:
- ✅ Clean code architecture
- ✅ Type safety (Pydantic)
- ✅ Comprehensive testing
- ✅ API design
- ✅ Documentation

---

## 🌟 The Big Picture

### Problem:
People waste hours managing email → Need AI assistance

### Solution:
Train AI to manage email like a human assistant

### This Project:
Provides the training environment + evaluation framework

### Impact:
- Better AI email assistants
- More productive professionals
- Advancement in AI capabilities
- Real-world AI applications

---

## 📝 Summary

**What it is:**
A training gym for AI to learn email management

**What it does:**
Generates realistic emails, evaluates AI decisions, provides feedback

**Why it matters:**
Solves a real daily problem, advances AI research, enables products

**How it works:**
AI sees email → AI takes action → Environment gives reward → AI learns

**Who benefits:**
- Developers building AI assistants
- Researchers studying AI decision-making
- Companies creating productivity tools
- Anyone drowning in email

---

## 🎯 Bottom Line

**This project is about teaching AI to be a helpful email assistant.**

Just like you'd train a human assistant by:
1. Showing them emails
2. Explaining what to do
3. Giving feedback
4. Letting them practice

This environment does the same for AI:
1. Shows AI realistic emails
2. AI decides what to do
3. Environment gives feedback (rewards)
4. AI practices and improves

**The result:** AI that can actually help manage your inbox, just like a skilled human assistant would.

---

## 🔗 Learn More

- **README.md** - Setup and usage instructions
- **TESTING_GUIDE.md** - How to test everything
- **openenv.yaml** - Technical specification
- **GitHub:** https://github.com/hharshhsaini/email-triage-env
