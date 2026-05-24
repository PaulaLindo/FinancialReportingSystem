#!/usr/bin/env python3
"""
Create test approval workflow data for development
"""

import os
from supabase import create_client
from datetime import datetime
import uuid
from dotenv import load_dotenv

def create_test_approval_workflows():
    """Create test approval workflows in database"""
    
    load_dotenv()

    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')

    if not supabase_url or not supabase_key:
        print("Missing Supabase credentials")
        return False

    client = create_client(supabase_url, supabase_key)

    # Create test approval workflows
    test_workflows = [
        {
            'id': str(uuid.uuid4()),
            'document_id': str(uuid.uuid4()),
            'document_type': 'balance_sheet',
            'workflow_type': 'four_eyes',
            'current_step': 1,
            'status': 'pending',
            'priority': 'normal',
            'creator_id': str(uuid.uuid4()),  # Proper UUID
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'metadata': {'description': 'Test balance sheet for approval'}
        },
        {
            'id': str(uuid.uuid4()),
            'document_id': str(uuid.uuid4()),
            'document_type': 'income_statement',
            'workflow_type': 'two_eyes',
            'current_step': 2,
            'status': 'in_review',
            'priority': 'high',
            'creator_id': str(uuid.uuid4()),  # Proper UUID
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'metadata': {'description': 'Test income statement requiring review'}
        },
        {
            'id': str(uuid.uuid4()),
            'document_id': str(uuid.uuid4()),
            'document_type': 'budget_report',
            'workflow_type': 'three_eyes',
            'current_step': 3,
            'status': 'approved',
            'priority': 'low',
            'creator_id': str(uuid.uuid4()),  # Proper UUID
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'completed_at': datetime.now().isoformat(),
            'metadata': {'description': 'Test budget report already approved'}
        },
        {
            'id': str(uuid.uuid4()),
            'document_id': str(uuid.uuid4()),
            'document_type': 'cash_flow',
            'workflow_type': 'four_eyes',
            'current_step': 1,
            'status': 'rejected',
            'priority': 'urgent',
            'creator_id': str(uuid.uuid4()),  # Proper UUID
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'metadata': {'description': 'Test cash flow statement that was rejected'}
        }
    ]

    try:
        # Insert test workflows
        for workflow in test_workflows:
            result = client.table('approval_workflows').insert(workflow).execute()
            print(f'Created workflow: {workflow["document_type"]} - {workflow["status"]}')
        
        print('\nTest data created successfully!')
        
        # Verify data
        verify_result = client.table('approval_workflows').select('*').execute()
        print(f'Total workflows in database: {len(verify_result.data)}')
        
        # Show status counts
        status_counts = {}
        for workflow in verify_result.data:
            status = workflow.get('status', 'unknown')
            status_counts[status] = status_counts.get(status, 0) + 1
        print('Status counts:', status_counts)
        
        return True
        
    except Exception as e:
        print(f'Error creating test data: {e}')
        return False

if __name__ == "__main__":
    create_test_approval_workflows()
