#!/usr/bin/env python3
"""
Test script to verify GitHub Pages setup locally
Checks all main pages for proper structure and links
"""

import requests
import time
from urllib.parse import urljoin

def test_page(url, page_name):
    """Test a single page for basic functionality"""
    try:
        response = requests.get(url, timeout=10)
        
        print(f"\n📄 Testing {page_name}: {url}")
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            content = response.text
            
            # Check for essential elements
            checks = {
                'DOCTYPE declaration': '<!DOCTYPE html>' in content,
                'CSS stylesheet': 'css/styles.css' in content,
                'Viewport meta': 'viewport' in content,
                'Language attribute': 'lang="en"' in content,
                'Navigation': 'navbar' in content,
                'Footer': 'footer' in content
            }
            
            all_passed = True
            for check_name, passed in checks.items():
                status = "✓" if passed else "✗"
                print(f"   {status} {check_name}")
                if not passed:
                    all_passed = False
            
            if all_passed:
                print(f"   ✅ {page_name} looks good!")
            else:
                print(f"   ⚠️  {page_name} has some issues")
                
            return all_passed
        else:
            print(f"   ❌ Failed to load: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Test all main pages"""
    base_url = "http://localhost:8080"
    
    print("🧪 Testing GitHub Pages Setup Locally")
    print("=" * 50)
    
    # Main pages to test
    pages = [
        ("index.html", "Dashboard"),
        ("upload.html", "Upload Page"),
        ("about.html", "About Page"),
        ("login.html", "Login Page"),
        ("admin.html", "Admin Page"),
        ("reports.html", "Reports Page"),
        ("results.html", "Results Page"),
        ("statement-financial-position.html", "Financial Position"),
        ("statement-financial-performance.html", "Financial Performance"),
        ("statement-cash-flows.html", "Cash Flows")
    ]
    
    results = []
    
    for page_url, page_name in pages:
        full_url = urljoin(base_url, page_url)
        success = test_page(full_url, page_name)
        results.append((page_name, success))
        time.sleep(0.5)  # Small delay between requests
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for page_name, success in results:
        status = "✅" if success else "❌"
        print(f"{status} {page_name}")
    
    print(f"\n🎯 Results: {passed}/{total} pages passed")
    
    if passed == total:
        print("🎉 All pages are ready for GitHub Pages!")
    else:
        print("⚠️  Some pages need attention before deploying")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
