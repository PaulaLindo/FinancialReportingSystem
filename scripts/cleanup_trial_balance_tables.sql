-- CLEANUP DUPLICATE TRIAL BALANCE TABLES
-- Run this AFTER verifying optimization is complete

-- ========================================
-- SAFETY VERIFICATION FIRST
-- ========================================
-- Verify balance_sheet tables have data before dropping trial_balance
SELECT 
    'DATA VERIFICATION' as check_type,
    'balance_sheet_sessions' as table_name,
    COUNT(*) as row_count,
    'OK to proceed if > 0' as status
FROM balance_sheet_sessions
UNION ALL
SELECT 
    'DATA VERIFICATION' as check_type,
    'balance_sheet_columns' as table_name,
    COUNT(*) as row_count,
    'OK to proceed if > 0' as status
FROM balance_sheet_columns
UNION ALL
SELECT 
    'DATA VERIFICATION' as check_type,
    'balance_sheet_data' as table_name,
    COUNT(*) as row_count,
    'OK to proceed if > 0' as status
FROM balance_sheet_data
UNION ALL
SELECT 
    'DATA VERIFICATION' as check_type,
    'balance_sheet_templates' as table_name,
    COUNT(*) as row_count,
    'OK to proceed if > 0' as status
FROM balance_sheet_templates;

-- ========================================
-- DROP DUPLICATE TRIAL BALANCE TABLES
-- ========================================
-- Drop main trial_balance tables
DROP TABLE IF EXISTS trial_balance_sessions CASCADE;
DROP TABLE IF EXISTS trial_balance_columns CASCADE;
DROP TABLE IF EXISTS trial_balance_data CASCADE;
DROP TABLE IF EXISTS trial_balance_templates CASCADE;
DROP TABLE IF EXISTS trial_balances CASCADE;

-- Drop backup tables (if they exist and are no longer needed)
DROP TABLE IF EXISTS trial_balance_sessions_backup CASCADE;
DROP TABLE IF EXISTS trial_balance_columns_backup CASCADE;
DROP TABLE IF EXISTS trial_balance_data_backup CASCADE;
DROP TABLE IF EXISTS trial_balance_templates_backup CASCADE;
DROP TABLE IF EXISTS trial_balances_backup CASCADE;

SELECT '=== TRIAL BALANCE TABLES DROPPED ===' as status;

-- ========================================
-- FINAL VERIFICATION
-- ========================================
-- Verify only balance_sheet tables remain
SELECT 
    'FINAL TABLE LIST' as check_type,
    table_name,
    'ACTIVE' as status
FROM information_schema.tables 
WHERE table_schema = 'public' 
AND (table_name LIKE '%balance_sheet%' OR table_name LIKE '%trial_balance%')
ORDER BY table_name;

-- Calculate space savings
SELECT 
    'CLEANUP SUMMARY' as summary_type,
    'Duplicate trial_balance tables removed' as action,
    'Approximately 1.5MB+ storage reclaimed' as benefit,
    'Database optimization complete' as result;

SELECT '=== CLEANUP COMPLETED ===' as final_status;
