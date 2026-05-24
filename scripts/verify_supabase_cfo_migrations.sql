-- Verify CFO period-lock migrations and RLS policies in Supabase.
-- Run in Supabase SQL Editor → compare Results with expected policies below.

-- 1) Migration registry rows
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

-- 3) RLS enabled
SELECT
    relname AS table_name,
    relrowsecurity AS rls_enabled
FROM pg_class
WHERE relname = 'financial_periods'
  AND relnamespace = 'public'::regnamespace;

-- 4) Policies on financial_periods (expect exactly these four)
SELECT
    policyname,
    cmd,
    qual,
    with_check
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename = 'financial_periods'
ORDER BY policyname;

-- Expected policies (2026-05):
--   • Authenticated users can view financial periods     (SELECT)
--   • CFO can lock financial periods                     (UPDATE — CFO / SYSTEM_ADMIN)
--   • Finance roles can create financial periods         (INSERT — CFO / FINANCE_MANAGER / SYSTEM_ADMIN)
--   • System admin can delete financial periods          (DELETE — SYSTEM_ADMIN)
--
-- Legacy policy "Allow admin users to update periods" must NOT appear.
-- CFO lock UPDATE qual should reference users.role IN ('CFO', 'SYSTEM_ADMIN').
