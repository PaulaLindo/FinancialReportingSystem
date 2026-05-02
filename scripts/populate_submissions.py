#!/usr/bin/env python3
"""
Populate Submissions Table
Create submission records for existing trial balance sessions
"""

import sys
import os
from datetime import datetime

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.trial_balance_models import trial_balance_model
from models.workflow_models import SubmissionWorkflowModel


def populate_submissions():
    """Create submission records for existing sessions"""
    
    print("🔒 Populating submissions table...")
    print("=" * 50)
    
    # Initialize models
    submission_model = SubmissionWorkflowModel()
    
    # Get all existing sessions
    try:
        # Query all sessions directly since get_all_sessions doesn't exist
        result = trial_balance_model.client.table('trial_balance_sessions').select('*').order('created_at', desc=True).limit(100).execute()
        sessions = result.data if result.data else []
        print(f"📊 Found {len(sessions)} existing sessions")
        
        success_count = 0
        error_count = 0
        
        for session in sessions:
            try:
                # Check if submission already exists
                session_id = session.get('id')
                if not session_id:
                    print(f"⚠️  Session missing ID - skipping")
                    continue
                    
                existing_result = submission_model.get_submission(session_id)
                
                if existing_result['success']:
                    print(f"⏭️  Session {session_id[:8]}... - Submission already exists")
                    continue
                
                # Create submission record
                submission_data = {
                    'session_id': session_id,
                    'user_id': session.get('user_id'),
                    'submission_name': f"Submission - {session.get('original_filename', 'Unknown File')}",
                    'original_filename': session.get('original_filename'),
                    'period_id': None,  # Can be set later
                    'total_accounts': 0,  # Will be updated when mapping is complete
                    'mapped_accounts': 0,
                    'unmapped_accounts': 0,
                    'total_assets': 0.0,
                    'total_liabilities': 0.0,
                    'total_equity': 0.0,
                    'total_revenue': 0.0,
                    'total_expenses': 0.0,
                    'data_quality_score': 0.0,
                    'grap_categories_used': 0,
                    'mapping_completion_percentage': 0.00,
                    'submitted_at': session.get('created_at') or datetime.now().isoformat(),
                    'mapping_date': None,
                    'status_date': datetime.now().isoformat(),
                    'is_locked': False,  # Default to unlocked
                    'locked_at': None,
                    'locked_by': None,
                    'status': 'draft',  # Initial status
                    'priority': 'normal',
                    'metadata': {
                        'created_from_session': True,
                        'original_session_status': session.get('status'),
                        'migration_date': datetime.now().isoformat()
                    },
                    'grap_mapping_data': {},
                    'financial_statements': {}
                }
                
                # Create the submission
                result = submission_model.create_submission(submission_data)
                
                if result['success']:
                    success_count += 1
                    print(f"✅ Session {session_id[:8]}... - Created submission (Locked: {submission_data['is_locked']})")
                else:
                    error_count += 1
                    print(f"❌ Session {session_id[:8]}... - Failed: {result.get('error', 'Unknown error')}")
                
            except Exception as e:
                error_count += 1
                print(f"❌ Session {session_id[:8]}... - Error: {str(e)}")
        
        print("=" * 50)
        print(f"📊 Summary: {success_count} submissions created, {error_count} errors")
        
        if error_count == 0:
            print("🎉 All sessions processed successfully!")
        else:
            print("⚠️ Some sessions failed to process. Check the errors above.")
        
        return success_count, error_count
        
    except Exception as e:
        print(f"💥 Fatal error getting sessions: {str(e)}")
        return 0, 1


def verify_submissions():
    """Verify submissions were created correctly"""
    
    print("\n🔍 Verifying submissions...")
    print("=" * 50)
    
    try:
        submission_model = SubmissionWorkflowModel()
        
        # Get all submissions
        result = submission_model.client.table('submissions').select('*').execute()
        
        if result.data:
            print(f"📊 Total submissions in database: {len(result.data)}")
            
            # Show sample submissions
            for i, sub in enumerate(result.data[:5]):  # Show first 5
                print(f"  {i+1}. Session: {sub.get('session_id', 'N/A')[:8]}...")
                print(f"     Status: {sub.get('status', 'N/A')}")
                print(f"     Locked: {sub.get('is_locked', False)}")
                print(f"     Created: {sub.get('created_at', 'N/A')}")
                print()
        else:
            print("❌ No submissions found")
        
        return len(result.data) if result.data else 0
        
    except Exception as e:
        print(f"❌ Error verifying submissions: {str(e)}")
        return 0


def main():
    """Main function to populate submissions"""
    try:
        # Populate submissions
        success_count, error_count = populate_submissions()
        
        # Verify results
        total_submissions = verify_submissions()
        
        print(f"\n🎯 Final Result: {total_submissions} total submissions in database")
        
        return 0 if error_count == 0 else 1
        
    except Exception as e:
        print(f"💥 Fatal error: {str(e)}")
        return 1


if __name__ == '__main__':
    exit_code = main()
    sys.exit(exit_code)
