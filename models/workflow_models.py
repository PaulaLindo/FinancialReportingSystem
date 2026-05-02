"""
SADPMR Financial Reporting System - Workflow Models
Period management and submission workflow tracking
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from supabase import create_client
import os
import json

class WorkflowModel:
    """Period management and submission workflow model"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.supabase_url = os.environ.get('SUPABASE_URL')
        self.supabase_key = os.environ.get('SUPABASE_ANON_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
        
        self.client = create_client(self.supabase_url, self.supabase_key)
    
    def create_period(self, period_data: Dict) -> Dict[str, Any]:
        """Create a new reporting period"""
        try:
            period_record = {
                'name': period_data['name'],
                'start_date': period_data['start_date'],
                'end_date': period_data['end_date'],
                'due_date': period_data['due_date'],
                'status': 'open',  # open, closed, locked
                'required_count': period_data.get('required_count', 1),
                'uploaded_count': 0,
                'created_by': period_data['created_by'],
                'created_at': datetime.now().isoformat()
            }
            
            result = self.client.table('periods').insert(period_record).execute()
            
            if result.data:
                return {
                    'success': True,
                    'period': result.data[0],
                    'message': f'Period {period_data["name"]} created successfully'
                }
            else:
                return {'success': False, 'error': 'Failed to create period'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_open_periods(self) -> List[Dict[str, Any]]:
        """Get all open reporting periods"""
        try:
            result = self.client.table('periods').select('*').eq('status', 'open').order('due_date', desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            return []
    
    def get_all_periods(self) -> List[Dict[str, Any]]:
        """Get all reporting periods"""
        try:
            result = self.client.table('periods').select('*').order('created_at', desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            return []
    
    def update_period_status(self, period_id: str, status: str) -> Dict[str, Any]:
        """Update period status"""
        try:
            result = self.client.table('periods').update({
                'status': status,
                'updated_at': datetime.now().isoformat()
            }).eq('id', period_id).execute()
            
            if result.data:
                return {
                    'success': True,
                    'period': result.data[0],
                    'message': f'Period status updated to {status}'
                }
            else:
                return {'success': False, 'error': 'Failed to update period status'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def increment_period_uploads(self, period_id: str) -> Dict[str, Any]:
        """Increment upload count for a period"""
        try:
            # Get current period
            period_result = self.client.table('periods').select('uploaded_count').eq('id', period_id).execute()
            
            if not period_result.data:
                return {'success': False, 'error': 'Period not found'}
            
            current_count = period_result.data[0]['uploaded_count']
            
            # Update with incremented count
            result = self.client.table('periods').update({
                'uploaded_count': current_count + 1,
                'last_upload': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }).eq('id', period_id).execute()
            
            if result.data:
                return {
                    'success': True,
                    'uploaded_count': current_count + 1,
                    'message': 'Upload count updated'
                }
            else:
                return {'success': False, 'error': 'Failed to update upload count'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_period_stats(self) -> Dict[str, Any]:
        """Get statistics for dashboard"""
        try:
            # Get all periods
            periods_result = self.client.table('periods').select('*').execute()
            periods = periods_result.data if periods_result.data else []
            
            stats = {
                'open_periods': 0,
                'closed_periods': 0,
                'total_periods': len(periods),
                'pending_uploads': 0,
                'submitted_today': 0,
                'approved_this_month': 0
            }
            
            # Calculate stats
            today = datetime.now().date()
            this_month_start = today.replace(day=1)
            
            for period in periods:
                if period['status'] == 'open':
                    stats['open_periods'] += 1
                elif period['status'] == 'closed':
                    stats['closed_periods'] += 1
                
                # Count uploads today and this month
                if period.get('last_upload'):
                    last_upload_date = datetime.fromisoformat(period['last_upload']).date()
                    if last_upload_date == today:
                        stats['submitted_today'] += 1
                    if this_month_start <= last_upload_date <= today:
                        stats['approved_this_month'] += 1
            
            return stats
            
        except Exception as e:
            return {
                'open_periods': 0,
                'closed_periods': 0,
                'total_periods': 0,
                'pending_uploads': 0,
                'submitted_today': 0,
                'approved_this_month': 0
            }

class SubmissionWorkflowModel:
    """Submission workflow tracking model"""
    
    def __init__(self):
        """Initialize Supabase client"""
        self.supabase_url = os.environ.get('SUPABASE_URL')
        self.supabase_key = os.environ.get('SUPABASE_ANON_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")
        
        self.client = create_client(self.supabase_url, self.supabase_key)
    
    def create_submission(self, submission_data: Dict) -> Dict[str, Any]:
        """Create a new submission"""
        try:
            submission_record = {
                'session_id': submission_data['session_id'],
                'period_id': submission_data.get('period_id'),
                'user_id': submission_data['user_id'],
                'filename': submission_data['filename'],
                'original_filename': submission_data['original_filename'],
                'status': submission_data['draft'],
                'total_accounts': submission_data.get('total_accounts', 0),
                'mapped_accounts': submission_data.get('mapped_accounts', 0),
                'unmapped_accounts': submission_data.get('unmapped_accounts', 0),
                'total_assets': submission_data.get('total_assets', 0),
                'total_liabilities': submission_data.get('total_liabilities', 0),
                'grap_categories_used': submission_data.get('grap_categories_used', 0),
                'mapping_completeness': submission_data.get('mapping_completeness', '0%'),
                'upload_date': submission_data.get('upload_date', datetime.now().isoformat()),
                'mapping_date': submission_data.get('mapping_date'),
                'status_date': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat()
            }
            
            result = self.client.table('submissions').insert(submission_record).execute()
            
            if result.data:
                return {
                    'success': True,
                    'submission': result.data[0],
                    'message': f'Submission {submission_data["session_id"]} created'
                }
            else:
                return {'success': False, 'error': 'Failed to create submission'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_submission(self, session_id: str) -> Dict[str, Any]:
        """Get submission by session ID"""
        try:
            result = self.client.table('submissions').select('*').eq('session_id', session_id).execute()
            
            if result.data:
                return {
                    'success': True,
                    'submission': result.data[0]
                }
            else:
                return {'success': False, 'error': 'Submission not found'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def update_submission_status(self, session_id: str, status: str, feedback: Dict = None) -> Dict[str, Any]:
        """Update submission status"""
        try:
            update_data = {
                'status': status,
                'status_date': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            if feedback:
                update_data['feedback'] = feedback
            
            result = self.client.table('submissions').update(update_data).eq('session_id', session_id).execute()
            
            if result.data:
                return {
                    'success': True,
                    'submission': result.data[0],
                    'message': f'Submission status updated to {status}'
                }
            else:
                return {'success': False, 'error': 'Failed to update submission status'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_pending_submissions(self, approver_role: str = None) -> List[Dict[str, Any]]:
        """Get pending submissions for approval"""
        try:
            query = self.client.table('submissions').select('*').eq('status', 'submitted').order('created_at', desc=True)
            
            result = query.execute()
            return result.data if result.data else []
            
        except Exception as e:
            return []
    
    def get_user_submissions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all submissions by a user"""
        try:
            result = self.client.table('submissions').select('*').eq('user_id', user_id).order('created_at', desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            return []
    
    def delete_submission(self, session_id: str) -> Dict[str, Any]:
        """Delete a submission"""
        try:
            result = self.client.table('submissions').delete().eq('session_id', session_id).execute()
            
            if result.data:
                return {
                    'success': True,
                    'message': 'Submission deleted successfully'
                }
            else:
                return {'success': False, 'error': 'Failed to delete submission'}
                
        except Exception as e:
            return {'success': False, 'error': str(e)}

# Initialize models
workflow_model = WorkflowModel()
submission_workflow_model = SubmissionWorkflowModel()
