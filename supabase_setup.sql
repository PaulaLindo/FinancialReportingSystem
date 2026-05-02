-- SADPMR Financial Reporting System - Supabase Setup
-- Run this in your Supabase SQL Editor

-- 1. Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Create trial_balances table
CREATE TABLE trial_balances (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    public_url TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status TEXT DEFAULT 'uploaded'
);

-- 3. Create financial_results table
CREATE TABLE financial_results (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    trial_balance_id UUID REFERENCES trial_balances(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    results JSONB NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status TEXT DEFAULT 'completed'
);

-- 4. Create pdf_reports table
CREATE TABLE pdf_reports (
    id UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    results_id UUID REFERENCES financial_results(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    public_url TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    status TEXT DEFAULT 'completed'
);

-- 5. Create indexes for better performance
CREATE INDEX idx_trial_balances_user_id ON trial_balances(user_id);
CREATE INDEX idx_financial_results_user_id ON financial_results(user_id);
CREATE INDEX idx_pdf_reports_user_id ON pdf_reports(user_id);
CREATE INDEX idx_trial_balances_uploaded_at ON trial_balances(uploaded_at DESC);
CREATE INDEX idx_financial_results_generated_at ON financial_results(generated_at DESC);

-- 6. Set up Row Level Security (RLS)
ALTER TABLE trial_balances ENABLE ROW LEVEL SECURITY;
ALTER TABLE financial_results ENABLE ROW LEVEL SECURITY;
ALTER TABLE pdf_reports ENABLE ROW LEVEL SECURITY;

-- 7. Create RLS policies (simple version for demo)
CREATE POLICY "Enable read access for all users" ON trial_balances
    FOR SELECT USING (true);

CREATE POLICY "Enable insert for all users" ON trial_balances
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Enable update for all users" ON trial_balances
    FOR UPDATE USING (true);

CREATE POLICY "Enable delete for all users" ON trial_balances
    FOR DELETE USING (true);

-- Similar policies for financial_results
CREATE POLICY "Enable read access for all users" ON financial_results
    FOR SELECT USING (true);

CREATE POLICY "Enable insert for all users" ON financial_results
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Enable update for all users" ON financial_results
    FOR UPDATE USING (true);

CREATE POLICY "Enable delete for all users" ON financial_results
    FOR DELETE USING (true);

-- Similar policies for pdf_reports
CREATE POLICY "Enable read access for all users" ON pdf_reports
    FOR SELECT USING (true);

CREATE POLICY "Enable insert for all users" ON pdf_reports
    FOR INSERT WITH CHECK (true);

CREATE POLICY "Enable update for all users" ON pdf_reports
    FOR UPDATE USING (true);

CREATE POLICY "Enable delete for all users" ON pdf_reports
    FOR DELETE USING (true);

-- Setup complete! 
-- NEXT: Create storage bucket manually in Supabase dashboard:
-- 1. Go to Storage section in Supabase dashboard
-- 2. Click "New bucket"
-- 3. Name it: "financial-reports"
-- 4. Make it public
-- 5. Set file size limit to 10MB
