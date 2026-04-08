#!/usr/bin/env python3
"""
Complete GitHub Pages Cleanup Script
Performs full repository purge, cache busting, and fresh deployment
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
import json

class GitHubPagesCleanup:
    def __init__(self, base_dir=None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent
        self.docs_dir = self.base_dir / 'docs'
        self.build_dir = self.base_dir / 'build'
        
    def perform_complete_cleanup(self, force=False):
        """Perform complete cleanup and fresh deployment"""
        print("=== Complete GitHub Pages Cleanup ===")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Base Directory: {self.base_dir}")
        print()
        
        try:
            # 1. Repository Purge
            self.repository_purge()
            
            # 2. Local Cleanup
            self.local_cleanup()
            
            # 3. Fresh Static Generation with Cache Busting
            self.fresh_generation_with_cache_busting()
            
            # 4. Empty Commit Trick
            if force:
                self.empty_commit_trick()
            
            # 5. Final Deployment
            self.final_deployment()
            
            print("\n=== Cleanup Complete ===")
            print("Your GitHub Pages site will reflect the latest changes immediately!")
            
        except Exception as e:
            print(f"\nERROR: Cleanup failed: {e}")
            return False
        
        return True
    
    def repository_purge(self):
        """Step 1: Complete repository purge"""
        print("1. Repository Purge")
        print("-" * 40)
        
        # Check if docs directory exists and purge it
        if self.docs_dir.exists():
            print(f"   Deleting docs directory: {self.docs_dir}")
            shutil.rmtree(self.docs_dir)
            print("   docs directory deleted")
        else:
            print("   docs directory not found (already clean)")
        
        # Create fresh docs directory
        self.docs_dir.mkdir(exist_ok=True)
        
        # Create .gitkeep to ensure directory is tracked
        (self.docs_dir / '.gitkeep').write_text('')
        
        print("   Fresh docs directory created")
        print()
    
    def local_cleanup(self):
        """Step 2: Complete local cleanup"""
        print("2. Local Cleanup")
        print("-" * 40)
        
        # Delete build directory if exists
        if self.build_dir.exists():
            print(f"   Deleting build directory: {self.build_dir}")
            shutil.rmtree(self.build_dir)
            print("   build directory deleted")
        else:
            print("   build directory not found (already clean)")
        
        # Clean up any other generated directories
        cleanup_dirs = [
            self.base_dir / 'dist',
            self.base_dir / 'output',
            self.base_dir / 'static_build'
        ]
        
        for cleanup_dir in cleanup_dirs:
            if cleanup_dir.exists():
                print(f"   Deleting: {cleanup_dir}")
                shutil.rmtree(cleanup_dir)
        
        # Clean up temporary files
        temp_files = [
            self.base_dir / '.DS_Store',
            self.base_dir / 'Thumbs.db'
        ]
        
        for temp_file in temp_files:
            if temp_file.exists():
                temp_file.unlink()
                print(f"   Deleted temp file: {temp_file}")
        
        print("   Local cleanup complete")
        print()
    
    def fresh_generation_with_cache_busting(self):
        """Step 3: Fresh static generation with cache busting"""
        print("3. Fresh Generation with Cache Busting")
        print("-" * 40)
        
        # Import and run the enhanced static generator with cache busting
        try:
            sys.path.insert(0, str(self.base_dir))
            from freeze_with_cache_busting import CacheBustingStaticGenerator
            
            generator = CacheBustingStaticGenerator(self.base_dir)
            generator.generate_with_cache_busting()
            
            print("   Fresh static generation with cache busting complete")
            
        except ImportError:
            print("   Cache busting generator not found, using standard generator")
            # Fallback to standard generator
            from freeze_with_relative_urls import RelativeURLStaticGenerator
            
            generator = RelativeURLStaticGenerator(self.base_dir)
            generator.generate_static_site()
            
            print("   Standard static generation complete")
        
        print()
    
    def empty_commit_trick(self):
        """Step 4: Empty commit trick to trigger fresh build"""
        print("4. Empty Commit Trick")
        print("-" * 40)
        
        try:
            # Check if we're in a git repository
            result = subprocess.run(['git', 'status'], 
                                  cwd=self.base_dir, 
                                  capture_output=True, 
                                  text=True)
            
            if result.returncode != 0:
                print("   Not in a git repository")
                return
            
            # Create empty commit to trigger GitHub Pages rebuild
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            commit_message = f"trigger-github-pages-rebuild-{timestamp}"
            
            print(f"   Creating empty commit: {commit_message}")
            
            # Allow empty commit
            subprocess.run(['git', 'commit', '--allow-empty', '-m', commit_message], 
                         cwd=self.base_dir, 
                         check=True)
            
            print("   Empty commit created successfully")
            
        except subprocess.CalledProcessError as e:
            print(f"   Error creating empty commit: {e}")
        
        print()
    
    def final_deployment(self):
        """Step 5: Final deployment"""
        print("5. Final Deployment")
        print("-" * 40)
        
        # Copy fresh build to docs
        if self.build_dir.exists():
            print("   Copying fresh build to docs...")
            
            # Remove docs directory contents (except .gitkeep)
            for item in self.docs_dir.iterdir():
                if item.name != '.gitkeep':
                    if item.is_file():
                        item.unlink()
                    else:
                        shutil.rmtree(item)
            
            # Copy build contents to docs
            for item in self.build_dir.iterdir():
                if item.is_file():
                    shutil.copy2(item, self.docs_dir / item.name)
                else:
                    shutil.copytree(item, self.docs_dir / item.name)
            
            print("   Build copied to docs directory")
        
        print("   Final deployment ready")
        print()


def main():
    """Main execution function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Complete GitHub Pages cleanup and fresh deployment')
    parser.add_argument('--force', action='store_true', 
                       help='Force complete cleanup including empty commit')
    parser.add_argument('--purge-only', action='store_true', 
                       help='Only perform repository purge')
    parser.add_argument('--local-only', action='store_true', 
                       help='Only perform local cleanup')
    
    args = parser.parse_args()
    
    cleanup = GitHubPagesCleanup()
    
    if args.purge_only:
        cleanup.repository_purge()
    elif args.local_only:
        cleanup.local_cleanup()
    else:
        cleanup.perform_complete_cleanup(force=args.force)
        
        print("\nNext Steps:")
        print("1. Review changes: git status")
        print("2. Commit changes: git add . && git commit -m 'Fresh deployment with cache busting'")
        print("3. Push to GitHub: git push origin main")
        print("4. Wait 2-5 minutes for GitHub Pages to rebuild")
        print("5. Clear browser cache and visit your site")


if __name__ == '__main__':
    main()
