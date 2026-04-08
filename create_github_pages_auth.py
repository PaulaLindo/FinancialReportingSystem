#!/usr/bin/env python3
"""
Create GitHub Pages compatible authentication system
Uses URL parameters and localStorage instead of sessionStorage
"""

import os
import re
from pathlib import Path

# GitHub Pages compatible authentication script
GITHUB_PAGES_AUTH_SCRIPT = '''    <script>
        // Role-based page configuration for GitHub Pages
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

        // Get URL parameters
        function getUrlParams() {
            const params = {};
            const urlParams = new URLSearchParams(window.location.search);
            for (const [key, value] of urlParams) {
                params[key] = value;
            }
            return params;
        }

        // Set URL parameter
        function setUrlParam(key, value) {
            const url = new URL(window.location);
            url.searchParams.set(key, value);
            window.history.replaceState({}, '', url);
        }

        // Remove URL parameter
        function removeUrlParam(key) {
            const url = new URL(window.location);
            url.searchParams.delete(key);
            window.history.replaceState({}, '', url);
        }

        // Check authentication for GitHub Pages
        function checkAuthGitHubPages() {
            console.log('Checking GitHub Pages authentication...');
            
            // Get current page name
            const pathParts = window.location.pathname.split('/');
            const currentPage = pathParts[pathParts.length - 1] || 'index.html';
            console.log('Current page:', currentPage);
            
            // Get URL parameters
            const params = getUrlParams();
            console.log('URL params:', params);
            
            // Check for auth token in URL or localStorage
            const authToken = params.auth || localStorage.getItem('auth_token');
            
            // If no auth and not on login page, redirect to login
            if (!authToken && currentPage !== 'login.html') {
                console.log('No auth found, redirecting to login');
                window.location.href = 'login.html';
                return false;
            }
            
            // If auth exists and on login page, redirect to appropriate page
            if (authToken && currentPage === 'login.html') {
                const user = decodeURIComponent(authToken);
                const [email, role] = user.split('|');
                const roleConfig = ROLE_CONFIG[role];
                if (roleConfig) {
                    console.log('User already logged in, redirecting to:', roleConfig.defaultPage);
                    window.location.href = roleConfig.defaultPage + '?auth=' + authToken;
                    return false;
                }
            }
            
            // If auth exists, validate and update UI
            if (authToken) {
                try {
                    const user = decodeURIComponent(authToken);
                    const [email, role] = user.split('|');
                    
                    if (!ROLE_CONFIG[role]) {
                        console.error('Invalid role:', role);
                        logout();
                        return false;
                    }
                    
                    const roleConfig = ROLE_CONFIG[role];
                    const userData = {
                        email: email,
                        role: role,
                        name: roleConfig.name
                    };
                    
                    console.log('User authenticated:', userData);
                    
                    // Check if user has permission for current page
                    if (!roleConfig.allowedPages.includes(currentPage)) {
                        console.log('Access denied for role', role, 'on page', currentPage);
                        console.log('Redirecting to:', roleConfig.defaultPage);
                        window.location.href = roleConfig.defaultPage + '?auth=' + authToken;
                        return false;
                    }
                    
                    console.log('Access granted for role', role, 'on page', currentPage);
                    
                    // Store auth in localStorage for persistence
                    localStorage.setItem('auth_token', authToken);
                    
                    // Clean URL (remove auth parameter for cleaner URLs)
                    if (params.auth) {
                        removeUrlParam('auth');
                    }
                    
                    // Update user info in navbar
                    updateNavbar(userData);
                    
                    // Hide navigation items based on role
                    updateNavigation(role);
                    
                    // Show role-specific content
                    showRoleSpecificContent(role);
                    
                    console.log('UI updated for user:', userData.role);
                    return true;
                    
                } catch (e) {
                    console.error('Error parsing auth token:', e);
                    logout();
                    return false;
                }
            }
            
            return true;
        }

        function updateNavbar(userData) {
            const userNameElements = document.querySelectorAll('.user-name');
            const userRoleElements = document.querySelectorAll('.user-role');
            
            userNameElements.forEach(el => {
                if (el) el.textContent = userData.name;
            });
            
            userRoleElements.forEach(el => {
                if (el) {
                    el.textContent = userData.role;
                    el.className = 'user-role user-role--' + userData.role.toLowerCase();
                }
            });
        }

        function updateNavigation(role) {
            const roleConfig = ROLE_CONFIG[role];
            const navLinks = document.querySelectorAll('.nav-menu a');
            
            console.log('Hiding nav items for role', role, ':', roleConfig.hiddenNav);
            
            navLinks.forEach(link => {
                const href = link.getAttribute('href');
                if (href && roleConfig.hiddenNav.includes(href)) {
                    link.style.display = 'none';
                    console.log('Hiding nav item:', href);
                }
            });
        }

        function showRoleSpecificContent(role) {
            // Hide all role-specific sections first
            document.querySelectorAll('[data-role]').forEach(el => {
                el.style.display = 'none';
            });
            
            // Show content for current role
            document.querySelectorAll(`[data-role="${role}"]`).forEach(el => {
                el.style.display = 'block';
            });
            
            // Show content for "all" roles
            document.querySelectorAll('[data-role="all"]').forEach(el => {
                el.style.display = 'block';
            });
            
            console.log('Role-specific content shown for:', role);
        }

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
                const roleConfig = ROLE_CONFIG[user.role];
                
                // Create auth token (email|role)
                const authToken = encodeURIComponent(username + '|' + user.role);
                
                // Store in localStorage
                localStorage.setItem('auth_token', authToken);
                
                // Redirect to role-specific default page
                const redirectTarget = roleConfig.defaultPage;
                console.log('Redirecting to:', redirectTarget);
                window.location.href = redirectTarget + '?auth=' + authToken;
            } else {
                console.log('Login failed');
                alert('Invalid credentials. Use demo credentials shown below.');
            }
        }

        // Logout function for GitHub Pages
        function logout() {
            console.log('Logging out');
            localStorage.removeItem('auth_token');
            window.location.href = 'login.html';
        }

        // Quick login function for GitHub Pages
        function quickLogin(username, password) {
            document.getElementById('username').value = username;
            document.getElementById('password').value = password;
            handleLoginForm(new Event('submit'), 'index.html');
        }

        // Initialize authentication when page loads
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM loaded, checking GitHub Pages auth...');
            checkAuthGitHubPages();
        });
    </script>'''

def create_github_pages_auth():
    """Create GitHub Pages compatible authentication system"""
    docs_dir = Path(__file__).parent / 'docs'
    
    print("Creating GitHub Pages Compatible Authentication")
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
                
                # Replace existing script with GitHub Pages compatible script
                script_pattern = r'(\s*<script>.*?</script>)'
                
                if '<script>' in content:
                    # Replace existing script
                    content = re.sub(script_pattern, GITHUB_PAGES_AUTH_SCRIPT, content, flags=re.DOTALL)
                    
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
    
    print("\nGitHub Pages Authentication Features:")
    print("- Uses localStorage for persistence")
    print("- URL parameters for initial auth")
    print("- Works on static GitHub Pages")
    print("- Role-based access control")
    print("- Clean URLs after authentication")
    
    print("\nTest steps:")
    print("1. Clear browser storage")
    print("2. Visit: http://localhost:8080")
    print("3. Should redirect to login.html")
    print("4. Login with demo credentials")
    print("5. Should redirect to role-specific page")
    print("6. Navigation should be filtered by role")
    
    return success_count == len(files_to_update)

if __name__ == '__main__':
    success = create_github_pages_auth()
    exit(0 if success else 1)
