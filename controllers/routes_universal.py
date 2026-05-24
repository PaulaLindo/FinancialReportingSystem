"""
Universal Financial Document Routes
Handles uploads for all financial document types (Balance Sheets, Income Statements, Budget Reports)
"""

from flask import jsonify, request, session
from functools import wraps
import copy
import os
import tempfile
from datetime import datetime
import uuid

# Import authentication and permissions
from models.supabase_auth_models import get_current_user, get_supabase_auth
from utils.constants import WorkflowErrorMessages, ClerkWorkflowMessages

# Import document services
from services.financial_document_service import FinancialDocumentService
from services.income_statement_service import IncomeStatementService
from services.budget_report_service import BudgetReportService
from services.universal_workflow_service import UniversalWorkflowService
from services.session_formula_breakdown import build_formula_breakdown_response
from services.approval_facade import approval_facade

# Import existing balance sheet service for backward compatibility
from services.flexible_balance_sheet_service import FlexibleBalanceSheetService
from utils.document_format_detection import (
    column_names_from_data_rows,
    column_names_from_upload_result,
    peek_file_column_names,
    resolve_document_type_mismatch,
)
from utils.period_lock import check_period_id_unlocked, check_session_period_unlocked


def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def permission_required(*permissions):
    """Decorator — user must have at least one of the listed permissions."""
    required = permissions or ('',)

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user or not any(user.has_permission(p) for p in required):
                return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def allowed_file(filename):
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv', 'xlsm', 'xlsb', 'tsv'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


class UniversalUploadHandler:
    """Universal handler for all financial document uploads"""
    
    def __init__(self):
        self.document_services = {
            'balance_sheet': FlexibleBalanceSheetService(),
            'income_statement': IncomeStatementService(),
            'budget_report': BudgetReportService()
        }
        self.workflow_service = UniversalWorkflowService()
    
    def get_service(self, document_type: str):
        """Get the appropriate service for a document type"""
        return self.document_services.get(document_type)
    
    def process_upload(self, document_type: str, file, user_id: str, **kwargs):
        """Process upload for any document type"""
        try:
            # Get the appropriate service
            service = self.get_service(document_type)
            if not service:
                return {
                    'success': False,
                    'error': f'Unsupported document type: {document_type}'
                }
            
            # Create temporary file for processing
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
                file.save(temp_file.name)
                temp_file_path = temp_file.name
            
            try:
                file_columns = peek_file_column_names(temp_file_path)
                detected_type, mismatch_message = resolve_document_type_mismatch(
                    document_type,
                    file_columns,
                    filename=file.filename,
                )
                if detected_type:
                    print(
                        f"⚠️ Upload blocked — document type mismatch: "
                        f"selected={document_type}, detected={detected_type}, "
                        f"columns={file_columns}"
                    )
                    return {
                        'success': False,
                        'format_mismatch': True,
                        'error_code': 'document_type_mismatch',
                        'selected_document_type': document_type,
                        'detected_document_type': detected_type,
                        'error': mismatch_message,
                        'session_discarded': False,
                    }

                result = service.process_upload(
                    file_path=temp_file_path,
                    user_id=user_id,
                    filename=file.filename,
                    **kwargs
                )
                
                return result
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except:
                    pass
                    
        except Exception as e:
            return {
                'success': False,
                'error': f'Error processing {document_type}: {str(e)}'
            }


# Create global upload handler
upload_handler = UniversalUploadHandler()


def _load_document_session(session_id: str, document_type: str):
    """Load upload session row for a document type."""
    if not session_id or not document_type:
        return None
    model = upload_handler.workflow_service._get_model_for_document_type(document_type)
    if not model:
        return None
    return model.get_session(session_id)


def _period_lock_json_error(session_id: str, document_type: str):
    """Return 403 if session's period is locked, else None."""
    sess = _load_document_session(session_id, document_type)
    if not sess:
        return None
    allowed, message = check_session_period_unlocked(sess)
    if not allowed:
        return jsonify({'success': False, 'error': message, 'period_locked': True}), 403
    return None


def _clerk_mapping_locked_json_error(session_id: str, document_type: str):
    """Return 403 when clerk mapping / GRAP panels must stay read-only."""
    from utils.session_workflow import clerk_mapping_locked

    sess = _load_document_session(session_id, document_type)
    if not sess:
        return None
    if clerk_mapping_locked(sess):
        return jsonify({
            'success': False,
            'error': 'Session is locked pending review — changes cannot be saved.',
            'locked': True,
        }), 403
    return None


def _session_view_json_error(session_id: str, document_type: str, user) -> tuple | None:
    """Return 403 if user may not view this session."""
    if not user:
        return jsonify({'success': False, 'error': 'User not authenticated'}), 401
    if getattr(user, 'can_review', lambda: False)():
        return None
    sess = _load_document_session(session_id, document_type)
    if not sess:
        return None
    if str(getattr(sess, 'user_id', '')) != str(user.id):
        return jsonify({'success': False, 'error': 'Permission denied'}), 403
    return None


def _normalize_session_summary_for_breakdown(raw):
    """Accept both FlexibleBalanceSheet-style summaries and FinancialDocumentService-style responses."""
    if not isinstance(raw, dict):
        return None, 'Invalid response'
    if raw.get('error'):
        return None, str(raw['error'])
    if raw.get('success') is False:
        return None, str(raw.get('error') or 'Session error')
    return raw, None


def _document_service_model(svc):
    m = getattr(svc, 'model', None)
    if m is not None:
        return m
    gm = getattr(svc, 'get_model', None)
    return gm() if callable(gm) else None


def _column_names_from_session_metadata(session_data) -> list:
    """Pull header names stored on the session during upload."""
    meta = getattr(session_data, 'metadata', None) or {}
    if isinstance(meta, str):
        import json
        try:
            meta = json.loads(meta)
        except (json.JSONDecodeError, TypeError):
            meta = {}
    names: list = []
    file_columns = meta.get('file_columns') or []
    names.extend(str(c) for c in file_columns if c)
    mapping = meta.get('column_mapping') or {}
    if isinstance(mapping, dict):
        for value in mapping.values():
            if isinstance(value, str) and value.strip():
                names.append(value.strip())
    return names


def _discard_ephemeral_session(session_id: str, document_type: str) -> bool:
    """Remove a staging upload when validation fails (e.g. wrong document type)."""
    try:
        from services.cleanup_service import CleanupService
        from utils.session_workflow import session_is_ephemeral_staging

        service = upload_handler.get_service(document_type)
        if not service:
            return False
        model = _document_service_model(service)
        if not model:
            return False
        session_data = model.get_session(session_id)
        if not session_data or not session_is_ephemeral_staging(session_data):
            return False
        result = CleanupService().cleanup_specific_session(session_id)
        return bool(result.get('success'))
    except Exception as exc:
        print(f"⚠️ Ephemeral session discard failed: {exc}")
        return False


def _fetch_session_data_rows(model, session_id: str, document_type: str):
    """Load row objects for balance validation from the document model."""
    try:
        return model.get_data_rows(session_id)
    except AttributeError:
        pass
    try:
        return model.get_session_data(session_id)
    except AttributeError:
        pass
    raise AttributeError(
        f'Model for {document_type} has no get_data_rows or get_session_data'
    )


def _apply_calculation_verification(document_type: str, session_id: str, calc_id: str, verified: bool):
    """Persist metadata.calculation_verifications[calc_id] on the session row."""
    service = upload_handler.get_service(document_type)
    if not service:
        return False, 'Unsupported document type'
    model = _document_service_model(service)
    if not model:
        return False, 'Model unavailable'
    sess = model.get_session(session_id)
    if not sess:
        return False, 'Session not found'
    meta = copy.deepcopy(sess.metadata) if sess.metadata else {}
    ver = dict(meta.get('calculation_verifications') or {})
    user = get_current_user()
    ver[str(calc_id)] = {
        'verified': bool(verified),
        'user_id': str(user.id) if user else '',
        'at': datetime.utcnow().isoformat() + 'Z',
    }
    meta['calculation_verifications'] = ver
    sess.metadata = meta
    if hasattr(sess, 'updated_at'):
        sess.updated_at = datetime.utcnow()
    model.update_session(sess)
    return True, None


def _infer_document_type_from_session(session_id):
    """Infer document type from an existing upload session id."""
    from utils.period_lock import infer_document_type_from_session

    return infer_document_type_from_session(session_id)


