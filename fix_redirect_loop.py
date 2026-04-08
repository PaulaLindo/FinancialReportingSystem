#!/usr/bin/env python3
"""
Fix redirect loop issue in role-based access control
"""

import os
import re
from pathlib import Path

# Fixed authentication script with better debugging
FIXED_AUTH_SCRIPT = '''    <script>
        // Debug function
        function debug(message) {
            console.log('[Auth Debug]', message);
        }

        // Check authentication on page load
        function checkAuthentication() {
            debug('Checking authentication...');
            const currentUser = sessionStorage.getItem('demoUser');
            debug('Current user from sessionStorage:', currentUser);
            
            if (!currentUser) {
                debug('No user found, redirecting to login');
                // Not logged in, redirect to login
                window.location.href = 'login.html';
                return false;
            }
            
            const user = JSON.parse(currentUser);
            debug('User parsed:', user);
            return user;
        }

        // Check if user has permission to access this page
        function checkPagePermission(userRole, pagePermissions) {
            const hasPermission = pagePermissions.includes(userRole);
            debug('Permission check for role', userRole, ':', hasPermission);
            return hasPermission;
        }

        // Get current page name more reliably
        function getCurrentPage() {
            const pathname = window.location.pathname;
            debug('Full pathname:', pathname);
            
            // Handle different path formats
            let page = pathname;
            if (page.endsWith('/')) {
                page = page.slice(0, -1);
            }
            
            // Extract filename
            const parts = page.split('/');
            page = parts[parts.length - 1];
            
            // Default to index.html if empty
            if (!page || page === '') {
                page = 'index.html';
            }
            
            debug('Detected current page:', page);
            return page;
        }

        // Role-based access control
        function setupRoleBasedAccess() {
            debug('Setting up role-based access...');
            
            const user = checkAuthentication();
            if (!user) {
                debug('Authentication failed, stopping setup');
                return;
            }

            debug('User authenticated:', user);

            // Define page permissions for each role
            const pagePermissions = {
                'CFO': ['index.html', 'upload.html', 'reports.html', 'admin.html', 'export.html', 'about.html'],
                'Accountant': ['index.html', 'upload.html', 'reports.html', 'export.html', 'about.html'],
                'Clerk': ['index.html', 'upload.html', 'about.html'],
                'Auditor': ['index.html', 'reports.html', 'about.html']
            };

            // Get current page
            const currentPage = getCurrentPage();
            
            // Check if user has permission
            if (!checkPagePermission(user.role, pagePermissions[user.role] || [])) {
                debug('Access denied for role', user.role, 'on page', currentPage);
                // Redirect to dashboard with access denied message
                sessionStorage.setItem('accessDenied', 'true');
                window.location.href = 'index.html';
                return;
            }

            debug('Access granted for role', user.role, 'on page', currentPage);

            // Update user info in navbar
            const userNameElements = document.querySelectorAll('.user-name');
            const userRoleElements = document.querySelectorAll('.user-role');
            
            debug('Updating user info in navbar...');
            userNameElements.forEach(el => {
                if (el) {
                    el.textContent = user.name;
                    debug('Set user name to:', user.name);
                }
            });
            
            userRoleElements.forEach(el => {
                if (el) {
                    el.textContent = user.role;
                    el.className = `user-role user-role--${user.role.toLowerCase()}`;
                    debug('Set user role to:', user.role);
                }
            });

            // Hide/show navigation items based on role
            const navItems = document.querySelectorAll('.nav-menu a');
            debug('Found navigation items:', navItems.length);
            
            navItems.forEach(item => {
                const href = item.getAttribute('href');
                debug('Checking nav item:', href);
                if (href && !checkPagePermission(user.role, pagePermissions[user.role] || [])) {
                    item.style.display = 'none';
                    debug('Hiding nav item:', href);
                }
            });

            // Show access denied message if needed
            if (sessionStorage.getItem('accessDenied') === 'true') {
                sessionStorage.removeItem('accessDenied');
                showAccessDeniedMessage();
            }

            debug('Role-based access setup complete');
        }

        function showAccessDeniedMessage() {
            debug('Showing access denied message');
            const message = document.createElement('div');
            message.className = 'alert alert-warning';
            message.innerHTML = `
                <strong>Access Denied</strong><br>
                You don't have permission to access that page.
            `;
            
            const hero = document.querySelector('.hero');
            if (hero) {
                hero.insertBefore(message, hero.firstChild);
            }
            
            setTimeout(() => {
                message.remove();
            }, 5000);
        }

        function handleLoginForm(event, redirectUrl) {
            event.preventDefault();
            debug('Handling login form...');
            
            // Simple demo login validation
            const username = document.getElementById('username')?.value || '';
            const password = document.getElementById('password')?.value || '';
            
            debug('Login attempt:', username);
            
            // Demo credentials with role-based redirects
            const demoUsers = {
                'cfo@sadpmr.gov.za': { role: 'CFO', name: 'Sarah Nkosi', redirect: 'index.html' },
                'accountant@sadpmr.gov.za': { role: 'Accountant', name: 'John Smith', redirect: 'index.html' },
                'clerk@sadpmr.gov.za': { role: 'Clerk', name: 'Mike Davis', redirect: 'index.html' },
                'auditor@agsa.gov.za': { role: 'Auditor', name: 'Patience Moyo', redirect: 'reports.html' }
            };
            
            if (demoUsers[username] && password === 'demo123') {
                debug('Login successful for:', username);
                // Store user info in sessionStorage for demo
                const user = demoUsers[username];
                sessionStorage.setItem('demoUser', JSON.stringify(user));
                debug('Stored user in sessionStorage:', user);
                
                // Redirect to appropriate page based on role
                const redirectTarget = user.redirect || redirectUrl || 'index.html';
                debug('Redirecting to:', redirectTarget);
                window.location.href = redirectTarget;
            } else {
                debug('Login failed for:', username);
                // Show error message
                alert('Invalid credentials. Use demo credentials shown below.');
            }
        }

        function logout() {
            debug('Logging out...');
            sessionStorage.removeItem('demoUser');
            sessionStorage.removeItem('accessDenied');
            window.location.href = 'login.html';
        }

        // Check authentication and set up role-based access
        document.addEventListener('DOMContentLoaded', function() {
            debug('DOM loaded, starting setup...');
            setupRoleBasedAccess();
        });
    </script>'''

