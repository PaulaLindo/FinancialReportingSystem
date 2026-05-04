-- Correct Database Migration Script: Trial Balance to Balance Sheet
-- This script matches the actual database schema structure
-- Run this in Supabase SQL Editor

-- Step 1: Create balance_sheet_sessions table (matching actual schema)
CREATE TABLE IF NOT EXISTS balance_sheet_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NULL,
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NULL,
    file_type VARCHAR(50) NULL DEFAULT 'unknown',
    file_format VARCHAR(50) NULL DEFAULT 'unknown',
    status VARCHAR(50) NULL DEFAULT 'uploaded',
    total_rows INTEGER NULL DEFAULT 0,
    total_columns INTEGER NULL DEFAULT 0,
    file_size_bytes BIGINT NULL,
    checksum_md5 VARCHAR(32) NULL,
    created_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE NULL,
    metadata JSONB NULL DEFAULT '{}',
    processing_log JSONB NULL DEFAULT '[]',
    validation_results JSONB NULL DEFAULT '{}',
    CONSTRAINT balance_sheet_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    CONSTRAINT balance_sheet_sessions_status_check CHECK (
        (status)::text = ANY (ARRAY['uploaded', 'processing', 'mapped', 'validated', 'approved', 'rejected', 'archived']::text[])
    )
);

-- Step 2: Create balance_sheet_columns table (matching actual schema)
CREATE TABLE IF NOT EXISTS balance_sheet_columns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NULL,
    column_name VARCHAR(255) NOT NULL,
    original_column_name VARCHAR(255) NULL,
    column_index INTEGER NOT NULL,
    column_type VARCHAR(50) NOT NULL,
    data_type VARCHAR(50) NOT NULL,
    format_pattern VARCHAR(255) NULL,
    mapped_to VARCHAR(100) NULL,
    mapping_confidence NUMERIC(3, 2) NULL DEFAULT 0.00,
    is_required BOOLEAN NULL DEFAULT FALSE,
    is_key_column BOOLEAN NULL DEFAULT FALSE,
    validation_rules JSONB NULL DEFAULT '{}',
    transformation_rules JSONB NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    CONSTRAINT balance_sheet_columns_session_id_fkey FOREIGN KEY (session_id) REFERENCES balance_sheet_sessions (id) ON DELETE CASCADE,
    CONSTRAINT balance_sheet_columns_type_check CHECK (
        (column_type)::text = ANY (ARRAY['account_code', 'account_desc', 'debit', 'credit', 'net_balance', 'period_1', 'period_2', 'period_3', 'period_4', 'period_5', 'period_6', 'period_7', 'period_8', 'period_9', 'period_10', 'period_11', 'period_12', 'custom']::text[])
    )
);

-- Step 3: Create balance_sheet_data table (matching actual schema)
CREATE TABLE IF NOT EXISTS balance_sheet_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NULL,
    row_index INTEGER NOT NULL,
    raw_data JSONB NOT NULL,
    processed_data JSONB NULL DEFAULT '{}',
    account_code VARCHAR(100) NULL,
    account_description TEXT NULL,
    account_number VARCHAR(50) NULL,
    debit_balance NUMERIC(15, 2) NULL,
    credit_balance NUMERIC(15, 2) NULL,
    net_balance NUMERIC(15, 2) NULL,
    period_1 NUMERIC(15, 2) NULL,
    period_2 NUMERIC(15, 2) NULL,
    period_3 NUMERIC(15, 2) NULL,
    period_4 NUMERIC(15, 2) NULL,
    period_5 NUMERIC(15, 2) NULL,
    period_6 NUMERIC(15, 2) NULL,
    period_7 NUMERIC(15, 2) NULL,
    period_8 NUMERIC(15, 2) NULL,
    period_9 NUMERIC(15, 2) NULL,
    period_10 NUMERIC(15, 2) NULL,
    period_11 NUMERIC(15, 2) NULL,
    period_12 NUMERIC(15, 2) NULL,
    grap_category VARCHAR(100) NULL,
    grap_account VARCHAR(100) NULL,
    grap_subcategory VARCHAR(100) NULL,
    mapping_status VARCHAR(50) NULL DEFAULT 'unmapped',
    mapping_confidence NUMERIC(3, 2) NULL DEFAULT 0.00,
    last_mapped_by UUID NULL,
    last_mapped_at TIMESTAMP WITH TIME ZONE NULL,
    validation_status VARCHAR(50) NULL DEFAULT 'pending',
    validation_errors JSONB NULL DEFAULT '[]',
    data_quality_score NUMERIC(3, 2) NULL DEFAULT 0.00,
    row_type VARCHAR(50) NULL DEFAULT 'data',
    is_active BOOLEAN NULL DEFAULT TRUE,
    notes TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    CONSTRAINT balance_sheet_data_last_mapped_by_fkey FOREIGN KEY (last_mapped_by) REFERENCES users (id),
    CONSTRAINT balance_sheet_data_session_id_fkey FOREIGN KEY (session_id) REFERENCES balance_sheet_sessions (id) ON DELETE CASCADE,
    CONSTRAINT balance_sheet_data_status_check CHECK (
        (mapping_status)::text = ANY (ARRAY['unmapped', 'auto_mapped', 'manual_mapped', 'reviewed', 'approved', 'rejected']::text[])
    ),
    CONSTRAINT balance_sheet_data_type_check CHECK (
        (row_type)::text = ANY (ARRAY['data', 'header', 'footer', 'total', 'subtotal']::text[])
    ),
    CONSTRAINT balance_sheet_data_validation_check CHECK (
        (validation_status)::text = ANY (ARRAY['pending', 'valid', 'invalid', 'warning']::text[])
    )
);

