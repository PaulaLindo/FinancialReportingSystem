"""
Optimized approval workflow models (SADPMR / Varydian).

**Primary import surface:** ``from services.approval_facade import approval_facade`` then
``.workflow`` (this model) and ``.transactions`` (transactional stack). Prefer that over
importing ``approval_model`` from this module in application code.

**Two stacks** (both may exist in the same deployment):

1. **Document / step workflow — ``ApprovalModel``** (this module, class ``ApprovalModel``)  
   Tables: ``approval_workflows``, ``approval_steps``, ``audit_logs``.  
   Used from classic routes (e.g. ``controllers/routes.py``) for step-based review.

2. **Transactional four-eyes — ``approval_facade.transactions``**  
   Implementation: ``services.transaction_approval_service`` / ``SupabaseApprovalModel``.  
   Tables: ``transaction_approvals``, ``approval_actions``; views: ``pending_approvals``, etc.  
   Use for TX-style approve/reject without a document ``session_id`` (e.g. universal
   ``/api/transaction/approve`` when only ``transaction_id`` is sent).

**Session queue (not stack #2):** ``UniversalWorkflowService.get_pending_approvals`` builds
the finance manager queue from **upload sessions** by status; it does not read
``transaction_approvals``. See that service’s docstring for ``/api/transactions/pending``.

``TransactionApprovalModel`` remains a thin wrapper for backward compatibility; prefer
``approval_facade.transactions`` (or ``transaction_approval_service``) in new code.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from supabase import create_client, Client
from .supabase_auth_models import supabase_auth


@dataclass
class ApprovalWorkflow:
    """Represents an approval workflow instance"""
    id: Optional[str] = None
    document_id: str = ""
    document_type: str = ""
    workflow_type: str = "four_eyes"
    current_step: int = 1
    status: str = "pending"
    priority: str = "normal"
    creator_id: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database operations"""
        data = asdict(self)
        # Remove id field if it's None to let database generate UUID
        if data.get('id') is None:
            del data['id']
        # Convert datetime objects to ISO format
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        return data


@dataclass
class ApprovalStep:
    """Represents a step in the approval workflow"""
    id: Optional[str] = None
    workflow_id: str = ""
    step_name: str = ""
    step_type: str = "review"
    step_order: int = 1
    assigned_role: str = ""
    required_approvals: int = 1
    current_approvals: int = 0
    status: str = "pending"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    approver_id: Optional[str] = None
    approval_notes: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database operations"""
        data = asdict(self)
        # Remove id field if it's None to let database generate UUID
        if data.get('id') is None:
            del data['id']
        # Convert datetime objects to ISO format
        if self.started_at:
            data['started_at'] = self.started_at.isoformat()
        if self.completed_at:
            data['completed_at'] = self.completed_at.isoformat()
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        # Convert empty strings to None for UUID fields
        uuid_fields = ['approver_id']
        for field in uuid_fields:
            if data.get(field) == '':
                data[field] = None
        return data


@dataclass
class UserSession:
    """Represents a user session for security tracking"""
    id: Optional[str] = None
    user_id: str = ""
    session_token: str = ""
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_active: bool = True
    last_activity: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database operations"""
        data = asdict(self)
        # Remove id field if it's None to let database generate UUID
        if data.get('id') is None:
            del data['id']
        # Convert datetime objects to ISO format
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.expires_at:
            data['expires_at'] = self.expires_at.isoformat()
        if self.last_activity:
            data['last_activity'] = self.last_activity.isoformat()
        return data


