#!/usr/bin/env python3
"""
Complete UI parity fix for Flask vs GitHub Pages
Ensures identical layout, styling, and navigation
"""

import re
from pathlib import Path

def fix_ui_parity():
    """Fix all layout, styling, and navigation differences"""
    docs_dir = Path('docs')
    templates_dir = Path('templates')
    
    print("=== Fixing UI Parity Issues ===")
    
    # Fix each HTML file to match Flask templates exactly
    for html_file in docs_dir.glob('*.html'):
        if html_file.name in ['auth-debug.html', 'auth-test-simple.html', 'auth-test.html', 
                             'complete-auth-test.html', 'debug.html', 'js-test.html', 
                             'navigation-test.html', 'simple-index.html']:
            continue  # Skip test files
            
        print(f"Fixing: {html_file.name}")
        
        # Find corresponding Flask template
        flask_template = templates_dir / html_file.name
        if not flask_template.exists():
            print(f"  No Flask template found for {html_file.name}")
            continue
            
        # Read Flask template
        flask_content = flask_template.read_text(encoding='utf-8')
        
        # Process Flask template to create identical GitHub Pages version
        github_content = process_template_inheritance(flask_content, html_file.name)
        
        # Write to docs
        html_file.write_text(github_content, encoding='utf-8')
    
    print("=== UI Parity Fixed ===")

def process_flask_template(content, filename):
    """Process Flask template to create identical GitHub Pages version"""
    
    # Check if template extends another template
    extends_match = re.search(r'\{%\s*extends\s+[\'"]([^\'"]+)[\'"]\s*%\}', content)
    if extends_match:
        # Get the parent template
        parent_template = extends_match.group(1)
        parent_path = Path('templates') / f"{parent_template}.html"
        
        if parent_path.exists():
            parent_content = parent_path.read_text(encoding='utf-8')
            
            # Extract blocks from child template
            content_blocks = {}
            for block_match in re.finditer(r'\{%\s*block\s+(\w+)\s*%\}(.*?)\{%\s*endblock\s*%\}', content, re.DOTALL):
                block_name = block_match.group(1)
                block_content = block_match.group(2).strip()
                content_blocks[block_name] = block_content
            
            # Replace blocks in parent template
            processed_parent = parent_content
            for block_name, block_content in content_blocks.items():
                processed_parent = re.sub(
                    rf'\{{%\s*block\s+{re.escape(block_name)}\s*%}}.*?\{{%\s*endblock\s*%}}',
                    block_content,
                    processed_parent,
                    flags=re.DOTALL
                )
            
            # Process the final content (this will handle includes, URLs, etc.)
            return process_template_content(processed_parent, filename)
    
    # If no extends, process as regular template
    return process_template_content(content, filename)

def process_template_content(content, filename):
    """Process template content after inheritance is resolved"""
    
    # Step 1: Process template logic
    content = process_template_logic(content, filename)
    
    # Step 2: Process variables
    content = process_variables(content)
    
    # Step 3: Process URLs
    content = process_urls(content)
    
    # Step 4: Process includes
    content = process_includes(content)
    
    # Step 5: Clean up any remaining template tags
    content = re.sub(r'\{%\s*[^%]*%\}', '', content)
    
    return content

def process_template_inheritance(content, filename):
    """Handle template inheritance"""
    
    # Get base template content first
    base_template = Path('templates/base.html')
    if base_template.exists():
        base_content = base_template.read_text(encoding='utf-8')
        
        # Process base template URLs first
        base_content = process_urls(base_content)
        
        # Process base template includes
        base_content = process_includes(base_content)
        
        # Process base template logic
        base_content = process_template_logic(base_content, filename)
        
        # Process base template variables
        base_content = process_variables(base_content)
        
        # Extract blocks from content
        title_block = extract_block(content, 'title')
        content_block = extract_block(content, 'content')
        extra_css_block = extract_block(content, 'extra_css')
        extra_js_block = extract_block(content, 'extra_js')
        
        # Build complete HTML
        html = base_content
        
        # Replace blocks
        html = html.replace('{% block title %}SADPMR Financial Reporting System{% endblock %}', 
                          title_block or 'SADPMR Financial Reporting System')
        html = html.replace('{% block extra_css %}{% endblock %}', extra_css_block or '')
        html = html.replace('{% block content %}{% endblock %}', content_block or '')
        html = html.replace('{% block extra_js %}{% endblock %}', extra_js_block or '')
        
        # Process active states based on current filename
        html = fix_navigation_active_states(html, filename)
        
        # Process any remaining template logic in the final HTML
        html = process_template_logic(html, filename)
        
        # Process any remaining variables in the final HTML
        html = process_variables(html)
        
        # Process any remaining URLs in the final HTML
        html = process_urls(html)
        
        # Clean up any remaining template tags
        html = re.sub(r'\{%\s*[^%]*%\}', '', html)
        html = re.sub(r'\{\{\s*[^}]*\}\}', '', html)
        
        return html
    
    return content

