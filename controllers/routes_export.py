"""
Export Center API — Excel, CSV, archive, and session-backed PDF generation.
"""

from __future__ import annotations

import os
from datetime import datetime
from io import BytesIO

from flask import jsonify, request, send_file, session

from models.supabase_auth_models import SupabaseUser, get_current_user, get_supabase_auth
from services.export_center_service import build_pdf_results_from_summary, export_center_service
from services.export_log_service import export_log_service


def _record_export_event(
    export_format: str,
    *,
    session_id: str,
    document_type: str,
    filename: str | None = None,
    period_name: str | None = None,
) -> None:
    try:
        current_user = get_current_user()
        export_log_service.record(
            export_format=export_format,
            session_id=session_id,
            document_type=document_type,
            user_id=current_user.id if current_user else session.get("user_id"),
            user_name=current_user.full_name if current_user else "",
            user_role=current_user.role if current_user else "",
            filename=filename,
            period_name=period_name,
            ip_address=request.remote_addr,
            user_agent=(request.headers.get("User-Agent") or "")[:500],
        )
    except Exception as exc:
        from flask import current_app

        current_app.logger.warning("Export log write failed: %s", exc)


def _period_name_from_payload(payload: dict) -> str:
    md = payload.get("metadata") or {}
    return (
        payload.get("period_name")
        or md.get("period_name")
        or payload.get("reporting_period")
        or ""
    )


def permission_required(*permissions):
    from functools import wraps

    from flask import current_app

    required = permissions or ("",)

    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return jsonify({"success": False, "error": "Authentication required"}), 401
            try:
                user_data = get_supabase_auth().get_user_by_id(session["user_id"])
                if not user_data:
                    return jsonify({"success": False, "error": "User not found"}), 401
                user = SupabaseUser(user_data)
                if not any(user.has_permission(p) for p in required):
                    label = " or ".join(p.upper() for p in required)
                    return jsonify({"success": False, "error": f"Permission denied. {label} required."}), 403
                return f(*args, **kwargs)
            except Exception as exc:
                current_app.logger.error("Export permission check failed: %s", exc)
                return jsonify({"success": False, "error": "Authentication error"}), 500

        return wrapper

    return decorator


def _require_exportable(session_id: str, document_type: str):
    if not session_id or not document_type:
        return None, (jsonify({"success": False, "error": "session_id and document_type are required"}), 400)
    try:
        payload = export_center_service.load_export_payload(session_id, document_type)
        return payload, None
    except ValueError as exc:
        return None, (jsonify({"success": False, "error": str(exc)}), 400)


def _export_log_formats_for_user(user: SupabaseUser | None) -> set | None:
    """Scope log entries by role — FM sees PDF activity only; CFO sees all exports."""
    if not user:
        return {"pdf_generate", "pdf_download"}
    if user.can_export():
        return None
    if user.can_download_pdf():
        return {"pdf_generate", "pdf_download"}
    if user.can_export_audit():
        return {"csv"}
    return set()


