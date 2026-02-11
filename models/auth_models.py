"""
SADPMR Financial Reporting System - Authentication Models
User authentication and role-based access control
"""

from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os

# Simple file-based database for demo (in production, use PostgreSQL)
class SimpleDB:
    def __init__(self, db_file='data/users.json'):
        self.db_file = db_file
        self.ensure_db_exists()
    
    def ensure_db_exists(self):
        os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
        if not os.path.exists(self.db_file):
            self._initialize_demo_users()
    
    def _initialize_demo_users(self):
        """Create demo users for the presentation"""
        demo_users = {
            'users': [
                {
                    'id': 1,
                    'username': 'cfo@sadpmr.gov.za',
                    'password_hash': generate_password_hash('demo123'),
                    'full_name': 'Sarah Nkosi',
                    'role': 'CFO',
                    'email': 'cfo@sadpmr.gov.za',
                    'created_at': datetime.now().isoformat(),
                    'is_active': True
                },
                {
                    'id': 2,
                    'username': 'accountant@sadpmr.gov.za',
                    'password_hash': generate_password_hash('demo123'),
                    'full_name': 'Thabo Mthembu',
                    'role': 'ACCOUNTANT',
                    'email': 'accountant@sadpmr.gov.za',
                    'created_at': datetime.now().isoformat(),
                    'is_active': True
                },
                {
                    'id': 3,
                    'username': 'clerk@sadpmr.gov.za',
                    'password_hash': generate_password_hash('demo123'),
                    'full_name': 'Lerato Dlamini',
                    'role': 'CLERK',
                    'email': 'clerk@sadpmr.gov.za',
                    'created_at': datetime.now().isoformat(),
                    'is_active': True
                },
                {
                    'id': 4,
                    'username': 'auditor@agsa.gov.za',
                    'password_hash': generate_password_hash('demo123'),
                    'full_name': 'AGSA Auditor',
                    'role': 'AUDITOR',
                    'email': 'auditor@agsa.gov.za',
                    'created_at': datetime.now().isoformat(),
                    'is_active': True
                }
            ],
            'sessions': []
        }
        
        with open(self.db_file, 'w') as f:
            json.dump(demo_users, f, indent=2)
    
    def get_user_by_username(self, username):
        """Get user by username"""
        with open(self.db_file, 'r') as f:
            data = json.load(f)
        
        for user in data['users']:
            if user['username'] == username:
                return user
        return None
    
    def get_user_by_id(self, user_id):
        """Get user by ID"""
        with open(self.db_file, 'r') as f:
            data = json.load(f)
        
        for user in data['users']:
            if user['id'] == user_id:
                return user
        return None
    
    def verify_password(self, username, password):
        """Verify user password"""
        user = self.get_user_by_username(username)
        if user and check_password_hash(user['password_hash'], password):
            return user
        return None


class User:
    """User model for authentication"""
    
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = user_data['username']
        self.full_name = user_data['full_name']
        self.role = user_data['role']
        self.email = user_data['email']
        self.is_active = user_data['is_active']
    
    def get_id(self):
        return str(self.id)
    
    def is_authenticated(self):
        return True
    
    def is_anonymous(self):
        return False
    
    def has_permission(self, permission):
        """Check if user has specific permission"""
        permissions = {
            'CFO': ['upload', 'process', 'approve', 'generate_pdf', 'view_all', 'export'],
            'ACCOUNTANT': ['upload', 'process', 'generate_pdf', 'view_all'],
            'CLERK': ['upload', 'view_own'],
            'AUDITOR': ['view_all']
        }
        return permission in permissions.get(self.role, [])
    
    def can_upload(self):
        return self.has_permission('upload')
    
    def can_process(self):
        return self.has_permission('process')
    
    def can_approve(self):
        return self.has_permission('approve')
    
    def can_generate_pdf(self):
        return self.has_permission('generate_pdf')
    
    def can_view_all(self):
        return self.has_permission('view_all')


def get_role_description(role):
    """Get human-readable role description"""
    descriptions = {
        'CFO': 'Chief Financial Officer - Full Access',
        'ACCOUNTANT': 'Accountant - Process & Generate Reports',
        'CLERK': 'Clerk - Upload Trial Balances Only',
        'AUDITOR': 'Auditor - View Only Access'
    }
    return descriptions.get(role, role)


def get_role_color(role):
    """Get color for role badge"""
    colors = {
        'CFO': '#d4a574',  # Gold
        'ACCOUNTANT': '#3182ce',  # Blue
        'CLERK': '#10b981',  # Green
        'AUDITOR': '#f59e0b'  # Orange
    }
    return colors.get(role, '#6b7280')


# Initialize database
db = SimpleDB()
