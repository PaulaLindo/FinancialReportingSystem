# Database Migration: Trial Balance to Balance Sheet

## Overview
This migration will convert all database tables and data from `trial_balance` terminology to `balance_sheet` terminology to match the codebase refactoring.

## Current Database State
Based on the database check, we currently have:

### 🔴 Tables that need migration:
- `trial_balance_sessions` (22 rows)
- `trial_balance_columns` (88 rows) 
- `trial_balance_data` (616 rows)

### 🟢 Tables that will be created:
- `balance_sheet_sessions`
- `balance_sheet_columns`
- `balance_sheet_data`

### ⚪ Other tables (unchanged):
- `users` (13 rows)
- `grap_chart_of_accounts` (0 rows)
- `mapping_rules` (0 rows)

## Migration Options

### Option 1: SQL Script (Recommended)
Run the SQL script directly in Supabase SQL Editor:

1. **Open Supabase Dashboard**
2. **Go to SQL Editor**
3. **Copy and paste the contents of**: `scripts/migrate_trial_balance_to_balance_sheet.sql`
4. **Run the script**

**Advantages:**
- Direct control over the process
- Can review each step
- Easy to rollback if needed
- No Python dependencies

### Option 2: Python Script
Run the Python migration script:

```bash
python scripts/migrate_trial_balance_to_balance_sheet.py
```

**Advantages:**
- Interactive prompts
- Built-in verification
- Error handling
- Progress reporting

## Migration Steps

### Phase 1: Preparation
1. ✅ **Code refactoring completed** - All Python, JS, and HTML files updated
2. ✅ **Database check completed** - Current state identified
3. ⚠️ **Backup database** - Create a backup before proceeding

### Phase 2: Database Migration
1. **Create new balance_sheet tables** with identical structure
2. **Migrate data** from trial_balance to balance_sheet tables
3. **Create indexes** for performance
4. **Set up Row Level Security (RLS)** policies
5. **Create database functions** (get_balance_sheet_summary)
6. **Grant permissions**

### Phase 3: Verification
1. **Check row counts** match between old and new tables
2. **Test application** with new tables
3. **Verify all functionality** works correctly

### Phase 4: Cleanup (Optional - After Testing)
1. **Drop old trial_balance tables** (only after thorough testing)
2. **Clean up any remaining references**

## Safety Precautions

### ⚠️ IMPORTANT:
1. **Always backup your database** before making structural changes
2. **Test in a development environment** first if possible
3. **Have a rollback plan** ready
4. **Run during maintenance window** to minimize user impact

### 🛡️ Backup Commands:
```sql
-- Create backup tables (included in migration script)
CREATE TABLE trial_balance_sessions_backup AS SELECT * FROM trial_balance_sessions;
CREATE TABLE trial_balance_columns_backup AS SELECT * FROM trial_balance_columns;
CREATE TABLE trial_balance_data_backup AS SELECT * FROM trial_balance_data;
```

## Post-Migration Testing

### Test Checklist:
- [ ] User can upload new balance sheets
- [ ] Existing data displays correctly
- [ ] GRAP mapping works
- [ ] Financial statements generate
- [ ] User permissions work correctly
- [ ] All API endpoints function
- [ ] Frontend displays data properly

### Rollback Plan (if needed):
```sql
-- Restore from backup tables
TRUNCATE TABLE trial_balance_sessions;
INSERT INTO trial_balance_sessions SELECT * FROM trial_balance_sessions_backup;

TRUNCATE TABLE trial_balance_columns;
INSERT INTO trial_balance_columns SELECT * FROM trial_balance_columns_backup;

TRUNCATE TABLE trial_balance_data;
INSERT INTO trial_balance_data SELECT * FROM trial_balance_data_backup;
```

## Files Created

### Scripts:
- `scripts/check_supabase_tables.py` - Check current database state
- `scripts/check_db_with_available_keys.py` - Simple database checker
- `scripts/migrate_trial_balance_to_balance_sheet.py` - Python migration script
- `scripts/migrate_trial_balance_to_balance_sheet.sql` - SQL migration script
- `scripts/README_MIGRATION.md` - This documentation

## Troubleshooting

### Common Issues:

#### 1. Permission Denied Errors
**Cause:** RLS policies blocking access
**Solution:** Check user roles and permissions in Supabase

#### 2. Table Already Exists
**Cause:** Migration run multiple times
**Solution:** Use `IF NOT EXISTS` clauses (included in script)

#### 3. Foreign Key Constraint Errors
**Cause:** Data integrity issues
**Solution:** Ensure data is migrated in correct order (sessions → columns → data)

#### 4. Connection Issues
**Cause:** Environment variables not set
**Solution:** Check `.env` file has correct Supabase credentials

## Support

If you encounter issues:
1. Check the error messages carefully
2. Verify your Supabase credentials
3. Ensure you have sufficient permissions
4. Review the SQL script for any syntax issues
5. Test with smaller data subsets first

## Next Steps After Migration

1. **Test thoroughly** with the new tables
2. **Monitor for any issues** in production
3. **Update documentation** if needed
4. **Train users** on any changes (though terminology should be consistent)
5. **Consider archiving** old tables instead of dropping them initially

---

**Migration Status:** 🟡 Ready to Execute  
**Risk Level:** 🟡 Medium (data migration requires caution)  
**Estimated Time:** 15-30 minutes  
**Required Permissions:** Database admin or service role key
