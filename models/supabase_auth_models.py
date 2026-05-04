"""
Varydian Financial Reporting System - Supabase Authentication Models
User authentication and role-based access control using Supabase
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from supabase import create_client
import os
import json

class SupabaseAuthModel:
    """Supabase-based user authentication model"""
    
    def __init__(self):
        """Initialize Supabase client with anon key only"""
        self.supabase_url = None
        self.supabase_anon_key = None
        self.client = None
        self._initialized = False
    
    def _ensure_initialized(self):
        """Lazy initialization of Supabase client"""
        if self._initialized:
            return
        
        # Load environment variables if not already loaded
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass  # dotenv not available in production
        
        self.supabase_url = os.environ.get('SUPABASE_URL')
        self.supabase_anon_key = os.environ.get('SUPABASE_ANON_KEY')
        
        if not self.supabase_url or not self.supabase_anon_key:
            raise ValueError("Supabase credentials not found. Check SUPABASE_URL and SUPABASE_ANON_KEY in environment variables")
        
        try:
            # Create client with only URL and key - maximum compatibility
            self.client = create_client(self.supabase_url, self.supabase_anon_key)
            self._initialized = True
            print("✅ Supabase auth model initialized with anon key (secure, RLS-compliant)")
        except Exception as e:
            # Try alternative import pattern
            try:
                from supabase import Client
                self.client = Client(self.supabase_url, self.supabase_anon_key)
                self._initialized = True
                print("✅ Supabase auth model initialized with Client class")
            except Exception as fallback_error:
                raise ValueError(f"Supabase authentication unavailable: {e} (fallback: {fallback_error})")
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        self._ensure_initialized()
        try:
            result = self.client.table('users').select('*').eq('username', username).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            return None
    
    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        self._ensure_initialized()
        try:
            result = self.client.table('users').select('*').eq('email', email).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            return None
    
    def verify_password(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """Verify user password using Supabase"""
        from werkzeug.security import check_password_hash
        
        user = self.get_user_by_username(username)
        if user:
            # Supabase authentication with secure hash check
            if check_password_hash(user['password_hash'], password):
                return user
        
        return None
    
    def create_user(self, username: str, password: str, full_name: str, 
                   role: str, email: str) -> Dict[str, Any]:
        """Create a new user"""
        from werkzeug.security import generate_password_hash
        
        try:
            user_data = {
                'username': username,
                'password_hash': generate_password_hash(password),
                'full_name': full_name,
                'role': role,
                'email': email,
                'is_active': True,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            self._ensure_initialized()
            result = self.client.table('users').insert(user_data).execute()
            
            if result.data:
                return {
                    'success': True,
                    'user': result.data[0],
                    'message': 'User created successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to create user'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_user(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user information"""
        try:
            updates['updated_at'] = datetime.now().isoformat()
            
            self._ensure_initialized()
            result = self.client.table('users').update(updates).eq('id', user_id).execute()
            
            if result.data:
                return {
                    'success': True,
                    'user': result.data[0],
                    'message': 'User updated successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'User not found or update failed'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def deactivate_user(self, user_id: str) -> Dict[str, Any]:
        """Deactivate a user"""
        return self.update_user(user_id, {'is_active': False})
    
    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users"""
        self._ensure_initialized()
        try:
            result = self.client.table('users').select('*').order('created_at', desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            return []
    
    def get_users_by_role(self, role: str) -> List[Dict[str, Any]]:
        """Get users by role"""
        self._ensure_initialized()
        try:
            result = self.client.table('users').select('*').eq('role', role).execute()
            return result.data if result.data else []
        except Exception as e:
            return []
    
    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        self._ensure_initialized()
        try:
            result = self.client.table('users').select('*').eq('id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            return None
    
        
    def get_user_by_role(self, role: str) -> Optional[Dict[str, Any]]:
        """Get first user by role"""
        users = self.get_users_by_role(role)
        return users[0] if users else None
    
    def change_password(self, user_id: str, new_password: str) -> Dict[str, Any]:
        """Change user password"""
        from werkzeug.security import generate_password_hash
        
        return self.update_user(user_id, {
            'password_hash': generate_password_hash(new_password)
        })

class SupabaseUser:
    """User model for Supabase authentication"""
    
    def __init__(self, user_data: Dict[str, Any]):
        self.id = user_data['id']
        self.username = user_data['username']
        self.full_name = user_data['full_name']
        self.role = user_data['role']
        self.email = user_data['email']
        self.is_active = user_data['is_active']
        self.created_at = user_data['created_at']
        self.updated_at = user_data.get('updated_at')
    
    def get_id(self):
        return str(self.id)
    
    def is_authenticated(self):
        return True
    
    def is_anonymous(self):
        return False
    
    def has_permission(self, permission):
        """Check if user has specific permission"""
        permissions = {
            # Primary active roles
            'FINANCE_CLERK': ['upload', 'process', 'view_own'],
            'FINANCE_MANAGER': ['review', 'approve', 'process', 'view_all'],
            'CFO': ['final_approve', 'generate_pdf', 'view_all', 'export', 'export_audit', 'review', 'process'],
            'ASSET_MANAGER': ['manage_assets', 'view_assets'],
            'AUDITOR': ['view_all', 'export_audit'],
            'SYSTEM_ADMIN': ['manage_users', 'system_settings', 'view_logs'],
            # Additional active roles for compatibility
            'ACCOUNTANT': ['review', 'approve', 'view_all', 'process'],
        }
        return permission in permissions.get(self.role, [])
    
    def can_upload(self):
        return self.has_permission('upload')
    
    def can_process(self):
        return self.has_permission('process')
    
    def can_approve(self):
        return self.has_permission('approve')
    
    def can_review(self):
        return self.has_permission('review')
    
    def can_final_approve(self):
        return self.has_permission('final_approve')
    
    def can_generate_pdf(self):
        return self.has_permission('generate_pdf')
    
    def can_view_all(self):
        return self.has_permission('view_all')
    
    def can_manage_assets(self):
        return self.has_permission('manage_assets')
    
    def can_manage_users(self):
        return self.has_permission('manage_users')
    
    def can_export_audit(self):
        return self.has_permission('export_audit')
    
    def can_export(self):
        return self.has_permission('export')

# Lazy initialization of Supabase auth model
supabase_auth = None

def get_supabase_auth():
    """Get or create Supabase auth model instance"""
    global supabase_auth
    if supabase_auth is None:
        supabase_auth = SupabaseAuthModel()
    return supabase_auth

# Legacy compatibility functions
def get_role_description(role):
    """Get human-readable role description"""
    descriptions = {
        # Primary active roles
        'FINANCE_CLERK': 'Finance Clerk - Upload & Create Transactions (Requires Approval)',
        'FINANCE_MANAGER': 'Finance Manager - Review & Approve Transactions',
        'CFO': 'Chief Financial Officer - Final Approval & Strategic Oversight',
        'ASSET_MANAGER': 'Asset Manager - Manage Asset Register & Impairments',
        'AUDITOR': 'Auditor - View Only Access (Read-Only)',
        'SYSTEM_ADMIN': 'System Administrator - User & System Management (No Financial Access)',
        'ACCOUNTANT': 'Accountant - Review, Approve, Process & Generate Reports',
        'CLERK': 'Clerk - Upload Balance Sheets & View Own Files'
    }
    return descriptions.get(role, role)

def get_role_color(role):
    """Get color for role badge"""
    colors = {
        # Primary active roles
        'FINANCE_CLERK': '#10b981',  # Green
        'FINANCE_MANAGER': '#3182ce',  # Blue
        'CFO': '#d4a574',  # Gold
        'ASSET_MANAGER': '#8b5cf6',  # Purple
        'AUDITOR': '#f59e0b',  # Orange
        'SYSTEM_ADMIN': '#ef4444',  # Red
        'ACCOUNTANT': '#3182ce',  # Blue
        'CLERK': '#10b981'  # Green
    }
    return colors.get(role, '#6b7280')


def get_current_user():
    """Get current user from session"""
    from flask import session
    
    if 'user_id' not in session:
        return None
    
    auth = get_supabase_auth()
    user_data = auth.get_user_by_id(session['user_id'])
    if not user_data:
        return None
    
    return SupabaseUser(user_data)

# For backward compatibility with existing code
User = SupabaseUser
db = get_supabase_auth()
