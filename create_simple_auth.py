#!/usr/bin/env python3
"""
Create simplified, robust authentication system for GitHub Pages
"""

import os
import re
from pathlib import Path

# Simplified and robust authentication script
SIMPLE_AUTH_SCRIPT = '''    <script>
        // Role-based page configuration
        const ROLE_CONFIG = {
            'CFO': {
                name: 'Sarah Nkosi',
                allowedPages: ['index.html', 'upload.html', 'reports.html', 'admin.html', 'export.html', 'about.html'],
                defaultPage: 'index.html',
                hiddenNav: []
            },
            'Accountant': {
                name: 'John Smith', 
                allowedPages: ['index.html', 'upload.html', 'reports.html', 'export.html', 'about.html'],
                defaultPage: 'index.html',
                hiddenNav: ['admin.html']
            },
            'Clerk': {
                name: 'Mike Davis',
                allowedPages: ['index.html', 'upload.html', 'about.html'],
                defaultPage: 'upload.html',
                hiddenNav: ['admin.html', 'reports.html', 'export.html']
            },
            'Auditor': {
                name: 'Patience Moyo',
                allowedPages: ['index.html', 'reports.html', 'about.html'],
                defaultPage: 'reports.html',
                hiddenNav: ['admin.html', 'upload.html', 'export.html']
            }
        };

        let currentUser = null;

        // Get current page name
        function getCurrentPage() {
            const pathParts = window.location.pathname.split('/');
            return pathParts[pathParts.length - 1] || 'index.html';
        }

        // Get auth token from URL or localStorage
        function getAuthToken() {
            const urlParams = new URLSearchParams(window.location.search);
            const urlAuth = urlParams.get('auth');
            const localAuth = localStorage.getItem('auth_token');
            
            // Prefer URL auth (fresh login), fallback to localStorage
            const authToken = urlAuth || localAuth;
            
            console.log('Auth token sources - URL:', urlAuth, 'localStorage:', localAuth, 'using:', authToken);
            
            return authToken;
        }

        // Parse user from auth token
        function parseUser(authToken) {
            try {
                const user = decodeURIComponent(authToken);
                const [email, role] = user.split('|');
                
                if (!email || !role || !ROLE_CONFIG[role]) {
                    console.error('Invalid auth token format:', authToken);
                    return null;
                }
                
                return {
                    email: email,
                    role: role,
                    name: ROLE_CONFIG[role].name
                };
            } catch (e) {
                console.error('Error parsing auth token:', e);
                return null;
            }
        }

        // Check authentication
        function checkAuthentication() {
            const currentPage = getCurrentPage();
            console.log('Current page:', currentPage);
            
            // If login page, don't check auth
            if (currentPage === 'login.html') {
                console.log('On login page - no auth check needed');
                return true;
            }
            
            const authToken = getAuthToken();
            
            // If no auth, redirect to login
            if (!authToken) {
                console.log('No auth found - redirecting to login');
                window.location.href = 'login.html';
                return false;
            }
            
            // Parse user
            const user = parseUser(authToken);
            if (!user) {
                console.log('Invalid auth - redirecting to login');
                logout();
                return false;
            }
            
            currentUser = user;
            console.log('User authenticated:', user);
            
            // Store in localStorage for persistence
            localStorage.setItem('auth_token', authToken);
            
            // Check page permissions
            const roleConfig = ROLE_CONFIG[user.role];
            if (!roleConfig.allowedPages.includes(currentPage)) {
                console.log('Access denied for role', user.role, 'on page', currentPage);
                console.log('Redirecting to:', roleConfig.defaultPage);
                window.location.href = roleConfig.defaultPage + '?auth=' + authToken;
                return false;
            }
            
            console.log('Access granted for role', user.role, 'on page', currentPage);
            
            // Update UI
            updateUI(user);
            
            return true;
        }

        // Update UI with user info
        function updateUI(user) {
            // Update navbar
            const userNameElements = document.querySelectorAll('.user-name');
            const userRoleElements = document.querySelectorAll('.user-role');
            
            userNameElements.forEach(el => {
                if (el) el.textContent = user.name;
            });
            
            userRoleElements.forEach(el => {
                if (el) {
                    el.textContent = user.role;
                    el.className = 'user-role user-role--' + user.role.toLowerCase();
                }
            });
            
            // Update navigation
            const roleConfig = ROLE_CONFIG[user.role];
            const navLinks = document.querySelectorAll('.nav-menu a');
            
            console.log('Hiding nav items for role', user.role, ':', roleConfig.hiddenNav);
            
            navLinks.forEach(link => {
                const href = link.getAttribute('href');
                if (href && roleConfig.hiddenNav.includes(href)) {
                    link.style.display = 'none';
                    console.log('Hiding nav item:', href);
                } else if (href && href !== 'login.html') {
                    // Add auth token to navigation links
                    link.setAttribute('href', href + '?auth=' + getAuthToken());
                }
            });
            
            // Fix other links
            document.querySelectorAll('a[href$=".html"]').forEach(link => {
                const href = link.getAttribute('href');
                if (href && href !== 'login.html' && !href.includes('?auth=')) {
                    link.setAttribute('href', href + '?auth=' + getAuthToken());
                }
            });
            
            console.log('UI updated for user:', user.role);
        }

        // Login function
        function handleLoginForm(event, redirectUrl) {
            event.preventDefault();
            console.log('Login form submitted');
            
            const username = document.getElementById('username')?.value || '';
            const password = document.getElementById('password')?.value || '';
            
            console.log('Login attempt:', username);
            
            // Demo credentials
            const demoUsers = {
                'cfo@sadpmr.gov.za': { role: 'CFO' },
                'accountant@sadpmr.gov.za': { role: 'Accountant' },
                'clerk@sadpmr.gov.za': { role: 'Clerk' },
                'auditor@agsa.gov.za': { role: 'Auditor' }
            };
            
            if (demoUsers[username] && password === 'demo123') {
                console.log('Login successful');
                const user = demoUsers[username];
                const roleConfig = ROLE_CONFIG[user.role];
                
                // Create auth token
                const authToken = encodeURIComponent(username + '|' + user.role);
                
                // Store in localStorage
                localStorage.setItem('auth_token', authToken);
                
                // Redirect to role-specific page
                const redirectTarget = roleConfig.defaultPage;
                console.log('Redirecting to:', redirectTarget);
                window.location.href = redirectTarget + '?auth=' + authToken;
            } else {
                console.log('Login failed');
                alert('Invalid credentials. Use demo credentials shown below.');
            }
        }

        // Logout function
        function logout() {
            console.log('Logging out');
            localStorage.removeItem('auth_token');
            window.location.href = 'login.html';
        }

        // Quick login function
        function quickLogin(username, password) {
            document.getElementById('username').value = username;
            document.getElementById('password').value = password;
            handleLoginForm(new Event('submit'), 'index.html');
        }

        // Initialize when page loads
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM loaded - checking authentication...');
            checkAuthentication();
        });
    </script>'''

def create_simple_auth():
    """Create simplified, robust authentication system"""
    docs_dir = Path(__file__).parent / 'docs'
    
    print("Creating Simplified, Robust Authentication")
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
                
                # Replace existing script with simplified script
                script_pattern = r'(\s*<script>.*?</script>)'
                
                if '<script>' in content:
                    # Replace existing script
                    content = re.sub(script_pattern, SIMPLE_AUTH_SCRIPT, content, flags=re.DOTALL)
                    
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
    
    print("\nSimplified Authentication Features:")
    print("- Robust auth token parsing")
    print("- Better error handling")
    print("- Clear logging for debugging")
    print("- Improved localStorage handling")
    print("- Fixed navigation links")
    
    print("\nTest steps:")
    print("1. Clear browser storage")
    print("2. Visit: http://localhost:8080/auth-debug.html")
    print("3. Test auth flow with debug page")
    print("4. Try login from login.html")
    print("5. Check navigation links work")
    
    return success_count == len(files_to_update)

if __name__ == '__main__':
    success = create_simple_auth()
    exit(0 if success else 1)