-- Step 4: Create balance_sheet_templates table (matching actual schema)
CREATE TABLE IF NOT EXISTS balance_sheet_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NULL,
    template_name VARCHAR(255) NOT NULL,
    template_description TEXT NULL,
    file_type VARCHAR(50) NULL,
    column_mappings JSONB NOT NULL,
    validation_rules JSONB NULL DEFAULT '{}',
    processing_rules JSONB NULL DEFAULT '{}',
    usage_count INTEGER NULL DEFAULT 0,
    success_rate NUMERIC(3, 2) NULL DEFAULT 0.00,
    is_active BOOLEAN NULL DEFAULT TRUE,
    is_public BOOLEAN NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    CONSTRAINT balance_sheet_templates_user_id_fkey FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Step 5: Create balance_sheets table (matching actual schema)
CREATE TABLE IF NOT EXISTS balance_sheets (
    id UUID PRIMARY KEY DEFAULT extensions.uuid_generate_v4(),
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    public_url TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NOW(),
    status TEXT NULL DEFAULT 'uploaded'
);

-- Step 6: Create indexes
CREATE INDEX IF NOT EXISTS idx_balance_sheet_sessions_user_id ON balance_sheet_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_balance_sheet_sessions_status ON balance_sheet_sessions(status);
CREATE INDEX IF NOT EXISTS idx_balance_sheet_sessions_created_at ON balance_sheet_sessions(created_at);
CREATE INDEX IF NOT EXISTS idx_balance_sheet_columns_session_id ON balance_sheet_columns(session_id);
CREATE INDEX IF NOT EXISTS idx_balance_sheet_columns_type ON balance_sheet_columns(column_type);
CREATE INDEX IF NOT EXISTS idx_balance_sheet_data_session_id ON balance_sheet_data(session_id);
CREATE INDEX IF NOT EXISTS idx_balance_sheet_data_account_code ON balance_sheet_data(account_code);
CREATE INDEX IF NOT EXISTS idx_balance_sheet_data_mapping_status ON balance_sheet_data(mapping_status);
CREATE INDEX IF NOT EXISTS idx_balance_sheet_data_grap_category ON balance_sheet_data(grap_category);
CREATE INDEX IF NOT EXISTS idx_balance_sheet_templates_user_id ON balance_sheet_templates(user_id);
CREATE INDEX IF NOT EXISTS idx_balance_sheet_templates_active ON balance_sheet_templates(is_active);
CREATE INDEX IF NOT EXISTS idx_balance_sheets_user_id ON balance_sheets(user_id);
CREATE INDEX IF NOT EXISTS idx_balance_sheets_uploaded_at ON balance_sheets(uploaded_at DESC);

-- Step 7: Migrate data - Sessions
INSERT INTO balance_sheet_sessions (
    id, user_id, filename, original_filename, file_type, file_format, 
    status, total_rows, total_columns, file_size_bytes, checksum_md5, 
    created_at, updated_at, processed_at, metadata, processing_log, validation_results
)
SELECT 
    id, user_id, filename, original_filename, file_type, file_format, 
    status, total_rows, total_columns, file_size_bytes, checksum_md5, 
    created_at, updated_at, processed_at, metadata, processing_log, validation_results
