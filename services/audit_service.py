"""
SADPMR Financial Reporting System - Audit Trail Service
Non-destructive edit history and change tracking service
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from models.audit_models import AuditTrailModel

class AuditService:
    """Service for audit trail management and compliance tracking"""
    
    def __init__(self):
        self.audit_model = AuditTrailModel()
        self.request_context = {}  # Store request context for logging
        
    def set_request_context(self, user_id: str = 'system', ip_address: str = '127.0.0.1', 
                          user_agent: str = 'System'):
        """Set request context for audit logging"""
        self.request_context = {
            'user_id': user_id,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'request_id': f"REQ_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        }
    
    def get_client_info(self) -> Dict[str, str]:
        """Get client information from request context"""
        return {
            'ip_address': self.request_context.get('ip_address', '127.0.0.1'),
            'user_agent': self.request_context.get('user_agent', 'System'),
            'user_id': self.request_context.get('user_id', 'system')
        }
    
    def log_file_upload(self, filename: str, file_size: int, file_type: str = 'unknown', 
                    storage_path: str = '') -> Dict[str, Any]:
        """Log file upload with audit trail"""
        client_info = self.get_client_info()
        
        change_record = self.audit_model.log_file_upload(
            filename=filename,
            file_size=file_size,
            file_type=file_type,
            storage_path=storage_path,
            user_id=client_info['user_id']
        )
        
        # Add client info to the record
        change_record['ip_address'] = client_info['ip_address']
        change_record['user_agent'] = client_info['user_agent']
        
        return {
            'success': True,
            'audit_record': change_record,
            'message': f'File upload logged: {filename}'
        }
    
    def log_file_deletion(self, filename: str, file_id: str, reason: str = '') -> Dict[str, Any]:
        """Log file deletion with mandatory reason"""
        client_info = self.get_client_info()
        
        if not reason or not reason.strip():
            return {
                'success': False,
                'error': 'Reason for file deletion is required'
            }
        
        change_record = self.audit_model.log_file_deletion(
            filename=filename,
            file_id=file_id,
            user_id=client_info['user_id'],
            reason=reason.strip()
        )
        
        # Add client info to the record
        change_record['ip_address'] = client_info['ip_address']
        change_record['user_agent'] = client_info['user_agent']
        
        return {
            'success': True,
            'audit_record': change_record,
            'message': f'File deletion logged: {filename}'
        }
    
    def log_budget_creation(self, budget_id: str, budget_data: Dict, user_id: str, reason: str) -> Dict[str, Any]:
        """Log budget creation"""
        client_info = self.get_client_info()
        
        # Log budget creation
        change_record = self.audit_model.log_change(
            entity_type='budget',
            entity_id=budget_id,
            action='create',
            old_data=None,
            new_data=budget_data,
            user_id=user_id,
            reason=reason.strip()
        )
        
        # Add client info to the record
        change_record['ip_address'] = client_info['ip_address']
        change_record['user_agent'] = client_info['user_agent']
        
        return {
            'success': True,
            'audit_record': change_record,
            'message': f'Budget creation logged: {budget_id}'
        }
    
    def log_budget_revision(self, budget_id: str, revision_reason: str, 
                        old_budget: Dict, new_budget: Dict) -> Dict[str, Any]:
        """Log budget revision with mandatory reason"""
        client_info = self.get_client_info()
        
        if not revision_reason or not revision_reason.strip():
            return {
                'success': False,
                'error': 'Reason for budget revision is required'
            }
        
        change_record = self.audit_model.log_budget_change(
            budget_id=budget_id,
            action='revise',
            old_budget=old_budget,
            new_budget=new_budget,
            user_id=client_info['user_id'],
            reason=revision_reason.strip()
        )
        
        # Add client info to the record
        change_record['ip_address'] = client_info['ip_address']
        change_record['user_agent'] = client_info['user_agent']
        
        return {
            'success': True,
            'audit_record': change_record,
            'message': f'Budget revision logged: {budget_id}'
        }
    
    def log_budget_deletion(self, budget_id: str, reason: str = '') -> Dict[str, Any]:
        """Log budget deletion (soft delete) with mandatory reason"""
        client_info = self.get_client_info()
        
        if not reason or not reason.strip():
            return {
                'success': False,
                'error': 'Reason for budget deletion is required'
            }
        
        change_record = self.audit_model.log_budget_change(
            budget_id=budget_id,
            action='delete',
            old_budget={'status': 'active'},
            new_budget={'status': 'deleted', 'deleted_at': datetime.now().isoformat()},
            user_id=client_info['user_id'],
            reason=reason.strip()
        )
        
        # Add client info to the record
        change_record['ip_address'] = client_info['ip_address']
        change_record['user_agent'] = client_info['user_agent']
        
        return {
            'success': True,
            'audit_record': change_record,
            'message': f'Budget deletion logged: {budget_id}'
        }
    
    def log_balance_sheet_processing(self, file_id: str, processing_result: Dict) -> Dict[str, Any]:
        """Log balance sheet processing"""
        client_info = self.get_client_info()
        
        change_record = self.audit_model.log_balance_sheet_processing(
            file_id=file_id,
            processing_result=processing_result,
            user_id=client_info['user_id']
        )
        
        # Add client info to the record
        change_record['ip_address'] = client_info['ip_address']
        change_record['user_agent'] = client_info['user_agent']
        
        return {
            'success': True,
            'audit_record': change_record,
            'message': f'Balance sheet processing logged: {file_id}'
        }
    
    def log_financial_statement_generation(self, file_id: str, statement_type: str, 
                                       generation_result: Dict) -> Dict[str, Any]:
        """Log financial statement generation"""
        client_info = self.get_client_info()
        
        change_record = self.audit_model.log_financial_statement_generation(
            file_id=file_id,
            statement_type=statement_type,
            generation_result=generation_result,
            user_id=client_info['user_id']
        )
        
        # Add client info to the record
        change_record['ip_address'] = client_info['ip_address']
        change_record['user_agent'] = client_info['user_agent']
        
        return {
            'success': True,
            'audit_record': change_record,
            'message': f'Financial statement generation logged: {statement_type}'
        }
    
    def log_user_login(self, user_id: str, login_result: Dict, ip_address: str = None,
                   user_agent: str = None) -> Dict[str, Any]:
        """Log user login attempt"""
        # Use provided IP and user agent if available, otherwise use request context
        client_ip = ip_address or self.request_context.get('ip_address', '127.0.0.1')
        client_ua = user_agent or self.request_context.get('user_agent', 'Web Browser')
        
        change_record = self.audit_model.log_user_login(
            user_id=user_id,
            login_result=login_result,
            ip_address=client_ip,
            user_agent=client_ua
        )
        
        return {
            'success': True,
            'audit_record': change_record,
            'message': f'User login logged: {user_id}'
        }
    
    def log_user_logout(self, user_id: str, session_duration: int = 0) -> Dict[str, Any]:
        """Log user logout"""
        client_info = self.get_client_info()
        
        change_record = self.audit_model.log_user_logout(
            user_id=user_id,
            session_duration=session_duration,
            ip_address=client_info['ip_address'],
            user_agent=client_info['user_agent']
        )
        
        return {
            'success': True,
            'audit_record': change_record,
            'message': f'User logout logged: {user_id}'
        }
    
    def get_entity_history(self, entity_type: str, entity_id: str = None) -> Dict[str, Any]:
        """Get complete change history for an entity"""
        history = self.audit_model.get_entity_history(entity_type, entity_id)
        
        return {
            'success': True,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'history': history,
            'total_changes': len(history)
        }
    
    def get_user_activity(self, user_id: str, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Get all activity for a specific user"""
        activity = self.audit_model.get_user_activity(user_id, start_date, end_date)
        
        return {
            'success': True,
            'user_id': user_id,
            'activity': activity,
            'total_activities': len(activity),
            'date_range': {
                'start_date': start_date,
                'end_date': end_date
            }
        }
    
    def get_system_activity(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Get all system activity within date range"""
        activity = self.audit_model.get_system_activity(start_date, end_date)
        
        return {
            'success': True,
            'activity': activity,
            'total_activities': len(activity),
            'date_range': {
                'start_date': start_date,
                'end_date': end_date
            }
        }
    
    def get_audit_summary(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Get audit summary for reporting"""
        summary = self.audit_model.get_audit_summary(start_date, end_date)
        
        return {
            'success': True,
            'summary': summary,
            'generated_at': summary['generated_at']
        }
    
    def export_audit_report(self, start_date: str = None, end_date: str = None, 
                      format_type: str = 'json') -> Dict[str, Any]:
        """Export audit trail report"""
        report = self.audit_model.export_audit_report(start_date, end_date, format_type)
        
        return {
            'success': True,
            'report': report,
            'format': format_type,
            'message': f'Audit report exported in {format_type} format'
        }
    
    def search_audit_trail(self, query: str, entity_type: str = None, 
                        user_id: str = None, start_date: str = None, 
                        end_date: str = None) -> Dict[str, Any]:
        """Search audit trail with various filters"""
        results = self.audit_model.search_audit_trail(query, entity_type, user_id, start_date, end_date)
        
        return {
            'success': True,
            'query': query,
            'filters': {
                'entity_type': entity_type,
                'user_id': user_id,
                'start_date': start_date,
                'end_date': end_date
            },
            'results': results,
            'total_results': len(results)
        }
    
    def get_compliance_metrics(self, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Get compliance metrics for audit readiness"""
        activity = self.audit_model.get_system_activity(start_date, end_date)
        metrics = self.audit_model._calculate_compliance_metrics(activity)
        
        return {
            'success': True,
            'metrics': metrics,
            'date_range': {
                'start_date': start_date,
                'end_date': end_date
            },
            'compliance_score': metrics['compliance_score'],
            'risk_level': metrics['risk_level'],
            'recommendations': self._generate_compliance_recommendations(metrics)
        }
    
    def _generate_compliance_recommendations(self, metrics: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on compliance metrics"""
        recommendations = []
        
        score = metrics.get('compliance_score', 0)
        risk_level = metrics.get('risk_level', 'LOW')
        
        if score < 80:
            recommendations.append("Compliance score below 80% - Immediate attention required")
            recommendations.append("Implement mandatory reason fields for all auditable events")
            recommendations.append("Train staff on proper audit trail procedures")
        elif score < 95:
            recommendations.append("Compliance score below 95% - Review audit procedures")
            recommendations.append("Consider automated compliance monitoring")
        else:
            recommendations.append("Excellent compliance - Maintain current procedures")
        
        if metrics.get('events_without_reasons', 0) > 0:
            recommendations.append("Events without reasons detected - Implement mandatory reason validation")
        
        if risk_level == 'HIGH':
            recommendations.append("High risk level - Schedule immediate audit review")
        elif risk_level == 'MEDIUM':
            recommendations.append("Medium risk level - Enhance monitoring procedures")
        
        return recommendations
    
    def create_correction_entry(self, original_entity: str, original_id: str, 
                           correction_data: Dict, reason: str, 
                           user_id: str = 'system') -> Dict[str, Any]:
        """Create a correction entry for audit trail"""
        client_info = self.get_client_info()
        
        if not reason or not reason.strip():
            return {
                'success': False,
                'error': 'Reason for correction is required'
            }
        
        change_record = self.audit_model.log_change(
            entity_type=original_entity,
            entity_id=original_id,
            action='correct',
            old_data=correction_data.get('original_data'),
            new_data=correction_data.get('corrected_data'),
            user_id=user_id,
            reason=reason.strip(),
            ip_address=client_info['ip_address'],
            user_agent=client_info['user_agent']
        )
        
        return {
            'success': True,
            'audit_record': change_record,
            'message': f'Correction entry created: {original_entity} {original_id}'
        }
