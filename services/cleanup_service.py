"""
SADPMR Financial Reporting System - Cleanup Service
Service for cleaning up failed/unbalanced balance sheets from the database
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List

from models.balance_sheet_models import balance_sheet_model

logger = logging.getLogger(__name__)

class CleanupService:
    """Service for cleaning up failed balance sheets and maintaining database hygiene"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def cleanup_unbalanced_balance_sheets(self, hours_old: int = 24) -> Dict[str, Any]:
        """
        Remove unbalanced balance sheets from the database
        
        Args:
            hours_old: Only remove sessions older than this many hours (default: 24)
            
        Returns:
            Dict with cleanup results
        """
        try:
            self.logger.info(f"Starting cleanup of unbalanced balance sheets older than {hours_old} hours")
            
            # Get cutoff time
            cutoff_time = datetime.now() - timedelta(hours=hours_old)
            
            # Get all uploaded sessions that are unbalanced
            unbalanced_sessions = self._get_unbalanced_sessions(cutoff_time)
            
            if not unbalanced_sessions:
                self.logger.info("No unbalanced balance sheets found for cleanup")
                return {
                    'success': True,
                    'cleaned_count': 0,
                    'message': 'No unbalanced balance sheets found for cleanup'
                }
            
            # Clean up each session
            cleaned_count = 0
            errors = []
            
            for session in unbalanced_sessions:
                try:
                    # Delete the session and all related data
                    success = self._delete_session(session.id)
                    
                    if success:
                        cleaned_count += 1
                        self.logger.info(f"Cleaned up unbalanced session: {session.id[:8]}...")
                    else:
                        errors.append(f"Failed to delete session {session.id}")
                        
                except Exception as e:
                    error_msg = f"Error cleaning session {session.id}: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)
            
            result = {
                'success': len(errors) == 0,
                'cleaned_count': cleaned_count,
                'total_found': len(unbalanced_sessions),
                'errors': errors,
                'message': f"Cleaned {cleaned_count} out of {len(unbalanced_sessions)} unbalanced balance sheets"
            }
            
            if errors:
                result['message'] += f". {len(errors)} errors occurred."
            
            self.logger.info(f"Cleanup completed: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'cleaned_count': 0
            }
    
    def cleanup_failed_uploads(self, hours_old: int = 1) -> Dict[str, Any]:
        """
        Remove recently failed uploads (sessions that never progressed beyond 'uploaded')
        
        Args:
            hours_old: Only remove sessions older than this many hours (default: 1)
            
        Returns:
            Dict with cleanup results
        """
        try:
            self.logger.info(f"Starting cleanup of failed uploads older than {hours_old} hours")
            
            # Get cutoff time
            cutoff_time = datetime.now() - timedelta(hours=hours_old)
            
            # Get all uploaded sessions that never progressed
            failed_sessions = self._get_failed_uploads(cutoff_time)
            
            if not failed_sessions:
                self.logger.info("No failed uploads found for cleanup")
                return {
                    'success': True,
                    'cleaned_count': 0,
                    'message': 'No failed uploads found for cleanup'
                }
            
            # Clean up each session
            cleaned_count = 0
            errors = []
            
            for session in failed_sessions:
                try:
                    # Delete the session and all related data
                    success = self._delete_session(session.id)
                    
                    if success:
                        cleaned_count += 1
                        self.logger.info(f"Cleaned up failed upload session: {session.id[:8]}...")
                    else:
                        errors.append(f"Failed to delete session {session.id}")
                        
                except Exception as e:
                    error_msg = f"Error cleaning session {session.id}: {str(e)}"
                    self.logger.error(error_msg)
                    errors.append(error_msg)
            
            result = {
                'success': len(errors) == 0,
                'cleaned_count': cleaned_count,
                'total_found': len(failed_sessions),
                'errors': errors,
                'message': f"Cleaned {cleaned_count} out of {len(failed_sessions)} failed uploads"
            }
            
            if errors:
                result['message'] += f". {len(errors)} errors occurred."
            
            self.logger.info(f"Failed upload cleanup completed: {result}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed upload cleanup failed: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'cleaned_count': 0
            }
    
    def cleanup_specific_session(self, session_id: str) -> Dict[str, Any]:
        """
        Clean up a specific session (immediate cleanup for current uploads)
        
        Args:
            session_id: The session ID to clean up
            
        Returns:
            Dict with cleanup results
        """
        try:
            self.logger.info(f"Starting cleanup of specific session: {session_id}")
            
            # Get the session
            session = balance_sheet_model.get_session(session_id)
            if not session:
                return {
                    'success': False,
                    'error': f'Session {session_id} not found'
                }
            
            if self._delete_session(session_id):
                self.logger.info(f"Successfully cleaned up session: {session_id}")
                return {
                    'success': True,
                    'message': f'Session {session_id} and all related data cleaned up successfully'
                }
            else:
                return {
                    'success': False,
                    'error': f'Failed to delete session {session_id}'
                }
            
        except Exception as e:
            self.logger.error(f"Error in cleanup_specific_session for {session_id}: {str(e)}")
            return {
                'success': False,
                'error': f'An unexpected error occurred during cleanup: {str(e)}'
            }
    
    def _delete_session(self, session_id: str) -> bool:
        """Delete a session and all its related data"""
        try:
            # Delete balance sheet data rows first
            data_rows = balance_sheet_model.client.table('balance_sheet_data').select('*').eq('session_id', session_id).execute().data
            if data_rows:
                for row in data_rows:
                    balance_sheet_model.client.table('balance_sheet_data').delete().eq('id', row['id']).execute()
            
            # Delete column definitions
            balance_sheet_model.client.table('balance_sheet_columns').delete().eq('session_id', session_id).execute()
            
            # Delete the session itself
            balance_sheet_model.client.table('balance_sheet_sessions').delete().eq('id', session_id).execute()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting session {session_id}: {str(e)}")
            return False
    
    def _get_unbalanced_sessions(self, cutoff_time: datetime) -> List:
        """Get unbalanced balance sheet sessions older than cutoff time"""
        try:
            # Get sessions that are marked as unbalanced
            response = balance_sheet_model.client.table('balance_sheet_sessions').select('*').eq('status', 'unbalanced').lt('created_at', cutoff_time.isoformat()).execute()
            return response.data or []
        except Exception as e:
            self.logger.error(f"Error getting unbalanced sessions: {str(e)}")
            return []
    
    def _get_failed_uploads(self, cutoff_time: datetime) -> List:
        """Get failed upload sessions older than cutoff time"""
        try:
            # Get sessions that are still in 'uploaded' status and are old
            response = balance_sheet_model.client.table('balance_sheet_sessions').select('*').eq('status', 'uploaded').lt('created_at', cutoff_time.isoformat()).execute()
            return response.data or []
        except Exception as e:
            self.logger.error(f"Error getting failed uploads: {str(e)}")
            return []