def register_universal_routes(app):
    """Register universal financial document routes"""

    @app.route('/api/universal/upload', methods=['POST'])
    @login_required
    @permission_required('upload')
    def upload_financial_document():
        """
        Universal API endpoint to handle any financial document upload
        Supports: Balance Sheets, Income Statements, Budget Reports
        """
        try:
            print("🔄 Universal upload endpoint called")
            print(f"📁 Request files: {list(request.files.keys())}")
            print(f"📋 Request form: {dict(request.form)}")
            
            # Get document type from form data
            document_type = request.form.get('document_type', 'balance_sheet')
            print(f"📄 Document type: {document_type}")
            
            # Validate document type
            if document_type not in upload_handler.document_services:
                return jsonify({
                    'success': False,
                    'error': f'Unsupported document type: {document_type}'
                }), 400
            
            # Check if file is present
            if 'file' not in request.files:
                return jsonify({'success': False, 'error': 'No file uploaded'}), 400
            
            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'error': 'No file selected'}), 400
            
            # Validate file type
            if not allowed_file(file.filename):
                return jsonify({
                    'success': False,
                    'error': 'File type not supported. Please use Excel (.xlsx, .xls) or CSV (.csv)'
                }), 400
            
            # Get current user
            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            
            print(f"👤 User authenticated: {current_user.username}")
            
            # Get additional parameters
            period_id = request.form.get('period_id')
            notes = request.form.get('notes', '')

            if period_id:
                allowed, lock_msg = check_period_id_unlocked(period_id)
                if not allowed:
                    return jsonify({'success': False, 'error': lock_msg, 'period_locked': True}), 403
            
            # Process the upload
            result = upload_handler.process_upload(
                document_type=document_type,
                file=file,
                user_id=current_user.id,
                period_id=period_id
            )
            
            if result.get('format_mismatch'):
                print(
                    f"⚠️ Upload rejected — document type mismatch: "
                    f"selected={result.get('selected_document_type')}, "
                    f"detected={result.get('detected_document_type')}"
                )
                return jsonify(result)

            if result['success']:
                print(f"✅ {document_type} uploaded successfully")
                print(f"📋 Session ID: {result['session_id']}")
                print(f"📊 Total rows: {result.get('total_rows', 0)}")
                print(f"📈 Total columns: {result.get('total_columns', 0)}")

                column_names = column_names_from_upload_result(result)
                detected_type, mismatch_message = resolve_document_type_mismatch(
                    document_type,
                    column_names,
                    filename=file.filename,
                )
                if detected_type:
                    session_discarded = _discard_ephemeral_session(
                        result['session_id'], document_type
                    )
                    print(
                        f"⚠️ Document type mismatch: selected={document_type}, "
                        f"detected={detected_type}"
                    )
                    return jsonify({
                        'success': False,
                        'format_mismatch': True,
                        'error_code': 'document_type_mismatch',
                        'selected_document_type': document_type,
                        'detected_document_type': detected_type,
                        'error': mismatch_message,
                        'session_discarded': session_discarded,
                    })

                result['document_type'] = document_type
                return jsonify(result)
            else:
                print(f"❌ Upload failed: {result.get('error', 'Unknown error')}")
                return jsonify(result), 400
                
        except Exception as e:
            print(f"💥 Unexpected error in universal upload: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Unexpected error during upload: {str(e)}'
            }), 500
    
    @app.route('/api/universal/process-grap-mapping', methods=['POST'])
    @login_required
    @permission_required('process')
    def universal_process_grap_mapping():
        """Run GRAP account mapping after upload (all document types)."""
        try:
            data = request.get_json() or {}
            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            from controllers.handlers.grap_processing import process_grap_mapping_request
            return process_grap_mapping_request(
                data.get('session_id'),
                current_user.id,
                data.get('document_type'),
            )
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/universal/submit-for-review', methods=['POST'])
    @login_required
    @permission_required('process')
    def submit_document_for_review():
        """
        Submit any financial document for review
        """
        try:
            data = request.get_json() or {}
            document_type = data.get('document_type')
            session_id = data.get('session_id')
            notes = data.get('notes', '')
            clerk_correction_note = (data.get('clerk_correction_note') or '').strip()
            
            if not document_type or not session_id:
                return jsonify({
                    'success': False,
                    'error': 'Document type and session ID are required'
                }), 400

            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401

            lock_resp = _period_lock_json_error(session_id, document_type)
            if lock_resp:
                return lock_resp

            locked_resp = _clerk_mapping_locked_json_error(session_id, document_type)
            if locked_resp:
                return locked_resp

            balanced, balance_error = require_balanced_session(session_id, document_type)
            if not balanced:
                return jsonify({'success': False, 'error': balance_error}), 400

            # Submit for review using universal workflow service
            result = upload_handler.workflow_service.submit_for_review(
                document_type=document_type,
                session_id=session_id,
                user_id=current_user.id,
                notes=notes,
                clerk_correction_note=clerk_correction_note,
            )
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error submitting document for review: {str(e)}'
            }), 500

    @app.route('/api/universal/correction-workspace/<session_id>', methods=['GET'])
    @login_required
    @permission_required('process')
    def correction_workspace(session_id):
        """Clerk revision page context: rejection banner, timeline, correction mode flags."""
        try:
            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401

            document_type = request.args.get('document_type') or _infer_document_type_from_session(session_id)
            if not document_type:
                return jsonify({'success': False, 'error': 'Document type could not be determined'}), 400

            model = upload_handler.workflow_service._get_model_for_document_type(document_type)
            if not model:
                return jsonify({'success': False, 'error': 'Unsupported document type'}), 400

            db_session = model.get_session(session_id)
            if not db_session:
                return jsonify({'success': False, 'error': 'Session not found'}), 404

            if str(db_session.user_id) != str(current_user.id) and not current_user.can_review():
                return jsonify({'success': False, 'error': 'Access denied'}), 403

            from services.workflow_timeline_service import correction_workspace_payload

            payload = correction_workspace_payload(
                db_session, document_type=document_type, user_id=current_user.id
            )
            return jsonify({'success': True, **payload})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/universal/session/<session_id>/workflow-timeline', methods=['GET'])
    @login_required
    def session_workflow_timeline(session_id):
        """Auditable resubmission history for FM/CFO review screens."""
        try:
            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401

            document_type = request.args.get('document_type') or _infer_document_type_from_session(session_id)
            if not document_type:
                return jsonify({'success': False, 'error': 'Document type required'}), 400

            model = upload_handler.workflow_service._get_model_for_document_type(document_type)
            db_session = model.get_session(session_id) if model else None
            if not db_session:
                return jsonify({'success': False, 'error': 'Session not found'}), 404

            if str(db_session.user_id) != str(current_user.id) and not current_user.can_review():
                return jsonify({'success': False, 'error': 'Access denied'}), 403

            from services.workflow_timeline_service import (
                build_timeline_from_metadata,
                timeline_has_resubmission,
                timeline_tab_label,
            )

            md = getattr(db_session, 'metadata', None) or {}
            from utils.session_workflow import effective_workflow_status

            workflow_status = effective_workflow_status(db_session)
            timeline = build_timeline_from_metadata(md)
            return jsonify({
                'success': True,
                'session_id': session_id,
                'document_type': document_type,
                'status': workflow_status,
                'workflow_status': workflow_status,
                'db_status': getattr(db_session, 'status', ''),
                'timeline': timeline,
                'has_resubmission': timeline_has_resubmission(timeline),
                'timeline_tab_label': timeline_tab_label(timeline),
                'rejection_reason': (md.get('rejection_reason') or '').strip(),
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/universal/approve', methods=['POST'])
    @login_required
    @permission_required('approve', 'final_approve')
    def approve_document():
        """
        Approve any financial document
        """
        try:
            data = request.get_json()
            document_type = data.get('document_type')
            session_id = data.get('session_id')
            notes = data.get('notes', '')
            
            if not document_type or not session_id:
                return jsonify({
                    'success': False,
                    'error': 'Document type and session ID are required'
                }), 400
            
            # Get current user
            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            
            # Approve document using universal workflow service
            result = upload_handler.workflow_service.approve_document(
                document_type=document_type,
                session_id=session_id,
                user_id=current_user.id,
                notes=notes
            )
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error approving document: {str(e)}'
            }), 500

    @app.route('/api/universal/batch-approve', methods=['POST'])
    @login_required
    @permission_required('approve', 'final_approve')
    def batch_approve_documents():
        """Approve multiple financial document sessions in one request."""
        try:
            data = request.get_json() or {}
            items = data.get('items') or data.get('sessions') or []
            notes = data.get('notes', '')

            if not items:
                return jsonify({
                    'success': False,
                    'error': 'items array is required (document_type + session_id per entry)',
                }), 400

            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401

            result = upload_handler.workflow_service.batch_approve(
                items=items,
                user_id=current_user.id,
                notes=notes,
            )
            status = 200 if result.get('success') else (207 if result.get('partial') else 400)
            return jsonify(result), status
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error in batch approve: {str(e)}',
            }), 500
    
    @app.route('/api/universal/reject', methods=['POST'])
    @login_required
    @permission_required('approve', 'final_approve')
    def reject_document():
        """
        Reject any financial document
        """
        try:
            data = request.get_json()
            document_type = data.get('document_type')
            session_id = data.get('session_id')
            reason = data.get('reason', '')
            
            if not document_type or not session_id:
                return jsonify({
                    'success': False,
                    'error': 'Document type and session ID are required'
                }), 400
            
            if not reason:
                return jsonify({
                    'success': False,
                    'error': 'Rejection reason is required'
                }), 400
            
            # Get current user
            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            
            # Reject document using universal workflow service
            result = upload_handler.workflow_service.reject_document(
                document_type=document_type,
                session_id=session_id,
                user_id=current_user.id,
                reason=reason
            )
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error rejecting document: {str(e)}'
            }), 500

    @app.route('/api/universal/session/<session_id>/review-draft-notes', methods=['POST'])
    @login_required
    @permission_required('approve', 'final_approve')
    def save_review_panel_draft_notes(session_id):
        """Persist reviewer free-form notes shown on statement review panel (approval optional appendix)."""
        try:
            data = request.get_json() or {}
            document_type = data.get('document_type')
            notes = data.get('notes', '')
            if notes is None:
                notes = ''
            if not isinstance(notes, str):
                return jsonify({'success': False, 'error': 'notes must be a string'}), 400
            if len(notes) > 32000:
                return jsonify({'success': False, 'error': 'notes exceed maximum length'}), 400
            model, sess, resolved_type = _comment_resolve_session(session_id, document_type)
            if not sess or not model:
                return jsonify({'success': False, 'error': 'Session not found'}), 404
            if sess.metadata is None:
                sess.metadata = {}
            sess.metadata['review_panel_draft_notes'] = notes
            sess.metadata['review_panel_draft_notes_at'] = datetime.now().isoformat()
            model.update_session(sess)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/transaction/approve', methods=['POST'])
    @login_required
    @permission_required('approve', 'final_approve')
    def approve_transaction():
        """Approve a transaction using approval models"""
        try:
            data = request.get_json()
            transaction_id = data.get('transaction_id')
            session_id = data.get('session_id')  # Add session_id for document approvals
            reason = data.get('reason', '')
            
            if not transaction_id:
                return jsonify({
                    'success': False,
                    'error': 'Transaction ID is required'
                }), 400
            
            # Get current user
            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            
            # Check if this is a document approval (has session_id) or traditional transaction
            if session_id:
                # Handle document approval through Universal Workflow Service
                from services.universal_workflow_service import UniversalWorkflowService
                workflow_service = UniversalWorkflowService()
                
                result = workflow_service.process_approval(
                    session_id=session_id,
                    user_id=current_user.id,
                    action='approve',
                    reason=reason
                )
                
                if result['success']:
                    document_type = result.get('document_type', 'unknown')
                    return jsonify({
                        'success': True,
                        'message': 'Document approved successfully',
                        'transaction': {
                            'transaction_id': transaction_id,
                            'session_id': session_id,
                            'status': 'approved',
                            'required_approvals': ['FINANCE_MANAGER', 'CFO'] if document_type in ['income_statement', 'balance_sheet', 'budget_report'] else ['FINANCE_MANAGER'],
                            'current_approvals': [{
                                'approver_name': current_user.full_name if hasattr(current_user, 'full_name') else current_user.id,
                                'approver_role': current_user.role if hasattr(current_user, 'role') else 'Unknown',
                                'approved_at': datetime.now().isoformat(),
                                'reason': reason
                            }]
                        }
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': result.get('error', 'Failed to approve document')
                    }), 500
            else:
                # Traditional transaction approval (transaction_approvals / approval_actions)
                result = approval_facade.transactions.approve_transaction(
                    approver_id=current_user.id,
                    transaction_id=transaction_id,
                    approval_reason=reason
                )
                
                return jsonify(result)
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error approving transaction: {str(e)}'
            }), 500
    
    @app.route('/api/transaction/reject', methods=['POST'])
    @login_required
    @permission_required('approve', 'final_approve')
    def reject_transaction():
        """Reject a transaction using approval models"""
        try:
            data = request.get_json()
            transaction_id = data.get('transaction_id')
            session_id = data.get('session_id')  # Add session_id for document approvals
            reason = data.get('reason', '')
            
            if not transaction_id:
                return jsonify({
                    'success': False,
                    'error': 'Transaction ID is required'
                }), 400
            
            if not reason:
                return jsonify({
                    'success': False,
                    'error': 'Rejection reason is required'
                }), 400
            
            # Get current user
            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            
            # Check if this is a document approval (has session_id) or traditional transaction
            if session_id:
                # Handle document rejection through Universal Workflow Service
                from services.universal_workflow_service import UniversalWorkflowService
                workflow_service = UniversalWorkflowService()
                
                result = workflow_service.process_approval(
                    session_id=session_id,
                    user_id=current_user.id,
                    action='reject',
                    reason=reason
                )
                
                if result['success']:
                    document_type = result.get('document_type', 'unknown')
                    return jsonify({
                        'success': True,
                        'message': 'Document rejected successfully',
                        'transaction': {
                            'transaction_id': transaction_id,
                            'session_id': session_id,
                            'status': 'rejected',
                            'required_approvals': ['FINANCE_MANAGER', 'CFO'] if document_type in ['income_statement', 'balance_sheet', 'budget_report'] else ['FINANCE_MANAGER'],
                            'current_approvals': []  # Rejected documents have no current approvals
                        }
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': result.get('error', 'Failed to reject document')
                    }), 500
            else:
                # Traditional transaction rejection (transaction_approvals / approval_actions)
                result = approval_facade.transactions.reject_transaction(
                    rejecter_id=current_user.id,
                    transaction_id=transaction_id,
                    rejection_reason=reason
                )
                
                return jsonify(result)
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error rejecting transaction: {str(e)}'
            }), 500
    
    @app.route('/api/universal/submissions', methods=['GET'])
    @login_required
    def get_universal_submissions():
        """
        Get all submissions for the current user across all document types
        """
        try:
            # Get current user
            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            
            # Get document type filter
            document_type = request.args.get('document_type')
            
            # Get submissions using universal workflow service
            result = upload_handler.workflow_service.get_user_submissions(
                user_id=current_user.id,
                document_type=document_type
            )
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error getting submissions: {str(e)}'
            }), 500
    
    @app.route('/api/universal/pending-approvals', methods=['GET'])
    @login_required
    @permission_required('approve', 'final_approve')
    def get_pending_approvals():
        """
        Get all pending approvals for managers/CFOs across all document types
        """
        try:
            # Get current user
            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401
            
            # Get pending approvals using universal workflow service
            result = upload_handler.workflow_service.get_pending_approvals(
                user_id=current_user.id
            )
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error getting pending approvals: {str(e)}'
            }), 500
    
    @app.route('/api/universal/session/<session_id>', methods=['GET'])
    @login_required
    def get_document_session(session_id):
        """
        Get session details for any document type
        """
        try:
            document_type = request.args.get('document_type')
            
            if not document_type:
                return jsonify({
                    'success': False,
                    'error': 'Document type is required'
                }), 400

            current_user = get_current_user()
            access_resp = _session_view_json_error(session_id, document_type, current_user)
            if access_resp:
                return access_resp
            
            # Get the appropriate service
            service = upload_handler.get_service(document_type)
            if not service:
                return jsonify({
                    'success': False,
                    'error': f'Unsupported document type: {document_type}'
                }), 400
            
            # Get session summary
            result = service.get_session_summary(session_id)
            
            return jsonify(result)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error getting session: {str(e)}'
            }), 500

    @app.route('/api/universal/session/<session_id>/variance-explanations', methods=['POST'])
    @login_required
    @permission_required('process')
    def save_variance_explanations(session_id):
        """Persist GRAP 24 variance explanations for budget report line items."""
        try:
            data = request.get_json() or {}
            document_type = data.get('document_type', 'budget_report')
            explanations = data.get('variance_explanations') or data.get('explanations') or {}

            if document_type != 'budget_report':
                return jsonify({'success': False, 'error': 'Variance explanations apply to budget reports only'}), 400

            lock_resp = _period_lock_json_error(session_id, document_type)
            if lock_resp:
                return lock_resp

            from models.budget_report_models import budget_report_model
            from services.budget_variance_service import validate_variance_explanations

            sess = budget_report_model.get_session(session_id)
            if not sess:
                return jsonify({'success': False, 'error': 'Session not found'}), 404

            from utils.session_workflow import clerk_mapping_locked

            if clerk_mapping_locked(sess):
                return jsonify({
                    'success': False,
                    'error': 'Session is locked pending review — variance explanations cannot be edited.',
                }), 403

            rows_raw = budget_report_model.get_data_rows(session_id)
            budget_rows = [{
                'row_index': r.row_index,
                'account_code': r.account_code,
                'account_description': r.account_description,
                'budget_amount': float(r.budget_amount),
                'actual_amount': float(r.actual_amount),
                'variance': float(r.variance),
                'is_total_row': r.is_total_row,
                'is_subtotal_row': r.is_subtotal_row,
            } for r in rows_raw]

            cleaned = {str(k): str(v).strip() for k, v in explanations.items() if str(v).strip()}
            passed, missing, required = validate_variance_explanations(budget_rows, cleaned)

            if sess.metadata is None:
                sess.metadata = {}
            sess.metadata['variance_explanations'] = cleaned
            sess.metadata['grap24_variance_complete'] = passed
            budget_report_model.update_session(sess)

            return jsonify({
                'success': True,
                'grap24_variance_complete': passed,
                'grap24_variance_missing': missing,
                'grap24_lines_requiring_explanation': len(required),
                'variance_explanations': cleaned,
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/universal/session/<session_id>/export-acknowledged', methods=['POST'])
    @login_required
    @permission_required('review', 'download_pdf', 'export')
    def acknowledge_export_ready(session_id):
        """Persist CFO/FM acknowledgment that a finalized submission is noted for export."""
        try:
            data = request.get_json() or {}
            document_type = data.get('document_type') or _infer_document_type_from_session(session_id)
            if not document_type:
                return jsonify({'success': False, 'error': 'document_type is required'}), 400

            model = upload_handler.workflow_service._get_model_for_document_type(document_type)
            if not model:
                return jsonify({'success': False, 'error': 'Unsupported document type'}), 400

            sess = model.get_session(session_id)
            if not sess:
                return jsonify({'success': False, 'error': 'Session not found'}), 404

            from utils.session_workflow import effective_workflow_status

            if effective_workflow_status(sess) != 'approved':
                return jsonify({'success': False, 'error': 'Only finalized submissions can be acknowledged'}), 400

            if sess.metadata is None:
                sess.metadata = {}
            sess.metadata['export_ready_acknowledged_at'] = datetime.now().isoformat()
            sess.metadata['export_ready_acknowledged_by'] = get_current_user().id
            model.update_session(sess)

            return jsonify({
                'success': True,
                'session_id': session_id,
                'export_acknowledged': True,
            })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/universal/session/<session_id>/validation', methods=['GET'])
    @login_required
    def get_session_validation(session_id):
        """Validation checklist for review / approval (metadata + optional line data)."""
        try:
            document_type = request.args.get('document_type') or _infer_document_type_from_session(session_id)
            if not document_type:
                return jsonify({'success': False, 'error': 'document_type is required'}), 400

            from services.statement_validation_service import validate_for_review

            meta = {}
            model = upload_handler.get_service(document_type)
            if model and hasattr(model, 'get_session'):
                sess = model.get_session(session_id)
                if sess:
                    meta = getattr(sess, 'metadata', None) or {}

            lines = None
            if document_type == 'balance_sheet' and model:
                try:
                    raw_rows = _fetch_session_data_rows(model, session_id, document_type)
                    lines = [
                        r if isinstance(r, dict) else getattr(r, '__dict__', {})
                        for r in (raw_rows or [])
                    ]
                except Exception:
                    lines = None
            report = validate_for_review(
                document_type=document_type,
                lines=lines,
                session_metadata=meta,
            )
            return jsonify({'success': True, 'validation': report})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/universal/session/<session_id>/formula-breakdown', methods=['GET'])
    @login_required
    def get_session_formula_breakdown(session_id):
        """
        Session-backed formula / calculation transparency for review modal.
        Query: document_type (required), scope=session|calculation|line, calc_id, account_code, grap_code
        """
        try:
            document_type = request.args.get('document_type')
            if not document_type:
                return jsonify({'success': False, 'error': 'document_type is required'}), 400

            service = upload_handler.get_service(document_type)
            if not service:
                return jsonify({'success': False, 'error': f'Unsupported document type: {document_type}'}), 400

            result = service.get_session_summary(session_id)
            summary, err = _normalize_session_summary_for_breakdown(result)
            if err:
                err_lower = err.lower()
                code = 404 if 'not found' in err_lower or 'session' in err_lower and 'found' in err_lower else 400
                return jsonify({'success': False, 'error': err}), code

            scope = request.args.get('scope') or 'session'
            payload = build_formula_breakdown_response(
                summary,
                scope,
                calc_id=request.args.get('calc_id'),
                account_code=request.args.get('account_code'),
                grap_code=request.args.get('grap_code'),
            )
            return jsonify({'success': True, 'data': payload})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/universal/session/<session_id>/calculation-verify', methods=['POST'])
    @login_required
    @permission_required('review')
    def post_session_calculation_verify(session_id):
        """Persist reviewer verification flags on session.metadata.calculation_verifications."""
        try:
            data = request.get_json() or {}
            document_type = data.get('document_type')
            calc_id = data.get('calc_id')
            verified = data.get('verified', True)
            if not document_type:
                return jsonify({'success': False, 'error': 'document_type is required'}), 400
            if calc_id is None or str(calc_id).strip() == '':
                return jsonify({'success': False, 'error': 'calc_id is required'}), 400

            ok, err = _apply_calculation_verification(
                document_type, session_id, str(calc_id), bool(verified),
            )
            if not ok:
                return jsonify({'success': False, 'error': err}), 400
            return jsonify({'success': True, 'message': 'Verification saved'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    @app.route('/api/submit-mapping', methods=['POST'])
    @login_required
    @permission_required('process')
    def submit_universal_mapping():
        """
        Universal API endpoint to submit mapped financial data for review
        Handles all document types: Balance Sheets, Income Statements, Budget Reports
        """
        try:
            data = request.get_json()
            mapped_data = data.get('mapped_data')
            session_id = data.get('session_id')
            document_type = data.get('document_type')
            
            if not mapped_data:
                return jsonify({'success': False, 'error': 'No mapped data provided'}), 400
            
            if not session_id:
                return jsonify({'success': False, 'error': 'No session ID provided'}), 400

            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401

            # If document_type not provided, try to infer it from session
            if not document_type:
                document_type = _infer_document_type_from_session(session_id)
                if not document_type:
                    return jsonify({'success': False, 'error': 'Document type is required and could not be inferred'}), 400

            lock_resp = _period_lock_json_error(session_id, document_type)
            if lock_resp:
                return lock_resp

            locked_resp = _clerk_mapping_locked_json_error(session_id, document_type)
            if locked_resp:
                return locked_resp

            balanced, balance_error = require_balanced_session(session_id, document_type)
            if not balanced:
                return jsonify({'success': False, 'error': balance_error}), 400

            clerk_correction_note = (data.get('clerk_correction_note') or '').strip()

            result = upload_handler.workflow_service.submit_for_review(
                document_type=document_type,
                session_id=session_id,
                user_id=current_user.id,
                notes=f"Submitted {len(mapped_data)} mapped accounts for review",
                mapped_data=mapped_data,
                clerk_correction_note=clerk_correction_note,
            )
            
            if result['success']:
                return jsonify(result)
            else:
                return jsonify(result), 400
                
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error submitting mapping: {str(e)}'
            }), 500
    
    @app.route('/api/universal/discard-session', methods=['POST'])
    @login_required
    @permission_required('upload')
    def discard_ephemeral_session():
        """Remove a staging upload that did not proceed to submit-for-review."""
        try:
            data = request.get_json() or {}
            session_id = data.get('session_id')
            if not session_id:
                return jsonify({'success': False, 'error': 'No session ID provided'}), 400

            current_user = get_current_user()
            if not current_user:
                return jsonify({'success': False, 'error': 'User not authenticated'}), 401

            document_type = data.get('document_type') or _infer_document_type_from_session(session_id)
            if not document_type:
                return jsonify({'success': False, 'error': 'Could not determine document type'}), 400

            service = upload_handler.get_service(document_type)
            model = _document_service_model(service) if service else None
            if not model:
                return jsonify({'success': False, 'error': 'Invalid document type'}), 400

            session_row = model.get_session(session_id)
            if not session_row:
                return jsonify({'success': True, 'message': 'Session already removed'})

            if getattr(session_row, 'user_id', None) != current_user.id:
                return jsonify({'success': False, 'error': 'Not allowed to discard this session'}), 403

            from utils.session_workflow import session_is_ephemeral_staging, session_submitted_for_review
            if session_submitted_for_review(session_row):
                return jsonify({
                    'success': False,
                    'error': 'Cannot discard a submission that was already forwarded for review',
                }), 400

            if not session_is_ephemeral_staging(session_row):
                return jsonify({'success': False, 'error': 'Session is not a discardable staging upload'}), 400

            from services.cleanup_service import CleanupService
            result = CleanupService().cleanup_specific_session(session_id)
            if result.get('success'):
                return jsonify({'success': True, 'message': 'Staging upload removed'})
            return jsonify({'success': False, 'error': result.get('error', 'Discard failed')}), 400
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/universal/validate-balance', methods=['POST'])
    @login_required
    def validate_universal_balance():
        """
        Universal API endpoint to validate balance for all document types
        Returns balance check results for Balance Sheets, Income Statements, and Budget Reports
        """
        try:
            data = request.get_json()
            session_id = data.get('session_id')
            document_type = data.get('document_type')
            
            if not session_id:
                return jsonify({'success': False, 'error': 'No session ID provided'}), 400
            
            # If document_type not provided, try to infer it from session
            if not document_type:
                document_type = _infer_document_type_from_session(session_id)
                if not document_type:
                    return jsonify({'success': False, 'error': 'Document type is required and could not be inferred'}), 400

            lock_resp = _period_lock_json_error(session_id, document_type)
            if lock_resp:
                return lock_resp
            
            print(f"🔍 Universal balance check request - Session ID: {session_id}, Document Type: {document_type}")
            
            # Get the appropriate service for document type
            service = upload_handler.get_service(document_type)
            if not service:
                return jsonify({'success': False, 'error': f'Invalid document type: {document_type}'}), 400
            
            # Get the model from the service and retrieve data
            try:
                model = _document_service_model(service)
                if not model:
                    return jsonify({'success': False, 'error': f'Unable to get model for document type: {document_type}'}), 500
                
                # Get session and data from database
                session_data = model.get_session(session_id)
                if not session_data:
                    return jsonify({'success': False, 'error': f'Session not found for document type: {document_type}'}), 404
                
                data_rows = _fetch_session_data_rows(model, session_id, document_type)
                if not data_rows:
                    column_names = _column_names_from_session_metadata(session_data)
                    original_filename = getattr(session_data, 'original_filename', None) or getattr(
                        session_data, 'filename', ''
                    )
                    detected_type, mismatch_message = resolve_document_type_mismatch(
                        document_type,
                        column_names,
                        filename=original_filename,
                    )
                    if detected_type:
                        session_discarded = _discard_ephemeral_session(session_id, document_type)
                        return jsonify({
                            'success': False,
                            'format_mismatch': True,
                            'error_code': 'document_type_mismatch',
                            'selected_document_type': document_type,
                            'detected_document_type': detected_type,
                            'error': mismatch_message,
                            'session_discarded': session_discarded,
                        })
                    return jsonify({
                        'success': False,
                        'error': f'Document data not found for session_id: {session_id}',
                    })
                    
            except Exception as e:
                print(f"❌ Error accessing model data: {str(e)}")
                return jsonify({'success': False, 'error': f'Unable to access data for document type: {document_type}: {str(e)}'}), 500

            original_filename = getattr(session_data, 'original_filename', None) or getattr(
                session_data, 'filename', ''
            )
            column_names = column_names_from_data_rows(data_rows)
            if not column_names:
                column_names = _column_names_from_session_metadata(session_data)
            detected_type, mismatch_message = resolve_document_type_mismatch(
                document_type,
                column_names,
                filename=original_filename,
            )
            if detected_type:
                session_discarded = _discard_ephemeral_session(session_id, document_type)
                print(
                    f"⚠️ Balance check blocked — document type mismatch: "
                    f"selected={document_type}, detected={detected_type}"
                )
                return jsonify({
                    'success': False,
                    'format_mismatch': True,
                    'error_code': 'document_type_mismatch',
                    'selected_document_type': document_type,
                    'detected_document_type': detected_type,
                    'error': mismatch_message,
                    'session_discarded': session_discarded,
                })

            # Calculate balance based on document type
            balance_results = _calculate_balance_for_document_type(document_type, data_rows)

            detected_type, mismatch_message = resolve_document_type_mismatch(
                document_type,
                column_names,
                balance_results,
                filename=original_filename,
            )
            if detected_type:
                session_discarded = _discard_ephemeral_session(session_id, document_type)
                return jsonify({
                    'success': False,
                    'format_mismatch': True,
                    'error_code': 'document_type_mismatch',
                    'selected_document_type': document_type,
                    'detected_document_type': detected_type,
                    'error': mismatch_message,
                    'session_discarded': session_discarded,
                })

            session_discarded = False
            if document_type == 'balance_sheet' and not balance_results.get('is_balanced'):
                from services.cleanup_service import CleanupService
                from utils.session_workflow import session_is_ephemeral_staging
                if session_is_ephemeral_staging(session_data):
                    discard = CleanupService().cleanup_specific_session(session_id)
                    session_discarded = discard.get('success', False)
            
            # Debug logging for budget reports
            if document_type == 'budget_report':
                print(f"🔍 Budget Report Balance Calculation:")
                print(f"   Total Budget: {balance_results.get('total_budget', 0)}")
                print(f"   Total Actual: {balance_results.get('total_actual', 0)}")
                print(f"   Variance: {balance_results.get('variance', 0)}")
                print(f"   is_balanced: {balance_results.get('is_balanced', False)}")
                print(f"   Tolerance Check: abs({balance_results.get('variance', 0)}) < 0.01 = {abs(balance_results.get('variance', 0)) < 0.01}")
            
            return jsonify({
                'success': True,
                'document_type': document_type,
                'balance_check': balance_results,
                'session_discarded': session_discarded,
            })
            
        except Exception as e:
            print(f"❌ Universal balance check error: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Balance check error: {str(e)}'
            }), 500

    # Register the /api/transactions/pending endpoint
    register_transactions_pending_route(app)
    
    # Register the /api/transactions/approval-chain endpoint
    register_approval_chain_route(app)
    
    # Register the /api/transactions/history endpoint
    register_transaction_history_route(app)

    register_line_item_comment_routes(app)

def _income_statement_row_amount(row, field_names):
    """Read a numeric field from a data row object or its embedded dicts."""
    for name in field_names:
        val = getattr(row, name, None)
        if val is not None:
            try:
                return float(val)
            except (TypeError, ValueError):
                pass
    parsed = _row_dict_field(row, *field_names)
    if parsed is not None:
        return parsed
    return None


def _classify_income_statement_row(row):
    """Return 'revenue', 'expense', 'skip', or None."""
    if _should_skip_balance_row(row):
        return 'skip'

    category_val = (
        getattr(row, 'category', None)
        or _row_dict_field(row, 'category', 'type', 'classification')
    )
    category = str(category_val or '').lower()
    if category and 'summary' in category:
        return 'skip'

    code = str(getattr(row, 'account_code', None) or _row_dict_field(row, 'account_code', 'code') or '').strip().upper()
    desc = str(
        getattr(row, 'account_description', None)
        or getattr(row, 'account_name', None)
        or _row_dict_field(row, 'account_description', 'account_name', 'description')
        or ''
    ).lower()

    if category:
        if any(t in category for t in ('revenue', 'income', 'grant', 'sales', 'fees')):
            return 'revenue'
        if any(t in category for t in ('expense', 'cost', 'expenditure')):
            return 'expense'

    if code.startswith('4') or code.startswith('REV'):
        return 'revenue'
    if code.startswith('5') or code.startswith('EXP'):
        return 'expense'

    text = f'{code} {desc}'.lower()
    if any(t in text for t in ('revenue', 'income', 'grant')):
        return 'revenue'
    if any(t in text for t in ('expense', 'cost', 'expenditure')):
        return 'expense'
    return None


def _amount_for_income_kind(row, kind):
    """Pick the best numeric column for revenue/expense classification."""
    credit = _income_statement_row_amount(row, ('credit_balance', 'credit'))
    debit = _income_statement_row_amount(row, ('debit_balance', 'debit'))
    amount = _income_statement_row_amount(row, ('amount', 'net_balance', 'balance', 'value'))
    if kind == 'revenue':
        if credit is not None and credit > 0:
            return credit
        if amount is not None and amount > 0:
            return amount
        if debit is not None and debit < 0:
            return abs(debit)
    if kind == 'expense':
        if debit is not None and debit > 0:
            return debit
        if amount is not None and amount > 0:
            return amount
        if credit is not None and credit < 0:
            return abs(credit)
    if amount is not None:
        return abs(amount)
    return None


def _row_dict_field(row, *field_names):
    """Read a numeric field from row raw_data / processed_data (case-insensitive)."""
    import json
    for attr in ('processed_data', 'raw_data'):
        source = getattr(row, attr, None)
        if source is None:
            continue
        if isinstance(source, str):
            try:
                source = json.loads(source)
            except (json.JSONDecodeError, TypeError):
                continue
        if not isinstance(source, dict):
            continue
        for key, val in source.items():
            norm = str(key).lower().replace(' ', '_').replace('%', '')
            for fn in field_names:
                if norm == str(fn).lower().replace(' ', '_').replace('%', ''):
                    try:
                        text = str(val).replace(',', '').replace('R', '').strip()
                        if text.endswith('%'):
                            text = text[:-1]
                        return float(text) if text else 0.0
                    except (ValueError, TypeError):
                        return None
    return None


def _row_has_debit_credit(row) -> bool:
    debit_val = getattr(row, 'debit_balance', None) or getattr(row, 'debit', None)
    credit_val = getattr(row, 'credit_balance', None) or getattr(row, 'credit', None)
    return debit_val is not None or credit_val is not None


def _should_skip_balance_row(row) -> bool:
    """Exclude total/subtotal lines from trial balance sums."""
    if getattr(row, 'is_total_row', False) or getattr(row, 'is_subtotal_row', False):
        return True
    code = str(getattr(row, 'account_code', None) or '').strip().upper()
    desc = str(
        getattr(row, 'account_description', None)
        or getattr(row, 'description', None)
        or ''
    ).strip().upper()
    if code in ('TOTALS', 'TOTAL', 'GRAND TOTAL'):
        return True
    if desc.startswith('TOTAL') or desc == 'TOTALS':
        return True
    return False


def _balance_result_payload(
    *,
    total_debits: float = 0.0,
    total_credits: float = 0.0,
    difference: float = 0.0,
    balance_type: str,
    **extra,
) -> dict:
    diff = float(difference)
    abs_diff = abs(diff)
    payload = {
        'total_debits': total_debits,
        'total_credits': total_credits,
        'difference': diff,
        'balance_difference': abs_diff,
        'is_balanced': abs_diff < 0.01,
        'balance_type': balance_type,
    }
    payload.update(extra)
    return payload


def _sum_debit_credit_from_rows(data_rows) -> dict:
    """Sum debit/credit columns excluding total/subtotal rows."""
    total_debits = 0.0
    total_credits = 0.0
    for row in data_rows:
        if _should_skip_balance_row(row):
            continue
        debit_val = getattr(row, 'debit_balance', None)
        if debit_val is None:
            debit_val = getattr(row, 'debit', None)
        if debit_val is None:
            debit_val = _row_dict_field(row, 'debit_balance', 'debit balance', 'debit')
        credit_val = getattr(row, 'credit_balance', None)
        if credit_val is None:
            credit_val = getattr(row, 'credit', None)
        if credit_val is None:
            credit_val = _row_dict_field(row, 'credit_balance', 'credit balance', 'credit')
        total_debits += float(debit_val) if debit_val is not None else 0.0
        total_credits += float(credit_val) if credit_val is not None else 0.0
    difference = total_debits - total_credits
    return _balance_result_payload(
        total_debits=total_debits,
        total_credits=total_credits,
        difference=difference,
        balance_type='debits_vs_credits',
    )


def _calculate_balance_for_document_type(document_type, data_rows):
    """Calculate balance based on document type"""
    print(f"🔍 Calculating balance for document type: {document_type}")
    print(f"🔍 Number of data rows: {len(data_rows)}")
    print(f"🔍 First few rows: {data_rows[:3] if data_rows else 'No data'}")
    
    total_debits = 0.0
    total_credits = 0.0
    total_revenue = 0.0
    total_expenses = 0.0
    total_budget = 0.0
    total_actual = 0.0
    
    for row in data_rows:
        if document_type == 'balance_sheet':
            continue  # handled below after format detection
            
        elif document_type == 'income_statement':
            kind = _classify_income_statement_row(row)
            if kind == 'skip' or not kind:
                continue
            amt = _amount_for_income_kind(row, kind)
            if amt is None or amt == 0:
                continue
            if kind == 'revenue':
                total_revenue += amt
            else:
                total_expenses += amt
            
        elif document_type == 'budget_report':
            # Budget report: check budget vs actual
            budget_val = getattr(row, 'budget_amount', None) or getattr(row, 'budget', None)
            actual_val = getattr(row, 'actual_amount', None) or getattr(row, 'actual', None)
            
            # For budget reports, we'll treat budget as "debits" and actual as "credits" for consistency
            total_budget += float(budget_val) if budget_val is not None else 0.0
            total_actual += float(actual_val) if actual_val is not None else 0.0
    
    # Return appropriate balance results based on document type
    if document_type == 'balance_sheet':
        has_debit_credit = any(_row_has_debit_credit(row) for row in data_rows)
        has_budget_actual = any(
            _row_dict_field(row, 'budget_amount', 'budget amount') is not None
            or _row_dict_field(row, 'actual_amount', 'actual amount') is not None
            for row in data_rows
        )

        if has_debit_credit:
            tb_payload = _sum_debit_credit_from_rows(data_rows)
            total_debits = tb_payload['total_debits']
            total_credits = tb_payload['total_credits']
            balance_type = 'debits_vs_credits'
            return _balance_result_payload(
                total_debits=total_debits,
                total_credits=total_credits,
                difference=tb_payload['difference'],
                balance_type=balance_type,
            )
        elif has_budget_actual:
            for row in data_rows:
                if _should_skip_balance_row(row):
                    continue
                budget_val = _row_dict_field(row, 'budget_amount', 'budget amount')
                actual_val = _row_dict_field(row, 'actual_amount', 'actual amount')
                if budget_val is not None:
                    total_budget += budget_val
                if actual_val is not None:
                    total_actual += actual_val
            from services.budget_variance_service import compute_session_variance

            total_debits = total_budget
            total_credits = total_actual
            variance = float(compute_session_variance(total_budget, total_actual))
            return _balance_result_payload(
                total_debits=total_debits,
                total_credits=total_credits,
                difference=variance,
                balance_type='budget_vs_actual',
                total_budget=total_budget,
                total_actual=total_actual,
                variance=variance,
            )
        else:
            for row in data_rows:
                if _should_skip_balance_row(row):
                    continue
                net_val = getattr(row, 'net_balance', None)
                if net_val is None:
                    continue
                net_float = float(net_val)
                if net_float > 0:
                    total_debits += net_float
                elif net_float < 0:
                    total_credits += abs(net_float)
            balance_type = 'net_balance_split'

        difference = total_debits - total_credits
        return _balance_result_payload(
            total_debits=total_debits,
            total_credits=total_credits,
            difference=difference,
            balance_type=balance_type,
        )
    elif document_type == 'income_statement':
        net_income = total_revenue - total_expenses
        has_lines = total_revenue > 0 or total_expenses > 0
        has_debit_credit = any(_row_has_debit_credit(row) for row in data_rows)
        result = {
            'total_revenue': total_revenue,
            'total_expenses': total_expenses,
            'net_income': net_income,
            'has_performance_lines': has_lines,
            'has_debit_credit_format': has_debit_credit,
            'balance_type': 'revenue_vs_expenses',
        }
        if has_debit_credit:
            tb_payload = _sum_debit_credit_from_rows(data_rows)
            result.update({
                'total_debits': tb_payload['total_debits'],
                'total_credits': tb_payload['total_credits'],
                'difference': tb_payload['difference'],
                'balance_difference': tb_payload['balance_difference'],
                'debit_credit_balanced': tb_payload['is_balanced'],
            })
            result['is_balanced'] = has_lines and tb_payload['is_balanced']
        else:
            result['is_balanced'] = has_lines
        return result
    elif document_type == 'budget_report':
        from services.budget_variance_service import compute_session_variance

        variance = float(compute_session_variance(total_budget, total_actual))
        has_lines = total_budget > 0 or total_actual > 0
        return {
            'total_budget': total_budget,
            'total_actual': total_actual,
            'variance': variance,
            # Line-level variance is expected; upload succeeds when rows were captured.
            'is_balanced': has_lines,
            'has_aggregate_variance': abs(variance) >= 0.01,
            'balance_type': 'budget_vs_actual',
        }


def compute_submission_balance_totals(session_id: str, document_type: str) -> dict:
    """Revenue/expense/debit/credit totals from stored session rows for status pages."""
    service = upload_handler.get_service(document_type)
    model = _document_service_model(service) if service else None
    if not model:
        return {}
    try:
        rows = _fetch_session_data_rows(model, session_id, document_type)
    except (AttributeError, Exception):
        return {}
    if not rows:
        return {}
    return _calculate_balance_for_document_type(document_type, rows) or {}


def require_balanced_session(session_id: str, document_type: str | None = None) -> tuple[bool, str | None]:
    """
    Enforce upload/submit balance rules before process/submit for all document types.
    Returns (ok, error_message).
    """
    if not document_type:
        document_type = _infer_document_type_from_session(session_id)
    if not document_type:
        return False, "Document type is required and could not be inferred"

    service = upload_handler.get_service(document_type)
    if not service:
        return False, f"Invalid document type: {document_type}"

    model = _document_service_model(service)
    if not model:
        return False, f"Unable to load model for {document_type}"

    if not model.get_session(session_id):
        return False, "Session not found"

    try:
        data_rows = _fetch_session_data_rows(model, session_id, document_type)
    except AttributeError:
        return False, "Unable to read session data for balance validation"

    if not data_rows:
        return False, "No data found for balance validation"

    balance_results = _calculate_balance_for_document_type(document_type, data_rows)

    if document_type == "balance_sheet":
        if balance_results.get("is_balanced"):
            return True, None
        difference = abs(balance_results.get("difference", 0))
        return False, (
            f"{ClerkWorkflowMessages.BALANCE_REQUIRED} "
            f"Difference: R {difference:,.2f}"
        )

    if document_type == "income_statement":
        if balance_results.get("has_debit_credit_format") and balance_results.get("debit_credit_balanced") is False:
            difference = abs(balance_results.get("difference", 0))
            return False, (
                f"{ClerkWorkflowMessages.BALANCE_REQUIRED} "
                f"Difference: R {difference:,.2f}"
            )
        if not balance_results.get("has_performance_lines"):
            return False, ClerkWorkflowMessages.INCOME_STATEMENT_REQUIRED
        return True, None

    if document_type == "budget_report":
        if balance_results.get("is_balanced"):
            return True, None
        return False, ClerkWorkflowMessages.BUDGET_REPORT_REQUIRED

    return True, None


# Add the missing /api/transactions/pending endpoint
def register_transactions_pending_route(app):
    """
    Register ``/api/transactions/pending``.

    **Note:** The handler uses ``UniversalWorkflowService.get_pending_approvals``, which
    aggregates **document upload sessions** awaiting manager/CFO action — not rows from
    the ``transaction_approvals`` table. For TX-style queues use
    ``approval_facade.transactions.get_pending_transactions`` and a dedicated route if
    needed.
    """
    
    @app.route('/api/transactions/pending', methods=['GET'])
    @login_required
    @permission_required('review')  # Finance Manager and CFO can view pending
    def get_pending_transactions():
        """Get pending transactions for approval"""
        try:
            user = get_current_user()
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not authenticated'
                }), 401

            # Import Universal Workflow Service
            workflow_service = UniversalWorkflowService()

            try:
                limit = min(max(int(request.args.get('limit', 50)), 1), 200)
            except (TypeError, ValueError):
                limit = 50
            try:
                offset = max(int(request.args.get('offset', 0)), 0)
            except (TypeError, ValueError):
                offset = 0

            result = workflow_service.get_pending_approvals(
                user.id, limit=limit, offset=offset
            )

            if not result['success']:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Failed to get pending approvals')
                }), 500

            # Transform the data to match expected format
            pending_approvals = result.get('pending_approvals', [])
            pending_transactions = []
            
            for approval in pending_approvals:
                # Create user-friendly transaction ID
                doc_type_abbr = {
                    'income_statement': 'INC',
                    'balance_sheet': 'BAL',
                    'budget_report': 'BUD',
                    'financial_statement': 'FIN'
                }.get(approval['document_type'], 'DOC')
                
                # Extract last 8 chars of session ID for reference
                short_id = approval['session_id'][-8:] if approval['session_id'] else 'UNKNOWN'
                readable_id = f"{doc_type_abbr}-{short_id.upper()}"
                
                # Convert to transaction format expected by frontend
                transaction = {
                    'transaction_id': readable_id,  # User-friendly ID instead of UUID
                    'session_id': approval['session_id'],  # Keep original for operations
                    'transaction_type': approval['document_type'],
                    'creator_name': approval.get('submitted_by', 'Unknown User'),
                    'created_at': approval.get('submitted_at', approval.get('created_at', '')),
                    'reason': approval.get('filename', ''),
                    'period_name': approval.get('period_name') or '',
                    'total_rows': approval.get('total_rows', 0),
                    'transaction_data': {
                        'document_type': approval['document_type'],
                        'filename': approval.get('filename', ''),
                        'total_rows': approval.get('total_rows', 0),
                        'total_columns': approval.get('total_columns', 0),
                    },
                    'required_approvals': ['FINANCE_MANAGER', 'CFO'] if approval['document_type'] in ['income_statement', 'balance_sheet', 'budget_report'] else ['FINANCE_MANAGER'],
                    'current_approvals': [],
                    'status': approval.get('status'),  # Pure database status, no fallback
                    'metadata': approval.get('metadata') or {},
                    'priority': 'medium'  # Default priority
                }
                pending_transactions.append(transaction)

            return jsonify({
                'success': True,
                'pending_transactions': pending_transactions,
                'count': len(pending_transactions),
                'total_count': result.get('total_count', len(pending_transactions)),
                'limit': result.get('limit', limit),
                'offset': result.get('offset', offset),
                'has_more': result.get('has_more', False),
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error fetching pending transactions: {str(e)}'
            }), 500

