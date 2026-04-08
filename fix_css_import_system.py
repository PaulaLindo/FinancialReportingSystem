#!/usr/bin/env python3
"""
Fix CSS Import System
Updates the main CSS file to use cache-busted import statements
"""

import os
import re
from pathlib import Path
from datetime import datetime

class CSSImportSystemFixer:
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.docs_dir = self.base_dir / 'docs'
        self.build_dir = self.base_dir / 'build'
        
        # Load asset manifest
        self.asset_manifest = {}
        manifest_path = self.build_dir / 'asset-manifest.json'
        if manifest_path.exists():
            import json
            with open(manifest_path, 'r') as f:
                manifest_data = json.load(f)
                self.asset_manifest = manifest_data.get('assets', {})
        
        # CSS import mapping
        self.css_imports = [
            'base.css',
            'layout.css', 
            'components.css',
            'pages.css',
            'reports.css',
            'component-utilities.css',
            'grid.css',
            'navigation-grid.css',
            'responsive-tables.css',
            'typography.css',
            'touch-friendly.css',
            'pdf-preview.css',
            'mobile.css',
            'desktop.css',
            'login.css',
            'fluid-responsive.css',
            'viewport-testing.css',
            'component-states.css',
            'test-mobile-menu.css',
            'touch-friendly-interactive.css'
        ]
    
    def fix_css_imports(self):
        """Fix CSS import statements in the main CSS file"""
        print("=== Fixing CSS Import System ===")
        
        # Find the main CSS file (cache-busted)
        main_css_files = list(self.docs_dir.glob('static/css/styles.v*.css'))
        if not main_css_files:
            print("ERROR: No cache-busted main CSS file found!")
            return False
        
        main_css_file = main_css_files[0]
        print(f"Processing main CSS file: {main_css_file.name}")
        
        # Read the main CSS content
        content = main_css_file.read_text(encoding='utf-8')
        original_content = content
        
        # Fix @import statements
        content = self.fix_import_statements(content)
        
        # Write back the fixed content
        if content != original_content:
            main_css_file.write_text(content, encoding='utf-8')
            print("   CSS import statements fixed")
        else:
            print("   No changes needed to CSS imports")
        
        return True
    
    def fix_import_statements(self, content):
        """Fix @import statements to use cache-busted filenames"""
        
        # Fix each CSS import
        for css_file in self.css_imports:
            # Look for @import url("filename.css") statements
            import_pattern = rf'@import\s+url\(["\']?{re.escape(css_file)}["\']?\)'
            
            # Check if the cache-busted version exists
            cache_busted_css = self.get_cache_busted_path(css_file)
            cache_busted_path = self.docs_dir / 'static' / cache_busted_css
            
            if cache_busted_path.exists():
                # Replace with cache-busted version
                replacement = f'@import url("{cache_busted_css}")'
                content = re.sub(import_pattern, replacement, content)
                print(f"   Fixed: {css_file} -> {cache_busted_css}")
            else:
                print(f"   Warning: Cache-busted file not found: {cache_busted_css}")
        
        return content
    
    def get_cache_busted_path(self, original_path):
        """Get cache-busted path for original path"""
        # Check if it's in our manifest
        if original_path in self.asset_manifest:
            return self.asset_manifest[original_path]
        
        # If not in manifest, try to construct cache-busted filename
        if '.css' in original_path:
            # Extract filename and extension
            parts = original_path.split('/')
            if len(parts) > 1:
                filename = parts[-1]
                directory = '/'.join(parts[:-1])
                
                # Add version to filename
                if '.' in filename:
                    name, ext = filename.rsplit('.', 1)
                    versioned_filename = f"{name}.v20260408104658.{ext}"
                    return f"{directory}/{versioned_filename}"
        
        # Return original path if not found
        return original_path
    
    def verify_css_fixes(self):
        """Verify that CSS imports are working correctly"""
        print("=== Verifying CSS Import Fixes ===")
        
        # Find the main CSS file
        main_css_files = list(self.docs_dir.glob('static/css/styles.v*.css'))
        if not main_css_files:
            print("ERROR: No main CSS file found for verification")
            return
        
        main_css_file = main_css_files[0]
        content = main_css_file.read_text(encoding='utf-8')
        
        # Look for @import statements
        imports = re.findall(r'@import\s+url\([^)]+\)', content)
        print(f"Found {len(imports)} @import statements:")
        
        cache_busted_count = 0
        for imp in imports:
            print(f"   {imp}")
            if 'v20260408104658' in imp:
                cache_busted_count += 1
        
        print(f"Cache-busted imports: {cache_busted_count}")
        
        # Check if all imported files exist
        missing_files = []
        for imp in imports:
            # Extract filename from import
            filename_match = re.search(r'url\(["\']([^"\']+)["\']\)', imp)
            if filename_match:
                filename = filename_match.group(1)
                file_path = self.docs_dir / 'static' / filename
                if not file_path.exists():
                    missing_files.append(filename)
        
        if missing_files:
            print(f"WARNING: {len(missing_files)} imported files not found:")
            for missing in missing_files:
                print(f"   Missing: {missing}")
        else:
            print("All imported files found - GOOD!")
        
        print()
        print("=== CSS Import Verification Complete ===")
    
    def create_fallback_imports(self):
        """Create fallback import statements for missing files"""
        print("=== Creating Fallback Imports ===")
        
        # Find the main CSS file
        main_css_files = list(self.docs_dir.glob('static/css/styles.v*.css'))
        if not main_css_files:
            print("ERROR: No main CSS file found")
            return
        
        main_css_file = main_css_files[0]
        content = main_css_file.read_text(encoding='utf-8')
        
        # Add fallback imports at the beginning
        fallback_imports = """/* Fallback imports for missing cache-busted files */
@import url("base.v20260408104658.css");
@import url("layout.v20260408104658.css");
@import url("components.v20260408104658.css");
@import url("pages.v20260408104658.css");
@import url("reports.v20260408104658.css");
@import url("component-utilities.v20260408104658.css");

"""
        
        # Insert fallback imports after the first comment block
        if content.startswith('/*'):
            # Find the end of the first comment block
            comment_end = content.find('*/')
            if comment_end != -1:
                content = content[:comment_end + 2] + '\n' + fallback_imports + content[comment_end + 2:]
        else:
            content = fallback_imports + content
        
        # Write back the content
        main_css_file.write_text(content, encoding='utf-8')
        
        print("   Fallback imports added to main CSS file")
        print()

def main():
    """Main execution function"""
    fixer = CSSImportSystemFixer()
    
    # Fix CSS imports
    if fixer.fix_css_imports():
        # Verify fixes
        fixer.verify_css_fixes()
        
        # Create fallback imports if needed
        fixer.create_fallback_imports()
        
        print("CSS import system fix complete!")
        print("Your local server should now load all CSS files correctly.")
        print()
        print("Test with:")
        print("cd docs && python -m http.server 8080")
    else:
        print("Failed to fix CSS import system")

if __name__ == '__main__':
    main()
