-- Check existing RLS policies on financial_periods table
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE tablename = 'financial_periods';

-- Show existing policies
SELECT 
    policyname, 
    permissive, 
    roles, 
    cmd, 
    qual 
FROM pg_policies 
WHERE tablename = 'financial_periods';
