#!/usr/bin/env python3
"""
Windows-Compatible GitHub Pages Cleanup
Handles file locking issues and provides robust cleanup
"""

import os
import sys
import shutil
import subprocess
import time
from pathlib import Path
from datetime import datetime

class WindowsGitHubPagesCleanup:
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.docs_dir = self.base_dir / 'docs'
        self.build_dir = self.base_dir / 'build'
    
    def safe_delete_directory(self, directory):
        """Safely delete directory with retry logic"""
        if not directory.exists():
            return True
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Try to remove directory
                shutil.rmtree(directory)
                return True
            except PermissionError as e:
                print(f"   Attempt {attempt + 1}: {e}")
                
                if attempt < max_retries - 1:
                    # Wait and retry
                    time.sleep(1)
                    
                    # Try to force unlock files on Windows
                    try:
                        subprocess.run(['taskkill', '/F', '/IM', 'python.exe'], 
                                     capture_output=True, check=False)
                    except:
                        pass
                else:
                    print(f"   Failed to delete {directory} after {max_retries} attempts")
                    return False
        
        return False
    
    def repository_purge_windows(self):
        """Windows-compatible repository purge"""
        print("1. Repository Purge (Windows)")
        print("-" * 40)
        
        # Try to delete docs directory
        if self.docs_dir.exists():
            print(f"   Attempting to delete docs directory...")
            
            if self.safe_delete_directory(self.docs_dir):
                print("   docs directory deleted successfully")
            else:
                print("   Could not delete docs directory, trying alternative method...")
                
                # Alternative: Delete contents only
                try:
                    for item in self.docs_dir.iterdir():
                        if item.is_file():
                            item.unlink()
                        else:
                            self.safe_delete_directory(item)
                    print("   docs contents deleted (directory preserved)")
                except Exception as e:
                    print(f"   Alternative method failed: {e}")
        else:
            print("   docs directory not found (already clean)")
        
        # Create fresh docs directory
        self.docs_dir.mkdir(exist_ok=True)
        
        # Create .gitkeep
        (self.docs_dir / '.gitkeep').write_text('')
        
        print("   Fresh docs directory created")
        print()
    
    def local_cleanup_windows(self):
        """Windows-compatible local cleanup"""
        print("2. Local Cleanup (Windows)")
        print("-" * 40)
        
        # Clean build directory
        if self.build_dir.exists():
            print(f"   Deleting build directory...")
            self.safe_delete_directory(self.build_dir)
        else:
            print("   build directory not found (already clean)")
        
        # Clean other directories
        cleanup_dirs = [
            self.base_dir / 'dist',
            self.base_dir / 'output',
            self.base_dir / 'static_build'
        ]
        
        for cleanup_dir in cleanup_dirs:
            if cleanup_dir.exists():
                print(f"   Deleting: {cleanup_dir.name}")
                self.safe_delete_directory(cleanup_dir)
        
        # Clean temporary files
        temp_files = list(self.base_dir.rglob('.DS_Store')) + list(self.base_dir.rglob('Thumbs.db'))
        for temp_file in temp_files:
            try:
                temp_file.unlink()
                print(f"   Deleted: {temp_file.name}")
            except:
                pass
        
        print("   Local cleanup complete")
        print()
    
    def generate_fresh_with_cache_busting(self):
        """Generate fresh static site with cache busting"""
        print("3. Fresh Generation with Cache Busting")
        print("-" * 40)
        
        try:
            # Import cache busting generator
            sys.path.insert(0, str(self.base_dir))
            from freeze_with_cache_busting import CacheBustingStaticGenerator
            
            generator = CacheBustingStaticGenerator(self.base_dir)
            generator.generate_with_cache_busting()
            
            print("   Fresh generation with cache busting complete")
            
        except ImportError as e:
            print(f"   Cache busting generator not found: {e}")
            print("   Using standard generator...")
            
            try:
                from freeze_with_relative_urls import RelativeURLStaticGenerator
                
                generator = RelativeURLStaticGenerator(self.base_dir)
                generator.generate_static_site()
                
                print("   Standard generation complete")
            except ImportError as e2:
                print(f"   Standard generator not found: {e2}")
                print("   Please ensure generator scripts are available")
        
        print()
    
    def copy_to_docs_windows(self):
        """Windows-safe copy to docs directory"""
        print("4. Copy to docs directory")
        print("-" * 40)
        
        if not self.build_dir.exists():
            print("   Build directory not found, skipping copy")
            return
        
        # Clear docs directory (except .gitkeep)
        for item in self.docs_dir.iterdir():
            if item.name != '.gitkeep':
                try:
                    if item.is_file():
                        item.unlink()
                    else:
                        self.safe_delete_directory(item)
                except Exception as e:
                    print(f"   Warning: Could not delete {item.name}: {e}")
        
        # Copy build contents to docs
        copied_count = 0
        for item in self.build_dir.iterdir():
            try:
                if item.is_file():
                    shutil.copy2(item, self.docs_dir / item.name)
                    copied_count += 1
                else:
                    shutil.copytree(item, self.docs_dir / item.name)
                    copied_count += 1
            except Exception as e:
                print(f"   Warning: Could not copy {item.name}: {e}")
        
        print(f"   Copied {copied_count} items to docs directory")
        print()
    
    def create_empty_commit_windows(self):
        """Create empty commit to trigger rebuild"""
        print("5. Empty Commit Trick")
        print("-" * 40)
        
        try:
            # Check git status
            result = subprocess.run(['git', 'status'], 
                                  cwd=self.base_dir, 
                                  capture_output=True, 
                                  text=True)
            
            if result.returncode != 0:
                print("   Not in a git repository")
                return
            
            # Create empty commit
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            commit_message = f"trigger-github-pages-rebuild-{timestamp}"
            
            print(f"   Creating empty commit: {commit_message}")
            
            subprocess.run(['git', 'commit', '--allow-empty', '-m', commit_message], 
                         cwd=self.base_dir, 
                         check=True)
            
            print("   Empty commit created successfully")
            
        except subprocess.CalledProcessError as e:
            print(f"   Error creating empty commit: {e}")
        except Exception as e:
            print(f"   Unexpected error: {e}")
        
        print()
    
    def perform_windows_cleanup(self, create_empty_commit=False):
        """Perform complete Windows cleanup"""
        print("=== Windows GitHub Pages Cleanup ===")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Base Directory: {self.base_dir}")
        print()
        
        try:
            # 1. Repository purge
            self.repository_purge_windows()
            
            # 2. Local cleanup
            self.local_cleanup_windows()
            
            # 3. Fresh generation
            self.generate_fresh_with_cache_busting()
            
            # 4. Copy to docs
            self.copy_to_docs_windows()
            
            # 5. Empty commit (optional)
            if create_empty_commit:
                self.create_empty_commit_windows()
            
            print("=== Windows Cleanup Complete ===")
            print("Your GitHub Pages site is ready for fresh deployment!")
            
        except Exception as e:
            print(f"\nERROR: Cleanup failed: {e}")
            return False
        
        return True


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Windows GitHub Pages cleanup')
    parser.add_argument('--empty-commit', action='store_true', 
                       help='Create empty commit to trigger rebuild')
    parser.add_argument('--purge-only', action='store_true', 
                       help='Only perform repository purge')
    parser.add_argument('--local-only', action='store_true', 
                       help='Only perform local cleanup')
    
    args = parser.parse_args()
    
    cleanup = WindowsGitHubPagesCleanup()
    
    if args.purge_only:
        cleanup.repository_purge_windows()
    elif args.local_only:
        cleanup.local_cleanup_windows()
    else:
        cleanup.perform_windows_cleanup(create_empty_commit=args.empty_commit)
        
        print("\nNext Steps:")
        print("1. Review changes: git status")
        print("2. Commit changes: git add docs/ && git commit -m 'Fresh deployment'")
        print("3. Push to GitHub: git push origin main")
        print("4. Wait 2-5 minutes for GitHub Pages to rebuild")
        print("5. Clear browser cache and visit your site")


if __name__ == '__main__':
    main()
