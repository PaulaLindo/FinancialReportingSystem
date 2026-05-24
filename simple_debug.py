#!/usr/bin/env python3
"""
Simple debug by adding print to login_required decorator
"""

def add_simple_debug():
    """Add a simple print statement to login_required decorator"""
    
    routes_file = 'c:\\dev\\FinancialReportingSystem\\controllers\\routes.py'
    
    with open(routes_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add a simple print statement after the user_data check
    original_line = '        if user_data and user_data[\'is_active\']:'
    new_line = '        if user_data and user_data[\'is_active\']:\n            print(f"DEBUG: User authenticated: {user_data[\'id\']}")'
    
    content = content.replace(original_line, new_line)
    
    with open(routes_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ Simple debug added to login_required decorator")

if __name__ == "__main__":
    add_simple_debug()
