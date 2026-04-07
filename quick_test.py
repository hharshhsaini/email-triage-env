#!/usr/bin/env python3
"""
Quick Test Script for Email Triage OpenEnv
Run this to verify everything is working correctly.
"""

import sys
import subprocess
from pathlib import Path

def print_header(text):
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70)

def print_step(step, text):
    print(f"\n[{step}] {text}")

def run_test(description, test_func):
    """Run a test and report results."""
    try:
        test_func()
        print(f"  ✓ {description}")
        return True
    except Exception as e:
        print(f"  ✗ {description}")
        print(f"    Error: {e}")
        return False

def main():
    print_header("Email Triage OpenEnv - Quick Test")
    
    results = []
    
    # Test 1: Python version
    print_step(1, "Checking Python version...")
    def test_python():
        version = sys.version_info
        assert version.major == 3 and version.minor >= 11, \
            f"Python 3.11+ required, found {version.major}.{version.minor}"
        print(f"    Python {version.major}.{version.minor}.{version.micro}")
    results.append(run_test("Python version check", test_python))
    
    # Test 2: Import modules
    print_step(2, "Checking dependencies...")
    def test_imports():
        import fastapi
        import pydantic
        import pytest
        import openai
        print(f"    FastAPI {fastapi.__version__}")
        print(f"    Pydantic {pydantic.__version__}")
    results.append(run_test("Dependencies installed", test_imports))
    
    # Test 3: Import environment
    print_step(3, "Checking environment modules...")
    def test_env_imports():
        from env.environment import EmailTriageEnv
        from env.models import Action, AgentAction
        from env.email_generator import EmailGenerator
        from env.tasks import get_task
    results.append(run_test("Environment modules", test_env_imports))
    
    # Test 4: Create environment
    print_step(4, "Testing environment creation...")
    def test_env_creation():
        from env.environment import EmailTriageEnv
        env = EmailTriageEnv()
        assert env is not None
    results.append(run_test("Environment creation", test_env_creation))
    
    # Test 5: Reset environment
    print_step(5, "Testing environment reset...")
    def test_env_reset():
        from env.environment import EmailTriageEnv
        env = EmailTriageEnv()
        obs = env.reset('priority_triage', seed=42)
        assert obs.current_email is not None
        assert obs.emails_remaining == 10
        print(f"    Loaded {obs.emails_remaining} emails")
        print(f"    First email: {obs.current_email.subject[:50]}...")
    results.append(run_test("Environment reset", test_env_reset))
    
    # Test 6: Take action
    print_step(6, "Testing environment step...")
    def test_env_step():
        from env.environment import EmailTriageEnv
        from env.models import Action, AgentAction, EmailPriority
        env = EmailTriageEnv()
        obs = env.reset('priority_triage', seed=42)
        action = Action(
            email_id=obs.current_email.id,
            action_type=AgentAction.SET_PRIORITY,
            priority=EmailPriority.HIGH
        )
        result = env.step(action)
        assert result.reward is not None
        assert -1.0 <= result.reward.total <= 1.0
        print(f"    Reward: {result.reward.total:.3f}")
        print(f"    Explanation: {result.reward.explanation}")
    results.append(run_test("Environment step", test_env_step))
    
    # Test 7: Deterministic generation
    print_step(7, "Testing deterministic generation...")
    def test_deterministic():
        from env.environment import EmailTriageEnv
        env1 = EmailTriageEnv()
        obs1 = env1.reset('priority_triage', seed=42)
        env2 = EmailTriageEnv()
        obs2 = env2.reset('priority_triage', seed=42)
        assert obs1.current_email.id == obs2.current_email.id
        print(f"    Same email ID: {obs1.current_email.id}")
    results.append(run_test("Deterministic generation", test_deterministic))
    
    # Test 8: All tasks
    print_step(8, "Testing all tasks...")
    def test_all_tasks():
        from env.environment import EmailTriageEnv
        tasks = ['priority_triage', 'smart_categorization', 'executive_assistant']
        for task_id in tasks:
            env = EmailTriageEnv()
            obs = env.reset(task_id, seed=42)
            assert obs.current_email is not None
            print(f"    ✓ {task_id}: {obs.emails_remaining} emails")
    results.append(run_test("All tasks", test_all_tasks))
    
    # Test 9: Run pytest
    print_step(9, "Running test suite...")
    def test_pytest():
        result = subprocess.run(
            ['pytest', 'tests/', '-v', '--tb=short'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            # Count passed tests
            output = result.stdout
            if 'passed' in output:
                passed = output.split('passed')[0].split()[-1]
                print(f"    {passed} tests passed")
        else:
            raise Exception("Some tests failed")
    results.append(run_test("Test suite", test_pytest))
    
    # Summary
    print_header("Test Summary")
    passed = sum(results)
    total = len(results)
    
    print(f"\nResults: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ All tests passed! Your environment is ready to use.")
        print("\nNext steps:")
        print("  1. Start the server: uvicorn app:app --reload")
        print("  2. Test the API: curl http://localhost:8000/health")
        print("  3. Run demo: curl http://localhost:8000/demo")
        print("  4. (Optional) Run baseline: python baseline.py")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please check the errors above.")
        print("\nTroubleshooting:")
        print("  1. Make sure you're in the project directory")
        print("  2. Install dependencies: pip install -r requirements.txt")
        print("  3. Check Python version: python --version (need 3.11+)")
        return 1

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        sys.exit(1)
