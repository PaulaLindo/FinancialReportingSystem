#!/usr/bin/env python3
"""
Add authentication check to all protected pages (except login.html)
"""

import os
import re
from pathlib import Path

# Authentication script to add to each page
AUTH_SCRIPT = '''    <script>
        // Check authentication on page load
        function checkAuthentication() {
            const currentUser = sessionStorage.getItem('demoUser');
            if (!currentUser) {
                // Not logged in, redirect to login
                window.location.href = 'login.html';
                return false;
            }
            return JSON.parse(currentUser);
        }

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

        function logout() {
            sessionStorage.removeItem('demoUser');
            window.location.href = 'login.html';
        }

        // Check authentication immediately
        document.addEventListener('DOMContentLoaded', function() {
            const user = checkAuthentication();
            if (user) {
                // Update user info in navbar
                const userNameElements = document.querySelectorAll('.user-name');
                const userRoleElements = document.querySelectorAll('.user-role');
                
                userNameElements.forEach(el => {
                    if (el) el.textContent = user.name;
                });
                
                userRoleElements.forEach(el => {
                    if (el) {
                        el.textContent = user.role;
                        el.className = `user-role user-role--${user.role.toLowerCase()}`;
                    }
                });
            }
        });
    </script>'''

# Pages that need authentication (protected pages)
PROTECTED_PAGES = [
    'index.html',
    'upload.html', 
    'about.html',
    'admin.html',
    'reports.html',
    'results.html',
    'export.html',
    'statement-financial-position.html',
    'statement-financial-performance.html',
    'statement-cash-flows.html'
]

def add_authentication_to_page(page_path):
    """Add authentication check to a specific page"""
    try:
        content = page_path.read_text(encoding='utf-8')
        
        # Skip if already has authentication
        if 'checkAuthentication' in content:
            print(f"✓ {page_path.name} already has authentication")
            return True
        
        # Find existing script tag and replace it
        script_pattern = r'(\s*<script>.*?</script>)'
        
        if '<script>' in content:
            # Replace existing script with authentication script
            content = re.sub(script_pattern, AUTH_SCRIPT, content, flags=re.DOTALL)
        else:
            # Add script before closing head tag
            content = content.replace('</head>', AUTH_SCRIPT + '</head>')
        
        # Update logout button
        content = re.sub(
            r'<a href="logout\.html" class="logout-btn">Logout</a>',
            '<a href="#" onclick="logout(); return false;" class="logout-btn">Logout</a>',
            content
        )
        
        page_path.write_text(content, encoding='utf-8')
        print(f"✓ Added authentication to {page_path.name}")
        return True
        
    except Exception as e:
        print(f"✗ Failed to process {page_path.name}: {e}")
        return False

def main():
    """Add authentication to all protected pages"""
    docs_dir = Path(__file__).parent / 'docs'
    
    print("🔐 Adding Authentication to Protected Pages")
    print("=" * 50)
    
    success_count = 0
    total_count = len(PROTECTED_PAGES)
    
    for page_name in PROTECTED_PAGES:
        page_path = docs_dir / page_name
        if page_path.exists():
            if add_authentication_to_page(page_path):
                success_count += 1
        else:
            print(f"⚠️  {page_name} not found")
    
    print("\n" + "=" * 50)
    print(f"✅ Authentication added to {success_count}/{total_count} pages")
    
    if success_count == total_count:
        print("\n🎉 All protected pages now require authentication!")
        print("\nNext steps:")
        print("1. Test locally: python -m http.server 8080")
        print("2. Visit: http://localhost:8080")
        print("3. Should redirect to login.html")
        print("4. Login with demo credentials")
        print("5. Access any protected page")
    else:
        print(f"\n⚠️  {total_count - success_count} pages had issues")
    
    return success_count == total_count

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
