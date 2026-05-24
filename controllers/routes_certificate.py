"""
Varydian Financial Reporting System - Manager's Certificate Routes
API endpoints for generating Manager's Certificates with digital signatures
"""

from flask import Blueprint, jsonify, request, send_file
from functools import wraps
import os
from datetime import datetime, timedelta
import hashlib

from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Create Blueprint
certificate_bp = Blueprint('certificate', __name__)

# App is defined under controllers/; certificate files live at project outputs/
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CERTIFICATES_DIR = os.path.join(_PROJECT_ROOT, 'outputs', 'certificates')


def _certificate_pdf_path(certificate_id: str) -> str:
    return os.path.join(CERTIFICATES_DIR, f'{certificate_id}.pdf')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session as flask_session

        if 'user_id' not in flask_session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        return f(*args, **kwargs)

    return decorated_function


def _resolve_session_for_certificate(session_id: str, document_type: str = None):
    from services.universal_workflow_service import UniversalWorkflowService

    svc = UniversalWorkflowService()
    order = []
    if document_type:
        order.append(document_type)
    for dt in ['balance_sheet', 'income_statement', 'budget_report']:
        if dt not in order:
            order.append(dt)
    for dt in order:
        if not dt:
            continue
        model = svc._get_model_for_document_type(dt)
        if not model:
            continue
        sess = model.get_session(session_id)
        if sess:
            return model, sess, dt
    return None, None, None


@certificate_bp.route('/api/certificate/generate/<session_id>', methods=['POST'])
@login_required
def generate_managers_certificate(session_id):
    """Generate Manager's Certificate after Finance Manager forwards submission to CFO."""
    try:
        from models.supabase_auth_models import get_current_user, get_supabase_auth

        user = get_current_user()
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        if user.role != 'FINANCE_MANAGER':
            return jsonify({'success': False, 'error': 'Only Finance Manager can generate certificates'}), 403

        payload = request.get_json(silent=True) or {}
        document_type = payload.get('document_type')

        _, sess, resolved_type = _resolve_session_for_certificate(session_id, document_type)
        if not sess:
            return jsonify({'success': False, 'error': 'Session not found'}), 404

        md = sess.metadata or {}
        manager_approval = md.get('manager_approval') or {}
        from utils.session_workflow import effective_workflow_status

        workflow_status = effective_workflow_status(sess)
        fm_approved = workflow_status in ('pending_cfo', 'approved_by_manager', 'approved')
        if not (sess.status == 'pending_cfo' or fm_approved or manager_approval.get('at')):
            return jsonify({
                'success': False,
                'error': 'Certificate available only after Finance Manager approval (forwarded to CFO)',
            }), 400

        auth = get_supabase_auth()
        creator = auth.get_user_by_id(sess.user_id) if sess.user_id else None
        creator_name = creator.get('full_name', 'Unknown') if creator else 'Unknown'

        transaction = {
            'transaction_id': sess.id,
            'transaction_type': resolved_type,
            'creator_name': creator_name,
            'created_at': sess.created_at.isoformat() if getattr(sess, 'created_at', None) else datetime.now().isoformat(),
            'filename': getattr(sess, 'filename', '') or getattr(sess, 'original_filename', ''),
        }

        approval = {
            'approved_at': manager_approval.get('at') or datetime.now().isoformat(),
            'notes': manager_approval.get('notes', ''),
        }

        user_dict = {'id': user.id, 'full_name': user.full_name, 'role': user.role}
        certificate_data = generate_certificate_pdf(transaction, user_dict, approval)

        return jsonify({
            'success': True,
            'certificate_url': certificate_data['url'],
            'certificate_filename': certificate_data['filename'],
            'certificate_id': certificate_data['certificate_id'],
            'message': "Manager's Certificate generated successfully",
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to generate certificate: {str(e)}'}), 500


@certificate_bp.route('/api/certificate/verify/<certificate_id>', methods=['GET'])
def verify_certificate_public(certificate_id):
    """Verify certificate registry entry, PDF, and signature sidecar."""
    try:
        from services.certificate_registry_service import verify_certificate

        return jsonify(verify_certificate(certificate_id))
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)}), 500


@certificate_bp.route('/api/certificate/download/<certificate_id>')
@login_required
def download_certificate(certificate_id):
    """Download generated certificate"""
    try:
        certificate_path = _certificate_pdf_path(certificate_id)

        if not os.path.isfile(certificate_path):
            return jsonify({'success': False, 'error': 'Certificate not found'}), 404

        return send_file(
            os.path.abspath(certificate_path),
            as_attachment=True,
            download_name=f'Managers_Certificate_{certificate_id}.pdf',
            mimetype='application/pdf',
        )

    except Exception as e:
        return jsonify({'success': False, 'error': f'Failed to download certificate: {str(e)}'}), 500


