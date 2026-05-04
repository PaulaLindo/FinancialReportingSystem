"""
BalanceSheet Database Models
Flexible models for handling any kind of balance sheet format
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
class BalanceSheetSession:
    """Represents a balance sheet upload session"""
    id: Optional[str] = None
    user_id: str = ""
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
        return data


@dataclass
class BalanceSheetColumn:
    """Represents a column in a balance sheet file"""
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
class BalanceSheetDataRow:
    """Represents a single row of balance sheet data"""
    id: Optional[str] = None
    session_id: str = ""
    row_index: int = 0
    raw_data: Dict = None
    processed_data: Dict = None
    account_code: str = ""
    account_description: str = ""
    account_number: str = ""
    debit_balance: Optional[Decimal] = None
    credit_balance: Optional[Decimal] = None
    net_balance: Optional[Decimal] = None
    
    # Multi-period support
    period_1: Optional[Decimal] = None
    period_2: Optional[Decimal] = None
    period_3: Optional[Decimal] = None
    period_4: Optional[Decimal] = None
    period_5: Optional[Decimal] = None
    period_6: Optional[Decimal] = None
    period_7: Optional[Decimal] = None
    period_8: Optional[Decimal] = None
    period_9: Optional[Decimal] = None
    period_10: Optional[Decimal] = None
    period_11: Optional[Decimal] = None
    period_12: Optional[Decimal] = None
    
    # GRAP mapping
    grap_category: str = ""
    grap_account: str = ""
    grap_subcategory: str = ""
    
    # Mapping and validation
    mapping_status: str = "unmapped"
    mapping_confidence: float = 0.0
    last_mapped_by: str = ""
    last_mapped_at: Optional[datetime] = None
    validation_status: str = "pending"
    validation_errors: List = None
    data_quality_score: float = 0.0
    
    # Metadata
    row_type: str = "data"
    is_active: bool = True
    notes: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.raw_data is None:
            self.raw_data = {}
        if self.processed_data is None:
            self.processed_data = {}
        if self.validation_errors is None:
            self.validation_errors = []
        
        # Validate session_id
        if not self.session_id or self.session_id == "":
            raise ValueError(f"BalanceSheetDataRow: session_id cannot be empty. Got: '{self.session_id}'")
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database operations"""
        data = asdict(self)
        # Remove id field if it's None to let database generate UUID
        if data.get('id') is None:
            del data['id']
        
        # Convert Decimal objects to strings for JSON serialization
        for field in ['debit_balance', 'credit_balance', 'net_balance'] + \
                    [f'period_{i}' for i in range(1, 13)]:
            if getattr(self, field) is not None:
                data[field] = str(getattr(self, field))
            else:
                data[field] = None
        
        # Convert datetime objects
        if self.last_mapped_at:
            data['last_mapped_at'] = self.last_mapped_at.isoformat()
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        
        # Convert empty strings to None for UUID fields
        uuid_fields = ['last_mapped_by']
        for field in uuid_fields:
            if data.get(field) == '':
                data[field] = None
        
        return data


@dataclass
class MappingRule:
    """Represents a mapping rule for auto-categorization"""
    id: Optional[str] = None
    user_id: str = ""
    rule_name: str = ""
    rule_type: str = "account_mapping"
    pattern_type: str = "contains"
    input_pattern: str = ""
    output_value: str = ""
    context: Dict = None
    conditions: Dict = None
    confidence_score: float = 0.0
    usage_count: int = 0
    success_rate: float = 0.0
    is_active: bool = True
    is_system_rule: bool = False
    priority: int = 50
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}
        if self.conditions is None:
            self.conditions = {}
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database operations"""
        data = asdict(self)
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        if self.last_used_at:
            data['last_used_at'] = self.last_used_at.isoformat()
        return data


@dataclass
class GRAPChartOfAccounts:
    """GRAP Chart of Accounts master data"""
    id: Optional[str] = None
    grap_category: str = ""
    grap_subcategory: str = ""
    grap_account: str = ""
    grap_account_code: str = ""
    account_description: str = ""
    account_type: str = ""
    normal_balance: str = ""
    keywords: List = None
    alternative_names: List = None
    mapping_patterns: List = None
    is_active: bool = True
    is_custom: bool = False
    created_by: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []
        if self.alternative_names is None:
            self.alternative_names = []
        if self.mapping_patterns is None:
            self.mapping_patterns = []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for database operations"""
        data = asdict(self)
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        return data