def register_approval_chain_route(app):
    """Register the /api/transactions/approval-chain endpoint"""
    print("🔍 DEBUG: Registering approval chain route...")
    
    try:
        @app.route('/api/transactions/approval-chain/<transaction_id>', methods=['GET'])
        @login_required
        @permission_required('review')  # Finance Manager and CFO can view approval chains
        def get_approval_chain(transaction_id):
            print("🔍 DEBUG: Approval chain route function called!")
            """Get approval chain for a specific transaction"""
            print(f"🔍 DEBUG: Approval chain request received for transaction_id: {transaction_id}")
            
            try:
                user = get_current_user()
                print(f"🔍 DEBUG: Current user: {user}")
                if not user:
                    print(f"🔍 DEBUG: No user authenticated")
                    return jsonify({
                        'success': False,
                        'error': 'User not authenticated'
                    }), 401

            # Import Audit Model and Workflow Service
                from models.audit_models import AuditTrailModel
                from services.universal_workflow_service import UniversalWorkflowService
                audit_model = AuditTrailModel()
                workflow_service = UniversalWorkflowService()

                # Try to get approval chain using the transaction_id first
                print(f"🔍 DEBUG: Trying approval chain lookup with transaction_id: {transaction_id}")
                approval_chain = audit_model.get_approval_chain(transaction_id)
                print(f"🔍 DEBUG: Approval chain result (direct lookup): {len(approval_chain) if approval_chain else 0} items")
                
                # If not found, try to find the full session_id and use that
                if not approval_chain and '-' in transaction_id:
                    print(f"🔍 DEBUG: Direct lookup failed, trying session ID lookup")
                    # Extract the session ID part from readable format like "INC-9DEE02A9"
                    parts = transaction_id.split('-')
                    print(f"🔍 DEBUG: Transaction ID parts: {parts}")
                    if len(parts) >= 2:
                        session_suffix = parts[1]
                        print(f"🔍 DEBUG: Looking for session suffix: {session_suffix}")
                        # Get pending approvals to find the full session ID
                        pending_approvals = workflow_service.get_pending_approvals(user.id)
                        print(f"🔍 DEBUG: Pending approvals: {len(pending_approvals.get('pending_approvals', []))} items")
                        for approval in pending_approvals.get('pending_approvals', []):
                            print(f"🔍 DEBUG: Checking approval session: {approval.get('session_id')}")
                            if approval['session_id'] and approval['session_id'].endswith(session_suffix):
                                print(f"🔍 DEBUG: Found matching session: {approval['session_id']}")
                                # Try with the full session ID
                                approval_chain = audit_model.get_approval_chain(approval['session_id'])
                                print(f"🔍 DEBUG: Approval chain result (session lookup): {len(approval_chain) if approval_chain else 0} items")
                                if approval_chain:
                                    break
                
                if not approval_chain:
                    print(f"🔍 DEBUG: No approval chain found for transaction {transaction_id}")
                    # Check if this is a session ID lookup issue
                    if '-' in transaction_id:
                        print(f"🔍 DEBUG: This might be a new transaction that hasn't been approved yet")
                        return jsonify({
                            'success': False,
                            'error': f'No approval chain found for transaction {transaction_id}. This transaction may not have been processed through the approval workflow yet.'
                        }), 404
                    else:
                        return jsonify({
                            'success': False,
                            'error': 'No approval chain found for this transaction'
                        }), 404

                print(f"🔍 DEBUG: Found approval chain with {len(approval_chain)} items")
                # Get transaction status
                
                # Extract session_id from transaction_id if it's a readable format
                if '-' in transaction_id:
                    # Format like "INC-9DEE02A9" - extract the session ID part
                    parts = transaction_id.split('-')
                    if len(parts) >= 2:
                        session_id = parts[1]
                        # Try to find the full session ID
                        pending_approvals = workflow_service.get_pending_approvals(user.id)
                        for approval in pending_approvals.get('pending_approvals', []):
                            if approval['session_id'] and approval['session_id'].endswith(session_id):
                                session_id = approval['session_id']
                                break
                    else:
                        session_id = transaction_id
                else:
                    session_id = transaction_id

                # Get transaction details
                transaction_status = 'pending'
                source = 'unknown'
                
                # Try to get transaction details from workflow service
                try:
                    # This would need to be implemented in the workflow service
                    # For now, we'll use default values
                    source = 'financial_document'
                except:
                    pass

                print(f"🔍 DEBUG: Returning successful response with approval chain")
                return jsonify({
                    'success': True,
                    'approval_chain': approval_chain,
                    'source': source,
                    'transaction_status': transaction_status
                })
                    
            except Exception as e:
                print(f"🔍 DEBUG: Exception in approval chain endpoint: {str(e)}")
                import traceback
                traceback.print_exc()
                return jsonify({
                    'success': False,
                    'error': f'Error fetching approval chain: {str(e)}'
                }), 500
                    
        print("🔍 DEBUG: Approval chain route registered successfully!")
        print(f"🔍 DEBUG: Route function name: {get_approval_chain.__name__}")
        print(f"🔍 DEBUG: Route function exists: {get_approval_chain is not None}")
        
    except Exception as e:
        print(f"🔍 DEBUG: Error registering approval chain route: {str(e)}")
        import traceback
        traceback.print_exc()


