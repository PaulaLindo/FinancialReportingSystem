#!/usr/bin/env python3
"""
Frozen-Flask Configuration for GitHub Pages
Handles proper relative URLs, base URL handling, and automatic discovery
"""

import os
import sys
from pathlib import Path
from flask import Flask
from flask_frozen import Freezer

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import your Flask application
from controllers.routes import app, get_current_user

# === FROZEN-FLASK CONFIGURATION ===

# CRITICAL: Relative URLs for GitHub Pages subfolder deployment
# This ensures url_for generates paths like ./static/css/style.css instead of /static/css/style.css
# Without this, GitHub Pages breaks when hosted in username.github.io/repo-name/
FREEZER_RELATIVE_URLS = True

# CRITICAL: Base URL matching your GitHub Pages structure
# Set this to your repository name if deploying to username.github.io/repo-name/
# Leave as '/' if deploying to username.github.io (custom domain)
FREEZER_BASE_URL = 'https://[username].github.io/FinancialReportingSystem/'

# Output directory for static files
FREEZER_DESTINATION = 'build'

# Default MIME types for proper GitHub Pages serving
FREEZER_DEFAULT_MIME_TYPE = 'text/html'

# Remove .html extensions from URLs (optional)
FREEZER_REMOVE_EXTRA_SLASH = False

# === MOCK USER FOR STATIC GENERATION ===
class MockUser:
    def __init__(self):
        self.full_name = 'Sarah Nkosi'
        self.role = 'CFO'
        self.username = 'sarah.nkosi'
        self.role_lower = 'cfo'
    
    def can_upload(self):
        return True
    
    def has_permission(self, permission):
        return True  # Mock user has all permissions

# Override get_current_user for static generation
def mock_get_current_user():
    return MockUser()

# === FLASK APP CONFIGURATION FOR STATIC GENERATION ===

# Configure app for static generation
app.config.update({
    'FREEZER_RELATIVE_URLS': FREEZER_RELATIVE_URLS,
    'FREEZER_BASE_URL': FREEZER_BASE_URL,
    'FREEZER_DESTINATION': FREEZER_DESTINATION,
    'SECRET_KEY': 'static-generation-key'
})

# Mock authentication context processor
@app.context_processor
def mock_context_processor():
    return {
        'current_user': mock_get_current_user(),
        'get_role_description': lambda role: 'Chief Financial Officer',
        'get_role_color': lambda role: '#2563eb'
    }

# === FREEZER INITIALIZATION ===
freezer = Freezer(app)

# === AUTOMATIC ROUTE DISCOVERY ===

# Freezer automatically discovers all @app.route() decorated functions
# These routes will be included in static generation:
# - / -> index.html
# - /upload -> upload.html  
# - /about -> about.html
# - /reports -> reports.html
# - /admin -> admin.html
# - /export -> export.html
# - /login -> login.html
# - /results -> results.html

# === MANUAL GENERATOR REGISTRATION ===

# For dynamic routes that aren't directly linked in navigation
# Example: Blog posts, user profiles, specific financial statements

@freezer.register_generator
def financial_statements():
    """Generate all financial statement pages"""
    statements = [
        'statement-financial-position',
        'statement-financial-performance', 
        'statement-cash-flows'
    ]
    
    for statement in statements:
        yield f'/{statement}', {'statement_type': statement}

@freezer.register_generator  
def sample_reports():
    """Generate sample report pages"""
    sample_data = [
        {'id': 'sample-2024-q1', 'title': 'Q1 2024 Report'},
        {'id': 'sample-2024-q2', 'title': 'Q2 2024 Report'},
        {'id': 'sample-2024-q3', 'title': 'Q3 2024 Report'}
    ]
    
    for report in sample_data:
        yield f'/reports/{report["id"]}', {'report_id': report['id']}

# === DYNAMIC ROUTES FOR GENERATION ===

@app.route('/statement-financial-position')
def statement_financial_position():
    """Static financial position statement"""
    user = mock_get_current_user()
    return app.jinja_env.render_template(
        'statement-financial-position.html',
        user=user,
        statement_type='financial-position'
    )

@app.route('/statement-financial-performance')
def statement_financial_performance():
    """Static financial performance statement"""
    user = mock_get_current_user()
    return app.jinja_env.render_template(
        'statement-financial-performance.html',
        user=user,
        statement_type='financial-performance'
    )

@app.route('/statement-cash-flows')
def statement_cash_flows():
    """Static cash flows statement"""
    user = mock_get_current_user()
    return app.jinja_env.render_template(
        'statement-cash-flows.html',
        user=user,
        statement_type='cash-flows'
    )

