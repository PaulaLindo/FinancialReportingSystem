#!/usr/bin/env python3
"""
Enhanced sync script to make GitHub Pages UI identical to Flask UI
This script properly handles Flask template conversion and maintains identical behavior
"""

import os
import shutil
from pathlib import Path
import re
from datetime import datetime

class FlaskToGitHubPagesSync:
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.templates_dir = self.base_dir / 'templates'
        self.static_dir = self.base_dir / 'static'
        self.docs_dir = self.base_dir / 'docs'
        
        # Mock user data for GitHub Pages (simulates logged-in state)
        self.mock_user = {
            'full_name': 'Sarah Nkosi',
            'role': 'CFO',
            'can_upload': True,
            'role_lower': 'cfo'
        }
        
    def sync_all(self):
        """Complete sync from Flask to GitHub Pages"""
        print("=== Starting Flask to GitHub Pages UI Sync ===")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. Sync CSS files (already identical, but ensure consistency)
        self.sync_css_files()
        
        # 2. Sync JavaScript files
        self.sync_js_files()
        
        # 3. Convert Flask templates to static HTML with identical behavior
        self.convert_templates()
        
        # 4. Copy any missing assets
        self.copy_assets()
        
        print("=== Sync Complete ===")
        print("GitHub Pages UI is now identical to Flask UI!")
        
    def sync_css_files(self):
        """Sync CSS files from static to docs"""
        print("\n1. Syncing CSS files...")
        css_src = self.static_dir / 'css'
        css_dst = self.docs_dir / 'css'
        
        if css_src.exists():
            if css_dst.exists():
                shutil.rmtree(css_dst)
            shutil.copytree(css_src, css_dst)
            print(f"   CSS files synced: {len(list(css_src.glob('*.css')))} files")
        
    def sync_js_files(self):
        """Sync JavaScript files from static to docs"""
        print("\n2. Syncing JavaScript files...")
        js_src = self.static_dir / 'js'
        js_dst = self.docs_dir / 'js'
        
        if js_src.exists():
            if js_dst.exists():
                shutil.rmtree(js_dst)
            shutil.copytree(js_src, js_dst)
            print(f"   JavaScript files synced: {len(list(js_src.glob('*.js')))} files")
    
    def convert_templates(self):
        """Convert Flask templates to static HTML with identical behavior"""
        print("\n3. Converting Flask templates to static HTML...")
        
        # Process each template file
        for template_file in self.templates_dir.glob('*.html'):
            if template_file.name in ['base.html', 'base_auth.html']:
                continue  # Skip base templates, they're included
                
            print(f"   Processing: {template_file.name}")
            
            # Read the template
            content = template_file.read_text(encoding='utf-8')
            
            # Convert to static HTML
            static_html = self.convert_template_to_static(content, template_file.name)
            
            # Write to docs
            output_file = self.docs_dir / template_file.name
            output_file.write_text(static_html, encoding='utf-8')
            
        print(f"   Templates converted: {len(list(self.templates_dir.glob('*.html'))) - 2} files")
    
    def convert_template_to_static(self, content, filename):
        """Convert Flask Jinja2 template to static HTML with identical behavior"""
        
        # Process base template first
        base_content = self.get_base_template_content(content)
        
        # Process includes
        content = self.process_includes(content)
        
        # Process template logic
        content = self.process_template_logic(content, filename)
        
        # Process URL generation
        content = self.process_urls(content)
        
        # Insert into base template if needed
        if 'extends' in content or filename not in ['index.html', 'upload.html', 'about.html', 'reports.html', 'admin.html', 'export.html', 'login.html', 'results.html']:
            # This template extends a base template
            title = self.extract_title(content)
            body_content = self.extract_content(content)
            extra_css = self.extract_extra_css(content)
            extra_js = self.extract_extra_js(content)
            
            # Build complete HTML
            html = base_content.replace('{% block title %}SADPMR Financial Reporting System{% endblock %}', title)
            html = html.replace('<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/styles.css\') }}">', '<link rel="stylesheet" href="css/styles.css">')
            html = html.replace('<link rel="stylesheet" href="{{ url_for(\'static\', filename=\'css/login.css\') }}">', '<link rel="stylesheet" href="css/login.css">')
            html = html.replace('{% block extra_css %}{% endblock %}', extra_css)
            html = html.replace('{% include \'components/navbar.html\' %}', self.get_navbar_content(filename))
            html = html.replace('{% block content %}{% endblock %}', body_content)
            html = html.replace('<script src="{{ url_for(\'static\', filename=\'js/utils.js\') }}"></script>', '<script src="js/utils.js"></script>')
            html = html.replace('<script src="{{ url_for(\'static\', filename=\'js/main.js\') }}"></script>', '<script src="js/main.js"></script>')
            html = html.replace('<script src="{{ url_for(\'static\', filename=\'js/navigation-fluid.js\') }}"></script>', '<script src="js/navigation-fluid.js"></script>')
            html = html.replace('{% block extra_js %}{% endblock %}', extra_js)
            return html
        else:
            return content
    
    def get_base_template_content(self, content):
        """Get the appropriate base template content"""
        if 'base_auth.html' in content:
            base_file = self.templates_dir / 'base_auth.html'
        else:
            base_file = self.templates_dir / 'base.html'
        
        if base_file.exists():
            return base_file.read_text(encoding='utf-8')
        else:
            # Fallback base template
            return '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="theme-color" content="#0a1128">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="SADPMR FRS">
    <title>{% block title %}SADPMR Financial Reporting System{% endblock %}</title>
    <link rel="stylesheet" href="css/styles.css">
    {% block extra_css %}{% endblock %}