@dataclass
class AuditLog:
    """Represents an audit log entry"""
    id: Optional[str] = None
    table_name: str = ""
    record_id: str = ""
    action: str = ""
    old_values: Optional[Dict] = None
    new_values: Optional[Dict] = None
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.old_values is None:
            self.old_values = {}
        if self.new_values is None:
            self.new_values = {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database operations"""
        data = asdict(self)
        # Remove id field if it's None to let database generate UUID
        if data.get('id') is None:
            del data['id']
        # Convert datetime objects to ISO format
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        # Convert empty strings to None for UUID fields
        uuid_fields = ['user_id']
        for field in uuid_fields:
            if data.get(field) == '':
                data[field] = None
        return data


@dataclass
class SystemConfiguration:
    """Represents system configuration"""
    id: Optional[str] = None
    config_key: str = ""
    config_value: Any = None
    config_type: str = "string"
    description: Optional[str] = None
    is_public: bool = False
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database operations"""
        data = asdict(self)
        # Remove id field if it's None to let database generate UUID
        if data.get('id') is None:
            del data['id']
        # Convert datetime objects to ISO format
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        # Convert empty strings to None for UUID fields
        uuid_fields = ['created_by', 'updated_by']
        for field in uuid_fields:
            if data.get(field) == '':
                data[field] = None
        return data


@dataclass
class FinancialPeriod:
    """Represents a financial period"""
    id: Optional[str] = None
    period_name: str = ""
    period_code: str = ""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    period_type: str = "monthly"
    fiscal_year: int = 2024
    is_current: bool = False
    is_locked: bool = False
    created_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database operations"""
        data = asdict(self)
        # Remove id field if it's None to let database generate UUID
        if data.get('id') is None:
            del data['id']
        # Convert datetime objects to ISO format
        if self.start_date:
            data['start_date'] = self.start_date.isoformat()
        if self.end_date:
            data['end_date'] = self.end_date.isoformat()
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        # Convert empty strings to None for UUID fields
        uuid_fields = ['created_by']
        for field in uuid_fields:
            if data.get(field) == '':
                data[field] = None
        return data


class ApprovalModel:
    """Optimized approval workflow model using Supabase database"""
    
    def __init__(self):
        # Use centralized Supabase client with fallback authentication
        from utils.supabase_client import create_admin_supabase_client
        
        try:
            self.client = create_admin_supabase_client()
        except ValueError as e:
            # Final fallback to auth client if all keys fail
            from .supabase_auth_models import supabase_auth
            self.client = supabase_auth.client
            print(f"⚠️ Fallback to auth client: {e}")
    
    # ==================== APPROVAL WORKFLOW MANAGEMENT ====================
    
    def create_workflow(self, creator_id: str, document_id: str, document_type: str, workflow_type: str = 'four_eyes', priority: str = 'normal') -> ApprovalWorkflow:
        """Create a new approval workflow with parameters"""
        try:
            # Create ApprovalWorkflow object
            workflow = ApprovalWorkflow(
                document_id=document_id,
                document_type=document_type,
                workflow_type=workflow_type,
                priority=priority,
                creator_id=creator_id,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Call the original create_workflow method
            workflow_id = self._create_workflow_object(workflow)
            workflow.id = workflow_id
            
            return workflow
            
        except Exception as e:
            print(f"💥 Error in create_workflow wrapper: {str(e)}")
            raise Exception(f"Failed to create approval workflow: {str(e)}")
    
    def _create_workflow_object(self, workflow: ApprovalWorkflow) -> str:
        """Create a new approval workflow"""
        try:
            print(f"💾 ApprovalModel.create_workflow called")
            print(f"📄 document_id: {workflow.document_id}")
            print(f"📊 document_type: {workflow.document_type}")
            print(f"🔄 workflow_type: {workflow.workflow_type}")
            
            workflow_data = workflow.to_dict()
            
            print(f"📋 Inserting workflow into approval_workflows table...")
            result = self.client.table('approval_workflows').insert(workflow_data).execute()
            
            if result.data:
                workflow_id = result.data[0]['id']
                workflow.id = workflow_id
                print(f"✅ Workflow created successfully with ID: {workflow_id}")
                
                # Create default approval steps based on workflow type
                self._create_default_steps(workflow_id, workflow.workflow_type, workflow.document_type)
                
                return workflow_id
            else:
                raise Exception("Failed to create workflow - no data returned from database")
                
        except Exception as e:
            print(f"💥 Exception in create_workflow: {str(e)}")
            import traceback
            print(f"📚 Full traceback: {traceback.format_exc()}")
            raise Exception(f"Failed to create approval workflow: {str(e)}")
    
    def _create_default_steps(self, workflow_id: str, workflow_type: str, document_type: str):
        """Create default approval steps for a workflow"""
        try:
            # Define step templates based on workflow type
            step_templates = {
                'four_eyes': [
                    {'step_name': 'Finance Manager Review', 'step_type': 'review', 'assigned_role': 'FINANCE_MANAGER', 'step_order': 1},
                    {'step_name': 'CFO Final Approval', 'step_type': 'finalize', 'assigned_role': 'CFO', 'step_order': 2}
                ],
                'three_eyes': [
                    {'step_name': 'Initial Review', 'step_type': 'review', 'assigned_role': 'FINANCE_MANAGER', 'step_order': 1},
                    {'step_name': 'Senior Review', 'step_type': 'review', 'assigned_role': 'SENIOR_MANAGER', 'step_order': 2},
                    {'step_name': 'CFO Final Approval', 'step_type': 'finalize', 'assigned_role': 'CFO', 'step_order': 3}
                ],
                'two_eyes': [
                    {'step_name': 'Manager Review', 'step_type': 'review', 'assigned_role': 'FINANCE_MANAGER', 'step_order': 1},
                    {'step_name': 'Director Approval', 'step_type': 'approve', 'assigned_role': 'DIRECTOR', 'step_order': 2}
                ]
            }
            
            steps = step_templates.get(workflow_type, step_templates['four_eyes'])
            
            for step_template in steps:
                step = ApprovalStep(
                    workflow_id=workflow_id,
                    step_name=step_template['step_name'],
                    step_type=step_template['step_type'],
                    step_order=step_template['step_order'],
                    assigned_role=step_template['assigned_role']
                )
                
                step_data = step.to_dict()
                result = self.client.table('approval_steps').insert(step_data).execute()
                
                if not result.data:
                    raise Exception(f"Failed to create approval step: {step_template['step_name']}")
            
            print(f"✅ Created {len(steps)} default approval steps for workflow {workflow_id}")
            
        except Exception as e:
            print(f"❌ Error creating default steps: {str(e)}")
            raise
    
    def get_workflow(self, workflow_id: str) -> Optional[ApprovalWorkflow]:
        """Get an approval workflow by ID"""
        try:
            result = self.client.table('approval_workflows').select('*').eq('id', workflow_id).execute()
            if result.data:
                data = result.data[0]
                return ApprovalWorkflow(
                    id=data['id'],
                    document_id=data['document_id'],
                    document_type=data['document_type'],
                    workflow_type=data['workflow_type'],
                    current_step=data.get('current_step', 1),
                    status=data['status'],
                    priority=data.get('priority', 'normal'),
                    creator_id=data['creator_id'],
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None,
                    updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')) if data.get('updated_at') else None,
                    completed_at=datetime.fromisoformat(data['completed_at'].replace('Z', '+00:00')) if data.get('completed_at') else None,
                    metadata=data.get('metadata', {})
                )
            return None
        except Exception as e:
            raise Exception(f"Error getting approval workflow: {str(e)}")
    
    def get_workflow_details(self, workflow_id: str, user_id: str, user_role: str) -> Optional[ApprovalWorkflow]:
        """Get detailed workflow information with access control"""
        try:
            # Get the workflow
            workflow_result = self.client.table('approval_workflows').select('*').eq('id', workflow_id).execute()
            
            if not workflow_result.data:
                return None
            
            workflow_data = workflow_result.data[0]
            
            # Check access permissions
            if user_role not in ['FINANCE_MANAGER', 'CFO', 'SYSTEM_ADMIN']:
                # Non-admin users can only see their own workflows
                if workflow_data['creator_id'] != user_id:
                    return None
            
            # Get workflow steps
            steps_result = self.client.table('approval_steps').select('*').eq('workflow_id', workflow_id).execute()
            
            # Create ApprovalWorkflow object
            workflow = ApprovalWorkflow(
                id=workflow_data['id'],
                document_id=workflow_data['document_id'],
                document_type=workflow_data['document_type'],
                workflow_type=workflow_data['workflow_type'],
                current_step=workflow_data['current_step'],
                status=workflow_data['status'],
                priority=workflow_data['priority'],
                creator_id=workflow_data['creator_id'],
                created_at=datetime.fromisoformat(workflow_data['created_at'].replace('Z', '+00:00')) if workflow_data.get('created_at') else None,
                updated_at=datetime.fromisoformat(workflow_data['updated_at'].replace('Z', '+00:00')) if workflow_data.get('updated_at') else None,
                completed_at=datetime.fromisoformat(workflow_data['completed_at'].replace('Z', '+00:00')) if workflow_data.get('completed_at') else None,
                metadata=workflow_data.get('metadata', {})
            )
            
            return workflow
            
        except Exception as e:
            print(f"⚠️ Error getting workflow details: {str(e)}")
            return None
    
    def process_approval(self, workflow_id: str, user_id: str, action: str, comments: str = '') -> bool:
        """Process an approval action (approve/reject)"""
        try:
            print(f"🔄 Processing approval: workflow_id={workflow_id}, user_id={user_id}, action={action}")
            
            # Get the workflow
            workflow_result = self.client.table('approval_workflows').select('*').eq('id', workflow_id).execute()
            
            if not workflow_result.data:
                print(f"❌ Workflow not found: {workflow_id}")
                return False
            
            workflow_data = workflow_result.data[0]
            
            # Get user role to find steps assigned to this role
            from services.supabase_service import supabase_service
            user_result = supabase_service.client.auth.admin.get_user_by_id(user_id)
            user_role = user_result.user.user_metadata.get('role', 'USER') if user_result.user and user_result.user.user_metadata else 'USER'
            
            # Get current step for this user's role
            steps_result = self.client.table('approval_steps').select('*').eq('workflow_id', workflow_id).eq('assigned_role', user_role).eq('status', 'pending').execute()
            
            if not steps_result.data:
                print(f"❌ No pending step found for user {user_id} in workflow {workflow_id}")
                return False
            
            current_step = steps_result.data[0]
            
            # Update the step
            step_update = {
                'status': action,
                'comments': comments,
                'completed_at': datetime.now().isoformat()
            }
            
            self.client.table('approval_steps').update(step_update).eq('id', current_step['id']).execute()
            
            # Create audit log
            audit_log = AuditLog(
                table_name='approval_steps',
                record_id=current_step['id'],
                action=f'approval_{action}',
                old_values={'status': 'pending'},
                new_values={'status': action, 'comments': comments},
                user_id=user_id
            )
            
            try:
                self.create_audit_log(audit_log)
            except Exception as e:
                print(f"⚠️ Failed to create audit log: {str(e)}")
            
            # Update workflow status
            self._update_workflow_status(workflow_id)
            
            print(f"✅ Approval processed successfully: {action}")
            return True
            
        except Exception as e:
            print(f"💥 Error processing approval: {str(e)}")
            import traceback
            print(f"📚 Full traceback: {traceback.format_exc()}")
            return False
    
    def get_user_workflows(self, user_id: str, status: str = None) -> List[ApprovalWorkflow]:
        """Get workflows for a user, optionally filtered by status"""
        try:
            query = self.client.table('approval_workflows').select('*').eq('creator_id', user_id)
            
            if status:
                query = query.eq('status', status)
            
            result = query.order('created_at', desc=True).execute()
            
            workflows = []
            for data in result.data:
                workflows.append(ApprovalWorkflow(
                    id=data['id'],
                    document_id=data['document_id'],
                    document_type=data['document_type'],
                    workflow_type=data['workflow_type'],
                    current_step=data.get('current_step', 1),
                    status=data['status'],
                    priority=data.get('priority', 'normal'),
                    creator_id=data['creator_id'],
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None,
                    updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')) if data.get('updated_at') else None,
                    completed_at=datetime.fromisoformat(data['completed_at'].replace('Z', '+00:00')) if data.get('completed_at') else None,
                    metadata=data.get('metadata', {})
                ))
            return workflows
        except Exception as e:
            raise Exception(f"Error getting user workflows: {str(e)}")
    
    def get_pending_workflows(self, user_role: str) -> List[Dict[str, Any]]:
        """Get pending workflows for a user role"""
        try:
            # Get workflows that have pending steps for this role
            result = self.client.rpc('get_pending_workflows_for_role', {'p_user_role': user_role}).execute()
            
            if result.data:
                return result.data
            return []
        except Exception as e:
            # Fallback to manual query if RPC not available
            try:
                # Get approval steps for this role that are pending
                steps_result = self.client.table('approval_steps').select('*').eq('assigned_role', user_role).eq('status', 'pending').execute()
                
                pending_workflows = []
                for step in steps_result.data:
                    # Get the full workflow
                    workflow_result = self.client.table('approval_workflows').select('*').eq('id', step['workflow_id']).execute()
                    if workflow_result.data:
                        workflow_data = workflow_result.data[0]
                        pending_workflows.append({
                            'workflow': workflow_data,
                            'current_step': step,
                            'step_order': step['step_order']
                        })
                
                return pending_workflows
            except Exception as fallback_error:
                raise Exception(f"Error getting pending workflows: {str(e)} (Fallback: {str(fallback_error)})")
    
    def approve_step(self, step_id: str, approver_id: str, approval_notes: str = "") -> bool:
        """Approve an approval step"""
        try:
            update_data = {
                'status': 'approved',
                'completed_at': datetime.now().isoformat(),
                'approver_id': approver_id,
                'approval_notes': approval_notes,
                'current_approvals': 1  # For now, single approval per step
            }
            
            result = self.client.table('approval_steps').update(update_data).eq('id', step_id).execute()
            
            if result.data:
                # Update workflow status if all steps are approved
                self._update_workflow_status(result.data[0]['workflow_id'])
                return True
            return False
        except Exception as e:
            raise Exception(f"Error approving step: {str(e)}")
    
    def reject_step(self, step_id: str, rejecter_id: str, rejection_reason: str) -> bool:
        """Reject an approval step"""
        try:
            update_data = {
                'status': 'rejected',
                'completed_at': datetime.now().isoformat(),
                'approver_id': rejecter_id,
                'rejection_reason': rejection_reason
            }
            
            result = self.client.table('approval_steps').update(update_data).eq('id', step_id).execute()
            
            if result.data:
                # Mark workflow as rejected
                self._update_workflow_status(result.data[0]['workflow_id'], 'rejected')
                return True
            return False
        except Exception as e:
            raise Exception(f"Error rejecting step: {str(e)}")
    
    def _update_workflow_status(self, workflow_id: str, status: str = None):
        """Update workflow status based on step completion"""
        try:
            # Get all steps for this workflow
            steps_result = self.client.table('approval_steps').select('*').eq('workflow_id', workflow_id).execute()
            
            if not steps_result.data:
                return
            
            steps = steps_result.data
            
            # Check if all steps are completed
            all_completed = all(step['status'] in ['approved', 'rejected', 'skipped'] for step in steps)
            any_rejected = any(step['status'] == 'rejected' for step in steps)
            
            # Determine workflow status
            if any_rejected:
                workflow_status = 'rejected'
                completed_at = datetime.now().isoformat()
            elif all_completed:
                workflow_status = 'completed'
                completed_at = datetime.now().isoformat()
            else:
                workflow_status = 'in_review'
                completed_at = None
            
            # Update workflow
            update_data = {
                'status': workflow_status,
                'updated_at': datetime.now().isoformat()
            }
            
            if completed_at:
                update_data['completed_at'] = completed_at
            
            self.client.table('approval_workflows').update(update_data).eq('id', workflow_id).execute()
            
        except Exception as e:
            print(f"⚠️ Error updating workflow status: {str(e)}")
    
    # ==================== AUDIT LOGGING ====================
    
    def create_audit_log(self, audit_log: AuditLog) -> str:
        """Create an audit log entry"""
        try:
            audit_data = audit_log.to_dict()
            result = self.client.table('audit_logs').insert(audit_data).execute()
            
            if result.data:
                return result.data[0]['id']
            raise Exception("Failed to create audit log")
        except Exception as e:
            raise Exception(f"Error creating audit log: {str(e)}")
    
    def get_audit_logs(self, table_name: str = None, record_id: str = None, limit: int = 100) -> List[AuditLog]:
        """Get audit logs with optional filters"""
        try:
            query = self.client.table('audit_logs').select('*')
            
            if table_name:
                query = query.eq('table_name', table_name)
            if record_id:
                query = query.eq('record_id', record_id)
            
            result = query.order('created_at', desc=True).limit(limit).execute()
            
            audit_logs = []
            for data in result.data:
                audit_logs.append(AuditLog(
                    id=data['id'],
                    table_name=data['table_name'],
                    record_id=data['record_id'],
                    action=data['action'],
                    old_values=data.get('old_values', {}),
                    new_values=data.get('new_values', {}),
                    user_id=data.get('user_id'),
                    ip_address=data.get('ip_address'),
                    user_agent=data.get('user_agent'),
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None
                ))
            return audit_logs
        except Exception as e:
            raise Exception(f"Error getting audit logs: {str(e)}")
    
    def get_user_statistics(self, user_id: str, user_role: str) -> Dict[str, Any]:
        """Get approval statistics for a specific user"""
        try:
            from datetime import datetime, timedelta
            
            # Get today's date
            today = datetime.now().date()
            week_ago = today - timedelta(days=7)
            
            # Get workflows where user is involved (as creator or approver)
            workflows_query = self.client.table('approval_workflows').select('*')
            
            # If user is an approver, get workflows they can approve
            if user_role in ['FINANCE_MANAGER', 'CFO', 'SYSTEM_ADMIN']:
                # Get all workflows for approvers
                workflows_result = workflows_query.execute()
            else:
                # For other users, only get their own workflows
                workflows_result = workflows_query.eq('creator_id', user_id).execute()
            
            workflows = workflows_result.data
            
            # Get approval steps for this user's role
            steps_result = self.client.table('approval_steps').select('*').eq('assigned_role', user_role).execute()
            steps = steps_result.data
            
            # Calculate statistics
            stats = {
                'pending': 0,
                'approved_today': 0,
                'rejected_today': 0,
                'completed_this_week': 0,
                'total_workflows': len(workflows),
                'my_approvals_pending': 0,
                'my_approvals_completed': 0
            }
            
            # Count workflow statuses
            for workflow in workflows:
                if workflow['status'] == 'pending':
                    stats['pending'] += 1
                elif workflow['status'] == 'completed':
                    # Check if completed this week
                    if workflow.get('completed_at'):
                        completed_date = datetime.fromisoformat(workflow['completed_at'].replace('Z', '+00:00')).date()
                        if completed_date >= week_ago:
                            stats['completed_this_week'] += 1
            
            # Count user's approval actions today
            for step in steps:
                if step.get('completed_at'):
                    completed_date = datetime.fromisoformat(step['completed_at'].replace('Z', '+00:00')).date()
                    if completed_date == today:
                        if step['status'] == 'approved':
                            stats['approved_today'] += 1
                        elif step['status'] == 'rejected':
                            stats['rejected_today'] += 1
                
                if step['status'] == 'pending':
                    stats['my_approvals_pending'] += 1
                elif step['status'] in ['approved', 'rejected']:
                    stats['my_approvals_completed'] += 1
            
            return stats
            
        except Exception as e:
            print(f"⚠️ Error getting user statistics: {str(e)}")
            # Return default statistics
            return {
                'pending': 0,
                'approved_today': 0,
                'rejected_today': 0,
                'completed_this_week': 0,
                'total_workflows': 0,
                'my_approvals_pending': 0,
                'my_approvals_completed': 0
            }
    
    # ==================== STATISTICS ====================
    
    def get_approval_statistics(self) -> Dict[str, Any]:
        """Get approval workflow statistics"""
        try:
            # Get workflow counts by status
            workflows_result = self.client.table('approval_workflows').select('status').execute()
            
            stats = {
                'pending_count': 0,
                'in_review_count': 0,
                'approved_count': 0,
                'rejected_count': 0,
                'completed_count': 0,
                'total_workflows': 0,
                'approval_rate': 0.0,
                'rejection_rate': 0.0
            }
            
            for workflow in workflows_result.data:
                status = workflow['status']
                stats['total_workflows'] += 1
                
                if status == 'pending':
                    stats['pending_count'] += 1
                elif status == 'in_review':
                    stats['in_review_count'] += 1
                elif status in ['approved', 'completed']:
                    stats['approved_count'] += 1
                    stats['completed_count'] += 1
                elif status == 'rejected':
                    stats['rejected_count'] += 1
            
            # Calculate rates
            total_processed = stats['approved_count'] + stats['rejected_count']
            if total_processed > 0:
                stats['approval_rate'] = (stats['approved_count'] / total_processed) * 100
                stats['rejection_rate'] = (stats['rejected_count'] / total_processed) * 100
            
            return stats
        except Exception as e:
            raise Exception(f"Error getting approval statistics: {str(e)}")
    
    def approve_workflow(self, workflow_id: str, user_id: str, comments: str = '') -> bool:
        """Approve a workflow (convenience method)"""
        try:
            # Get the current pending step for this workflow
            steps_result = self.client.table('approval_steps').select('*').eq('workflow_id', workflow_id).eq('status', 'pending').execute()
            
            if not steps_result.data:
                print(f"⚠️ No pending step found for workflow {workflow_id}")
                return False
            
            # Approve the first pending step
            step_id = steps_result.data[0]['id']
            return self.approve_step(step_id, user_id, comments)
        except Exception as e:
            print(f"💥 Error approving workflow: {str(e)}")
            return False
    
    def reject_workflow_step(self, workflow_id: str, user_id: str, reason: str) -> bool:
        """Reject the current step in a workflow (convenience method)"""
        try:
            # Get the current pending step for this workflow
            steps_result = self.client.table('approval_steps').select('*').eq('workflow_id', workflow_id).eq('status', 'pending').execute()
            
            if not steps_result.data:
                print(f"⚠️ No pending step found for workflow {workflow_id}")
                return False
            
            # Reject the first pending step
            step_id = steps_result.data[0]['id']
            return self.reject_step(step_id, user_id, reason)
        except Exception as e:
            print(f"💥 Error rejecting workflow: {str(e)}")
            return False
    
    def get_workflow_details(self, workflow_id: str, user_id: str, user_role: str) -> Optional[ApprovalWorkflow]:
        """Get detailed workflow information with access control"""
        try:
            workflow_result = self.client.table('approval_workflows').select('*').eq('id', workflow_id).execute()
            
            if not workflow_result.data:
                return None
            
            workflow_data = workflow_result.data[0]
            
            # Check if user has permission to view this workflow
            # Creator can always view
            if workflow_data['creator_id'] != user_id:
                # Check if user is assigned to this workflow
                steps_result = self.client.table('approval_steps').select('*').eq('workflow_id', workflow_id).execute()
                user_has_access = False
                
                for step in steps_result.data:
                    if step['assigned_role'] == user_role or user_role in ['SYSTEM_ADMIN', 'CFO']:
                        user_has_access = True
                        break
                
                if not user_has_access:
                    return None
            
            return ApprovalWorkflow(
                id=workflow_data['id'],
                document_id=workflow_data['document_id'],
                document_type=workflow_data['document_type'],
                workflow_type=workflow_data['workflow_type'],
                current_step=workflow_data.get('current_step', 1),
                status=workflow_data['status'],
                priority=workflow_data.get('priority', 'normal'),
                creator_id=workflow_data['creator_id'],
                created_at=datetime.fromisoformat(workflow_data['created_at'].replace('Z', '+00:00')) if workflow_data.get('created_at') else None,
                updated_at=datetime.fromisoformat(workflow_data['updated_at'].replace('Z', '+00:00')) if workflow_data.get('updated_at') else None,
                completed_at=datetime.fromisoformat(workflow_data['completed_at'].replace('Z', '+00:00')) if workflow_data.get('completed_at') else None,
                metadata=workflow_data.get('metadata', {})
            )
        except Exception as e:
            print(f"⚠️ Error getting workflow details: {str(e)}")
            return None
    
    def get_user_statistics(self, user_id: str, user_role: str) -> Dict[str, Any]:
        """Get statistics specific to a user's approval activities"""
        try:
            stats = {
                'my_approvals_pending': 0,
                'my_approvals_completed': 0,
                'my_approvals_rejected': 0
            }
            
            # Get steps assigned to this user's role
            steps_result = self.client.table('approval_steps').select('*').eq('assigned_role', user_role).execute()
            
            if steps_result.data:
                for step in steps_result.data:
                    if step['status'] == 'pending':
                        stats['my_approvals_pending'] += 1
                    elif step['status'] == 'approved':
                        stats['my_approvals_completed'] += 1
                    elif step['status'] == 'rejected':
                        stats['my_approvals_rejected'] += 1
            
            return stats
        except Exception as e:
            print(f"⚠️ Error getting user statistics: {str(e)}")
            return {
                'my_approvals_pending': 0,
                'my_approvals_completed': 0,
                'my_approvals_rejected': 0
            }


class TransactionApprovalModel:
    """
    Back-compat wrapper for transactional approvals.

    Prefer ``services.approval_facade.approval_facade.transactions`` in new code.
    """

    def __init__(self):
        from services.approval_facade import approval_facade

        self._impl = approval_facade.transactions

    def approve_transaction(
        self, approver_id: str, transaction_id: str, approval_reason: str = ""
    ) -> Dict[str, Any]:
        return self._impl.approve_transaction(approver_id, transaction_id, approval_reason)

    def reject_transaction(
        self, rejecter_id: str, transaction_id: str, rejection_reason: str
    ) -> Dict[str, Any]:
        return self._impl.reject_transaction(rejecter_id, transaction_id, rejection_reason)


# Global instance
approval_model = ApprovalModel()
