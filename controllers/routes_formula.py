"""
Formula Transparency Routes for GRAP Financial Reporting System
Handles formula breakdown API endpoints for CFO and AUDITOR roles
Integrated with processing state model for phase-based visibility control
"""

from flask import Blueprint, jsonify, request, send_file, session
from functools import wraps
import os
from io import BytesIO
from datetime import datetime
import json

# Create blueprint
formula_bp = Blueprint('formula', __name__, url_prefix='/api/formula')

# Import authentication and permissions
from models.supabase_auth_models import supabase_auth, get_current_user
from models.processing_models import processing_state

def permission_required(permission):
    """Decorator to check specific permissions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import session
            
            if 'user_id' not in session:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            
            user_data = supabase_auth.get_user_by_id(session['user_id'])
            if not user_data:
                return jsonify({'success': False, 'error': 'User not found'}), 401
            
            from models.supabase_auth_models import SupabaseUser
            user = SupabaseUser(user_data)
            if not user.has_permission(permission):
                return jsonify({'success': False, 'error': f'Permission denied. {permission.upper()} access required.'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def any_permission_required(*permissions):
    """User must have at least one of the given permissions."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import session

            if 'user_id' not in session:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401

            user_data = supabase_auth.get_user_by_id(session['user_id'])
            if not user_data:
                return jsonify({'success': False, 'error': 'User not found'}), 401

            from models.supabase_auth_models import SupabaseUser
            user = SupabaseUser(user_data)
            if not any(user.has_permission(p) for p in permissions):
                perms_s = ', '.join(permissions)
                return jsonify({
                    'success': False,
                    'error': f'Permission denied. Requires one of: {perms_s}.',
                }), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Formula data will be loaded from Supabase database
        
