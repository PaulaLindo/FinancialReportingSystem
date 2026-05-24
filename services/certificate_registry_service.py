"""Persist and verify Manager's Certificate records."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

TABLE = "certificates_registry"

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CERTIFICATES_DIR = os.path.join(_PROJECT_ROOT, "outputs", "certificates")


def _resolve_pdf_path(certificate_id: str, file_path: Optional[str] = None) -> str:
    if file_path and os.path.isfile(file_path):
        return file_path
    candidate = os.path.join(CERTIFICATES_DIR, f"{certificate_id}.pdf")
    if os.path.isfile(candidate):
        return candidate
    legacy = os.path.join("outputs", "certificates", f"{certificate_id}.pdf")
    if os.path.isfile(legacy):
        return legacy
    return candidate


def _client():
    from utils.supabase_service_client import get_service_supabase_client

    return get_service_supabase_client()


def _next_sequence(client) -> int:
    try:
        res = client.table(TABLE).select("sequence_number").order("sequence_number", desc=True).limit(1).execute()
        if res.data:
            return int(res.data[0]["sequence_number"]) + 1
    except Exception:
        pass
    return 1


def record_certificate(
    *,
    certificate_id: str,
    session_id: str,
    document_type: str,
    issued_by: str,
    signature_hash: str,
    filepath: str,
) -> Dict[str, Any]:
    seq = None
    client = _client()
    row = {
        "certificate_id": certificate_id,
        "session_id": str(session_id),
        "document_type": document_type,
        "issued_by": str(issued_by),
        "signature_hash": signature_hash,
        "file_path": filepath.replace("\\", "/"),
        "issued_at": datetime.now(timezone.utc).isoformat(),
    }
    if client:
        try:
            row["sequence_number"] = _next_sequence(client)
            res = client.table(TABLE).insert(row).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass
    row["sequence_number"] = row.get("sequence_number") or 0
    return row


def get_certificate(certificate_id: str) -> Optional[Dict[str, Any]]:
    client = _client()
    if not client:
        return None
    try:
        res = client.table(TABLE).select("*").eq("certificate_id", certificate_id).limit(1).execute()
        if res.data:
            return res.data[0]
    except Exception:
        pass
    return None


def verify_certificate(certificate_id: str) -> Dict[str, Any]:
    """Verify PDF exists and signature sidecar matches registry hash."""
    record = get_certificate(certificate_id)
    if not record:
        return {"valid": False, "error": "Certificate not found in registry"}

    pdf_path = _resolve_pdf_path(certificate_id, record.get("file_path"))
    if not os.path.isfile(pdf_path):
        return {"valid": False, "error": "Certificate PDF file missing", "certificate_id": certificate_id}

    sidecar = pdf_path.replace(".pdf", "_signature.txt")
    stored_hash = record.get("signature_hash", "")
    sidecar_ok = False
    if os.path.isfile(sidecar):
        with open(sidecar, encoding="utf-8") as f:
            content = f.read()
            sidecar_ok = stored_hash in content

    return {
        "valid": bool(stored_hash and sidecar_ok),
        "certificate_id": certificate_id,
        "sequence_number": record.get("sequence_number"),
        "session_id": record.get("session_id"),
        "issued_at": record.get("issued_at"),
        "signature_hash": stored_hash,
        "pdf_exists": True,
        "sidecar_matches": sidecar_ok,
    }


def verify_signature_hash(user_id: str, session_id: str, claimed_hash: str) -> bool:
    """Recompute SHA-256 from stored sidecar format (best-effort)."""
    sidecar_path = CERTIFICATES_DIR
    if not os.path.isdir(sidecar_path):
        return False
    for name in os.listdir(sidecar_path):
        if not name.endswith("_signature.txt"):
            continue
        path = os.path.join(sidecar_path, name)
        with open(path, encoding="utf-8") as f:
            if claimed_hash in f.read():
                return True
    expected_prefix = hashlib.sha256(f"{user_id}:{session_id}".encode()).hexdigest()[:16]
    return claimed_hash.startswith(expected_prefix) if claimed_hash else False
