#!/usr/bin/env python3
"""
Pre-commit hook to validate critical imports and syntax
Run this automatically before commits to catch upload-breaking issues
"""

import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

def main():
    """Run pre-commit validation"""
    print("🔍 Pre-commit Validation...")
    
    # Import and run the validation script
    try:
        from scripts.validate_imports import main as validate_main
        success = validate_main()
        
        if success:
            print("✅ Pre-commit validation passed. Ready to commit.")
            return 0
        else:
            print("❌ Pre-commit validation failed. Please fix issues before committing.")
            return 1
    except Exception as e:
        print(f"❌ Pre-commit validation error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
