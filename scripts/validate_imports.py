#!/usr/bin/env python3
"""
Import validation script to catch missing imports before runtime
Run this script to validate all critical service imports
"""

import sys
import os
import importlib
import traceback
from typing import List, Dict, Tuple

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Critical services and their required imports
CRITICAL_SERVICES = {
    'services.flexible_trial_balance_service': [
        'pandas', 'uuid', 'json', 'hashlib', 'logging', 're', 
        'datetime', 'typing', 'dataclasses', 'decimal', 'supabase'
    ],
    'services.grap_mapping_service': [
        'pandas', 'json', 'logging', 'datetime', 'typing'
    ],
    'models.supabase_auth_models': [
        'supabase', 'uuid', 'logging', 'datetime'
    ],
    'models.trial_balance_models': [
        'pandas', 'uuid', 'json', 'logging', 'datetime', 'typing', 'dataclasses'
    ]
}

def validate_service_imports(service_name: str, required_imports: List[str]) -> Tuple[bool, List[str]]:
    """
    Validate that a service can be imported and has all required modules available
    """
    missing_imports = []
    
    try:
        # Test importing the service itself
        module = importlib.import_module(service_name)
        print(f"✅ {service_name} imported successfully")
        
        # Test that required modules are available
        for import_name in required_imports:
            try:
                importlib.import_module(import_name)
                print(f"   ✅ {import_name} available")
            except ImportError as e:
                missing_imports.append(f"{import_name}: {e}")
                print(f"   ❌ {import_name} missing: {e}")
        
        # Test basic functionality if it's the flexible service
        if 'flexible_trial_balance_service' in service_name:
            try:
                service_instance = getattr(module, 'flexible_trial_balance_service', None)
                if service_instance:
                    # Test critical methods exist
                    required_methods = ['process_upload', '_detect_structure', '_detect_column_types']
                    for method in required_methods:
                        if hasattr(service_instance, method):
                            print(f"   ✅ Method {method} exists")
                        else:
                            missing_imports.append(f"Method {method} missing")
                            print(f"   ❌ Method {method} missing")
                else:
                    missing_imports.append("Service instance not found")
                    print(f"   ❌ Service instance not found")
            except Exception as e:
                missing_imports.append(f"Service instantiation error: {e}")
                print(f"   ❌ Service instantiation error: {e}")
        
        return len(missing_imports) == 0, missing_imports
        
    except Exception as e:
        error_msg = f"Failed to import {service_name}: {e}"
        print(f"❌ {error_msg}")
        traceback.print_exc()
        return False, [error_msg]

def check_syntax_errors() -> List[str]:
    """Check for syntax errors in critical Python files"""
    syntax_errors = []
    
    critical_files = [
        'services/flexible_trial_balance_service.py',
        'services/grap_mapping_service.py',
        'controllers/routes.py',
        'models/supabase_auth_models.py',
        'models/trial_balance_models.py'
    ]
    
    for file_path in critical_files:
        full_path = os.path.join(project_root, file_path)
        if os.path.exists(full_path):
            try:
                with open(full_path, 'r', encoding='utf-8') as f:
                    compile(f.read(), full_path, 'exec')
                print(f"✅ {file_path} - No syntax errors")
            except SyntaxError as e:
                error_msg = f"{file_path}: Syntax error at line {e.lineno}: {e.msg}"
                syntax_errors.append(error_msg)
                print(f"❌ {error_msg}")
            except Exception as e:
                error_msg = f"{file_path}: Error checking syntax: {e}"
                syntax_errors.append(error_msg)
                print(f"⚠️  {error_msg}")
        else:
            error_msg = f"{file_path}: File not found"
            syntax_errors.append(error_msg)
            print(f"⚠️  {error_msg}")
    
    return syntax_errors

def main():
    """Run all validation checks"""
    print("🔍 Validating Critical Service Imports...")
    print("=" * 60)
    
    all_issues = []
    
    # Check syntax errors first
    print("\n📝 Checking Syntax Errors:")
    syntax_errors = check_syntax_errors()
    all_issues.extend(syntax_errors)
    
    # Validate service imports
    print("\n🔧 Validating Service Imports:")
    for service_name, required_imports in CRITICAL_SERVICES.items():
        is_valid, issues = validate_service_imports(service_name, required_imports)
        if not is_valid:
            all_issues.extend(issues)
    
    # Summary
    print("\n" + "=" * 60)
    if not all_issues:
        print("🎉 All validations passed! No import issues detected.")
        print("✅ Upload functionality should work correctly.")
        return True
    else:
        print("❌ Validation Issues Found:")
        for i, issue in enumerate(all_issues, 1):
            print(f"   {i}. {issue}")
        
        print(f"\n⚠️  {len(all_issues)} issue(s) found that may cause upload failures.")
        print("🔧 Please fix these issues before deploying.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
