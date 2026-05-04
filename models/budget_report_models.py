"""
Budget Report Database Models
Flexible models for handling any kind of budget report format
"""

import uuid
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from decimal import Decimal

from supabase import create_client, Client
from .supabase_auth_models import supabase_auth


@dataclass
class BudgetReportSession:
    """Represents a budget report upload session"""
    id: Optional[str] = None
    user_id: str = ""
    document_type: str = "budget_report"
    filename: str = ""
    original_filename: str = ""
    file_type: str = "unknown"
    file_format: str = "unknown"
    status: str = "draft"
    total_rows: int = 0
    total_columns: int = 0
    file_size_bytes: int = 0
    checksum_md5: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    metadata: Dict = None
    processing_log: List = None
    validation_results: Dict = None
    # Budget report specific fields
    total_budget: Decimal = Decimal('0.00')
    total_actual: Decimal = Decimal('0.00')
    total_variance: Decimal = Decimal('0.00')
    variance_percentage: Decimal = Decimal('0.00')
    fiscal_year: int = 0
    budget_type: str = ""
    department: str = ""
    reporting_period: str = ""
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.processing_log is None:
            self.processing_log = []
        if self.validation_results is None:
            self.validation_results = {}
    
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
        if self.processed_at:
            data['processed_at'] = self.processed_at.isoformat()
        # Convert Decimal to string for JSON serialization
        data['total_budget'] = str(self.total_budget)
        data['total_actual'] = str(self.total_actual)
        data['total_variance'] = str(self.total_variance)
        data['variance_percentage'] = str(self.variance_percentage)
        return data


