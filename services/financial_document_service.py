"""
Financial Document Service - Base Abstract Class
Provides common functionality for all financial document types (Balance Sheets, Income Statements, Budget Reports)
"""

import pandas as pd
import uuid
import json
import hashlib
import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from decimal import Decimal

from supabase import create_client, Client
from models.supabase_auth_models import supabase_auth

# Set up logging
logger = logging.getLogger(__name__)


@dataclass
class FinancialDocumentSession:
    """Base class for financial document upload sessions"""
    id: Optional[str] = None
    user_id: str = ""
    document_type: str = ""  # 'balance_sheet', 'income_statement', 'budget_report'
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
        if data['id'] is None:
            data.pop('id')
        # Convert datetime objects to ISO strings
        if data['created_at']:
            data['created_at'] = data['created_at'].isoformat()
        if data['updated_at']:
            data['updated_at'] = data['updated_at'].isoformat()
        if data['processed_at']:
            data['processed_at'] = data['processed_at'].isoformat()
        return data


class FinancialDocumentService(ABC):
    """Abstract base class for all financial document services"""
    
    def __init__(self, document_type: str):
        self.document_type = document_type
        self.supported_formats = ['xlsx', 'xls', 'csv', 'xlsm', 'xlsb', 'tsv']
        
        # Common column patterns (can be extended by subclasses)
        self.common_column_patterns = {
            'account_code': [
                r'(?i)account\s*code',
                r'(?i)acc\s*code',
                r'(?i)code',
                r'(?i)account\s*no',
                r'(?i)account\s*number',
                r'(?i)gl\s*code'
            ],
            'account_desc': [
                r'(?i)account\s*desc',
                r'(?i)account\s*name',
                r'(?i)description',
                r'(?i)particulars',
                r'(?i)details',
                r'(?i)explanation',
                r'(?i)reference',
                r'(?i)note'
            ]
        }
        
        # Document-specific patterns (to be overridden by subclasses)
        self.document_specific_patterns = {}
    
    @abstractmethod
    def get_document_specific_patterns(self) -> Dict[str, List[str]]:
        """Get document-specific column patterns"""
        pass
    
    @abstractmethod
    def validate_document_structure(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Validate document-specific structure"""
        pass
    
    @abstractmethod
    def create_session(self, file_path: str, user_id: str, filename: str) -> FinancialDocumentSession:
        """Create document-specific session"""
        pass
    
    @abstractmethod
    def get_model(self):
        """Get the appropriate model for this document type"""
        pass
    
    def process_upload(self, file_path: str, user_id: str, filename: str, period_id: Optional[str] = None) -> Dict:
        """
        Process uploaded financial document file with optional period validation
        """
        logger.info(f"🔄 {self.__class__.__name__}.process_upload called")
        logger.info(f"📁 file_path: {file_path}")
        logger.info(f"👤 user_id: {user_id}")
        logger.info(f"📄 filename: {filename}")
        logger.info(f"📋 document_type: {self.document_type}")
        
        try:
            # Step 1: Create session
            logger.info("📋 Step 1: Creating session...")
            session = self.create_session(file_path, user_id, filename)
            logger.info(f"✅ Session created: {session.id}")
            
            # Check if session ID is valid
            if not session.id or session.id == "":
                raise Exception("Session creation failed - empty session ID returned")
            
            # Step 2: Read and analyze file
            logger.info("📖 Step 2: Reading file...")
            df = self._read_file(file_path)
            logger.info(f"✅ File read successfully. Shape: {df.shape}")
            logger.info(f"📊 Columns: {list(df.columns)}")
            
            # Step 3: Detect column structure
            logger.info("🔍 Step 3: Detecting column structure...")
            column_mapping = self._detect_columns(df)
            logger.info(f"📋 Column mapping: {column_mapping}")
            
            # Step 4: Validate document structure
            logger.info("✅ Step 4: Validating document structure...")
            validation_result = self.validate_document_structure(df)
            logger.info(f"📊 Validation result: {validation_result}")
            
            # Step 5: Store session data
            logger.info("💾 Step 5: Storing session data...")
            session.total_rows = len(df)
            session.total_columns = len(df.columns)
            session.file_size_bytes = self._get_file_size(file_path)
            session.checksum_md5 = self._calculate_checksum(file_path)
            session.metadata['column_mapping'] = column_mapping
            session.metadata['validation_result'] = validation_result
            session.processing_log.append(f"File processed successfully: {len(df)} rows, {len(df.columns)} columns")
            
            # Store in database
            stored_session = self._store_session(session)
            logger.info(f"💾 Session stored in database: {stored_session.id}")
            
            # Step 6: Process data rows
            logger.info("📝 Step 6: Processing data rows...")
            data_rows = self._process_data_rows(stored_session.id, df, column_mapping, validation_result)
            logger.info(f"✅ Processed {len(data_rows)} data rows")
            
            return {
                'success': True,
                'session_id': stored_session.id,
                'document_type': self.document_type,
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'column_mapping': column_mapping,
                'validation_result': validation_result,
                'data_rows_count': len(data_rows),
                'message': f'{self.document_type.replace("_", " ").title()} processed successfully'
            }
            
        except Exception as e:
            logger.error(f"❌ Error processing {self.document_type}: {str(e)}")
            return {
                'success': False,
                'error': f'Error processing {self.document_type}: {str(e)}',
                'document_type': self.document_type
            }
    
    def _process_data_rows(self, session_id: str, df: pd.DataFrame, column_mapping: Dict, validation_result: Dict) -> List:
        """Process data rows from uploaded file and save to database"""
        data_rows = []
        
        # Determine data start row (skip headers if present)
        has_headers = validation_result.get('has_headers', False)
        start_row = 1 if has_headers else 0
        
        # Process each row in the dataframe
        for idx, row in df.iloc[start_row:].iterrows():
            # Skip empty rows
            if row.isna().all():
                continue
            
            # Create data row based on document type
            data_row = self._create_data_row_from_row(session_id, idx, row, column_mapping)
            if data_row:
                data_rows.append(data_row)
        
        # Save data rows to database
        if data_rows:
            model = self.get_model()
            if hasattr(model, 'create_data_row'):
                created_rows = []
                for data_row in data_rows:
                    try:
                        created_row = model.create_data_row(data_row)
                        created_rows.append(created_row)
                    except Exception as e:
                        logger.error(f" Error creating data row: {str(e)}")
                logger.info(f" Created {len(created_rows)} data rows in database")
            else:
                logger.warning(f" Model does not support create_data_row method")
        
        return data_rows
    
    def _read_file(self, file_path: str) -> pd.DataFrame:
        """Read file based on format"""
        file_extension = file_path.split('.')[-1].lower()
        
        if file_extension in ['xlsx', 'xls', 'xlsm', 'xlsb']:
            return pd.read_excel(file_path)
        elif file_extension == 'csv':
            return pd.read_csv(file_path)
        elif file_extension == 'tsv':
            return pd.read_csv(file_path, sep='\t')
        else:
            raise ValueError(f"Unsupported file format: {file_extension}")
    
    def _detect_columns(self, df: pd.DataFrame) -> Dict[str, str]:
        """Detect column mappings based on patterns"""
        column_mapping = {}
        detected_patterns = {}
        
        # Combine common and document-specific patterns
        all_patterns = {**self.common_column_patterns, **self.document_specific_patterns}
        
        for field_name, patterns in all_patterns.items():
            for pattern in patterns:
                for col in df.columns:
                    if re.match(pattern, str(col).strip()):
                        column_mapping[field_name] = col
                        detected_patterns[field_name] = pattern
                        break
                if field_name in column_mapping:
                    break
        
        logger.info(f" Detected column patterns: {detected_patterns}")
        return column_mapping
    
    def _get_file_size(self, file_path: str) -> int:
        """Get file size in bytes"""
        try:
            return os.path.getsize(file_path)
        except:
            return 0
    
    def _calculate_checksum(self, file_path: str) -> str:
        """Calculate MD5 checksum of file"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""
    
        return model.create_session(session)
    
    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get session summary for display"""
        model = self.get_model()
        session = model.get_session(session_id)
        
        if not session:
            return {
                'success': False,
                'error': f'Session {session_id} not found'
            }
        
        return {
            'success': True,
            'session_id': session.id,
            'document_type': session.document_type,
            'filename': session.filename,
            'status': session.status,
            'total_rows': session.total_rows,
            'total_columns': session.total_columns,
            'created_at': session.created_at.isoformat() if session.created_at else None,
            'metadata': session.metadata,
            'processing_log': session.processing_log[-5:] if session.processing_log else []
        }


# Import os for file operations
import os