def fix_navigation_active_states(content, filename):
    """Fix navigation active states based on current page"""
    
    # Remove all existing active classes first
    content = re.sub(r'\s*class="active"', '', content)
    
    # Add active class based on filename
    page_mappings = {
        'index.html': 'Dashboard',
        'upload.html': 'Upload Trial Balance',
        'reports.html': 'Reports',
        'export.html': 'Export',
        'admin.html': 'Admin',
        'about.html': 'About'
    }
    
    current_page = page_mappings.get(filename, '')
    if current_page:
        # Find the navigation link for current page and add active class
        pattern = rf'(<li><a href="[^"]*"[^>]*>)({re.escape(current_page)})(</a></li>)'
        content = re.sub(pattern, rf'\1 class="active">\2\3', content)
    
    return content

def extract_block(content, block_name):
    """Extract content from a block"""
    pattern = rf'\{{%\s*block\s*{block_name}\s*%\}}(.*?)\{{%\s*endblock\s*%\}}'
    match = re.search(pattern, content, re.DOTALL)
    return match.group(1).strip() if match else ''

def process_template_logic(content, filename):
    """Process Flask template logic"""
    
    # Mock user data
    mock_user = {
        'full_name': 'Sarah Nkosi',
        'role': 'CFO',
        'role_lower': 'cfo',
        'can_upload': True
    }
    
    # Process nested if/else blocks from inside out
    # First process current_user.can_upload() blocks
    content = re.sub(
        r'\{%\s*if\s+current_user\.can_upload\(\)\s*%\}(.*?)\{%\s*else\s*%\}(.*?)\{%\s*endif\s*%\}',
        lambda m: m.group(1) if mock_user['can_upload'] else m.group(2),
        content,
        flags=re.DOTALL
    )
    
    # Then process current_user blocks (the outer ones)
    content = re.sub(
        r'\{%\s*if\s+current_user\s*%\}(.*?)\{%\s*else\s*%\}(.*?)\{%\s*endif\s*%\}',
        lambda m: m.group(1) if mock_user else m.group(2),
        content,
        flags=re.DOTALL
    )
    
    # Process current_user.role == 'CFO' logic
    content = re.sub(
        r'\{%\s*if\s+current_user\.role\s*==\s*[\'"]CFO[\'"]\s*%\}(.*?)\{%\s*endif\s*%\}',
        lambda m: m.group(1) if mock_user['role'] == 'CFO' else '',
        content,
        flags=re.DOTALL
    )
    
    # Clean up any remaining template tags
    content = re.sub(r'\{%\s*else\s*%\}', '', content)
    content = re.sub(r'\{%\s*endif\s*%\}', '', content)
    content = re.sub(r'\{%\s*if.*?%\}', '', content)
    
    return content

def process_variables(content):
    """Process Flask variables"""
    
    # Mock data
    mock_data = {
        'current_user.full_name': 'Sarah Nkosi',
        'current_user.role': 'CFO',
        'get_role_description(current_user.role)': 'Chief Financial Officer',
        'current_user.role.lower()': 'cfo'
    }
    
    # Replace variables
    for var, value in mock_data.items():
        content = content.replace('{{ ' + var + ' }}', value)
        content = content.replace('{{' + var + '}}', value)
    
    return content

def process_urls(content):
    """Process Flask URLs"""
    
    # URL mappings
    url_mappings = {
        '/': 'index.html',
        '/upload': 'upload.html',
        '/reports': 'reports.html',
        '/export': 'export.html',
        '/admin': 'admin.html',
        '/about': 'about.html',
        '/login': 'login.html',
        '/logout': '#'
    }
    
    # Replace Flask routes with static HTML files
    for flask_url, static_url in url_mappings.items():
        # Handle href attributes
        content = re.sub(
            rf'href=["\']({re.escape(flask_url)})["\']',
            f'href="{static_url}"',
            content
        )
    
    # Replace url_for calls with static filename parameter
    content = re.sub(
        r'\{\{\s*url_for\(\s*[\'"]static[\'"]\s*,\s*filename\s*=\s*[\'"]([^\'"]*)[\'"]\s*\)\s*\}\}',
        r'../\1',
        content
    )
    
    # Handle any remaining simple url_for patterns
    content = re.sub(
        r'\{\{\s*url_for\([\'"]([^\'"]*)[\'"]\)\s*\}\}',
        r'\1.html',
        content
    )
    
    return content

def process_includes(content):
    """Process template includes"""
    
    # Process navbar include
    navbar_file = Path('templates/components/navbar.html')
    if navbar_file.exists() and '{% include \'components/navbar.html\' %}' in content:
        navbar_content = navbar_file.read_text(encoding='utf-8')
        
        # Process navbar content
        navbar_content = process_template_logic(navbar_content, 'navbar')
        navbar_content = process_variables(navbar_content)
        navbar_content = process_urls(navbar_content)
        
        # Remove Flask active state logic from navbar
        navbar_content = re.sub(r'\{%\s*if\s+request\.endpoint\s*==\s*[\'"][^\'"]*[\'"]\s*%\}class="active"\{%\s*endif\s*%\}', '', navbar_content)
        
        content = content.replace('{% include \'components/navbar.html\' %}', navbar_content)
    
    return content

if __name__ == '__main__':
    fix_ui_parity()
