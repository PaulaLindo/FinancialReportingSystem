"""
Varydian Financial Reporting System - Fund Accounting Service
GRAP 18 compliant multi-dimensional fund accounting service
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import pandas as pd
from models.fund_accounting_models import FundAccountingModel

class FundAccountingService:
    """Service for fund accounting and segment reporting"""
    
    def __init__(self):
        self.fund_model = FundAccountingModel()
        self.tagged_data = {}
        self.segment_reports = {}
        
    def apply_fund_tags(self, balance_sheet_path: str, 
                     auto_tag: bool = True, user_id: str = 'system') -> Dict[str, Any]:
        """Apply fund tags to balance sheet data"""
        try:
            # Import balance sheet
            df = pd.read_excel(balance_sheet_path) if balance_sheet_path.endswith('.xlsx') else pd.read_csv(balance_sheet_path)
            
            # Apply fund tags
            if auto_tag:
                tagged_data = self.fund_model.apply_fund_tags(df)
            else:
                tagged_data = df.copy()
            
            # Store tagged data
            data_id = f"FT_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.tagged_data[data_id] = {
                'data_id': data_id,
                'original_filename': balance_sheet_path.split('\\')[-1],
                'created_at': datetime.now().isoformat(),
                'created_by': user_id,
                'tagged_data': tagged_data.to_dict('records'),
                'auto_tagged': auto_tag,
                'fund_analysis': self.fund_model._analyze_fund_segments(tagged_data),
                'department_analysis': self.fund_model._analyze_department_segments(tagged_data),
                'function_analysis': self.fund_model._analyze_function_segments(tagged_data),
                'cross_segment_analysis': self.fund_model._analyze_cross_segments(tagged_data),
                'compliance_metrics': self.fund_model._calculate_segment_compliance(tagged_data)
            }
            
            return {
                'success': True,
                'data_id': data_id,
                'tagged_records': len(tagged_data),
                'message': f'Fund tags applied to {len(tagged_data)} records'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to apply fund tags: {str(e)}'
            }
    
    def manual_tag_records(self, data_id: str, record_updates: List[Dict[str, Any]], 
                      user_id: str = 'system') -> Dict[str, Any]:
        """Manually tag specific records"""
        try:
            if data_id not in self.tagged_data:
                return {
                    'success': False,
                    'error': f'Data ID {data_id} not found'
                }
            
            original_data = self.tagged_data[data_id]['tagged_data']
            updated_data = []
            
            # Update specific records
            for update in record_updates:
                record_index = update.get('record_index', -1)
                if record_index >= 0 and record_index < len(original_data):
                    record = original_data[record_index].copy()
                    
                    # Update fund tags
                    if 'fund_code' in update:
                        record['fund_code'] = update['fund_code']
                        fund_info = self.fund_model.fund_structure.get(update['fund_code'])
                        if fund_info:
                            record['fund_name'] = fund_info['name']
                            record['fund_restriction'] = fund_info['restrictions']
                            record['fund_reporting_required'] = fund_info['reporting_required']
                            record['fund_audit_required'] = fund_info['audit_required']
                    
                    # Update department tags
                    if 'department_code' in update:
                        record['department_code'] = update['department_code']
                        dept_info = self.fund_model.department_structure.get(update['department_code'])
                        if dept_info:
                            record['department_name'] = dept_info['name']
                            record['cost_center'] = dept_info['cost_center']
                    
                    # Update function tags
                    if 'function_code' in update:
                        record['function_code'] = update['function_code']
                        func_info = self.fund_model.function_structure.get(update['function_code'])
                        if func_info:
                            record['function_name'] = func_info['name']
                            record['function_nature'] = func_info['nature']
                    
                    updated_data.append(record)
            
            # Update stored data
            self.tagged_data[data_id]['tagged_data'] = updated_data
            self.tagged_data[data_id]['manual_updates'] = {
                'updated_at': datetime.now().isoformat(),
                'updated_by': user_id,
                'updates_count': len(record_updates)
            }
            
            return {
                'success': True,
                'data_id': data_id,
                'updated_records': len(updated_data),
                'message': f'Manually tagged {len(updated_data)} records'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to manually tag records: {str(e)}'
            }
    
    def generate_segment_report(self, data_id: str, report_type: str = 'comprehensive',
                           user_id: str = 'system') -> Dict[str, Any]:
        """Generate GRAP 18 segment report"""
        try:
            if data_id not in self.tagged_data:
                return {
                    'success': False,
                    'error': f'Data ID {data_id} not found'
                }
            
            tagged_data = self.tagged_data[data_id]['tagged_data']
            
            # Convert to DataFrame for analysis
            df = pd.DataFrame(tagged_data)
            
            # Generate segment report
            segment_report = self.fund_model.generate_segment_report(df)
            
            # Store report
            report_id = f"SEG_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.segment_reports[report_id] = {
                'report_id': report_id,
                'data_id': data_id,
                'report_type': report_type,
                'generated_at': datetime.now().isoformat(),
                'generated_by': user_id,
                'segment_report': segment_report
            }
            
            return {
                'success': True,
                'report_id': report_id,
                'report_type': report_type,
                'segment_report': segment_report,
                'message': f'Segment report {report_type} generated for data {data_id}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to generate segment report: {str(e)}'
            }
    
    def get_fund_analysis(self, data_id: str) -> Dict[str, Any]:
        """Get fund analysis for tagged data"""
        try:
            if data_id not in self.tagged_data:
                return {
                    'success': False,
                    'error': f'Data ID {data_id} not found'
                }
            
            fund_analysis = self.tagged_data[data_id].get('fund_analysis', {})
            
            return {
                'success': True,
                'data_id': data_id,
                'fund_analysis': fund_analysis,
                'message': f'Fund analysis retrieved for data {data_id}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get fund analysis: {str(e)}'
            }
    
    def get_department_analysis(self, data_id: str) -> Dict[str, Any]:
        """Get department analysis for tagged data"""
        try:
            if data_id not in self.tagged_data:
                return {
                    'success': False,
                    'error': f'Data ID {data_id} not found'
                }
            
            department_analysis = self.tagged_data[data_id].get('department_analysis', {})
            
            return {
                'success': True,
                'data_id': data_id,
                'department_analysis': department_analysis,
                'message': f'Department analysis retrieved for data {data_id}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get department analysis: {str(e)}'
            }
    
    def get_function_analysis(self, data_id: str) -> Dict[str, Any]:
        """Get function analysis for tagged data"""
        try:
            if data_id not in self.tagged_data:
                return {
                    'success': False,
                    'error': f'Data ID {data_id} not found'
                }
            
            function_analysis = self.tagged_data[data_id].get('function_analysis', {})
            
            return {
                'success': True,
                'data_id': data_id_data_id,
                'function_analysis': function_analysis,
                'message': f'Function analysis retrieved for data {data_id}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get function analysis: {str(e)}'
            }
    
    def get_cross_segment_analysis(self, data_id: str) -> Dict[str, Any]:
        """Get cross-segment analysis for tagged data"""
        try:
            if data_id not in self.tagged_data:
                return {
                    'success': False,
                    'error': f'Data ID {data_id} not found'
                }
            
            cross_analysis = self.tagged_data[data_id].get('cross_segment_analysis', {})
            
            return {
                'success': True,
                'data_id': data_id,
                'cross_segment_analysis': cross_analysis,
                'message': f'Cross-segment analysis retrieved for data {data_id}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get cross-segment analysis: {str(e)}'
            }
    
    def get_compliance_metrics(self, data_id: str) -> Dict[str, Any]:
        """Get compliance metrics for tagged data"""
        try:
            if data_id not in self.tagged_data:
                return {
                    'success': False,
                    'error': f'Data ID {data_id} not found'
                }
            
            compliance_metrics = self.tagged_data[data_id].get('compliance_metrics', {})
            
            return {
                'success': True,
                'data_id': data_id,
                'compliance_metrics': compliance_metrics,
                'message': f'Compliance metrics retrieved for data {data_id}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to get compliance metrics: {str(e)}'
            }
    
    def export_tagged_data(self, data_id: str, format_type: str = 'excel') -> Dict[str, Any]:
        """Export tagged data in specified format"""
        try:
            if data_id not in self.tagged_data:
                return {
                    'success': False,
                    'error': f'Data ID {data_id} not found'
                }
            
            tagged_data = self.tagged_data[data_id]['tagged_data']
            df = pd.DataFrame(tagged_data)
            
            if format_type == 'excel':
                # Create Excel file with fund tags
                output_file = f"outputs/fund_tagged_data_{data_id}.xlsx"
                
                # Reorder columns for better readability
                column_order = [
                    'Account Code', 'Account Description', 'Net Balance',
                    'fund_code', 'fund_name', 'fund_restriction',
                    'department_code', 'department_name', 'cost_center',
                    'function_code', 'function_name', 'function_nature'
                ]
                
                df_reordered = df.reindex(columns=column_order)
                df_reordered.to_excel(output_file, index=False)
                
                return {
                    'success': True,
                    'data_id': data_id,
                    'format': format_type,
                    'output_file': output_file,
                    'records_exported': len(df_reordered),
                    'message': f'Tagged data exported to {output_file}'
                }
            
            elif format_type == 'csv':
                output_file = f"outputs/fund_tagged_data_{data_id}.csv"
                df.to_csv(output_file, index=False)
                
                return {
                    'success': True,
                    'data_id': data_id,
                    'format': format_type,
                    'output_file': output_file,
                    'records_exported': len(df),
                    'message': f'Tagged data exported to {output_file}'
                }
            
            else:
                return {
                    'success': False,
                    'error': f'Format {format_type} not yet implemented'
                }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to export tagged data: {str(e)}'
            }
    
    def list_tagged_datasets(self) -> Dict[str, Any]:
        """List all tagged datasets"""
        try:
            datasets = []
            
            for data_id, data_info in self.tagged_data.items():
                datasets.append({
                    'data_id': data_id,
                    'original_filename': data_info.get('original_filename', 'Unknown'),
                    'created_at': data_info.get('created_at', ''),
                    'created_by': data_info.get('created_by', ''),
                    'auto_tagged': data_info.get('auto_tagged', False),
                    'total_records': len(data_info.get('tagged_data', [])),
                    'fund_types_count': len(set([r.get('fund_code', '') for r in data_info.get('tagged_data', [])])),
                    'department_types_count': len(set([r.get('department_code', '') for r in data_info.get('tagged_data', [])])),
                    'function_types_count': len(set([r.get('function_code', '') for r in data_info.get('tagged_data', [])])),
                    'compliance_score': data_info.get('compliance_metrics', {}).get('compliance_score', 0),
                    'risk_level': data_info.get('compliance_metrics', {}).get('risk_level', 'LOW')
                })
            
            return {
                'success': True,
                'datasets': datasets,
                'total_datasets': len(datasets),
                'message': f'Listed {len(datasets)} tagged datasets'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to list tagged datasets: {str(e)}'
            }
    
    def delete_tagged_dataset(self, data_id: str, reason: str = '', user_id: str = 'system') -> Dict[str, Any]:
        """Delete tagged dataset (soft delete)"""
        try:
            if data_id not in self.tagged_data:
                return {
                    'success': False,
                    'error': f'Data ID {data_id} not found'
                }
            
            if not reason or not reason.strip():
                return {
                    'success': False,
                    'error': 'Reason for deletion is required'
                }
            
            # Soft delete - mark as deleted but keep for audit trail
            self.tagged_data[data_id]['status'] = 'deleted'
            self.tagged_data[data_id]['deleted_at'] = datetime.now().isoformat()
            self.tagged_data[data_id]['deleted_by'] = user_id
            self.tagged_data[data_id]['deletion_reason'] = reason.strip()
            
            return {
                'success': True,
                'data_id': data_id,
                'message': f'Tagged dataset {data_id} marked as deleted'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to delete tagged dataset: {str(e)}'
            }