def register_export_routes(app):
    @app.route("/api/export/sessions", methods=["GET"])
    @permission_required("export", "download_pdf", "export_audit")
    def list_export_sessions():
        try:
            limit = min(int(request.args.get("limit", 50)), 200)
            sessions = export_center_service.list_exportable_sessions(limit=limit)
            for row in sessions:
                updated = row.get("updated_at")
                if updated is not None and hasattr(updated, "isoformat"):
                    row["updated_at"] = updated.isoformat()
            return jsonify({"success": True, "sessions": sessions, "count": len(sessions)})
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    @app.route("/api/export/excel", methods=["POST"])
    @permission_required("export")
    def export_excel():
        data = request.get_json(silent=True) or {}
        payload, err = _require_exportable(data.get("session_id"), data.get("document_type"))
        if err:
            return err
        try:
            content = export_center_service.export_excel_bytes(payload)
            sid = data.get("session_id", "")[:8]
            filename = f"Varydian_{data.get('document_type')}_{sid}_{datetime.now().strftime('%Y%m%d')}.xlsx"
            _record_export_event(
                "excel",
                session_id=data.get("session_id"),
                document_type=data.get("document_type"),
                filename=filename,
                period_name=_period_name_from_payload(payload),
            )
            return send_file(
                BytesIO(content),
                as_attachment=True,
                download_name=filename,
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    @app.route("/api/export/csv", methods=["POST"])
    @permission_required("export", "export_audit")
    def export_csv():
        data = request.get_json(silent=True) or {}
        payload, err = _require_exportable(data.get("session_id"), data.get("document_type"))
        if err:
            return err
        try:
            content = export_center_service.export_csv_bytes(payload)
            sid = data.get("session_id", "")[:8]
            filename = f"Varydian_{data.get('document_type')}_{sid}_{datetime.now().strftime('%Y%m%d')}.csv"
            _record_export_event(
                "csv",
                session_id=data.get("session_id"),
                document_type=data.get("document_type"),
                filename=filename,
                period_name=_period_name_from_payload(payload),
            )
            return send_file(
                BytesIO(content),
                as_attachment=True,
                download_name=filename,
                mimetype="text/csv",
            )
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    @app.route("/api/export/archive", methods=["POST"])
    @permission_required("export")
    def export_archive():
        data = request.get_json(silent=True) or {}
        payload, err = _require_exportable(data.get("session_id"), data.get("document_type"))
        if err:
            return err
        try:
            output_folder = app.config.get("OUTPUT_FOLDER", "outputs")
            content = export_center_service.export_archive_bytes(
                payload,
                output_folder=output_folder,
            )
            sid = data.get("session_id", "")[:8]
            filename = f"Varydian_archive_{sid}_{datetime.now().strftime('%Y%m%d')}.zip"
            _record_export_event(
                "archive",
                session_id=data.get("session_id"),
                document_type=data.get("document_type"),
                filename=filename,
                period_name=_period_name_from_payload(payload),
            )
            return send_file(
                BytesIO(content),
                as_attachment=True,
                download_name=filename,
                mimetype="application/zip",
            )
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    @app.route("/api/export/generate-pdf", methods=["POST"])
    @permission_required("generate_pdf")
    def export_generate_pdf_from_session():
        """Generate official AFS PDF from a finalized session (no legacy results_file required)."""
        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id")
        document_type = data.get("document_type")
        payload, err = _require_exportable(session_id, document_type)
        if err:
            return err
        try:
            from models.grap_models import generate_pdf_report
            from utils.pdf_download_guard import write_pdf_download_meta

            results = build_pdf_results_from_summary(payload)
            pdf_filename = f"Varydian_AFS_{session_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            output_folder = app.config.get("OUTPUT_FOLDER", "outputs")
            os.makedirs(output_folder, exist_ok=True)
            pdf_path = os.path.join(output_folder, pdf_filename)
            generate_pdf_report(results, pdf_path)

            current_user = get_current_user()
            user_id = current_user.id if current_user else session.get("user_id")
            period_id = (payload.get("metadata") or {}).get("period_id")
            write_pdf_download_meta(
                output_folder,
                pdf_filename,
                session_id=session_id,
                document_type=document_type,
                period_id=period_id,
                user_id=user_id,
            )

            q = f"?session_id={session_id}&document_type={document_type}"
            _record_export_event(
                "pdf_generate",
                session_id=session_id,
                document_type=document_type,
                filename=pdf_filename,
                period_name=_period_name_from_payload(payload),
            )
            return jsonify(
                {
                    "success": True,
                    "pdf_filename": pdf_filename,
                    "download_url": f"/download/{pdf_filename}{q}",
                }
            )
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500

    @app.route("/api/export/session-pdf", methods=["GET"])
    @permission_required("generate_pdf", "download_pdf")
    def find_session_pdf_download():
        """Return an existing PDF download URL for a finalized session, if one exists."""
        session_id = request.args.get("session_id")
        document_type = request.args.get("document_type")
        if not session_id or not document_type:
            return jsonify({"success": False, "error": "session_id and document_type are required"}), 400
        _, err = _require_exportable(session_id, document_type)
        if err:
            return err
        output_folder = app.config.get("OUTPUT_FOLDER", "outputs")
        pdf_path = export_center_service.find_session_pdf(output_folder, session_id, document_type)
        if not pdf_path:
            return jsonify({"success": True, "found": False, "download_url": None})
        filename = os.path.basename(pdf_path)
        q = f"?session_id={session_id}&document_type={document_type}"
        return jsonify({"success": True, "found": True, "download_url": f"/download/{filename}{q}"})

    @app.route("/api/export/log", methods=["GET"])
    @permission_required("export", "download_pdf", "export_audit")
    def export_activity_log():
        try:
            limit = min(int(request.args.get("limit", 25)), 100)
            session_id = (request.args.get("session_id") or "").strip() or None
            current_user = get_current_user()
            export_formats = _export_log_formats_for_user(current_user)
            events = export_log_service.list_events(
                limit=limit,
                session_id=session_id,
                export_formats=export_formats,
            )
            scope = "pdf" if export_formats == {"pdf_generate", "pdf_download"} else "full"
            return jsonify({"success": True, "events": events, "count": len(events), "scope": scope})
        except Exception as exc:
            return jsonify({"success": False, "error": str(exc)}), 500