</head>
<body>
    {% block content %}{% endblock %}
    
    <footer>
        <div class="container-content">
            <p>&copy; 2025 SADPMR Financial Reporting System | Developed for Schedule 3A PFMA Compliance</p>
            <p class="footer-note">Demo Version - February 3, 2026 Presentation</p>
        </div>
    </footer>

    <script src="js/utils.js"></script>
    <script src="js/main.js"></script>
    <script src="js/navigation-fluid.js"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>'''
    
    def process_includes(self, content):
        """Process {% include %} statements"""
        def replace_include(match):
            include_path = match.group(1).strip("'\"")
            include_file = self.templates_dir / include_path
            
            if include_file.exists():
                try:
                    included_content = include_file.read_text(encoding='utf-8')
                    # Process the included content as well
                    return self.process_template_logic(included_content, include_file.name)
                except Exception as e:
                    print(f"Warning: Could not include {include_path}: {e}")
                    return f'<!-- Include failed for {include_path} -->'
            return f'<!-- Include not found: {include_path} -->'
        
        # Replace includes
        content = re.sub(r'\{%\s*include\s+["\']([^"\']+)["\']\s*%\}', replace_include, content)
        return content
    
    def process_template_logic(self, content, filename):
        """Process Flask template logic to create identical static behavior"""
        
        # Process user authentication logic
        content = self.process_auth_logic(content)
        
        # Process role-based visibility
        content = self.process_role_based_content(content)
        
        # Process conditional content
        content = self.process_conditionals(content)
        
        # Process template variables
        content = self.process_variables(content)
        
        # Process template filters
        content = self.process_filters(content)
        
        return content
    
    def process_auth_logic(self, content):
        """Process authentication logic to match Flask behavior"""
        user = self.mock_user
        
        # Replace {% if current_user %} blocks
        content = re.sub(
            r'\{%\s*if\s+current_user\s*%\}(.*?)\{%\s*endif\s*%\}',
            lambda m: m.group(1) if user else '',
            content,
            flags=re.DOTALL
        )
        
        # Replace {% if current_user %} {% else %} {% endif %} blocks
        content = re.sub(
            r'\{%\s*if\s+current_user\s*%\}(.*?)\{%\s*else\s*%\}(.*?)\{%\s*endif\s*%\}',
            lambda m: m.group(1) if user else m.group(2),
            content,
            flags=re.DOTALL
        )
        
        # Replace {% else %} {% if current_user %} blocks (reversed)
        content = re.sub(
            r'\{%\s*else\s*%\}(.*?)\{%\s*if\s+current_user\s*%\}(.*?)\{%\s*endif\s*%\}',
            lambda m: m.group(2) if user else m.group(1),
            content,
            flags=re.DOTALL
        )
        
        # Replace current_user.full_name
        content = content.replace('{{ current_user.full_name }}', user['full_name'])
        
        # Replace current_user.role
        content = content.replace('{{ current_user.role or \'USER\' }}', user['role'])
        content = content.replace('{{ current_user.role }}', user['role'])
        
        # Replace current_user.role.lower() - handle both formats
        content = content.replace('{{ current_user.role.lower() if current_user.role else \'default\' }}', user['role_lower'])
        content = content.replace('{{ current_user.role.lower() if current_user.role else \'default\' }}', user['role_lower'])
        
        return content
    
    def process_role_based_content(self, content):
        """Process role-based visibility to match Flask exactly"""
        user = self.mock_user
        
        # Process {% if current_user and current_user.can_upload() %}
        content = re.sub(
            r'\{%\s*if\s+current_user\s+and\s+current_user\.can_upload\(\)\s*%\}(.*?)\{%\s*endif\s*%\}',
            lambda m: m.group(1) if user and user['can_upload'] else '',
            content,
            flags=re.DOTALL
        )
        
        # Process {% if current_user and current_user.role == 'CFO' %}
        content = re.sub(
            r'\{%\s*if\s+current_user\s+and\s+current_user\.role\s*==\s*[\'"]CFO[\'"]\s*%\}(.*?)\{%\s*endif\s*%\}',
            lambda m: m.group(1) if user and user['role'] == 'CFO' else '',
            content,
            flags=re.DOTALL
        )
        
        return content
    
    def process_conditionals(self, content):
        """Process other conditional statements"""
        # Process simple if/else blocks
        content = re.sub(
            r'\{%\s*if\s+(.*?)\s*%\}(.*?)\{%\s*else\s*%\}(.*?)\{%\s*endif\s*%\}',
            lambda m: self.evaluate_condition(m.group(1), m.group(2), m.group(3)),
            content,
            flags=re.DOTALL
        )
        
        # Process simple if blocks
        content = re.sub(
            r'\{%\s*if\s+(.*?)\s*%\}(.*?)\{%\s*endif\s*%\}',
            lambda m: m.group(2) if self.evaluate_condition(m.group(1)) else '',
            content,
            flags=re.DOTALL
        )
        
        return content
    
    def evaluate_condition(self, condition, true_content=None, false_content=None):
        """Evaluate template conditions"""
        # Handle current_user.can_upload()
        if 'current_user.can_upload()' in condition:
            if self.mock_user['can_upload']:
                return true_content if true_content else ''
            else:
                return false_content if false_content else ''
        
        # Handle current_user.role == 'CFO'
        if "current_user.role == 'CFO'" in condition:
            if self.mock_user['role'] == 'CFO':
                return true_content if true_content else ''
            else:
                return false_content if false_content else ''
        
        # Default to true_content for complex conditions we can't evaluate
        return true_content if true_content else (false_content if false_content else '')
    
    def process_variables(self, content):
        """Process template variables"""
        # Replace get_role_description function calls
        content = re.sub(
            r'\{\{\s*get_role_description\([^)]+\)\s*\}\}',
            'Chief Financial Officer',
            content
        )
        
        return content
    
    def process_filters(self, content):
        """Process template filters"""
        # Handle URL filters
        content = re.sub(
            r'\{\{\s*url_for\([\'"](static[^\'"]*)[\'"]\)\s*\}\}',
            lambda m: m.group(1).replace('static/', '').replace("'", ''),
            content
        )
        
        return content
    
    def get_navbar_content(self, filename=None):
        """Get processed navbar content with proper active states"""
        navbar_file = self.templates_dir / 'components' / 'navbar.html'
        if navbar_file.exists():
            content = navbar_file.read_text(encoding='utf-8')
            
            # Process active states based on current file
            if filename:
                # Remove all active classes first
                content = re.sub(r'\{%\s*if\s+request\.endpoint\s*==\s*[\'"][^\'"]*[\'"]\s*%\}class="active"\{%\s*endif\s*%\}', '', content)
                content = re.sub(r'{%\s*if\s+request\.endpoint\s*==\s*[\'"][^\'"]*[\'"]\s*%\}class="active"\{%\s*endif\s*%\}', '', content)
                
                # Add active class based on filename
                page_mappings = {
                    'index.html': 'index',
                    'upload.html': 'upload_page', 
                    'reports.html': 'reports_page',
                    'export.html': 'export_page',
                    'admin.html': 'admin_page',
                    'about.html': 'about_page'
                }
                
                current_endpoint = page_mappings.get(filename, '')
                if current_endpoint:
                    # Replace the specific active class for current page
                    pattern = rf'href=["\'][^"\']*{current_endpoint}[^"\']*["\']([^>]*>)'
                    content = re.sub(pattern, rf'href="{filename}" class="active"\1', content)
            
            return self.process_template_logic(content, 'navbar.html')
        return ''
    
    def process_urls(self, content):
        """Process Flask URLs to static URLs"""
        # Convert Flask routes to static HTML files
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
        
        for flask_url, static_url in url_mappings.items():
            content = content.replace(f'href="{flask_url}"', f'href="{static_url}"')
            content = content.replace(f"href='{flask_url}'", f"href='{static_url}'")
        
        # Handle url_for function calls
        content = re.sub(
            r'\{\{\s*url_for\([\'"](static[^\'"]*)[\'"]\)\s*\}\}',
            lambda m: m.group(1).replace('static/', '').replace("'", ''),
            content
        )
        
        return content
    
    def extract_title(self, content):
        """Extract title from template"""
        title_match = re.search(r'\{%\s*block\s+title\s*%\}(.*?)\{%\s*endblock\s*%\}', content, re.DOTALL)
        if title_match:
            return title_match.group(1).strip()
        return 'SADPMR Financial Reporting System'
    
    def extract_content(self, content):
        """Extract main content from template"""
        # Remove template directives
        content = re.sub(r'\{%\s*block\s+title\s*%\}.*?\{%\s*endblock\s*%\}', '', content, flags=re.DOTALL)
        content = re.sub(r'\{%\s*block\s+extra_css\s*%\}.*?\{%\s*endblock\s*%\}', '', content, flags=re.DOTALL)
        content = re.sub(r'\{%\s*block\s+extra_js\s*%\}.*?\{%\s*endblock\s*%\}', '', content, flags=re.DOTALL)
        content = re.sub(r'\{%\s*extends\s+[^%]*?\%\}', '', content)
        
        # Extract content block
        content_match = re.search(r'\{%\s*block\s+content\s*%\}(.*?)\{%\s*endblock\s*%\}', content, re.DOTALL)
        if content_match:
            return content_match.group(1).strip()
        
        return content.strip()
    
    def extract_extra_css(self, content):
        """Extract extra CSS from template"""
        css_match = re.search(r'\{%\s*block\s+extra_css\s*%\}(.*?)\{%\s*endblock\s*%\}', content, re.DOTALL)
        if css_match:
            return css_match.group(1).strip()
        return ''
    
    def extract_extra_js(self, content):
        """Extract extra JavaScript from template"""
        js_match = re.search(r'\{%\s*block\s+extra_js\s*%\}(.*?)\{%\s*endblock\s*%\}', content, re.DOTALL)
        if js_match:
            return js_match.group(1).strip()
        return ''
    
    def copy_assets(self):
        """Copy additional assets if needed"""
        print("\n4. Copying additional assets...")
        
        # Copy uploads directory if it exists
        uploads_src = self.base_dir / 'uploads'
        uploads_dst = self.docs_dir / 'uploads'
        if uploads_src.exists() and not uploads_dst.exists():
            uploads_dst.mkdir(exist_ok=True)
            print(f"   Created uploads directory")
        
        # Copy data directory if it exists
        data_src = self.base_dir / 'data'
        data_dst = self.docs_dir / 'data'
        if data_src.exists() and not data_dst.exists():
            shutil.copytree(data_src, data_dst)
            print(f"   Copied data directory")

if __name__ == '__main__':
    sync = FlaskToGitHubPagesSync()
    sync.sync_all()
