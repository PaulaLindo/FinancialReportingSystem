#!/usr/bin/env python3
"""
Add role-based access control to all pages
Different user roles see different screens based on their permissions
"""

import os
import re
from pathlib import Path

# Role-based access control script
ROLE_BASED_SCRIPT = '''    <script>
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

        // Check if user has permission to access this page
        function checkPagePermission(userRole, pagePermissions) {
            return pagePermissions.includes(userRole);
        }

        // Role-based access control
        function setupRoleBasedAccess() {
            const user = checkAuthentication();
            if (!user) return;

            // Define page permissions for each role
            const pagePermissions = {
                'CFO': ['index.html', 'upload.html', 'reports.html', 'admin.html', 'export.html', 'about.html'],
                'Accountant': ['index.html', 'upload.html', 'reports.html', 'export.html', 'about.html'],
                'Clerk': ['index.html', 'upload.html', 'about.html'],
                'Auditor': ['index.html', 'reports.html', 'about.html']
            };

            // Get current page
            const currentPage = window.location.pathname.split('/').pop() || 'index.html';
            
            // Check if user has permission
            if (!checkPagePermission(user.role, pagePermissions[user.role] || [])) {
                // Redirect to dashboard with access denied message
                sessionStorage.setItem('accessDenied', 'true');
                window.location.href = 'index.html';
                return;
            }

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

            // Hide/show navigation items based on role
            const navItems = document.querySelectorAll('.nav-menu a');
            navItems.forEach(item => {
                const href = item.getAttribute('href');
                if (href && !checkPagePermission(user.role, pagePermissions[user.role] || [])) {
                    item.style.display = 'none';
                }
            });

            // Show access denied message if needed
            if (sessionStorage.getItem('accessDenied') === 'true') {
                sessionStorage.removeItem('accessDenied');
                showAccessDeniedMessage();
            }
        }

        function showAccessDeniedMessage() {
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
            
            // Simple demo login validation
            const username = document.getElementById('username')?.value || '';
            const password = document.getElementById('password')?.value || '';
            
            // Demo credentials with role-based redirects
            const demoUsers = {
                'cfo@sadpmr.gov.za': { role: 'CFO', name: 'Sarah Nkosi', redirect: 'index.html' },
                'accountant@sadpmr.gov.za': { role: 'Accountant', name: 'John Smith', redirect: 'index.html' },
                'clerk@sadpmr.gov.za': { role: 'Clerk', name: 'Mike Davis', redirect: 'index.html' },
                'auditor@agsa.gov.za': { role: 'Auditor', name: 'Patience Moyo', redirect: 'reports.html' }
            };
            
            if (demoUsers[username] && password === 'demo123') {
                // Store user info in sessionStorage for demo
                const user = demoUsers[username];
                sessionStorage.setItem('demoUser', JSON.stringify(user));
                
                // Redirect to appropriate page based on role
                window.location.href = user.redirect || redirectUrl || 'index.html';
            } else {
                // Show error message
                alert('Invalid credentials. Use demo credentials shown below.');
            }
        }

        function logout() {
            sessionStorage.removeItem('demoUser');
            sessionStorage.removeItem('accessDenied');
            window.location.href = 'login.html';
        }

        // Check authentication and set up role-based access
        document.addEventListener('DOMContentLoaded', function() {
            setupRoleBasedAccess();
        });
    </script>'''

# Pages and their required permissions
PAGE_PERMISSIONS = {
    'index.html': ['CFO', 'Accountant', 'Clerk', 'Auditor'],
    'upload.html': ['CFO', 'Accountant', 'Clerk'],
    'reports.html': ['CFO', 'Accountant', 'Auditor'],
    'admin.html': ['CFO'],
    'export.html': ['CFO', 'Accountant'],
    'about.html': ['CFO', 'Accountant', 'Clerk', 'Auditor'],
    'results.html': ['CFO', 'Accountant', 'Auditor'],
    'statement-financial-position.html': ['CFO', 'Accountant', 'Auditor'],
    'statement-financial-performance.html': ['CFO', 'Accountant', 'Auditor'],
    'statement-cash-flows.html': ['CFO', 'Accountant', 'Auditor']
}

def add_role_based_access_to_page(page_path, page_name):
    """Add role-based access control to a specific page"""
    try:
        content = page_path.read_text(encoding='utf-8')
        
        # Skip login page
        if page_name == 'login.html':
            print(f"  Skipping {page_name} (login page)")
            return True
        
        # Replace existing script with role-based script
        script_pattern = r'(\s*<script>.*?</script>)'
        
        if '<script>' in content:
            # Replace existing script
            content = re.sub(script_pattern, ROLE_BASED_SCRIPT, content, flags=re.DOTALL)
        else:
            # Add script before closing head tag
            content = content.replace('</head>', ROLE_BASED_SCRIPT + '</head>')
        
        # Update logout button
        content = re.sub(
            r'<a href="logout\.html" class="logout-btn">Logout</a>',
            '<a href="#" onclick="logout(); return false;" class="logout-btn">Logout</a>',
            content
        )
        
        page_path.write_text(content, encoding='utf-8')
        print(f"  Added role-based access to {page_name}")
        return True
        
    except Exception as e:
        print(f"  Failed to process {page_name}: {e}")
        return False

def main():
    """Add role-based access control to all pages"""
    docs_dir = Path(__file__).parent / 'docs'
    
    print("Role-Based Access Control Setup")
    print("=" * 50)
    
    success_count = 0
    total_count = len(PAGE_PERMISSIONS)
    
    for page_name in PAGE_PERMISSIONS.keys():
        page_path = docs_dir / page_name
        if page_path.exists():
            if add_role_based_access_to_page(page_path, page_name):
                success_count += 1
        else:
            print(f"  Warning: {page_name} not found")
    
    print("\n" + "=" * 50)
    print(f"Role-based access added to {success_count}/{total_count} pages")
    
    print("\nRole Permissions:")
    print("CFO: Full access to all pages")
    print("Accountant: Upload, Reports, Export (no Admin)")
    print("Clerk: Upload only (plus Dashboard, About)")
    print("Auditor: Reports only (plus Dashboard, About)")
    
    print("\nNext steps:")
    print("1. Test locally: python -m http.server 8080")
    print("2. Login with different roles:")
    print("   - cfo@sadpmr.gov.za (full access)")
    print("   - accountant@sadpmr.gov.za (no admin)")
    print("   - clerk@sadpmr.gov.za (upload only)")
    print("   - auditor@agsa.gov.za (reports only)")
    
    return success_count == total_count

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
