"""
In-app inbox: durable messages stored in Supabase ``user_inbox_messages``.
"""

from functools import wraps
import logging

from flask import render_template, request, redirect, session, url_for, jsonify, flash

from utils.datetime_display import format_display_datetime
from models.supabase_auth_models import get_current_user
from services import inbox_service

logger = logging.getLogger(__name__)


def login_required(f):
    """Require login; JSON 401 for /api/, redirect to login for pages."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"success": False, "error": "Authentication required"}), 401
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return decorated_function


def register_inbox_routes(app):
    @app.route("/inbox")
    @login_required
    def inbox_page():
        uid = session.get("user_id")
        user = get_current_user()
        messages = inbox_service.list_messages_for_user(str(uid), limit=100)
        return render_template(
            "inbox.html",
            current_user=user,
            format_display_datetime=format_display_datetime,
            inbox_messages=messages,
        )

    @app.route("/api/inbox/unread-count", methods=["GET"])
    @login_required
    def inbox_unread_count():
        uid = session.get("user_id")
        try:
            n = inbox_service.unread_count(str(uid))
            return jsonify({"success": True, "count": int(n)})
        except Exception as e:
            logger.warning("Inbox unread count failed: %s", e)
            return jsonify({"success": True, "count": 0})

    @app.route("/api/inbox/mark-all-read", methods=["POST"])
    @login_required
    def inbox_mark_all_read():
        uid = session.get("user_id")
        try:
            updated = inbox_service.mark_all_read(str(uid))
            return jsonify({"success": True, "updated": updated})
        except Exception as e:
            logger.warning("Inbox mark all read failed: %s", e)
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/inbox/<message_id>/read", methods=["POST"])
    @login_required
    def inbox_mark_read(message_id: str):
        uid = session.get("user_id")
        try:
            ok = inbox_service.mark_read(str(message_id), str(uid))
            if not ok:
                return jsonify({"success": False, "error": "Message not found or already read"}), 404
            return jsonify({"success": True})
        except Exception as e:
            logger.warning("Inbox mark read failed: %s", e)
            return jsonify({"success": False, "error": str(e)}), 500
