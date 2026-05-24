"""
Export activity log — persisted to ``app_audit_events`` (entity_type ``export``).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from models.audit_models import AUDIT_EVENTS_TABLE, AuditTrailModel, _db_audit_row_to_record
from models.supabase_auth_models import get_role_label

logger = logging.getLogger(__name__)

EXPORT_ENTITY = "export"

FORMAT_LABELS = {
    "pdf_generate": "PDF generated",
    "pdf_download": "PDF downloaded",
    "excel": "Excel exported",
    "csv": "CSV exported",
    "archive": "Archive downloaded",
}


def _action_to_format(action: str) -> str:
    action = (action or "").strip()
    if action.startswith("export_"):
        return action[len("export_") :]
    return action


def _normalize_export_event(record: Dict[str, Any]) -> Dict[str, Any]:
    new_data = record.get("new_data") or {}
    export_format = new_data.get("export_format") or _action_to_format(record.get("action") or "")
    doc_type = (new_data.get("document_type") or "").replace("_", " ")
    label = FORMAT_LABELS.get(export_format, export_format.replace("_", " ").title())
    title = label
    if doc_type:
        title = f"{label} — {doc_type}"
    filename = new_data.get("filename") or ""
    if filename:
        title = f"{title} ({filename})"

    user_name = new_data.get("user_name") or "Unknown user"
    role_label = new_data.get("user_role_label") or get_role_label(new_data.get("user_role") or "")

    return {
        "audit_id": record.get("audit_id"),
        "timestamp": record.get("timestamp") or record.get("created_at"),
        "export_format": export_format,
        "title": title,
        "session_id": new_data.get("session_id") or record.get("entity_id"),
        "document_type": new_data.get("document_type"),
        "filename": filename,
        "period_name": new_data.get("period_name"),
        "user_id": record.get("user_id"),
        "user_name": user_name,
        "user_role": new_data.get("user_role"),
        "user_role_label": role_label,
        "actor_label": f"{user_name} ({role_label})" if role_label else user_name,
    }


class ExportLogService:
    def __init__(self) -> None:
        self._audit = AuditTrailModel()

    def record(
        self,
        *,
        export_format: str,
        session_id: str,
        document_type: str,
        user_id: Optional[str] = None,
        user_name: Optional[str] = None,
        user_role: Optional[str] = None,
        filename: Optional[str] = None,
        period_name: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        fmt = (export_format or "").strip().lower()
        new_data = {
            "export_format": fmt,
            "session_id": session_id,
            "document_type": document_type,
            "filename": filename or "",
            "period_name": period_name or "",
            "user_name": user_name or "",
            "user_role": user_role or "",
            "user_role_label": get_role_label(user_role or ""),
        }
        reason = FORMAT_LABELS.get(fmt, f"Export ({fmt})")
        return self._audit.log_change(
            entity_type=EXPORT_ENTITY,
            entity_id=session_id,
            action=f"export_{fmt}",
            old_data=None,
            new_data=new_data,
            user_id=user_id or "system",
            reason=reason,
            ip_address=ip_address or "",
            user_agent=user_agent or "",
        )

    def list_events(
        self,
        *,
        limit: int = 25,
        session_id: Optional[str] = None,
        export_formats: Optional[set] = None,
    ) -> List[Dict[str, Any]]:
        cap = min(max(int(limit), 1), 100)
        fetch_limit = cap * 4 if session_id or export_formats else cap
        db_rows: List[Dict[str, Any]] = []
        svc = self._audit._svc
        if svc:
            try:
                res = (
                    svc.table(AUDIT_EVENTS_TABLE)
                    .select("*")
                    .eq("entity_type", EXPORT_ENTITY)
                    .order("created_at", desc=True)
                    .limit(fetch_limit)
                    .execute()
                )
                db_rows = [_normalize_export_event(_db_audit_row_to_record(r)) for r in (res.data or [])]
            except Exception as ex:
                logger.warning("Export log DB read failed: %s", ex)

        memory = self._audit.get_entity_history(EXPORT_ENTITY)
        memory.sort(key=lambda r: r.get("timestamp") or "", reverse=True)
        memory_rows = [_normalize_export_event(r) for r in memory[:fetch_limit]]

        merged: Dict[str, Dict[str, Any]] = {}
        for row in db_rows + memory_rows:
            key = row.get("audit_id") or f"{row.get('timestamp')}-{row.get('export_format')}-{row.get('session_id')}"
            merged[key] = row
        rows = sorted(merged.values(), key=lambda r: r.get("timestamp") or "", reverse=True)

        if export_formats:
            rows = [r for r in rows if r.get("export_format") in export_formats]

        if session_id:
            rows = [r for r in rows if r.get("session_id") == session_id]

        return rows[:cap]

    def session_ids_with_pdf_export(self, session_ids: List[str]) -> set:
        """Return session IDs that have at least one PDF generated (official export)."""
        ids = {str(s).strip() for s in (session_ids or []) if str(s).strip()}
        if not ids:
            return set()
        exported: set = set()
        try:
            rows = self.list_events(limit=100, export_formats={"pdf_generate"})
            for row in rows:
                sid = row.get("session_id")
                if sid and sid in ids:
                    exported.add(sid)
        except Exception as ex:
            logger.warning("session_ids_with_pdf_export failed: %s", ex)
        return exported


export_log_service = ExportLogService()
