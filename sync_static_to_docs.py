#!/usr/bin/env python3
"""
Sync assets and templates from source folders to docs/ folder for GitHub Pages
Since GitHub Pages can't serve from static/, we need to copy assets to docs/
"""

import os
import shutil
from pathlib import Path
import re

def convert_template_to_static(template_content, filename, templates_dir=None):
    """
    Convert Flask Jinja2 template to static HTML
    Removes template tags and converts URLs for static use
    """
    content = template_content
    
    # First, check if this is a base template that extends another
    # For these, we'll build a complete HTML document
    is_extending = 'extends' in content
    
    # If extending, we need to process the base template first
    if is_extending and templates_dir:
        # Extract the base template name
        extends_match = re.search(r'\{%\s+extends\s+["\']([^"\']+)["\']\s+%\}', content)
        if extends_match:
            base_template_name = extends_match.group(1)
            base_template_path = templates_dir / base_template_name
            
            if base_template_path.exists():
                try:
                    # Read the base template
                    base_content = base_template_path.read_text(encoding='utf-8')
                    
                    # Handle includes in the base template first
                    def replace_include(match):
                        include_path = match.group(1).strip("'\"")
                        include_file = templates_dir / include_path
                        if include_file.exists():
                            try:
                                included_content = include_file.read_text(encoding='utf-8')
                                # Convert the included content
                                return convert_template_to_static(included_content, include_file.name, templates_dir)
                            except Exception as e:
                                print(f"Warning: Could not include {include_path}: {e}")
                                return f'<!-- Include failed for {include_path} -->'
                        return f'<!-- Include not found: {include_path} -->'
                    
                    # Replace includes in base template
                    base_content = re.sub(r'\{%\s+include\s+["\']([^"\']+)["\']\s+%\}', replace_include, base_content)
                    
                    # Extract blocks from the child template
                    content_blocks = {}
                    for block_match in re.finditer(r'\{%\s+block\s+(\w+)\s*%\}(.*?)\{%\s+endblock\s*%\}', content, re.DOTALL):
                        block_name = block_match.group(1)
                        block_content = block_match.group(2)
                        content_blocks[block_name] = block_content
                    
                    # Replace blocks in base template with child content
                    for block_name, block_content in content_blocks.items():
                        base_content = re.sub(
                            r'\{%\s+block\s+' + block_name + r'\s*%\}.*?\{%\s+endblock\s*%\}',
                            block_content,
                            base_content,
                            flags=re.DOTALL
                        )
                    
                    # Use the processed base content as our content
                    content = base_content
                    
                except Exception as e:
                    print(f"Warning: Could not process base template {base_template_name}: {e}")
    
    # Remove extends statement (if any)
    content = re.sub(r'\{%\s+extends\s+["\'].*?["\']\s+%\}\n*', '', content)
    
    # Extract title from block content if present
    title_match = re.search(r'\{%\s+block\s+title\s*%\}(.*?)\{%\s+endblock\s*%\}', content, re.DOTALL)
    title = "Dashboard - SADPMR Financial Reporting System"
    if title_match:
        title = title_match.group(1).strip()
    
    # Remove all block statement markers
    content = re.sub(r'\{%\s+block\s+\w+\s*%\}\n*', '', content)
    content = re.sub(r'\{%\s+endblock\s*%\}\n*', '', content)
    content = re.sub(r'\{%\s+endif\s*%\}\n*', '', content)
    content = re.sub(r'\{%\s+endfor\s*%\}\n*', '', content)
    
    # Remove content blocks we want to exclude
    content = re.sub(r'\{%\s+extra_(js|css)\s+%\}.*?\{%\s+endblock\s+%\}', '', content, flags=re.DOTALL)
    
    # Remove if/for blocks while keeping their body content
    content = re.sub(r'\{%\s+if\s+[^%]*?%\}(.*?)\{%\s+elif[^%]*?%\}.*?\{%\s+endif\s*%\}', 
                     r'\1', content, flags=re.DOTALL)
    content = re.sub(r'\{%\s+if\s+[^%]*?%\}(.*?)\{%\s+else\s+%\}.*?\{%\s+endif\s*%\}', 
                     r'\1', content, flags=re.DOTALL)
    content = re.sub(r'\{%\s+if\s+[^%]*?%\}(.*?)\{%\s+endif\s*%\}', 
                     r'\1', content, flags=re.DOTALL)
    content = re.sub(r'\{%\s+for\s+[^%]*?%\}(.*?)\{%\s+endfor\s*%\}', 
                     r'\1', content, flags=re.DOTALL)
    
    # Convert Flask url_for to static paths
    content = re.sub(r"\{\{\s*url_for\('static',\s*filename='([^']+)'\)\s*\}\}", 
                     r'\1', content)
    
    # Replace template variables with demo content
    content = re.sub(r"\{\{\s*current_user\.full_name\s*\}\}", "Sarah Nkosi", content)
    content = re.sub(r"\{\{\s*current_user\.role\s*\}\}", "CFO", content)
    content = re.sub(r"\{\{\s*get_role_description\([^)]*\)\s*\}\}", 
                     "Chief Financial Officer - Full system access", content)
    content = re.sub(r"\{\{\s*get_role_color\([^)]*\)\s*\}\}", "#d4a574", content)
    content = re.sub(r"\{\{\s*request\.endpoint\s*\}\}", "dashboard", content)
    
    # Handle Flask routes to .html files
    content = re.sub(r'href="/"', 'href="index.html"', content)
    content = re.sub(r'href="/([a-z_-]+)"', r'href="\1.html"', content)
    content = re.sub(r"href='/([a-z_-]+)'", r"href='\1.html'", content)
    content = re.sub(r"href='/'", "href='index.html'", content)
    
    # Handle form submissions - convert POST forms to JavaScript handlers
    content = re.sub(
        r'<form[^>]*method="POST"[^>]*action="([^"]*)"[^>]*>',
        lambda m: f'<form onsubmit="handleLoginForm(event, \'{m.group(1)}\')" method="GET">',
        content
    )
    content = re.sub(
        r'<form[^>]*method="POST"[^>]*>',
        '<form onsubmit="handleLoginForm(event, \'index.html\')" method="GET">',
        content
    )
    
    # Handle Flask url_for calls with parameters
    content = re.sub(r"\{\{\s*url_for\('([a-z_]+)'[^}]*\)\s*\}\}", 
                     lambda m: f'{m.group(1)}.html', content)
    
    # Remove remaining template tags
    content = re.sub(r'\{%[^%]*%\}', '', content)
    content = re.sub(r'\{\{[^}]*\}\}', '', content)
    
    # Clean up any extra whitespace
    content = re.sub(r'\n\s*\n\s*\n', '\n\n', content)
    
    # Build complete HTML if extending from base template
    if is_extending:
        # Check for a complete HTML structure
        if not content.strip().startswith('<!DOCTYPE'):
            # Add login handler script to head section
            login_script = """
    <script>
        function handleLoginForm(event, redirectUrl) {
            event.preventDefault();
            
            // Simple demo login validation
            const username = document.getElementById('username')?.value || '';
            const password = document.getElementById('password')?.value || '';
            
            // Demo credentials
            const demoUsers = {
                'cfo@sadpmr.gov.za': { role: 'CFO', name: 'Sarah Nkosi', redirect: 'index.html' },
                'accountant@sadpmr.gov.za': { role: 'Accountant', name: 'John Smith', redirect: 'index.html' },
                'clerk@sadpmr.gov.za': { role: 'Clerk', name: 'Mike Davis', redirect: 'index.html' },
                'auditor@agsa.gov.za': { role: 'Auditor', name: 'Patience Moyo', redirect: 'index.html' }
            };
            
            if (demoUsers[username] && password === 'demo123') {
                // Store user info in sessionStorage for demo
                const user = demoUsers[username];
                sessionStorage.setItem('demoUser', JSON.stringify(user));
                
                // Redirect to dashboard
                window.location.href = user.redirect || redirectUrl || 'index.html';
            } else {
                // Show error message
                alert('Invalid credentials. Use demo credentials shown below.');
            }
        }
    </script>"""
            
            # Wrap the content in a proper HTML structure
            html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="theme-color" content="#0a1128">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="SADPMR FRS">
    <title>{title}</title>
    <link rel="stylesheet" href="css/styles.css">{login_script}
