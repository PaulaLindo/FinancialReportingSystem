"""
Server-side Supabase client (service role JWT). Used for durable audit + inbox rows.
Bypasses RLS; only call from Flask after authz checks.
"""

import os
from typing import Any, Optional

try:
    from supabase import create_client, Client
except ImportError:  # pragma: no cover
    Client = Any  # type: ignore
    create_client = None  # type: ignore


def get_service_supabase_client() -> Optional[Any]:
    """
    Returns Supabase client using SUPABASE_SECRET_KEY (service role JWT).
    None if unavailable (local dev without keys).
    """
    if create_client is None:
        return None
    from utils.supabase_client import get_supabase_secret_key

    url = os.getenv("SUPABASE_URL")
    key = get_supabase_secret_key()
    if not url or not key:
        return None
    try:
        return create_client(url, key)
    except Exception:
        return None


def service_client_available() -> bool:
    return get_service_supabase_client() is not None
