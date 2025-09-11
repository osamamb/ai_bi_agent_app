#!/usr/bin/env python3
"""
Simple structure test for the LangChain BI Agent
Tests basic imports and class definitions without requiring external dependencies
"""

import ast
import sys
from pathlib import Path

def test_file_structure(file_path):
    """Test if a Python file has valid syntax and expected structure"""
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Parse the AST to check syntax
        tree = ast.parse(content)
        
        # Extract class and function names
        classes = []
        functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.FunctionDef):
                functions.append(node.name)
        
        return True, classes, functions
        
    except SyntaxError as e:
        return False, [], [], f"Syntax error: {e}"
    except Exception as e:
        return False, [], [], f"Error: {e}"

def main():
    """Test all Python files in the project"""
    base_dir = Path(__file__).parent
    
    files_to_test = [
        'langchain_tools.py',
        'langchain_agents.py',
        'app.py'
    ]
    
    print("🧪 Testing LangChain BI Agent Structure")
    print("=" * 50)
    
    all_passed = True
    
    for file_name in files_to_test:
        file_path = base_dir / file_name
        
        if not file_path.exists():
            print(f"❌ {file_name}: File not found")
            all_passed = False
            continue
        
        success, classes, functions = test_file_structure(file_path)
        
        if success:
            print(f"✅ {file_name}: Valid syntax")
            if classes:
                print(f"   Classes: {', '.join(classes)}")
            if functions:
                print(f"   Functions: {', '.join(functions[:5])}{'...' if len(functions) > 5 else ''}")
        else:
            print(f"❌ {file_name}: {success}")
            all_passed = False
        
        print()
    
    # Test expected components
    print("🔍 Checking Expected Components")
    print("-" * 30)
    
    # Check langchain_tools.py
    tools_file = base_dir / 'langchain_tools.py'
    if tools_file.exists():
        success, classes, _ = test_file_structure(tools_file)
        if success:
            expected_tools = ['GenieQueryTool', 'ResponseEnhancementTool', 'SQLQueryTool']
            found_tools = [cls for cls in classes if cls in expected_tools]
            print(f"✅ Tools found: {', '.join(found_tools)}")
            if len(found_tools) != len(expected_tools):
                missing = set(expected_tools) - set(found_tools)
                print(f"⚠️  Missing tools: {', '.join(missing)}")
    
    # Check langchain_agents.py
    agents_file = base_dir / 'langchain_agents.py'
    if agents_file.exists():
        success, classes, _ = test_file_structure(agents_file)
        if success:
            expected_agents = ['BusinessIntelligenceAgent', 'VisualizationAgent']
            found_agents = [cls for cls in classes if cls in expected_agents]
            print(f"✅ Agents found: {', '.join(found_agents)}")
            if len(found_agents) != len(expected_agents):
                missing = set(expected_agents) - set(found_agents)
                print(f"⚠️  Missing agents: {', '.join(missing)}")
    
    print()
    if all_passed:
        print("🎉 All structure tests passed!")
        print("📝 Note: Runtime testing requires installing dependencies from requirements.txt")
    else:
        print("❌ Some tests failed. Check the errors above.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