</head>
<body>
{content}
    <script src="js/utils.js"></script>
    <script src="js/main.js"></script>
    <script src="js/mobile-menu.js"></script>
</body>
</html>"""
            return html
    
    return content

def sync_static_to_docs():
    """Synchronize static assets and templates from source to docs/"""
    
    # Get the project root
    script_dir = Path(__file__).parent.absolute()
    
    static_css = script_dir / 'static' / 'css'
    static_js = script_dir / 'static' / 'js'
    templates_dir = script_dir / 'templates'
    docs_css = script_dir / 'docs' / 'css'
    docs_js = script_dir / 'docs' / 'js'
    docs_dir = script_dir / 'docs'
    
    def sync_directory(src, dest, dest_name):
        """Sync a directory from src to dest"""
        if not src.exists():
            print(f"❌ Source directory not found: {src}")
            return False
        
        # Create destination if it doesn't exist
        dest.mkdir(parents=True, exist_ok=True)
        
        # Copy all files
        copied = 0
        for src_file in src.glob('*'):
            if src_file.is_file():
                dest_file = dest / src_file.name
                try:
                    shutil.copy2(src_file, dest_file)
                    copied += 1
                    print(f"✓ Copied: {src_file.name}")
                except Exception as e:
                    print(f"✗ Failed to copy {src_file.name}: {e}")
                    return False
        
        print(f"\n✓ Synced {copied} files to {dest_name}/")
        return True
    
    def sync_templates():
        """Sync HTML templates from templates/ to docs/"""
        if not templates_dir.exists():
            print(f"❌ Templates directory not found: {templates_dir}")
            return False
        
        copied = 0
        for template_file in templates_dir.glob('*.html'):
            # Skip base templates - only copy end-user pages
            if template_file.name.startswith('base'):
                continue
                
            dest_file = docs_dir / template_file.name
            try:
                # Read template content and convert to static HTML
                template_content = template_file.read_text(encoding='utf-8')
                static_content = convert_template_to_static(template_content, template_file.name, templates_dir)
                
                # Add JavaScript form handler to all pages (especially login)
                if 'handleLoginForm' not in static_content:
                    # Insert the login handler script before closing head tag
                    login_script = """
    <script>
        function handleLoginForm(event, redirectUrl) {
            event.preventDefault();
            
            // Simple demo login validation
            const username = document.getElementById('username')?.value || '';
            const password = document.getElementById('password')?.value || '';
            
            // Demo credentials
            const demoUsers = {
                'cfo@sadpmr.gov.za': { role: 'CFO', name: 'Sarah Nkosi', redirect: 'index.html' },
                'accountant@sadpmr.gov.za': { role: 'Accountant', name: 'John Smith', redirect: 'index.html' },
                'clerk@sadpmr.gov.za': { role: 'Clerk', name: 'Mike Davis', redirect: 'index.html' },
                'auditor@agsa.gov.za': { role: 'Auditor', name: 'Patience Moyo', redirect: 'index.html' }
            };
            
            if (demoUsers[username] && password === 'demo123') {
                // Store user info in sessionStorage for demo
                const user = demoUsers[username];
                sessionStorage.setItem('demoUser', JSON.stringify(user));
                
                // Redirect to dashboard
                window.location.href = user.redirect || redirectUrl || 'index.html';
            } else {
                // Show error message
                alert('Invalid credentials. Use demo credentials shown below.');
            }
        }
    </script>"""
                    
                    # Insert before closing head tag
                    static_content = static_content.replace('</head>', f'{login_script}</head>')
                
                # Write converted content to docs/
                dest_file.write_text(static_content, encoding='utf-8')
                
                copied += 1
                print(f"✓ Updated: {template_file.name}")
            except Exception as e:
                print(f"✗ Failed to process {template_file.name}: {e}")
                return False
        
        print(f"\n✓ Updated {copied} HTML files")
        return True
    
    print("=" * 60)
    print("SYNCING STATIC ASSETS & TEMPLATES TO DOCS FOR GITHUB PAGES")
    print("=" * 60)
    
    # Sync CSS
    print("\n📁 Syncing CSS files...")
    css_success = sync_directory(static_css, docs_css, 'docs/css')
    
    # Sync JS
    print("\n📁 Syncing JavaScript files...")
    js_success = sync_directory(static_js, docs_js, 'docs/js')
    
    # Sync HTML templates
    print("\n📝 Syncing HTML templates...")
    templates_success = sync_templates()
    
    if css_success and js_success and templates_success:
        print("\n" + "=" * 60)
        print("✓ SYNC COMPLETE - All assets updated in docs/")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Review the changes: git status")
        print("2. Stage the changes: git add docs/")
        print("3. Commit: git commit -m 'Sync all assets to docs for GitHub Pages'")
        print("4. Push: git push")
        return True
    else:
        print("\n" + "=" * 60)
        print("✗ SYNC FAILED - Please check the errors above")
        print("=" * 60)
        return False

if __name__ == '__main__':
    success = sync_static_to_docs()
    exit(0 if success else 1)
