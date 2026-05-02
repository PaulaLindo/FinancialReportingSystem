-- ========================================
-- FLEXIBLE TRIAL BALANCE DATABASE SCHEMA
-- Handles any kind of trial balance format
-- ========================================

-- Users table (for authentication and authorization)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'USER',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT users_role_check CHECK (role IN ('USER', 'FINANCE_CLERK', 'FINANCE_MANAGER', 'CFO', 'ASSET_MANAGER', 'AUDITOR', 'SYSTEM_ADMIN', 'ACCOUNTANT'))
);

-- Core trial balance sessions (flexible for any format)
CREATE TABLE trial_balance_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    file_type VARCHAR(50) DEFAULT 'unknown', -- 'standard', 'hospital', 'government', 'custom', 'excel', 'csv'
    file_format VARCHAR(50) DEFAULT 'unknown', -- 'xlsx', 'xls', 'csv', 'json'
    status VARCHAR(50) DEFAULT 'uploaded', -- 'uploaded', 'processing', 'mapped', 'validated', 'approved', 'rejected'
    total_rows INTEGER DEFAULT 0,
    total_columns INTEGER DEFAULT 0,
    file_size_bytes BIGINT,
    checksum_md5 VARCHAR(32), -- file integrity check
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata for flexible storage
    metadata JSONB DEFAULT '{}', -- store any custom fields, detected patterns, etc.
    processing_log JSONB DEFAULT '[]', -- detailed processing history
    validation_results JSONB DEFAULT '{}', -- validation results and errors
    
    -- Constraints
    CONSTRAINT trial_balance_sessions_status_check CHECK (status IN ('uploaded', 'processing', 'mapped', 'validated', 'processed', 'approved', 'rejected', 'archived'))
);

-- Dynamic column definitions (handles any trial balance structure)
CREATE TABLE trial_balance_columns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES trial_balance_sessions(id) ON DELETE CASCADE,
    column_name VARCHAR(255) NOT NULL,
    original_column_name VARCHAR(255), -- keep original name for reference
    column_index INTEGER NOT NULL,
    
    -- Column classification (flexible)
    column_type VARCHAR(50) NOT NULL, -- 'account_code', 'account_desc', 'debit', 'credit', 'net_balance', 'period_1', 'period_2', 'custom'
    data_type VARCHAR(50) NOT NULL, -- 'text', 'number', 'date', 'boolean', 'currency'
    format_pattern VARCHAR(255), -- regex pattern for validation
    
    -- Mapping information
    mapped_to VARCHAR(100), -- what this column maps to in standard format
    mapping_confidence DECIMAL(3,2) DEFAULT 0.00, -- AI mapping confidence
    is_required BOOLEAN DEFAULT FALSE,
    is_key_column BOOLEAN DEFAULT FALSE, -- primary identifier column
    
    -- Validation rules
    validation_rules JSONB DEFAULT '{}', -- custom validation rules
    transformation_rules JSONB DEFAULT '{}', -- data transformation rules
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT trial_balance_columns_type_check CHECK (column_type IN ('account_code', 'account_desc', 'debit', 'credit', 'net_balance', 'period_1', 'period_2', 'period_3', 'period_4', 'period_5', 'period_6', 'period_7', 'period_8', 'period_9', 'period_10', 'period_11', 'period_12', 'custom'))
);

