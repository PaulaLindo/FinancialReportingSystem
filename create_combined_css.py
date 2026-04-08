#!/usr/bin/env python3
"""
Create Combined CSS File
Combines all CSS files into a single cache-busted file for GitHub Pages
"""

import os
import re
from pathlib import Path
from datetime import datetime

class CombinedCSSGenerator:
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.static_dir = self.base_dir / 'static'
        self.docs_dir = self.base_dir / 'docs'
        
        # Version string
        self.version = datetime.now().strftime('%Y%m%d%H%M%S')
        
        # CSS files to combine (in correct order)
        self.css_files = [
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
    
    def create_combined_css(self):
        """Create a single combined CSS file"""
        print("=== Creating Combined CSS File ===")
        print(f"Version: {self.version}")
        print()
        
        # Create combined CSS content
        combined_content = self.build_combined_css()
        
        # Write combined CSS file
        combined_css_path = self.docs_dir / 'static' / f'combined.v{self.version}.css'
        combined_css_path.write_text(combined_content, encoding='utf-8')
        
        print(f"Combined CSS created: {combined_css_path.name}")
        print(f"Size: {len(combined_content)} characters")
        print()
        
        # Update HTML files to use combined CSS
        self.update_html_files()
        
        print("=== Combined CSS Creation Complete ===")
    
    def build_combined_css(self):
        """Build the combined CSS content"""
        content = []
        
        # Add header comment
        content.append(f"""/*
 * Combined CSS File - SADPMR Financial Reporting System
 * Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
 * Version: {self.version}
 * Description: All CSS files combined into single file for GitHub Pages
 */

""")
        
        # Add each CSS file content
        css_dir = self.static_dir / 'css'
        for css_file in self.css_files:
            css_path = css_dir / css_file
            
            if css_path.exists():
                print(f"   Adding: {css_file}")
                file_content = css_path.read_text(encoding='utf-8')
                
                # Add file header
                content.append(f"\n/* ======================================== */")
                content.append(f"/* {css_file.upper()} */")
                content.append(f"/* ======================================== */\n")
                
                # Add file content
                content.append(file_content)
                content.append("\n")
            else:
                print(f"   Warning: {css_file} not found, skipping")
        
        return ''.join(content)
    
    def update_html_files(self):
        """Update HTML files to use combined CSS"""
        print("=== Updating HTML Files ===")
        
        html_files = list(self.docs_dir.glob('*.html'))
        print(f"Updating {len(html_files)} HTML files...")
        
        combined_css_name = f"combined.v{self.version}.css"
        
        for html_file in html_files:
            print(f"   Updating: {html_file.name}")
            
            # Read HTML content
            content = html_file.read_text(encoding='utf-8')
            
            # Replace all CSS references with combined CSS
            content = self.replace_css_references(content, combined_css_name)
            
            # Write back updated content
            html_file.write_text(content, encoding='utf-8')
        
        print(f"HTML files updated to use {combined_css_name}")
        print()
    
    def replace_css_references(self, content, combined_css_name):
        """Replace all CSS references with combined CSS"""
        
        # Replace individual CSS file references
        for css_file in self.css_files:
            # Replace @import statements
            content = re.sub(
                rf'@import\s+url\(["\']?{re.escape(css_file)}["\']?\)',
                f'@import url("{combined_css_name}")',
                content
            )
        
        # Replace link tags
        content = re.sub(
            r'<link[^>]*rel=["\']stylesheet["\'][^>]*href=["\'][^"\']*\.css["\'][^>]*>',
            f'<link rel="stylesheet" href="./static/css/{combined_css_name}">',
            content
        )
        
        # Replace url_for static calls
        content = re.sub(
            r'\{\{\s*url_for\([\'"]static[\'"],\s*filename=[\'"]([^\'"]*)\.css[\'"]\)\s*\}\}',
            f'./static/css/{combined_css_name}',
            content
        )
        
        return content
    
    def verify_combined_css(self):
        """Verify the combined CSS setup"""
        print("=== Verifying Combined CSS Setup ===")
        
        # Check combined CSS file exists
        combined_css_files = list(self.docs_dir.glob(f'static/css/combined.v*.css'))
        if combined_css_files:
            combined_css_file = combined_css_files[0]
            print(f"Combined CSS file: {combined_css_file.name}")
            print(f"File size: {combined_css_file.stat().st_size} bytes")
        else:
            print("ERROR: No combined CSS file found!")
            return
        
        # Check HTML files reference combined CSS
        html_files = list(self.docs_dir.glob('*.html'))
        correct_references = 0
        
        for html_file in html_files:
            content = html_file.read_text(encoding='utf-8')
            
            if f'combined.v{self.version}.css' in content:
                correct_references += 1
        
        print(f"HTML files with correct CSS reference: {correct_references}/{len(html_files)}")
        
        # Check for any remaining individual CSS references
        remaining_refs = 0
        for html_file in html_files:
            content = html_file.read_text(encoding='utf-8')
            
            # Look for individual CSS file references
            for css_file in self.css_files:
                if css_file in content and f'combined.v{self.version}.css' not in content:
                    remaining_refs += 1
                    break
        
        if remaining_refs > 0:
            print(f"WARNING: {remaining_refs} individual CSS references remain")
        else:
            print("No individual CSS references found - GOOD!")
        
        print()
        print("=== Combined CSS Verification Complete ===")

def main():
    """Main execution function"""
    generator = CombinedCSSGenerator()
    
    # Create combined CSS
    generator.create_combined_css()
    
    # Verify the setup
    generator.verify_combined_css()
    
    print("Combined CSS setup complete!")
    print("Your local server should now work correctly with a single CSS file.")
    print()
    print("Test with:")
    print("cd docs && python -m http.server 8080")

if __name__ == '__main__':
    main()
