#!/usr/bin/env python3
"""
Create GitHub Pages authentication that exactly replicates the Flask app user flow
"""

import os
import re
from pathlib import Path

# Flask-like authentication system for GitHub Pages
FLASK_LIKE_AUTH_SCRIPT = '''    <script>
        // Demo users exactly like the Flask app
        const DEMO_USERS = {
            'cfo@sadpmr.gov.za': {
                id: 1,
                username: 'cfo@sadpmr.gov.za',
                full_name: 'Sarah Nkosi',
                role: 'CFO',
                email: 'cfo@sadpmr.gov.za',
                permissions: ['upload', 'process', 'approve', 'generate_pdf', 'view_all', 'export'],
                can_upload: true,
                can_process: true,
                can_approve: true,
                can_generate_pdf: true,
                can_view_all: true
            },
            'accountant@sadpmr.gov.za': {
                id: 2,
                username: 'accountant@sadpmr.gov.za',
                full_name: 'Thabo Mthembu',
                role: 'ACCOUNTANT',
                email: 'accountant@sadpmr.gov.za',
                permissions: ['upload', 'process', 'generate_pdf', 'view_all'],
                can_upload: true,
                can_process: true,
                can_approve: false,
                can_generate_pdf: true,
                can_view_all: true
            },
            'clerk@sadpmr.gov.za': {
                id: 3,
                username: 'clerk@sadpmr.gov.za',
                full_name: 'Lerato Dlamini',
                role: 'CLERK',
                email: 'clerk@sadpmr.gov.za',
                permissions: ['upload', 'view_own'],
                can_upload: true,
                can_process: false,
                can_approve: false,
                can_generate_pdf: false,
                can_view_all: false
            },
            'auditor@agsa.gov.za': {
                id: 4,
                username: 'auditor@agsa.gov.za',
                full_name: 'AGSA Auditor',
                role: 'AUDITOR',
                email: 'auditor@agsa.gov.za',
                permissions: ['view_all'],
                can_upload: false,
                can_process: false,
                can_approve: false,
                can_generate_pdf: false,
                can_view_all: true
            }
        };

        let currentUser = null;
        let sessionData = {};

        // Session management for GitHub Pages
        class SessionManager {
            constructor() {
                this.sessionKey = 'sadpmr_session';
                this.loadSession();
            }

            loadSession() {
                const session = localStorage.getItem(this.sessionKey);
                if (session) {
                    sessionData = JSON.parse(session);
                    console.log('Session loaded:', sessionData);
                } else {
                    console.log('No session found');
                }
            }

            saveSession() {
                localStorage.setItem(this.sessionKey, JSON.stringify(sessionData));
                console.log('Session saved:', sessionData);
            }

            set(key, value) {
                sessionData[key] = value;
                this.saveSession();
            }

            get(key) {
                return sessionData[key];
            }

            has(key) {
                return key in sessionData;
            }

            clear() {
                sessionData = {};
                localStorage.removeItem(this.sessionKey);
                console.log('Session cleared');
            }
        }

        const session = new SessionManager();

        // User class like Flask app
        class User {
            constructor(userData) {
                this.id = userData.id;
                this.username = userData.username;
                this.full_name = userData.full_name;
                this.role = userData.role;
                this.email = userData.email;
                this.permissions = userData.permissions;
                this.can_upload = userData.can_upload;
                this.can_process = userData.can_process;
                this.can_approve = userData.can_approve;
                this.can_generate_pdf = userData.can_generate_pdf;
                this.can_view_all = userData.can_view_all;
            }

            get_id() {
                return String(this.id);
            }

            is_authenticated() {
                return true;
            }

            is_anonymous() {
                return false;
            }

            has_permission(permission) {
                return this.permissions.includes(permission);
            }
        }

        // Authentication decorator simulation
        function login_required() {
            if (!session.has('user_id')) {
                console.log('Login required - redirecting to login');
                window.location.href = 'login.html';
                return false;
            }
            return true;
        }

        function permission_required(permission) {
            if (!session.has('user_id')) {
                console.log('Authentication required for permission:', permission);
                return false;
            }

            const user = getCurrentUser();
            if (!user || !user.has_permission(permission)) {
                console.log('Permission denied:', permission, 'for user:', user?.role);
                return false;
            }
            return true;
        }

        // Get current user like Flask app
        function getCurrentUser() {
            if (!session.has('user_id')) {
                return null;
            }

            const userData = DEMO_USERS[session.get('username')];
            if (userData) {
                return new User(userData);
            }
            return null;
        }

        // Get current page name
        function getCurrentPage() {
            const pathParts = window.location.pathname.split('/');
            return pathParts[pathParts.length - 1] || 'index.html';
        }

        // Check authentication for GitHub Pages
        function checkAuthentication() {
            const currentPage = getCurrentPage();
            console.log('Checking authentication for page:', currentPage);

            // If login page, don't check auth
            if (currentPage === 'login.html') {
                console.log('On login page - no auth check needed');
                return true;
            }

            // Check if user is logged in
            if (!login_required()) {
                return false;
            }

            // Get current user
            currentUser = getCurrentUser();
            if (!currentUser) {
                console.log('No current user found');
                logout();
                return false;
            }

            console.log('User authenticated:', currentUser);

            // Page-specific permission checks (exactly like Flask app)
            if (currentPage === 'upload.html' && !currentUser.can_upload) {
                console.log('Upload permission denied for role:', currentUser.role);
                flashMessage('You do not have permission to upload files.', 'error');
                window.location.href = 'index.html';
                return false;
            }

            if (currentPage === 'admin.html' && currentUser.role !== 'CFO') {
                console.log('Admin access denied for role:', currentUser.role);
                flashMessage('You do not have permission to access the administration panel.', 'error');
                window.location.href = 'index.html';
                return false;
            }

            // Update UI
            updateUI(currentUser);

            console.log('Access granted for user:', currentUser.role, 'on page:', currentPage);
            return true;
        }

        // Flash messages like Flask app
        function flashMessage(message, type = 'info') {
            // Store flash message in session
            const flashes = session.get('flashes') || [];
            flashes.push({ message: message, type: type });
            session.set('flashes', flashes);
            console.log('Flash message stored:', message, type);
        }

        function getFlashMessages() {
            const flashes = session.get('flashes') || [];
            session.set('flashes', []); // Clear after getting
            return flashes;
        }

        // Update UI with user info (like Flask context processor)
        function updateUI(user) {
            // Update navbar with user info like Flask app
            const userNameElements = document.querySelectorAll('.user-name');
            const userRoleElements = document.querySelectorAll('.user-role');

            userNameElements.forEach(el => {
                if (el) el.textContent = user.full_name;
            });

            userRoleElements.forEach(el => {
                if (el) {
                    el.textContent = user.role;
                    el.className = 'user-role user-role--' + user.role.toLowerCase();
                }
            });

            // Hide navigation items based on permissions (like Flask app)
            const navLinks = document.querySelectorAll('.nav-menu a');
            navLinks.forEach(link => {
                const href = link.getAttribute('href');
                if (href && href !== 'login.html') {
                    // Add auth token to navigation links
                    link.setAttribute('href', href + '?auth=' + encodeURIComponent(session.get('username') + '|' + user.role));
                }
            });

            // Fix other links
            document.querySelectorAll('a[href$=".html"]').forEach(link => {
                const href = link.getAttribute('href');
                if (href && href !== 'login.html' && !href.includes('?auth=')) {
                    link.setAttribute('href', href + '?auth=' + encodeURIComponent(session.get('username') + '|' + user.role));
                }
            });

            console.log('UI updated for user:', user.role);
        }

        // Login function (exactly like Flask app)
        function handleLoginForm(event, redirectUrl) {
            event.preventDefault();
            console.log('Login form submitted');

            const username = document.getElementById('username')?.value || '';
            const password = document.getElementById('password')?.value || '';

            console.log('Login attempt:', username);

            // Verify password (like Flask app)
            const user = DEMO_USERS[username];
            if (user && password === 'demo123') {
                console.log('Login successful');

                // Set session data exactly like Flask app
                session.set('user_id', user.id);
                session.set('username', user.username);
                session.set('role', user.role);
                session.set('full_name', user.full_name);
                session.set('email', user.email);

                currentUser = new User(user);

                // Redirect to index (like Flask app)
                console.log('Redirecting to index');
                window.location.href = 'index.html';
            } else {
                console.log('Login failed');
                flashMessage('Invalid username or password.', 'error');
                updateFlashMessages();
            }
        }

        // Logout function (exactly like Flask app)
        function logout() {
            console.log('Logging out');
            session.clear();
            window.location.href = 'login.html';
        }

        // Update flash messages display
        function updateFlashMessages() {
            const flashes = getFlashMessages();
            const container = document.querySelector('.flash-messages');
            
            if (container && flashes.length > 0) {
                container.innerHTML = '';
                flashes.forEach(flash => {
                    const alertDiv = document.createElement('div');
                    alertDiv.className = `alert alert-${flash.type}`;
                    alertDiv.textContent = flash.message;
                    container.appendChild(alertDiv);
                });

                // Auto-hide after 5 seconds
                setTimeout(() => {
                    container.innerHTML = '';
                }, 5000);
            }
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
            
            // Check for auth token in URL (for initial login)
            const urlParams = new URLSearchParams(window.location.search);
            const urlAuth = urlParams.get('auth');
            
            if (urlAuth) {
                console.log('Auth token found in URL:', urlAuth);
                const [username, role] = decodeURIComponent(urlAuth).split('|');
                const user = DEMO_USERS[username];
                
                if (user && user.role === role) {
                    console.log('Setting session from URL auth token');
                    session.set('user_id', user.id);
                    session.set('username', user.username);
                    session.set('role', user.role);
                    session.set('full_name', user.full_name);
                    session.set('email', user.email);
                    
                    // Clean URL
                    const cleanUrl = window.location.pathname;
                    window.history.replaceState({}, '', cleanUrl);
                }
            }
            
            // Update flash messages
            updateFlashMessages();
            
            // Check authentication
            checkAuthentication();
        });
    </script>'''

