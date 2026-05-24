-- Verify CFO period-lock migrations were applied in Supabase.
-- Run in Supabase SQL Editor → Results tab shows green/red checks.

-- 1) Migration registry rows (both scripts should appear)
SELECT
    id,
    description,
    applied_at,
    applied_by
FROM schema_migrations
WHERE id IN (
    'add_period_lock_and_variance_explanations',
    'enable_financial_periods_cfo_lock_rls',
    'consolidate_financial_periods_rls'
)
ORDER BY applied_at;

-- 2) Column exists on financial_periods
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_schema = 'public'
  AND table_name = 'financial_periods'
  AND column_name = 'is_locked';

-- 3) RLS enabled + policies on financial_periods
SELECT
    relname AS table_name,
    relrowsecurity AS rls_enabled
FROM pg_class
WHERE relname = 'financial_periods'
  AND relnamespace = 'public'::regnamespace;

SELECT
    policyname,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename = 'financial_periods'
ORDER BY policyname;

-- Expected:
--   • 3 rows in schema_migrations
--   • is_locked BOOLEAN NOT NULL DEFAULT false
--   • rls_enabled = true
--   • policies include "Authenticated users can view financial periods",
--     "CFO can lock financial periods", "Finance roles can create financial periods"
--   • legacy "Allow admin users to update periods" should NOT appear