class BalanceSheetModel:
    """Flexible balance sheet database model"""
    
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
    
    # ==================== SESSION MANAGEMENT ====================
    
    def create_session(self, session: BalanceSheetSession) -> str:
        """Create a new balance sheet session"""
        try:
            print(f"💾 BalanceSheetModel.create_session called")
            print(f"👤 user_id: {session.user_id}")
            print(f"📄 filename: {session.filename}")
            print(f"📊 status: {session.status}")
            
            session_data = {
                'user_id': session.user_id,
                'filename': session.filename,
                'original_filename': session.original_filename,
                'file_type': session.file_type,
                'file_format': session.file_format,
                'status': session.status,
                'total_rows': session.total_rows,
                'total_columns': session.total_columns,
                'file_size_bytes': session.file_size_bytes,
                'checksum_md5': session.checksum_md5,
                'metadata': session.metadata or {},
                'processing_log': session.processing_log or [],
                'validation_results': session.validation_results or {}
            }
            
            print(f"📋 Inserting session data into balance_sheet_sessions table...")
            result = self.client.table('balance_sheet_sessions').insert(session_data).execute()
            
            print(f"📊 Database result: {result}")
            print(f"📊 Result data: {result.data}")
            
            if result.data:
                session_id = result.data[0]['id']
                session.id = session_id
                print(f"✅ Session created successfully with ID: {session_id}")
                return session_id
            else:
                print(f"❌ No data returned from database insert")
                print(f"❌ Database error: {result}")
                raise Exception("Failed to create session - no data returned from database")
                
        except Exception as e:
            print(f"💥 Exception in create_session: {str(e)}")
            import traceback
            print(f"📚 Full traceback: {traceback.format_exc()}")
            raise Exception(f"Failed to create balance sheet session: {str(e)}")
    
    def get_session(self, session_id: str) -> Optional[BalanceSheetSession]:
        """Get a balance sheet session by ID"""
        try:
            result = self.client.table('balance_sheet_sessions').select('*').eq('id', session_id).execute()
            if result.data:
                data = result.data[0]
                return BalanceSheetSession(
                    id=data['id'],
                    user_id=data['user_id'],
                    filename=data['filename'],
                    original_filename=data.get('original_filename', ''),
                    file_type=data.get('file_type', 'unknown'),
                    file_format=data.get('file_format', 'unknown'),
                    status=data.get('status', 'uploaded'),
                    total_rows=data.get('total_rows', 0),
                    total_columns=data.get('total_columns', 0),
                    file_size_bytes=data.get('file_size_bytes', 0),
                    checksum_md5=data.get('checksum_md5', ''),
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None,
                    updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')) if data.get('updated_at') else None,
                    processed_at=datetime.fromisoformat(data['processed_at'].replace('Z', '+00:00')) if data.get('processed_at') else None,
                    metadata=data.get('metadata', {}),
                    processing_log=data.get('processing_log', []),
                    validation_results=data.get('validation_results', {})
                )
            return None
        except Exception as e:
            raise Exception(f"Error getting balance sheet session: {str(e)}")
    
    def update_session_status(self, session_id: str, status: str, metadata: Dict = None) -> bool:
        """Update session status"""
        try:
            update_data = {'status': status, 'updated_at': datetime.now().isoformat()}
            if metadata:
                update_data['metadata'] = metadata
            
            result = self.client.table('balance_sheet_sessions').update(update_data).eq('id', session_id).execute()
            return result.data is not None
        except Exception as e:
            raise Exception(f"Error updating session status: {str(e)}")
    
    def get_user_sessions(self, user_id: str, limit: int = 50) -> List[BalanceSheetSession]:
        """Get all sessions for a user"""
        try:
            result = self.client.table('balance_sheet_sessions').select('*').eq('user_id', user_id).order('created_at', desc=True).limit(limit).execute()
            sessions = []
            for data in result.data:
                sessions.append(BalanceSheetSession(
                    id=data['id'],
                    user_id=data['user_id'],
                    filename=data['filename'],
                    original_filename=data.get('original_filename', ''),
                    file_type=data.get('file_type', 'unknown'),
                    file_format=data.get('file_format', 'unknown'),
                    status=data.get('status', 'uploaded'),
                    total_rows=data.get('total_rows', 0),
                    total_columns=data.get('total_columns', 0),
                    file_size_bytes=data.get('file_size_bytes', 0),
                    checksum_md5=data.get('checksum_md5', ''),
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None,
                    updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')) if data.get('updated_at') else None,
                    processed_at=datetime.fromisoformat(data['processed_at'].replace('Z', '+00:00')) if data.get('processed_at') else None,
                    metadata=data.get('metadata', {}),
                    processing_log=data.get('processing_log', []),
                    validation_results=data.get('validation_results', {})
                ))
            return sessions
        except Exception as e:
            raise Exception(f"Error getting user sessions: {str(e)}")
    
    def get_sessions_by_status(self, status: str, limit: int = 50) -> List[BalanceSheetSession]:
        """Get sessions by status"""
        try:
            result = self.client.table('balance_sheet_sessions').select('*').eq('status', status).order('created_at', desc=True).limit(limit).execute()
            
            sessions = []
            for data in result.data:
                sessions.append(BalanceSheetSession(
                    id=data['id'],
                    user_id=data['user_id'],
                    filename=data['filename'],
                    original_filename=data.get('original_filename', ''),
                    file_type=data.get('file_type', 'unknown'),
                    file_format=data.get('file_format', 'unknown'),
                    status=data['status'],
                    total_rows=data.get('total_rows', 0),
                    total_columns=data.get('total_columns', 0),
                    file_size_bytes=data.get('file_size_bytes', 0),
                    checksum_md5=data.get('checksum_md5', ''),
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None,
                    updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')) if data.get('updated_at') else None,
                    processed_at=datetime.fromisoformat(data['processed_at'].replace('Z', '+00:00')) if data.get('processed_at') else None,
                    metadata=data.get('metadata', {}),
                    processing_log=data.get('processing_log', []),
                    validation_results=data.get('validation_results', {})
                ))
            return sessions
        except Exception as e:
            raise Exception(f"Error getting sessions by status: {str(e)}")
    
    # ==================== COLUMN MANAGEMENT ====================
    
    def create_columns(self, columns: List[BalanceSheetColumn]) -> bool:
        """Create column definitions for a session"""
        try:
            data = [col.to_dict() for col in columns]
            result = self.client.table('balance_sheet_columns').insert(data).execute()
            return result.data is not None
        except Exception as e:
            raise Exception(f"Error creating columns: {str(e)}")
    
    def get_session_columns(self, session_id: str) -> List[BalanceSheetColumn]:
        """Get all columns for a session"""
        try:
            result = self.client.table('balance_sheet_columns').select('*').eq('session_id', session_id).order('column_index').execute()
            columns = []
            for data in result.data:
                columns.append(BalanceSheetColumn(
                    id=data['id'],
                    session_id=data['session_id'],
                    column_name=data['column_name'],
                    original_column_name=data.get('original_column_name', ''),
                    column_index=data['column_index'],
                    column_type=data.get('column_type', 'custom'),
                    data_type=data.get('data_type', 'text'),
                    format_pattern=data.get('format_pattern', ''),
                    mapped_to=data.get('mapped_to', ''),
                    mapping_confidence=data.get('mapping_confidence', 0.0),
                    is_required=data.get('is_required', False),
                    is_key_column=data.get('is_key_column', False),
                    validation_rules=data.get('validation_rules', {}),
                    transformation_rules=data.get('transformation_rules', {}),
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None
                ))
            return columns
        except Exception as e:
            raise Exception(f"Error getting session columns: {str(e)}")
    
    def update_column_mapping(self, column_id: str, mapped_to: str, confidence: float = 0.0) -> bool:
        """Update column mapping"""
        try:
            update_data = {
                'mapped_to': mapped_to,
                'mapping_confidence': confidence,
                'updated_at': datetime.now().isoformat()
            }
            result = self.client.table('balance_sheet_columns').update(update_data).eq('id', column_id).execute()
            return result.data is not None
        except Exception as e:
            raise Exception(f"Error updating column mapping: {str(e)}")
    
    # ==================== DATA MANAGEMENT ====================
    
    def create_data_rows(self, rows: List[BalanceSheetDataRow]) -> bool:
        """Create balance sheet data rows"""
        try:
            data = [row.to_dict() for row in rows]
            result = self.client.table('balance_sheet_data').insert(data).execute()
            return result.data is not None
        except Exception as e:
            raise Exception(f"Error creating data rows: {str(e)}")
    
    def get_session_data(self, session_id: str, limit: int = 1000, offset: int = 0) -> List[BalanceSheetDataRow]:
        """Get balance sheet data for a session"""
        try:
            result = self.client.table('balance_sheet_data').select('*').eq('session_id', session_id).eq('is_active', True).order('row_index').range(offset, offset + limit - 1).execute()
            rows = []
            for data in result.data:
                rows.append(BalanceSheetDataRow(
                    id=data['id'],
                    session_id=data['session_id'],
                    row_index=data['row_index'],
                    raw_data=data.get('raw_data', {}),
                    processed_data=data.get('processed_data', {}),
                    account_code=data.get('account_code', ''),
                    account_description=data.get('account_description', ''),
                    account_number=data.get('account_number', ''),
                    debit_balance=Decimal(data['debit_balance']) if data.get('debit_balance') else None,
                    credit_balance=Decimal(data['credit_balance']) if data.get('credit_balance') else None,
                    net_balance=Decimal(data['net_balance']) if data.get('net_balance') else None,
                    # Multi-period fields
                    **{f'period_{i}': Decimal(data[f'period_{i}']) if data.get(f'period_{i}') else None for i in range(1, 13)},
                    # GRAP mapping
                    grap_category=data.get('grap_category', ''),
                    grap_account=data.get('grap_account', ''),
                    grap_subcategory=data.get('grap_subcategory', ''),
                    # Mapping and validation
                    mapping_status=data.get('mapping_status', 'unmapped'),
                    mapping_confidence=data.get('mapping_confidence', 0.0),
                    last_mapped_by=data.get('last_mapped_by', ''),
                    last_mapped_at=datetime.fromisoformat(data['last_mapped_at'].replace('Z', '+00:00')) if data.get('last_mapped_at') else None,
                    validation_status=data.get('validation_status', 'pending'),
                    validation_errors=data.get('validation_errors', []),
                    data_quality_score=data.get('data_quality_score', 0.0),
                    # Metadata
                    row_type=data.get('row_type', 'data'),
                    is_active=data.get('is_active', True),
                    notes=data.get('notes', ''),
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None,
                    updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')) if data.get('updated_at') else None
                ))
            return rows
        except Exception as e:
            raise Exception(f"Error getting session data: {str(e)}")
    
    def update_data_row(self, row_id: str, updates: Dict) -> bool:
        """Update a data row"""
        try:
            updates['updated_at'] = datetime.now().isoformat()
            result = self.client.table('balance_sheet_data').update(updates).eq('id', row_id).execute()
            return result.data is not None
        except Exception as e:
            raise Exception(f"Error updating data row: {str(e)}")
    
    def batch_update_mapping(self, session_id: str, mappings: List[Dict]) -> bool:
        """Batch update mappings for multiple rows"""
        try:
            result = self.client.table('balance_sheet_data').upsert(mappings).execute()
            return result.data is not None
        except Exception as e:
            raise Exception(f"Error batch updating mappings: {str(e)}")
    
    # ==================== MAPPING RULES ====================
    
    def create_mapping_rule(self, rule: MappingRule) -> str:
        """Create a new mapping rule"""
        try:
            data = rule.to_dict()
            result = self.client.table('mapping_rules').insert(data).execute()
            if result.data:
                return result.data[0]['id']
            raise Exception("Failed to create mapping rule")
        except Exception as e:
            raise Exception(f"Error creating mapping rule: {str(e)}")
    
    def get_mapping_rules(self, user_id: str = None, rule_type: str = None, active_only: bool = True) -> List[MappingRule]:
        """Get mapping rules"""
        try:
            query = self.client.table('mapping_rules').select('*')
            
            if user_id:
                query = query.eq('user_id', user_id)
            if rule_type:
                query = query.eq('rule_type', rule_type)
            if active_only:
                query = query.eq('is_active', True)
            
            result = query.order('priority', desc=True).execute()
            rules = []
            for data in result.data:
                rules.append(MappingRule(
                    id=data['id'],
                    user_id=data['user_id'],
                    rule_name=data['rule_name'],
                    rule_type=data['rule_type'],
                    pattern_type=data['pattern_type'],
                    input_pattern=data['input_pattern'],
                    output_value=data['output_value'],
                    context=data.get('context', {}),
                    conditions=data.get('conditions', {}),
                    confidence_score=data.get('confidence_score', 0.0),
                    usage_count=data.get('usage_count', 0),
                    success_rate=data.get('success_rate', 0.0),
                    is_active=data.get('is_active', True),
                    is_system_rule=data.get('is_system_rule', False),
                    priority=data.get('priority', 50),
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None,
                    updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')) if data.get('updated_at') else None,
                    last_used_at=datetime.fromisoformat(data['last_used_at'].replace('Z', '+00:00')) if data.get('last_used_at') else None
                ))
            return rules
        except Exception as e:
            raise Exception(f"Error getting mapping rules: {str(e)}")
    
    # ==================== GRAP CHART OF ACCOUNTS ====================
    
    def get_grap_accounts(self, category: str = None, active_only: bool = True) -> List[GRAPChartOfAccounts]:
        """Get GRAP chart of accounts"""
        try:
            query = self.client.table('grap_chart_of_accounts').select('*')
            
            if category:
                query = query.eq('grap_category', category)
            if active_only:
                query = query.eq('is_active', True)
            
            result = query.order('grap_category').execute()
            accounts = []
            for data in result.data:
                accounts.append(GRAPChartOfAccounts(
                    id=data['id'],
                    grap_category=data['grap_category'],
                    grap_subcategory=data.get('grap_subcategory', ''),
                    grap_account=data['grap_account'],
                    grap_account_code=data.get('grap_account_code', ''),
                    account_description=data.get('account_description', ''),
                    account_type=data.get('account_type', ''),
                    normal_balance=data.get('normal_balance', ''),
                    keywords=data.get('keywords', []),
                    alternative_names=data.get('alternative_names', []),
                    mapping_patterns=data.get('mapping_patterns', []),
                    is_active=data.get('is_active', True),
                    is_custom=data.get('is_custom', False),
                    created_by=data.get('created_by', ''),
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None,
                    updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')) if data.get('updated_at') else None
                ))
            return accounts
        except Exception as e:
            raise Exception(f"Error getting GRAP accounts: {str(e)}")
    
    def search_grap_accounts(self, search_term: str) -> List[GRAPChartOfAccounts]:
        """Search GRAP accounts by name or keywords"""
        try:
            result = self.client.table('grap_chart_of_accounts').select('*').or_(
                f"grap_account.ilike.%{search_term}%,account_description.ilike.%{search_term}%,keywords.cs.{{{search_term}}}"
            ).eq('is_active', True).execute()
            
            accounts = []
            for data in result.data:
                accounts.append(GRAPChartOfAccounts(
                    id=data['id'],
                    grap_category=data['grap_category'],
                    grap_subcategory=data.get('grap_subcategory', ''),
                    grap_account=data['grap_account'],
                    grap_account_code=data.get('grap_account_code', ''),
                    account_description=data.get('account_description', ''),
                    account_type=data.get('account_type', ''),
                    normal_balance=data.get('normal_balance', ''),
                    keywords=data.get('keywords', []),
                    alternative_names=data.get('alternative_names', []),
                    mapping_patterns=data.get('mapping_patterns', []),
                    is_active=data.get('is_active', True),
                    is_custom=data.get('is_custom', False),
                    created_by=data.get('created_by', ''),
                    created_at=datetime.fromisoformat(data['created_at'].replace('Z', '+00:00')) if data.get('created_at') else None,
                    updated_at=datetime.fromisoformat(data['updated_at'].replace('Z', '+00:00')) if data.get('updated_at') else None
                ))
            return accounts
        except Exception as e:
            raise Exception(f"Error searching GRAP accounts: {str(e)}")
    
    # ==================== UTILITY METHODS ====================
    
    def calculate_file_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum of a file"""
        try:
            with open(file_path, 'rb') as f:
                file_hash = hashlib.md5()
                while chunk := f.read(8192):
                    file_hash.update(chunk)
                return file_hash.hexdigest()
        except Exception as e:
            raise Exception(f"Error calculating file checksum: {str(e)}")
    
    def get_session_summary(self, session_id: str) -> Dict:
        """Get balance sheet session summary using database function"""
        try:
            result = self.client.rpc('get_balance_sheet_summary', {'p_session_id': session_id}).execute()
            if result.data:
                return result.data[0]
            return {}
        except Exception as e:
            raise Exception(f"Error getting session summary: {str(e)}")
    
    def add_processing_log(self, session_id: str, action: str, details: Dict = None) -> bool:
        """Add entry to processing log"""
        try:
            session = self.get_session(session_id)
            if session:
                log_entry = {
                    'action': action,
                    'timestamp': datetime.now().isoformat(),
                    'details': details or {}
                }
                session.processing_log.append(log_entry)
                return self.update_session_status(session_id, session.status, session.metadata)
            return False
        except Exception as e:
            raise Exception(f"Error adding processing log: {str(e)}")


# Global instance
balance_sheet_model = BalanceSheetModel()