def generate_certificate_pdf(transaction, user, approval):
    """Generate PDF certificate with digital signature metadata."""

    certificates_dir = CERTIFICATES_DIR
    os.makedirs(certificates_dir, exist_ok=True)

    certificate_id = f"CERT_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(transaction['transaction_id'])[:8]}"
    filename = f'{certificate_id}.pdf'
    filepath = os.path.join(certificates_dir, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.darkblue,
    )

    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.black,
    )

    normal_style = styles['Normal']
    normal_style.fontSize = 11
    normal_style.spaceAfter = 12

    story = []

    story.append(Paragraph("MANAGER'S CERTIFICATE", title_style))
    story.append(Paragraph("Four-Eyes Approval Verification", subtitle_style))
    story.append(Spacer(1, 20))

    tx_type = str(transaction.get('transaction_type', '')).replace('_', ' ').title()
    cert_details = [
        ['Certificate ID:', certificate_id],
        ['Date Issued:', datetime.now().strftime('%d %B %Y')],
        ['Time Issued:', datetime.now().strftime('%H:%M:%S')],
        ['Session ID:', str(transaction.get('transaction_id', ''))],
        ['Document Type:', tx_type],
        ['File:', transaction.get('filename', '') or '—'],
        ['Creator:', transaction.get('creator_name', '')],
        ['Created Date:', transaction.get('created_at', '')[:10]],
    ]

    cert_table = Table(cert_details, colWidths=[2 * inch, 4 * inch])
    cert_table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 11),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ]
        )
    )

    story.append(cert_table)
    story.append(Spacer(1, 20))

    certification_text = f"""
    I, {user.get('full_name')}, in my capacity as Finance Manager of the Varydian Financial Reporting System,
    hereby certify that I have thoroughly reviewed the above-referenced submission and verify the following:

    1. The underlying calculations and mappings have been reviewed
    2. Account classifications follow GRAP (Generally Recognised Accounting Practice) guidance used in this system
    3. The submission has been forwarded for CFO final approval under the Four-Eyes workflow

    Notes recorded at approval: {approval.get('notes') or '—'}
    """

    story.append(Paragraph(certification_text, normal_style))
    story.append(Spacer(1, 20))

    signature_data = generate_digital_signature(user.get('id'), str(transaction.get('transaction_id')))

    signature_section = [
        ['Digital Signature:', signature_data['signature_hash']],
        ['Signature Algorithm:', 'SHA-256'],
        ['Certificate Valid Until:', (datetime.now() + timedelta(days=365)).strftime('%d %B %Y')],
        ['Manager approval timestamp:', approval.get('approved_at', 'N/A')],
    ]

    signature_table = Table(signature_section, colWidths=[2 * inch, 4 * inch])
    signature_table.setStyle(
        TableStyle(
            [
                ('BACKGROUND', (0, 0), (-1, -1), colors.whitesmoke),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ]
        )
    )

    story.append(signature_table)
    story.append(Spacer(1, 30))

    story.append(Paragraph("_____________________________", normal_style))
    story.append(Paragraph(f"{user.get('full_name')}", normal_style))
    story.append(Paragraph("Finance Manager", normal_style))
    story.append(Paragraph("Varydian Financial Reporting System", normal_style))

    story.append(Spacer(1, 40))
    story.append(
        Paragraph(
            "This certificate is electronically generated and digitally signed. "
            "Any alteration will invalidate the certificate.",
            ParagraphStyle(
                'Footer',
                parent=styles['Normal'],
                fontSize=9,
                alignment=TA_CENTER,
                textColor=colors.gray,
            ),
        )
    )

    doc.build(story)

    add_digital_signature_watermark(filepath, signature_data['signature_hash'])

    try:
        from services.certificate_registry_service import record_certificate

        record_certificate(
            certificate_id=certificate_id,
            session_id=str(transaction.get('transaction_id')),
            document_type=str(transaction.get('transaction_type', '')),
            issued_by=str(user.get('id')),
            signature_hash=signature_data['signature_hash'],
            filepath=filepath,
        )
    except Exception:
        pass

    return {
        'certificate_id': certificate_id,
        'filename': filename,
        'url': f'/api/certificate/download/{certificate_id}',
        'verify_url': f'/api/certificate/verify/{certificate_id}',
        'filepath': filepath,
        'signature_hash': signature_data['signature_hash'],
    }


def generate_digital_signature(user_id, transaction_id):
    """Generate digital signature hash"""
    signature_string = f"{user_id}:{transaction_id}:{datetime.now().isoformat()}"
    signature_hash = hashlib.sha256(signature_string.encode()).hexdigest()

    return {
        'signature_hash': signature_hash,
        'signature_string': signature_string,
        'algorithm': 'SHA-256',
        'timestamp': datetime.now().isoformat(),
    }


def add_digital_signature_watermark(filepath, signature_hash):
    """Persist signature verification sidecar file."""
    try:
        signature_file = filepath.replace('.pdf', '_signature.txt')
        with open(signature_file, 'w', encoding='utf-8') as f:
            f.write("Digital Signature Verification\n")
            f.write(f"Signature Hash: {signature_hash}\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write(f"File: {os.path.basename(filepath)}\n")
            f.write("Verification: SHA-256 hash of user_id:session_id:timestamp\n")

        return True
    except Exception as e:
        print(f"Error adding watermark: {e}")
        return False


def register_certificate_routes(app):
    """Register certificate routes with Flask app"""
    app.register_blueprint(certificate_bp)
