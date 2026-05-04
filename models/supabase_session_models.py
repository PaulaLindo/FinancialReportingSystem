"""
Varydian Financial Reporting System - Supabase Session Management
Session handling using Supabase instead of filesystem storage
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from supabase import create_client
import os
import json
import hashlib

class SupabaseSessionManager:
    """Supabase-based session management"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.supabase_url = os.environ.get('SUPABASE_URL')
        self.supabase_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
        
        self.client = create_client(self.supabase_url, self.supabase_key)
        self.session_lifetime = timedelta(hours=1)  # 1 hour sessions
    
    def generate_session_token(self, user_id: str) -> str:
        """Generate a secure session token"""
        timestamp = str(datetime.now().timestamp())
        raw_token = f"{user_id}:{timestamp}:{os.urandom(16).hex()}"
        return hashlib.sha256(raw_token.encode()).hexdigest()
    
    def create_session(self, user_id: str, ip_address: str = None, 
                      user_agent: str = None) -> Dict[str, Any]:
        """Create a new session for a user"""
        try:
            session_token = self.generate_session_token(user_id)
            expires_at = datetime.now() + self.session_lifetime
            
            session_data = {
                'user_id': user_id,
                'session_token': session_token,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'expires_at': expires_at.isoformat(),
                'is_active': True,
                'last_activity': datetime.now().isoformat()
            }
            
            result = self.client.table('user_sessions').insert(session_data).execute()
            
            if result.data:
                return {
                    'success': True,
                    'session_token': session_token,
                    'expires_at': expires_at.isoformat(),
                    'session_id': result.data[0]['id']
                }
            else:
                return {'success': False, 'error': 'Failed to create session'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Get session by token"""
        try:
            result = self.client.table('user_sessions').select(
                '*',
                count='exact'
            ).eq('session_token', session_token).eq('is_active', True).execute()
            
            if result.data and len(result.data) > 0:
                session = result.data[0]
                
                # Check if session is expired
                expires_at_str = session['expires_at'].replace('Z', '+00:00') if session['expires_at'].endswith('Z') else session['expires_at']
                expires_at = datetime.fromisoformat(expires_at_str)
                now = datetime.now()
                if expires_at.replace(tzinfo=None) <= now.replace(tzinfo=None):
                    # Session expired, deactivate it
                    self.deactivate_session(session_token)
                    return None
                
                # Update last activity
                self.update_session_activity(session_token)
                return session
            
            return None
            
        except Exception as e:
            return None
    
    def update_session_activity(self, session_token: str) -> bool:
        """Update session last activity timestamp"""
        try:
            result = self.client.table('user_sessions').update({
                'last_activity': datetime.now().isoformat()
            }).eq('session_token', session_token).execute()
            
            return result.data is not None
            
        except Exception as e:
            return False
    
    def deactivate_session(self, session_token: str) -> bool:
        """Deactivate a session"""
        try:
            result = self.client.table('user_sessions').update({
                'is_active': False
            }).eq('session_token', session_token).execute()
            
            return result.data is not None
            
        except Exception as e:
            return False
    
    def deactivate_user_sessions(self, user_id: str) -> int:
        """Deactivate all sessions for a user"""
        try:
            result = self.client.table('user_sessions').update({
                'is_active': False
            }).eq('user_id', user_id).eq('is_active', True).execute()
            
            return len(result.data) if result.data else 0
            
        except Exception as e:
            return 0
    
    def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions"""
        try:
            result = self.client.rpc('cleanup_expired_sessions').execute()
            return result.data[0]['cleanup_expired_sessions'] if result.data else 0
            
        except Exception as e:
            return 0
    
    def get_active_sessions(self, user_id: str = None) -> List[Dict[str, Any]]:
        """Get active sessions"""
        try:
            query = self.client.table('active_sessions').select('*')
            
            if user_id:
                query = query.eq('user_id', user_id)
            
            result = query.order('created_at', desc=True).execute()
            return result.data if result.data else []
            
        except Exception as e:
            return []
    
    def get_session_count(self, user_id: str = None) -> int:
        """Get count of active sessions"""
        try:
            query = self.client.table('user_sessions').select('id', count='exact')
            
            if user_id:
                query = query.eq('user_id', user_id)
            
            query = query.eq('is_active', True).eq('expires_at', 'gt', datetime.now().isoformat())
            
            result = query.execute()
            return result.count if result.count else 0
            
        except Exception as e:
            return 0

# Initialize session manager
supabase_session_manager = SupabaseSessionManager()

# Flask session interface compatibility
class SupabaseSessionInterface:
    """Flask session interface using Supabase"""
    
    def __init__(self, session_manager=None):
        self.session_manager = session_manager or supabase_session_manager
    
    def get(self, key: str, default=None):
        """Get session value"""
        # This would need to be integrated with Flask's session handling
        # For now, return None as this is a placeholder
        return default
    
    def set(self, key: str, value):
        """Set session value"""
        # This would need to be integrated with Flask's session handling
        pass
    
    def delete(self, key: str):
        """Delete session value"""
        # This would need to be integrated with Flask's session handling
        pass
    
    def clear(self):
        """Clear all session data"""
        # This would need to be integrated with Flask's session handling
        pass