-- Trial balance data rows (flexible structure)
CREATE TABLE trial_balance_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES trial_balance_sessions(id) ON DELETE CASCADE,
    row_index INTEGER NOT NULL,
    
    -- Original and processed data
    raw_data JSONB NOT NULL, -- store complete original row
    processed_data JSONB DEFAULT '{}', -- cleaned/processed data
    
    -- Standardized fields (populated after processing)
    account_code VARCHAR(100),
    account_description TEXT,
    account_number VARCHAR(50), -- alternative account identifier
    
    -- Balance fields (flexible - can handle multiple periods)
    debit_balance DECIMAL(15,2),
    credit_balance DECIMAL(15,2),
    net_balance DECIMAL(15,2),
    
    -- Multi-period support
    period_1 DECIMAL(15,2),
    period_2 DECIMAL(15,2),
    period_3 DECIMAL(15,2),
    period_4 DECIMAL(15,2),
    period_5 DECIMAL(15,2),
    period_6 DECIMAL(15,2),
    period_7 DECIMAL(15,2),
    period_8 DECIMAL(15,2),
    period_9 DECIMAL(15,2),
    period_10 DECIMAL(15,2),
    period_11 DECIMAL(15,2),
    period_12 DECIMAL(15,2),
    
    -- GRAP mapping
    grap_category VARCHAR(100),
    grap_account VARCHAR(100),
    grap_subcategory VARCHAR(100),
    
    -- Mapping status and quality
    mapping_status VARCHAR(50) DEFAULT 'unmapped', -- 'unmapped', 'auto_mapped', 'manual_mapped', 'reviewed', 'approved'
    mapping_confidence DECIMAL(3,2) DEFAULT 0.00,
    last_mapped_by UUID REFERENCES users(id),
    last_mapped_at TIMESTAMP WITH TIME ZONE,
    
    -- Validation and quality
    validation_status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'valid', 'invalid', 'warning'
    validation_errors JSONB DEFAULT '[]',
    data_quality_score DECIMAL(3,2) DEFAULT 0.00,
    
    -- Metadata
    row_type VARCHAR(50) DEFAULT 'data', -- 'data', 'header', 'footer', 'total', 'subtotal'
    is_active BOOLEAN DEFAULT TRUE,
    notes TEXT,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT trial_balance_data_status_check CHECK (mapping_status IN ('unmapped', 'auto_mapped', 'manual_mapped', 'reviewed', 'approved', 'rejected')),
    CONSTRAINT trial_balance_data_validation_check CHECK (validation_status IN ('pending', 'valid', 'invalid', 'warning')),
    CONSTRAINT trial_balance_data_type_check CHECK (row_type IN ('data', 'header', 'footer', 'total', 'subtotal'))
);

-- Mapping rules and patterns (learned and user-defined)
CREATE TABLE mapping_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Rule definition
    rule_name VARCHAR(255) NOT NULL,
    rule_type VARCHAR(50) NOT NULL, -- 'column_mapping', 'account_mapping', 'category_mapping', 'validation'
    pattern_type VARCHAR(50) NOT NULL, -- 'regex', 'exact', 'contains', 'starts_with', 'ends_with', 'fuzzy'
    
    -- Pattern matching
    input_pattern VARCHAR(500) NOT NULL, -- regex or text pattern
    output_value VARCHAR(255) NOT NULL, -- mapped value
    
    -- Context and conditions
    context JSONB DEFAULT '{}', -- additional context for rule matching
    conditions JSONB DEFAULT '{}', -- conditions for rule application
    
    -- Rule metadata
    confidence_score DECIMAL(3,2) DEFAULT 0.00,
    usage_count INTEGER DEFAULT 0,
    success_rate DECIMAL(3,2) DEFAULT 0.00,
    
    -- Status and management
    is_active BOOLEAN DEFAULT TRUE,
    is_system_rule BOOLEAN DEFAULT FALSE, -- system-generated vs user-defined
    priority INTEGER DEFAULT 50, -- rule priority (higher = more priority)
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT mapping_rules_type_check CHECK (rule_type IN ('column_mapping', 'account_mapping', 'category_mapping', 'validation')),
    CONSTRAINT mapping_rules_pattern_check CHECK (pattern_type IN ('regex', 'exact', 'contains', 'starts_with', 'ends_with', 'fuzzy'))
);

-- GRAP chart of accounts (master data)
CREATE TABLE grap_chart_of_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- GRAP classification
    grap_category VARCHAR(100) NOT NULL,
    grap_subcategory VARCHAR(100),
    grap_account VARCHAR(100) NOT NULL,
    grap_account_code VARCHAR(50),
    
    -- Account details
    account_description TEXT,
    account_type VARCHAR(50), -- 'asset', 'liability', 'equity', 'revenue', 'expense'
    normal_balance VARCHAR(10), -- 'debit', 'credit'
    
    -- Classification and mapping
    keywords JSONB DEFAULT '[]', -- keywords for matching
    alternative_names JSONB DEFAULT '[]', -- alternative account names
    mapping_patterns JSONB DEFAULT '[]', -- patterns for auto-mapping
    
    -- Status and metadata
    is_active BOOLEAN DEFAULT TRUE,
    is_custom BOOLEAN DEFAULT FALSE, -- custom vs standard GRAP account
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT grap_coa_type_check CHECK (account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')),
    CONSTRAINT grap_coa_balance_check CHECK (normal_balance IN ('debit', 'credit'))
);

