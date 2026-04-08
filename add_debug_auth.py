#!/usr/bin/env python3
"""
Add debug logging to authentication scripts to verify they're running
"""

import os
import re
from pathlib import Path

# Authentication script with debug logging
DEBUG_AUTH_SCRIPT = '''    <script>
        console.log('=== AUTH SCRIPT LOADING ===');
        console.log('Current page:', window.location.pathname);
        console.log('User agent:', navigator.userAgent);
        
        // Add visible debug indicator
        function addDebugIndicator() {
            const indicator = document.createElement('div');
            indicator.id = 'auth-debug-indicator';
            indicator.style.cssText = `
                position: fixed;
                top: 10px;
                right: 10px;
                background: #ff6b6b;
                color: white;
                padding: 5px 10px;
                border-radius: 5px;
                font-size: 12px;
                z-index: 9999;
                font-family: monospace;
            `;
            indicator.textContent = 'Auth: Loading...';
            document.body.appendChild(indicator);
            return indicator;
        }
        
        function updateDebugIndicator(message, color = '#ff6b6b') {
            const indicator = document.getElementById('auth-debug-indicator');
            if (indicator) {
                indicator.textContent = message;
                indicator.style.background = color;
            }
        }
        
        // Demo users
        const DEMO_USERS = {
            'cfo@sadpmr.gov.za': { role: 'CFO', name: 'Sarah Nkosi' },
            'accountant@sadpmr.gov.za': { role: 'Accountant', name: 'Thabo Mthembu' },
            'clerk@sadpmr.gov.za': { role: 'Clerk', name: 'Lerato Dlamini' },
            'auditor@agsa.gov.za': { role: 'Auditor', name: 'AGSA Auditor' }
        };
        
        function checkAuth() {
            console.log('=== CHECKING AUTHENTICATION ===');
            updateDebugIndicator('Auth: Checking...', '#ffa500');
            
            const currentPage = window.location.pathname.split('/').pop() || 'index.html';
            console.log('Current page:', currentPage);
            
            if (currentPage === 'login.html') {
                console.log('On login page - no auth check needed');
                updateDebugIndicator('Auth: Login Page', '#28a745');
                return true;
            }
            
            const session = localStorage.getItem('flask_session');
            console.log('Session found:', !!session);
            
            if (!session) {
                console.log('No session - redirecting to login');
                updateDebugIndicator('Auth: Redirecting...', '#dc3545');
                setTimeout(() => {
                    window.location.href = 'login.html';
                }, 1000);
                return false;
            }
            
            try {
                const userData = JSON.parse(session);
                console.log('User data:', userData);
                updateDebugIndicator('Auth: ' + userData.role, '#28a745');
                
                // Update UI
                const userNameElements = document.querySelectorAll('.user-name');
                const userRoleElements = document.querySelectorAll('.user-role');
                
                userNameElements.forEach(el => {
                    if (el) {
                        el.textContent = userData.full_name;
                        console.log('Updated user name to:', userData.full_name);
                    }
                });
                
                userRoleElements.forEach(el => {
                    if (el) {
                        el.textContent = userData.role;
                        el.className = 'user-role user-role--' + userData.role.toLowerCase();
                        console.log('Updated user role to:', userData.role);
                    }
                });
                
                console.log('UI updated successfully');
                return true;
                
            } catch (e) {
                console.error('Error parsing session:', e);
                updateDebugIndicator('Auth: Error', '#dc3545');
                localStorage.removeItem('flask_session');
                setTimeout(() => {
                    window.location.href = 'login.html';
                }, 1000);
                return false;
            }
        }
        
        function handleLogin(event) {
            event.preventDefault();
            console.log('=== LOGIN ATTEMPT ===');
            updateDebugIndicator('Auth: Logging in...', '#ffa500');
            
            const username = document.getElementById('username')?.value || '';
            const password = document.getElementById('password')?.value || '';
            
            console.log('Username:', username);
            
            if (DEMO_USERS[username] && password === 'demo123') {
                console.log('Login successful');
                
                const user = DEMO_USERS[username];
                const sessionData = {
                    user_id: 1,
                    username: username,
                    role: user.role,
                    full_name: user.name,
                    email: username
                };
                
                localStorage.setItem('flask_session', JSON.stringify(sessionData));
                console.log('Session stored');
                updateDebugIndicator('Auth: Success!', '#28a745');
                
                setTimeout(() => {
                    window.location.href = 'index.html';
                }, 1000);
            } else {
                console.log('Login failed');
                updateDebugIndicator('Auth: Failed', '#dc3545');
                alert('Invalid credentials. Use demo credentials.');
            }
        }
        
        function logout() {
            console.log('=== LOGGING OUT ===');
            localStorage.removeItem('flask_session');
            window.location.href = 'login.html';
        }
        
        function quickLogin(username, password) {
            document.getElementById('username').value = username;
            document.getElementById('password').value = password;
            handleLogin(new Event('submit'));
        }
        
        // Initialize with debug indicator
        document.addEventListener('DOMContentLoaded', function() {
            console.log('=== DOM LOADED - INITIALIZING AUTH ===');
            
            // Add debug indicator
            addDebugIndicator();
            
            // Check auth after a short delay
            setTimeout(() => {
                checkAuth();
            }, 100);
        });
    </script>'''

def add_debug_auth():
    """Add debug logging to authentication scripts"""
    docs_dir = Path(__file__).parent / 'docs'
    
    print("Adding Debug Logging to Authentication")
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
                
                # Replace existing script with debug version
                script_pattern = r'(\s*<script>.*?</script>)'
                
                if '<script>' in content:
                    # Replace existing script
                    content = re.sub(script_pattern, DEBUG_AUTH_SCRIPT, content, flags=re.DOTALL)
                    
                    page_path.write_text(content, encoding='utf-8')
                    print(f"  Added debug to {page_name}")
                    success_count += 1
                else:
                    print(f"  No script found in {page_name}")
                    
            except Exception as e:
                print(f"  Failed to update {page_name}: {e}")
        else:
            print(f"  {page_name} not found")
    
    print("\n" + "=" * 50)
    print(f"Added debug to {success_count}/{len(files_to_update)} pages")
    
    print("\nDebug Features:")
    print("- Console logging")
    print("- Visual debug indicator")
    print("- Step-by-step auth flow")
    print("- Error tracking")
    
    print("\nTest steps:")
    print("1. Visit: http://localhost:8080/js-test.html")
    print("2. Check JavaScript execution")
    print("3. Visit: http://localhost:8080")
    print("4. Look for red debug indicator")
    print("5. Check console logs")
    
    return success_count == len(files_to_update)

if __name__ == '__main__':
    success = add_debug_auth()
    exit(0 if success else 1)
