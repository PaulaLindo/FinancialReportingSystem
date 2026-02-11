"""
SADPMR Financial Reporting System - PDF Service
Refactored PDF generation with smaller, focused methods
"""

from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from utils.exceptions import ReportGenerationError
from utils.constants import PDF_COLORS, TABLE_COLUMN_WIDTHS


class PDFService:
    """Service for generating PDF reports"""
    
    def __init__(self):
        self.doc = None
        self.story = []
        self.styles = None
        self.custom_styles = {}
    
    def generate_financial_statements_pdf(self, results, output_path):
        """Generate complete financial statements PDF"""
        try:
            self._initialize_document(output_path)
            self._create_custom_styles()
            self._add_document_header()
            self._add_statement_of_financial_position(results)
            self._add_statement_of_performance(results)
            if 'scf' in results:
                self._add_statement_of_cash_flows(results)
            self._add_financial_ratios(results)
            self._build_document()
            return output_path
        except Exception as e:
            raise ReportGenerationError(f'PDF generation failed: {str(e)}', 'financial_statements')
    
    def _initialize_document(self, output_path):
        """Initialize PDF document with margins"""
        self.doc = SimpleDocTemplate(
            output_path, 
            pagesize=A4,
            topMargin=2*cm, 
            bottomMargin=2*cm,
            leftMargin=2.5*cm, 
            rightMargin=2.5*cm
        )
        self.story = []
        self.styles = getSampleStyleSheet()
    
    def _create_custom_styles(self):
        """Create custom paragraph styles"""
        self.custom_styles['title'] = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor(PDF_COLORS['primary']),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        self.custom_styles['heading'] = ParagraphStyle(
            'CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=12,
            textColor=colors.HexColor(PDF_COLORS['secondary']),
            spaceAfter=12,
            fontName='Helvetica-Bold'
        )
    
    def _add_document_header(self):
        """Add document title and header information"""
        self.story.append(Paragraph("SOUTH AFRICAN DIAMOND AND PRECIOUS METALS REGULATOR", self.custom_styles['title']))
        self.story.append(Paragraph("ANNUAL FINANCIAL STATEMENTS", self.custom_styles['title']))
        self.story.append(Paragraph(f"For the year ended 31 March {datetime.now().year}", self.styles['Normal']))
        self.story.append(Spacer(1, 1*cm))
    
    def _add_statement_of_financial_position(self, results):
        """Add Statement of Financial Position section"""
        self._add_section_header("STATEMENT OF FINANCIAL POSITION", f"as at 31 March {datetime.now().year}")
        
        # Assets table
        assets_table = self._create_financial_table(
            results['sofp']['assets'], 
            'ASSETS',
            PDF_COLORS['light_blue'],
            PDF_COLORS['primary']
        )
        self.story.append(assets_table)
        self.story.append(Spacer(1, 0.5*cm))
        
        # Liabilities table
        liabilities_table = self._create_financial_table(
            results['sofp']['liabilities'], 
            'LIABILITIES',
            PDF_COLORS['light_blue'],
            PDF_COLORS['primary']
        )
        self.story.append(liabilities_table)
        self.story.append(Spacer(1, 0.5*cm))
        
        # Net Assets table
        net_assets_table = self._create_net_assets_table(results)
        self.story.append(net_assets_table)
        self.story.append(Spacer(1, 1*cm))
    
    def _add_statement_of_performance(self, results):
        """Add Statement of Financial Performance section"""
        self._add_section_header("STATEMENT OF FINANCIAL AND ECONOMIC PERFORMANCE", f"for the year ended 31 March {datetime.now().year}")
        
        # Revenue table
        revenue_table = self._create_financial_table(
            results['sofe']['revenue'], 
            'REVENUE',
            PDF_COLORS['light_green'],
            PDF_COLORS['success']
        )
        self.story.append(revenue_table)
        self.story.append(Spacer(1, 0.5*cm))
        
        # Expenses table
        expenses_table = self._create_financial_table(
            results['sofe']['expenses'], 
            'EXPENSES',
            PDF_COLORS['light_red'],
            PDF_COLORS['danger']
        )
        self.story.append(expenses_table)
        self.story.append(Spacer(1, 0.5*cm))
        
        # Surplus/Deficit table
        surplus_table = self._create_surplus_table(results)
        self.story.append(surplus_table)
        self.story.append(Spacer(1, 1*cm))
    
    def _add_statement_of_cash_flows(self, results):
        """Add Statement of Cash Flows section (Indirect Method)"""
        self._add_section_header("CASH FLOW STATEMENT - INDIRECT METHOD", f"for the year ended 31 March {datetime.now().year}")
        
        scf = results['scf']
        
        # Operating Activities table
        operating_table = self._create_cash_flow_table(
            scf['operating'],
            'OPERATING ACTIVITIES',
            PDF_COLORS['light_blue'],
            PDF_COLORS['primary']
        )
        self.story.append(operating_table)
        self.story.append(Spacer(1, 0.5*cm))
        
        # Investing Activities table
        investing_table = self._create_cash_flow_table(
            scf['investing'],
            'INVESTING ACTIVITIES',
            PDF_COLORS['light_blue'],
            PDF_COLORS['primary']
        )
        self.story.append(investing_table)
        self.story.append(Spacer(1, 0.5*cm))
        
        # Financing Activities table
        financing_table = self._create_cash_flow_table(
            scf['financing'],
            'FINANCING ACTIVITIES',
            PDF_COLORS['light_blue'],
            PDF_COLORS['primary']
        )
        self.story.append(financing_table)
        self.story.append(Spacer(1, 0.5*cm))
        
        # Net Cash Movement
        net_movement_data = [
            ['Note', 'NET MOVEMENT IN CASH', f'{datetime.now().year}\nR'],
            ['', '', f"{scf['net_movement']:,.2f}"]
        ]
        
        net_movement_table = Table(net_movement_data, colWidths=[
            TABLE_COLUMN_WIDTHS['note'], 
            TABLE_COLUMN_WIDTHS['description'], 
            TABLE_COLUMN_WIDTHS['amount']
        ])
        
        net_movement_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(PDF_COLORS['light_orange'])),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(PDF_COLORS['warning'])),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor(PDF_COLORS['light_grey'])),
        ]))
        
        self.story.append(net_movement_table)
        self.story.append(Spacer(1, 1*cm))
    
    def _create_cash_flow_table(self, data, section_title, bg_color, text_color):
        """Create a cash flow statement table"""
        table_data = [[f'{datetime.now().year}\nR']]
        table_data[0].insert(0, section_title)
        table_data[0].insert(0, 'Note')
        
        for item in data:
            table_data.append(['', item['Line Item'], f"{item['Amount']:,.2f}"])
        
        table = Table(table_data, colWidths=[
            TABLE_COLUMN_WIDTHS['note'], 
            TABLE_COLUMN_WIDTHS['description'], 
            TABLE_COLUMN_WIDTHS['amount']
        ])
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(bg_color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(text_color)),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        return table
    
    def _add_financial_ratios(self, results):
        """Add Financial Ratios section"""
        self._add_section_header("KEY FINANCIAL RATIOS")
        
        ratios_table = self._create_ratios_table(results)
        self.story.append(ratios_table)
    
    def _add_section_header(self, title, subtitle=None):
        """Add section header with optional subtitle"""
        self.story.append(Paragraph(title, self.custom_styles['heading']))
        if subtitle:
            self.story.append(Paragraph(subtitle, self.styles['Normal']))
        self.story.append(Spacer(1, 0.5*cm))
    
    def _create_financial_table(self, data, section_title, bg_color, text_color):
        """Create a financial statement table"""
        table_data = [[f'{datetime.now().year}\nR']]
        table_data[0].insert(0, section_title)
        table_data[0].insert(0, 'Note')
        
        for item in data:
            table_data.append(['', item['Line Item'], f"{item['Amount']:,.2f}"])
        
        # Add total row
        total_amount = sum(item['Amount'] for item in data)
        table_data.append(['', f'TOTAL {section_title.upper()}', f"{total_amount:,.2f}"])
        
        table = Table(table_data, colWidths=[
            TABLE_COLUMN_WIDTHS['note'], 
            TABLE_COLUMN_WIDTHS['description'], 
            TABLE_COLUMN_WIDTHS['amount']
        ])
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(bg_color)),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(text_color)),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor(PDF_COLORS['light_grey'])),
        ]))
        
        return table
    
    def _create_net_assets_table(self, results):
        """Create net assets table"""
        net_assets_data = [
            ['Note', 'NET ASSETS', f'{datetime.now().year}\nR'],
            ['', 'Accumulated Surplus/(Deficit)', f"{results['summary']['net_assets']:,.2f}"],
            ['', 'TOTAL NET ASSETS', f"{results['summary']['net_assets']:,.2f}"]
        ]
        
        table = Table(net_assets_data, colWidths=[
            TABLE_COLUMN_WIDTHS['note'], 
            TABLE_COLUMN_WIDTHS['description'], 
            TABLE_COLUMN_WIDTHS['amount']
        ])
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(PDF_COLORS['light_blue'])),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(PDF_COLORS['primary'])),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor(PDF_COLORS['light_grey'])),
        ]))
        
        return table
    
    def _create_surplus_table(self, results):
        """Create surplus/deficit table"""
        surplus_data = [
            ['Note', 'SURPLUS/(DEFICIT) FOR THE YEAR', f'{datetime.now().year}\nR'],
            ['', '', f"{results['summary']['surplus_deficit']:,.2f}"]
        ]
        
        table = Table(surplus_data, colWidths=[
            TABLE_COLUMN_WIDTHS['note'], 
            TABLE_COLUMN_WIDTHS['description'], 
            TABLE_COLUMN_WIDTHS['amount']
        ])
        
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(PDF_COLORS['light_orange'])),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(PDF_COLORS['warning'])),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor(PDF_COLORS['light_grey'])),
        ]))
        
        return table
    
    def _create_ratios_table(self, results):
        """Create financial ratios table"""
        ratios_data = [['Ratio', 'Value', 'Benchmark']]
        ratios_data.extend([
            ['Current Ratio', f"{results['summary']['ratios']['current_ratio']:.2f}", '≥ 1.5'],
            ['Debt to Equity', f"{results['summary']['ratios']['debt_to_equity']:.2f}", '≤ 1.0'],
            ['Operating Margin (%)', f"{results['summary']['ratios']['operating_margin']:.2f}%", '≥ 10%'],
            ['Return on Assets (%)', f"{results['summary']['ratios']['return_on_assets']:.2f}%", '≥ 5%']
        ])
        
        table = Table(ratios_data, colWidths=[6*cm, 4*cm, 4*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor(PDF_COLORS['light_purple'])),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor(PDF_COLORS['info'])),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (2, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        
        return table
    
    def _build_document(self):
        """Build the final PDF document"""
        self.doc.build(self.story)