FROM trial_balance_sessions;

-- Step 8: Migrate data - Columns
INSERT INTO balance_sheet_columns (
    id, session_id, column_name, original_column_name, column_index, 
    column_type, data_type, format_pattern, mapped_to, mapping_confidence, 
    is_required, is_key_column, validation_rules, transformation_rules, created_at
)
SELECT 
    id, session_id, column_name, original_column_name, column_index, 
    column_type, data_type, format_pattern, mapped_to, mapping_confidence, 
    is_required, is_key_column, validation_rules, transformation_rules, created_at
FROM trial_balance_columns;

-- Step 9: Migrate data - Data rows
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
FROM trial_balance_data;

-- Step 10: Migrate data - Templates
INSERT INTO balance_sheet_templates (
    id, user_id, template_name, template_description, file_type, 
    column_mappings, validation_rules, processing_rules, usage_count, 
    success_rate, is_active, is_public, created_at, updated_at
)
SELECT 
    id, user_id, template_name, template_description, file_type, 
    column_mappings, validation_rules, processing_rules, usage_count, 
    success_rate, is_active, is_public, created_at, updated_at
FROM trial_balance_templates;

-- Step 11: Migrate data - Balance sheets
INSERT INTO balance_sheets (
    id, user_id, filename, storage_path, public_url, file_size, 
    uploaded_at, status
)
SELECT 
    id, user_id, filename, storage_path, public_url, file_size, 
    uploaded_at, status
FROM trial_balances;

-- Step 12: Verify migration results
SELECT '=== MIGRATION VERIFICATION ===' as info;

SELECT 'NEW BALANCE SHEET TABLES:' as table_type, 
       'balance_sheet_sessions' as table_name, 
       COUNT(*) as row_count 
FROM balance_sheet_sessions
UNION ALL
SELECT 'NEW BALANCE SHEET TABLES:' as table_type, 
       'balance_sheet_columns' as table_name, 
       COUNT(*) as row_count 
FROM balance_sheet_columns
UNION ALL
SELECT 'NEW BALANCE SHEET TABLES:' as table_type, 
       'balance_sheet_data' as table_name, 
       COUNT(*) as row_count 
FROM balance_sheet_data
UNION ALL
SELECT 'NEW BALANCE SHEET TABLES:' as table_type, 
       'balance_sheet_templates' as table_name, 
       COUNT(*) as row_count 
FROM balance_sheet_templates
UNION ALL
SELECT 'NEW BALANCE SHEET TABLES:' as table_type, 
       'balance_sheets' as table_name, 
       COUNT(*) as row_count 
FROM balance_sheets
UNION ALL
SELECT 'OLD TRIAL BALANCE TABLES:' as table_type, 
       'trial_balance_sessions' as table_name, 
       COUNT(*) as row_count 
FROM trial_balance_sessions
UNION ALL
SELECT 'OLD TRIAL BALANCE TABLES:' as table_type, 
       'trial_balance_columns' as table_name, 
       COUNT(*) as row_count 
FROM trial_balance_columns
UNION ALL
SELECT 'OLD TRIAL BALANCE TABLES:' as table_type, 
       'trial_balance_data' as table_name, 
       COUNT(*) as row_count 
FROM trial_balance_data
UNION ALL
SELECT 'OLD TRIAL BALANCE TABLES:' as table_type, 
       'trial_balance_templates' as table_name, 
       COUNT(*) as row_count 
FROM trial_balance_templates
UNION ALL
SELECT 'OLD TRIAL BALANCE TABLES:' as table_type, 
       'trial_balances' as table_name, 
       COUNT(*) as row_count 
FROM trial_balances
ORDER BY table_type, table_name;

-- Step 13: Create backup tables (for safety)
CREATE TABLE IF NOT EXISTS trial_balance_sessions_backup AS SELECT * FROM trial_balance_sessions;
CREATE TABLE IF NOT EXISTS trial_balance_columns_backup AS SELECT * FROM trial_balance_columns;
CREATE TABLE IF NOT EXISTS trial_balance_data_backup AS SELECT * FROM trial_balance_data;
CREATE TABLE IF NOT EXISTS trial_balance_templates_backup AS SELECT * FROM trial_balance_templates;
CREATE TABLE IF NOT EXISTS trial_balances_backup AS SELECT * FROM trial_balances;

SELECT '=== MIGRATION COMPLETED SUCCESSFULLY ===' as status;
