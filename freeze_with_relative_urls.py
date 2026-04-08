#!/usr/bin/env python3
"""
Enhanced Static Generator with Relative URL Support
Mimics Frozen-Flask behavior but works with existing Flask setup
"""

import os
import sys
import shutil
from pathlib import Path
import re
from datetime import datetime

class RelativeURLStaticGenerator:
    def __init__(self, base_dir=None, base_url=None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.templates_dir = self.base_dir / 'templates'
        self.static_dir = self.base_dir / 'static'
        self.build_dir = self.base_dir / 'build'
        
        # CRITICAL: Base URL configuration for GitHub Pages
        # This ensures all generated links work in subfolder deployment
        if base_url:
            self.base_url = base_url.rstrip('/')
        else:
            # Default for username.github.io/repo-name/
            self.base_url = 'https://[username].github.io/FinancialReportingSystem/'
        
        # CRITICAL: Relative URLs setting
        # When True, generates ./static/ instead of /static/
        self.relative_urls = True
        
        # Mock user data
        self.mock_user = {
            'full_name': 'Sarah Nkosi',
            'role': 'CFO',
            'can_upload': True,
            'role_lower': 'cfo',
            'username': 'sarah.nkosi'
        }
        
        # Route mappings for automatic discovery
        self.route_mappings = {
            '/': 'index.html',
            '/upload': 'upload.html',
            '/about': 'about.html',
            '/reports': 'reports.html',
            '/admin': 'admin.html',
            '/export': 'export.html',
            '/login': 'login.html',
            '/results': 'results.html',
            '/statement-financial-position': 'statement-financial-position.html',
            '/statement-financial-performance': 'statement-financial-performance.html',
            '/statement-cash-flows': 'statement-cash-flows.html'
        }
        
        # Dynamic route generators (like @freezer.register_generator)
        self.dynamic_generators = [
            self.generate_financial_statements,
            self.generate_sample_reports
        ]
    
    def generate_static_site(self):
        """Main method to generate static site with relative URLs"""
        print("🚀 Enhanced Static Site Generation with Relative URLs")
        print("=" * 70)
        print(f"🔧 Configuration:")
        print(f"   Base URL: {self.base_url}")
        print(f"   Relative URLs: {self.relative_urls}")
        print(f"   Output Directory: {self.build_dir}")
        print(f"   Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 1. Prepare build directory
        self.prepare_build_directory()
        
        # 2. Copy static assets with relative paths
        self.copy_static_assets()
        
        # 3. Generate HTML files with relative URLs
        self.generate_html_files()
        
        # 4. Generate dynamic routes
        self.generate_dynamic_routes()
        
        # 5. Create GitHub Pages configuration
        self.create_github_pages_config()
        
        # 6. Verify output
        self.verify_output()
        
        print()
        print("✅ Static site generation complete!")
        print(f"📂 Build directory: {self.build_dir}")
        print("🌐 Ready for GitHub Pages deployment!")
    
    def prepare_build_directory(self):
        """Prepare clean build directory"""
        print("1. 📁 Preparing build directory...")
        
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        self.build_dir.mkdir(exist_ok=True)
        
        print(f"   ✅ Build directory prepared: {self.build_dir}")
    
    def copy_static_assets(self):
        """Copy static assets with proper structure"""
        print("2. 🎨 Copying static assets...")
        
        # Copy static directory to build
        build_static = self.build_dir / 'static'
        if self.static_dir.exists():
            shutil.copytree(self.static_dir, build_static)
            
            # Count files
            css_count = len(list(build_static.glob('**/*.css')))
            js_count = len(list(build_static.glob('**/*.js')))
            
            print(f"   ✅ Static assets copied:")
            print(f"      CSS files: {css_count}")
            print(f"      JavaScript files: {js_count}")
        else:
            print("   ⚠️  Static directory not found")
    
    def generate_html_files(self):
        """Generate HTML files with relative URL processing"""
        print("3. 📄 Generating HTML files with relative URLs...")
        
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
                
                # Read template
                template_content = template_path.read_text(encoding='utf-8')
                
                # Convert with relative URL processing
                static_html = self.convert_template_with_relative_urls(template_content, template_name)
                
                # Write to build directory
                output_path = self.build_dir / template_name
                output_path.write_text(static_html, encoding='utf-8')
                generated_count += 1
            else:
                print(f"   ⚠️  Template not found: {template_name}")
        
        print(f"   ✅ HTML files generated: {generated_count}")
    
    def convert_template_with_relative_urls(self, content, filename):
        """Convert template to static HTML with relative URL processing"""
        
        # Step 1: Process template inheritance
        content = self.process_template_inheritance(content, filename)
        
        # Step 2: Process includes
        content = self.process_includes(content)
        
        # Step 3: Process template logic
        content = self.process_template_logic(content, filename)
        
        # Step 4: CRITICAL - Convert URLs to relative paths
        content = self.convert_to_relative_urls(content, filename)
        
        # Step 5: Process static asset references
        content = self.process_static_assets_relative(content)
        
        return content
    
    def convert_to_relative_urls(self, content, filename):
        """Convert all URLs to relative paths for GitHub Pages"""
        
        # Determine current page depth for relative path calculation
        current_depth = filename.count('/') if '/' in filename else 0
        
        # Calculate relative prefix based on depth
        if current_depth == 0:
            relative_prefix = './' if self.relative_urls else ''
        else:
            relative_prefix = '../' * current_depth
        
        # Convert Flask routes to relative HTML paths
        for flask_route, html_file in self.route_mappings.items():
            # Handle different link formats
            patterns = [
                f'href="{flask_route}"',
                f"href='{flask_route}'",
                f'action="{flask_route}"',
                f"action='{flask_route}'"
            ]
            
            for pattern in patterns:
                if 'href=' in pattern:
                    replacement = f'href="{relative_prefix}{html_file}"'
                else:  # action=
                    replacement = f'action="{relative_prefix}{html_file}"'
                
                content = content.replace(pattern, replacement)
        
        # Convert url_for function calls to relative paths
        content = re.sub(
            r'\{\{\s*url_for\([\'"]([^\'"]*)[\'"]\)\s*\}\}',
            lambda m: self.convert_url_for_to_relative(m.group(1), relative_prefix),
            content
        )
        
        # Convert static url_for calls
        content = re.sub(
            r'\{\{\s*url_for\([\'"]static[\'"],\s*filename=[\'"]([^\'"]*)[\'"]\)\s*\}\}',
            lambda m: f"{relative_prefix}static/{m.group(1)}",
            content
        )
        
        return content
    
    def convert_url_for_to_relative(self, endpoint, relative_prefix):
        """Convert url_for endpoint to relative path"""
        
        # Handle static files
        if endpoint.startswith('static'):
            if 'filename=' in endpoint:
                filename = endpoint.split('filename=')[1].strip("'\"")
                return f"{relative_prefix}static/{filename}"
            else:
                return f"{relative_prefix}static/"
        
        # Handle route endpoints
        route_path = f"/{endpoint}" if not endpoint.startswith('/') else endpoint
        html_file = self.route_mappings.get(route_path, f"{endpoint}.html")
        
        return f"{relative_prefix}{html_file}"
    
    def process_static_assets_relative(self, content):
        """Process static asset references to be relative"""
        
        # If relative URLs enabled, ensure static paths are relative
        if self.relative_urls:
            # Convert absolute static paths to relative
            content = re.sub(
                r'href="/static/([^"]*)"',
                r'href="./static/\1"',
                content
            )
            
            content = re.sub(
                r'src="/static/([^"]*)"',
                r'src="./static/\1"',
                content
            )
            
            content = re.sub(
                r'href="static/([^"]*)"',
                r'href="./static/\1"',
                content
            )
            
            content = re.sub(
                r'src="static/([^"]*)"',
                r'src="./static/\1"',
                content
            )
        
        return content
    
    def process_template_inheritance(self, content, filename):
        """Process template inheritance"""
        
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
                
                # Remove extends directive
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
                    return self.process_template_logic(included_content, include_file.name)
                except Exception as e:
                    print(f"      ⚠️  Could not include {include_path}: {e}")
                    return f'<!-- Include failed for {include_path} -->'
            return f'<!-- Include not found: {include_path} -->'
        
        content = re.sub(r'\{%\s*include\s+["\']([^"\']+)["\']\s*%\}', replace_include, content)
        return content
    
    def process_template_logic(self, content, filename):
        """Process Flask template logic and variables"""
        
        # Process authentication logic
        content = self.process_authentication_logic(content)
        
        # Process role-based visibility
        content = self.process_role_based_visibility(content)
        
        # Process conditionals
        content = self.process_conditionals(content)
        
        # Process variables
        content = self.process_variables(content)
        
        # Set navigation active state
        content = self.set_navigation_active_state(content, filename)
        
        return content
    
    def process_authentication_logic(self, content):
        """Process authentication logic"""
        user = self.mock_user
        
        # Replace {% if current_user %} blocks
        content = re.sub(
            r'\{%\s*if\s+current_user\s*%\}(.*?)\{%\s*endif\s*%\}',
            lambda m: m.group(1) if user else '',
            content,
            flags=re.DOTALL
        )
        
        # Replace current_user variables
        content = content.replace('{{ current_user.full_name }}', user['full_name'])
        content = content.replace('{{ current_user.role or \'USER\' }}', user['role'])
        content = content.replace('{{ current_user.role }}', user['role'])
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
        """Evaluate template conditions"""
        if 'current_user.can_upload()' in condition:
            return true_content if self.mock_user['can_upload'] else (false_content or '')
        
        if "current_user.role == 'CFO'" in condition:
            return true_content if self.mock_user['role'] == 'CFO' else (false_content or '')
        
        return true_content if true_content else (false_content or '')
    
    def process_variables(self, content):
        """Process template variables"""
        # Replace function calls
        content = re.sub(
            r'\{\{\s*get_role_description\([^)]+\)\s*\}\}',
            'Chief Financial Officer',
            content
        )
        
        content = re.sub(
            r'\{\{\s*get_role_color\([^)]+\)\s*\}\}',
            '#2563eb',
            content
        )
        
        return content
    
    def set_navigation_active_state(self, content, filename):
        """Set active state for navigation items"""
        # Remove existing active classes
        content = re.sub(r'class="active"', '', content)
        
        # Page to route mapping
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
            # Find navigation link for current page and add active class
            patterns = [
                f'href=["\']{current_route}["\']',
                f'href=["\']{filename}["\']'
            ]
            
            for pattern in patterns:
                content = re.sub(
                    f'{pattern}([^>]*)>',
                    f'href="{filename}" class="active"\\1>',
                    content
                )
        
        return content
    
    def generate_dynamic_routes(self):
        """Generate dynamic routes (like @freezer.register_generator)"""
        print("4. 🔄 Generating dynamic routes...")
        
        for generator in self.dynamic_generators:
            generator()
    
    def generate_financial_statements(self):
        """Generate financial statement pages"""
        statements = [
            'statement-financial-position',
            'statement-financial-performance', 
            'statement-cash-flows'
        ]
        
        # These are already handled in main template processing
        # This is where you'd generate additional dynamic content
        print(f"   ✅ Financial statements: {len(statements)} pages")
    
    def generate_sample_reports(self):
        """Generate sample report pages"""
        sample_reports = [
            {'id': 'sample-2024-q1', 'title': 'Q1 2024 Report'},
            {'id': 'sample-2024-q2', 'title': 'Q2 2024 Report'},
            {'id': 'sample-2024-q3', 'title': 'Q3 2024 Report'}
        ]
        
        # Create reports directory
        reports_dir = self.build_dir / 'reports'
        reports_dir.mkdir(exist_ok=True)
        
        for report in sample_reports:
            # Generate report detail page
            report_html = self.generate_report_detail_page(report)
            report_path = reports_dir / f"{report['id']}.html"
            report_path.write_text(report_html, encoding='utf-8')
        
        print(f"   ✅ Sample reports: {len(sample_reports)} pages")
    
    def generate_report_detail_page(self, report):
        """Generate a single report detail page"""
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report['title']} - SADPMR Financial Reporting System</title>
    <link rel="stylesheet" href="../static/css/styles.css">
</head>
<body>
    <nav class="navbar">
        <div class="container-content">
            <div class="nav-brand">
                <h2>SADPMR Financial Reporting System</h2>
            </div>
            <ul class="nav-menu">
                <li><a href="../index.html">Dashboard</a></li>
                <li><a href="../reports.html" class="active">Reports</a></li>
                <li><a href="../about.html">About</a></li>
            </ul>
        </div>
    </nav>

    <main class="container-content">
        <div class="page-header">
            <h1>{report['title']}</h1>
            <p class="text-muted">Generated on {datetime.now().strftime('%Y-%m-%d')}</p>
        </div>

        <div class="report-content">
            <div class="card">
                <div class="card-header">
                    <h3>Report Summary</h3>
                </div>
                <div class="card-body">
                    <p>This is a sample report page demonstrating dynamic route generation.</p>
                    <p>In a real application, this would contain actual financial data and analysis.</p>
                    
                    <div class="button-group">
                        <a href="../reports.html" class="btn btn-secondary">← Back to Reports</a>
                        <button class="btn btn-primary">Download PDF</button>
                    </div>
                </div>
            </div>
        </div>
    </main>

    <footer>
        <div class="container-content">
            <p>&copy; 2025 SADPMR Financial Reporting System</p>
        </div>
    </footer>
</body>
</html>'''
    
    def create_github_pages_config(self):
        """Create GitHub Pages configuration files"""
        print("5. ⚙️  Creating GitHub Pages configuration...")
        
        # Create .nojekyll file
        nojekyll_path = self.build_dir / '.nojekyll'
        nojekyll_path.write_text('')
        
        # Create README for build directory
        readme_path = self.build_dir / 'README.md'
        readme_content = f"""# Static Site Build

This directory contains the generated static site for GitHub Pages deployment.

## Configuration

- **Base URL**: {self.base_url}
- **Relative URLs**: {self.relative_urls}
- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Deployment

This build is ready for deployment to GitHub Pages.

### Manual Deployment
```bash
# Copy to docs folder
cp -r build/* docs/

# Commit and push
git add docs/
git commit -m "Update static site"
git push origin main
```

### Automatic Deployment
Push to main branch and GitHub Actions will deploy automatically.

## File Structure

- HTML files: Root level pages
- static/: CSS, JavaScript, and images
- reports/: Dynamic report pages

Generated with relative URL support for GitHub Pages subfolder deployment.
"""
        readme_path.write_text(readme_content)
        
        print("   ✅ GitHub Pages configuration created")
    
    def verify_output(self):
        """Verify the generated static site"""
        print("6. 🔍 Verifying output...")
        
        # Count files
        html_files = list(self.build_dir.glob('**/*.html'))
        css_files = list(self.build_dir.glob('**/*.css'))
        js_files = list(self.build_dir.glob('**/*.js'))
        
        print(f"   📄 HTML files: {len(html_files)}")
        print(f"   🎨 CSS files: {len(css_files)}")
        print(f"   📜 JavaScript files: {len(js_files)}")
        
        # Check essential files
        essential_files = ['index.html', 'static/css/styles.css']
        for file in essential_files:
            if (self.build_dir / file).exists():
                print(f"   ✅ {file} found")
            else:
                print(f"   ❌ {file} missing")
        
        # Check relative URLs
        index_file = self.build_dir / 'index.html'
        if index_file.exists():
            content = index_file.read_text(encoding='utf-8')
            if './static/' in content or 'static/' in content:
                print("   ✅ Relative URLs detected")
            else:
                print("   ⚠️  No relative URLs found")
        
        print("   ✅ Output verification complete")


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate static site with relative URLs for GitHub Pages')
    parser.add_argument('--base-url', help='Base URL for GitHub Pages (e.g., https://username.github.io/repo-name/)')
    parser.add_argument('--username', help='GitHub username (auto-generates base URL)')
    parser.add_argument('--repo', help='Repository name (auto-generates base URL)')
    parser.add_argument('--absolute-urls', action='store_true', help='Use absolute URLs instead of relative')
    
    args = parser.parse_args()
    
    # Determine base URL
    base_url = args.base_url
    if not base_url and args.username:
        repo_name = args.repo or 'FinancialReportingSystem'
        base_url = f'https://{args.username}.github.io/{repo_name}/'
    
    # Create generator
    generator = RelativeURLStaticGenerator(
        base_dir=Path(__file__).parent,
        base_url=base_url
    )
    
    # Override relative URLs setting if requested
    if args.absolute_urls:
        generator.relative_urls = False
    
    # Generate static site
    generator.generate_static_site()
    
    print()
    print("📋 Next Steps:")
    print("1. Test locally: cd build && python -m http.server 8000")
    print("2. Deploy manually: cp -r build/* docs/ && git commit/push")
    print("3. Or enable GitHub Actions for automatic deployment")


if __name__ == '__main__':
    main()
