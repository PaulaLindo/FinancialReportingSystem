-- Financial Periods Table Schema
-- For SADPMR Financial Reporting System

-- Create financial_periods table
CREATE TABLE IF NOT EXISTS financial_periods (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    start_date TEXT NOT NULL,  -- ISO format date string
    end_date TEXT NOT NULL,    -- ISO format date string
    due_date TEXT NOT NULL,    -- ISO format date string
    status TEXT NOT NULL DEFAULT 'draft',  -- draft, open, closed, archived
    urgency TEXT NOT NULL DEFAULT 'normal',  -- normal, urgent, overdue
    required_uploads INTEGER NOT NULL DEFAULT 1,
    uploaded_count INTEGER NOT NULL DEFAULT 0,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,  -- ISO format timestamp
    updated_at TEXT NOT NULL,  -- ISO format timestamp
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Create indexes for performance
CREATE INDEX idx_financial_periods_status ON financial_periods(status);
CREATE INDEX idx_financial_periods_created_by ON financial_periods(created_by);
CREATE INDEX idx_financial_periods_dates ON financial_periods(start_date, end_date);
CREATE INDEX idx_financial_periods_due_date ON financial_periods(due_date);

-- Add RLS (Row Level Security) policies
ALTER TABLE financial_periods ENABLE ROW LEVEL SECURITY;

-- Policy: Users can view all periods (read access for all authenticated users)
CREATE POLICY "Users can view financial periods" ON financial_periods
    FOR SELECT USING (auth.role() = 'authenticated');

-- Policy: Only users with manage_users permission can insert periods
CREATE POLICY "Users with manage_users permission can create periods" ON financial_periods
    FOR INSERT WITH CHECK (
        auth.role() = 'authenticated' AND 
        EXISTS (
            SELECT 1 FROM auth.users 
            WHERE id = auth.uid() 
            AND raw_user_meta_data->>'role' IN ('CFO', 'FINANCE_MANAGER', 'ADMIN')
        )
    );

-- Policy: Only users with manage_users permission can update periods
CREATE POLICY "Users with manage_users permission can update periods" ON financial_periods
    FOR UPDATE USING (
        auth.role() = 'authenticated' AND 
        EXISTS (
            SELECT 1 FROM auth.users 
            WHERE id = auth.uid() 
            AND raw_user_meta_data->>'role' IN ('CFO', 'FINANCE_MANAGER', 'ADMIN')
        )
    );

-- Policy: Only users with manage_users permission can delete periods
CREATE POLICY "Users with manage_users permission can delete periods" ON financial_periods
    FOR DELETE USING (
        auth.role() = 'authenticated' AND 
        EXISTS (
            SELECT 1 FROM auth.users 
            WHERE id = auth.uid() 
            AND raw_user_meta_data->>'role' IN ('CFO', 'FINANCE_MANAGER', 'ADMIN')
        )
    );

-- Sample data insertion (optional - for testing)
-- This would be removed in production and replaced with proper seed data
INSERT INTO financial_periods (
    id, 
    name, 
    description, 
    start_date, 
    end_date, 
    due_date, 
    status, 
    urgency, 
    required_uploads, 
    uploaded_count, 
    created_by, 
    created_at, 
    updated_at,
    metadata
) VALUES 
(
    'sample-period-1',
    'May 2026 Financial Period',
    'Monthly financial reporting for May 2026',
    '2026-05-01T00:00:00Z',
    '2026-05-31T23:59:59Z',
    '2026-06-07T23:59:59Z',
    'open',
    'normal',
    3,
    0,
    'system',
    '2026-05-02T00:00:00Z',
    '2026-05-02T00:00:00Z',
    '{"department": "finance", "fiscal_year": "2026"}'::jsonb
),
(
    'sample-period-2',
    'June 2026 Financial Period',
    'Monthly financial reporting for June 2026',
    '2026-06-01T00:00:00Z',
    '2026-06-30T23:59:59Z',
    '2026-07-07T23:59:59Z',
    'draft',
    'normal',
    3,
    0,
    'system',
    '2026-05-02T00:00:00Z',
    '2026-05-02T00:00:00Z',
    '{"department": "finance", "fiscal_year": "2026"}'::jsonb
),
(
    'sample-period-3',
    'April 2026 Financial Period',
    'Monthly financial reporting for April 2026',
    '2026-04-01T00:00:00Z',
    '2026-04-30T23:59:59Z',
    '2026-05-07T23:59:59Z',
    'closed',
    'normal',
    2,
    2,
    'system',
    '2026-05-02T00:00:00Z',
    '2026-05-02T00:00:00Z',
    '{"department": "finance", "fiscal_year": "2026", "completed_uploads": ["upload_1", "upload_2"]}'::jsonb
)
ON CONFLICT (id) DO NOTHING;
