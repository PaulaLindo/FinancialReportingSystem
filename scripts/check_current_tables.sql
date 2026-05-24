-- Check Current Database Structure
-- Run this in Supabase SQL Editor first

-- ========================================
-- 1. LIST ALL TABLES IN DATABASE
-- ========================================
SELECT 
    schemaname,
    tablename,
    tableowner,
    tablespace,
    hasindexes,
    hasrules,
    hastriggers
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;

-- ========================================
-- 2. GET TABLE SIZES AND ROW COUNTS
-- ========================================
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = schemaname AND table_name = tablename) AS column_count
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- ========================================
-- 3. CHECK FOR TRIAL BALANCE VS BALANCE SHEET TABLES
-- ========================================
SELECT 
    'TABLE ANALYSIS' as analysis_type,
    tablename,
    CASE 
        WHEN tablename LIKE '%trial_balance%' THEN 'LEGACY - Should be migrated'
        WHEN tablename LIKE '%balance_sheet%' THEN 'CURRENT - Keep and optimize'
        WHEN tablename IN ('users', 'mapping_rules', 'grap_chart_of_accounts') THEN 'CORE - Keep'
        WHEN tablename LIKE '%approval%' THEN 'APPROVAL - Check if needed'
        WHEN tablename LIKE '%audit%' THEN 'AUDIT - Check if needed'
        ELSE 'UNKNOWN - Review needed'
    END as recommendation
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;

-- ========================================
-- 4. CHECK FOR DUPLICATE TABLES
-- ========================================
SELECT 
    'DUPLICATE CHECK' as analysis_type,
    tablename,
    CASE 
        WHEN tablename = 'trial_balance_sessions' THEN 'DUPLICATE - Migrate to balance_sheet_sessions'
        WHEN tablename = 'trial_balance_columns' THEN 'DUPLICATE - Migrate to balance_sheet_columns'
        WHEN tablename = 'trial_balance_data' THEN 'DUPLICATE - Migrate to balance_sheet_data'
        WHEN tablename = 'trial_balance_templates' THEN 'DUPLICATE - Migrate to balance_sheet_templates'
        WHEN tablename = 'trial_balances' THEN 'DUPLICATE - Migrate to balance_sheets'
        ELSE 'UNIQUE - Keep'
    END as duplicate_status
FROM pg_tables 
WHERE schemaname = 'public'
AND (tablename LIKE '%trial_balance%' OR tablename LIKE '%balance_sheet%')
ORDER BY tablename;

-- ========================================
-- 5. CHECK FOR MISSING CORE TABLES
-- ========================================
SELECT 
    'MISSING TABLES' as analysis_type,
    expected_table,
    CASE 
        WHEN EXISTS (
            SELECT 1 FROM pg_tables 
            WHERE schemaname = 'public' AND tablename = expected_table
        ) THEN 'EXISTS'
        ELSE 'MISSING - Create needed'
    END as status
FROM (VALUES 
    ('users'),
    ('balance_sheet_sessions'),
    ('balance_sheet_columns'),
    ('balance_sheet_data'),
    ('balance_sheet_templates'),
    ('balance_sheets'),
    ('mapping_rules'),
    ('grap_chart_of_accounts'),
    ('financial_periods'),
    ('approval_workflows'),
    ('approval_steps'),
    ('user_sessions'),
    ('audit_logs'),
    ('system_configuration')
) AS t(expected_table)
ORDER BY expected_table;

-- ========================================
-- 6. CHECK TABLE RELATIONSHIPS
-- ========================================
SELECT 
    tc.table_name,
    tc.constraint_name,
    tc.constraint_type,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
WHERE tc.constraint_type IN ('FOREIGN KEY', 'PRIMARY KEY')
    AND tc.table_schema = 'public'
ORDER BY tc.table_name, tc.constraint_type;

-- ========================================
-- 7. CHECK FOR ROW LEVEL SECURITY
-- ========================================
SELECT 
    schemaname,
    tablename,
    rowsecurity as rls_enabled
FROM pg_tables 
WHERE schemaname = 'public'
ORDER BY tablename;

-- ========================================
-- 8. CHECK INDEXES ON KEY TABLES
-- ========================================
SELECT 
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes 
WHERE schemaname = 'public'
    AND tablename IN (
        'users', 'balance_sheet_sessions', 'balance_sheet_columns', 
        'balance_sheet_data', 'mapping_rules', 'grap_chart_of_accounts'
    )
ORDER BY tablename, indexname;

-- ========================================
-- 9. RECOMMENDATIONS SUMMARY
-- ========================================
SELECT '=== RECOMMENDATIONS ===' as section;

SELECT 
    'REMOVE DUPLICATE TABLES' as action,
    'Drop trial_balance_* tables after migration' as recommendation
UNION ALL
SELECT 
    'CREATE MISSING TABLES' as action,
    'Create approval_workflows, approval_steps, user_sessions, audit_logs' as recommendation
UNION ALL
SELECT 
    'OPTIMIZE EXISTING TABLES' as action,
    'Add missing indexes, optimize queries, check RLS policies' as recommendation
UNION ALL
SELECT 
    'DATA MIGRATION' as action,
    'Migrate data from trial_balance to balance_sheet tables' as recommendation
UNION ALL
SELECT 
    'BACKUP BEFORE CHANGES' as action,
    'Export all data before making structural changes' as recommendation;
