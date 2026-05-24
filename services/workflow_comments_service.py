"""Persist approval workflow comments (Supabase with in-memory fallback)."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

TABLE = "workflow_comments"
_MEMORY: Dict[str, List[Dict[str, Any]]] = defaultdict(list)


def _client():
    from utils.supabase_service_client import get_service_supabase_client

    return get_service_supabase_client()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_comments(workflow_id: str) -> List[Dict[str, Any]]:
    client = _client()
    if client:
        try:
            res = (
                client.table(TABLE)
                .select("*")
                .eq("workflow_id", str(workflow_id))
                .order("created_at", desc=False)
                .execute()
            )
            if res.data is not None:
                return [_normalize_row(r) for r in res.data]
        except Exception:
            pass
    return list(_MEMORY.get(str(workflow_id), []))


def add_comment(
    workflow_id: str,
    *,
    author_id: str,
    author_name: str,
    author_role: str,
    text: str,
) -> Dict[str, Any]:
    row = {
        "id": str(uuid4()),
        "workflow_id": str(workflow_id),
        "author_id": str(author_id),
        "author_name": author_name[:200],
        "author_role": author_role[:64],
        "text": text.strip()[:8000],
        "created_at": _now_iso(),
    }
    client = _client()
    if client:
        try:
            insert_row = {
                "workflow_id": row["workflow_id"],
                "author_id": row["author_id"],
                "author_name": row["author_name"],
                "author_role": row["author_role"],
                "text": row["text"],
            }
            res = client.table(TABLE).insert(insert_row).execute()
            if res.data:
                return _normalize_row(res.data[0])
        except Exception:
            pass
    _MEMORY[str(workflow_id)].append(row)
    return row


def update_comment(
    workflow_id: str,
    comment_id: str,
    *,
    author_id: str,
    text: str,
) -> Optional[Dict[str, Any]]:
    text = text.strip()[:8000]
    if not text:
        return None
    client = _client()
    if client:
        try:
            res = (
                client.table(TABLE)
                .update({"text": text})
                .eq("id", comment_id)
                .eq("workflow_id", str(workflow_id))
                .eq("author_id", str(author_id))
                .execute()
            )
            if res.data:
                return _normalize_row(res.data[0])
        except Exception:
            pass
    for c in _MEMORY.get(str(workflow_id), []):
        if c["id"] == comment_id and c["author_id"] == str(author_id):
            c["text"] = text
            return c
    return None


def delete_comment(workflow_id: str, comment_id: str, *, author_id: str) -> bool:
    client = _client()
    if client:
        try:
            res = (
                client.table(TABLE)
                .delete()
                .eq("id", comment_id)
                .eq("workflow_id", str(workflow_id))
                .eq("author_id", str(author_id))
                .execute()
            )
            if res.data is not None:
                return True
        except Exception:
            pass
    mem = _MEMORY.get(str(workflow_id), [])
    before = len(mem)
    _MEMORY[str(workflow_id)] = [c for c in mem if not (c["id"] == comment_id and c["author_id"] == str(author_id))]
    return len(_MEMORY[str(workflow_id)]) < before


def _normalize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    created = row.get("created_at")
    if hasattr(created, "isoformat"):
        created = created.isoformat()
    return {
        "id": str(row.get("id", "")),
        "workflow_id": str(row.get("workflow_id", "")),
        "author_id": str(row.get("author_id", "")),
        "author_name": row.get("author_name") or "Unknown",
        "author_role": row.get("author_role") or "USER",
        "text": row.get("text") or "",
        "created_at": created or _now_iso(),
    }
