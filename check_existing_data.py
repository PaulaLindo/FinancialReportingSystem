#!/usr/bin/env python3
"""
Check existing data in database
"""

import os
from supabase import create_client
from dotenv import load_dotenv

def check_existing_data():
    load_dotenv()

    client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_ANON_KEY'))

    print('=== CHECKING EXISTING DATA ===')

    # Check all workflows in database
    all_workflows = client.table('approval_workflows').select('*').execute()
    print(f'Total workflows in database: {len(all_workflows.data)}')

    # Group by creator_id to see what users have workflows
    user_workflows = {}
    for workflow in all_workflows.data:
        creator_id = workflow.get('creator_id', 'unknown')
        if creator_id not in user_workflows:
            user_workflows[creator_id] = []
        user_workflows[creator_id].append(workflow.get('document_type', 'unknown'))

    print('\nWorkflows by user:')
    for user_id, workflows in user_workflows.items():
        print(f'  User {user_id}: {len(workflows)} workflows')
        for workflow in workflows[:3]:  # Show first 3 per user
            doc_type = workflow.get('document_type', 'unknown')
            status = workflow.get('status', 'unknown')
            created = workflow.get('created_at', 'unknown')
            print(f'    - {doc_type}: {status} (created: {created})')

    # Check specifically for our target user
    target_user = '55a380a8-44f0-4502-9024-b23a10e6e17f'
    if target_user in user_workflows:
        print(f'\nTarget user already has {len(user_workflows[target_user])} workflows')
    else:
        print(f'\nTarget user has no workflows')

if __name__ == "__main__":
    check_existing_data()
