-- GRAP 17 asset register persistence (run in Supabase SQL editor).
-- Flask uses service role for CRUD; RLS enabled with no anon policies.

CREATE TABLE IF NOT EXISTS assets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    asset_id TEXT NOT NULL UNIQUE,
    asset_name TEXT NOT NULL,
    asset_category TEXT NOT NULL,
    purchase_date DATE NOT NULL,
    purchase_cost NUMERIC(18, 2) NOT NULL,
    residual_value NUMERIC(18, 2) NOT NULL DEFAULT 0,
    useful_life_years INTEGER NOT NULL,
    remaining_useful_life INTEGER NOT NULL,
    depreciation_method TEXT NOT NULL DEFAULT 'straight_line',
    depreciation_start_date DATE,
    carrying_value NUMERIC(18, 2) NOT NULL,
    accumulated_depreciation NUMERIC(18, 2) NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',
    category_details JSONB NOT NULL DEFAULT '{}'::jsonb,
    review_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    impairment_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    disposal_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    depreciation_schedule JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_reviewed TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_assets_category ON assets (asset_category);
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets (status);
CREATE INDEX IF NOT EXISTS idx_assets_created ON assets (created_at DESC);

CREATE TABLE IF NOT EXISTS asset_journals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    journal_id TEXT NOT NULL UNIQUE,
    journal_type TEXT NOT NULL,
    asset_id TEXT NOT NULL REFERENCES assets (asset_id) ON DELETE CASCADE,
    asset_name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending_review',
    description TEXT NOT NULL,
    reason TEXT NOT NULL,
    amount NUMERIC(18, 2) NOT NULL DEFAULT 0,
    debit_account TEXT,
    credit_account TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_by TEXT,
    submitter_name TEXT,
    reviewed_at TIMESTAMPTZ,
    reviewed_by TEXT,
    reviewer_name TEXT,
    rejection_reason TEXT,
    CONSTRAINT asset_journals_status_check CHECK (
        status IN ('pending_review', 'pending_cfo', 'approved', 'rejected')
    ),
    CONSTRAINT asset_journals_type_check CHECK (
        journal_type IN ('useful_life_review', 'impairment', 'disposal')
    )
);

CREATE INDEX IF NOT EXISTS idx_asset_journals_status ON asset_journals (status, submitted_at DESC);
CREATE INDEX IF NOT EXISTS idx_asset_journals_asset ON asset_journals (asset_id, submitted_at DESC);

CREATE TABLE IF NOT EXISTS asset_gl_balances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_id UUID REFERENCES public.financial_periods (id) ON DELETE SET NULL,
    gl_account_range TEXT NOT NULL DEFAULT '1200-1799',
    balance NUMERIC(18, 2) NOT NULL,
    note TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    source_session_id TEXT,
    updated_by TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_current BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_asset_gl_balances_current
    ON asset_gl_balances (gl_account_range)
    WHERE is_current = TRUE AND period_id IS NULL;

ALTER TABLE assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE asset_journals ENABLE ROW LEVEL SECURITY;
ALTER TABLE asset_gl_balances ENABLE ROW LEVEL SECURITY;

INSERT INTO schema_migrations (id, description)
VALUES (
    'create_asset_register_tables',
    'GRAP 17 assets, asset journals, GL balance reconciliation'
)
ON CONFLICT (id) DO UPDATE
SET applied_at = NOW(), description = EXCLUDED.description;
