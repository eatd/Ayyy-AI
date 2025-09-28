#!/usr/bin/env python3
"""
Simple test script to validate Ayyy-AI setup.
Run this to check if all components are working correctly.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

def test_imports():
    """Test that all core modules can be imported."""
    try:
        from tools import initialize_tool_registry
        from conversation_store import load_history, save_history
        from utils import get_logger
        print("✓ Core imports successful")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_tool_registry():
    """Test tool registry initialization."""
    try:
        from tools import initialize_tool_registry
        registry = initialize_tool_registry()
        tools = list(registry._tools.keys())
        print(f"✓ Tool registry initialized with {len(tools)} tools: {', '.join(tools)}")
        return True
    except Exception as e:
        print(f"✗ Tool registry error: {e}")
        return False

def test_config():
    """Test configuration loading."""
    try:
        from main import AppConfig
        config = AppConfig.load()
        print(f"✓ Configuration loaded - Model: {config.model}, Base URL: {config.base_url}")
        return True
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False

async def test_tools():
    """Test basic tool functionality."""
    try:
        from tools import initialize_tool_registry
        registry = initialize_tool_registry()
        
        # Test write_file tool
        test_content = "Test content from Ayyy-AI setup validation"
        result = await registry.execute("write_file", file_path="/tmp/ayyy_test.txt", content=test_content)
        print(f"✓ Write file test: {result}")
        
        # Test read_file tool  
        result = await registry.execute("read_file", file_path="/tmp/ayyy_test.txt")
        if test_content in result:
            print("✓ Read file test: Content matches")
        else:
            print(f"✗ Read file test: Content mismatch - {result}")
            return False
            
        # Clean up
        Path("/tmp/ayyy_test.txt").unlink(missing_ok=True)
        return True
    except Exception as e:
        print(f"✗ Tool execution error: {e}")
        return False

async def main():
    """Run all tests."""
    print("Ayyy-AI Setup Validation")
    print("=" * 40)
    
    tests = [
        ("Import Test", test_imports),
        ("Tool Registry Test", test_tool_registry), 
        ("Configuration Test", test_config),
        ("Tool Execution Test", test_tools),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\nRunning {name}...")
        if asyncio.iscoroutinefunction(test_func):
            success = await test_func()
        else:
            success = test_func()
        results.append(success)
    
    print("\n" + "=" * 40)
    print("Summary:")
    all_passed = all(results)
    status = "PASS" if all_passed else "FAIL"
    print(f"Overall Status: {status}")
    
    if all_passed:
        print("\n🎉 Ayyy-AI is ready to use!")
        print("Run 'python main.py' to start the assistant.")
    else:
        print("\n❌ Some tests failed. Check the error messages above.")
        print("You may need to install missing dependencies or fix configuration issues.")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))