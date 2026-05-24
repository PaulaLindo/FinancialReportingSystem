-- Database Schema Optimization Script
-- SADPMR Financial Reporting System
-- Run this in Supabase SQL Editor

-- ========================================
-- PRIORITY 1: ENHANCED APPROVAL WORKFLOW
-- ========================================

-- Create unified approval workflow table
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
    ),
    CONSTRAINT approval_workflows_priority_check CHECK (
        (priority)::text = ANY (ARRAY[
            'low', 'normal', 'high', 'urgent'
        ]::text[])
    )
);

-- Create approval steps tracking table
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
    CONSTRAINT approval_steps_step_type_check CHECK (
        (step_type)::text = ANY (ARRAY[
            'review', 'approve', 'verify', 'finalize'
        ]::text[])
    ),
    CONSTRAINT approval_steps_status_check CHECK (
        (status)::text = ANY (ARRAY[
            'pending', 'in_progress', 'approved', 'rejected', 'skipped'
        ]::text[])
    )
);

-- ========================================
-- PRIORITY 2: ENHANCED USER MANAGEMENT
-- ========================================

-- Create user sessions table for better security
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

-- ========================================
-- PRIORITY 3: AUDIT LOG SYSTEM
-- ========================================

-- Create comprehensive audit log table
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

-- ========================================
-- PRIORITY 4: SYSTEM CONFIGURATION
-- ========================================

-- Create system configuration table
CREATE TABLE IF NOT EXISTS system_configuration (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value JSONB NOT NULL,
    config_type VARCHAR(50) NOT NULL DEFAULT 'string',
    description TEXT NULL,
    is_public BOOLEAN DEFAULT FALSE,
    created_by UUID NULL,
    updated_by UUID NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT system_configuration_config_type_check CHECK (
        (config_type)::text = ANY (ARRAY[
            'string', 'number', 'boolean', 'json', 'array'
        ]::text[])
    )
);

-- ========================================
-- PRIORITY 5: ENHANCED FINANCIAL PERIODS
-- ========================================

-- Drop existing financial_periods if it exists and recreate with better structure
DROP TABLE IF EXISTS financial_periods CASCADE;

CREATE TABLE IF NOT EXISTS financial_periods (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_name VARCHAR(100) NOT NULL UNIQUE,
    period_code VARCHAR(20) NOT NULL UNIQUE,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    period_type VARCHAR(50) NOT NULL,
    fiscal_year INTEGER NOT NULL,
    is_current BOOLEAN DEFAULT FALSE,
    is_locked BOOLEAN DEFAULT FALSE,
    created_by UUID NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT financial_periods_type_check CHECK (
        (period_type)::text = ANY (ARRAY[
            'monthly', 'quarterly', 'semi_annual', 'annual'
        ]::text[])
    )
);

-- ========================================
-- INDEXES FOR PERFORMANCE
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

-- System configuration indexes
CREATE INDEX IF NOT EXISTS idx_system_configuration_key ON system_configuration(config_key);

-- Financial periods indexes
CREATE INDEX IF NOT EXISTS idx_financial_periods_current ON financial_periods(is_current);
CREATE INDEX IF NOT EXISTS idx_financial_periods_dates ON financial_periods(start_date, end_date);

-- ========================================
-- RLS POLICIES FOR NEW TABLES
-- ========================================

-- Enable RLS on new tables
ALTER TABLE approval_workflows ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE system_configuration ENABLE ROW LEVEL SECURITY;
ALTER TABLE financial_periods ENABLE ROW LEVEL SECURITY;

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

-- Approval steps policies
CREATE POLICY "Users can view steps for accessible workflows" ON approval_steps
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM approval_workflows 
            WHERE approval_workflows.id = approval_steps.workflow_id 
            AND (
                auth.uid()::text = approval_workflows.creator_id::text 
                OR EXISTS (
                    SELECT 1 FROM users 
                    WHERE users.id = auth.uid() 
                    AND users.role IN ('FINANCE_MANAGER', 'CFO', 'SYSTEM_ADMIN')
                )
            )
        )
    );

-- User sessions policies
CREATE POLICY "Users can view own sessions" ON user_sessions
    FOR SELECT USING (auth.uid()::text = user_id::text OR auth.uid() IS NULL);

CREATE POLICY "Users can create own sessions" ON user_sessions
    FOR INSERT WITH CHECK (auth.uid()::text = user_id::text OR auth.uid() IS NULL);

CREATE POLICY "Users can update own sessions" ON user_sessions
    FOR UPDATE USING (auth.uid()::text = user_id::text OR auth.uid() IS NULL);

CREATE POLICY "Users can delete own sessions" ON user_sessions
    FOR DELETE USING (auth.uid()::text = user_id::text OR auth.uid() IS NULL);

-- Audit logs policies (read-only for users, admin for all)
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

-- System configuration policies
CREATE POLICY "Public configs for all authenticated users" ON system_configuration
    FOR SELECT USING (is_public = TRUE OR auth.uid() IS NULL);

CREATE POLICY "Admins can manage system configuration" ON system_configuration
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() 
            AND users.role = 'SYSTEM_ADMIN'
        )
    );

-- Financial periods policies
CREATE POLICY "Authenticated users can view financial periods" ON financial_periods
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Admins can manage financial periods" ON financial_periods
    FOR ALL USING (
        EXISTS (
            SELECT 1 FROM users 
            WHERE users.id = auth.uid() 
            AND users.role = 'SYSTEM_ADMIN'
        )
    );

-- ========================================
-- INITIAL DATA SETUP
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

-- Insert default financial periods
INSERT INTO financial_periods (period_name, period_code, start_date, end_date, period_type, fiscal_year, is_current) VALUES
('January 2024', 'JAN2024', '2024-01-01', '2024-01-31', 'monthly', 2024, false),
('February 2024', 'FEB2024', '2024-02-01', '2024-02-29', 'monthly', 2024, false),
('March 2024', 'MAR2024', '2024-03-01', '2024-03-31', 'monthly', 2024, false),
('April 2024', 'APR2024', '2024-04-01', '2024-04-30', 'monthly', 2024, false),
('May 2024', 'MAY2024', '2024-05-01', '2024-05-31', 'monthly', 2024, false),
('June 2024', 'JUN2024', '2024-06-01', '2024-06-30', 'monthly', 2024, false),
('July 2024', 'JUL2024', '2024-07-01', '2024-07-31', 'monthly', 2024, false),
('August 2024', 'AUG2024', '2024-08-01', '2024-08-31', 'monthly', 2024, false),
('September 2024', 'SEP2024', '2024-09-01', '2024-09-30', 'monthly', 2024, false),
('October 2024', 'OCT2024', '2024-10-01', '2024-10-31', 'monthly', 2024, false),
('November 2024', 'NOV2024', '2024-11-01', '2024-11-30', 'monthly', 2024, false),
('December 2024', 'DEC2024', '2024-12-01', '2024-12-31', 'monthly', 2024, true)
ON CONFLICT (period_code) DO NOTHING;

SELECT '=== DATABASE OPTIMIZATION COMPLETED ===' as status;
SELECT 'New tables created: approval_workflows, approval_steps, user_sessions, audit_logs, system_configuration, financial_periods' as details;
