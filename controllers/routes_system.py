"""System / schema status routes (migration verification)."""

from flask import jsonify

from models.supabase_auth_models import get_current_user


def register_system_routes(app):
    """Register system health and schema migration verification routes."""

    @app.route('/api/system/schema-migrations', methods=['GET'])
    def get_schema_migration_status():
        """
        Verify CFO period-lock SQL scripts were applied in Supabase.

        Accessible to CFO and SYSTEM_ADMIN (no auth required in local dev if
        service role is configured — returns connection errors otherwise).
        """
        user = get_current_user()
        if user:
            role = (getattr(user, 'role', None) or '').upper()
            if role not in ('CFO', 'SYSTEM_ADMIN'):
                return jsonify({
                    'success': False,
                    'error': 'Only CFO or System Admin can view schema migration status',
                }), 403
        else:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401

        from services.schema_migration_service import check_cfo_period_lock_migrations

        report = check_cfo_period_lock_migrations()
        status_code = 200 if report.get('success') else 503
        return jsonify(report), status_code
