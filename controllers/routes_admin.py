"""System Admin pages and APIs — users, reporting periods, schema health."""

from typing import Dict

import logging
from functools import wraps

from flask import flash, jsonify, redirect, render_template, request, session, url_for

from models.supabase_auth_models import get_current_user, get_role_description, get_role_label

logger = logging.getLogger(__name__)

ASSIGNABLE_ROLES = (
    'FINANCE_CLERK',
    'FINANCE_MANAGER',
    'CFO',
    'ASSET_MANAGER',
    'AUDITOR',
    'SYSTEM_ADMIN',
)


def _login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapper


def _admin_api(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        user = get_current_user()
        if not user or not user.can_manage_users():
            return jsonify({'success': False, 'error': 'System Administrator access required'}), 403
        return f(*args, **kwargs)
    return wrapper


def _public_user(row: dict) -> dict:
    return {
        'id': row.get('id'),
        'username': row.get('username'),
        'full_name': row.get('full_name'),
        'email': row.get('email'),
        'role': row.get('role'),
        'is_active': row.get('is_active', True),
        'created_at': row.get('created_at'),
    }


def register_admin_routes(app):
    @app.route('/admin/cleanup')
    @_login_required
    def admin_cleanup_page():
        user = get_current_user()
        if not user or not user.can_manage_users():
            flash('Access denied. System Administrator privileges required.', 'error')
            return redirect(url_for('dashboard'))
        return render_template('admin_cleanup.html', user=user, current_user=user)

    @app.route('/api/admin/overview', methods=['GET'])
    @_admin_api
    def api_admin_overview():
        from models.supabase_auth_models import supabase_auth
        from services.period_management_service import period_management_service
        from services.schema_migration_service import check_cfo_period_lock_migrations

        users = supabase_auth.get_all_users()
        active_users = [u for u in users if u.get('is_active', True)]
        periods = period_management_service.model.get_all_periods()
        period_management_service.consolidate_duplicate_periods()
        periods = period_management_service.dedupe_periods(
            period_management_service.model.get_all_periods()
        )
        open_periods = [
            p for p in periods
            if getattr(p, 'status', '') == 'open'
            and not (
                getattr(p, 'is_locked', False)
                or (getattr(p, 'metadata', None) or {}).get('is_locked')
            )
        ]
        locked_periods = [
            p for p in periods
            if getattr(p, 'is_locked', False) or (getattr(p, 'metadata', None) or {}).get('is_locked')
        ]
        migrations = check_cfo_period_lock_migrations()

        return jsonify({
            'success': True,
            'stats': {
                'user_count': len(users),
                'active_user_count': len(active_users),
                'period_count': len(periods),
                'open_period_count': len(open_periods),
                'locked_period_count': len(locked_periods),
                'migrations_ok': bool(migrations.get('all_applied')),
            },
            'migrations': migrations,
        })

    @app.route('/api/admin/users', methods=['GET'])
    @_admin_api
    def api_admin_list_users():
        from models.supabase_auth_models import supabase_auth

        users = [_public_user(u) for u in supabase_auth.get_all_users()]
        return jsonify({'success': True, 'users': users, 'count': len(users)})

    @app.route('/api/admin/users', methods=['POST'])
    @_admin_api
    def api_admin_create_user():
        from models.supabase_auth_models import supabase_auth

        data = request.get_json(silent=True) or {}
        username = str(data.get('username') or data.get('email') or '').strip()
        email = str(data.get('email') or username).strip()
        full_name = str(data.get('full_name') or '').strip()
        password = str(data.get('password') or '').strip()
        role = str(data.get('role') or '').strip().upper()

        if not all([username, email, full_name, password, role]):
            return jsonify({'success': False, 'error': 'All fields are required'}), 400
        if role not in ASSIGNABLE_ROLES:
            return jsonify({'success': False, 'error': f'Invalid role. Choose one of: {", ".join(ASSIGNABLE_ROLES)}'}), 400
        if len(password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400

        result = supabase_auth.create_user(username, password, full_name, role, email)
        status = 200 if result.get('success') else 400
        if result.get('success') and result.get('user'):
            result = {**result, 'user': _public_user(result['user'])}
        return jsonify(result), status

    @app.route('/api/admin/users/<user_id>/deactivate', methods=['POST'])
    @_admin_api
    def api_admin_deactivate_user(user_id):
        from models.supabase_auth_models import supabase_auth

        actor = get_current_user()
        if actor and str(actor.id) == str(user_id):
            return jsonify({'success': False, 'error': 'You cannot deactivate your own account'}), 400

        result = supabase_auth.deactivate_user(user_id)
        status = 200 if result.get('success') else 400
        if result.get('success') and result.get('user'):
            result = {**result, 'user': _public_user(result['user'])}
        return jsonify(result), status

    @app.route('/api/admin/users/<user_id>/activate', methods=['POST'])
    @_admin_api
    def api_admin_activate_user(user_id):
        from models.supabase_auth_models import supabase_auth

        result = supabase_auth.activate_user(user_id)
        status = 200 if result.get('success') else 400
        if result.get('success') and result.get('user'):
            result = {**result, 'user': _public_user(result['user'])}
        return jsonify(result), status

    @app.route('/api/admin/periods', methods=['GET'])
    @_admin_api
    def api_admin_list_periods():
        from services.period_management_service import (
            STANDARD_REQUIRED_UPLOADS,
            period_management_service,
        )

        period_management_service.consolidate_duplicate_periods()
        all_periods = period_management_service.model.get_all_periods()
        periods = period_management_service.dedupe_periods(all_periods)
        identity_counts: Dict[str, int] = {}
        for period in all_periods:
            key = period_management_service._period_identity_key(period)
            identity_counts[key] = identity_counts.get(key, 0) + 1

        payload = []
        for period in periods:
            data = period.to_dict()
            try:
                period = period_management_service.reconcile_period_upload_counts(period.id)
                period = period_management_service.normalize_locked_period_status(period.id)
                data = period.to_dict()
            except Exception as sync_err:
                logger.warning("Could not reconcile period %s for admin list: %s", period.id, sync_err)
            data['completion_percentage'] = period.completion_percentage
            data['expected_required_uploads'] = STANDARD_REQUIRED_UPLOADS
            dup_key = period_management_service._period_identity_key(period)
            extra_copies = max(0, identity_counts.get(dup_key, 1) - 1)
            data['extra_copy_count'] = extra_copies
            data['is_duplicate'] = extra_copies > 0
            payload.append(data)
        payload.sort(key=lambda row: (str(row.get('start_date') or '')[:10], str(row.get('name') or '')))
        return jsonify({
            'success': True,
            'periods': payload,
            'count': len(payload),
            'expected_required_uploads': STANDARD_REQUIRED_UPLOADS,
        })

    @app.route('/api/admin/periods/<period_id>/merge-duplicates', methods=['POST'])
    @_admin_api
    def api_admin_merge_duplicate_periods(period_id):
        from services.period_management_service import period_management_service

        try:
            result = period_management_service.merge_duplicate_period_rows(period_id)
            return jsonify(result), 200
        except Exception as exc:
            return jsonify({'success': False, 'error': str(exc)}), 400

    @app.route('/api/admin/periods/<period_id>', methods=['DELETE'])
    @_admin_api
    def api_admin_delete_period(period_id):
        from services.period_management_service import period_management_service

        try:
            period_management_service.delete_financial_period(period_id)
            return jsonify({
                'success': True,
                'message': 'Period deleted.',
            })
        except Exception as exc:
            return jsonify({'success': False, 'error': str(exc)}), 400

    logger.info('System Admin routes registered')
    return app
