"""
Cross-app URLs (Maroon Traceability, etc.).
Normalize once here — never concatenate raw env paths in scattered places.
"""


def normalize_maroon_app_url(raw: str | None) -> str | None:
    """
    Canonical Maroon deployment root: no trailing slash, no stray whitespace.
    MAROON_APP_URL should be the site root only (e.g. https://maroondemo.vercel.app).
    Subpaths like /intro are built separately (maroon_intro_url).
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    return s.rstrip("/")


def maroon_intro_url(canonical_root: str | None) -> str | None:
    """Maroon onboarding / intro route when that page exists (do not bake /intro into env)."""
    if not canonical_root:
        return None
    return f"{canonical_root}/intro"
