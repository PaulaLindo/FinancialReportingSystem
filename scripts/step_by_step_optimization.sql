-- STEP-BY-STEP DATABASE OPTIMIZATION
-- Run each step separately in Supabase SQL Editor

-- ========================================
-- STEP 1: BACKUP CURRENT DATA (Run this first!)
-- ========================================
-- Create backup tables for safety
CREATE TABLE IF NOT EXISTS users_backup AS SELECT * FROM users;
CREATE TABLE IF NOT EXISTS balance_sheet_sessions_backup AS SELECT * FROM balance_sheet_sessions;
CREATE TABLE IF NOT EXISTS balance_sheet_columns_backup AS SELECT * FROM balance_sheet_columns;
CREATE TABLE IF NOT EXISTS balance_sheet_data_backup AS SELECT * FROM balance_sheet_data;
CREATE TABLE IF NOT EXISTS balance_sheet_templates_backup AS SELECT * FROM balance_sheet_templates;
CREATE TABLE IF NOT EXISTS balance_sheets_backup AS SELECT * FROM balance_sheets;
CREATE TABLE IF NOT EXISTS mapping_rules_backup AS SELECT * FROM mapping_rules;
CREATE TABLE IF NOT EXISTS grap_chart_of_accounts_backup AS SELECT * FROM grap_chart_of_accounts;

SELECT '=== BACKUP TABLES CREATED ===' as status;
SELECT 'You can now proceed with optimization safely' as message;

-- ========================================
-- STEP 2: CHECK FOR TRIAL BALANCE TABLES TO MIGRATE
-- ========================================
-- Check if trial balance tables exist and need migration
SELECT 
    tablename,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = tablename) 
        THEN 'EXISTS - Needs migration'
        ELSE 'NOT FOUND - Already migrated'
    END as status
FROM (VALUES 
    ('trial_balance_sessions'),
    ('trial_balance_columns'),
    ('trial_balance_data'),
    ('trial_balance_templates'),
    ('trial_balances')
) AS t(tablename);

-- ========================================
-- STEP 3: MIGRATE TRIAL BALANCE DATA (Only if tables exist)
-- ========================================
-- Only run this if trial_balance tables exist from step 2

-- Migrate sessions (only if both tables exist)
INSERT INTO balance_sheet_sessions (
    id, user_id, filename, original_filename, file_type, file_format, 
    status, total_rows, total_columns, file_size_bytes, checksum_md5, 
    created_at, updated_at, processed_at, metadata, processing_log, validation_results
)
SELECT 
    id, user_id, filename, original_filename, file_type, file_format, 
    status, total_rows, total_columns, file_size_bytes, checksum_md5, 
    created_at, updated_at, processed_at, metadata, processing_log, validation_results
FROM trial_balance_sessions
WHERE NOT EXISTS (
    SELECT 1 FROM balance_sheet_sessions 
    WHERE balance_sheet_sessions.id = trial_balance_sessions.id
);

-- Migrate columns
INSERT INTO balance_sheet_columns (
    id, session_id, column_name, original_column_name, column_index, 
    column_type, data_type, format_pattern, mapped_to, mapping_confidence, 
    is_required, is_key_column, validation_rules, transformation_rules, created_at
)
SELECT 
    id, session_id, column_name, original_column_name, column_index, 
    column_type, data_type, format_pattern, mapped_to, mapping_confidence, 
    is_required, is_key_column, validation_rules, transformation_rules, created_at
FROM trial_balance_columns
WHERE NOT EXISTS (
    SELECT 1 FROM balance_sheet_columns 
    WHERE balance_sheet_columns.id = trial_balance_columns.id
);

-- Migrate data
INSERT INTO balance_sheet_data (
    id, session_id, row_index, raw_data, processed_data, account_code, 
    account_description, account_number, debit_balance, credit_balance, 
    net_balance, period_1, period_2, period_3, period_4, period_5, 
    period_6, period_7, period_8, period_9, period_10, period_11, 
    period_12, grap_category, grap_account, grap_subcategory, mapping_status, 
    mapping_confidence, last_mapped_by, last_mapped_at, validation_status, 
    validation_errors, data_quality_score, row_type, is_active, notes, 
    created_at, updated_at
)
SELECT 
    id, session_id, row_index, raw_data, processed_data, account_code, 
    account_description, account_number, debit_balance, credit_balance, 
    net_balance, period_1, period_2, period_3, period_4, period_5, 
    period_6, period_7, period_8, period_9, period_10, period_11, 
    period_12, grap_category, grap_account, grap_subcategory, mapping_status, 
    mapping_confidence, last_mapped_by, last_mapped_at, validation_status, 
    validation_errors, data_quality_score, row_type, is_active, notes, 
    created_at, updated_at
FROM trial_balance_data
WHERE NOT EXISTS (
    SELECT 1 FROM balance_sheet_data 
    WHERE balance_sheet_data.id = trial_balance_data.id
);

