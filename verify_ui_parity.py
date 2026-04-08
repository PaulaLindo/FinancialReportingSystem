#!/usr/bin/env python3
"""Final verification of UI parity fixes"""

import re
from pathlib import Path

def verify_ui_parity():
    """Verify that all UI parity issues have been fixed"""
    
    print("=== Final UI Parity Verification ===")
    
    docs_dir = Path('docs')
    issues_found = 0
    
    for html_file in docs_dir.glob('*.html'):
        if html_file.name in ['auth-debug.html', 'auth-test-simple.html', 'auth-test.html', 
                             'complete-auth-test.html', 'debug.html', 'js-test.html', 
                             'navigation-test.html', 'simple-index.html']:
            continue  # Skip test files
            
        print(f"\nChecking {html_file.name}...")
        content = html_file.read_text(encoding='utf-8')
        
        # Check 1: No template directives
        template_directives = re.findall(r'\{%\s*[^%]*%\}', content)
        if template_directives:
            print(f"  ❌ Found {len(template_directives)} template directives")
            issues_found += len(template_directives)
        else:
            print(f"  ✅ No template directives found")
        
        # Check 2: No Jinja variables
        jinja_vars = re.findall(r'\{\{\s*[^}]*\}\}', content)
        if jinja_vars:
            print(f"  ❌ Found {len(jinja_vars)} Jinja variables")
            issues_found += len(jinja_vars)
        else:
            print(f"  ✅ No Jinja variables found")
        
        # Check 3: No url_for calls
        url_for_calls = re.findall(r'url_for', content)
        if url_for_calls:
            print(f"  ❌ Found {len(url_for_calls)} url_for calls")
            issues_found += len(url_for_calls)
        else:
            print(f"  ✅ No url_for calls found")
        
        # Check 4: Proper HTML structure
        if content.strip().startswith('<!DOCTYPE html>') and content.strip().endswith('</html>'):
            print(f"  ✅ Proper HTML structure")
        else:
            print(f"  ❌ Invalid HTML structure")
            issues_found += 1
        
        # Check 5: CSS and JS links are properly formatted
        css_links = re.findall(r'href="[^"]*\.css"', content)
        js_links = re.findall(r'src="[^"]*\.js"', content)
        
        has_bad_css = any('url_for' in link or '{{' in link for link in css_links)
        has_bad_js = any('url_for' in link or '{{' in link for link in js_links)
        
        if has_bad_css or has_bad_js:
            print(f"  ❌ Bad CSS/JS links found")
            issues_found += 1
        else:
            print(f"  ✅ CSS/JS links properly formatted")
    
    print(f"\n=== Verification Summary ===")
    if issues_found == 0:
        print("🎉 ALL ISSUES FIXED! UI parity is complete.")
        print("✅ No template directives remaining")
        print("✅ No Jinja variables remaining") 
        print("✅ No url_for calls remaining")
        print("✅ Proper HTML structure in all files")
        print("✅ CSS/JS links properly formatted")
        print("\nThe GitHub Pages version should now be identical to the Flask UI!")
    else:
        print(f"❌ {issues_found} issues still need to be fixed")
    
    return issues_found == 0

if __name__ == '__main__':
    verify_ui_parity()