def fix_redirect_loop():
    """Fix the redirect loop issue in all pages"""
    docs_dir = Path(__file__).parent / 'docs'
    
    print("Fixing Redirect Loop Issue")
    print("=" * 50)
    
    # Files to fix
    files_to_fix = [
        'index.html', 'upload.html', 'reports.html', 'admin.html', 
        'export.html', 'about.html', 'results.html',
        'statement-financial-position.html', 'statement-financial-performance.html', 
        'statement-cash-flows.html'
    ]
    
    success_count = 0
    
    for page_name in files_to_fix:
        page_path = docs_dir / page_name
        if page_path.exists():
            try:
                content = page_path.read_text(encoding='utf-8')
                
                # Replace existing script with fixed script
                script_pattern = r'(\s*<script>.*?</script>)'
                
                if '<script>' in content:
                    # Replace existing script
                    content = re.sub(script_pattern, FIXED_AUTH_SCRIPT, content, flags=re.DOTALL)
                    
                    page_path.write_text(content, encoding='utf-8')
                    print(f"  Fixed {page_name}")
                    success_count += 1
                else:
                    print(f"  No script found in {page_name}")
                    
            except Exception as e:
                print(f"  Failed to fix {page_name}: {e}")
        else:
            print(f"  {page_name} not found")
    
    print("\n" + "=" * 50)
    print(f"Fixed {success_count}/{len(files_to_fix)} pages")
    
    print("\nTesting steps:")
    print("1. Clear browser session storage")
    print("2. Visit: http://localhost:8080")
    print("3. Should redirect to login.html")
    print("4. Login with demo credentials")
    print("5. Check console for debug messages")
    
    return success_count == len(files_to_fix)

if __name__ == '__main__':
    success = fix_redirect_loop()
    exit(0 if success else 1)
