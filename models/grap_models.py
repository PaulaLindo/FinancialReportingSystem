"""
SADPMR GRAP Mapping Engine
Phase 2: Enhanced Financial Statement Generation with PDF Export
"""

import pandas as pd
import numpy as np
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


class GRAPMappingEngine:
    """Core GRAP mapping engine for financial statement generation"""
    
    def __init__(self):
        self.mapping_schema = self._load_mapping_schema()
        self.grap_line_items = self._load_grap_structure()
        
    def _load_mapping_schema(self):
        """Load account to GRAP mapping schema"""
        mapping = {
            # Assets
            '1000': {'grap_code': 'CA-001', 'grap_item': 'Cash and Cash Equivalents'},
            '1100': {'grap_code': 'CA-001', 'grap_item': 'Cash and Cash Equivalents'},
            '1200': {'grap_code': 'CA-002', 'grap_item': 'Receivables from Exchange Transactions'},
            '1210': {'grap_code': 'CA-002', 'grap_item': 'Receivables from Exchange Transactions'},
            '1250': {'grap_code': 'CA-002', 'grap_item': 'Receivables from Exchange Transactions'},
            '1300': {'grap_code': 'CA-004', 'grap_item': 'Inventories'},
            '1400': {'grap_code': 'CA-003', 'grap_item': 'Receivables from Non-Exchange Transactions'},
            '1500': {'grap_code': 'CA-005', 'grap_item': 'Prepayments'},
            '1600': {'grap_code': 'NCA-001', 'grap_item': 'Property, Plant and Equipment'},
            '1700': {'grap_code': 'NCA-002', 'grap_item': 'Intangible Assets'},
            '1800': {'grap_code': 'NCA-003', 'grap_item': 'Investments'},
            
            # Liabilities
            '2000': {'grap_code': 'CL-001', 'grap_item': 'Payables from Exchange Transactions'},
            '2100': {'grap_code': 'CL-002', 'grap_item': 'Employee Benefit Obligations (Current)'},
            '2200': {'grap_code': 'CL-003', 'grap_item': 'Provisions (Current)'},
            '2300': {'grap_code': 'NCL-001', 'grap_item': 'Employee Benefit Obligations (Non-Current)'},
            '2400': {'grap_code': 'NCL-002', 'grap_item': 'Provisions (Non-Current)'},
            
            # Equity
            '3000': {'grap_code': 'NA-001', 'grap_item': 'Accumulated Surplus/(Deficit)'},
            
            # Revenue
            '4000': {'grap_code': 'REV-002', 'grap_item': 'Revenue from Non-Exchange Transactions'},
            '4100': {'grap_code': 'REV-001', 'grap_item': 'Revenue from Exchange Transactions'},
            '4200': {'grap_code': 'REV-001', 'grap_item': 'Revenue from Exchange Transactions'},
            
            # Expenses
            '5000': {'grap_code': 'EXP-001', 'grap_item': 'Employee Costs'},
            '5100': {'grap_code': 'EXP-001', 'grap_item': 'Employee Costs'},
            '5200': {'grap_code': 'EXP-001', 'grap_item': 'Employee Costs'},
            '6000': {'grap_code': 'EXP-003', 'grap_item': 'General Expenses'},
            '6100': {'grap_code': 'EXP-002', 'grap_item': 'Depreciation and Amortisation'},
            '6200': {'grap_code': 'EXP-004', 'grap_item': 'Finance Costs'},
            '6300': {'grap_code': 'EXP-003', 'grap_item': 'General Expenses'},
        }
        return pd.DataFrame.from_dict(mapping, orient='index').reset_index()
    
    def _load_grap_structure(self):
        """Load GRAP financial statement structure"""
        return {
            'SOFP_ASSETS': ['CA-001', 'CA-002', 'CA-003', 'CA-004', 'CA-005', 
                           'NCA-001', 'NCA-002', 'NCA-003'],
            'SOFP_LIABILITIES': ['CL-001', 'CL-002', 'CL-003', 
                                'NCL-001', 'NCL-002', 'NCL-003'],
            'SOFP_NET_ASSETS': ['NA-001'],
            'SOFE_REVENUE': ['REV-001', 'REV-002'],
            'SOFE_EXPENSES': ['EXP-001', 'EXP-002', 'EXP-003', 'EXP-004']
        }
    
    def import_trial_balance(self, file_path):
        """Import and validate trial balance from Excel/CSV"""
        df = pd.read_excel(file_path) if file_path.endswith('.xlsx') else pd.read_csv(file_path)
        
        # Standardize column names
        df.columns = df.columns.str.strip()
        
        # Handle column name variations
        col_mapping = {
            'Acc Code': 'Account Code',
            'AccCode': 'Account Code',
            'Account': 'Account Code',
            'Description': 'Account Description',
            'Debit': 'Debit Balance',
            'Credit': 'Credit Balance'
        }
        
        df.rename(columns=col_mapping, inplace=True)
        
        # Calculate net balance
        if 'Net Balance' not in df.columns:
            df['Net Balance'] = df['Debit Balance'] - df['Credit Balance']
        
        return df
    
    def map_to_grap(self, trial_balance_df):
        """Map trial balance accounts to GRAP line items"""
        trial_balance_df['Account Code'] = trial_balance_df['Account Code'].astype(str)
        self.mapping_schema['index'] = self.mapping_schema['index'].astype(str)
        
        mapped_df = pd.merge(
            trial_balance_df,
            self.mapping_schema,
            left_on='Account Code',
            right_on='index',
            how='left'
        )
        
        return mapped_df
    
    def generate_statement_of_financial_position(self, mapped_df):
        """Generate Statement of Financial Position (Balance Sheet)"""
        sofp = mapped_df.groupby(['grap_code', 'grap_item'])['Net Balance'].sum().reset_index()
        sofp.columns = ['GRAP Code', 'Line Item', 'Amount']
        
        # Separate components
        assets = sofp[sofp['GRAP Code'].str.contains('CA-|NCA-', na=False)].copy()
        liabilities = sofp[sofp['GRAP Code'].str.contains('CL-|NCL-', na=False)].copy()
        net_assets = sofp[sofp['GRAP Code'].str.contains('NA-', na=False)].copy()
        
        # Convert to positive values for presentation
        liabilities['Amount'] = liabilities['Amount'].abs()
        net_assets['Amount'] = net_assets['Amount'].abs()
        
        return {'assets': assets, 'liabilities': liabilities, 'net_assets': net_assets}
    
    def generate_statement_of_performance(self, mapped_df):
        """Generate Statement of Financial Performance (Income Statement)"""
        sofe = mapped_df.groupby(['grap_code', 'grap_item'])['Net Balance'].sum().reset_index()
        sofe.columns = ['GRAP Code', 'Line Item', 'Amount']
        
        # Separate revenue and expenses
        revenue = sofe[sofe['GRAP Code'].str.contains('REV-', na=False)].copy()
        expenses = sofe[sofe['GRAP Code'].str.contains('EXP-', na=False)].copy()
        
        revenue['Amount'] = revenue['Amount'].abs()
        
        # Calculate surplus/deficit
        total_revenue = revenue['Amount'].sum()
        total_expenses = expenses['Amount'].sum()
        surplus_deficit = total_revenue - total_expenses
        
        return {'revenue': revenue, 'expenses': expenses, 'surplus': surplus_deficit}
    
    def calculate_ratios(self, sofp, sofe):
        """Calculate key financial ratios"""
        # Extract totals
        total_assets = sofp['assets']['Amount'].sum()
        current_assets = sofp['assets'][sofp['assets']['GRAP Code'].str.contains('CA-')]['Amount'].sum()
        total_liabilities = sofp['liabilities']['Amount'].sum()
        current_liabilities = sofp['liabilities'][sofp['liabilities']['GRAP Code'].str.contains('CL-')]['Amount'].sum()
        
        total_revenue = sofe['revenue']['Amount'].sum()
        total_expenses = sofe['expenses']['Amount'].sum()
        net_assets = sofp['net_assets']['Amount'].sum()
        
        # Calculate ratios with error handling
        ratios = {
            'current_ratio': round(current_assets / current_liabilities, 2) if current_liabilities > 0 else 0,
            'debt_to_equity': round(total_liabilities / net_assets, 2) if net_assets > 0 else 0,
            'operating_margin': round((total_revenue - total_expenses) / total_revenue * 100, 2) if total_revenue > 0 else 0,
            'return_on_assets': round(sofe['surplus'] / total_assets * 100, 2) if total_assets > 0 else 0
        }
        
        return ratios


