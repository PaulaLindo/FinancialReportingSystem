-- Migration registry for Supabase SQL scripts (CFO period lock, RLS, etc.)
-- Run once in Supabase SQL Editor before or alongside feature migrations.
-- Safe to run multiple times.

CREATE TABLE IF NOT EXISTS schema_migrations (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    applied_by TEXT DEFAULT current_user
);

COMMENT ON TABLE schema_migrations IS
    'Records which repo SQL scripts have been applied in this Supabase project.';

CREATE INDEX IF NOT EXISTS idx_schema_migrations_applied_at
    ON schema_migrations (applied_at DESC);
