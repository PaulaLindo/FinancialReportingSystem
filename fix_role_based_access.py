#!/usr/bin/env python3
"""
Fix role-based access control to show correct screens for specific users
"""

import os
import re
from pathlib import Path

# Enhanced role-based authentication script
ENHANCED_AUTH_SCRIPT = '''    <script>
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

        // Wait for everything to load before checking auth
        window.addEventListener('load', function() {
            console.log('Page fully loaded, checking auth...');
            
            // Get current page name
            const pathParts = window.location.pathname.split('/');
            const currentPage = pathParts[pathParts.length - 1] || 'index.html';
            console.log('Current page:', currentPage);
            
            // Simple authentication check
            const currentUser = sessionStorage.getItem('demoUser');
            console.log('User in sessionStorage:', currentUser);
            
            // If no user and not on login page, redirect to login
            if (!currentUser && currentPage !== 'login.html') {
                console.log('No user found, redirecting to login');
                window.location.href = 'login.html';
                return;
            }
            
            // If user exists and on login page, redirect to appropriate page
            if (currentUser && currentPage === 'login.html') {
                try {
                    const user = JSON.parse(currentUser);
                    const roleConfig = ROLE_CONFIG[user.role];
                    if (roleConfig) {
                        console.log('User already logged in, redirecting to:', roleConfig.defaultPage);
                        window.location.href = roleConfig.defaultPage;
                        return;
                    }
                } catch (e) {
                    console.error('Error parsing user for redirect:', e);
                }
            }
            
            // If user exists, check permissions and update UI
            if (currentUser) {
                try {
                    const user = JSON.parse(currentUser);
                    console.log('User data:', user);
                    
                    const roleConfig = ROLE_CONFIG[user.role];
                    if (!roleConfig) {
                        console.error('Unknown role:', user.role);
                        return;
                    }
                    
                    // Check if user has permission for current page
                    if (!roleConfig.allowedPages.includes(currentPage)) {
                        console.log('Access denied for role', user.role, 'on page', currentPage);
                        console.log('Redirecting to:', roleConfig.defaultPage);
                        window.location.href = roleConfig.defaultPage;
                        return;
                    }
                    
                    console.log('Access granted for role', user.role, 'on page', currentPage);
                    
                    // Update user info in navbar
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
                    
                    // Hide navigation items based on role
                    const navLinks = document.querySelectorAll('.nav-menu a');
                    console.log('Found navigation items:', navLinks.length);
                    console.log('Hidden nav items for role', user.role, ':', roleConfig.hiddenNav);
                    
                    navLinks.forEach(link => {
                        const href = link.getAttribute('href');
                        if (href && roleConfig.hiddenNav.includes(href)) {
                            link.style.display = 'none';
                            console.log('Hiding nav item:', href);
                        }
                    });
                    
                    // Show role-specific content
                    showRoleSpecificContent(user.role);
                    
                    console.log('UI updated for user:', user.role);
                    
                } catch (e) {
                    console.error('Error parsing user:', e);
                }
            }
        });
        
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
        
        // Login function with role-based redirect
        function handleLoginForm(event, redirectUrl) {
            event.preventDefault();
            console.log('Login form submitted');
            
            const username = document.getElementById('username')?.value || '';
            const password = document.getElementById('password')?.value || '';
            
            console.log('Login attempt:', username);
            
            // Demo credentials with role-based redirects
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
                
                // Store user info in sessionStorage
                sessionStorage.setItem('demoUser', JSON.stringify(user));
                console.log('Stored user in sessionStorage:', user);
                
                // Redirect to role-specific default page
                const redirectTarget = roleConfig.defaultPage;
                console.log('Redirecting to:', redirectTarget);
                window.location.href = redirectTarget;
            } else {
                console.log('Login failed');
                alert('Invalid credentials. Use demo credentials shown below.');
            }
        }
        
        // Logout function
        function logout() {
            console.log('Logging out');
            sessionStorage.removeItem('demoUser');
            window.location.href = 'login.html';
        }
        
        // Quick login function
        function quickLogin(username, password) {
            document.getElementById('username').value = username;
            document.getElementById('password').value = password;
            handleLoginForm(new Event('submit'), 'index.html');
        }
    </script>'''

def fix_role_based_access():
    """Fix role-based access control to show correct screens"""
    docs_dir = Path(__file__).parent / 'docs'
    
    print("Fixing Role-Based Access Control")
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
                
                # Replace existing script with enhanced script
                script_pattern = r'(\s*<script>.*?</script>)'
                
                if '<script>' in content:
                    # Replace existing script
                    content = re.sub(script_pattern, ENHANCED_AUTH_SCRIPT, content, flags=re.DOTALL)
                    
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
    
    print("\nRole-Based Access Control:")
    print("CFO (Sarah): Full access to all pages")
    print("Accountant (John): No admin page, default to dashboard")
    print("Clerk (Mike): Upload only, default to upload page")
    print("Auditor (Patience): Reports only, default to reports page")
    
    print("\nTest steps:")
    print("1. Clear browser storage")
    print("2. Visit: http://localhost:8080")
    print("3. Login with different roles:")
    print("   - cfo@sadpmr.gov.za (full access, stays on dashboard)")
    print("   - accountant@sadpmr.gov.za (no admin, stays on dashboard)")
    print("   - clerk@sadpmr.gov.za (upload only, goes to upload page)")
    print("   - auditor@agsa.gov.za (reports only, goes to reports page)")
    
    return success_count == len(files_to_update)

if __name__ == '__main__':
    success = fix_role_based_access()
    exit(0 if success else 1)