def create_flask_like_auth():
    """Create GitHub Pages authentication that exactly replicates Flask app flow"""
    docs_dir = Path(__file__).parent / 'docs'
    
    print("Creating Flask-like Authentication for GitHub Pages")
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
                
                # Replace existing script with Flask-like script
                script_pattern = r'(\s*<script>.*?</script>)'
                
                if '<script>' in content:
                    # Replace existing script
                    content = re.sub(script_pattern, FLASK_LIKE_AUTH_SCRIPT, content, flags=re.DOTALL)
                    
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
    
    print("\nFlask-like Authentication Features:")
    print("- Exact same demo users as Flask app")
    print("- Session management like Flask")
    print("- Permission system like Flask")
    print("- Flash messages like Flask")
    print("- Role-based access control like Flask")
    print("- Same user flow and redirects")
    
    print("\nDemo Accounts (exactly like Flask app):")
    print("- CFO:        cfo@sadpmr.gov.za / demo123")
    print("- Accountant: accountant@sadpmr.gov.za / demo123")
    print("- Clerk:      clerk@sadpmr.gov.za / demo123")
    print("- Auditor:    auditor@agsa.gov.za / demo123")
    
    print("\nPermissions (exactly like Flask app):")
    print("- CFO: upload, process, approve, generate_pdf, view_all, export")
    print("- Accountant: upload, process, generate_pdf, view_all")
    print("- Clerk: upload, view_own")
    print("- Auditor: view_all")
    
    print("\nTest steps:")
    print("1. Clear browser storage")
    print("2. Visit: http://localhost:8080")
    print("3. Login with demo credentials")
    print("4. Try different roles - should behave like Flask app")
    print("5. Check permissions work correctly")
    
    return success_count == len(files_to_update)

if __name__ == '__main__':
    success = create_flask_like_auth()
    exit(0 if success else 1)
