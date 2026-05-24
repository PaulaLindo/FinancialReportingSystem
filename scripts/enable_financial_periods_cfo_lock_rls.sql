-- Enable RLS on financial_periods: CFO period lock + consolidated policies.
-- Safe to run multiple times (DROP POLICY IF EXISTS).
-- Requires public.users with id = auth.uid() and role column.

CREATE TABLE IF NOT EXISTS schema_migrations (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    applied_by TEXT DEFAULT current_user
);

ALTER TABLE financial_periods ENABLE ROW LEVEL SECURITY;

-- Remove legacy policies (auth.users.raw_user_meta_data) that allowed FM UPDATE
DROP POLICY IF EXISTS "Allow admin users to create periods" ON financial_periods;
DROP POLICY IF EXISTS "Allow admin users to delete periods" ON financial_periods;
DROP POLICY IF EXISTS "Allow admin users to update periods" ON financial_periods;
DROP POLICY IF EXISTS "Allow all users to view periods" ON financial_periods;
DROP POLICY IF EXISTS "Admins can manage financial periods" ON financial_periods;

DROP POLICY IF EXISTS "Authenticated users can view financial periods" ON financial_periods;
CREATE POLICY "Authenticated users can view financial periods" ON financial_periods
    FOR SELECT USING (auth.role() = 'authenticated');

DROP POLICY IF EXISTS "Finance roles can create financial periods" ON financial_periods;
CREATE POLICY "Finance roles can create financial periods" ON financial_periods
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.role IN ('CFO', 'FINANCE_MANAGER', 'SYSTEM_ADMIN')
        )
    );

DROP POLICY IF EXISTS "CFO can lock financial periods" ON financial_periods;
CREATE POLICY "CFO can lock financial periods" ON financial_periods
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM users
            WHERE users.id = auth.uid()
            AND users.role IN ('CFO', 'SYSTEM_ADMIN')
        )
    );

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
    'CFO finalization sets is_locked on financial_periods. Service role (SUPABASE_SECRET_KEY) bypasses RLS.';

INSERT INTO schema_migrations (id, description)
VALUES (
    'enable_financial_periods_cfo_lock_rls',
    'RLS on financial_periods: SELECT authenticated; INSERT FM/CFO; UPDATE CFO lock only'
)
ON CONFLICT (id) DO UPDATE
    SET applied_at = NOW(),
        description = EXCLUDED.description;

INSERT INTO schema_migrations (id, description)
VALUES (
    'consolidate_financial_periods_rls',
    'Remove legacy FM UPDATE on financial_periods; CFO-only lock via public.users.role'
)
ON CONFLICT (id) DO UPDATE
    SET applied_at = NOW(),
        description = EXCLUDED.description;
