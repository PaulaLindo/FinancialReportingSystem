"""
Verify Supabase SQL migrations for CFO period lock (schema_migrations registry + probes).
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional

EXPECTED_MIGRATIONS: List[Dict[str, str]] = [
    {
        "id": "add_period_lock_and_variance_explanations",
        "description": "Add financial_periods.is_locked column for CFO period closure",
    },
    {
        "id": "enable_financial_periods_cfo_lock_rls",
        "description": "RLS on financial_periods for CFO period lock",
    },
    {
        "id": "consolidate_financial_periods_rls",
        "description": "Remove legacy FM UPDATE on financial_periods",
    },
]


@dataclass
class MigrationCheck:
    id: str
    description: str
    registered: bool
    applied_at: Optional[str] = None
    applied_by: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SchemaProbe:
    name: str
    passed: bool
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _get_client():
    from utils.supabase_service_client import get_service_supabase_client

    return get_service_supabase_client()


def _probe_is_locked_column(client) -> SchemaProbe:
    try:
        result = client.table("financial_periods").select("is_locked").limit(1).execute()
        rows = result.data or []
        sample = rows[0].get("is_locked") if rows else None
        detail = (
            f"Column readable; sample is_locked={sample!r}"
            if rows
            else "Column readable (no period rows yet)"
        )
        return SchemaProbe(name="financial_periods.is_locked", passed=True, detail=detail)
    except Exception as exc:
        msg = str(exc)
        if "is_locked" in msg or "42703" in msg:
            return SchemaProbe(
                name="financial_periods.is_locked",
                passed=False,
                detail="Column missing — run scripts/add_period_lock_and_variance_explanations.sql",
            )
        return SchemaProbe(
            name="financial_periods.is_locked",
            passed=False,
            detail=f"Probe failed: {msg}",
        )


def _load_registry(client) -> Dict[str, Dict[str, Any]]:
    try:
        result = (
            client.table("schema_migrations")
            .select("id, description, applied_at, applied_by")
            .execute()
        )
        rows = result.data or []
        return {str(row["id"]): row for row in rows if row.get("id")}
    except Exception:
        return {}


def check_cfo_period_lock_migrations() -> Dict[str, Any]:
    """
    Return migration registry status and live schema probes for CFO period lock.
    """
    client = _get_client()
    if not client:
        return {
            "success": False,
            "error": "Supabase service client unavailable (set SUPABASE_URL and SUPABASE_SECRET_KEY)",
            "all_applied": False,
            "migrations": [],
            "probes": [],
        }

    registry = _load_registry(client)
    migrations: List[MigrationCheck] = []
    for expected in EXPECTED_MIGRATIONS:
        row = registry.get(expected["id"])
        migrations.append(
            MigrationCheck(
                id=expected["id"],
                description=expected["description"],
                registered=bool(row),
                applied_at=str(row.get("applied_at")) if row and row.get("applied_at") else None,
                applied_by=str(row.get("applied_by")) if row and row.get("applied_by") else None,
            )
        )

    probes = [_probe_is_locked_column(client)]
    all_registered = all(m.registered for m in migrations)
    all_probes_pass = all(p.passed for p in probes)

    return {
        "success": True,
        "all_applied": all_registered and all_probes_pass,
        "registry_available": bool(registry) or all_registered,
        "migrations": [m.to_dict() for m in migrations],
        "probes": [p.to_dict() for p in probes],
        "verify_sql": "scripts/verify_supabase_cfo_migrations.sql",
        "hint": (
            "Run scripts in Supabase SQL Editor: add_period_lock_and_variance_explanations.sql, "
            "enable_financial_periods_cfo_lock_rls.sql (includes RLS consolidation)"
        ),
    }
