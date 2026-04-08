#!/usr/bin/env python3
"""
Static Generator with Cache Busting
Implements version query strings and timestamps for force-refresh
"""

import os
import sys
import shutil
from pathlib import Path
import re
import hashlib
from datetime import datetime
import json

class CacheBustingStaticGenerator:
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.templates_dir = self.base_dir / 'templates'
        self.static_dir = self.base_dir / 'static'
        self.build_dir = self.base_dir / 'build'
        
        # Cache busting configuration
        self.cache_busting_method = 'timestamp'  # 'timestamp' or 'hash'
        self.version_string = self.generate_version_string()
        
        # Mock user data
        self.mock_user = {
            'full_name': 'Sarah Nkosi',
            'role': 'CFO',
            'can_upload': True,
            'role_lower': 'cfo',
            'username': 'sarah.nkosi'
        }
        
        # Route mappings
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
        
        # Asset manifest for cache busting
        self.asset_manifest = {}
    
    def generate_version_string(self):
        """Generate version string for cache busting"""
        if self.cache_busting_method == 'timestamp':
            return datetime.now().strftime('%Y%m%d%H%M%S')
        elif self.cache_busting_method == 'hash':
            # Generate hash from current timestamp and some randomness
            timestamp = str(datetime.now().timestamp()).encode()
            return hashlib.md5(timestamp).hexdigest()[:8]
        else:
            return datetime.now().strftime('%Y%m%d%H%M%S')
    
    def generate_with_cache_busting(self):
        """Generate static site with cache busting"""
        print("=== Static Generation with Cache Busting ===")
        print(f"Method: {self.cache_busting_method}")
        print(f"Version: {self.version_string}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # 1. Clean build directory
        self.clean_build_directory()
        
        # 2. Copy and process static assets with cache busting
        self.process_static_assets_with_cache_busting()
        
        # 3. Generate HTML files with cache-busted URLs
        self.generate_html_with_cache_busting()
        
        # 4. Generate asset manifest
        self.generate_asset_manifest()
        
        # 5. Create cache busting configuration
        self.create_cache_busting_config()
        
        print()
        print("=== Cache Busting Generation Complete ===")
        print(f"Build directory: {self.build_dir}")
        print(f"Version: {self.version_string}")
        print("All static assets now have cache-busting URLs!")
    
    def clean_build_directory(self):
        """Clean build directory completely"""
        print("1. Cleaning build directory...")
        
        if self.build_dir.exists():
            shutil.rmtree(self.build_dir)
        
        self.build_dir.mkdir(exist_ok=True)
        print("   Build directory cleaned")
    
    def process_static_assets_with_cache_busting(self):
        """Copy static assets and apply cache busting"""
        print("2. Processing static assets with cache busting...")
        
        build_static = self.build_dir / 'static'
        
        if self.static_dir.exists():
            # Copy static directory
            shutil.copytree(self.static_dir, build_static)
            
            # Process CSS files
            self.process_css_files(build_static)
            
            # Process JavaScript files
            self.process_js_files(build_static)
            
            # Process images if they exist
            self.process_image_files(build_static)
            
            print(f"   Static assets processed with cache busting")
        else:
            print("   Static directory not found")
    
    def process_css_files(self, static_dir):
        """Process CSS files with cache busting"""
        css_dir = static_dir / 'css'
        if css_dir.exists():
            css_files = list(css_dir.glob('*.css'))
            print(f"   Processing {len(css_files)} CSS files...")
            
            for css_file in css_files:
                # Generate cache-busted filename
                cache_busted_name = f"{css_file.stem}.v{self.version_string}.css"
                cache_busted_path = css_dir / cache_busted_name
                
                # Copy file with new name
                shutil.copy2(css_file, cache_busted_path)
                
                # Remove original file
                css_file.unlink()
                
                # Add to manifest
                self.asset_manifest[f"css/{css_file.name}"] = f"css/{cache_busted_name}"
                
                # Process CSS content to update internal references
                self.process_css_content(cache_busted_path)
    
    def process_js_files(self, static_dir):
        """Process JavaScript files with cache busting"""
        js_dir = static_dir / 'js'
        if js_dir.exists():
            js_files = list(js_dir.glob('*.js'))
            print(f"   Processing {len(js_files)} JavaScript files...")
            
            for js_file in js_files:
                # Generate cache-busted filename
                cache_busted_name = f"{js_file.stem}.v{self.version_string}.js"
                cache_busted_path = js_dir / cache_busted_name
                
                # Copy file with new name
                shutil.copy2(js_file, cache_busted_path)
                
                # Remove original file
                js_file.unlink()
                
                # Add to manifest
                self.asset_manifest[f"js/{js_file.name}"] = f"js/{cache_busted_name}"
    
    def process_image_files(self, static_dir):
        """Process image files with cache busting"""
        image_extensions = ['*.png', '*.jpg', '*.jpeg', '*.gif', '*.svg', '*.ico']
        image_files = []
        
        for ext in image_extensions:
            image_files.extend(static_dir.rglob(ext))
        
        if image_files:
            print(f"   Processing {len(image_files)} image files...")
            
            for img_file in image_files:
                # Generate cache-busted filename
                cache_busted_name = f"{img_file.stem}.v{self.version_string}{img_file.suffix}"
                cache_busted_path = img_file.parent / cache_busted_name
                
                # Copy file with new name
                shutil.copy2(img_file, cache_busted_path)
                
                # Remove original file
                img_file.unlink()
                
                # Add to manifest
                relative_path = img_file.relative_to(static_dir)
                cache_busted_relative = cache_busted_path.relative_to(static_dir)
                self.asset_manifest[str(relative_path)] = str(cache_busted_relative)
    
    def process_css_content(self, css_file):
        """Process CSS content to update internal references"""
        try:
            content = css_file.read_text(encoding='utf-8')
            
            # Update font references
            content = re.sub(
                r'url\(["\']?([^"\')]+\.(woff|woff2|ttf|eot)["\']?\)',
                lambda m: f'url({self.update_asset_reference(m.group(1))})',
                content
            )
            
            # Update image references
            content = re.sub(
                r'url\(["\']?([^"\')]+\.(png|jpg|jpeg|gif|svg)["\']?\)',
                lambda m: f'url({self.update_asset_reference(m.group(1))})',
                content
            )
            
            css_file.write_text(content, encoding='utf-8')
            
        except Exception as e:
            print(f"   Warning: Could not process CSS content for {css_file}: {e}")
    
    def update_asset_reference(self, asset_path):
        """Update asset reference with cache busting"""
        # Remove quotes if present
        clean_path = asset_path.strip("'\"")
        
        # Check if it's in our manifest
        if clean_path in self.asset_manifest:
            return self.asset_manifest[clean_path]
        
        # Check if it's a relative path
        if clean_path.startswith('../'):
            # Handle relative paths
            parts = clean_path.split('/')
            if len(parts) >= 2:
                filename = parts[-1]
                if filename in self.asset_manifest:
                    # Reconstruct relative path
                    return '/'.join(parts[:-1] + [self.asset_manifest[filename]])
        
        return asset_path
    
    def generate_html_with_cache_busting(self):
        """Generate HTML files with cache-busted asset URLs"""
        print("3. Generating HTML with cache-busted URLs...")
        
        templates_to_process = [
            'index.html', 'upload.html', 'about.html', 'reports.html',
            'admin.html', 'export.html', 'login.html', 'results.html',
            'statement-financial-position.html', 'statement-financial-performance.html',
            'statement-cash-flows.html'
        ]
        
        for template_name in templates_to_process:
            template_path = self.templates_dir / template_name
            if template_path.exists():
                print(f"   Processing: {template_name}")
                
                # Read template
                template_content = template_path.read_text(encoding='utf-8')
                
                # Convert with cache busting
                static_html = self.convert_template_with_cache_busting(template_content, template_name)
                
                # Write to build directory
                output_path = self.build_dir / template_name
                output_path.write_text(static_html, encoding='utf-8')
        
        print("   HTML files generated with cache busting")
    
    def convert_template_with_cache_busting(self, content, filename):
        """Convert template to static HTML with cache busting"""
        
        # Process template inheritance
        content = self.process_template_inheritance(content, filename)
        
        # Process includes
        content = self.process_includes(content)
        
        # Process template logic
        content = self.process_template_logic(content, filename)
        
        # CRITICAL: Apply cache busting to URLs
        content = self.apply_cache_busting_to_urls(content)
        
        # Process static asset references
        content = self.process_static_assets_with_cache_busting_urls(content)
        
        return content
    
    def apply_cache_busting_to_urls(self, content):
        """Apply cache busting to all asset URLs"""
        
        # Apply to CSS files
        content = re.sub(
            r'href=["\']([^"\']*\.css)["\']',
            lambda m: f'href="{self.add_cache_busting(m.group(1))}"',
            content
        )
        
        # Apply to JavaScript files
        content = re.sub(
            r'src=["\']([^"\']*\.js)["\']',
            lambda m: f'src="{self.add_cache_busting(m.group(1))}"',
            content
        )
        
        # Apply to images
        content = re.sub(
            r'src=["\']([^"\']*\.(png|jpg|jpeg|gif|svg|ico))["\']',
            lambda m: f'src="{self.add_cache_busting(m.group(1))}"',
            content
        )
        
        # Apply to url_for static calls
        content = re.sub(
            r'\{\{\s*url_for\([\'"]static[\'"],\s*filename=[\'"]([^\'"]*)[\'"]\)\s*\}\}',
            lambda m: self.add_cache_busting(f"static/{m.group(1)}"),
            content
        )
        
        return content
    
    def add_cache_busting(self, asset_path):
        """Add cache busting to asset path"""
        
        # Remove leading ./ or / if present
        clean_path = asset_path.lstrip('./')
        
        # Check if it's in our manifest
        if clean_path in self.asset_manifest:
            return f"./{self.asset_manifest[clean_path]}"
        
        # If not in manifest, add query string
        if '?' in asset_path:
            return f"{asset_path}&v={self.version_string}"
        else:
            return f"{asset_path}?v={self.version_string}"
    
    def process_static_assets_with_cache_busting_urls(self, content):
        """Process static asset references with cache busting"""
        
        # Convert to relative paths with cache busting
        content = re.sub(
            r'href="/static/([^"]*)"',
            lambda m: f'href="./static/{self.add_cache_busting_to_static(m.group(1))}"',
            content
        )
        
        content = re.sub(
            r'src="/static/([^"]*)"',
            lambda m: f'src="./static/{self.add_cache_busting_to_static(m.group(1))}"',
            content
        )
        
        return content
    
    def add_cache_busting_to_static(self, asset_path):
        """Add cache busting to static asset"""
        if asset_path in self.asset_manifest:
            return self.asset_manifest[asset_path]
        return f"{asset_path}?v={self.version_string}"
    
    def process_template_inheritance(self, content, filename):
        """Process template inheritance (simplified)"""
        # Check for extends directive
        extends_match = re.search(r'\{%\s*extends\s+["\']([^"\']+)["\']\s*%\}', content)
        if extends_match:
            base_template_name = extends_match.group(1)
            base_template_path = self.templates_dir / base_template_name
            
            if base_template_path.exists():
                base_content = base_template_path.read_text(encoding='utf-8')
                
                # Extract blocks
                title = self.extract_block_content(content, 'title') or 'SADPMR Financial Reporting System'
                main_content = self.extract_block_content(content, 'content') or content
                extra_css = self.extract_block_content(content, 'extra_css') or ''
                extra_js = self.extract_block_content(content, 'extra_js') or ''
                
                # Replace in base template
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
                    print(f"      Warning: Could not include {include_path}: {e}")
                    return f'<!-- Include failed for {include_path} -->'
            return f'<!-- Include not found: {include_path} -->'
        
        content = re.sub(r'\{%\s*include\s+["\']([^"\']+)["\']\s*%\}', replace_include, content)
        return content
    
    def process_template_logic(self, content, filename):
        """Process Flask template logic"""
        
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
        
        content = re.sub(
            r'\{%\s*if\s+current_user\s*%\}(.*?)\{%\s*endif\s*%\}',
            lambda m: m.group(1) if user else '',
            content,
            flags=re.DOTALL
        )
        
        content = content.replace('{{ current_user.full_name }}', user['full_name'])
        content = content.replace('{{ current_user.role or \'USER\' }}', user['role'])
        content = content.replace('{{ current_user.role }}', user['role'])
        content = content.replace('{{ current_user.role.lower() if current_user.role else \'default\' }}', user['role_lower'])
        
        return content
    
    def process_role_based_visibility(self, content):
        """Process role-based content visibility"""
        user = self.mock_user
        
        content = re.sub(
            r'\{%\s*if\s+current_user\s+and\s+current_user\.can_upload\(\)\s*%\}(.*?)\{%\s*endif\s*%\}',
            lambda m: m.group(1) if user and user['can_upload'] else '',
            content,
            flags=re.DOTALL
        )
        
        content = re.sub(
            r'\{%\s*if\s+current_user\s+and\s+current_user\.role\s*==\s*[\'"]CFO[\'"]\s*%\}(.*?)\{%\s*endif\s*%\}',
            lambda m: m.group(1) if user and user['role'] == 'CFO' else '',
            content,
            flags=re.DOTALL
        )
        
        return content
    
    def process_conditionals(self, content):
        """Process conditional statements"""
        content = re.sub(
            r'\{%\s*if\s+(.*?)\s*%\}(.*?)\{%\s*else\s*%\}(.*?)\{%\s*endif\s*%\}',
            lambda m: self.evaluate_condition(m.group(1), m.group(2), m.group(3)),
            content,
            flags=re.DOTALL
        )
        
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
        """Set active state for navigation"""
        content = re.sub(r'class="active"', '', content)
        
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
    
    def generate_asset_manifest(self):
        """Generate asset manifest for cache busting"""
        print("4. Generating asset manifest...")
        
        manifest_path = self.build_dir / 'asset-manifest.json'
        manifest_data = {
            'version': self.version_string,
            'timestamp': datetime.now().isoformat(),
            'method': self.cache_busting_method,
            'assets': self.asset_manifest
        }
        
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding='utf-8')
        print(f"   Asset manifest created: {len(self.asset_manifest)} assets")
    
    def create_cache_busting_config(self):
        """Create cache busting configuration"""
        print("5. Creating cache busting configuration...")
        
        config_path = self.build_dir / 'cache-busting-info.json'
        config_data = {
            'cache_busting_enabled': True,
            'method': self.cache_busting_method,
            'version': self.version_string,
            'generated_at': datetime.now().isoformat(),
            'force_refresh_urls': True,
            'browser_cache_duration': '0 seconds (forced refresh)'
        }
        
        config_path.write_text(json.dumps(config_data, indent=2), encoding='utf-8')
        
        # Create .nojekyll
        nojekyll_path = self.build_dir / '.nojekyll'
        nojekyll_path.write_text('')
        
        print("   Cache busting configuration created")


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate static site with cache busting')
    parser.add_argument('--method', choices=['timestamp', 'hash'], default='timestamp',
                       help='Cache busting method (default: timestamp)')
    
    args = parser.parse_args()
    
    generator = CacheBustingStaticGenerator()
    generator.cache_busting_method = args.method
    generator.version_string = generator.generate_version_string()
    
    generator.generate_with_cache_busting()
    
    print()
    print("Cache Busting Summary:")
    print(f"- Method: {generator.cache_busting_method}")
    print(f"- Version: {generator.version_string}")
    print(f"- Assets processed: {len(generator.asset_manifest)}")
    print("- All URLs now include cache-busting parameters")
    print("- Browsers will be forced to download latest assets")


if __name__ == '__main__':
    main()
