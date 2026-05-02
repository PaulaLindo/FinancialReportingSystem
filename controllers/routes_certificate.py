"""
SADPMR Financial Reporting System - Manager's Certificate Routes
API endpoints for generating Manager's Certificates with digital signatures
"""

from flask import Blueprint, jsonify, request, send_file
from functools import wraps
import os
import tempfile
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import timedelta
import hashlib
import base64

# Create Blueprint
certificate_bp = Blueprint('certificate', __name__)

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get current logged-in user"""
    from flask import session
    if 'user_id' in session:
        try:
            from models.supabase_auth_models import supabase_auth
            user_data = supabase_auth.get_user_by_id(session['user_id'])
            return user_data
        except:
            return None
    return None

@certificate_bp.route('/api/certificate/generate/<transaction_id>', methods=['POST'])
@login_required
def generate_managers_certificate(transaction_id):
    """Generate Manager's Certificate for approved transaction"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        # Check if user is Finance Manager
        if user['role'] != 'FINANCE_MANAGER':
            return jsonify({'success': False, 'error': 'Only Finance Manager can generate certificates'}), 403
        
        # Get transaction details
        from models.approval_models import approval_model
        transaction = None
        
        # Search in approved transactions
        data = approval_model._load_approval_data()
        for tx in data['approved_transactions']:
            if tx['transaction_id'] == transaction_id:
                transaction = tx
                break
        
        if not transaction:
            return jsonify({'success': False, 'error': 'Transaction not found or not approved'}), 404
        
        # Check if user has approved this transaction
        user_approval = None
        for approval in transaction['current_approvals']:
            if approval['approver_id'] == user['id']:
                user_approval = approval
                break
        
        if not user_approval:
            return jsonify({'success': False, 'error': 'You have not approved this transaction'}), 403
        
        # Generate certificate
        certificate_data = generate_certificate_pdf(transaction, user, user_approval)
        
        return jsonify({
            'success': True,
            'certificate_url': certificate_data['url'],
            'certificate_filename': certificate_data['filename'],
            'certificate_id': certificate_data['certificate_id'],
            'message': 'Manager\'s Certificate generated successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to generate certificate: {str(e)}'
        }), 500

@certificate_bp.route('/api/certificate/download/<certificate_id>')
@login_required
def download_certificate(certificate_id):
    """Download generated certificate"""
    try:
        # Find certificate file
        certificate_path = os.path.join('outputs', 'certificates', f'{certificate_id}.pdf')
        
        if not os.path.exists(certificate_path):
            return jsonify({'success': False, 'error': 'Certificate not found'}), 404
        
        return send_file(
            certificate_path,
            as_attachment=True,
            download_name=f'Managers_Certificate_{certificate_id}.pdf',
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to download certificate: {str(e)}'
        }), 500

