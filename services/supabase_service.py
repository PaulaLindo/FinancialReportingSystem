"""
Varydian Financial Reporting System - Secure Supabase Service
Private storage bucket with signed URLs for maximum security
"""

import os
import json
import tempfile
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
from supabase import create_client, Client
from utils.constants import ALLOWED_EXTENSIONS

class SupabaseServiceSecure:
    """Secure Supabase integration with private storage and signed URLs"""
    
    def __init__(self):
        """Initialize Supabase client with anon key only"""
        # Load environment variables if not already loaded
        from dotenv import load_dotenv
        load_dotenv()
        
        self.supabase_url = os.environ.get('SUPABASE_URL')
        self.supabase_anon_key = os.environ.get('SUPABASE_ANON_KEY')
        
        if not self.supabase_url or not self.supabase_anon_key:
            raise ValueError("Supabase credentials not found. Check SUPABASE_URL and SUPABASE_ANON_KEY in .env file")
        
        try:
            self.client = create_client(self.supabase_url, self.supabase_anon_key)
            print("✅ Supabase service initialized with anon key (secure, RLS-compliant)")
        except Exception as e:
            raise ValueError(f"Failed to initialize Supabase client with anon key: {e}")
        self.storage_bucket = 'financial-reports'
    
    def upload_file_to_storage(self, file_data: bytes, file_path: str) -> Dict[str, Any]:
        """Upload file to private storage bucket"""
        try:
            # Upload to private storage
            upload_result = self.client.storage.from_(self.storage_bucket).upload(
                file_path, file_data
            )
            
            return {
                'success': True,
                'file_path': file_path,
                'note': 'File uploaded to private storage'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def generate_signed_url(self, file_path: str, expires_in_hours: int = 24) -> str:
        """Generate signed URL for private file access"""
        try:
            # Generate signed URL that expires
            expires_in_seconds = expires_in_hours * 3600
            signed_url = self.client.storage.from_(self.storage_bucket).create_signed_url(
                file_path, expires_in_seconds
            )
            return signed_url['signedURL']
        except Exception as e:
            return None
    
    def save_balance_sheet(self, file_data: bytes, filename: str, user_id: str) -> Dict[str, Any]:
        """Save balance sheet to private storage"""
        try:
            # Create storage path
            storage_path = f"balance-sheets/{user_id}/{filename}"
            
            # Upload to private storage
            upload_result = self.upload_file_to_storage(file_data, storage_path)
            if not upload_result['success']:
                return upload_result
            
            # Save record to database
            record = {
                'user_id': user_id,
                'filename': filename,
                'storage_path': storage_path,
                'public_url': '',  # Empty for private storage
                'file_size': len(file_data),
                'uploaded_at': datetime.utcnow().isoformat(),
                'status': 'uploaded'
            }
            
            db_result = self.client.table('balance_sheets').insert(record).execute()
            
            return {
                'success': True,
                'record_id': db_result.data[0]['id'],
                'storage_path': storage_path,
                'note': 'File saved to private storage - use signed URLs for access'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_balance_sheet_file(self, record_id: str, user_id: str) -> Dict[str, Any]:
        """Get balance sheet file with signed URL"""
        try:
            # Get record from database
            record = self.client.table('balance_sheets').select('*').eq('id', record_id).execute()
            
            if not record.data or record.data[0]['user_id'] != user_id:
                return {'success': False, 'error': 'File not found or unauthorized'}
            
            file_record = record.data[0]
            
            # Generate signed URL for file access
            signed_url = self.generate_signed_url(file_record['storage_path'])
            
            return {
                'success': True,
                'filename': file_record['filename'],
                'signed_url': signed_url,
                'expires_in_hours': 24,
                'file_size': file_record['file_size']
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def save_financial_results(self, results: Dict[str, Any], balance_sheet_id: str, user_id: str) -> Dict[str, Any]:
        """Save financial statement results to database"""
        try:
            record = {
                'balance_sheet_id': balance_sheet_id,
                'user_id': user_id,
                'results': results,
                'generated_at': datetime.utcnow().isoformat(),
                'status': 'completed'
            }
            
            result = self.client.table('financial_results').insert(record).execute()
            
            return {
                'success': True,
                'record_id': result.data[0]['id']
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def save_pdf_report(self, pdf_data: bytes, filename: str, results_id: str, user_id: str) -> Dict[str, Any]:
        """Save PDF report to private storage"""
        try:
            # Create storage path
            storage_path = f"pdf-reports/{user_id}/{filename}"
            
            # Upload to private storage
            upload_result = self.upload_file_to_storage(pdf_data, storage_path)
            if not upload_result['success']:
                return upload_result
            
            # Save record to database
            record = {
                'results_id': results_id,
                'user_id': user_id,
                'filename': filename,
                'storage_path': storage_path,
                'public_url': '',  # Empty for private storage
                'file_size': len(pdf_data),
                'generated_at': datetime.utcnow().isoformat(),
                'status': 'completed'
            }
            
            db_result = self.client.table('pdf_reports').insert(record).execute()
            
            return {
                'success': True,
                'record_id': db_result.data[0]['id'],
                'storage_path': storage_path,
                'note': 'PDF saved to private storage - use signed URLs for access'
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_pdf_report(self, record_id: str, user_id: str) -> Dict[str, Any]:
        """Get PDF report with signed URL"""
        try:
            # Get PDF record
            pdf_result = self.client.table('pdf_reports').select('*').eq('results_id', record_id).execute()
            
            if not pdf_result.data or pdf_result.data[0]['user_id'] != user_id:
                return {'success': False, 'error': 'PDF not found or unauthorized'}
            
            pdf_record = pdf_result.data[0]
            
            # Generate signed URL for PDF access
            signed_url = self.generate_signed_url(pdf_record['storage_path'])
            
            return {
                'success': True,
                'filename': pdf_record['filename'],
                'signed_url': signed_url,
                'expires_in_hours': 24,
                'file_size': pdf_record['file_size']
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_user_reports(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all reports for a user (without file URLs for security)"""
        try:
            result = self.client.table('financial_results').select(
                '*',
                count='exact'
            ).eq('user_id', user_id).order('generated_at', desc=True).execute()
            
            # Remove detailed results for security in list view
            reports = []
            for report in result.data:
                report_copy = report.copy()
                report_copy['results'] = {  # Keep only summary info
                    'summary': report['results'].get('summary', {}),
                    'processed_at': report['results'].get('processed_at')
                }
                reports.append(report_copy)
            
            return reports
            
        except Exception as e:
            return []
    
    def delete_report(self, report_id: str, user_id: str) -> Dict[str, Any]:
        """Delete a report and associated files"""
        try:
            # Get report data
            report = self.client.table('financial_results').select('*').eq('id', report_id).execute()
            
            if not report.data or report.data[0]['user_id'] != user_id:
                return {'success': False, 'error': 'Report not found or unauthorized'}
            
            # Delete associated PDF from storage
            pdf_result = self.client.table('pdf_reports').select('*').eq('results_id', report_id).execute()
            if pdf_result.data:
                pdf_path = pdf_result.data[0]['storage_path']
                self.client.storage.from_(self.storage_bucket).remove([pdf_path])
                self.client.table('pdf_reports').delete().eq('results_id', report_id).execute()
            
            # Delete financial results
            self.client.table('financial_results').delete().eq('id', report_id).execute()
            
            return {'success': True}
            
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_storage_stats(self, user_id: str) -> Dict[str, Any]:
        """Get storage statistics for a user"""
        try:
            # Get balance sheets
            tb_result = self.client.table('balance_sheets').select('file_size').eq('user_id', user_id).execute()
            tb_size = sum(r['file_size'] for r in tb_result.data) if tb_result.data else 0
            
            # Get PDF reports
            pdf_result = self.client.table('pdf_reports').select('file_size').eq('user_id', user_id).execute()
            pdf_size = sum(r['file_size'] for r in pdf_result.data) if pdf_result.data else 0
            
            return {
                'total_files': len(tb_result.data or []) + len(pdf_result.data or []),
                'total_size_mb': round((tb_size + pdf_size) / (1024 * 1024), 2),
                'balance_sheet_count': len(tb_result.data or []),
                'pdf_report_count': len(pdf_result.data or []),
                'storage_type': 'private_with_signed_urls'
            }
            
        except Exception as e:
            return {'error': str(e)}

# Secure service instance - initialize lazily to handle missing env vars
supabase_service_secure = None

def get_supabase_service():
    """Get Supabase service instance, initializing if needed"""
    if 'supabase_service_secure' not in globals():
        globals()['supabase_service_secure'] = None
    
    if globals()['supabase_service_secure'] is None:
        try:
            globals()['supabase_service_secure'] = SupabaseServiceSecure()
        except ValueError as e:
            raise ValueError(f"Supabase service initialization failed: {e}")
    
    return globals()['supabase_service_secure']