def register_transaction_history_route(app):
    """Register the /api/transactions/history endpoint"""
    
    @app.route('/api/transactions/history', methods=['GET'])
    @login_required
    @permission_required('review')  # Finance Manager and CFO can view history
    def get_transaction_history():
        """Session submission history (not the ``transaction_approvals`` table).

        With no ``status`` query param, returns role-appropriate settled decisions only
        (no pending — use ``GET /api/transactions/pending`` for the active queue).
        CFO: ``approved``, ``rejected``. FM: those plus ``approved_by_manager``,
        ``rejected_by_manager``.
        """
        try:
            user = get_current_user()
            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not authenticated'
                }), 401

            status_filter = (request.args.get('status') or '').strip()
            user_filter = request.args.get('user_id', '')
            limit = int(request.args.get('limit', 50))

            from utils.session_workflow import parse_iso_datetime, resolve_history_statuses

            role = getattr(user, 'role', '') or ''
            statuses = resolve_history_statuses(role, status_filter)

            workflow_service = UniversalWorkflowService()
            settled = workflow_service.collect_settled_history_sessions(
                statuses,
                limit=limit,
                user_filter=user_filter,
            )

            from services.export_log_service import export_log_service

            session_ids = [row['session'].id for row in settled if getattr(row.get('session'), 'id', None)]
            pdf_exported_ids = export_log_service.session_ids_with_pdf_export(session_ids)

            all_transactions = []
            for row in settled:
                session = row['session']
                display_status = row.get('display_status') or getattr(session, 'status', '')

                submitted_by_id = session.user_id
                submitted_by_user = get_supabase_auth().get_user_by_id(submitted_by_id)
                submitted_by_name = (
                    submitted_by_user.get('full_name', 'Unknown User')
                    if submitted_by_user
                    else 'Unknown User'
                )

                doc_type_abbr = {
                    'income_statement': 'INC',
                    'balance_sheet': 'BAL',
                    'budget_report': 'BUD',
                    'financial_statement': 'FIN',
                }.get(session.document_type, 'DOC')

                short_id = session.id[-8:] if session.id else 'UNKNOWN'
                readable_id = f"{doc_type_abbr}-{short_id.upper()}"

                created_dt = parse_iso_datetime(session.created_at)
                updated_dt = parse_iso_datetime(session.updated_at)
                created_at = created_dt.isoformat() if created_dt else (str(session.created_at or ''))
                updated_at = updated_dt.isoformat() if updated_dt else (str(session.updated_at or ''))

                md = getattr(session, 'metadata', None) or {}
                sid = session.id
                all_transactions.append({
                    'transaction_id': readable_id,
                    'session_id': sid,
                    'transaction_type': session.document_type,
                    'creator_name': submitted_by_name,
                    'created_at': created_at or '',
                    'updated_at': updated_at or '',
                    'status': display_status,
                    'reason': session.filename or '',
                    'pdf_exported': sid in pdf_exported_ids,
                    'export_acknowledged': bool(md.get('export_ready_acknowledged_at')),
                    'metadata': md,
                    'transaction_data': {
                        'document_type': session.document_type,
                        'filename': session.filename,
                        'total_rows': session.total_rows,
                        'total_columns': session.total_columns,
                    },
                })

            return jsonify({
                'success': True,
                'transactions': all_transactions,
                'count': len(all_transactions)
            })
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': f'Error fetching transaction history: {str(e)}'
            }), 500


