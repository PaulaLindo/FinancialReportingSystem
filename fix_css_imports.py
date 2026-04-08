#!/usr/bin/env python3
"""
Fix CSS Import References
Updates CSS @import statements to use cache-busted filenames
"""

import os
import re
from pathlib import Path

class CSSImportFixer:
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
    
    def fix_css_imports(self):
        """Fix CSS @import statements"""
        print("=== Fixing CSS Import Statements ===")
        
        css_files = list(self.docs_dir.glob('static/css/*.css'))
        print(f"Processing {len(css_files)} CSS files...")
        
        fixed_count = 0
        for css_file in css_files:
            # Read CSS content
            content = css_file.read_text(encoding='utf-8')
            original_content = content
            
            # Fix @import statements
            content = self.fix_import_statements(content)
            
            # Fix url() references
            content = self.fix_url_references(content)
            
            # Write back if changed
            if content != original_content:
                css_file.write_text(content, encoding='utf-8')
                fixed_count += 1
                print(f"   Fixed: {css_file.name}")
        
        print(f"   Fixed {fixed_count} CSS files")
        print()
    
    def fix_import_statements(self, content):
        """Fix @import statements"""
        # Fix @import statements with cache busting
        content = re.sub(
            r'@import\s+url\(["\']?([^"\')]+\.css)["\']?\)',
            lambda m: f'@import url("{self.get_cache_busted_path(m.group(1))}")',
            content
        )
        
        return content
    
    def fix_url_references(self, content):
        """Fix url() references in CSS"""
        # Fix url() references for fonts and images
        content = re.sub(
            r'url\(["\']?([^"\')]+\.(woff|woff2|ttf|eot|png|jpg|jpeg|gif|svg))["\']?\)',
            lambda m: f'url("{self.get_cache_busted_path(m.group(1))}")',
            content
        )
        
        return content
    
    def get_cache_busted_path(self, original_path):
        """Get cache-busted path for original path"""
        # Remove leading ./ if present
        clean_path = original_path.lstrip('./')
        
        # Check if it's in our manifest
        if clean_path in self.asset_manifest:
            return self.asset_manifest[clean_path]
        
        # If not in manifest, try to construct cache-busted filename
        if '.css' in clean_path or '.js' in clean_path:
            # Extract filename and extension
            parts = clean_path.split('/')
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
        """Verify CSS fixes"""
        print("=== Verifying CSS Fixes ===")
        
        # Check main CSS file
        main_css = self.docs_dir / 'static/css/styles.v20260408104658.css'
        if main_css.exists():
            content = main_css.read_text(encoding='utf-8')
            
            # Look for @import statements
            imports = re.findall(r'@import\s+url\([^)]+\)', content)
            print(f"Found {len(imports)} @import statements in main CSS:")
            for imp in imports[:5]:  # Show first 5
                print(f"   {imp}")
            
            # Check for cache-busted imports
            cache_busted_imports = re.findall(r'@import\s+url\([^)]*v[0-9]+[^)]*\)', content)
            print(f"Cache-busted imports: {len(cache_busted_imports)}")
        
        print()
        print("=== CSS Verification Complete ===")

def main():
    """Main execution function"""
    fixer = CSSImportFixer()
    
    # Fix CSS imports
    fixer.fix_css_imports()
    
    # Verify fixes
    fixer.verify_css_fixes()
    
    print("CSS import fixes complete!")
    print("All CSS files should now load correctly.")

if __name__ == '__main__':
    main()
