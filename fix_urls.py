#!/usr/bin/env python3
"""
Quick fix script to correct all navigation URLs in HTML files
"""

import os
import re
from pathlib import Path

def fix_urls_in_html():
    """Fix URLs in all HTML files in docs directory"""
    docs_dir = Path('docs')
    
    # URL mappings
    url_mappings = {
        'href="/"': 'href="index.html"',
        'href="/upload"': 'href="upload.html"',
        'href="/reports"': 'href="reports.html"',
        'href="/export"': 'href="export.html"',
        'href="/admin"': 'href="admin.html"',
        'href="/about"': 'href="about.html"',
        'href="/login"': 'href="login.html"',
        'href="/logout"': 'href="#"',
    }
    
    for html_file in docs_dir.glob('*.html'):
        print(f"Fixing URLs in {html_file.name}")
        
        content = html_file.read_text(encoding='utf-8')
        original_content = content
        
        # Apply URL mappings
        for flask_url, static_url in url_mappings.items():
            content = content.replace(flask_url, static_url)
        
        # Only write if content changed
        if content != original_content:
            html_file.write_text(content, encoding='utf-8')
            print(f"  ✅ Updated {html_file.name}")
        else:
            print(f"  ⚪ No changes needed for {html_file.name}")

if __name__ == '__main__':
    fix_urls_in_html()
    print("\nURL fixing complete!")
