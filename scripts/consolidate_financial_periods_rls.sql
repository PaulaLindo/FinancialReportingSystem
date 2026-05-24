-- Consolidate financial_periods RLS: remove legacy auth.users policies that allowed
-- Finance Manager to UPDATE (including is_locked). Safe to run multiple times.
--
-- Run after add_period_lock_and_variance_explanations.sql and
-- enable_financial_periods_cfo_lock_rls.sql (or re-run enable script which includes this).

CREATE TABLE IF NOT EXISTS schema_migrations (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    applied_by TEXT DEFAULT current_user
);

ALTER TABLE financial_periods ENABLE ROW LEVEL SECURITY;

-- Legacy policies (auth.users.raw_user_meta_data) — superseded by public.users.role
DROP POLICY IF EXISTS "Allow admin users to create periods" ON financial_periods;
DROP POLICY IF EXISTS "Allow admin users to delete periods" ON financial_periods;
DROP POLICY IF EXISTS "Allow admin users to update periods" ON financial_periods;
DROP POLICY IF EXISTS "Allow all users to view periods" ON financial_periods;
DROP POLICY IF EXISTS "Admins can manage financial periods" ON financial_periods;

-- SELECT: authenticated users
DROP POLICY IF EXISTS "Authenticated users can view financial periods" ON financial_periods;
CREATE POLICY "Authenticated users can view financial periods" ON financial_periods
    FOR SELECT USING (auth.role() = 'authenticated');

-- INSERT: period setup (FM/CFO/System Admin via app users table)
DROP POLICY IF EXISTS "Finance roles can create financial periods" ON financial_periods;
CREATE POLICY "Finance roles can create financial periods" ON financial_periods
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.role IN ('CFO', 'FINANCE_MANAGER', 'SYSTEM_ADMIN')
        )
    );

-- UPDATE: CFO period lock only (FM cannot set is_locked via user JWT)
DROP POLICY IF EXISTS "CFO can lock financial periods" ON financial_periods;
CREATE POLICY "CFO can lock financial periods" ON financial_periods
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.role IN ('CFO', 'SYSTEM_ADMIN')
        )
    );

-- DELETE: system admin only
DROP POLICY IF EXISTS "System admin can delete financial periods" ON financial_periods;
CREATE POLICY "System admin can delete financial periods" ON financial_periods
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.role = 'SYSTEM_ADMIN'
        )
    );

COMMENT ON POLICY "CFO can lock financial periods" ON financial_periods IS
    'Only CFO/SYSTEM_ADMIN may UPDATE financial_periods (period lock). Flask uses service role for app-side lock_period().';

INSERT INTO schema_migrations (id, description)
VALUES (
    'consolidate_financial_periods_rls',
    'Remove legacy FM UPDATE on financial_periods; CFO-only lock via public.users.role'
)
ON CONFLICT (id) DO UPDATE
    SET applied_at = NOW(),
        description = EXCLUDED.description;
