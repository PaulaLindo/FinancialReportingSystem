"""
Secure PDF download — only after reporting period is locked (CFO finalized).
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional, Tuple

from utils.pdf_availability import resolve_pdf_availability


def _meta_path(output_folder: str, filename: str) -> str:
    safe_name = os.path.basename(filename)
    return os.path.join(output_folder, f"{safe_name}.meta.json")


def write_pdf_download_meta(
    output_folder: str,
    filename: str,
    *,
    session_id: Optional[str],
    document_type: Optional[str],
    period_id: Optional[str],
    user_id: Optional[str],
) -> None:
    """Persist generation context beside the PDF for download verification."""
    meta = {
        "filename": os.path.basename(filename),
        "session_id": session_id,
        "document_type": document_type,
        "period_id": period_id,
        "user_id": user_id,
    }
    path = _meta_path(output_folder, filename)
    os.makedirs(output_folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(meta, fh)


def read_pdf_download_meta(output_folder: str, filename: str) -> Optional[Dict[str, Any]]:
    path = _meta_path(output_folder, filename)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError):
        return None


def verify_pdf_download_allowed(
    output_folder: str,
    filename: str,
    *,
    session_id: Optional[str] = None,
    document_type: Optional[str] = None,
    period_id: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Return (allowed, error_message).
    Uses sidecar .meta.json from generation, with query-param fallback.
    """
    meta = read_pdf_download_meta(output_folder, filename) or {}
    sid = session_id or meta.get("session_id")
    dtype = document_type or meta.get("document_type")
    pid = period_id or meta.get("period_id")

    if not sid and not pid:
        return (
            False,
            "PDF download requires a locked reporting period. Regenerate the PDF from Export after CFO finalization.",
        )

    availability = resolve_pdf_availability(
        session_id=sid,
        document_type=dtype,
        period_id=pid,
    )
    if availability.get("can_generate_pdf"):
        return True, ""

    return False, availability.get("reason") or "Reporting period is not locked."
