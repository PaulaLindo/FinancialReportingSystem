#!/usr/bin/env python3
"""
Complete GitHub Pages Deployment Script
Automates the entire process from Flask to GitHub Pages deployment
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from datetime import datetime
import webbrowser

class GitHubPagesDeployer:
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.docs_dir = self.base_dir / 'docs'
        
    def deploy(self, auto_commit=False, auto_push=False, open_browser=True):
        """Complete deployment process"""
        print("🚀 GitHub Pages Deployment - SADPMR Financial Reporting System")
        print("=" * 70)
        print(f"📁 Project Directory: {self.base_dir}")
        print(f"📅 Deployment Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        try:
            # Step 1: Generate static site
            self.generate_static_site()
            
            # Step 2: Verify deployment readiness
            self.verify_deployment_readiness()
            
            # Step 3: Git operations (optional)
            if auto_commit:
                self.commit_changes()
            
            if auto_push:
                self.push_to_github()
            
            # Step 4: Provide deployment instructions
            self.show_deployment_instructions()
            
            # Step 5: Open browser if requested
            if open_browser:
                self.open_preview()
                
        except Exception as e:
            print(f"❌ Deployment failed: {e}")
            return False
        
        return True
    
    def generate_static_site(self):
        """Generate the static site"""
        print("1. 🔄 Generating static site...")
        
        # Import and run the static generator
        try:
            sys.path.insert(0, str(self.base_dir))
            from freeze_flask_app import FlaskStaticGenerator
            
            generator = FlaskStaticGenerator(self.base_dir)
            generator.generate_static_site()
            
            print("   ✅ Static site generated successfully")
            
        except ImportError as e:
            print(f"   ❌ Failed to import static generator: {e}")
            raise
        except Exception as e:
            print(f"   ❌ Failed to generate static site: {e}")
            raise
    
    def verify_deployment_readiness(self):
        """Verify that the site is ready for deployment"""
        print("2. 🔍 Verifying deployment readiness...")
        
        # Check if docs directory exists and has files
        if not self.docs_dir.exists():
            raise Exception("docs directory not found")
        
        html_files = list(self.docs_dir.glob('*.html'))
        css_files = list((self.docs_dir / 'css').glob('*.css')) if (self.docs_dir / 'css').exists() else []
        js_files = list((self.docs_dir / 'js').glob('*.js')) if (self.docs_dir / 'js').exists() else []
        
        print(f"   📄 HTML files: {len(html_files)}")
        print(f"   🎨 CSS files: {len(css_files)}")
        print(f"   📜 JavaScript files: {len(js_files)}")
        
        # Check for essential files
        essential_files = ['index.html']
        for file in essential_files:
            if not (self.docs_dir / file).exists():
                raise Exception(f"Essential file missing: {file}")
        
        # Check .nojekyll file
        nojekyll_path = self.docs_dir / '.nojekyll'
        if not nojekyll_path.exists():
            nojekyll_path.write_text('')
            print("   ✅ Created .nojekyll file")
        
        print("   ✅ Deployment verification passed")
    
    def commit_changes(self, message=None):
        """Commit changes to git"""
        print("3. 📝 Committing changes to git...")
        
        if not message:
            message = f"Update GitHub Pages static site - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        try:
            # Check if we're in a git repository
            result = subprocess.run(['git', 'status'], 
                                  cwd=self.base_dir, 
                                  capture_output=True, 
                                  text=True)
            
            if result.returncode != 0:
                raise Exception("Not in a git repository")
            
            # Add docs directory
            subprocess.run(['git', 'add', 'docs/'], 
                         cwd=self.base_dir, 
                         check=True)
            
            # Check if there are changes to commit
            result = subprocess.run(['git', 'diff', '--cached', '--quiet'], 
                                  cwd=self.base_dir)
            
            if result.returncode == 0:
                print("   ℹ️  No changes to commit")
                return
            
            # Commit changes
            subprocess.run(['git', 'commit', '-m', message], 
                         cwd=self.base_dir, 
                         check=True)
            
            print(f"   ✅ Changes committed: {message}")
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"Git commit failed: {e}")
        except Exception as e:
            raise Exception(f"Git operation failed: {e}")
    
    def push_to_github(self):
        """Push changes to GitHub"""
        print("4. 🚀 Pushing to GitHub...")
        
        try:
            # Get current branch
            result = subprocess.run(['git', 'branch', '--show-current'], 
                                  cwd=self.base_dir, 
                                  capture_output=True, 
                                  text=True)
            current_branch = result.stdout.strip()
            
            # Push to GitHub
            subprocess.run(['git', 'push', 'origin', current_branch], 
                         cwd=self.base_dir, 
                         check=True)
            
            print(f"   ✅ Pushed to GitHub (branch: {current_branch})")
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"Git push failed: {e}")
    
    def show_deployment_instructions(self):
        """Show GitHub Pages configuration instructions"""
        print("5. 📋 GitHub Pages Configuration Instructions:")
        print()
        print("   To complete deployment, follow these steps:")
        print()
        print("   1. Go to your GitHub repository")
        print("   2. Click on 'Settings' tab")
        print("   3. Scroll down to 'Pages' section")
        print("   4. Under 'Build and deployment', select:")
        print("      - Source: 'Deploy from branch'")
        print("      - Branch: 'main'")
        print("      - Folder: '/docs'")
        print("   5. Click 'Save'")
        print()
        print("   Your site will be available at:")
        print("   https://[your-username].github.io/FinancialReportingSystem/")
        print()
        print("   ⏱️  Deployment may take 1-2 minutes after saving...")
        print()
    
    def open_preview(self):
        """Open local preview in browser"""
        print("6. 🌐 Opening local preview...")
        
        index_file = self.docs_dir / 'index.html'
        if index_file.exists():
            try:
                webbrowser.open(f'file://{index_file.absolute()}')
                print("   ✅ Opened local preview in browser")
            except Exception as e:
                print(f"   ⚠️  Could not open browser: {e}")
        else:
            print("   ⚠️  index.html not found for preview")


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Deploy SADPMR Financial Reporting System to GitHub Pages')
    parser.add_argument('--auto-commit', action='store_true', 
                       help='Automatically commit changes to git')
    parser.add_argument('--auto-push', action='store_true', 
                       help='Automatically push changes to GitHub')
    parser.add_argument('--no-browser', action='store_true', 
                       help='Do not open browser preview')
    
    args = parser.parse_args()
    
    deployer = GitHubPagesDeployer()
    
    try:
        success = deployer.deploy(
            auto_commit=args.auto_commit,
            auto_push=args.auto_push,
            open_browser=not args.no_browser
        )
        
        if success:
            print()
            print("🎉 Deployment process completed successfully!")
            print()
            print("📝 Summary:")
            print("   ✅ Static site generated")
            print("   ✅ Deployment verification passed")
            if args.auto_commit:
                print("   ✅ Changes committed to git")
            if args.auto_push:
                print("   ✅ Changes pushed to GitHub")
            print("   ✅ Local preview opened")
            print()
            print("🌐 Next: Configure GitHub Pages in your repository settings")
        else:
            print("❌ Deployment failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Deployment cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