@formula_bp.route('/breakdown/<balance_sheet_id>/<line_item_id>')
@permission_required('view_all')
def get_formula_breakdown(balance_sheet_id, line_item_id):
    """Get formula breakdown for a specific line item with processing state validation"""
    try:
        from flask import session
        
        # Get current user
        user_data = supabase_auth.get_user_by_id(session['user_id'])
        if not user_data:
            return jsonify({'success': False, 'error': 'User not found'}), 401
        
        from models.supabase_auth_models import SupabaseUser
        user = SupabaseUser(user_data)
        
        # Check processing state and formula visibility
        visibility_check = processing_state.can_view_formulas(
            balance_sheet_id, user.role, user.id
        )
        
        if not visibility_check['can_view']:
            return jsonify({
                'success': False,
                'error': visibility_check['reason'],
                'access_mode': 'denied'
            }), 403
        
        # Get formula data
        formula_data = FORMULA_DATA.get(line_item_id)
        
        if not formula_data:
            return jsonify({
                'success': False,
                'error': f'Formula breakdown not available for line item: {line_item_id}'
            }), 404
        
        # Get processing state for context
        proc_state = processing_state.get_processing_state(balance_sheet_id)
        
        # Add metadata
        formula_data['lineItemId'] = line_item_id
        formula_data['balanceSheetId'] = balance_sheet_id
        formula_data['generatedAt'] = datetime.now().isoformat()
        formula_data['generatedBy'] = user.full_name
        formula_data['accessMode'] = visibility_check['mode']
        formula_data['processingStatus'] = proc_state.get('status', 'unknown') if proc_state else 'unknown'
        formula_data['formulaVisibility'] = proc_state.get('formula_visibility', 'unknown') if proc_state else 'unknown'
        
        # Add mapped accounts if available
        if proc_state and proc_state.get('mapped_accounts'):
            formula_data['mappedAccounts'] = proc_state['mapped_accounts']
        
        # Add GRAP validations if available
        if proc_state and proc_state.get('grap_validations'):
            formula_data['grapValidations'] = proc_state['grap_validations']
        
        return jsonify({
            'success': True,
            'data': formula_data,
            'access': {
                'mode': visibility_check['mode'],
                'reason': visibility_check['reason'],
                'processingStatus': proc_state.get('status') if proc_state else None,
                'formulaVisibility': proc_state.get('formula_visibility') if proc_state else None
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error retrieving formula breakdown: {str(e)}'
        }), 500

@formula_bp.route('/breakdown/<line_item_id>')
@permission_required('view_all')
def get_formula_breakdown_legacy(line_item_id):
    """Legacy formula breakdown endpoint (backward compatibility)"""
    try:
        # Get formula data without processing state validation
        formula_data = FORMULA_DATA.get(line_item_id)
        
        if not formula_data:
            return jsonify({
                'success': False,
                'error': f'Formula breakdown not available for line item: {line_item_id}'
            }), 404
        
        # Add metadata
        formula_data['lineItemId'] = line_item_id
        formula_data['generatedAt'] = datetime.now().isoformat()
        formula_data['generatedBy'] = get_current_user().full_name if get_current_user() else 'System'
        formula_data['accessMode'] = 'legacy'
        formula_data['processingStatus'] = 'unknown'
        formula_data['formulaVisibility'] = 'unknown'
        
        return jsonify({
            'success': True,
            'data': formula_data,
            'access': {
                'mode': 'legacy',
                'reason': 'Legacy endpoint - no processing state validation',
                'processingStatus': 'unknown',
                'formulaVisibility': 'unknown'
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error retrieving formula breakdown: {str(e)}'
        }), 500

@formula_bp.route('/export/formula-breakdown-pdf', methods=['POST'])
@any_permission_required('export_audit', 'review', 'final_approve')
def export_formula_breakdown_pdf():
    """Export formula breakdown as PDF"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided for export'
            }), 400

        try:
            uid = session.get('user_id')
            if uid:
                ud = supabase_auth.get_user_by_id(uid)
                if ud:
                    from models.supabase_auth_models import SupabaseUser

                    data.setdefault('generatedBy', SupabaseUser(ud).full_name)
        except Exception:
            pass

        pdf_bytes = generate_formula_breakdown_pdf(data)

        filename = f"formula-breakdown-{data.get('itemName', 'unknown').lower().replace(' ', '-')}-{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        return send_file(
            BytesIO(pdf_bytes),
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf',
        )
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error generating PDF: {str(e)}'
        }), 500

def generate_formula_breakdown_pdf(data):
    """Generate a valid PDF using ReportLab (plain UTF-8 text is not a PDF)."""
    from xml.sax.saxutils import escape

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    styles = getSampleStyleSheet()
    body = ParagraphStyle(name='ExportBody', parent=styles['Normal'], fontSize=10, leading=14)
    story = []

    story.append(Paragraph(escape('Formula breakdown report'), styles['Title']))
    story.append(Spacer(1, 10))

    def add_heading(text):
        story.append(Paragraph(f'<b>{escape(text)}</b>', styles['Heading2']))
        story.append(Spacer(1, 6))

    def add_kv(label, value):
        if value is None or str(value).strip() == '':
            return
        story.append(Paragraph(f'<b>{escape(label)}:</b> {escape(str(value))}', body))

    add_kv('Item', data.get('itemName'))
    add_kv('Period', data.get('period'))
    add_kv('Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    add_kv('Generated by', data.get('generatedBy'))
    add_kv('Framework', data.get('grapReference'))
    add_kv('Context', data.get('assetClass'))
    add_kv('Processing status', data.get('processingStatus'))
    add_kv('Access mode', data.get('accessMode'))
    add_kv('Note', data.get('noteReference'))
    add_kv('Audit reference', data.get('auditReference'))
    story.append(Spacer(1, 12))

    add_heading('Formula')
    story.append(Paragraph(escape(str(data.get('formula', '—'))), body))
    story.append(Spacer(1, 12))

    variables = data.get('variables') or []
    if variables:
        add_heading('Variables')
        for var in variables:
            nm = escape(str(var.get('name', '—')))
            val = escape(str(var.get('value', '—')))
            src = var.get('sourceLabel') or var.get('source')
            suffix = f' ({escape(str(src))})' if src else ''
            story.append(Paragraph(f'<b>{nm}</b>: {val}{suffix}', body))
            det = var.get('detail')
            if det:
                story.append(Paragraph(f'<i>{escape(str(det))}</i>', body))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 8))

    steps = data.get('steps') or []
    if steps:
        add_heading('Calculation steps')
        for i, step in enumerate(steps, 1):
            story.append(Paragraph(f'<b>Step {escape(str(i))}</b>', body))
            story.append(Paragraph(escape(str(step.get('formula', '—'))), body))
            story.append(
                Paragraph(f"<b>Result:</b> {escape(str(step.get('result', '—')))}", body)
            )
            story.append(Spacer(1, 8))

    add_heading('Final result')
    final_display = data.get('finalResult')
    if final_display is None or final_display == '':
        final_display = data.get('result', '—')
    story.append(Paragraph(escape(str(final_display)), body))

    trails = data.get('auditTrail') or []
    if trails:
        add_heading('Audit trail')
        for i, trail in enumerate(trails, 1):
            line = (
                f"{escape(str(trail.get('timestamp', '—')))} — "
                f"{escape(str(trail.get('action', '—')))} "
                f"({escape(str(trail.get('user', '—')))})"
            )
            story.append(Paragraph(line, body))
            details = trail.get('details')
            if details:
                story.append(Paragraph(escape(str(details)), body))
            story.append(Spacer(1, 4))

    doc.build(story)
    return buffer.getvalue()

@formula_bp.route('/source-ledger/<source_type>')
@permission_required('view_all')
def get_source_ledger_data(source_type):
    """Get source ledger data for a specific source type"""
    try:
        # Source ledger data will be loaded from Supabase database
        source_data = {}
        
        ledger_data = source_data.get(source_type)
        
        if not ledger_data:
            return jsonify({
                'success': False,
                'error': f'Source ledger not available: {source_type}'
            }), 404
        
        return jsonify({
            'success': True,
            'data': ledger_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error retrieving source ledger: {str(e)}'
        }), 500

@formula_bp.route('/balance-sheet')
@permission_required('view_all')
def get_balance_sheet_data():
    """Get raw balance sheet data"""
    try:
        # Balance sheet data will be loaded from Supabase database
        balance_sheet = {
            'title': 'Balance Sheet',
            'period': 'FY 2025-2026',
            'generated_at': datetime.now().isoformat(),
            'accounts': [],
            'totals': {
                'total_debits': 'R0.00',
                'total_credits': 'R0.00'
            }
        }
        
        return jsonify({
            'success': True,
            'data': balance_sheet
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error retrieving balance sheet: {str(e)}'
        }), 500

# Processing State Management Routes

@formula_bp.route('/processing/create/<balance_sheet_id>', methods=['POST'])
@permission_required('upload')
def create_processing_state(balance_sheet_id):
    """Create processing state for new Balance Sheet"""
    try:
        from flask import session
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        period = data.get('period')
        if not period:
            return jsonify({'success': False, 'error': 'Period is required'}), 400
        
        user_data = supabase_auth.get_user_by_id(session['user_id'])
        if not user_data:
            return jsonify({'success': False, 'error': 'User not found'}), 401
        
        # Create processing state
        state = processing_state.create_processing_state(
            balance_sheet_id, period, user_data['username']
        )
        
        return jsonify({
            'success': True,
            'data': state,
            'message': 'Processing state created successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error creating processing state: {str(e)}'
        }), 500

@formula_bp.route('/processing/update/<balance_sheet_id>', methods=['POST'])
@permission_required('review')
def update_processing_status(balance_sheet_id):
    """Update processing status for Balance Sheet"""
    try:
        from flask import session
        
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        new_status = data.get('status')
        if not new_status:
            return jsonify({'success': False, 'error': 'Status is required'}), 400
        
        user_data = supabase_auth.get_user_by_id(session['user_id'])
        if not user_data:
            return jsonify({'success': False, 'error': 'User not found'}), 401
        
        # Update processing status
        success = processing_state.update_processing_status(
            balance_sheet_id, new_status, user_data['id']
        )
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Balance Sheet not found or update failed'
            }), 404
        
        # Get updated state
        state = processing_state.get_processing_state(balance_sheet_id)
        
        return jsonify({
            'success': True,
            'data': state,
            'message': f'Processing status updated to {new_status}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error updating processing status: {str(e)}'
        }), 500