SELECT '=== DATA MIGRATION COMPLETED ===' as status;

-- ========================================
-- STEP 4: CREATE NEW OPTIMIZATION TABLES
-- ========================================
-- Create approval workflows table
CREATE TABLE IF NOT EXISTS approval_workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL,
    document_type VARCHAR(50) NOT NULL,
    workflow_type VARCHAR(50) NOT NULL DEFAULT 'four_eyes',
    current_step INTEGER DEFAULT 1,
    status VARCHAR(50) DEFAULT 'pending',
    priority VARCHAR(20) DEFAULT 'normal',
    creator_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE NULL,
    metadata JSONB DEFAULT '{}',
    CONSTRAINT approval_workflows_document_type_check CHECK (
        (document_type)::text = ANY (ARRAY[
            'balance_sheet', 'income_statement', 'cash_flow', 
            'budget_report', 'asset_register', 'journal_entry'
        ]::text[])
    ),
    CONSTRAINT approval_workflows_status_check CHECK (
        (status)::text = ANY (ARRAY[
            'pending', 'in_review', 'approved', 'rejected', 
            'finalized', 'archived'
        ]::text[])
    )
);

-- Create approval steps table
CREATE TABLE IF NOT EXISTS approval_steps (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id UUID NOT NULL,
    step_name VARCHAR(100) NOT NULL,
    step_type VARCHAR(50) NOT NULL,
    step_order INTEGER NOT NULL,
    assigned_role VARCHAR(50) NOT NULL,
    required_approvals INTEGER DEFAULT 1,
    current_approvals INTEGER DEFAULT 0,
    status VARCHAR(50) DEFAULT 'pending',
    started_at TIMESTAMP WITH TIME ZONE NULL,
    completed_at TIMESTAMP WITH TIME ZONE NULL,
    approver_id UUID NULL,
    approval_notes TEXT NULL,
    rejection_reason TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT approval_steps_status_check CHECK (
        (status)::text = ANY (ARRAY[
            'pending', 'in_progress', 'approved', 'rejected', 'skipped'
        ]::text[])
    )
);

-- Create user sessions table
CREATE TABLE IF NOT EXISTS user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    session_token VARCHAR(255) NOT NULL,
    ip_address INET NULL,
    user_agent TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_activity TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Create audit logs table
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    table_name VARCHAR(100) NOT NULL,
    record_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,
    old_values JSONB NULL,
    new_values JSONB NULL,
    user_id UUID NULL,
    ip_address INET NULL,
    user_agent TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT audit_logs_action_check CHECK (
        (action)::text = ANY (ARRAY[
            'INSERT', 'UPDATE', 'DELETE', 'APPROVE', 'REJECT', 
            'LOGIN', 'LOGOUT', 'UPLOAD', 'DOWNLOAD'
        ]::text[])
    )
);

SELECT '=== NEW TABLES CREATED ===' as status;

-- ========================================
-- STEP 5: CREATE INDEXES FOR PERFORMANCE
-- ========================================
-- Approval workflow indexes
CREATE INDEX IF NOT EXISTS idx_approval_workflows_document_id ON approval_workflows(document_id);
CREATE INDEX IF NOT EXISTS idx_approval_workflows_status ON approval_workflows(status);
CREATE INDEX IF NOT EXISTS idx_approval_workflows_creator_id ON approval_workflows(creator_id);
CREATE INDEX IF NOT EXISTS idx_approval_workflows_created_at ON approval_workflows(created_at DESC);

-- Approval steps indexes
CREATE INDEX IF NOT EXISTS idx_approval_steps_workflow_id ON approval_steps(workflow_id);
CREATE INDEX IF NOT EXISTS idx_approval_steps_assigned_role ON approval_steps(assigned_role);
CREATE INDEX IF NOT EXISTS idx_approval_steps_status ON approval_steps(status);

-- User sessions indexes
CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_sessions_token ON user_sessions(session_token);
CREATE INDEX IF NOT EXISTS idx_user_sessions_expires_at ON user_sessions(expires_at);

-- Audit logs indexes
CREATE INDEX IF NOT EXISTS idx_audit_logs_table_record ON audit_logs(table_name, record_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at DESC);

SELECT '=== INDEXES CREATED ===' as status;

-- ========================================
-- STEP 6: ENABLE ROW LEVEL SECURITY
-- ========================================
-- Enable RLS on new tables
ALTER TABLE approval_workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

SELECT '=== RLS ENABLED ===' as status;

-- ========================================
-- STEP 7: CREATE RLS POLICIES
-- ========================================
-- Approval workflows policies
CREATE POLICY "Users can view own approval workflows" ON approval_workflows
    FOR SELECT USING (auth.uid()::text = creator_id::text OR auth.uid() IS NULL);