@dataclass
class BudgetReportColumn:
    """Represents a column in a budget report file"""
    id: Optional[str] = None
    session_id: str = ""
    column_name: str = ""
    original_column_name: str = ""
    column_index: int = 0
    column_type: str = "custom"
    data_type: str = "text"
    format_pattern: str = ""
    mapped_to: str = ""
    mapping_confidence: float = 0.0
    is_required: bool = False
    is_key_column: bool = False
    validation_rules: Dict = None
    transformation_rules: Dict = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.validation_rules is None:
            self.validation_rules = {}
        if self.transformation_rules is None:
            self.transformation_rules = {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database operations"""
        data = asdict(self)
        # Remove id field if it's None to let database generate UUID
        if data.get('id') is None:
            del data['id']
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        return data


@dataclass
class BudgetReportDataRow:
    """Represents a data row in a budget report"""
    id: Optional[str] = None
    session_id: str = ""
    row_index: int = 0
    account_code: str = ""
    account_description: str = ""
    budget_amount: Decimal = Decimal('0.00')
    actual_amount: Decimal = Decimal('0.00')
    variance: Decimal = Decimal('0.00')
    variance_percentage: Decimal = Decimal('0.00')
    department: str = ""
    expense_category: str = ""
    period: str = ""
    is_total_row: bool = False
    is_subtotal_row: bool = False
    row_type: str = "detail"  # detail, subtotal, total
    confidence_score: float = 0.0
    validation_errors: List = None
    mapped_to_grap: str = ""
    grap_mapping_confidence: float = 0.0
    raw_data: Dict = None
    processed_data: Dict = None
    mapping_status: str = "unmapped"
    validation_status: str = "pending"
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []
        if self.raw_data is None:
            self.raw_data = {}
        if self.processed_data is None:
            self.processed_data = {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database operations"""
        data = asdict(self)
        # Remove id field if it's None to let database generate UUID
        if data.get('id') is None:
            del data['id']
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        # Convert Decimal to string for JSON serialization
        data['budget_amount'] = str(self.budget_amount)
        data['actual_amount'] = str(self.actual_amount)
        data['variance'] = str(self.variance)
        data['variance_percentage'] = str(self.variance_percentage)
        
        return data


@dataclass
class BudgetReportMappingRule:
    """Represents a mapping rule for budget report accounts"""
    id: Optional[str] = None
    pattern: str = ""
    grap_category: str = ""
    grap_code: str = ""
    description: str = ""
    confidence_threshold: float = 0.8
    is_active: bool = True
    usage_count: int = 0
    success_rate: float = 0.0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database operations"""
        data = asdict(self)
        # Remove id field if it's None to let database generate UUID
        if data.get('id') is None:
            del data['id']
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        return data


class BudgetReportModel:
    """Model for budget report database operations"""
    
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
        
        self.table_name = "budget_report_sessions"
        self.columns_table = "budget_report_columns"
        self.data_rows_table = "budget_report_data_rows"
        self.mapping_rules_table = "budget_report_mapping_rules"
    
    def create_session(self, session: BudgetReportSession) -> BudgetReportSession:
        """Create a new budget report session"""
        try:
            data = session.to_dict()
            response = self.client.table(self.table_name).insert(data).execute()
            
            if response.data:
                # Update session with generated ID
                session.id = response.data[0]['id']
                return session
            else:
                raise Exception("Failed to create session")
                
        except Exception as e:
            logger.error(f"Error creating budget report session: {str(e)}")
            raise
    
    def get_session(self, session_id: str) -> Optional[BudgetReportSession]:
        """Get a budget report session by ID"""
        try:
            response = self.client.table(self.table_name).select("*").eq("id", session_id).execute()
            
            if response.data:
                session_data = response.data[0]
                return BudgetReportSession(
                    id=session_data['id'],
                    user_id=session_data['user_id'],
                    document_type=session_data['document_type'],
                    filename=session_data['filename'],
                    original_filename=session_data['original_filename'],
                    file_type=session_data['file_type'],
                    file_format=session_data['file_format'],
                    status=session_data['status'],
                    total_rows=session_data['total_rows'],
                    total_columns=session_data['total_columns'],
                    file_size_bytes=session_data['file_size_bytes'],
                    checksum_md5=session_data['checksum_md5'],
                    created_at=datetime.fromisoformat(session_data['created_at']) if session_data['created_at'] else None,
                    updated_at=datetime.fromisoformat(session_data['updated_at']) if session_data['updated_at'] else None,
                    processed_at=datetime.fromisoformat(session_data['processed_at']) if session_data['processed_at'] else None,
                    metadata=session_data['metadata'],
                    processing_log=session_data['processing_log'],
                    validation_results=session_data['validation_results'],
                    total_budget=Decimal(session_data.get('total_budget', '0.00')),
                    total_actual=Decimal(session_data.get('total_actual', '0.00')),
                    total_variance=Decimal(session_data.get('total_variance', '0.00')),
                    variance_percentage=Decimal(session_data.get('variance_percentage', '0.00')),
                    fiscal_year=session_data.get('fiscal_year', 0),
                    budget_type=session_data.get('budget_type', ''),
                    department=session_data.get('department', ''),
                    reporting_period=session_data.get('reporting_period', '')
                )
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error getting budget report session: {str(e)}")
            return None
    
    def update_session(self, session: BudgetReportSession) -> BudgetReportSession:
        """Update a budget report session"""
        try:
            data = session.to_dict()
            response = self.client.table(self.table_name).update(data).eq("id", session.id).execute()
            
            if response.data:
                return session
            else:
                raise Exception("Failed to update session")
                
        except Exception as e:
            logger.error(f"Error updating budget report session: {str(e)}")
            raise
    
    def update_session_status(self, session_id: str, status: str, metadata: Dict = None) -> bool:
        """Update session status"""
        try:
            update_data = {'status': status, 'updated_at': datetime.now().isoformat()}
            if metadata:
                update_data['metadata'] = metadata
            
            result = self.client.table(self.table_name).update(update_data).eq('id', session_id).execute()
            return result.data is not None
        except Exception as e:
            raise Exception(f"Error updating session status: {str(e)}")
    
    def get_user_sessions(self, user_id: str, limit: int = 50) -> List[BudgetReportSession]:
        """Get all sessions for a user"""
        try:
            response = self.client.table(self.table_name).select("*").eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute()
            
            sessions = []
            for session_data in response.data:
                session = BudgetReportSession(
                    id=session_data['id'],
                    user_id=session_data['user_id'],
                    document_type=session_data['document_type'],
                    filename=session_data['filename'],
                    original_filename=session_data['original_filename'],
                    file_type=session_data['file_type'],
                    file_format=session_data['file_format'],
                    status=session_data['status'],
                    total_rows=session_data['total_rows'],
                    total_columns=session_data['total_columns'],
                    file_size_bytes=session_data['file_size_bytes'],
                    checksum_md5=session_data['checksum_md5'],
                    created_at=datetime.fromisoformat(session_data['created_at']) if session_data['created_at'] else None,
                    updated_at=datetime.fromisoformat(session_data['updated_at']) if session_data['updated_at'] else None,
                    processed_at=datetime.fromisoformat(session_data['processed_at']) if session_data['processed_at'] else None,
                    metadata=session_data['metadata'],
                    processing_log=session_data['processing_log'],
                    validation_results=session_data['validation_results'],
                    total_budget=Decimal(session_data.get('total_budget', '0.00')),
                    total_actual=Decimal(session_data.get('total_actual', '0.00')),
                    total_variance=Decimal(session_data.get('total_variance', '0.00')),
                    variance_percentage=Decimal(session_data.get('variance_percentage', '0.00')),
                    fiscal_year=session_data.get('fiscal_year', 0),
                    budget_type=session_data.get('budget_type', ''),
                    department=session_data.get('department', ''),
                    reporting_period=session_data.get('reporting_period', '')
                )
                sessions.append(session)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting user budget report sessions: {str(e)}")
            return []
    
    def get_sessions_by_status(self, status: str, limit: int = 100) -> List[BudgetReportSession]:
        """Get sessions by status"""
        try:
            response = self.client.table(self.table_name).select("*").eq("status", status).order("created_at", desc=True).limit(limit).execute()
            
            sessions = []
            for session_data in response.data:
                session = BudgetReportSession(
                    id=session_data['id'],
                    user_id=session_data['user_id'],
                    document_type=session_data['document_type'],
                    filename=session_data['filename'],
                    original_filename=session_data['original_filename'],
                    file_type=session_data['file_type'],
                    file_format=session_data['file_format'],
                    status=session_data['status'],
                    total_rows=session_data['total_rows'],
                    total_columns=session_data['total_columns'],
                    file_size_bytes=session_data['file_size_bytes'],
                    checksum_md5=session_data['checksum_md5'],
                    created_at=datetime.fromisoformat(session_data['created_at']) if session_data['created_at'] else None,
                    updated_at=datetime.fromisoformat(session_data['updated_at']) if session_data['updated_at'] else None,
                    processed_at=datetime.fromisoformat(session_data['processed_at']) if session_data['processed_at'] else None,
                    metadata=session_data['metadata'],
                    processing_log=session_data['processing_log'],
                    validation_results=session_data['validation_results'],
                    total_budget=Decimal(session_data.get('total_budget', '0.00')),
                    total_actual=Decimal(session_data.get('total_actual', '0.00')),
                    total_variance=Decimal(session_data.get('total_variance', '0.00')),
                    variance_percentage=Decimal(session_data.get('variance_percentage', '0.00')),
                    fiscal_year=session_data.get('fiscal_year', 0),
                    budget_type=session_data.get('budget_type', ''),
                    department=session_data.get('department', ''),
                    reporting_period=session_data.get('reporting_period', '')
                )
                sessions.append(session)
            
            return sessions
            
        except Exception as e:
            logger.error(f"Error getting budget report sessions by status: {str(e)}")
            return []
    
    def create_data_row(self, data_row: BudgetReportDataRow) -> BudgetReportDataRow:
        """Create a new data row"""
        try:
            data = data_row.to_dict()
            response = self.client.table(self.data_rows_table).insert(data).execute()
            
            if response.data:
                data_row.id = response.data[0]['id']
                return data_row
            else:
                raise Exception("Failed to create data row")
                
        except Exception as e:
            logger.error(f"Error creating budget report data row: {str(e)}")
            raise
    
    def get_data_rows(self, session_id: str) -> List[BudgetReportDataRow]:
        """Get all data rows for a session"""
        try:
            response = self.client.table(self.data_rows_table).select("*").eq("session_id", session_id).order("row_index").execute()
            
            data_rows = []
            for row_data in response.data:
                data_row = BudgetReportDataRow(
                    id=row_data['id'],
                    session_id=row_data['session_id'],
                    row_index=row_data['row_index'],
                    account_code=row_data['account_code'],
                    account_description=row_data['account_description'],
                    budget_amount=Decimal(row_data['budget_amount']),
                    actual_amount=Decimal(row_data['actual_amount']),
                    variance=Decimal(row_data['variance']),
                    variance_percentage=Decimal(row_data['variance_percentage']),
                    department=row_data['department'],
                    expense_category=row_data['expense_category'],
                    period=row_data['period'],
                    is_total_row=row_data['is_total_row'],
                    is_subtotal_row=row_data['is_subtotal_row'],
                    row_type=row_data['row_type'],
                    confidence_score=row_data['confidence_score'],
                    validation_errors=row_data['validation_errors'],
                    mapped_to_grap=row_data['mapped_to_grap'],
                    grap_mapping_confidence=row_data['grap_mapping_confidence'],
                    raw_data=row_data.get('raw_data', {}),
                    processed_data=row_data.get('processed_data', {}),
                    mapping_status=row_data.get('mapping_status', 'unmapped'),
                    validation_status=row_data.get('validation_status', 'pending'),
                    created_at=datetime.fromisoformat(row_data['created_at']) if row_data['created_at'] else None
                )
                data_rows.append(data_row)
            
            return data_rows
            
        except Exception as e:
            logger.error(f"Error getting budget report data rows: {str(e)}")
            return []
    
    def create_mapping_rule(self, rule: BudgetReportMappingRule) -> BudgetReportMappingRule:
        """Create a new mapping rule"""
        try:
            data = rule.to_dict()
            response = self.client.table(self.mapping_rules_table).insert(data).execute()
            
            if response.data:
                rule.id = response.data[0]['id']
                return rule
            else:
                raise Exception("Failed to create mapping rule")
                
        except Exception as e:
            logger.error(f"Error creating budget report mapping rule: {str(e)}")
            raise
    
    def get_mapping_rules(self, active_only: bool = True) -> List[BudgetReportMappingRule]:
        """Get all mapping rules"""
        try:
            query = self.client.table(self.mapping_rules_table).select("*")
            if active_only:
                query = query.eq("is_active", True)
            response = query.order("confidence_threshold", desc=True).execute()
            
            rules = []
            for rule_data in response.data:
                rule = BudgetReportMappingRule(
                    id=rule_data['id'],
                    pattern=rule_data['pattern'],
                    grap_category=rule_data['grap_category'],
                    grap_code=rule_data['grap_code'],
                    description=rule_data['description'],
                    confidence_threshold=rule_data['confidence_threshold'],
                    is_active=rule_data['is_active'],
                    usage_count=rule_data['usage_count'],
                    success_rate=rule_data['success_rate'],
                    created_at=datetime.fromisoformat(rule_data['created_at']) if rule_data['created_at'] else None,
                    updated_at=datetime.fromisoformat(rule_data['updated_at']) if rule_data['updated_at'] else None
                )
                rules.append(rule)
            
            return rules
            
        except Exception as e:
            logger.error(f"Error getting budget report mapping rules: {str(e)}")
            return []


# Create global instance
budget_report_model = BudgetReportModel()

# Import logging
import logging
logger = logging.getLogger(__name__)
