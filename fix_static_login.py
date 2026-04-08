#!/usr/bin/env python3
"""
Fix login form for static site usage
Modifies the generated login.html to work without server-side processing
"""

import re
from pathlib import Path

def fix_static_login():
    """Modify login.html to work as static form"""
    
    docs_dir = Path(__file__).parent / 'docs'
    login_file = docs_dir / 'login.html'
    
    if not login_file.exists():
        print("❌ login.html not found in docs directory")
        return
    
    # Read current login.html
    content = login_file.read_text(encoding='utf-8')
    
    # Add JavaScript for form handling
    login_script = """
    <script>
    document.addEventListener('DOMContentLoaded', function() {
        const loginForm = document.getElementById('loginForm');
        if (loginForm) {
            loginForm.addEventListener('submit', function(e) {
                e.preventDefault();
                
                // Get form values
                const username = document.getElementById('username').value;
                const password = document.getElementById('password').value;
                
                // Simple demo validation
                if (username && password) {
                    // Show success message
                    const successDiv = document.createElement('div');
                    successDiv.className = 'alert alert-success';
                    successDiv.innerHTML = 'Login successful! Redirecting to dashboard...';
                    
                    // Insert before form
                    loginForm.parentNode.insertBefore(successDiv, loginForm);
                    
                    // Redirect after 1.5 seconds
                    setTimeout(() => {
                        window.location.href = 'index.html';
                    }, 1500);
                } else {
                    // Show error message
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'alert alert-danger';
                    errorDiv.innerHTML = 'Please enter both username and password.';
                    
                    // Insert before form
                    loginForm.parentNode.insertBefore(errorDiv, loginForm);
                    
                    // Remove error after 3 seconds
                    setTimeout(() => {
                        if (errorDiv.parentNode) {
                            errorDiv.parentNode.removeChild(errorDiv);
                        }
                    }, 3000);
                }
            });
        }
        
        // Add demo credentials hint
        const loginHeader = document.querySelector('.login-header');
        if (loginHeader) {
            const demoHint = document.createElement('div');
            demoHint.className = 'demo-hint';
            demoHint.innerHTML = `
                <p><strong>Demo Credentials:</strong></p>
                <p>Email: cfo@sadpmr.gov.za</p>
                <p>Password: demo123</p>
                <p><em>(Any credentials work for demo)</em></p>
            `;
            demoHint.style.cssText = `
                background: #f0f8ff;
                padding: 15px;
                border-radius: 8px;
                margin: 20px 0;
                font-size: 14px;
                border-left: 4px solid #007bff;
            `;
            loginHeader.appendChild(demoHint);
        }
    });
    </script>
    """
    
    # Remove the form action to prevent server submission
    content = re.sub(r'action="[^"]*"', 'action="#"', content)
    
    # Add the script before closing body tag
    if '</body>' in content:
        content = content.replace('</body>', login_script + '</body>')
    else:
        content += login_script
    
    # Write back the modified file
    login_file.write_text(content, encoding='utf-8')
    
    print("✅ Fixed login.html for static usage")
    print("   - Added JavaScript form handling")
    print("   - Added demo credentials hint")
    print("   - Form now redirects to index.html")

if __name__ == '__main__':
    fix_static_login()
