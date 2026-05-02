-- Fix RLS Policies for Balance Sheet Tables
-- Run this in Supabase SQL Editor after creating the tables

-- Enable RLS on balance sheet tables
ALTER TABLE balance_sheet_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE balance_sheet_columns ENABLE ROW LEVEL SECURITY;
ALTER TABLE balance_sheet_data ENABLE ROW LEVEL SECURITY;
ALTER TABLE mapping_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE grap_chart_of_accounts ENABLE ROW LEVEL SECURITY;

-- Policies for balance_sheet_sessions
CREATE POLICY "Users can view own balance sheet sessions" ON balance_sheet_sessions
    FOR SELECT USING (auth.uid()::text = user_id::text OR auth.uid() IS NULL);

CREATE POLICY "Users can insert own balance sheet sessions" ON balance_sheet_sessions
    FOR INSERT WITH CHECK (auth.uid()::text = user_id::text OR auth.uid() IS NULL);

CREATE POLICY "Users can update own balance sheet sessions" ON balance_sheet_sessions
    FOR UPDATE USING (auth.uid()::text = user_id::text OR auth.uid() IS NULL);

CREATE POLICY "Users can delete own balance sheet sessions" ON balance_sheet_sessions
    FOR DELETE USING (auth.uid()::text = user_id::text OR auth.uid() IS NULL);

-- Policies for balance_sheet_columns
CREATE POLICY "Users can view balance sheet columns for own sessions" ON balance_sheet_columns
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM balance_sheet_sessions 
            WHERE balance_sheet_sessions.id = balance_sheet_columns.session_id 
            AND (auth.uid()::text = balance_sheet_sessions.user_id::text OR auth.uid() IS NULL)
        )
    );

CREATE POLICY "Users can insert balance sheet columns for own sessions" ON balance_sheet_columns
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM balance_sheet_sessions 
            WHERE balance_sheet_sessions.id = balance_sheet_columns.session_id 
            AND (auth.uid()::text = balance_sheet_sessions.user_id::text OR auth.uid() IS NULL)
        )
    );

CREATE POLICY "Users can update balance sheet columns for own sessions" ON balance_sheet_columns
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM balance_sheet_sessions 
            WHERE balance_sheet_sessions.id = balance_sheet_columns.session_id 
            AND (auth.uid()::text = balance_sheet_sessions.user_id::text OR auth.uid() IS NULL)
        )
    );

CREATE POLICY "Users can delete balance sheet columns for own sessions" ON balance_sheet_columns
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM balance_sheet_sessions 
            WHERE balance_sheet_sessions.id = balance_sheet_columns.session_id 
            AND (auth.uid()::text = balance_sheet_sessions.user_id::text OR auth.uid() IS NULL)
        )
    );

-- Policies for balance_sheet_data
CREATE POLICY "Users can view balance sheet data for own sessions" ON balance_sheet_data
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM balance_sheet_sessions 
            WHERE balance_sheet_sessions.id = balance_sheet_data.session_id 
            AND (auth.uid()::text = balance_sheet_sessions.user_id::text OR auth.uid() IS NULL)
        )
    );

CREATE POLICY "Users can insert balance sheet data for own sessions" ON balance_sheet_data
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM balance_sheet_sessions 
            WHERE balance_sheet_sessions.id = balance_sheet_data.session_id 
            AND (auth.uid()::text = balance_sheet_sessions.user_id::text OR auth.uid() IS NULL)
        )
    );

CREATE POLICY "Users can update balance sheet data for own sessions" ON balance_sheet_data
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM balance_sheet_sessions 
            WHERE balance_sheet_sessions.id = balance_sheet_data.session_id 
            AND (auth.uid()::text = balance_sheet_sessions.user_id::text OR auth.uid() IS NULL)
        )
    );

CREATE POLICY "Users can delete balance sheet data for own sessions" ON balance_sheet_data
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM balance_sheet_sessions 
            WHERE balance_sheet_sessions.id = balance_sheet_data.session_id 
            AND (auth.uid()::text = balance_sheet_sessions.user_id::text OR auth.uid() IS NULL)
        )
    );

-- Policies for mapping_rules
CREATE POLICY "Users can view own mapping rules" ON mapping_rules
    FOR SELECT USING (auth.uid()::text = user_id::text OR auth.uid() IS NULL);

CREATE POLICY "Users can insert own mapping rules" ON mapping_rules
    FOR INSERT WITH CHECK (auth.uid()::text = user_id::text OR auth.uid() IS NULL);

CREATE POLICY "Users can update own mapping rules" ON mapping_rules
    FOR UPDATE USING (auth.uid()::text = user_id::text OR auth.uid() IS NULL);

CREATE POLICY "Users can delete own mapping rules" ON mapping_rules
    FOR DELETE USING (auth.uid()::text = user_id::text OR auth.uid() IS NULL);

-- Policies for grap_chart_of_accounts (public read access for authenticated users)
CREATE POLICY "Authenticated users can view GRAP chart of accounts" ON grap_chart_of_accounts
    FOR SELECT USING (auth.role() = 'authenticated');

CREATE POLICY "Users can insert GRAP chart of accounts" ON grap_chart_of_accounts
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

CREATE POLICY "Users can update GRAP chart of accounts" ON grap_chart_of_accounts
    FOR UPDATE USING (auth.role() = 'authenticated');

CREATE POLICY "Users can delete GRAP chart of accounts" ON grap_chart_of_accounts
    FOR DELETE USING (auth.role() = 'authenticated');

SELECT '=== RLS POLICIES CREATED SUCCESSFULLY ===' as status;
