-- Session queue performance (FM/CFO pending, clerk history).
-- Run in Supabase SQL editor when preparing for more than demo-scale traffic.

CREATE INDEX IF NOT EXISTS idx_balance_sheet_sessions_status_updated
    ON balance_sheet_sessions (status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_balance_sheet_sessions_user_updated
    ON balance_sheet_sessions (user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_income_statement_sessions_status_updated
    ON income_statement_sessions (status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_income_statement_sessions_user_updated
    ON income_statement_sessions (user_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_budget_report_sessions_status_updated
    ON budget_report_sessions (status, updated_at DESC);

CREATE INDEX IF NOT EXISTS idx_budget_report_sessions_user_updated
    ON budget_report_sessions (user_id, updated_at DESC);
