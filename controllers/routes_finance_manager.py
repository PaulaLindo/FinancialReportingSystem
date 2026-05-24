"""
Finance Manager & CFO page routes — Review queue and settled history.

Approval APIs: use GET /api/transactions/pending and POST /api/universal/approve|reject|batch-approve
in controllers/routes_universal.py (legacy /api/finance-manager/* removed).
"""

from flask import render_template, flash, redirect, url_for
from functools import wraps
import logging

from models.supabase_auth_models import get_current_user, get_role_description

logger = logging.getLogger(__name__)


def login_required(f):
    """Require login; redirect to login for HTML pages."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import session, request

        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def permission_required(*allowed_roles):
    """Require role; redirect for HTML pages."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))

            if user.role not in allowed_roles:
                flash('You do not have access to that page.', 'warning')
                return redirect(url_for('dashboard'))

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def register_finance_manager_routes(app):
    """Register FM/CFO review and history pages."""

    @app.route('/finance-manager/dashboard', methods=['GET'])
    @login_required
    @permission_required('FINANCE_MANAGER', 'CFO')
    def finance_manager_dashboard():
        """Legacy bookmark → Review queue."""
        return redirect(url_for('finance_manager_review_queue'))

    @app.route('/finance-manager/review-queue', methods=['GET'])
    @login_required
    @permission_required('FINANCE_MANAGER', 'CFO')
    def finance_manager_review_queue():
        """Pending submissions: FM pending_review; CFO pending_cfo & approved_by_manager."""
        try:
            user = get_current_user()
            return render_template(
                'finance_manager_review_queue.html',
                current_user=user,
                get_role_description=get_role_description,
            )
        except Exception as e:
            logger.error('Error loading FM review queue: %s', e)
            flash('Could not load the review queue.', 'error')
            return redirect(url_for('dashboard'))

    @app.route('/finance-manager/history', methods=['GET'])
    @login_required
    @permission_required('FINANCE_MANAGER', 'CFO')
    def finance_manager_history():
        """Settled submission history for FM/CFO."""
        try:
            user = get_current_user()
            return render_template(
                'finance_manager_history.html',
                current_user=user,
                get_role_description=get_role_description,
            )
        except Exception as e:
            logger.error('Error loading FM history: %s', e)
            flash('Could not load submission history.', 'error')
            return redirect(url_for('finance_manager_review_queue'))

    logger.info('Finance Manager page routes registered')
    return app
