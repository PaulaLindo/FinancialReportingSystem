"""
Auditor pages — read-only access to finalized submissions and audit exports.
"""

from __future__ import annotations

from functools import wraps

from flask import flash, redirect, render_template, url_for

from models.supabase_auth_models import get_current_user, get_role_description
from services.export_center_service import export_center_service


def _login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        from flask import session

        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


def _auditor_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if not user or not user.can_access_audit_workspace():
            flash('Auditor access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return wrapper


def register_auditor_routes(app):
    @app.route('/audit')
    @_login_required
    @_auditor_required
    def auditor_workspace_page():
        user = get_current_user()
        sessions = export_center_service.list_exportable_sessions(limit=200)
        return render_template(
            'auditor/audit_workspace.html',
            current_user=user,
            get_role_description=get_role_description,
            finalized_count=len(sessions),
        )

    @app.route('/audit/asset-register')
    @_login_required
    @_auditor_required
    def auditor_asset_register_page():
        user = get_current_user()
        return render_template(
            'auditor/asset_register.html',
            current_user=user,
            get_role_description=get_role_description,
        )

    @app.route('/audit/reconciliation')
    @_login_required
    @_auditor_required
    def auditor_reconciliation_page():
        user = get_current_user()
        from services.asset_register_service import asset_register_service

        recon = asset_register_service.get_reconciliation()
        return render_template(
            'auditor/reconciliation.html',
            current_user=user,
            get_role_description=get_role_description,
            reconciliation=recon,
        )
