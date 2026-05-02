"""
Flexible Balance Sheet Upload Service
Handles any kind of balance sheet format with automatic detection and mapping
"""

import pandas as pd
import uuid
import json
import hashlib
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from decimal import Decimal

from supabase import create_client, Client
from models.supabase_auth_models import supabase_auth

# Set up logging
logger = logging.getLogger(__name__)

from models.balance_sheet_models import (
    balance_sheet_model, BalanceSheetSession, BalanceSheetColumn, 
    BalanceSheetDataRow, MappingRule, GRAPChartOfAccounts
)


class FlexibleBalanceSheetService:
    """Service for handling flexible balance sheet uploads"""
    
    def __init__(self):
        self.model = balance_sheet_model
        self.supported_formats = ['xlsx', 'xls', 'csv', 'xlsm', 'xlsb', 'tsv']
        self.column_patterns = {
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
            ],
            'debit': [
                r'(?i)debit',
                r'(?i)dr',
                r'(?i)debit\s*balance',
                r'(?i)debit\s*amt'
            ],
            'credit': [
                r'(?i)credit',
                r'(?i)cr',
                r'(?i)credit\s*balance',
                r'(?i)credit\s*amt'
            ],
            'net_balance': [
                r'(?i)net\s*balance',
                r'(?i)balance',
                r'(?i)amount',
                r'(?i)total'
            ]
        }
    
    def process_upload(self, file_path: str, user_id: str, filename: str, period_id: Optional[str] = None) -> Dict:
        """
        Process uploaded balance sheet file with optional period validation
        """
        print(f"🔄 FlexibleBalanceSheetService.process_upload called")
        print(f"📁 file_path: {file_path}")
        print(f"👤 user_id: {user_id}")
        print(f"📄 filename: {filename}")
        
        try:
            # Step 1: Create session
            print("📋 Step 1: Creating session...")
            session = self._create_session(file_path, user_id, filename)
            print(f"✅ Session created: {session.id}")
            print(f"🔍 Session ID type: {type(session.id)}")
            print(f"🔍 Session ID value: '{session.id}'")
            
            # Check if session ID is valid
            if not session.id or session.id == "":
                raise Exception("Session creation failed - empty session ID returned")
            
            # Step 2: Read and analyze file
            print("📖 Step 2: Reading file...")
            df = self._read_file(file_path)
            print(f"✅ File read successfully. Shape: {df.shape}")
            print(f"📊 Columns: {list(df.columns)}")
            
            file_format = self._detect_file_format(file_path)
            print(f"📋 File format detected: {file_format}")
            
            # Step 3: Detect structure and columns
            print("🔍 Step 3: Detecting structure...")
            structure_info = self._detect_structure(df)
            print(f"✅ Structure detected: {structure_info['file_type']}")
            print(f"📊 Quality score: {structure_info['quality_score']}")
            
            # Step 4: Create column definitions
            print("🏗️ Step 4: Creating column definitions...")
            columns = self._create_columns(session.id, df.columns, structure_info)
            print(f"✅ Created {len(columns)} column definitions")
            
            # Step 5: Process data rows
            print("📝 Step 5: Processing data rows...")
            data_rows = self._process_data_rows(session.id, df, columns, structure_info)
            print(f"✅ Processed {len(data_rows)} data rows")
            
            # Step 6: Update session with results
            print("💾 Step 6: Updating session results...")
            self._update_session_results(session, df, structure_info, data_rows)
            print("✅ Session updated")
            
            # Step 7: Perform initial auto-mapping
            print("🗺️ Step 7: Performing auto-mapping...")
            mapping_results = self._perform_auto_mapping(session.id, data_rows)
            print(f"✅ Auto-mapping completed: {mapping_results}")
            
            # Step 8: Store mapping results in session metadata
            print("💾 Step 8: Storing mapping results in session metadata...")
            processing_results = {
                'mapped_accounts': mapping_results.get('auto_mapped', 0),
                'unmapped_accounts': mapping_results.get('manual_review_needed', 0),
                'total_accounts': len(data_rows),
                'mapping_confidence': mapping_results.get('mapping_confidence', 0.0),
                'processed_at': datetime.now().isoformat()
            }
            
            # Update session metadata with processing results
            self._update_session_processing_results(session.id, processing_results)
            print(f"✅ Mapping results stored: {processing_results}")
            
            result = {
                'success': True,
                'session_id': session.id,
                'file_format': file_format,
                'structure_info': structure_info,
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'columns': [col.to_dict() for col in columns],
                'mapping_results': mapping_results
            }
            
            print(f"🎉 Processing completed successfully!")
            print(f"📊 Result summary: {result['total_rows']} rows, {result['total_columns']} columns")
            return result
            
        except Exception as e:
            print(f"💥 Exception in process_upload: {str(e)}")
            import traceback
            print(f"📚 Full traceback: {traceback.format_exc()}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _create_session(self, file_path: str, user_id: str, filename: str) -> BalanceSheetSession:
        """Create a new balance sheet session"""
        import os
        
        # Calculate file size and checksum
        file_size = os.path.getsize(file_path)
        checksum = self.model.calculate_file_checksum(file_path)
        
        session = BalanceSheetSession(
            user_id=user_id,
            filename=filename,
            original_filename=filename,
            status='uploaded',
            file_size_bytes=file_size,
            checksum_md5=checksum,
            metadata={
                'upload_source': 'web_interface',
                'processing_stage': 'initial_upload'
            }
        )
        
        session_id = self.model.create_session(session)
        session.id = session_id
        return session
    
    def _read_file(self, file_path: str) -> pd.DataFrame:
        """Read file with automatic format detection"""
        if file_path.endswith(('.xlsx', '.xlsm', '.xlsb')):
            # Handle Excel formats with appropriate engines
            if file_path.endswith('.xlsx'):
                return pd.read_excel(file_path, engine='openpyxl')
            elif file_path.endswith('.xlsm'):
                # Excel with macros - try openpyxl first
                try:
                    return pd.read_excel(file_path, engine='openpyxl')
                except:
                    return pd.read_excel(file_path)  # fallback to default
            elif file_path.endswith('.xlsb'):
                # Binary Excel format
                try:
                    return pd.read_excel(file_path, engine='pyxlsb')
                except ImportError:
                    # If pyxlsb not available, try default
                    return pd.read_excel(file_path)
        elif file_path.endswith('.xls'):
            # Legacy Excel format
            return pd.read_excel(file_path, engine='xlrd')
        elif file_path.endswith('.csv'):
            # CSV files - try different encodings
            encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
            for encoding in encodings:
                try:
                    return pd.read_csv(file_path, encoding=encoding)
                except UnicodeDecodeError:
                    continue
            raise Exception("Could not read CSV file with any supported encoding")
        elif file_path.endswith('.tsv'):
            # Tab-separated values
            encodings = ['utf-8', 'latin1', 'cp1252', 'iso-8859-1']
            for encoding in encodings:
                try:
                    return pd.read_csv(file_path, encoding=encoding, sep='\t')
                except UnicodeDecodeError:
                    continue
            raise Exception("Could not read TSV file with any supported encoding")
        else:
            raise Exception(f"Unsupported file format: {file_path}")
    
    def _detect_file_format(self, file_path: str) -> str:
        """Detect file format from extension"""
        if file_path.endswith('.xlsx'):
            return 'excel_xlsx'
        elif file_path.endswith('.xlsm'):
            return 'excel_xlsm'
        elif file_path.endswith('.xlsb'):
            return 'excel_xlsb'
        elif file_path.endswith('.xls'):
            return 'excel_xls'
        elif file_path.endswith('.csv'):
            return 'csv'
        elif file_path.endswith('.tsv'):
            return 'tsv'
        else:
            return 'unknown'
    
    def _detect_structure(self, df: pd.DataFrame) -> Dict:
        """Detect balance sheet structure"""
        structure_info = {
            'file_type': 'unknown',
            'has_headers': False,
            'column_mapping': {},
            'data_start_row': 0,
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'detected_patterns': {},
            'quality_score': 0.0
        }
        
        # Check if first row looks like headers
        first_row = df.iloc[0]
        structure_info['has_headers'] = self._looks_like_header_row(first_row)
        
        # Detect column types
        structure_info['column_mapping'] = self._detect_column_types(df.columns)
        
        # Detect data patterns
        structure_info['detected_patterns'] = self._detect_data_patterns(df)
        
        # Determine file type
        structure_info['file_type'] = self._determine_file_type(structure_info)
        
        # Calculate quality score
        structure_info['quality_score'] = self._calculate_quality_score(structure_info)
        
        return structure_info
    
    def _looks_like_header_row(self, row: pd.Series) -> bool:
        """Check if a row looks like headers"""
        text_columns = 0
        total_columns = len(row)
        
        for value in row:
            if pd.notna(value) and isinstance(value, str):
                # Check if it contains typical header keywords
                if any(keyword in value.lower() for keyword in 
                   ['account', 'code', 'desc', 'debit', 'credit', 'balance', 'amount', 'total']):
                    text_columns += 1
        
        # If more than 30% of columns look like headers, consider it a header row
        return (text_columns / total_columns) > 0.3
    
    def _detect_column_types(self, columns: List[str]) -> Dict:
        """Detect column types based on column names"""
        column_mapping = {}
        
        for i, col in enumerate(columns):
            if pd.notna(col):
                col_str = str(col).strip()
                detected_type = 'custom'
                confidence = 0.0
                
                # Check against patterns
                for col_type, patterns in self.column_patterns.items():
                    for pattern in patterns:
                        if re.search(pattern, col_str):
                            detected_type = col_type
                            confidence = 0.8  # Base confidence for pattern match
                            break
                    
                    if detected_type != 'custom':
                        break
                
                # Additional checks for numeric columns
                if detected_type == 'custom':
                    # Check if column name suggests numeric data
                    if any(keyword in col_str.lower() for keyword in ['amount', 'balance', 'total', 'sum']):
                        detected_type = 'numeric'
                        confidence = 0.6
                
                column_mapping[i] = {
                    'type': detected_type,
                    'confidence': confidence,
                    'original_name': col_str
                }
        
        return column_mapping
    
    def _detect_data_patterns(self, df: pd.DataFrame) -> Dict:
        """Detect patterns in the data"""
        patterns = {
            'has_numeric_data': False,
            'has_account_codes': False,
            'has_descriptions': False,
            'has_debit_credit': False,
            'has_multi_period': False,
            'date_columns': [],
            'numeric_columns': []
        }
        
        # Sample first few rows for pattern detection
        sample_rows = min(10, len(df))
        
        for col in df.columns:
            col_data = df[col].head(sample_rows)
            
            # Check for numeric data
            if col_data.apply(lambda x: pd.notna(x) and str(x).replace('.', '').replace('-', '').isdigit()).any():
                patterns['has_numeric_data'] = True
                patterns['numeric_columns'].append(col)
            
            # Check for account codes (alphanumeric patterns)
            if col_data.apply(lambda x: pd.notna(x) and isinstance(x, str) and 
                              any(c.isalpha() for c in str(x)) and any(c.isdigit() for c in str(x))).any():
                patterns['has_account_codes'] = True
            
            # Check for descriptions (text with spaces)
            if col_data.apply(lambda x: pd.notna(x) and isinstance(x, str) and 
                              len(str(x).split()) > 1).any():
                patterns['has_descriptions'] = True
            
            # Check for date columns
            if col_data.apply(lambda x: pd.notna(x) and isinstance(x, str) and 
                              any(char in str(x) for char in ['/', '-', '.'])).any():
                patterns['date_columns'].append(col)
        
        # Check for multiple periods (columns with period names)
        period_keywords = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
                         'q1', 'q2', 'q3', 'q4', 'period', 'month']
        
        for col in df.columns:
            if any(keyword in str(col).lower() for keyword in period_keywords):
                patterns['has_multi_period'] = True
                break
        
        return patterns
    
    def _determine_file_type(self, structure_info: Dict) -> str:
        """Determine the file type based on detected patterns"""
        if structure_info['has_headers'] and structure_info['detected_patterns']['has_account_codes']:
            if structure_info['detected_patterns']['has_multi_period']:
                return 'multi_period_standard'
            elif structure_info['detected_patterns']['has_debit_credit']:
                return 'standard_balance_sheet'
            else:
                return 'simple_balance_sheet'
        elif structure_info['detected_patterns']['has_numeric_data']:
            return 'numeric_only'
        else:
            return 'unknown'
    
    def _calculate_quality_score(self, structure_info: Dict) -> float:
        """Calculate quality score for the detected structure"""
        score = 0.0
        
        # Base score for having headers
        if structure_info['has_headers']:
            score += 0.2
        
        # Score for detected patterns
        if structure_info['detected_patterns']['has_account_codes']:
            score += 0.2
        if structure_info['detected_patterns']['has_descriptions']:
            score += 0.2
        if structure_info['detected_patterns']['has_numeric_data']:
            score += 0.2
        if structure_info['detected_patterns']['has_debit_credit']:
            score += 0.1
        if structure_info['detected_patterns']['has_multi_period']:
            score += 0.1
        
        return min(score, 1.0)
    
    def _create_columns(self, session_id: str, columns: pd.Index, structure_info: Dict) -> List[BalanceSheetColumn]:
        """Create column definitions"""
        balance_sheet_columns = []
        
        for i, col in enumerate(columns):
            col_mapping = structure_info['column_mapping'].get(i, {})
            
            balance_sheet_column = BalanceSheetColumn(
                session_id=session_id,
                column_name=str(col).strip(),
                original_column_name=str(col),
                column_index=i,
                column_type=col_mapping.get('type', 'custom'),
                data_type=self._detect_column_data_type(col, structure_info),
                mapping_confidence=col_mapping.get('confidence', 0.0),
                is_required=col_mapping.get('type') in ['account_code', 'account_desc'],
                is_key_column=col_mapping.get('type') == 'account_code'
            )
            
            balance_sheet_columns.append(balance_sheet_column)
        
        # Save columns to database
        self.model.create_columns(balance_sheet_columns)
        
        return balance_sheet_columns
    
    def _detect_column_data_type(self, column_name: str, structure_info: Dict) -> str:
        """Detect data type for a column"""
        col_mapping = structure_info['column_mapping']
        
        for i, mapping in col_mapping.items():
            if mapping['original_name'] == column_name:
                if mapping['type'] in ['debit', 'credit', 'net_balance']:
                    return 'currency'
                elif mapping['type'] == 'account_code':
                    return 'text'
                elif mapping['type'] == 'account_desc':
                    return 'text'
                elif structure_info['detected_patterns']['has_numeric_data'] and column_name in structure_info['detected_patterns']['numeric_columns']:
                    return 'number'
                else:
                    return 'text'
        
        return 'text'
    
    def _process_data_rows(self, session_id: str, df: pd.DataFrame, columns: List[BalanceSheetColumn], structure_info: Dict) -> List[BalanceSheetDataRow]:
        """Process data rows and save to database"""
        data_rows = []
        
        # Determine data start row (skip headers if present)
        start_row = 1 if structure_info['has_headers'] else 0
        
        for idx, row in df.iloc[start_row:].iterrows():
            # Skip empty rows
            if row.isna().all():
                continue
            
            # Create raw data dictionary
            raw_data = {str(col): str(val) if pd.notna(val) else '' for col, val in row.items()}
            
            # Process data based on column mappings
            processed_data = {}
            account_code = ''
            account_description = ''
            debit_balance = None
            credit_balance = None
            net_balance = None
            
            for col in columns:
                col_value = row.iloc[col.column_index] if col.column_index < len(row) else None
                
                if pd.notna(col_value):
                    value = str(col_value).strip()
                    
                    if col.column_type == 'account_code':
                        account_code = value
                        processed_data['account_code'] = value
                    elif col.column_type == 'account_desc':
                        account_description = value
                        processed_data['account_description'] = value
                    elif col.column_type == 'debit':
                        try:
                            debit_balance = Decimal(str(value).replace(',', ''))
                            processed_data['debit_balance'] = float(debit_balance)
                        except:
                            pass
                    elif col.column_type == 'credit':
                        try:
                            credit_balance = Decimal(str(value).replace(',', ''))
                            processed_data['credit_balance'] = float(credit_balance)
                        except:
                            pass
                    elif col.column_type == 'net_balance':
                        try:
                            net_balance = Decimal(str(value).replace(',', ''))
                            processed_data['net_balance'] = float(net_balance)
                        except:
                            pass
                    elif col.column_type.startswith('period_'):
                        try:
                            period_value = Decimal(str(value).replace(',', ''))
                            processed_data[col.column_type] = float(period_value)
                        except:
                            pass
                    else:
                        processed_data[col.column_name] = value
            
            # Calculate net balance if not provided
            if net_balance is None and debit_balance is not None and credit_balance is not None:
                net_balance = debit_balance - credit_balance
            
            # Create data row
            print(f"🔍 Creating data row for session_id: {session_id} (type: {type(session_id)})")
            data_row = BalanceSheetDataRow(
                session_id=session_id,
                row_index=idx,
                raw_data=raw_data,
                processed_data=processed_data,
                account_code=account_code,
                account_description=account_description,
                debit_balance=debit_balance,
                credit_balance=credit_balance,
                net_balance=net_balance,
                mapping_status='unmapped',
                validation_status='pending',
                row_type='data'
            )
            
            data_rows.append(data_row)
        
        # Save data rows to database
        if data_rows:
            self.model.create_data_rows(data_rows)
        
        return data_rows
    
        
    def _perform_auto_mapping(self, session_id: str, data_rows: List[BalanceSheetDataRow]) -> Dict:
        """Perform automatic mapping of accounts to GRAP categories"""
        mapping_results = {
            'total_rows': len(data_rows),
            'auto_mapped': 0,
            'manual_review_needed': 0,
            'mapping_confidence': 0.0
        }
        
        # Get GRAP accounts for mapping
        grap_accounts = self.model.get_grap_accounts()
        
        # Get mapping rules
        mapping_rules = self.model.get_mapping_rules(active_only=True)
        
        total_confidence = 0.0
        mapped_count = 0
        
        for row in data_rows:
            if not row.account_code and not row.account_description:
                continue
            
            best_match = None
            best_confidence = 0.0
            
            # Try exact matches first
            for grap_account in grap_accounts:
                confidence = self._calculate_match_confidence(row, grap_account)
                if confidence > best_confidence:
                    best_match = grap_account
                    best_confidence = confidence
            
            # Apply mapping if found
            if best_match and best_confidence > 0.5:
                updates = {
                    'grap_category': best_match.grap_category,
                    'grap_account': best_match.grap_account,
                    'grap_subcategory': best_match.grap_subcategory or '',
                    'mapping_status': 'auto_mapped',
                    'mapping_confidence': best_confidence
                }
                
                self.model.update_data_row(row.id, updates)
                mapped_count += 1
                total_confidence += best_confidence
            else:
                mapping_results['manual_review_needed'] += 1
        
        mapping_results['auto_mapped'] = mapped_count
        mapping_results['mapping_confidence'] = total_confidence / max(len(data_rows), 1)
        
        return mapping_results
    
    def _calculate_match_confidence(self, row: BalanceSheetDataRow, grap_account: GRAPChartOfAccounts) -> float:
        """Calculate confidence score for account matching"""
        confidence = 0.0
        
        # Exact account code match
        if row.account_code and row.account_code == grap_account.grap_account_code:
            confidence += 0.9
        
        # Account code contains match
        if row.account_code and grap_account.grap_account_code and grap_account.grap_account_code in row.account_code:
            confidence += 0.7
        
        # Exact description match
        if row.account_description and row.account_description.strip() == grap_account.account_description.strip():
            confidence += 0.8
        
        # Description contains match
        if row.account_description and grap_account.account_description:
            if grap_account.account_description.lower() in row.account_description.lower():
                confidence += 0.6
        
        # Keyword matching
        if row.account_description and grap_account.keywords:
            for keyword in grap_account.keywords:
                if keyword.lower() in row.account_description.lower():
                    confidence += 0.3
                    break
        
        # Alternative names matching
        if row.account_description and grap_account.alternative_names:
            for alt_name in grap_account.alternative_names:
                if alt_name.lower() in row.account_description.lower():
                    confidence += 0.4
                    break
        
        return min(confidence, 1.0)
    
    def _update_session_results(self, session: BalanceSheetSession, df: pd.DataFrame, structure_info: Dict, data_rows: List[BalanceSheetDataRow]):
        """Update session with processing results"""
        session.total_rows = len(df)
        session.total_columns = len(df.columns)
        session.file_type = structure_info['file_type']
        session.status = 'uploaded'  # Set to uploaded to match database constraint
            
        # Update metadata
        session.metadata.update({
            'structure_info': structure_info,
            'processing_timestamp': datetime.now().isoformat(),
            'data_quality_score': structure_info['quality_score']
        })
            
        # Update session
        self.model.update_session_status(session.id, session.status, session.metadata)

    def get_session_data(self, session_id: str) -> Dict:
        """Get session data including balance sheet data for validation"""
        try:
            with open('balance_check_debug.log', 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] get_session_data called with session_id: {session_id}\n")
            
            session = self.model.get_session(session_id)
            
            with open('balance_check_debug.log', 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] Session from model: {session}\n")
            
            if not session:
                with open('balance_check_debug.log', 'a') as f:
                    f.write(f"[{datetime.now().isoformat()}] Session not found for ID: {session_id}\n")
                return {'success': False, 'error': 'Session not found'}
            
            # Get data rows
            data_rows = self.model.get_session_data(session_id)
            
            with open('balance_check_debug.log', 'a') as f:
                f.write(f"[{datetime.now().isoformat()}] Data rows from model: {len(data_rows) if data_rows else 0} rows\n")
            
            if not data_rows:
                with open('balance_check_debug.log', 'a') as f:
                    f.write(f"[{datetime.now().isoformat()}] No data rows found for session: {session_id}\n")
                return {'success': False, 'error': 'No data rows found'}
            
            # Convert data rows to balance sheet data format
            balance_sheet_data = []
            for row in data_rows:
                balance_sheet_data.append({
                    'Account Code': row.account_code,
                    'Account Description': row.account_description,
                    'Debit Balance': float(row.debit_balance) if row.debit_balance else 0,
                    'Credit Balance': float(row.credit_balance) if row.credit_balance else 0,
                    'Net Balance': float(row.net_balance) if row.net_balance else 0
                })
            
            return {
                'success': True,
                'session_id': session.id,
                'balance_sheet_data': balance_sheet_data,
                'file_format': session.file_format,
                'metadata': session.metadata
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def process_grap_mapping(self, session_id: str, user_id: str) -> Dict:
        """Process GRAP mapping and generate financial statements"""
        try:
            # Import GRAP mapping service
            from services.grap_mapping_service import grap_mapping_service
            
            # Get session data
            session_data = self.get_session_data(session_id)
            if not session_data or not session_data.get('success'):
                return {'success': False, 'error': 'Session data not found or invalid'}
            
            # Get balance sheet data
            balance_sheet_data = session_data.get('balance_sheet_data', [])
            if not balance_sheet_data:
                return {'success': False, 'error': 'No balance sheet data found'}
            
            # Perform GRAP mapping for each account
            mapped_accounts = []
            unmapped_accounts = []
            
            for account in balance_sheet_data:
                account_code = account.get('Account Code', '')
                account_desc = account.get('Account Description', '')
                
                # Get GRAP mapping suggestion
                suggestions = grap_mapping_service.get_mapping_suggestions(account_desc, account_code)
                
                if suggestions and len(suggestions) > 0:
                    top_suggestion = suggestions[0]
                    if top_suggestion.confidence > 0.5:  # Confidence threshold
                        mapped_accounts.append({
                            'account_code': account_code,
                            'account_desc': account_desc,
                            'grap_code': top_suggestion.category_code,
                            'grap_name': top_suggestion.category_name,
                            'confidence': top_suggestion.confidence,
                        'debit': account.get('Debit Balance', 0),
                        'credit': account.get('Credit Balance', 0),
                        'net_balance': account.get('Net Balance', 0)
                    })
                else:
                    unmapped_accounts.append({
                        'account_code': account_code,
                        'account_desc': account_desc,
                        'debit': account.get('Debit Balance', 0),
                        'credit': account.get('Credit Balance', 0),
                        'net_balance': account.get('Net Balance', 0)
                    })
            
            # Generate financial statements
            financial_statements = self._generate_financial_statements(mapped_accounts)
            
            # Calculate detailed mapping statistics
            total_accounts = len(balance_sheet_data)
            mapped_count = len(mapped_accounts)
            unmapped_count = len(unmapped_accounts)
            
            # Calculate confidence statistics
            confidence_scores = [acc.get('confidence', 0) for acc in mapped_accounts]
            avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
            high_confidence_count = len([c for c in confidence_scores if c > 0.8])
            medium_confidence_count = len([c for c in confidence_scores if 0.5 <= c <= 0.8])
            low_confidence_count = len([c for c in confidence_scores if c < 0.5])
            
            # Get session structure info
            session_data = self.get_session_data(session_id)
            detected_structure = session_data.get('metadata', {}).get('structure_info', {}) if session_data.get('success') else {}
            
            # Update session with processing results
            processing_results = {
                'mapped_accounts': mapped_count,
                'unmapped_accounts': unmapped_count,
                'total_accounts': total_accounts,
                'mapping_confidence': avg_confidence,
                'confidence_breakdown': {
                    'high_confidence': high_confidence_count,
                    'medium_confidence': medium_confidence_count,
                    'low_confidence': low_confidence_count
                },
                'financial_statements': financial_statements,
                'processed_at': datetime.now().isoformat()
            }
            
            # Update session metadata
            self._update_session_processing_results(session_id, processing_results)
            
            return {
                'success': True,
                'session_id': session_id,
                'mapping_results': processing_results,
                'mapped_accounts': mapped_accounts,
                'unmapped_accounts': unmapped_accounts,
                'total_accounts': total_accounts,
                'mapping_confidence': avg_confidence,
                'confidence_breakdown': {
                    'high_confidence': high_confidence_count,
                    'medium_confidence': medium_confidence_count,
                    'low_confidence': low_confidence_count
                },
                'detected_structure': detected_structure,
                'financial_statements': financial_statements
            }
            
        except Exception as e:
            print(f"Error in process_grap_mapping: {str(e)}")
            return {'success': False, 'error': f'GRAP mapping failed: {str(e)}'}
    
    def _generate_financial_statements(self, mapped_accounts: List[Dict]) -> Dict:
        """Generate financial statements from mapped accounts"""
        try:
            # Group accounts by GRAP categories
            assets = []
            liabilities = []
            revenue = []
            expenses = []
            equity = []
            
            for account in mapped_accounts:
                grap_code = account.get('grap_code', '')
                net_balance = account.get('net_balance', 0)
                
                if grap_code.startswith('CA') or grap_code.startswith('NCA'):
                    assets.append(account)
                elif grap_code.startswith('CL') or grap_code.startswith('NCL'):
                    liabilities.append(account)
                elif grap_code.startswith('RV'):
                    revenue.append(account)
                elif grap_code.startswith('EX'):
                    expenses.append(account)
                elif grap_code.startswith('EQ'):
                    equity.append(account)
            
            # Calculate totals
            total_assets = sum(acc.get('net_balance', 0) for acc in assets)
            total_liabilities = sum(acc.get('net_balance', 0) for acc in liabilities)
            total_revenue = sum(acc.get('net_balance', 0) for acc in revenue)
            total_expenses = sum(acc.get('net_balance', 0) for acc in expenses)
            total_equity = sum(acc.get('net_balance', 0) for acc in equity)
            
            return {
                'statement_of_financial_position': {
                    'assets': {
                        'accounts': assets,
                        'total': total_assets
                    },
                    'liabilities': {
                        'accounts': liabilities,
                        'total': total_liabilities
                    },
                    'equity': {
                        'accounts': equity,
                        'total': total_equity
                    }
                },
                'statement_of_financial_performance': {
                    'revenue': {
                        'accounts': revenue,
                        'total': total_revenue
                    },
                    'expenses': {
                        'accounts': expenses,
                        'total': total_expenses
                    },
                    'surplus': total_revenue - total_expenses
                }
            }
        except Exception as e:
            print(f"Error generating financial statements: {str(e)}")
            return {}
    
    def _update_session_processing_results(self, session_id: str, results: Dict):
        """Update session with processing results"""
        try:
            session = self.model.get_session(session_id)
            if session:
                session.metadata.update(results)
                session.processed_at = datetime.now()
                self.model.update_session_status(session_id, session.status, session.metadata)
                
                # If mapping is complete, create submission workflow entry and update status
                if results.get('mapped_accounts', 0) > 0:
                    self._create_submission_workflow_entry(session_id, results)
                    # Update session status to reflect mapping completion
                    self.model.update_session_status(session_id, 'mapped', session.metadata)
        except Exception as e:
            print(f"Error updating session results: {str(e)}")
    
    def _create_submission_workflow_entry(self, session_id: str, processing_results: Dict):
        """Create submission workflow entry when mapping is complete"""
        try:
            from models.workflow_models import submission_workflow_model
            
            session = self.model.get_session(session_id)
            if not session:
                return
            
            # Check if submission already exists
            existing_submission = submission_workflow_model.get_submission(session_id)
            if existing_submission['success']:
                return  # Submission already exists
            
            # Prepare submission data
            submission_data = {
                'session_id': session_id,
                'user_id': session.user_id,
                'filename': session.filename,
                'original_filename': session.original_filename,
                'total_accounts': processing_results.get('total_accounts', 0),
                'mapped_accounts': processing_results.get('mapped_accounts', 0),
                'unmapped_accounts': processing_results.get('unmapped_accounts', 0),
                'total_assets': processing_results.get('total_assets', 0),
                'total_liabilities': processing_results.get('total_liabilities', 0),
                'grap_categories_used': processing_results.get('grap_categories_used', 0),
                'mapping_completeness': f"{processing_results.get('mapping_completeness', 0)}%",
                'upload_date': session.created_at.isoformat() if session.created_at else None,
                'mapping_date': datetime.now().isoformat()
            }
            
            # Create submission in workflow
            submission_workflow_model.create_submission(submission_data)
            logger.info(WorkflowLogMessages.WORKFLOW_ENTRY_CREATED.format(session_id=session_id))
            
        except Exception as e:
            logger.error(WorkflowLogMessages.WORKFLOW_ENTRY_ERROR.format(error=str(e)))

    def get_pending_submissions(self) -> List[Dict]:
        """Get all submissions pending finance clerk review"""
        try:
            from models.workflow_models import submission_workflow_model
            pending_submissions = submission_workflow_model.get_pending_submissions()
            
            # Enhance with session data
            enhanced_submissions = []
            for submission in pending_submissions:
                # Get session data for additional info
                session = self.model.get_session(submission['session_id'])
                if session:
                    enhanced_submission = {
                        **submission,
                        'filename': session.original_filename or session.filename,
                        'file_type': session.file_type,
                        'file_format': session.file_format,
                        'created_at': session.created_at.isoformat() if session.created_at else None,
                        'session_status': session.status,
                        'total_rows': session.total_rows,
                        'total_columns': session.total_columns
                    }
                    enhanced_submissions.append(enhanced_submission)
            
            return enhanced_submissions
            
        except Exception as e:
            logger.error(WorkflowLogMessages.PENDING_SUBMISSIONS_ERROR.format(error=str(e)))
            return []

    def get_session_summary(self, session_id: str) -> Dict:
        """Get detailed session summary with financial data"""
        try:
            session = self.model.get_session(session_id)
            if not session:
                return {'error': 'Session not found'}
            
            # Get session data for financial summary
            session_data = self.get_session_data(session_id)
            base_summary = {
                'session_id': session.id,
                'user_id': session.user_id,
                'filename': session.filename,
                'status': session.status,
                'total_rows': session.total_rows,
                'total_columns': session.total_columns,
                'file_size_bytes': session.file_size_bytes,
                'file_type': session.file_type,
                'file_format': session.file_format,
                'created_at': session.created_at.isoformat() if session.created_at else None,
                'updated_at': session.updated_at.isoformat() if session.updated_at else None,
                'processed_at': session.processed_at.isoformat() if session.processed_at else None,
                'metadata': session.metadata,
                'data_rows_count': session.total_rows if session.total_rows else 0,
                'columns_count': session.total_columns if session.total_columns else 0,
                'processing_log': session.processing_log[-5:] if session.processing_log else []
            }
            
            # Add accounts counts regardless of mapping status
            base_summary['mapped_accounts_count'] = 0
            base_summary['total_accounts_count'] = session.total_rows if session.total_rows else 0
            
            # First check for submission workflow data (preferred source)
            try:
                from models.workflow_models import submission_workflow_model
                submission_result = submission_workflow_model.get_submission(session_id)
                if submission_result['success']:
                    submission = submission_result['submission']
                    base_summary['mapped_accounts_count'] = submission.get('mapped_accounts', 0)
                    base_summary['total_accounts_count'] = submission.get('total_accounts', session.total_rows if session.total_rows else 0)
            except:
                pass  # Fallback to other methods if workflow model fails
            
            # If no workflow data, check for mapping results in processing_results metadata
            if base_summary['mapped_accounts_count'] == 0:
                processing_results = session.metadata.get('processing_results', {})
                if processing_results:
                    # Get mapped accounts count from processing results
                    base_summary['mapped_accounts_count'] = processing_results.get('mapped_accounts', 0)
            
            # If still no mapped accounts, check direct metadata fields
            if base_summary['mapped_accounts_count'] == 0:
                # Check direct metadata fields (where the actual data is stored)
                direct_mapped = session.metadata.get('mapped_accounts')
                if direct_mapped is not None:
                    base_summary['mapped_accounts_count'] = direct_mapped
                
                # Also update total accounts from direct metadata
                direct_total = session.metadata.get('total_accounts')
                if direct_total is not None:
                    base_summary['total_accounts_count'] = direct_total
            
            # If session has GRAP mapping results (legacy), add financial summary and update mapped count
            if session_data and session_data.get('success') and session.metadata.get('grap_mapping'):
                try:
                    # Get mapped accounts from metadata (legacy format)
                    grap_mapping = session.metadata.get('grap_mapping', {})
                    mapped_accounts = grap_mapping.get('mapped_accounts', [])
                    
                    # Update mapped accounts count (override if legacy format exists)
                    base_summary['mapped_accounts_count'] = len(mapped_accounts) if mapped_accounts else 0
                    
                    if mapped_accounts:
                        # Generate financial statements
                        financial_statements = self._generate_financial_statements(mapped_accounts)
                        
                        if financial_statements:
                            # Extract totals for frontend
                            sfp = financial_statements.get('statement_of_financial_position', {})
                            sfp_performance = financial_statements.get('statement_of_financial_performance', {})
                            
                            total_assets = sfp.get('assets', {}).get('total', 0)
                            total_liabilities = sfp.get('liabilities', {}).get('total', 0)
                            total_equity = sfp.get('equity', {}).get('total', 0)
                            total_revenue = sfp_performance.get('revenue', {}).get('total', 0)
                            total_expenses = sfp_performance.get('expenses', {}).get('total', 0)
                            surplus = sfp_performance.get('surplus', 0)
                            
                            # Calculate net assets
                            net_assets = total_assets - total_liabilities
                            
                            # Calculate basic ratios
                            ratios = {}
                            if total_liabilities > 0:
                                ratios['debt_to_equity'] = total_liabilities / max(total_equity, 1)
                            if total_assets > 0:
                                ratios['return_on_assets'] = surplus / max(total_assets, 1)
                            if total_liabilities > 0:
                                ratios['current_ratio'] = total_assets / total_liabilities
                            if total_revenue > 0:
                                ratios['operating_margin'] = (surplus / total_revenue) * 100
                            
                            # Add financial summary to base summary
                            base_summary.update({
                                'total_assets': total_assets,
                                'total_liabilities': total_liabilities,
                                'net_assets': net_assets,
                                'total_equity': total_equity,
                                'total_revenue': total_revenue,
                                'total_expenses': total_expenses,
                                'surplus_deficit': surplus,
                                'ratios': ratios,
                                'financial_statements': financial_statements
                            })
                except Exception as e:
                    print(f"Error generating financial summary: {str(e)}")
                    # Return base summary without financial data if there's an error
                    pass
            
            return base_summary
        except Exception as e:
            return {'error': str(e)}

    def update_session_metadata(self, session_id: str, metadata: Dict):
        """Update session metadata with mapping progress"""
        try:
            session = self.model.get_session(session_id)
            if not session:
                return {'success': False, 'error': 'Session not found'}
            
            # Update session metadata
            updated_metadata = session.get('metadata', {})
            updated_metadata.update(metadata)
            
            # Save to database
            success = self.model.update_session(session_id, {
                'metadata': updated_metadata,
                'updated_at': datetime.now().isoformat()
            })
            
            if success:
                return {'success': True, 'message': 'Session metadata updated successfully'}
            else:
                return {'success': False, 'error': 'Failed to update session metadata'}
                
        except Exception as e:
            print(f"Error updating session metadata: {str(e)}")
            return {'success': False, 'error': f'Failed to update session metadata: {str(e)}'}


# Global instance
flexible_balance_sheet_service = FlexibleBalanceSheetService()