def generate_pdf_report(results, output_path):
    """Generate professional PDF report with GRAP-compliant formatting"""
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                           topMargin=2*cm, bottomMargin=2*cm,
                           leftMargin=2.5*cm, rightMargin=2.5*cm)
    
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#283593'),
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    
    # Document title
    story.append(Paragraph("SOUTH AFRICAN DIAMOND AND PRECIOUS METALS REGULATOR", title_style))
    story.append(Paragraph("ANNUAL FINANCIAL STATEMENTS", title_style))
    story.append(Paragraph(f"For the year ended 31 March {datetime.now().year}", styles['Normal']))
    story.append(Spacer(1, 1*cm))
    
    # Statement of Financial Position
    story.append(Paragraph("STATEMENT OF FINANCIAL POSITION", heading_style))
    story.append(Paragraph(f"as at 31 March {datetime.now().year}", styles['Normal']))
    story.append(Spacer(1, 0.5*cm))
    
    # Assets table
    assets_data = [['Note', 'ASSETS', f'{datetime.now().year}\nR']]
    
    for item in results['sofp']['assets']:
        assets_data.append(['', item['Line Item'], f"{item['Amount']:,.2f}"])
    
    assets_data.append(['', 'TOTAL ASSETS', f"{results['summary']['total_assets']:,.2f}"])
    
    assets_table = Table(assets_data, colWidths=[2*cm, 12*cm, 3*cm])
    assets_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e3f2fd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5f5f5')),
    ]))
    
    story.append(assets_table)
    story.append(Spacer(1, 0.5*cm))
    
    # Liabilities table
    liabilities_data = [['Note', 'LIABILITIES', f'{datetime.now().year}\nR']]
    
    for item in results['sofp']['liabilities']:
        liabilities_data.append(['', item['Line Item'], f"{item['Amount']:,.2f}"])
    
    liabilities_data.append(['', 'TOTAL LIABILITIES', f"{results['summary']['total_liabilities']:,.2f}"])
    
    liabilities_table = Table(liabilities_data, colWidths=[2*cm, 12*cm, 3*cm])
    liabilities_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e3f2fd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5f5f5')),
    ]))
    
    story.append(liabilities_table)
    story.append(Spacer(1, 0.5*cm))
    
    # Net Assets table
    net_assets_data = [
        ['Note', 'NET ASSETS', f'{datetime.now().year}\nR'],
        ['', 'Accumulated Surplus/(Deficit)', f"{results['summary']['net_assets']:,.2f}"],
        ['', 'TOTAL NET ASSETS', f"{results['summary']['net_assets']:,.2f}"]
    ]
    
    net_assets_table = Table(net_assets_data, colWidths=[2*cm, 12*cm, 3*cm])
    net_assets_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e3f2fd')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5f5f5')),
    ]))
    
    story.append(net_assets_table)
    story.append(Spacer(1, 1*cm))
    
    # Statement of Financial Performance
    story.append(Paragraph("STATEMENT OF FINANCIAL AND ECONOMIC PERFORMANCE", heading_style))
    story.append(Paragraph(f"for the year ended 31 March {datetime.now().year}", styles['Normal']))
    story.append(Spacer(1, 0.5*cm))
    
    # Revenue table
    revenue_data = [['Note', 'REVENUE', f'{datetime.now().year}\nR']]
    
    for item in results['sofe']['revenue']:
        revenue_data.append(['', item['Line Item'], f"{item['Amount']:,.2f}"])
    
    revenue_data.append(['', 'TOTAL REVENUE', f"{results['summary']['total_revenue']:,.2f}"])
    
    revenue_table = Table(revenue_data, colWidths=[2*cm, 12*cm, 3*cm])
    revenue_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8f5e8')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#1b5e20')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5f5f5')),
    ]))
    
    story.append(revenue_table)
    story.append(Spacer(1, 0.5*cm))
    
    # Expenses table
    expenses_data = [['Note', 'EXPENSES', f'{datetime.now().year}\nR']]
    
    for item in results['sofe']['expenses']:
        expenses_data.append(['', item['Line Item'], f"{item['Amount']:,.2f}"])
    
    expenses_data.append(['', 'TOTAL EXPENSES', f"{results['summary']['total_expenses']:,.2f}"])
    
    expenses_table = Table(expenses_data, colWidths=[2*cm, 12*cm, 3*cm])
    expenses_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#ffebee')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#c62828')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5f5f5')),
    ]))
    
    story.append(expenses_table)
    story.append(Spacer(1, 0.5*cm))
    
    # Surplus/Deficit
    surplus_data = [
        ['Note', 'SURPLUS/(DEFICIT) FOR THE YEAR', f'{datetime.now().year}\nR'],
        ['', '', f"{results['summary']['surplus_deficit']:,.2f}"]
    ]
    
    surplus_table = Table(surplus_data, colWidths=[2*cm, 12*cm, 3*cm])
    surplus_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#fff3e0')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#e65100')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5f5f5')),
    ]))
    
    story.append(surplus_table)
    story.append(Spacer(1, 1*cm))
    
    # Financial Ratios
    story.append(Paragraph("KEY FINANCIAL RATIOS", heading_style))
    story.append(Spacer(1, 0.5*cm))
    
    ratios_data = [['Ratio', 'Value', 'Benchmark']]
    ratios_data.extend([
        ['Current Ratio', f"{results['summary']['ratios']['current_ratio']:.2f}", '≥ 1.5'],
        ['Debt to Equity', f"{results['summary']['ratios']['debt_to_equity']:.2f}", '≤ 1.0'],
        ['Operating Margin (%)', f"{results['summary']['ratios']['operating_margin']:.2f}%", '≥ 10%'],
        ['Return on Assets (%)', f"{results['summary']['ratios']['return_on_assets']:.2f}%", '≥ 5%']
    ])
    
    ratios_table = Table(ratios_data, colWidths=[6*cm, 4*cm, 4*cm])
    ratios_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f3e5f5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#4a148c')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (2, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))
    
    story.append(ratios_table)
    
    # Build PDF
    doc.build(story)
    return output_path
