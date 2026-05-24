-- Period lock flag for CFO finalization (GRAP period closure)
-- Safe to run multiple times (IF NOT EXISTS).
-- Run in Supabase SQL Editor (paste entire file).

CREATE TABLE IF NOT EXISTS schema_migrations (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    applied_by TEXT DEFAULT current_user
);

ALTER TABLE financial_periods
    ADD COLUMN IF NOT EXISTS is_locked BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN financial_periods.is_locked IS
    'When true, POST/PUT uploads and edits for this period are blocked; PDF generation allowed.';

INSERT INTO schema_migrations (id, description)
VALUES (
    'add_period_lock_and_variance_explanations',
    'Add financial_periods.is_locked column for CFO period closure and GRAP export gating'
)
ON CONFLICT (id) DO UPDATE
    SET applied_at = NOW(),
        description = EXCLUDED.description;

-- Next: run enable_financial_periods_cfo_lock_rls.sql in the same SQL Editor session.
-- Service role (SUPABASE_SECRET_KEY in .env) bypasses RLS for app-side lock_period().