@app.route('/reports/<report_id>')
def report_detail(report_id):
    """Static report detail page"""
    user = mock_get_current_user()
    sample_reports = {
        'sample-2024-q1': {'title': 'Q1 2024 Report', 'date': '2024-03-31'},
        'sample-2024-q2': {'title': 'Q2 2024 Report', 'date': '2024-06-30'},
        'sample-2024-q3': {'title': 'Q3 2024 Report', 'date': '2024-09-30'}
    }
    
    report = sample_reports.get(report_id, {'title': 'Report Not Found', 'date': 'Unknown'})
    
    return app.jinja_env.render_template(
        'report-detail.html',
        user=user,
        report=report,
        report_id=report_id
    )

# === STATIC GENERATION FUNCTIONS ===

def generate_static_site():
    """Generate the static site using Frozen-Flask"""
    print("🚀 Starting Frozen-Flask Static Generation")
    print("=" * 60)
    
    # Display configuration
    print(f"🔧 Configuration:")
    print(f"   FREEZER_RELATIVE_URLS: {FREEZER_RELATIVE_URLS}")
    print(f"   FREEZER_BASE_URL: {FREEZER_BASE_URL}")
    print(f"   FREEZER_DESTINATION: {FREEZER_DESTINATION}")
    print()
    
    # Create freezer instance
    freezer = Freezer(app)
    
    try:
        # Generate URLs that will be created
        print("🔍 Discovering routes...")
        urls = freezer.all_urls()
        print(f"   Found {len(urls)} routes to generate")
        
        # Display discovered routes
        print("\n📄 Routes to be generated:")
        for url in sorted(urls):
            print(f"   {url}")
        
        print()
        print("🏗️  Generating static files...")
        
        # Generate static site
        freezer.freeze()
        
        print()
        print("✅ Static site generated successfully!")
        print(f"📂 Output directory: {FREEZER_DESTINATION}")
        
        # Verify output
        verify_output()
        
    except Exception as e:
        print(f"❌ Error generating static site: {e}")
        raise

def verify_output():
    """Verify that the static site was generated correctly"""
    print("\n🔍 Verifying output...")
    
    build_dir = Path(FREEZER_DESTINATION)
    if not build_dir.exists():
        print("❌ Build directory not found")
        return
    
    # Count generated files
    html_files = list(build_dir.glob('**/*.html'))
    css_files = list(build_dir.glob('**/*.css'))
    js_files = list(build_dir.glob('**/*.js'))
    
    print(f"   📄 HTML files: {len(html_files)}")
    print(f"   🎨 CSS files: {len(css_files)}")
    print(f"   📜 JavaScript files: {len(js_files)}")
    
    # Check for essential files
    essential_files = ['index.html']
    for file in essential_files:
        if (build_dir / file).exists():
            print(f"   ✅ {file} found")
        else:
            print(f"   ❌ {file} missing")
    
    # Check static assets
    static_dir = build_dir / 'static'
    if static_dir.exists():
        print("   ✅ Static directory found")
    else:
        print("   ❌ Static directory missing")
    
    print("   ✅ Output verification complete")

def update_base_url(username, repo_name=None):
    """Update FREEZER_BASE_URL for your GitHub Pages setup"""
    global FREEZER_BASE_URL
    
    if repo_name:
        # For username.github.io/repo-name/
        FREEZER_BASE_URL = f'https://{username}.github.io/{repo_name}/'
    else:
        # For username.github.io/ (custom domain)
        FREEZER_BASE_URL = f'https://{username}.github.io/'
    
    print(f"🔗 Updated FREEZER_BASE_URL to: {FREEZER_BASE_URL}")

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate static site with Frozen-Flask')
    parser.add_argument('--username', help='GitHub username for base URL')
    parser.add_argument('--repo', help='Repository name for base URL')
    parser.add_argument('--verify-only', action='store_true', help='Only verify existing build')
    
    args = parser.parse_args()
    
    # Update base URL if provided
    if args.username:
        update_base_url(args.username, args.repo)
    
    if args.verify_only:
        verify_output()
    else:
        generate_static_site()
        
        print("\n📋 Next Steps:")
        print("1. Review generated files in /build directory")
        print("2. Test locally: python -m http.server --directory build 8000")
        print("3. Deploy to GitHub Pages:")
        print("   - Copy build/* to docs/ or gh-pages branch")
        print("   - Configure GitHub Pages settings")
