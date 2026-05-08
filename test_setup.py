#!/usr/bin/env python3
"""
Quick verification test to ensure everything is set up correctly
"""
import os
import sys
from pathlib import Path

def test_imports():
    """Test all required imports"""
    print("Testing imports...")
    try:
        import openai
        import anthropic
        import google.generativeai as genai
        from dotenv import load_dotenv
        from rich.console import Console
        print("✓ All dependencies installed")
        return True
    except ImportError as e:
        print(f"✗ Missing dependency: {e}")
        print("Run: pip install -r requirements.txt")
        return False

def test_env_file():
    """Check if .env file exists"""
    print("\nTesting .env file...")
    env_path = Path(".env")
    if env_path.exists():
        print("✓ .env file found")
        return True
    else:
        print("✗ .env file not found")
        print("Run: cp .env.example .env")
        print("Then add your API keys to .env")
        return False

def test_api_keys():
    """Check if API keys are set"""
    print("\nTesting API keys...")
    from dotenv import load_dotenv
    load_dotenv()
    
    keys = {
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "GOOGLE_API_KEY": os.getenv("GOOGLE_API_KEY"),
    }
    
    all_set = True
    for name, value in keys.items():
        if value and value != "your-key-here":
            print(f"✓ {name} is set")
        else:
            print(f"✗ {name} not set or is placeholder")
            all_set = False
    
    if not all_set:
        print("\nNote: You can run in MOCK_MODE=true to test without API keys")
    
    return all_set

def test_module_imports():
    """Test importing our modules"""
    print("\nTesting module imports...")
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from config import TaskType, MODELS
        from models import Task
        from policies import POLICIES
        from orchestrator import Orchestrator
        print("✓ All modules import successfully")
        return True
    except Exception as e:
        print(f"✗ Module import failed: {e}")
        return False

def test_basic_functionality():
    """Test basic orchestrator functionality"""
    print("\nTesting basic functionality...")
    try:
        from config import TaskType
        from models import Task
        from policies import POLICIES
        from orchestrator import Orchestrator
        
        # Create orchestrator in mock mode
        orchestrator = Orchestrator(mock_mode=True)
        
        # Create a test task
        task = Task(
            type=TaskType.DEAL_EXTRACTION,
            prompt="Extract discount details",
            input_text="Flat 50% off on all items"
        )
        
        # Try execution
        policy = POLICIES['balanced']
        result = orchestrator.execute_with_fallback(task, policy)
        
        if result.success:
            print("✓ Basic execution works in mock mode")
            return True
        else:
            print("✗ Execution failed")
            return False
            
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("="*60)
    print("ORCHESTRATOR VERIFICATION TEST")
    print("="*60 + "\n")
    
    results = []
    
    results.append(("Dependencies", test_imports()))
    results.append(("Environment file", test_env_file()))
    results.append(("API keys", test_api_keys()))
    results.append(("Module imports", test_module_imports()))
    results.append(("Basic functionality", test_basic_functionality()))
    
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status:8} {test_name}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "="*60)
    
    if all_passed:
        print("✓ ALL TESTS PASSED - Ready to run!")
        print("\nNext steps:")
        print("  python main.py eval --policy balanced")
        return 0
    else:
        print("✗ SOME TESTS FAILED - Fix issues above")
        print("\nFor mock mode (no API keys needed):")
        print("  export MOCK_MODE=true")
        print("  python main.py eval --policy balanced")
        return 1

if __name__ == "__main__":
    sys.exit(main())
