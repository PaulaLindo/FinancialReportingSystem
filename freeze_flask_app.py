#!/usr/bin/env python3
"""
Flask to Static Site Generator for GitHub Pages
Converts dynamic Flask routes into static HTML files with identical UI
"""

import os
import sys
import shutil
from pathlib import Path
import re
from datetime import datetime
import json

class FlaskStaticGenerator:
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.templates_dir = self.base_dir / 'templates'
        self.static_dir = self.base_dir / 'static'
        self.docs_dir = self.base_dir / 'docs'
        
        # Mock user data for static site (simulates logged-in CFO user)
        self.mock_user = {
            'full_name': 'Sarah Nkosi',
            'role': 'CFO',
            'can_upload': True,
            'role_lower': 'cfo',
            'username': 'sarah.nkosi'
        }
        
        # Route mappings for static generation
        self.route_mappings = {
            '/': 'index.html',
            '/upload': 'upload.html',
            '/reports': 'reports.html',
            '/export': 'export.html',
            '/admin': 'admin.html',
            '/about': 'about.html',
            '/login': 'login.html',
            '/results': 'results.html',
            '/statement-financial-position': 'statement-financial-position.html',
            '/statement-financial-performance': 'statement-financial-performance.html',
            '/statement-cash-flows': 'statement-cash-flows.html'
        }
        
    def generate_static_site(self):
        """Main method to generate complete static site"""
        print("🚀 Starting Flask to Static Site Generation")
        print("=" * 60)
        print(f"📁 Base Directory: {self.base_dir}")
        print(f"📅 Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 1. Prepare output directory
        self.prepare_output_directory()
        
        # 2. Copy static assets
        self.copy_static_assets()
        
        # 3. Generate static HTML files
        self.generate_html_files()
        
        # 4. Copy additional data
        self.copy_additional_data()
        
        # 5. Generate GitHub Pages configuration
        self.generate_github_pages_config()
        
        print()
        print("✅ Static site generation complete!")
        print(f"📂 Output directory: {self.docs_dir}")
        print("🌐 Ready for GitHub Pages deployment!")
        
    def prepare_output_directory(self):
        """Prepare the docs directory for GitHub Pages"""
        print("1. 📁 Preparing output directory...")
        
        # Create docs directory if it doesn't exist
        self.docs_dir.mkdir(exist_ok=True)
        
        # Clean up old files but preserve .gitkeep if exists
        for item in self.docs_dir.iterdir():
            if item.is_file() and item.name != '.gitkeep':
                item.unlink()
            elif item.is_dir() and item.name not in ['.git', 'css', 'js']:
                shutil.rmtree(item)
        
        print(f"   ✅ Output directory prepared: {self.docs_dir}")
        
    def copy_static_assets(self):
        """Copy CSS and JavaScript files"""
        print("2. 🎨 Copying static assets...")
        
        # Copy CSS files
        css_src = self.static_dir / 'css'
        css_dst = self.docs_dir / 'css'
        if css_src.exists():
            if css_dst.exists():
                shutil.rmtree(css_dst)
            shutil.copytree(css_src, css_dst)
            css_count = len(list(css_dst.glob('*.css')))
            print(f"   ✅ CSS files copied: {css_count} files")
        
        # Copy JavaScript files
        js_src = self.static_dir / 'js'
        js_dst = self.docs_dir / 'js'
        if js_src.exists():
            if js_dst.exists():
                shutil.rmtree(js_dst)
            shutil.copytree(js_src, js_dst)
            js_count = len(list(js_dst.glob('*.js')))
            print(f"   ✅ JavaScript files copied: {js_count} files")
        
        # Copy other static assets if they exist
        for asset_dir in ['images', 'fonts', 'icons']:
            asset_src = self.static_dir / asset_dir
            asset_dst = self.docs_dir / asset_dir
            if asset_src.exists():
                if asset_dst.exists():
                    shutil.rmtree(asset_dst)
                shutil.copytree(asset_src, asset_dst)
                print(f"   ✅ {asset_dir.title()} copied")
    
    def generate_html_files(self):
        """Generate static HTML files from Flask templates"""
        print("3. 📄 Generating static HTML files...")
        
        templates_to_process = [
            'index.html', 'upload.html', 'about.html', 'reports.html', 
            'admin.html', 'export.html', 'login.html', 'results.html',
            'statement-financial-position.html', 'statement-financial-performance.html',
            'statement-cash-flows.html'
        ]
        
        generated_count = 0
        for template_name in templates_to_process:
            template_path = self.templates_dir / template_name
            if template_path.exists():
                print(f"   🔄 Processing: {template_name}")
                
                # Read template content
                template_content = template_path.read_text(encoding='utf-8')
                
                # Convert to static HTML
                static_html = self.convert_template_to_static(template_content, template_name)
                
                # Write to docs directory
                output_path = self.docs_dir / template_name
                output_path.write_text(static_html, encoding='utf-8')
                generated_count += 1
            else:
                print(f"   ⚠️  Template not found: {template_name}")
        
        print(f"   ✅ HTML files generated: {generated_count} files")
    
    def convert_template_to_static(self, content, filename):
        """Convert Flask Jinja2 template to static HTML"""
        
        # Step 1: Process template inheritance
        content = self.process_template_inheritance(content, filename)
        
        # Step 2: Process includes
        content = self.process_includes(content)
        
        # Step 3: Process template logic and variables
        content = self.process_template_logic(content, filename)
        
        # Step 4: Convert URL generation
        content = self.convert_urls(content)
        
        # Step 5: Process static asset references
        content = self.process_static_assets(content)
        
        return content
    
    def process_template_inheritance(self, content, filename):
        """Process template inheritance (extends blocks)"""
        
        # Check if template extends a base template
        extends_match = re.search(r'\{%\s*extends\s+["\']([^"\']+)["\']\s*%\}', content)
        if extends_match:
            base_template_name = extends_match.group(1)
            base_template_path = self.templates_dir / base_template_name
            
            if base_template_path.exists():
                base_content = base_template_path.read_text(encoding='utf-8')
                
                # Extract blocks from child template
                title = self.extract_block_content(content, 'title') or 'SADPMR Financial Reporting System'
                main_content = self.extract_block_content(content, 'content') or content
                extra_css = self.extract_block_content(content, 'extra_css') or ''
                extra_js = self.extract_block_content(content, 'extra_js') or ''
                
                # Replace blocks in base template
                result = base_content
                result = re.sub(r'\{%\s*block\s+title\s*%\}.*?\{%\s*endblock\s*%\}', title, result, flags=re.DOTALL)
                result = re.sub(r'\{%\s*block\s+content\s*%\}.*?\{%\s*endblock\s*%\}', main_content, result, flags=re.DOTALL)
                result = re.sub(r'\{%\s*block\s+extra_css\s*%\}.*?\{%\s*endblock\s*%\}', extra_css, result, flags=re.DOTALL)
                result = re.sub(r'\{%\s*block\s+extra_js\s*%\}.*?\{%\s*endblock\s*%\}', extra_js, result, flags=re.DOTALL)
                
                # Remove the extends directive
                result = re.sub(r'\{%\s*extends\s+["\'][^"\']+["\']\s*%\}', '', result)
                
                return result
        
        return content
    
    def extract_block_content(self, content, block_name):
        """Extract content from a specific block"""
        pattern = rf'\{{%\s*block\s+{block_name}\s*%\}}(.*?)\{{%\s*endblock\s*%\}}'
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else None
    
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
                    print(f"      ⚠️  Could not include {include_path}: {e}")
                    return f'<!-- Include failed for {include_path} -->'
            return f'<!-- Include not found: {include_path} -->'
        
        # Replace includes
        content = re.sub(r'\{%\s*include\s+["\']([^"\']+)["\']\s*%\}', replace_include, content)
        return content
    
    def process_template_logic(self, content, filename):
        """Process Flask template logic and variables"""
        
        # Process authentication and user-related logic
        content = self.process_authentication_logic(content)
        
        # Process role-based visibility
        content = self.process_role_based_visibility(content)
        
        # Process conditional statements
        content = self.process_conditionals(content)
        
        # Process template variables
        content = self.process_variables(content)
        
        # Process function calls
        content = self.process_function_calls(content)
        
        # Set active navigation state
        content = self.set_navigation_active_state(content, filename)
        
        return content
    
    def process_authentication_logic(self, content):
        """Process authentication-related template logic"""
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
        
        # Replace current_user variables
        content = content.replace('{{ current_user.full_name }}', user['full_name'])
        content = content.replace('{{ current_user.role or \'USER\' }}', user['role'])
        content = content.replace('{{ current_user.role }}', user['role'])
        content = content.replace('{{ current_user.username }}', user['username'])
        
        # Handle role.lower() with fallback
        content = content.replace('{{ current_user.role.lower() if current_user.role else \'default\' }}', user['role_lower'])
        
        return content
    
    def process_role_based_visibility(self, content):
        """Process role-based content visibility"""
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
        """Process conditional statements"""
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
        """Evaluate template conditions for static generation"""
        # Handle user permission checks
        if 'current_user.can_upload()' in condition:
            return true_content if self.mock_user['can_upload'] else (false_content or '')
        
        if "current_user.role == 'CFO'" in condition:
            return true_content if self.mock_user['role'] == 'CFO' else (false_content or '')
        
        # For complex conditions we can't evaluate, default to true_content
        return true_content if true_content else (false_content or '')
    
    def process_variables(self, content):
        """Process template variables"""
        # Replace get_role_description function calls
        content = re.sub(
            r'\{\{\s*get_role_description\([^)]+\)\s*\}\}',
            'Chief Financial Officer',
            content
        )
        
        # Replace get_role_color function calls
        content = re.sub(
            r'\{\{\s*get_role_color\([^)]+\)\s*\}\}',
            '#2563eb',
            content
        )
        
        # Replace other common variables
        content = content.replace('{{ config.SECRET_KEY }}', '[REDACTED]')
        content = content.replace('{{ request.endpoint }}', 'static')
        
        return content
    
    def process_function_calls(self, content):
        """Process function calls in templates"""
        # Handle url_for calls (will be processed in convert_urls)
        # Handle other function calls as needed
        
        return content
    
    def set_navigation_active_state(self, content, filename):
        """Set active state for navigation items"""
        # Remove existing active classes
        content = re.sub(r'class="active"', '', content)
        content = re.sub(r'\{%\s*if\s+request\.endpoint.*?%\}class="active"\{%\s*endif\s*%\}', '', content)
        
        # Page to endpoint mapping
        page_mappings = {
            'index.html': '/',
            'upload.html': '/upload',
            'reports.html': '/reports',
            'export.html': '/export',
            'admin.html': '/admin',
            'about.html': '/about',
            'login.html': '/login',
            'results.html': '/results'
        }
        
        current_route = page_mappings.get(filename, '')
        if current_route:
            # Find the navigation link for current page and add active class
            patterns = [
                f'href=["\']{current_route}["\']',
                f'href=["\']{filename}["\']'
            ]
            
            for pattern in patterns:
                content = re.sub(
                    f'{pattern}([^>]*)>',
                    f'{pattern} class="active"\\1>',
                    content
                )
        
        return content
    
    def convert_urls(self, content):
        """Convert Flask URLs to static file paths"""
        # Route mappings
        url_mappings = {
            '/': 'index.html',
            '/upload': 'upload.html',
            '/reports': 'reports.html',
            '/export': 'export.html',
            '/admin': 'admin.html',
            '/about': 'about.html',
            '/login': 'login.html',
            '/results': 'results.html',
            '/logout': 'index.html',  # Redirect logout to home
            '/statement-financial-position': 'statement-financial-position.html',
            '/statement-financial-performance': 'statement-financial-performance.html',
            '/statement-cash-flows': 'statement-cash-flows.html'
        }
        
        # Replace Flask routes with static HTML files
        for flask_url, static_url in url_mappings.items():
            # Replace href attributes
            content = re.sub(
                f'href=["\']{re.escape(flask_url)}["\']',
                f'href="{static_url}"',
                content
            )
        
        # Handle url_for function calls
        content = re.sub(
            r'\{\{\s*url_for\([\'"](static[^\'"]*)[\'"]\)\s*\}\}',
            lambda m: m.group(1).replace('static/', '').replace("'", ''),
            content
        )
        
        content = re.sub(
            r'\{\{\s*url_for\([\'"]([^\'"]*)[\'"]\)\s*\}\}',
            lambda m: self.route_mappings.get(f"/{m.group(1)}", f"{m.group(1)}.html"),
            content
        )
        
        return content
    
    def process_static_assets(self, content):
        """Process static asset references"""
        # Convert url_for('static', filename='...') to relative paths
        content = re.sub(
            r'href=["\']\{\{\s*url_for\([\'"]static[\'"],\s*filename=[\'"]([^\'"]*)[\'"]\)\s*\}\}["\']',
            r'href="\1"',
            content
        )
        
        content = re.sub(
            r'src=["\']\{\{\s*url_for\([\'"]static[\'"],\s*filename=[\'"]([^\'"]*)[\'"]\)\s*\}\}["\']',
            r'src="\1"',
            content
        )
        
        return content
    
    def copy_additional_data(self):
        """Copy additional data files"""
        print("4. 📊 Copying additional data...")
        
        # Copy sample data if it exists
        data_src = self.base_dir / 'data'
        data_dst = self.docs_dir / 'data'
        if data_src.exists():
            if data_dst.exists():
                shutil.rmtree(data_dst)
            shutil.copytree(data_src, data_dst)
            data_count = len(list(data_dst.glob('*.json')))
            print(f"   ✅ Data files copied: {data_count} files")
        
        # Copy uploads directory if it exists (for sample files)
        uploads_src = self.base_dir / 'uploads'
        uploads_dst = self.docs_dir / 'uploads'
        if uploads_src.exists():
            uploads_dst.mkdir(exist_ok=True)
            # Copy sample files
            sample_files = list(uploads_src.glob('*.xlsx')) + list(uploads_src.glob('*.csv'))
            for file in sample_files[:3]:  # Copy up to 3 sample files
                shutil.copy2(file, uploads_dst / file.name)
            print(f"   ✅ Sample files copied: {min(3, len(sample_files))} files")
    
    def generate_github_pages_config(self):
        """Generate GitHub Pages configuration files"""
        print("5. ⚙️  Generating GitHub Pages configuration...")
        
        # Generate .nojekyll file
        nojekyll_path = self.docs_dir / '.nojekyll'
        nojekyll_path.write_text('')
        print("   ✅ Created .nojekyll file")
        
        # Generate CNAME file if needed (uncomment and modify)
        # cname_path = self.docs_dir / 'CNAME'
        # cname_path.write_text('yourdomain.com')
        # print("   ✅ Created CNAME file")
        
        # Generate README for docs directory
        readme_path = self.docs_dir / 'README.md'
        readme_content = f"""# SADPMR Financial Reporting System - Static Site

This directory contains the static version of the SADPMR Financial Reporting System, optimized for GitHub Pages deployment.

## Generated Files

- **HTML Pages**: {len(list(self.docs_dir.glob('*.html')))} static pages
- **CSS Files**: {len(list((self.docs_dir / 'css').glob('*.css'))) if (self.docs_dir / 'css').exists() else 0} stylesheets
- **JavaScript Files**: {len(list((self.docs_dir / 'js').glob('*.js'))) if (self.docs_dir / 'js').exists() else 0} scripts

## Deployment

This site is automatically deployed to GitHub Pages from the `main` branch, `/docs` folder.

## Last Updated

{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Notes

- This is a static demonstration of the Flask application
- Server-side functionality (file processing, PDF generation) is not available
- Authentication is simulated with a mock CFO user (Sarah Nkosi)
- All UI/UX features are fully functional
"""
        readme_path.write_text(readme_content)
        print("   ✅ Created README.md")


def main():
    """Main execution function"""
    print("🏦 SADPMR Financial Reporting System - Static Site Generator")
    print("   Converting Flask application to static GitHub Pages site")
    print()
    
    # Create generator instance
    generator = FlaskStaticGenerator()
    
    # Generate static site
    generator.generate_static_site()
    
    print()
    print("🎉 Static site generation complete!")
    print()
    print("📋 Next Steps:")
    print("1. Commit the changes to git:")
    print("   git add docs/")
    print("   git commit -m 'Update static site for GitHub Pages'")
    print()
    print("2. Push to GitHub:")
    print("   git push origin main")
    print()
    print("3. Configure GitHub Pages:")
    print("   - Go to repository Settings > Pages")
    print("   - Select 'Deploy from branch'")
    print("   - Choose 'main' branch, '/docs' folder")
    print()
    print("4. Visit your live site:")
    print("   https://[username].github.io/FinancialReportingSystem/")


if __name__ == '__main__':
    main()
