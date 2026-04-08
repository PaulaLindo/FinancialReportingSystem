#!/usr/bin/env python3
"""
Create GitHub Pages authentication that EXACTLY replicates Flask app user flow
"""

import os
import re
from pathlib import Path

# Exact Flask replica authentication script
FLASK_EXACT_REPLICA = '''    <script>
        console.log('=== SADPMR Financial Reporting System - GitHub Pages ===');
        console.log('Replicating Flask app authentication flow...');
        
        // EXACT demo users from Flask app models/auth_models.py
        const DEMO_USERS = {
            'cfo@sadpmr.gov.za': {
                id: 1,
                username: 'cfo@sadpmr.gov.za',
                full_name: 'Sarah Nkosi',
                role: 'CFO',
                email: 'cfo@sadpmr.gov.za',
                permissions: ['upload', 'process', 'approve', 'generate_pdf', 'view_all', 'export']
            },
            'accountant@sadpmr.gov.za': {
                id: 2,
                username: 'accountant@sadpmr.gov.za',
                full_name: 'Thabo Mthembu',
                role: 'ACCOUNTANT',
                email: 'accountant@sadpmr.gov.za',
                permissions: ['upload', 'process', 'generate_pdf', 'view_all']
            },
            'clerk@sadpmr.gov.za': {
                id: 3,
                username: 'clerk@sadpmr.gov.za',
                full_name: 'Lerato Dlamini',
                role: 'CLERK',
                email: 'clerk@sadpmr.gov.za',
                permissions: ['upload', 'view_own']
            },
            'auditor@agsa.gov.za': {
                id: 4,
                username: 'auditor@agsa.gov.za',
                full_name: 'AGSA Auditor',
                role: 'AUDITOR',
                email: 'auditor@agsa.gov.za',
                permissions: ['view_all']
            }
        };
        
        // Flask session replica
        class FlaskSession {
            constructor() {
                this.data = this.loadSession();
            }
            
            loadSession() {
                const session = localStorage.getItem('flask_session');
                return session ? JSON.parse(session) : {};
            }
            
            saveSession() {
                localStorage.setItem('flask_session', JSON.stringify(this.data));
            }
            
            get(key) {
                return this.data[key];
            }
            
            set(key, value) {
                this.data[key] = value;
                this.saveSession();
            }
            
            has(key) {
                return key in this.data;
            }
            
            clear() {
                this.data = {};
                localStorage.removeItem('flask_session');
            }
        }
        
        const session = new FlaskSession();
        
        // User class replica from Flask app
        class User {
            constructor(userData) {
                this.id = userData.id;
                this.username = userData.username;
                this.full_name = userData.full_name;
                this.role = userData.role;
                this.email = userData.email;
                this.permissions = userData.permissions;
            }
            
            has_permission(permission) {
                return this.permissions.includes(permission);
            }
            
            can_upload() {
                return this.has_permission('upload');
            }
            
            can_process() {
                return this.has_permission('process');
            }
            
            can_approve() {
                return this.has_permission('approve');
            }
            
            can_generate_pdf() {
                return this.has_permission('generate_pdf');
            }
            
            can_view_all() {
                return this.has_permission('view_all');
            }
        }
        
        // Get current user (exact Flask replica)
        function getCurrentUser() {
            if (!session.has('user_id')) {
                return null;
            }
            
            const username = session.get('username');
            const userData = DEMO_USERS[username];
            
            if (userData) {
                return new User(userData);
            }
            
            return null;
        }
        
        // Login decorator replica
        function login_required() {
            if (!session.has('user_id')) {
                console.log('Login required - redirecting to login');
                window.location.href = 'login.html';
                return false;
            }
            return true;
        }
        
        // Permission decorator replica
        function permission_required(permission) {
            if (!session.has('user_id')) {
                return false;
            }
            
            const user = getCurrentUser();
            if (!user || !user.has_permission(permission)) {
                return false;
            }
            return true;
        }
        
        // Flash messages replica
        function flash(message, type = 'info') {
            const flashes = session.get('flashes') || [];
            flashes.push({ message, type });
            session.set('flashes', flashes);
        }
        
        function getFlashes() {
            const flashes = session.get('flashes') || [];
            session.set('flashes', []);
            return flashes;
        }
        
        // Show flash messages
        function showFlashes() {
            const flashes = getFlashes();
            const container = document.querySelector('.flash-messages');
            
            if (container && flashes.length > 0) {
                container.innerHTML = '';
                flashes.forEach(flash => {
                    const div = document.createElement('div');
                    div.className = `alert alert-${flash.type}`;
                    div.textContent = flash.message;
                    container.appendChild(div);
                });
                
                setTimeout(() => {
                    container.innerHTML = '';
                }, 5000);
            }
        }
        
        // Update navbar (exact Flask context processor replica)
        function updateNavbar() {
            const user = getCurrentUser();
            if (!user) return;
            
            // Update user info like Flask context processor
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
            
            console.log('Navbar updated for user:', user.full_name, '(', user.role, ')');
        }
        
        // Update navigation based on permissions (exact Flask replica)
        function updateNavigation() {
            const user = getCurrentUser();
            if (!user) return;
            
            const navLinks = document.querySelectorAll('.nav-menu a');
            
            navLinks.forEach(link => {
                const href = link.getAttribute('href');
                if (!href || href === 'login.html') return;
                
                // Hide links based on permissions (exact Flask logic)
                if (href === 'admin.html' && user.role !== 'CFO') {
                    link.style.display = 'none';
                    console.log('Hidden admin link for role:', user.role);
                }
                
                // Add auth to remaining links
                if (href.endsWith('.html')) {
                    link.setAttribute('href', href + '?auth=' + encodeURIComponent(user.username + '|' + user.role));
                }
            });
        }
        
        // Main authentication check (exact Flask route behavior)
        function checkAuthentication() {
            const currentPage = window.location.pathname.split('/').pop() || 'index.html';
            console.log('Checking auth for page:', currentPage);
            
            // Don't check auth for login page
            if (currentPage === 'login.html') {
                console.log('On login page - no auth check');
                return true;
            }
            
            // Apply login_required decorator
            if (!login_required()) {
                return false;
            }
            
            const user = getCurrentUser();
            if (!user) {
                console.log('No user found - redirecting to login');
                logout();
                return false;
            }
            
            console.log('User authenticated:', user.full_name, '(', user.role, ')');
            
            // Apply exact Flask route permissions
            if (currentPage === 'upload.html' && !user.can_upload()) {
                flash('You do not have permission to upload files.', 'error');
                console.log('Upload permission denied for role:', user.role);
                window.location.href = 'index.html';
                return false;
            }
            
            if (currentPage === 'admin.html' && user.role !== 'CFO') {
                flash('You do not have permission to access the administration panel.', 'error');
                console.log('Admin access denied for role:', user.role);
                window.location.href = 'index.html';
                return false;
            }
            
            // Update UI
            updateNavbar();
            updateNavigation();
            showFlashes();
            
            console.log('Access granted for', user.role, 'on', currentPage);
            return true;
        }
        
        // Login function (exact Flask route replica)
        function handleLoginForm(event) {
            event.preventDefault();
            console.log('Login form submitted');
            
            const username = document.getElementById('username')?.value || '';
            const password = document.getElementById('password')?.value || '';
            
            console.log('Login attempt:', username);
            
            // Exact Flask verification logic
            const user = DEMO_USERS[username];
            if (user && password === 'demo123') {
                console.log('Login successful');
                
                // Set session exactly like Flask app
                session.set('user_id', user.id);
                session.set('username', user.username);
                session.set('role', user.role);
                session.set('full_name', user.full_name);
                session.set('email', user.email);
                
                console.log('Session set:', {
                    user_id: user.id,
                    username: user.username,
                    role: user.role,
                    full_name: user.full_name
                });
                
                // Redirect to index (exact Flask behavior)
                console.log('Redirecting to index.html');
                window.location.href = 'index.html';
            } else {
                console.log('Login failed');
                flash('Invalid username or password.', 'error');
                showFlashes();
            }
        }
        
        // Logout function (exact Flask route replica)
        function logout() {
            console.log('Logging out');
            session.clear();
            window.location.href = 'login.html';
        }
        
        // Quick login for demo
        function quickLogin(username, password) {
            document.getElementById('username').value = username;
            document.getElementById('password').value = password;
            handleLoginForm(new Event('submit'));
        }
        
        // Handle auth token from URL (for GitHub Pages)
        function handleAuthToken() {
            const urlParams = new URLSearchParams(window.location.search);
            const authToken = urlParams.get('auth');
            
            if (authToken) {
                console.log('Auth token found in URL:', authToken);
                const [username, role] = decodeURIComponent(authToken).split('|');
                const user = DEMO_USERS[username];
                
                if (user && user.role === role) {
                    console.log('Setting session from auth token');
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
        }
        
        // Initialize (exact Flask app behavior)
        document.addEventListener('DOMContentLoaded', function() {
            console.log('DOM loaded - initializing Flask replica...');
            
            handleAuthToken();
            showFlashes();
            checkAuthentication();
        });
    </script>'''

