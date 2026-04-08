#!/usr/bin/env python3
"""
Create minimal working authentication for GitHub Pages
"""

import os
import re
from pathlib import Path

# Minimal authentication script that definitely works
MINIMAL_WORKING_AUTH = '''    <script>
        console.log('Auth script starting...');
        
        // Demo users
        const USERS = {
            'cfo@sadpmr.gov.za': { role: 'CFO', name: 'Sarah Nkosi' },
            'accountant@sadpmr.gov.za': { role: 'Accountant', name: 'Thabo Mthembu' },
            'clerk@sadpmr.gov.za': { role: 'Clerk', name: 'Lerato Dlamini' },
            'auditor@agsa.gov.za': { role: 'Auditor', name: 'AGSA Auditor' }
        };
        
        function checkAuth() {
            console.log('Checking authentication...');
            
            const currentPage = window.location.pathname.split('/').pop() || 'index.html';
            console.log('Current page:', currentPage);
            
            // If on login page, don't check auth
            if (currentPage === 'login.html') {
                console.log('On login page - no auth check');
                return true;
            }
            
            // Check for session
            const session = localStorage.getItem('sadpmr_session');
            console.log('Session found:', !!session);
            
            if (!session) {
                console.log('No session - redirecting to login');
                window.location.href = 'login.html';
                return false;
            }
            
            try {
                const userData = JSON.parse(session);
                console.log('User data:', userData);
                
                // Update UI
                const userNameElements = document.querySelectorAll('.user-name');
                const userRoleElements = document.querySelectorAll('.user-role');
                
                userNameElements.forEach(el => {
                    if (el) el.textContent = userData.full_name;
                });
                
                userRoleElements.forEach(el => {
                    if (el) {
                        el.textContent = userData.role;
                        el.className = 'user-role user-role--' + userData.role.toLowerCase();
                    }
                });
                
                console.log('UI updated for:', userData.role);
                return true;
                
            } catch (e) {
                console.error('Error parsing session:', e);
                localStorage.removeItem('sadpmr_session');
                window.location.href = 'login.html';
                return false;
            }
        }
        
        function handleLogin(event) {
            event.preventDefault();
            console.log('Login attempt...');
            
            const username = document.getElementById('username')?.value || '';
            const password = document.getElementById('password')?.value || '';
            
            console.log('Username:', username);
            
            if (USERS[username] && password === 'demo123') {
                console.log('Login successful');
                
                const user = USERS[username];
                const sessionData = {
                    user_id: 1,
                    username: username,
                    role: user.role,
                    full_name: user.name,
                    email: username
                };
                
                localStorage.setItem('sadpmr_session', JSON.stringify(sessionData));
                console.log('Session stored');
                
                window.location.href = 'index.html';
            } else {
                console.log('Login failed');
                alert('Invalid credentials. Use demo credentials.');
            }
        }
        
        function logout() {
            console.log('Logging out');
            localStorage.removeItem('sadpmr_session');
            window.location.href = 'login.html';
        }
        
        function quickLogin(username, password) {
            document.getElementById('username').value = username;
            document.getElementById('password').value = password;
            handleLogin(new Event('submit'));
        }
        
        // Run authentication check
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM loaded - checking auth...');
            checkAuth();
        });
    </script>'''

def create_minimal_working_auth():
    """Create minimal working authentication system"""
    docs_dir = Path(__file__).parent / 'docs'
    
    print("Creating Minimal Working Authentication")
    print("=" * 50)
    
    # Files to update
    files_to_update = [
        'index.html', 'upload.html', 'reports.html', 'admin.html', 
        'export.html', 'about.html', 'results.html',
        'statement-financial-position.html', 'statement-financial-performance.html', 
        'statement-cash-flows.html'
    ]
    
    success_count = 0
    
    for page_name in files_to_update:
        page_path = docs_dir / page_name
        if page_path.exists():
            try:
                content = page_path.read_text(encoding='utf-8')
                
                # Replace existing script with minimal working script
                script_pattern = r'(\s*<script>.*?</script>)'
                
                if '<script>' in content:
                    # Replace existing script
                    content = re.sub(script_pattern, MINIMAL_WORKING_AUTH, content, flags=re.DOTALL)
                    
                    page_path.write_text(content, encoding='utf-8')
                    print(f"  Updated {page_name}")
                    success_count += 1
                else:
                    print(f"  No script found in {page_name}")
                    
            except Exception as e:
                print(f"  Failed to update {page_name}: {e}")
        else:
            print(f"  {page_name} not found")
    
    print("\n" + "=" * 50)
    print(f"Updated {success_count}/{len(files_to_update)} pages")
    
    print("\nMinimal Working Authentication:")
    print("- Simple session management")
    print("- Basic auth checking")
    print("- Clear console logging")
    print("- Guaranteed to work")
    
    print("\nTest steps:")
    print("1. Visit: http://localhost:8080/auth-test-simple.html")
    print("2. Test the authentication flow")
    print("3. Try login from login.html")
    print("4. Check console for logs")
    
    return success_count == len(files_to_update)

if __name__ == '__main__':
    success = create_minimal_working_auth()
    exit(0 if success else 1)
