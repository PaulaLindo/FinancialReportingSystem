"""
Finance Manager Dashboard Routes
Handles Finance Manager approvals, dashboard, and review workflows
Part of Phase 1: Route-service integration + FM dashboard
"""

from flask import jsonify, request, session, render_template, flash, redirect, url_for
from functools import wraps
from datetime import datetime
import logging

# Import authentication and services
from models.supabase_auth_models import get_current_user, get_role_description
from services.universal_workflow_service import UniversalWorkflowService

logger = logging.getLogger(__name__)


def login_required(f):
    """Require login; JSON 401 for /api/, redirect to login for pages."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def permission_required(*allowed_roles):
    """Require role; JSON for /api/, redirect for HTML pages."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'error': 'Authentication required'}), 401
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))

            if user.role not in allowed_roles:
                if request.path.startswith('/api/'):
                    return jsonify({'success': False, 'error': 'Insufficient permissions'}), 403
                flash('You do not have access to that page.', 'warning')
                return redirect(url_for('dashboard'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def register_finance_manager_routes(app):
    """Register Finance Manager routes"""
    
    workflow_service = UniversalWorkflowService()
    
    # ==================== DASHBOARD ROUTES ====================
    
    @app.route('/finance-manager/dashboard', methods=['GET'])
    @login_required
    @permission_required('FINANCE_MANAGER', 'CFO')
    def finance_manager_dashboard():
        """Legacy URL: merged into Review queue."""
        return redirect(url_for('finance_manager_review_queue'))

    @app.route('/finance-manager/review-queue', methods=['GET'])
    @login_required
    @permission_required('FINANCE_MANAGER', 'CFO')
    def finance_manager_review_queue():
        """Pending submissions: FM sees pending_review; CFO sees pending_cfo & approved_by_manager."""
        try:
            user = get_current_user()
            return render_template(
                'finance_manager_review_queue.html',
                current_user=user,
                get_role_description=get_role_description,
            )
        except Exception as e:
            logger.error(f"Error loading FM review queue: {str(e)}")
            flash('Could not load the review queue.', 'error')
            return redirect(url_for('dashboard'))

    @app.route('/finance-manager/history', methods=['GET'])
    @login_required
    @permission_required('FINANCE_MANAGER', 'CFO')
    def finance_manager_history():
        """Settled submission history for FM/CFO (no pending — active queue is Review)."""
        try:
            user = get_current_user()
            return render_template(
                'finance_manager_history.html',
                current_user=user,
                get_role_description=get_role_description,
            )
        except Exception as e:
            logger.error(f"Error loading FM history: {str(e)}")
            flash('Could not load submission history.', 'error')
            return redirect(url_for('finance_manager_review_queue'))
    
    
    # ==================== API ENDPOINTS ====================
    
    @app.route('/api/finance-manager/pending-approvals', methods=['GET'])
    @login_required
    @permission_required('FINANCE_MANAGER', 'CFO')
    def get_pending_approvals_api():
        """
        Get all pending approvals for Finance Manager/CFO
        Returns submissions awaiting manager approval
        """
        try:
            user = get_current_user()
            user_id = user.id if user else session.get('user_id')
            
            logger.info(f"📡 Fetching pending approvals for user {user_id}")
            
            # Call workflow service to get pending approvals
            result = workflow_service.get_pending_approvals(user_id)
            
            if not result['success']:
                logger.warning(f"⚠️ Error getting pending approvals: {result.get('error')}")
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Failed to fetch pending approvals'),
                    'pending_approvals': []
                }), 200
            
            pending_approvals = result.get('pending_approvals', [])
            logger.info(f"✅ Found {len(pending_approvals)} pending approvals")
            
            return jsonify({
                'success': True,
                'pending_approvals': pending_approvals,
                'total_count': result.get('total_count', 0)
            }), 200
            
        except Exception as e:
            logger.error(f"❌ Error in get_pending_approvals_api: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Server error: {str(e)}',
                'pending_approvals': []
            }), 500
    
    
    @app.route('/api/finance-manager/dashboard-stats', methods=['GET'])
    @login_required
    @permission_required('FINANCE_MANAGER', 'CFO')
    def get_dashboard_stats():
        """
        Get dashboard statistics for Finance Manager
        Returns counts of pending, approved, rejected approvals
        """
        try:
            user = get_current_user()
            user_id = user.id if user else session.get('user_id')
            
            logger.info(f"📊 Fetching dashboard stats for user {user_id}")
            
            # Get pending approvals
            pending_result = workflow_service.get_pending_approvals(user_id)
            pending_count = len(pending_result.get('pending_approvals', [])) if pending_result['success'] else 0
            
            # Calculate statistics
            stats = {
                'pending_count': pending_count,
                'approved_today': 0,  # TODO: Implement tracking
                'rejected_today': 0,  # TODO: Implement tracking
                'completed_this_week': 0,  # TODO: Implement tracking
                'timestamp': datetime.now().isoformat()
            }
            
            logger.info(f"✅ Dashboard stats: {stats}")
            
            return jsonify({
                'success': True,
                'data': stats
            }), 200
            
        except Exception as e:
            logger.error(f"❌ Error in get_dashboard_stats: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Server error: {str(e)}',
                'data': {}
            }), 500
    
    
    @app.route('/api/finance-manager/approve/<session_id>', methods=['POST'])
    @login_required
    @permission_required('FINANCE_MANAGER', 'CFO')
    def approve_submission(session_id):
        """
        Approve a financial document submission
        Uses workflow service to handle approval
        """
        try:
            user = get_current_user()
            user_id = user.id if user else session.get('user_id')
            
            data = request.get_json() or {}
            notes = data.get('notes', '')
            
            logger.info(f"✅ Approving submission {session_id} by user {user_id}")
            
            # Process approval using workflow service
            result = workflow_service.process_approval(
                session_id=session_id,
                user_id=user_id,
                action='approve',
                reason=notes
            )
            
            if result['success']:
                logger.info(f"✅ Successfully approved {session_id}")
                return jsonify({
                    'success': True,
                    'message': 'Submission approved successfully',
                    'data': result
                }), 200
            else:
                logger.warning(f"⚠️ Failed to approve {session_id}: {result.get('error')}")
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Failed to approve submission')
                }), 400
                
        except Exception as e:
            logger.error(f"❌ Error approving submission: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Server error: {str(e)}'
            }), 500
    
    
    @app.route('/api/finance-manager/reject/<session_id>', methods=['POST'])
    @login_required
    @permission_required('FINANCE_MANAGER', 'CFO')
    def reject_submission(session_id):
        """
        Reject a financial document submission with feedback
        Returns submission to Clerk for revision
        """
        try:
            user = get_current_user()
            user_id = user.id if user else session.get('user_id')
            
            data = request.get_json() or {}
            reason = data.get('reason', '')
            
            if not reason:
                logger.warning("❌ Rejection reason not provided")
                return jsonify({
                    'success': False,
                    'error': 'Rejection reason is required'
                }), 400
            
            logger.info(f"❌ Rejecting submission {session_id} by user {user_id}")
            
            # Process rejection using workflow service
            result = workflow_service.process_approval(
                session_id=session_id,
                user_id=user_id,
                action='reject',
                reason=reason
            )
            
            if result['success']:
                logger.info(f"✅ Successfully rejected {session_id}")
                return jsonify({
                    'success': True,
                    'message': 'Submission rejected successfully',
                    'data': result
                }), 200
            else:
                logger.warning(f"⚠️ Failed to reject {session_id}: {result.get('error')}")
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Failed to reject submission')
                }), 400
                
        except Exception as e:
            logger.error(f"❌ Error rejecting submission: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Server error: {str(e)}'
            }), 500
    
    
    @app.route('/api/finance-manager/submission/<session_id>', methods=['GET'])
    @login_required
    @permission_required('FINANCE_MANAGER', 'CFO')
    def get_submission_details(session_id):
        """
        Get detailed information about a specific submission
        Includes document data, metadata, and approval status
        """
        try:
            user = get_current_user()
            logger.info(f"📋 Fetching submission details for {session_id}")
            
            # Get user submissions to find this one
            result = workflow_service.get_user_submissions(user_id='', document_type=None)
            
            # For now, return a placeholder
            # TODO: Implement full submission detail retrieval
            
            return jsonify({
                'success': True,
                'data': {
                    'session_id': session_id,
                    'status': 'pending_review',
                    'message': 'Submission detail retrieval coming in Phase 2'
                }
            }), 200
            
        except Exception as e:
            logger.error(f"❌ Error fetching submission details: {str(e)}")
            return jsonify({
                'success': False,
                'error': f'Server error: {str(e)}'
            }), 500
    
    
    logger.info("✅ Finance Manager routes registered successfully")
    return app