CREATE POLICY "Users can create approval workflows" ON approval_workflows
    FOR INSERT WITH CHECK (auth.uid()::text = creator_id::text OR auth.uid() IS NULL);

CREATE POLICY "Finance managers can view all workflows" ON approval_workflows
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() 
            AND users.role IN ('FINANCE_MANAGER', 'CFO', 'SYSTEM_ADMIN')
        )
    );

-- User sessions policies
CREATE POLICY "Users can view own sessions" ON user_sessions
    FOR SELECT USING (auth.uid()::text = user_id::text OR auth.uid() IS NULL);

CREATE POLICY "Users can create own sessions" ON user_sessions
    FOR INSERT WITH CHECK (auth.uid()::text = user_id::text OR auth.uid() IS NULL);

CREATE POLICY "Users can update own sessions" ON user_sessions
    FOR UPDATE USING (auth.uid()::text = user_id::text OR auth.uid() IS NULL);

-- Audit logs policies
CREATE POLICY "Users can view own audit logs" ON audit_logs
    FOR SELECT USING (auth.uid()::text = user_id::text OR auth.uid() IS NULL);

CREATE POLICY "Admins can view all audit logs" ON audit_logs
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() 
            AND users.role = 'SYSTEM_ADMIN'
        )
    );

SELECT '=== RLS POLICIES CREATED ===' as status;

-- ========================================
-- STEP 8: CREATE SYSTEM CONFIGURATION TABLE
-- ========================================
-- Create system configuration table
CREATE TABLE IF NOT EXISTS system_configuration (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    config_key VARCHAR(255) NOT NULL UNIQUE,
    config_value TEXT,
    config_type VARCHAR(50) NOT NULL DEFAULT 'string',
    description TEXT,
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

-- Create indexes for system_configuration
CREATE INDEX IF NOT EXISTS idx_system_configuration_key ON system_configuration(config_key);
CREATE INDEX IF NOT EXISTS idx_system_configuration_public ON system_configuration(is_public);

SELECT '=== SYSTEM CONFIGURATION TABLE CREATED ===' as status;

-- ========================================
-- STEP 9: INSERT DEFAULT CONFIGURATION
-- ========================================
-- Insert default system configuration
INSERT INTO system_configuration (config_key, config_value, config_type, description, is_public) VALUES
('approval_workflow_types', '["four_eyes", "three_eyes", "two_eyes"]', 'json', 'Available approval workflow types', true),
('max_file_size_mb', '50', 'number', 'Maximum file size in MB', true),
('supported_file_types', '["xlsx", "xls", "csv"]', 'json', 'Supported file types for upload', true),
('session_timeout_hours', '8', 'number', 'User session timeout in hours', false),
('audit_retention_days', '365', 'number', 'Days to retain audit logs', false),
('grap_version', 'GRAP 2024', 'string', 'Current GRAP version', true)
ON CONFLICT (config_key) DO NOTHING;

SELECT '=== DEFAULT CONFIGURATION INSERTED ===' as status;

-- ========================================
-- STEP 10: ENABLE RLS ON SYSTEM CONFIGURATION
-- ========================================
ALTER TABLE system_configuration ENABLE ROW LEVEL SECURITY;

-- System configuration policies
CREATE POLICY "Public configs visible to all" ON system_configuration
    FOR SELECT USING (is_public = true OR auth.uid() IS NULL);

CREATE POLICY "Admins can manage all configs" ON system_configuration
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() 
            AND users.role IN ('SYSTEM_ADMIN', 'CFO')
        )
    );

SELECT '=== SYSTEM CONFIGURATION RLS ENABLED ===' as status;

-- ========================================
-- STEP 11: VERIFICATION AND CLEANUP
-- ========================================
-- Verify all tables were created successfully
SELECT 
    'TABLE VERIFICATION' as check_type,
    tablename,
    CASE 
        WHEN EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = tablename) 
        THEN 'CREATED'
        ELSE 'FAILED'
    END as status
FROM (VALUES 
    ('approval_workflows'),
    ('approval_steps'),
    ('user_sessions'),
    ('audit_logs'),
    ('system_configuration')
) AS t(tablename)
ORDER BY tablename;

-- Check if trial balance tables can be safely dropped
SELECT 
    'SAFE TO DROP TRIAL BALANCE TABLES?' as check_type,
    tablename,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_name = REPLACE(tablename, 'trial_balance', 'balance_sheet')
        ) THEN 'YES - Data migrated to balance_sheet equivalent'
        ELSE 'NO - Balance sheet equivalent not found'
    END as safe_to_drop
FROM (VALUES 
    ('trial_balance_sessions'),
    ('trial_balance_columns'),
    ('trial_balance_data'),
    ('trial_balance_templates'),
    ('trial_balances')
) AS t(tablename);

SELECT '=== OPTIMIZATION COMPLETED ===' as final_status;
SELECT 'You can now safely drop trial_balance tables if needed' as next_step;