def create_flask_exact_replica():
    """Create GitHub Pages authentication that EXACTLY replicates Flask app"""
    docs_dir = Path(__file__).parent / 'docs'
    
    print("Creating EXACT Flask Replica for GitHub Pages")
    print("=" * 60)
    
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
                
                # Replace existing script with exact Flask replica
                script_pattern = r'(\s*<script>.*?</script>)'
                
                if '<script>' in content:
                    # Replace existing script
                    content = re.sub(script_pattern, FLASK_EXACT_REPLICA, content, flags=re.DOTALL)
                    
                    page_path.write_text(content, encoding='utf-8')
                    print(f"  Updated {page_name}")
                    success_count += 1
                else:
                    print(f"  No script found in {page_name}")
                    
            except Exception as e:
                print(f"  Failed to update {page_name}: {e}")
        else:
            print(f"  {page_name} not found")
    
    print("\n" + "=" * 60)
    print(f"Updated {success_count}/{len(files_to_update)} pages")
    
    print("\nEXACT Flask Replica Features:")
    print("Same demo users: cfo@sadpmr.gov.za, accountant@sadpmr.gov.za, clerk@sadpmr.gov.za, auditor@agsa.gov.za")
    print("Same permissions:", ['upload', 'process', 'approve', 'generate_pdf', 'view_all', 'export'])
    print("Same session management")
    print("Same flash messages")
    print("Same role-based access control")
    print("Same redirect behavior")
    
    print("\nDemo Credentials (EXACT Flask replica):")
    print("CFO:        cfo@sadpmr.gov.za / demo123")
    print("Accountant: accountant@sadpmr.gov.za / demo123")
    print("Clerk:      clerk@sadpmr.gov.za / demo123")
    print("Auditor:    auditor@agsa.gov.za / demo123")
    
    print("\nGitHub Pages will behave EXACTLY like Flask app!")
    return success_count == len(files_to_update)

if __name__ == '__main__':
    success = create_flask_exact_replica()
    exit(0 if success else 1)
