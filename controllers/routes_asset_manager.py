"""
Asset Manager pages and APIs — GRAP 17 register, lifecycle journals, reconciliation.

Asset journals queue for Finance Manager approval (separate from TB universal workflow).
"""

from __future__ import annotations

import logging
from datetime import datetime
from functools import wraps

from flask import Response, flash, jsonify, redirect, render_template, request, url_for

from models.supabase_auth_models import SupabaseUser, get_current_user, get_role_description
from services.asset_register_service import JOURNAL_PENDING, asset_register_service

logger = logging.getLogger(__name__)


def _login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        from flask import session

        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


def _role_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = get_current_user()
            if not user:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            if user.role not in roles:
                flash('You do not have access to that page.', 'warning')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return wrapper
    return decorator


def _permission_api(*permissions):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            from flask import session

            if 'user_id' not in session:
                return jsonify({'success': False, 'error': 'Authentication required'}), 401
            user = get_current_user()
            if not user:
                return jsonify({'success': False, 'error': 'User not found'}), 401
            if not any(user.has_permission(p) for p in permissions):
                return jsonify({'success': False, 'error': 'Permission denied'}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


def _fm_api(f):
    """Finance Manager or CFO — asset journal approval."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        from flask import session

        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        user = get_current_user()
        if not user or user.role not in ('FINANCE_MANAGER', 'CFO'):
            return jsonify({'success': False, 'error': 'Finance Manager or CFO access required'}), 403
        return f(*args, **kwargs)
    return wrapper


def register_asset_manager_routes(app):
    """Asset Manager UI + APIs and FM asset journal queue."""

    @app.route('/asset-manager/register')
    @_login_required
    @_role_required('ASSET_MANAGER')
    def asset_manager_register_page():
        user = get_current_user()
        asset_register_service.seed_demo_assets_if_empty(user.id if user else 'system')
        return render_template(
            'asset_manager/register.html',
            current_user=user,
            get_role_description=get_role_description,
        )

    @app.route('/asset-manager/assets/<asset_id>')
    @_login_required
    @_role_required('ASSET_MANAGER')
    def asset_manager_asset_detail_page(asset_id):
        user = get_current_user()
        asset = asset_register_service.get_asset(asset_id)
        if not asset:
            flash('Asset not found.', 'error')
            return redirect(url_for('asset_manager_register_page'))
        journals = asset_register_service.list_journals(asset_id=asset_id)
        return render_template(
            'asset_manager/asset_detail.html',
            current_user=user,
            asset=asset,
            journals=journals,
            get_role_description=get_role_description,
        )

    @app.route('/asset-manager/reconciliation')
    @_login_required
    @_role_required('ASSET_MANAGER')
    def asset_manager_reconciliation_page():
        user = get_current_user()
        recon = asset_register_service.get_reconciliation()
        return render_template(
            'asset_manager/reconciliation.html',
            current_user=user,
            reconciliation=recon,
            get_role_description=get_role_description,
        )

    @app.route('/asset-manager/journals')
    @_login_required
    @_role_required('ASSET_MANAGER')
    def asset_manager_journals_page():
        user = get_current_user()
        return render_template(
            'asset_manager/journals.html',
            current_user=user,
            get_role_description=get_role_description,
        )

    @app.route('/finance-manager/asset-journals')
    @_login_required
    @_role_required('FINANCE_MANAGER', 'CFO')
    def finance_manager_asset_journals_page():
        user = get_current_user()
        return render_template(
            'asset_manager/fm_journals.html',
            current_user=user,
            get_role_description=get_role_description,
        )

    # --- Asset Manager APIs ---

    @app.route('/api/asset-manager/assets', methods=['GET'])
    @_login_required
    @_permission_api('manage_assets', 'view_assets')
    def api_list_assets():
        assets = asset_register_service.list_assets()
        return jsonify({'success': True, 'assets': assets, 'count': len(assets)})

    @app.route('/api/asset-manager/assets', methods=['POST'])
    @_login_required
    @_permission_api('manage_assets')
    def api_register_asset():
        user = get_current_user()
        data = request.get_json(silent=True) or {}
        result = asset_register_service.register_asset(data, user.id)
        status = 200 if result.get('success') else 400
        return jsonify(result), status

    @app.route('/api/asset-manager/assets/<asset_id>', methods=['GET'])
    @_login_required
    @_permission_api('manage_assets', 'view_assets')
    def api_get_asset(asset_id):
        asset = asset_register_service.get_asset(asset_id)
        if not asset:
            return jsonify({'success': False, 'error': 'Asset not found'}), 404
        return jsonify({'success': True, 'asset': asset})

    @app.route('/api/asset-manager/assets/<asset_id>/useful-life-journal', methods=['POST'])
    @_login_required
    @_permission_api('manage_assets')
    def api_useful_life_journal(asset_id):
        user = get_current_user()
        data = request.get_json(silent=True) or {}
        result = asset_register_service.create_useful_life_journal(
            asset_id,
            new_useful_life=int(data.get('new_useful_life') or 0),
            reason=str(data.get('reason') or ''),
            user_id=user.id,
            user_name=user.full_name or user.username,
            effective_date=data.get('effective_date'),
        )
        status = 200 if result.get('success') else 400
        return jsonify(result), status

    @app.route('/api/asset-manager/assets/<asset_id>/impairment-journal', methods=['POST'])
    @_login_required
    @_permission_api('manage_assets')
    def api_impairment_journal(asset_id):
        user = get_current_user()
        data = request.get_json(silent=True) or {}
        result = asset_register_service.create_impairment_journal(
            asset_id,
            impairment_amount=float(data.get('impairment_amount') or 0),
            reason=str(data.get('reason') or ''),
            user_id=user.id,
            user_name=user.full_name or user.username,
            recoverable_amount=data.get('recoverable_amount'),
        )
        status = 200 if result.get('success') else 400
        return jsonify(result), status

    @app.route('/api/asset-manager/assets/<asset_id>/disposal-journal', methods=['POST'])
    @_login_required
    @_permission_api('manage_assets')
    def api_disposal_journal(asset_id):
        user = get_current_user()
        data = request.get_json(silent=True) or {}
        result = asset_register_service.create_disposal_journal(
            asset_id,
            disposal_proceeds=float(data.get('disposal_proceeds') or 0),
            reason=str(data.get('reason') or ''),
            user_id=user.id,
            user_name=user.full_name or user.username,
            disposal_date=data.get('disposal_date'),
        )
        status = 200 if result.get('success') else 400
        return jsonify(result), status

    @app.route('/api/asset-manager/depreciation/run', methods=['POST'])
    @_login_required
    @_permission_api('manage_assets')
    def api_run_depreciation():
        user = get_current_user()
        data = request.get_json(silent=True) or {}
        fiscal_year = int(data.get('fiscal_year') or datetime.now().year)
        result = asset_register_service.process_annual_depreciation(fiscal_year, user.id)
        status = 200 if result.get('success') else 400
        return jsonify(result), status

    @app.route('/api/asset-manager/reconciliation/sync-tb/preview', methods=['GET'])
    @_login_required
    @_permission_api('manage_assets', 'review')
    def api_preview_sync_gl_from_tb():
        session_id = request.args.get('session_id')
        result = asset_register_service.preview_gl_sync_from_trial_balance(session_id=session_id)
        status = 200 if result.get('success') else 400
        return jsonify(result), status

    @app.route('/api/asset-manager/reconciliation/sync-tb', methods=['POST'])
    @_login_required
    @_permission_api('manage_assets', 'review')
    def api_sync_gl_from_tb():
        user = get_current_user()
        data = request.get_json(silent=True) or {}
        result = asset_register_service.sync_gl_from_trial_balance(
            session_id=data.get('session_id'),
            user_id=user.id,
        )
        status = 200 if result.get('success') else 400
        return jsonify(result), status

    @app.route('/api/asset-manager/reconciliation/gl-balance', methods=['PUT'])
    @_login_required
    @_permission_api('manage_assets', 'review')
    def api_update_gl_balance():
        user = get_current_user()
        data = request.get_json(silent=True) or {}
        result = asset_register_service.update_gl_balance_manual(
            float(data.get('balance') or 0),
            note=str(data.get('note') or ''),
            user_id=user.id,
        )
        status = 200 if result.get('success') else 400
        return jsonify(result), status

    @app.route('/api/asset-manager/dashboard-stats', methods=['GET'])
    @_login_required
    @_permission_api('manage_assets', 'view_assets')
    def api_asset_dashboard_stats():
        user = get_current_user()
        return jsonify(asset_register_service.get_dashboard_stats(user.id if user else None))

    @app.route('/api/asset-manager/export/register.csv', methods=['GET'])
    @_login_required
    @_permission_api('manage_assets', 'view_assets')
    def api_export_register_csv():
        user = get_current_user()
        csv_body = asset_register_service.export_register_csv()
        try:
            from services.export_log_service import export_log_service

            export_log_service.record(
                export_format='csv',
                session_id='asset_register',
                document_type='asset_register',
                user_id=user.id if user else '',
                user_name=user.full_name if user else '',
                user_role=user.role if user else '',
                filename='asset_register.csv',
                period_name='GRAP 17 Asset Register',
                ip_address=request.remote_addr,
                user_agent=(request.headers.get('User-Agent') or '')[:500],
            )
        except Exception as exc:
            logger.warning('Asset register export log failed: %s', exc)
        return Response(
            csv_body,
            mimetype='text/csv',
            headers={'Content-Disposition': 'attachment; filename=asset_register.csv'},
        )

    @app.route('/api/asset-manager/journals', methods=['GET'])
    @_login_required
    def api_list_asset_journals():
        user = get_current_user()
        if not user:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        status = request.args.get('status')
        asset_id = request.args.get('asset_id')
        submitter_id = None
        if user.role == 'ASSET_MANAGER':
            submitter_id = user.id
        elif user.role not in ('FINANCE_MANAGER', 'CFO', 'SYSTEM_ADMIN'):
            return jsonify({'success': False, 'error': 'Permission denied'}), 403

        journals = asset_register_service.list_journals(
            status=status,
            asset_id=asset_id,
            submitter_id=submitter_id,
        )
        return jsonify({'success': True, 'journals': journals, 'count': len(journals)})

    @app.route('/api/asset-manager/reconciliation', methods=['GET'])
    @_login_required
    @_permission_api('manage_assets', 'view_assets')
    def api_asset_reconciliation():
        return jsonify(asset_register_service.get_reconciliation())

    # --- FM asset journal approval ---

    @app.route('/api/asset-journals/pending', methods=['GET'])
    @_fm_api
    def api_pending_asset_journals():
        journals = asset_register_service.list_journals(status=JOURNAL_PENDING)
        return jsonify({'success': True, 'journals': journals, 'count': len(journals)})

    @app.route('/api/asset-journals/history', methods=['GET'])
    @_fm_api
    def api_asset_journal_history():
        status_filter = (request.args.get('status') or 'all').strip().lower()
        if status_filter not in ('all', 'approved', 'rejected'):
            status_filter = 'all'
        journals = asset_register_service.list_settled_journals(status_filter=status_filter)
        return jsonify({'success': True, 'journals': journals, 'count': len(journals)})

    @app.route('/api/asset-journals/<journal_id>/approve', methods=['POST'])
    @_fm_api
    def api_approve_asset_journal(journal_id):
        user = get_current_user()
        result = asset_register_service.approve_journal(
            journal_id,
            user.id,
            user.full_name or user.username,
        )
        status = 200 if result.get('success') else 400
        return jsonify(result), status

    @app.route('/api/asset-journals/<journal_id>/reject', methods=['POST'])
    @_fm_api
    def api_reject_asset_journal(journal_id):
        user = get_current_user()
        data = request.get_json(silent=True) or {}
        reason = str(data.get('reason') or data.get('rejection_reason') or '').strip()
        result = asset_register_service.reject_journal(
            journal_id,
            user.id,
            reason,
            user.full_name or user.username,
        )
        status = 200 if result.get('success') else 400
        return jsonify(result), status

    logger.info('Asset Manager routes registered')
    return app