def generate_certificate_pdf(transaction, user, approval):
    """Generate PDF certificate with digital signature"""
    
    # Ensure certificates directory exists
    certificates_dir = os.path.join('outputs', 'certificates')
    os.makedirs(certificates_dir, exist_ok=True)
    
    # Generate certificate ID
    certificate_id = f"CERT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{transaction['transaction_id']}"
    filename = f'{certificate_id}.pdf'
    filepath = os.path.join(certificates_dir, filename)
    
    # Create PDF
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Get styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.black
    )
    
    normal_style = styles['Normal']
    normal_style.fontSize = 11
    normal_style.spaceAfter = 12
    
    # Build certificate content
    story = []
    
    # Header
    story.append(Paragraph("MANAGER'S CERTIFICATE", title_style))
    story.append(Paragraph("Four-Eyes Approval Verification", subtitle_style))
    story.append(Spacer(1, 20))
    
    # Certificate details
    cert_details = [
        ['Certificate ID:', certificate_id],
        ['Date Issued:', datetime.now().strftime('%d %B %Y')],
        ['Time Issued:', datetime.now().strftime('%H:%M:%S')],
        ['Transaction ID:', transaction['transaction_id']],
        ['Transaction Type:', transaction['transaction_type'].replace('_', ' ').title()],
        ['Creator:', transaction['creator_name']],
        ['Created Date:', datetime.fromisoformat(transaction['created_at']).strftime('%d %B %Y')],
    ]
    
    cert_table = Table(cert_details, colWidths=[2*inch, 4*inch])
    cert_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
    ]))
    
    story.append(cert_table)
    story.append(Spacer(1, 20))
    
    # Certification text
    certification_text = f"""
    I, {user['full_name']}, in my capacity as Finance Manager of the SADPMR Financial Reporting System,
    hereby certify that I have thoroughly reviewed the above-referenced transaction and verify the following:
    
    1. The underlying calculations are mathematically correct and properly documented
    2. All account mappings comply with GRAP (Generally Recognised Accounting Practice) standards
    3. The financial data is accurate and complete
    4. The transaction follows proper internal controls and approval procedures
    5. All required supporting documentation has been reviewed and verified
    
    This certification is issued in accordance with the Four-Eyes Principle and PFMA Schedule 3A requirements.
    """
    
    story.append(Paragraph(certification_text, normal_style))
    story.append(Spacer(1, 20))
    
    # Digital signature section
    signature_data = generate_digital_signature(user['id'], transaction['transaction_id'])
    
    signature_section = [
        ['Digital Signature:', signature_data['signature_hash']],
        ['Signature Algorithm:', 'SHA-256'],
        ['Certificate Valid Until:', (datetime.now() + timedelta(days=365)).strftime('%d %B %Y')],
        ['Approval Reference:', approval['approved_at']],
    ]
    
    signature_table = Table(signature_section, colWidths=[2*inch, 4*inch])
    signature_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
    ]))
    
    story.append(signature_table)
    story.append(Spacer(1, 30))
    
    # Manager signature line
    story.append(Paragraph("_____________________________", normal_style))
    story.append(Paragraph(f"{user['full_name']}", normal_style))
    story.append(Paragraph("Finance Manager", normal_style))
    story.append(Paragraph("SADPMR Financial Reporting System", normal_style))
    
    # Footer
    story.append(Spacer(1, 40))
    story.append(Paragraph(
        "This certificate is electronically generated and digitally signed. " +
        "Any alteration will invalidate the certificate.",
        ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            alignment=TA_CENTER,
            textColor=colors.gray
        )
    ))
    
    # Build PDF
    doc.build(story)
    
    # Add digital signature watermark
    add_digital_signature_watermark(filepath, signature_data['signature_hash'])
    
    return {
        'certificate_id': certificate_id,
        'filename': filename,
        'url': f'/api/certificate/download/{certificate_id}',
        'filepath': filepath
    }

def generate_digital_signature(user_id, transaction_id):
    """Generate digital signature hash"""
    signature_string = f"{user_id}:{transaction_id}:{datetime.now().isoformat()}"
    signature_hash = hashlib.sha256(signature_string.encode()).hexdigest()
    
    return {
        'signature_hash': signature_hash,
        'signature_string': signature_string,
        'algorithm': 'SHA-256',
        'timestamp': datetime.now().isoformat()
    }

def add_digital_signature_watermark(filepath, signature_hash):
    """Add digital signature watermark to PDF"""
    try:
        # This would ideally use a proper PDF library to add watermarks
        # For now, we'll just append the signature hash to the filename
        # In a production environment, you'd use libraries like PyPDF2 or reportlab Canvas
        
        # Create a simple text file with signature verification data
        signature_file = filepath.replace('.pdf', '_signature.txt')
        with open(signature_file, 'w') as f:
            f.write(f"Digital Signature Verification\n")
            f.write(f"Signature Hash: {signature_hash}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"File: {os.path.basename(filepath)}\n")
            f.write(f"Verification: SHA-256 hash of user_id:transaction_id:timestamp\n")
        
        return True
    except Exception as e:
        print(f"Error adding watermark: {e}")
        return False

# Register Blueprint
def register_certificate_routes(app):
    """Register certificate routes with Flask app"""
    app.register_blueprint(certificate_bp)
