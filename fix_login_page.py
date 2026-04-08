#!/usr/bin/env python3
"""
Fix login page - remove auth script and empty alert
"""

import os
import re
from pathlib import Path

# Login page script (only login functionality, no auth checking)
LOGIN_SCRIPT = '''    <script>
        // Login function for GitHub Pages
        function handleLoginForm(event, redirectUrl) {
            event.preventDefault();
            console.log('GitHub Pages login form submitted');
            
            const username = document.getElementById('username')?.value || '';
            const password = document.getElementById('password')?.value || '';
            
            console.log('Login attempt:', username);
            
            // Demo credentials
            const demoUsers = {
                'cfo@sadpmr.gov.za': { role: 'CFO', name: 'Sarah Nkosi' },
                'accountant@sadpmr.gov.za': { role: 'Accountant', name: 'John Smith' },
                'clerk@sadpmr.gov.za': { role: 'Clerk', name: 'Mike Davis' },
                'auditor@agsa.gov.za': { role: 'Auditor', name: 'Patience Moyo' }
            };
            
            if (demoUsers[username] && password === 'demo123') {
                console.log('Login successful');
                const user = demoUsers[username];
                
                // Create auth token (email|role)
                const authToken = encodeURIComponent(username + '|' + user.role);
                
                // Store in localStorage
                localStorage.setItem('auth_token', authToken);
                
                // Redirect to role-specific default page
                const redirectTargets = {
                    'CFO': 'index.html',
                    'Accountant': 'index.html',
                    'Clerk': 'upload.html',
                    'Auditor': 'reports.html'
                };
                
                const redirectTarget = redirectTargets[user.role] || 'index.html';
                console.log('Redirecting to:', redirectTarget);
                window.location.href = redirectTarget + '?auth=' + authToken;
            } else {
                console.log('Login failed');
                alert('Invalid credentials. Use demo credentials shown below.');
            }
        }

        // Quick login function
        function quickLogin(username, password) {
            document.getElementById('username').value = username;
            document.getElementById('password').value = password;
            handleLoginForm(new Event('submit'), 'index.html');
        }
    </script>'''

def fix_login_page():
    """Fix login page - remove auth script and empty alert"""
    docs_dir = Path(__file__).parent / 'docs'
    
    print("Fixing Login Page")
    print("=" * 50)
    
    login_path = docs_dir / 'login.html'
    if login_path.exists():
        try:
            content = login_path.read_text(encoding='utf-8')
            
            # Remove empty alert div
            content = re.sub(r'\s*<div class="alert alert-">\s*\n\s*\s*\s*</div>', '', content)
            
            # Remove any existing authentication script
            content = re.sub(r'\s*<script>.*?checkAuthGitHubPages.*?</script>', '', content, flags=re.DOTALL)
            
            # Add only login script before closing head tag
            content = content.replace('</head>', LOGIN_SCRIPT + '</head>')
            
            login_path.write_text(content, encoding='utf-8')
            print("  Fixed login.html")
            print("  - Removed empty alert")
            print("  - Removed authentication script")
            print("  - Added login-only script")
            
        except Exception as e:
            print(f"  Failed to fix login.html: {e}")
            return False
    else:
        print("  login.html not found")
        return False
    
    print("\n" + "=" * 50)
    print("Login page fixed!")
    
    print("\nFeatures:")
    print("- No authentication checking on login page")
    print("- No empty alerts")
    print("- Clean login form")
    print("- Proper redirect after login")
    
    print("\nTest steps:")
    print("1. Visit: http://localhost:8080/login.html")
    print("2. Should see clean login form")
    print("3. Login with demo credentials")
    print("4. Should redirect to role-specific page")
    
    return True

if __name__ == '__main__':
    success = fix_login_page()
    exit(0 if success else 1)