-- Processing history and audit trail
CREATE TABLE processing_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES trial_balance_sessions(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Action details
    action_type VARCHAR(100) NOT NULL, -- 'upload', 'process', 'map', 'validate', 'approve', 'reject', 'export'
    action_description TEXT,
    
    -- Before/after states
    before_state JSONB,
    after_state JSONB,
    
    -- Metadata
    processing_time_ms INTEGER,
    affected_rows INTEGER,
    error_details JSONB,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT processing_history_action_check CHECK (action_type IN ('upload', 'process', 'map', 'validate', 'approve', 'reject', 'export', 'delete', 'modify'))
);

-- User-defined templates and formats
CREATE TABLE trial_balance_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Template details
    template_name VARCHAR(255) NOT NULL,
    template_description TEXT,
    file_type VARCHAR(50), -- 'excel', 'csv', 'fixed_width'
    
    -- Column mappings
    column_mappings JSONB NOT NULL, -- detailed column mapping rules
    
    -- Validation rules
    validation_rules JSONB DEFAULT '{}',
    
    -- Processing rules
    processing_rules JSONB DEFAULT '{}',
    
    -- Usage statistics
    usage_count INTEGER DEFAULT 0,
    success_rate DECIMAL(3,2) DEFAULT 0.00,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_public BOOLEAN DEFAULT FALSE, -- share with other users
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_trial_balance_sessions_user_id ON trial_balance_sessions(user_id);
CREATE INDEX idx_trial_balance_sessions_status ON trial_balance_sessions(status);
CREATE INDEX idx_trial_balance_sessions_created_at ON trial_balance_sessions(created_at);

CREATE INDEX idx_trial_balance_columns_session_id ON trial_balance_columns(session_id);
CREATE INDEX idx_trial_balance_columns_type ON trial_balance_columns(column_type);

CREATE INDEX idx_trial_balance_data_session_id ON trial_balance_data(session_id);
CREATE INDEX idx_trial_balance_data_account_code ON trial_balance_data(account_code);
CREATE INDEX idx_trial_balance_data_mapping_status ON trial_balance_data(mapping_status);
CREATE INDEX idx_trial_balance_data_grap_category ON trial_balance_data(grap_category);

CREATE INDEX idx_mapping_rules_user_id ON mapping_rules(user_id);
CREATE INDEX idx_mapping_rules_type ON mapping_rules(rule_type);
CREATE INDEX idx_mapping_rules_active ON mapping_rules(is_active);

CREATE INDEX idx_grap_coa_category ON grap_chart_of_accounts(grap_category);
CREATE INDEX idx_grap_coa_active ON grap_chart_of_accounts(is_active);

CREATE INDEX idx_processing_history_session_id ON processing_history(session_id);
CREATE INDEX idx_processing_history_user_id ON processing_history(user_id);
CREATE INDEX idx_processing_history_created_at ON processing_history(created_at);

CREATE INDEX idx_trial_balance_templates_user_id ON trial_balance_templates(user_id);
CREATE INDEX idx_trial_balance_templates_active ON trial_balance_templates(is_active);

-- Row Level Security (RLS) policies
ALTER TABLE trial_balance_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE trial_balance_columns ENABLE ROW LEVEL SECURITY;
ALTER TABLE trial_balance_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE mapping_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE grap_chart_of_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE processing_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE trial_balance_templates ENABLE ROW LEVEL SECURITY;

-- RLS Policies (basic - can be expanded)
CREATE POLICY "Users can view their own trial balance sessions" ON trial_balance_sessions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own trial balance sessions" ON trial_balance_sessions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update their own trial balance sessions" ON trial_balance_sessions
    FOR UPDATE USING (auth.uid() = user_id);

CREATE POLICY "Users can delete their own trial balance sessions" ON trial_balance_sessions
    FOR DELETE USING (auth.uid() = user_id);

-- Similar policies for other tables...
CREATE POLICY "Users can view trial balance data for their sessions" ON trial_balance_data
    FOR SELECT USING (
        session_id IN (
            SELECT id FROM trial_balance_sessions WHERE user_id = auth.uid()
        )
    );

