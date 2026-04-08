#!/usr/bin/env python3
"""
Fix Cache Busting Implementation
Updates HTML to use cache-busted filenames instead of query strings
"""

import os
import re
from pathlib import Path
from datetime import datetime

class CacheBustingFixer:
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
    
    def fix_html_files(self):
        """Fix HTML files to use cache-busted filenames"""
        print("=== Fixing Cache Busting Implementation ===")
        print(f"Asset manifest entries: {len(self.asset_manifest)}")
        print()
        
        html_files = list(self.docs_dir.glob('*.html'))
        print(f"Processing {len(html_files)} HTML files...")
        
        for html_file in html_files:
            print(f"   Fixing: {html_file.name}")
            
            # Read HTML content
            content = html_file.read_text(encoding='utf-8')
            
            # Fix CSS references
            content = self.fix_css_references(content)
            
            # Fix JavaScript references
            content = self.fix_js_references(content)
            
            # Fix static asset references
            content = self.fix_static_references(content)
            
            # Write back fixed content
            html_file.write_text(content, encoding='utf-8')
        
        print("   HTML files fixed")
        print()
    
    def fix_css_references(self, content):
        """Fix CSS file references"""
        # Replace query string versions with filename versions
        content = re.sub(
            r'href=["\']([^"\']*\.css)\?v=[^"\']*["\']',
            lambda m: f'href="{self.get_cache_busted_path(m.group(1))}"',
            content
        )
        
        # Replace url_for calls with cache-busted paths
        content = re.sub(
            r'href=["\']\{\{\s*url_for\([\'"]static[\'"],\s*filename=[\'"]([^\'"]*)\.css[\'"]\)\s*\}\}["\']',
            lambda m: f'href="{self.get_cache_busted_path(f"static/{m.group(1)}.css")}"',
            content
        )
        
        return content
    
    def fix_js_references(self, content):
        """Fix JavaScript file references"""
        # Replace query string versions with filename versions
        content = re.sub(
            r'src=["\']([^"\']*\.js)\?v=[^"\']*["\']',
            lambda m: f'src="{self.get_cache_busted_path(m.group(1))}"',
            content
        )
        
        # Replace url_for calls with cache-busted paths
        content = re.sub(
            r'src=["\']\{\{\s*url_for\([\'"]static[\'"],\s*filename=[\'"]([^\'"]*)\.js[\'"]\)\s*\}\}["\']',
            lambda m: f'src="{self.get_cache_busted_path(f"static/{m.group(1)}.js")}"',
            content
        )
        
        return content
    
    def fix_static_references(self, content):
        """Fix other static asset references"""
        # Fix image references
        content = re.sub(
            r'src=["\']([^"\']*\.(png|jpg|jpeg|gif|svg|ico))\?v=[^"\']*["\']',
            lambda m: f'src="{self.get_cache_busted_path(m.group(1))}"',
            content
        )
        
        # Fix absolute static paths
        content = re.sub(
            r'href=["\']\/static\/([^"\']*)["\']',
            lambda m: f'href="./static/{self.get_cache_busted_path(m.group(1))}"',
            content
        )
        
        content = re.sub(
            r'src=["\']\/static\/([^"\']*)["\']',
            lambda m: f'src="./static/{self.get_cache_busted_path(m.group(1))}"',
            content
        )
        
        return content
    
    def get_cache_busted_path(self, original_path):
        """Get cache-busted path for original path"""
        # Remove leading ./ or / if present
        clean_path = original_path.lstrip('./')
        
        # Check if it's in our manifest
        if clean_path in self.asset_manifest:
            return f"./{self.asset_manifest[clean_path]}"
        
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
                    return f"./{directory}/{versioned_filename}"
        
        # Return original path if not found
        return original_path
    
    def verify_fix(self):
        """Verify that cache busting is working correctly"""
        print("=== Verifying Cache Busting Fix ===")
        
        # Check index.html for cache-busted URLs
        index_file = self.docs_dir / 'index.html'
        if index_file.exists():
            content = index_file.read_text(encoding='utf-8')
            
            # Look for cache-busted filenames
            cache_busted_css = re.findall(r'href="[^"]*\.v[0-9]+\.css"', content)
            cache_busted_js = re.findall(r'src="[^"]*\.v[0-9]+\.js"', content)
            
            print(f"Cache-busted CSS references: {len(cache_busted_css)}")
            for ref in cache_busted_css[:3]:  # Show first 3
                print(f"   {ref}")
            
            print(f"Cache-busted JS references: {len(cache_busted_js)}")
            for ref in cache_busted_js[:3]:  # Show first 3
                print(f"   {ref}")
            
            # Check for any remaining query string versions
            query_string_refs = re.findall(r'[?&]v=[^"\']*', content)
            if query_string_refs:
                print(f"WARNING: Found {len(query_string_refs)} remaining query string references")
            else:
                print("   No query string references found - GOOD!")
        
        print()
        print("=== Verification Complete ===")

def main():
    """Main execution function"""
    fixer = CacheBustingFixer()
    
    # Fix HTML files
    fixer.fix_html_files()
    
    # Verify the fix
    fixer.verify_fix()
    
    print("Cache busting fix complete!")
    print("Your local server should now work correctly.")
    print()
    print("Test with:")
    print("cd docs && python -m http.server 8080")

if __name__ == '__main__':
    main()
