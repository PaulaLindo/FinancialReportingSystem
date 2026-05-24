"""
Varydian Financial Reporting System - Audit Trail Models
Non-destructive edit history and change tracking system
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import json
import logging
import os
import uuid as uuid_mod

AUDIT_EVENTS_TABLE = "app_audit_events"
logger = logging.getLogger(__name__)


def _json_safe(obj: Any) -> Any:
    if obj is None:
        return None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    return str(obj)


def _db_audit_row_to_record(row: Dict[str, Any]) -> Dict[str, Any]:
    payload = row.get("payload") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except Exception:
            payload = {}
    rec = {**payload} if isinstance(payload, dict) else {}
    rec["audit_id"] = row.get("audit_id") or rec.get("audit_id")
    ts = row.get("created_at")
    rec["timestamp"] = rec.get("timestamp") or ts
    if row.get("user_id") is not None and not rec.get("user_id"):
        rec["user_id"] = row.get("user_id")
    rec["_stored_id"] = row.get("id")
    return rec


def _coerce_uuid(user_id: Optional[str]) -> Optional[str]:
    if not user_id or user_id == "system":
        return None
    try:
        uuid_mod.UUID(str(user_id))
        return str(user_id)
    except Exception:
        return None
class AuditTrailModel:
    """Audit trail — in-process buffer plus durable Supabase ``app_audit_events`` when configured."""

    def __init__(self):
        self.audit_log: List[Dict[str, Any]] = []
        self.change_history: Dict[str, List] = {}
        self._svc = None
        try:
            from utils.supabase_service_client import get_service_supabase_client

            self._svc = get_service_supabase_client()
        except Exception:
            self._svc = None

    def _persist_audit_event(self, change_record: Dict[str, Any]) -> None:
        if not self._svc:
            return
        uid = _coerce_uuid(change_record.get("user_id"))
        payload = dict(change_record)
        row = {
            "audit_id": str(change_record.get("audit_id", ""))[:128],
            "entity_type": str(change_record.get("entity_type", "unknown"))[:200],
            "entity_id": str(change_record.get("entity_id", ""))[:512],
            "action": str(change_record.get("action", ""))[:100],
            "user_id": uid,
            "reason": ((change_record.get("reason") or "")[:8000]),
            "payload": _json_safe(payload),
            "ip_address": (str(change_record.get("ip_address") or "")[:128] or None),
            "user_agent": ((str(change_record.get("user_agent") or "")[:500]) or None),
        }
        try:
            self._svc.table(AUDIT_EVENTS_TABLE).insert(row).execute()
        except Exception as ex:
            logger.warning("Persist audit event failed (%s): %s", row.get("audit_id"), ex)
    def log_change(self, entity_type: str, entity_id: str, action: str, 
                  old_data: Dict = None, new_data: Dict = None, 
                  user_id: str = 'system', reason: str = '', 
                  ip_address: str = '127.0.0.1', user_agent: str = 'System',
                  creator_id: str = None, approver_id: str = None, 
                  approval_status: str = None, finalized_by: str = None) -> Dict[str, Any]:
        """Log a change in the audit trail"""
        change_record = {
            'audit_id': f"AUD_{uuid_mod.uuid4().hex[:16]}",
            'timestamp': datetime.now().isoformat(),
            'entity_type': entity_type,
            'entity_id': entity_id,
            'action': action,
            'user_id': user_id,
            'reason': reason,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'old_data': old_data,
            'new_data': new_data,
            'session_id': None,  # Can be enhanced later
            'is_reversal': action.lower().startswith('reverse'),
            'is_correction': action.lower().startswith('correct') or action.lower().startswith('update'),
            'is_deletion': action.lower().startswith('delete'),
            'is_creation': action.lower().startswith('create'),
            # Four-Eyes approval tracking
            'creator_id': creator_id,
            'approver_id': approver_id,
            'approval_status': approval_status,  # 'pending', 'approved', 'rejected', 'finalized'
            'finalized_by': finalized_by,
            'is_approval': action.lower() in ['approve', 'reject', 'finalize'],
            'is_financial_transaction': entity_type in ['transaction', 'journal_entry', 'asset_impairment', 'budget_adjustment']
        }
        
        # Add to audit log
        self.audit_log.append(change_record)
        
        # Update entity change history
        if entity_id not in self.change_history:
            self.change_history[entity_id] = []
        
        self.change_history[entity_id].append(change_record)

        self._persist_audit_event(change_record)

        return change_record
    
    def log_file_upload(self, filename: str, file_size: int, user_id: str = 'system',
                    file_type: str = 'unknown', storage_path: str = '') -> Dict[str, Any]:
        """Log file upload activity"""
        return self.log_change(
            entity_type='file',
            entity_id=filename,
            action='upload',
            old_data=None,
            new_data={
                'filename': filename,
                'file_size': file_size,
                'file_type': file_type,
                'storage_path': storage_path,
                'upload_status': 'completed'
            },
            user_id=user_id,
            reason='File uploaded to system',
            ip_address='127.0.0.1',
            user_agent='File Upload Service'
        )
    
    def log_file_deletion(self, filename: str, file_id: str, user_id: str = 'system',
                       reason: str = '') -> Dict[str, Any]:
        """Log file deletion (soft delete)"""
        return self.log_change(
            entity_type='file',
            entity_id=file_id,
            action='delete',
            old_data={'filename': filename, 'status': 'active'},
            new_data={'filename': filename, 'status': 'deleted', 'deleted_at': datetime.now().isoformat()},
            user_id=user_id,
            reason=reason or 'File deleted by user',
            ip_address='127.0.0.1',
            user_agent='File Management Service'
        )
    
    def log_budget_change(self, budget_id: str, action: str, user_id: str = 'system',
                      old_budget: Dict = None, new_budget: Dict = None,
                      reason: str = '') -> Dict[str, Any]:
        """Log budget-related changes"""
        return self.log_change(
            entity_type='budget',
            entity_id=budget_id,
            action=action,
            old_data=old_budget,
            new_data=new_budget,
            user_id=user_id,
            reason=reason or f'Budget {action} operation',
            ip_address='127.0.0.1',
            user_agent='Budget Management Service'
        )
    
    def log_balance_sheet_processing(self, file_id: str, user_id: str = 'system',
                                processing_result: Dict = None) -> Dict[str, Any]:
        """Log balance sheet processing"""
        return self.log_change(
            entity_type='balance_sheet',
            entity_id=file_id,
            action='process',
            old_data=None,
            new_data=processing_result,
            user_id=user_id,
            reason='Balance sheet processed for financial statements',
            ip_address='127.0.0.1',
            user_agent='GRAP Processing Service'
        )
    
    def log_financial_statement_generation(self, file_id: str, statement_type: str,
                                       user_id: str = 'system', 
                                       generation_result: Dict = None) -> Dict[str, Any]:
        """Log financial statement generation"""
        return self.log_change(
            entity_type='financial_statement',
            entity_id=file_id,
            action='generate',
            old_data=None,
            new_data={
                'statement_type': statement_type,
                'generation_result': generation_result,
                'generated_at': datetime.now().isoformat()
            },
            user_id=user_id,
            reason=f'Financial statement ({statement_type}) generated',
            ip_address='127.0.0.1',
            user_agent='Financial Statement Service'
        )
    
    def log_user_login(self, user_id: str, login_result: Dict, ip_address: str = '127.0.0.1',
                   user_agent: str = 'Web Browser') -> Dict[str, Any]:
        """Log user login attempts"""
        return self.log_change(
            entity_type='user_session',
            entity_id=user_id,
            action='login',
            old_data=None,
            new_data=login_result,
            user_id=user_id,
            reason='User login attempt',
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_user_logout(self, user_id: str, session_duration: int = 0,
                    ip_address: str = '127.0.0.1', user_agent: str = 'Web Browser') -> Dict[str, Any]:
        """Log user logout"""
        return self.log_change(
            entity_type='user_session',
            entity_id=user_id,
            action='logout',
            old_data=None,
            new_data={'session_duration': session_duration},
            user_id=user_id,
            reason='User logout',
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_permission_change(self, user_id: str, old_permissions: List, new_permissions: List,
                          changed_by: str = 'system', reason: str = '') -> Dict[str, Any]:
        """Log permission changes"""
        return self.log_change(
            entity_type='user_permissions',
            entity_id=user_id,
            action='permission_change',
            old_data={'permissions': old_permissions},
            new_data={'permissions': new_permissions, 'changed_by': changed_by},
            user_id=changed_by,
            reason=reason or 'User permissions updated',
            ip_address='127.0.0.1',
            user_agent='User Management Service'
        )
    
    def get_entity_history(self, entity_type: str, entity_id: str = None) -> List[Dict[str, Any]]:
        """Complete change history for an entity."""
        if self._svc:
            try:
                q = self._svc.table(AUDIT_EVENTS_TABLE).select("*").eq("entity_type", entity_type)
                if entity_id:
                    q = q.eq("entity_id", str(entity_id))
                res = q.order("created_at", desc=False).limit(5000).execute()
                return [_db_audit_row_to_record(r) for r in (res.data or [])]
            except Exception as ex:
                logger.warning("Audit DB read entity_history failed: %s", ex)
        if entity_id:
            return [
                r
                for r in self.audit_log
                if r["entity_type"] == entity_type and r["entity_id"] == entity_id
            ]
        return [r for r in self.audit_log if r["entity_type"] == entity_type]

    def get_user_activity(self, user_id: str, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """All activity attributed to ``user_id``."""
        uuid_filter = _coerce_uuid(user_id)
        if self._svc and uuid_filter:
            try:
                q = self._svc.table(AUDIT_EVENTS_TABLE).select("*").eq("user_id", uuid_filter)
                res = q.order("created_at", desc=True).limit(5000).execute()
                rows = [_db_audit_row_to_record(r) for r in (res.data or [])]
                if start_date:
                    rows = [r for r in rows if (r.get("timestamp") or "") >= start_date]
                if end_date:
                    rows = [r for r in rows if (r.get("timestamp") or "") <= end_date]
                return rows
            except Exception as ex:
                logger.warning("Audit DB read user_activity failed: %s", ex)
        user_activity = [record for record in self.audit_log if record["user_id"] == user_id]
        if start_date:
            user_activity = [record for record in user_activity if record["timestamp"] >= start_date]
        if end_date:
            user_activity = [record for record in user_activity if record["timestamp"] <= end_date]
        return user_activity

    def get_system_activity(self, start_date: str = None, end_date: str = None) -> List[Dict[str, Any]]:
        """System-wide activity."""
        if self._svc:
            try:
                q = self._svc.table(AUDIT_EVENTS_TABLE).select("*")
                # PostgREST filter by ISO string when provided
                if start_date:
                    q = q.gte("created_at", start_date)
                if end_date:
                    q = q.lte("created_at", end_date)
                res = q.order("created_at", desc=True).limit(10000).execute()
                return [_db_audit_row_to_record(r) for r in (res.data or [])]
            except Exception as ex:
                logger.warning("Audit DB read system_activity failed: %s", ex)
        system_activity = list(self.audit_log)
        if start_date:
            system_activity = [r for r in system_activity if r["timestamp"] >= start_date]
        if end_date:
            system_activity = [r for r in system_activity if r["timestamp"] <= end_date]
        return system_activity
    def get_audit_summary(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Get audit summary for reporting"""
        filtered_logs = self.get_system_activity(start_date, end_date)
        
        summary = {
            'summary_id': f"AUD_SUM_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'generated_at': datetime.now().isoformat(),
            'date_range': {
                'start_date': start_date,
                'end_date': end_date
            },
            'total_activities': len(filtered_logs),
            'activities_by_type': {},
            'activities_by_user': {},
            'activities_by_action': {},
            'login_attempts': 0,
            'failed_logins': 0,
            'file_operations': 0,
            'budget_operations': 0,
            'financial_statement_operations': 0
        }
        
        # Categorize activities
        for record in filtered_logs:
            entity_type = record['entity_type']
            action = record['action']
            user_id = record['user_id']
            
            # Count by entity type
            if entity_type not in summary['activities_by_type']:
                summary['activities_by_type'][entity_type] = 0
            summary['activities_by_type'][entity_type] += 1
            
            # Count by user
            if user_id not in summary['activities_by_user']:
                summary['activities_by_user'][user_id] = 0
            summary['activities_by_user'][user_id] += 1
            
            # Count by action
            if action not in summary['activities_by_action']:
                summary['activities_by_action'][action] = 0
            summary['activities_by_action'][action] += 1
            
            # Specific counters
            if entity_type == 'user_session':
                if action == 'login':
                    summary['login_attempts'] += 1
                    if record.get('new_data', {}).get('success', False):
                        summary['failed_logins'] += 1
            elif entity_type == 'file':
                summary['file_operations'] += 1
            elif entity_type == 'budget':
                summary['budget_operations'] += 1
            elif entity_type == 'financial_statement':
                summary['financial_statement_operations'] += 1
        
        return summary
    
    def export_audit_report(self, start_date: str = None, end_date: str = None, 
                      format_type: str = 'json') -> Dict[str, Any]:
        """Export audit trail report"""
        filtered_logs = self.get_system_activity(start_date, end_date)
        summary = self.get_audit_summary(start_date, end_date)
        
        report = {
            'report_id': f"AUD_RPT_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            'generated_at': datetime.now().isoformat(),
            'date_range': {
                'start_date': start_date,
                'end_date': end_date
            },
            'summary': summary,
            'detailed_logs': filtered_logs,
            'compliance_metrics': self._calculate_compliance_metrics(filtered_logs)
        }
        
        return report
    
    def _calculate_compliance_metrics(self, logs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate audit compliance metrics"""
        total_logs = len(logs)
        
        metrics = {
            'total_auditable_events': 0,
            'events_with_reasons': 0,
            'events_without_reasons': 0,
            'reversal_events': 0,
            'correction_events': 0,
            'deletion_events': 0,
            'compliance_score': 0.0,
            'risk_level': 'LOW'
        }
        
        for log in logs:
            if log['is_correction'] or log['is_reversal'] or log['is_deletion']:
                metrics['total_auditable_events'] += 1
                
                if log['reason'] and log['reason'].strip():
                    metrics['events_with_reasons'] += 1
                else:
                    metrics['events_without_reasons'] += 1
                
                if log['is_reversal']:
                    metrics['reversal_events'] += 1
                if log['is_correction']:
                    metrics['correction_events'] += 1
                if log['is_deletion']:
                    metrics['deletion_events'] += 1
        
        # Calculate compliance score
        if metrics['total_auditable_events'] > 0:
            reason_compliance = (metrics['events_with_reasons'] / metrics['total_auditable_events']) * 100
            metrics['compliance_score'] = round(reason_compliance, 2)
            
            # Determine risk level
            if metrics['compliance_score'] >= 95:
                metrics['risk_level'] = 'LOW'
            elif metrics['compliance_score'] >= 80:
                metrics['risk_level'] = 'MEDIUM'
            else:
                metrics['risk_level'] = 'HIGH'
        
        return metrics
    
    def log_transaction_creation(self, transaction_id: str, creator_id: str, 
                           transaction_data: Dict, reason: str) -> Dict[str, Any]:
        """Log transaction creation with Four-Eyes tracking"""
        return self.log_change(
            entity_type='transaction',
            entity_id=transaction_id,
            action='create',
            old_data=None,
            new_data={
                'creator_id': creator_id,
                'transaction_data': transaction_data,
                'status': 'pending_approval',
                'reason': reason
            },
            user_id=creator_id,
            reason=f'Transaction created: {reason}',
            creator_id=creator_id,
            approval_status='pending'
        )
    
    def log_transaction_approval(self, transaction_id: str, approver_id: str, 
                          approval_data: Dict) -> Dict[str, Any]:
        """Log transaction approval"""
        return self.log_change(
            entity_type='transaction_approval',
            entity_id=transaction_id,
            action='approve',
            old_data={'status': 'pending_approval'},
            new_data={
                'approver_id': approver_id,
                'approval_data': approval_data,
                'status': 'approved'
            },
            user_id=approver_id,
            reason=f'Transaction approved by {approver_id}',
            approver_id=approver_id,
            approval_status='approved'
        )
    
    def log_transaction_rejection(self, transaction_id: str, rejecter_id: str,
                          rejection_data: Dict) -> Dict[str, Any]:
        """Log transaction rejection"""
        rd = rejection_data or {}
        reason_detail = rd.get('reason') or rd.get('summary') or ''
        audit_reason = f"Transaction rejected: {reason_detail[:500]}" if reason_detail else f'Transaction rejected by {rejecter_id}'
        return self.log_change(
            entity_type='transaction_approval',
            entity_id=transaction_id,
            action='reject',
            old_data={'status': 'pending_approval'},
            new_data={
                'rejecter_id': rejecter_id,
                'rejection_data': rejection_data,
                'status': 'rejected'
            },
            user_id=rejecter_id,
            reason=audit_reason,
            approver_id=rejecter_id,
            approval_status='rejected'
        )

        """Log transaction finalization"""
        return self.log_change(
            entity_type='transaction',
            entity_id=transaction_id,
            action='finalize',
            old_data={'status': 'approved'},
            new_data={
                'finalizer_id': finalizer_id,
                'status': 'finalized',
                'finalized_at': datetime.now().isoformat()
            },
            user_id=finalizer_id,
            reason=f'Transaction finalized by {finalizer_id}',
            finalized_by=finalizer_id,
            approval_status='finalized'
        )
    
    def get_approval_chain(self, transaction_id: str) -> List[Dict[str, Any]]:
        """Approval-related events for a logical transaction identifier."""
        if self._svc:
            try:
                q = (
                    self._svc.table(AUDIT_EVENTS_TABLE)
                    .select("*")
                    .eq("entity_id", transaction_id)
                    .in_("entity_type", ["transaction", "transaction_approval"])
                    .order("created_at")
                    .limit(2000)
                )
                res = q.execute()
                chain = [_db_audit_row_to_record(r) for r in (res.data or [])]
                chain.sort(key=lambda x: x.get("timestamp") or "")
                return chain
            except Exception as ex:
                logger.warning("Audit DB approval chain failed: %s", ex)
        chain_logs = []
        for log in self.audit_log:
            if log["entity_id"] == transaction_id and log["entity_type"] in ["transaction", "transaction_approval"]:
                chain_logs.append(log)
        chain_logs.sort(key=lambda x: x["timestamp"])
        return chain_logs

    def get_four_eyes_compliance_report(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Generate Four-Eyes compliance report"""
        source = (
            self.get_system_activity(start_date, end_date)
            if self._svc
            else list(self.audit_log)
        )
        if start_date:
            source = [l for l in source if (l.get("timestamp") or "") >= start_date]
        if end_date:
            source = [l for l in source if (l.get("timestamp") or "") <= end_date]

        if not source:
            raise ValueError(
                "No audit data available. Cannot generate compliance report without transaction history."
            )

        financial_transactions = []
        for log in source:
            ts = log.get("timestamp") or ""
            if log.get("is_financial_transaction") or log.get("entity_type") == "transaction_approval":
                if start_date and ts < start_date:
                    continue
                if end_date and ts > end_date:
                    continue
                financial_transactions.append(log)

        # Check if we have any financial transactions
        if not financial_transactions:
            raise ValueError("No financial transactions found in audit trail. Cannot generate compliance report without transaction data.")
        
        # Analyze compliance
        compliance_report = {
            'total_financial_transactions': 0,
            'proper_segregation': 0,
            'violations': [],
            'approval_chains': {},
            'compliance_rate': 0.0,
            'risk_level': 'LOW'
        }
        
        # Group by transaction ID
        transaction_groups = {}
        for log in financial_transactions:
            tx_id = log['entity_id']
            if tx_id not in transaction_groups:
                transaction_groups[tx_id] = []
            transaction_groups[tx_id].append(log)
        
        compliance_report['total_financial_transactions'] = len(transaction_groups)
        
        # Analyze each transaction
        for tx_id, logs in transaction_groups.items():
            creator_id = None
            approvers = set()
            finalizer_id = None
            has_creation = False
            has_approval = False
            has_finalization = False
            
            for log in logs:
                if log['action'] == 'create':
                    creator_id = log.get('creator_id') or log['user_id']
                    has_creation = True
                elif log['action'] == 'approve':
                    approvers.add(log.get('approver_id') or log['user_id'])
                    has_approval = True
                elif log['action'] == 'finalize':
                    finalizer_id = log.get('finalized_by') or log['user_id']
                    has_finalization = True
            
            # Check for segregation violations
            violations = []
            if creator_id in approvers:
                violations.append('Creator approved own transaction')
            if creator_id == finalizer_id:
                violations.append('Creator finalized own transaction')
            if approvers and finalizer_id in approvers:
                violations.append('Approver also finalized transaction')
            
            compliance_report['approval_chains'][tx_id] = {
                'creator_id': creator_id,
                'approvers': list(approvers),
                'finalizer_id': finalizer_id,
                'violations': violations,
                'compliant': len(violations) == 0
            }
            
            if len(violations) == 0 and has_creation and (has_approval or has_finalization):
                compliance_report['proper_segregation'] += 1
            elif violations:
                compliance_report['violations'].extend([f"{tx_id}: {v}" for v in violations])
        
        # Calculate compliance rate
        if compliance_report['total_financial_transactions'] > 0:
            compliance_report['compliance_rate'] = (
                compliance_report['proper_segregation'] / compliance_report['total_financial_transactions']
            ) * 100
        
        # Determine risk level
        if compliance_report['compliance_rate'] >= 95:
            compliance_report['risk_level'] = 'LOW'
        elif compliance_report['compliance_rate'] >= 80:
            compliance_report['risk_level'] = 'MEDIUM'
        else:
            compliance_report['risk_level'] = 'HIGH'
        
        return compliance_report

    def search_audit_trail(self, query: str, entity_type: str = None, 
                        user_id: str = None, start_date: str = None, 
                        end_date: str = None) -> List[Dict[str, Any]]:
        """Search audit trail with various filters"""
        filtered_logs = self.get_system_activity(start_date, end_date)
        
        # Apply filters
        if entity_type:
            filtered_logs = [log for log in filtered_logs if log['entity_type'] == entity_type]
        
        if user_id:
            filtered_logs = [log for log in filtered_logs if log['user_id'] == user_id]
        
        if query:
            query_lower = query.lower()
            filtered_logs = [
                log for log in filtered_logs
                if query_lower in (log.get('entity_type') or '').lower()
                or query_lower in (log.get('entity_id') or '').lower()
                or query_lower in (log.get('action') or '').lower()
                or query_lower in (log.get('reason') or '').lower()
                or (log.get('old_data') and query_lower in str(log['old_data']).lower())
                or (log.get('new_data') and query_lower in str(log['new_data']).lower())
            ]
        
        return filtered_logs


class SupabaseAuditTrailModel:
    """Supabase-based audit trail model for tracking all system changes"""
    
    def __init__(self):
        """Initialize Supabase client"""
        from utils.supabase_client import get_supabase_secret_key

        self.supabase_url = os.environ.get('SUPABASE_URL')
        self.supabase_key = get_supabase_secret_key()

        if not self.supabase_url or not self.supabase_key:
            raise ValueError(
                "Supabase credentials not found. Set SUPABASE_URL and "
                "SUPABASE_SECRET_KEY (service role JWT)."
            )
        
        from supabase import create_client
        self.client = create_client(self.supabase_url, self.supabase_key)
    
    def get_approval_chain(self, transaction_id: str) -> List[Dict[str, Any]]:
        """Get complete approval chain for a transaction from Supabase"""
        try:
            # Query approval_actions table for this transaction
            result = self.client.table('approval_actions').select('*').eq('transaction_id', transaction_id).order('created_at', asc=True).execute()
            
            if result.data:
                # Transform Supabase data to expected format
                chain = []
                for action in result.data:
                    chain_item = {
                        'audit_id': action.get('id', ''),
                        'timestamp': action.get('created_at', ''),
                        'entity_type': 'transaction_approval',
                        'entity_id': action.get('transaction_id', ''),
                        'action': action.get('action_type', ''),
                        'user_id': action.get('user_id', ''),
                        'user_name': self._get_user_name(action.get('user_id', '')),
                        'reason': action.get('reason', ''),
                        'ip_address': action.get('ip_address', ''),
                        'user_agent': action.get('user_agent', ''),
                        'old_data': action.get('action_data', {}),
                        'new_data': action.get('action_data', {}),
                        'session_id': None,
                        'is_reversal': action.get('action_type', '').lower().startswith('reverse'),
                        'is_correction': action.get('action_type', '').lower().startswith('correct') or action.get('action_type', '').lower().startswith('update'),
                        'is_deletion': action.get('action_type', '').lower().startswith('delete'),
                        'is_creation': action.get('action_type', '').lower().startswith('create'),
                        'creator_id': action.get('user_id', ''),
                        'approver_id': action.get('user_id', '') if action.get('action_type') in ['approve', 'reject', 'finalize'] else None,
                        'approval_status': self._get_approval_status_from_action(action.get('action_type', '')),
                        'finalized_by': action.get('user_id', '') if action.get('action_type') == 'finalize' else None,
                        'is_approval': action.get('action_type', '').lower() in ['approve', 'reject', 'finalize'],
                        'is_financial_transaction': True,
                        'user_role': action.get('user_role', '')
                    }
                    chain.append(chain_item)
                
                return chain
            else:
                return []
                
        except Exception as e:
            print(f"Error getting approval chain from Supabase: {e}")
            return []
    
    def _get_user_name(self, user_id: str) -> str:
        """Get user name from ID"""
        try:
            try:
                from models.supabase_auth_models import supabase_auth
            except ImportError:
                supabase_auth = None
            user_data = supabase_auth.get_user_by_id(user_id)
            return user_data['full_name'] if user_data else f"User {user_id}"
        except:
            return f"User {user_id}"
    
    def _get_approval_status_from_action(self, action_type: str) -> str:
        """Map action type to approval status"""
        status_mapping = {
            'create': 'pending',
            'approve': 'approved',
            'reject': 'rejected',
            'finalize': 'finalized'
        }
        return status_mapping.get(action_type.lower(), 'pending')
    
    def log_approval_action(self, transaction_id: str, action_type: str, user_id: str,
                          user_role: str, action_data: Dict = None, reason: str = '',
                          ip_address: str = '127.0.0.1', user_agent: str = 'Web Browser'):
        """Log approval action to Supabase"""
        try:
            action_record = {
                'transaction_id': transaction_id,
                'action_type': action_type,
                'user_id': user_id,
                'user_role': user_role,
                'action_data': action_data or {},
                'reason': reason,
                'ip_address': ip_address,
                'user_agent': user_agent,
                'created_at': datetime.now().isoformat()
            }
            
            result = self.client.table('approval_actions').insert(action_record).execute()
            return result.data if result.data else None
            
        except Exception as e:
            print(f"Error logging approval action to Supabase: {e}")
            return None
