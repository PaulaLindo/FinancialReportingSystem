#!/usr/bin/env python3
"""
Create a minimal, working authentication system without redirect loops
"""

import os
from pathlib import Path

# Minimal authentication script that works
MINIMAL_AUTH_SCRIPT = '''    <script>
        // Wait for everything to load before checking auth
        window.addEventListener('load', function() {
            console.log('Page fully loaded, checking auth...');
            
            // Simple authentication check
            const currentUser = sessionStorage.getItem('demoUser');
            console.log('User in sessionStorage:', currentUser);
            
            // Get current page name
            const pathParts = window.location.pathname.split('/');
            const currentPage = pathParts[pathParts.length - 1] || 'index.html';
            console.log('Current page:', currentPage);
            
            // If no user and not on login page, redirect to login
            if (!currentUser && currentPage !== 'login.html') {
                console.log('No user found, redirecting to login');
                window.location.href = 'login.html';
                return;
            }
            
            // If user exists and on login page, redirect to dashboard
            if (currentUser && currentPage === 'login.html') {
                console.log('User already logged in, redirecting to dashboard');
                window.location.href = 'index.html';
                return;
            }
            
            // If user exists, update UI
            if (currentUser) {
                try {
                    const user = JSON.parse(currentUser);
                    console.log('User data:', user);
                    
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
                    
                    // Show/hide navigation based on role
                    const navLinks = document.querySelectorAll('.nav-menu a');
                    navLinks.forEach(link => {
                        const href = link.getAttribute('href');
                        if (href) {
                            // Simple role-based hiding
                            if (user.role === 'Clerk' && (href === 'admin.html' || href === 'export.html')) {
                                link.style.display = 'none';
                            }
                            if (user.role === 'Auditor' && (href === 'admin.html' || href === 'upload.html' || href === 'export.html')) {
                                link.style.display = 'none';
                            }
                            if (user.role === 'Accountant' && href === 'admin.html') {
                                link.style.display = 'none';
                            }
                        }
                    });
                    
                    console.log('UI updated for user:', user.role);
                    
                } catch (e) {
                    console.error('Error parsing user:', e);
                }
            }
        });
        
        // Login function
        function handleLoginForm(event, redirectUrl) {
            event.preventDefault();
            console.log('Login form submitted');
            
            const username = document.getElementById('username')?.value || '';
            const password = document.getElementById('password')?.value || '';
            
            console.log('Login attempt:', username);
            
            // Demo credentials
            const demoUsers = {
                'cfo@sadpmr.gov.za': { role: 'CFO', name: 'Sarah Nkosi', redirect: 'index.html' },
                'accountant@sadpmr.gov.za': { role: 'Accountant', name: 'John Smith', redirect: 'index.html' },
                'clerk@sadpmr.gov.za': { role: 'Clerk', name: 'Mike Davis', redirect: 'index.html' },
                'auditor@agsa.gov.za': { role: 'Auditor', name: 'Patience Moyo', redirect: 'reports.html' }
            };
            
            if (demoUsers[username] && password === 'demo123') {
                console.log('Login successful');
                const user = demoUsers[username];
                sessionStorage.setItem('demoUser', JSON.stringify(user));
                window.location.href = user.redirect || 'index.html';
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

def create_minimal_auth():
    """Create minimal authentication for all pages"""
    docs_dir = Path(__file__).parent / 'docs'
    
    print("Creating Minimal Authentication System")
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
                
                # Find and replace the script section
                import re
                
                # Remove existing script
                content = re.sub(r'\s*<script>.*?</script>', '', content, flags=re.DOTALL)
                
                # Add minimal script before closing head tag
                content = content.replace('</head>', MINIMAL_AUTH_SCRIPT + '</head>')
                
                # Update logout buttons
                content = re.sub(
                    r'<a href="logout\.html"[^>]*>Logout</a>',
                    '<a href="#" onclick="logout(); return false;">Logout</a>',
                    content
                )
                
                page_path.write_text(content, encoding='utf-8')
                print(f"  Updated {page_name}")
                success_count += 1
                
            except Exception as e:
                print(f"  Failed to update {page_name}: {e}")
        else:
            print(f"  {page_name} not found")
    
    print("\n" + "=" * 50)
    print(f"Updated {success_count}/{len(files_to_update)} pages")
    
    print("\nFeatures:")
    print("- Uses window.load event (waits for everything to load)")
    print("- Simple page detection")
    print("- Basic role-based navigation hiding")
    print("- No redirect loops")
    print("- Console logging for debugging")
    
    print("\nTest steps:")
    print("1. Clear browser storage")
    print("2. Visit: http://localhost:8080")
    print("3. Should redirect to login.html")
    print("4. Login with demo credentials")
    print("5. Should redirect to appropriate page")
    
    return success_count == len(files_to_update)

if __name__ == '__main__':
    success = create_minimal_auth()
    exit(0 if success else 1)
