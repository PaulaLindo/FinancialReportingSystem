#!/usr/bin/env python3
"""
Cleanup Duplicate Models Script
Removes duplicate model files and consolidates the codebase
"""

import os
import shutil
from pathlib import Path

def cleanup_duplicate_models():
    """Remove duplicate model files and update imports"""
    
    print("🧹 Cleaning up duplicate models...")
    
    # Define project root
    project_root = Path(__file__).parent.parent
    
    # Files to remove (duplicates)
    duplicates_to_remove = [
        'models/trial_balance_models.py',
        'services/flexible_trial_balance_service.py'
    ]
    
    # Files to keep (canonical versions)
    files_to_keep = [
        'models/balance_sheet_models.py',
        'services/flexible_balance_sheet_service.py'
    ]
    
    # Remove duplicate files
    for duplicate_path in duplicates_to_remove:
        full_path = project_root / duplicate_path
        if full_path.exists():
            print(f"🗑️  Removing duplicate: {duplicate_path}")
            backup_path = full_path.with_suffix('.py.backup')
            shutil.move(str(full_path), str(backup_path))
            print(f"💾 Backup created: {backup_path.name}")
        else:
            print(f"⚠️  File not found: {duplicate_path}")
    
    # Verify kept files exist
    for keep_path in files_to_keep:
        full_path = project_root / keep_path
        if full_path.exists():
            print(f"✅ Keeping canonical: {keep_path}")
        else:
            print(f"❌ Missing canonical file: {keep_path}")
    
    print("\n📝 Next steps:")
    print("1. Update all imports from trial_balance_models to balance_sheet_models")
    print("2. Update all imports from flexible_trial_balance_service to flexible_balance_sheet_service")
    print("3. Test the application thoroughly")
    print("4. Remove backup files if everything works correctly")
    
    return True

def find_imports_to_update():
    """Find all files that need import updates"""
    
    print("\n🔍 Searching for imports to update...")
    
    project_root = Path(__file__).parent.parent
    
    # Search patterns
    old_imports = [
        'from models.trial_balance_models import',
        'from services.flexible_trial_balance_service import',
        'import trial_balance_models',
        'import flexible_trial_balance_service'
    ]
    
    new_imports = [
        'from models.balance_sheet_models import',
        'from services.flexible_balance_sheet_service import',
        'import balance_sheet_models',
        'import flexible_balance_sheet_service'
    ]
    
    files_to_update = []
    
    # Search through Python files
    for py_file in project_root.rglob('*.py'):
        if 'scripts' in str(py_file) or '__pycache__' in str(py_file):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            for old_import in old_imports:
                if old_import in content:
                    files_to_update.append({
                        'file': str(py_file.relative_to(project_root)),
                        'old_import': old_import,
                        'new_import': new_imports[old_imports.index(old_import)]
                    })
                    break
        except Exception as e:
            print(f"⚠️  Error reading {py_file}: {e}")
    
    if files_to_update:
        print(f"\n📄 Found {len(files_to_update)} files that need import updates:")
        for file_info in files_to_update:
            print(f"   - {file_info['file']}")
            print(f"     Replace: {file_info['old_import']}")
            print(f"     With: {file_info['new_import']}")
    else:
        print("\n✅ No import updates needed")
    
    return files_to_update

def create_import_update_script(files_to_update):
    """Create a script to update all imports"""
    
    if not files_to_update:
        return
    
    print("\n📝 Creating import update script...")
    
    project_root = Path(__file__).parent.parent
    script_path = project_root / 'scripts' / 'update_imports.py'
    
    script_content = '''#!/usr/bin/env python3
"""
Update Imports Script
Automatically updates imports from old duplicate models to new canonical models
"""

import os
import re
from pathlib import Path

def update_imports():
    """Update all imports in the codebase"""
    
    project_root = Path(__file__).parent.parent
    
    # Import mappings
    import_mappings = {
'''
    
    # Group files by import mapping
    mappings = {}
    for file_info in files_to_update:
        key = file_info['old_import']
        if key not in mappings:
            mappings[key] = file_info['new_import']
    
    for old_import, new_import in mappings.items():
        script_content += f"        '{old_import}': '{new_import}',\n"
    
    script_content += '''    }
    
    files_updated = 0
    
    # Process each Python file
    for py_file in project_root.rglob('*.py'):
        if 'scripts' in str(py_file) or '__pycache__' in str(py_file):
            continue
            
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            content = original_content
            updated = False
            
            # Apply each import mapping
            for old_import, new_import in import_mappings.items():
                if old_import in content:
                    content = content.replace(old_import, new_import)
                    updated = True
            
            # Write back if updated
            if updated:
                with open(py_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                files_updated += 1
                print(f"✅ Updated: {py_file.relative_to(project_root)}")
                
        except Exception as e:
            print(f"❌ Error processing {py_file}: {e}")
    
    print(f"\\n🎉 Updated imports in {files_updated} files")

if __name__ == "__main__":
    update_imports()
'''
    
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    print(f"✅ Created import update script: {script_path.relative_to(project_root)}")
    print("   Run: python scripts/update_imports.py")

def main():
    """Main cleanup function"""
    
    print("🚀 Starting duplicate model cleanup...")
    
    # Step 1: Remove duplicate files
    cleanup_duplicate_models()
    
    # Step 2: Find imports to update
    files_to_update = find_imports_to_update()
    
    # Step 3: Create update script
    create_import_update_script(files_to_update)
    
    print("\n✨ Cleanup preparation completed!")
    print("\n📋 Next Steps:")
    print("1. Run: python scripts/update_imports.py")
    print("2. Test the application thoroughly")
    print("3. If everything works, remove backup files:")
    print("   - models/trial_balance_models.py.backup")
    print("   - services/flexible_trial_balance_service.py.backup")

if __name__ == "__main__":
    main()