def _comment_resolve_session(session_id: str, document_type: str = None):
    """Locate session across universal document types."""
    svc = UniversalWorkflowService()
    order = []
    if document_type:
        order.append(document_type)
    for dt in ['balance_sheet', 'income_statement', 'budget_report']:
        if dt not in order:
            order.append(dt)
    for dt in order:
        model = svc._get_model_for_document_type(dt)
        if not model:
            continue
        sess = model.get_session(session_id)
        if sess:
            return model, sess, dt
    return None, None, None


def _persist_session_metadata(model, session):
    """Save session metadata changes."""
    if hasattr(model, 'update_session'):
        model.update_session(session)
    else:
        model.update_session_status(session.id, session.status, session.metadata or {})


def register_line_item_comment_routes(app):
    """Line-item review comments stored on session.metadata['line_item_comments']."""

    @app.route('/api/comments/line-item/<session_id>', methods=['GET'])
    @login_required
    def list_line_item_comments(session_id):
        """
        Comments live on session.metadata['line_item_comments'].

        Params: ``document_type`` (optional resolver), ``account_code`` (optional filter).

        Readers: ``review`` (any session), or owning user with ``process`` (clerks viewing
        their submissions). Full list returned when ``account_code`` is omitted if allowed.
        """
        try:
            doc_type = request.args.get('document_type')
            _, sess, _ = _comment_resolve_session(session_id, doc_type)
            if not sess:
                return jsonify({'success': False, 'error': 'Session not found'}), 404

            user = get_current_user()
            if not user:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401

            sess_user = getattr(sess, 'user_id', None)
            owns = str(sess_user or '') == str(user.id)

            can_review = user.has_permission('review')
            can_process = user.has_permission('process')

            # Approve-capable reviewers often also have review; allow read for review or owning clerk
            if not can_review and not (owns and can_process):
                return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403

            account_code = request.args.get('account_code')
            from utils.session_metadata_helpers import resolve_line_item_comments

            comments = resolve_line_item_comments(sess.metadata or {})

            if account_code:
                filtered = [c for c in comments if str(c.get('account_code')) == str(account_code)]
                return jsonify({'success': True, 'comments': filtered})

            # Full list — allow reviewers for any session, or clerks only for their own
            if owns or can_review:
                return jsonify({'success': True, 'comments': comments})

            return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/comments/line-item', methods=['POST'])
    @login_required
    @permission_required('approve', 'final_approve')
    def create_line_item_comment():
        try:
            data = request.get_json() or {}
            session_id = data.get('transaction_id') or data.get('session_id')
            document_type = data.get('document_type')
            if not session_id:
                return jsonify({'success': False, 'error': 'session_id required'}), 400
            model, sess, resolved_type = _comment_resolve_session(session_id, document_type)
            if not sess:
                return jsonify({'success': False, 'error': 'Session not found'}), 404
            if sess.metadata is None:
                sess.metadata = {}
            comments = list(sess.metadata.get('line_item_comments') or [])
            entry = {
                'id': str(uuid.uuid4()),
                'account_code': data.get('account_code'),
                'comment_type': data.get('comment_type', 'general'),
                'subject': data.get('subject', ''),
                'comment_text': data.get('comment_text', ''),
                'correction_suggestion': data.get('correction_suggestion', ''),
                'urgency_level': data.get('urgency_level', 'medium'),
                'author_id': data.get('author_id', ''),
                'author_name': data.get('author_name', ''),
                'created_at': datetime.now().isoformat(),
                'document_type': resolved_type,
            }
            comments.append(entry)
            sess.metadata['line_item_comments'] = comments
            _persist_session_metadata(model, sess)
            return jsonify({'success': True, 'comment': entry})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/comments/line-item/<session_id>/<comment_id>', methods=['PUT', 'DELETE'])
    @login_required
    @permission_required('approve', 'final_approve')
    def modify_line_item_comment(session_id, comment_id):
        try:
            if request.method == 'PUT':
                data = request.get_json() or {}
                document_type = data.get('document_type')
                model, sess, _ = _comment_resolve_session(session_id, document_type)
                if not sess:
                    return jsonify({'success': False, 'error': 'Session not found'}), 404
                if sess.metadata is None:
                    sess.metadata = {}
                comments = list(sess.metadata.get('line_item_comments') or [])
                updated = None
                for i, c in enumerate(comments):
                    if c.get('id') == comment_id:
                        c.update({
                            'comment_type': data.get('comment_type', c.get('comment_type')),
                            'subject': data.get('subject', c.get('subject')),
                            'comment_text': data.get('comment_text', c.get('comment_text')),
                            'correction_suggestion': data.get('correction_suggestion', c.get('correction_suggestion')),
                            'urgency_level': data.get('urgency_level', c.get('urgency_level')),
                            'updated_at': datetime.now().isoformat(),
                        })
                        comments[i] = c
                        updated = c
                        break
                if not updated:
                    return jsonify({'success': False, 'error': 'Comment not found'}), 404
                sess.metadata['line_item_comments'] = comments
                _persist_session_metadata(model, sess)
                return jsonify({'success': True, 'comment': updated})

            doc_type = request.args.get('document_type')
            model, sess, _ = _comment_resolve_session(session_id, doc_type)
            if not sess:
                return jsonify({'success': False, 'error': 'Session not found'}), 404
            if sess.metadata is None:
                sess.metadata = {}
            prev = sess.metadata.get('line_item_comments') or []
            comments = [c for c in prev if c.get('id') != comment_id]
            if len(comments) == len(prev):
                return jsonify({'success': False, 'error': 'Comment not found'}), 404
            sess.metadata['line_item_comments'] = comments
            _persist_session_metadata(model, sess)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