-- Functions for common operations
CREATE OR REPLACE FUNCTION get_trial_balance_summary(p_session_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_summary JSONB;
BEGIN
    SELECT jsonb_build_object(
        'total_rows', COUNT(*),
        'mapped_rows', COUNT(*) FILTER (WHERE mapping_status IN ('auto_mapped', 'manual_mapped', 'approved')),
        'unmapped_rows', COUNT(*) FILTER (WHERE mapping_status = 'unmapped'),
        'valid_rows', COUNT(*) FILTER (WHERE validation_status = 'valid'),
        'invalid_rows', COUNT(*) FILTER (WHERE validation_status = 'invalid'),
        'total_debit', COALESCE(SUM(debit_balance), 0),
        'total_credit', COALESCE(SUM(credit_balance), 0),
        'net_balance', COALESCE(SUM(net_balance), 0),
        'mapping_completion', ROUND(
            (COUNT(*) FILTER (WHERE mapping_status IN ('auto_mapped', 'manual_mapped', 'approved')) * 100.0 / NULLIF(COUNT(*), 0)), 2
        )
    ) INTO v_summary
    FROM trial_balance_data
    WHERE session_id = p_session_id AND is_active = TRUE;
    
    RETURN v_summary;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger for updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply triggers
CREATE TRIGGER update_trial_balance_sessions_updated_at
    BEFORE UPDATE ON trial_balance_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trial_balance_data_updated_at
    BEFORE UPDATE ON trial_balance_data
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_mapping_rules_updated_at
    BEFORE UPDATE ON mapping_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_grap_coa_updated_at
    BEFORE UPDATE ON grap_chart_of_accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trial_balance_templates_updated_at
    BEFORE UPDATE ON trial_balance_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- SUBMISSIONS WORKFLOW TABLES
-- ========================================

-- Submissions for finance manager review
CREATE TABLE submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES trial_balance_sessions(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- Submission details
    submission_name VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    period_id UUID,
    
    -- Status and workflow
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'under_review', 'approved', 'rejected', 'returned_for_revision'
    priority VARCHAR(20) DEFAULT 'normal', -- 'low', 'normal', 'high', 'urgent'
    
    -- Mapping statistics
    total_accounts INTEGER DEFAULT 0,
    mapped_accounts INTEGER DEFAULT 0,
    unmapped_accounts INTEGER DEFAULT 0,
    mapping_completion_percentage DECIMAL(5,2) DEFAULT 0.00,
    
    -- Financial totals
    total_assets DECIMAL(15,2) DEFAULT 0.00,
    total_liabilities DECIMAL(15,2) DEFAULT 0.00,
    total_equity DECIMAL(15,2) DEFAULT 0.00,
    total_revenue DECIMAL(15,2) DEFAULT 0.00,
    total_expenses DECIMAL(15,2) DEFAULT 0.00,
    
    -- Quality metrics
    data_quality_score DECIMAL(3,2) DEFAULT 0.00,
    grap_categories_used INTEGER DEFAULT 0,
    
    -- Review information
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,
    review_notes TEXT,
    approval_comments TEXT,
    rejection_reason TEXT,
    
    -- Locked status (prevents changes after submission)
    is_locked BOOLEAN DEFAULT FALSE,
    locked_at TIMESTAMP WITH TIME ZONE,
    locked_by UUID REFERENCES users(id),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    grap_mapping_data JSONB DEFAULT '{}', -- Complete GRAP mapping data
    financial_statements JSONB DEFAULT '{}', -- Generated financial statements
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT submissions_status_check CHECK (status IN ('pending', 'under_review', 'approved', 'rejected', 'returned_for_revision')),
    CONSTRAINT submissions_priority_check CHECK (priority IN ('low', 'normal', 'high', 'urgent'))
);

-- Enable RLS for submissions table
ALTER TABLE submissions ENABLE ROW LEVEL SECURITY;

-- RLS Policies for submissions
CREATE POLICY "Users can view their own submissions" ON submissions
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert their own submissions" ON submissions
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Finance managers can view all submissions" ON submissions
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM users WHERE id = auth.uid() AND role IN ('FINANCE_MANAGER', 'CFO')
        )
    );

CREATE POLICY "Finance managers can update submission status" ON submissions
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM users WHERE id = auth.uid() AND role IN ('FINANCE_MANAGER', 'CFO')
        )
    );

-- Trigger for submissions updated_at
CREATE TRIGGER update_submissions_updated_at
    BEFORE UPDATE ON submissions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
