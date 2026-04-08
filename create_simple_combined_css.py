#!/usr/bin/env python3
"""
Simple Combined CSS Creator
Creates a single CSS file with all styles combined
"""

import os
import re
from pathlib import Path
from datetime import datetime

def create_combined_css():
    """Create a single combined CSS file"""
    base_dir = Path(__file__).parent
    static_dir = base_dir / 'static'
    docs_dir = base_dir / 'docs'
    
    # Version string
    version = datetime.now().strftime('%Y%m%d%H%M%S')
    
    print("=== Creating Simple Combined CSS ===")
    print(f"Version: {version}")
    
    # CSS files to combine
    css_files = [
        'base.css',
        'layout.css', 
        'components.css',
        'pages.css',
        'reports.css',
        'component-utilities.css',
        'mobile.css',
        'desktop.css',
        'login.css',
        'fluid-responsive.css',
        'viewport-testing.css',
        'component-states.css',
        'test-mobile-menu.css',
        'touch-friendly-interactive.css'
    ]
    
    # Build combined content
    content = []
    content.append(f"/*\n * Combined CSS - SADPMR Financial Reporting System\n * Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n * Version: {version}\n */\n\n")
    
    css_dir = static_dir / 'css'
    for css_file in css_files:
        css_path = css_dir / css_file
        if css_path.exists():
            print(f"   Adding: {css_file}")
            file_content = css_path.read_text(encoding='utf-8')
            content.append(f"/* {css_file.upper()} */\n")
            content.append(file_content)
            content.append("\n\n")
        else:
            print(f"   Warning: {css_file} not found")
    
    # Write combined CSS file
    combined_css_path = docs_dir / 'static' / 'css' / f'combined.v{version}.css'
    combined_css_path.write_text(''.join(content), encoding='utf-8')
    
    print(f"Combined CSS created: combined.v{version}.css")
    
    # Update HTML files
    update_html_files(docs_dir, f'combined.v{version}.css')
    
    print("=== Simple Combined CSS Complete ===")

def update_html_files(docs_dir, combined_css_name):
    """Update HTML files to use combined CSS"""
    print("=== Updating HTML Files ===")
    
    html_files = list(docs_dir.glob('*.html'))
    print(f"Updating {len(html_files)} HTML files...")
    
    for html_file in html_files:
        print(f"   Updating: {html_file.name}")
        
        content = html_file.read_text(encoding='utf-8')
        
        # Replace all CSS references with combined CSS
        # Replace link tags
        content = re.sub(
            r'<link[^>]*rel=["\']stylesheet["\'][^>]*href=["\'][^"\']*\.css["\'][^>]*>',
            f'<link rel="stylesheet" href="./static/css/{combined_css_name}">',
            content
        )
        
        # Replace @import statements
        content = re.sub(
            r'@import\s+url\(["\']?[^"\']*\.css["\']?\)',
            f'@import url("{combined_css_name}")',
            content
        )
        
        html_file.write_text(content, encoding='utf-8')
    
    print(f"HTML files updated to use {combined_css_name}")

if __name__ == '__main__':
    create_combined_css()
    print("\nTest with:")
    print("cd docs && python -m http.server 8080")
