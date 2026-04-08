#!/usr/bin/env python3
"""
Quick fix for GitHub Pages UI issues
"""

import re
from pathlib import Path

def fix_navbar_issues():
    """Fix the specific UI issues in GitHub Pages"""
    docs_dir = Path('docs')
    
    # Fix each HTML file
    for html_file in docs_dir.glob('*.html'):
        print(f"Fixing: {html_file.name}")
        content = html_file.read_text(encoding='utf-8')
        
        # Fix 1: Convert Flask routes to proper HTML files
        content = content.replace('href="/"', 'href="index.html"')
        content = content.replace('href="/upload"', 'href="upload.html"')
        content = content.replace('href="/reports"', 'href="reports.html"')
        content = content.replace('href="/export"', 'href="export.html"')
        content = content.replace('href="/admin"', 'href="admin.html"')
        content = content.replace('href="/about"', 'href="about.html"')
        content = content.replace('href="/logout"', 'href="#"')
        
        # Fix 2: Apply role-based visibility (CFO only sees Reports/Export/Admin)
        # Remove Reports, Export, Admin links for non-CFO users (GitHub Pages shows CFO by default)
        # Since we're simulating CFO user, these should stay visible
        
        # Fix 3: Add proper active classes based on filename
        current_file = html_file.name
        
        # First, remove all existing active classes to prevent duplicates
        content = re.sub(r'\s*class="active"[^>]*>', '', content)
        content = re.sub(r'href="[^"]*"([^>]*)class="active"', r'href="\1"', content)
        
        if current_file == 'index.html':
            content = re.sub(r'<li><a href="index\.html"([^>]*)>', r'<li><a href="index.html" class="active"\1>', content)
        elif current_file == 'upload.html':
            content = re.sub(r'<li><a href="upload\.html"([^>]*)>', r'<li><a href="upload.html" class="active"\1>', content)
        elif current_file == 'reports.html':
            content = re.sub(r'<li><a href="reports\.html"([^>]*)>', r'<li><a href="reports.html" class="active"\1>', content)
        elif current_file == 'export.html':
            content = re.sub(r'<li><a href="export\.html"([^>]*)>', r'<li><a href="export.html" class="active"\1>', content)
        elif current_file == 'admin.html':
            content = re.sub(r'<li><a href="admin\.html"([^>]*)>', r'<li><a href="admin.html" class="active"\1>', content)
        elif current_file == 'about.html':
            content = re.sub(r'<li><a href="about\.html"([^>]*)>', r'<li><a href="about.html" class="active"\1>', content)
        
        # Fix 4: Replace role description function calls
        content = content.replace('{{ get_role_description(current_user.role) }}', 'Chief Financial Officer')
        
        # Fix 5: Remove leftover template tags and clean up
        content = content.replace('{% else %}', '')
        content = content.replace('{% endif %}', '')
        content = content.replace('href="/login"', 'href="login.html"')
        
        # Remove auth menu since we have user menu
        content = re.sub(r'\s*<div class="auth-menu">\s*<a href="[^"]*"[^>]*>[^<]*</a>\s*</div>', '', content)
        
        content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
        
        # Write back
        html_file.write_text(content, encoding='utf-8')
    
    print("✅ All UI issues fixed!")

if __name__ == '__main__':
    fix_navbar_issues()
