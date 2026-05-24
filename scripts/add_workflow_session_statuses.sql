-- Extend balance_sheet_sessions.status CHECK for clerk → manager workflow.
-- Run in Supabase SQL editor if submit-for-review fails on status constraint.

ALTER TABLE balance_sheet_sessions
  DROP CONSTRAINT IF EXISTS balance_sheet_sessions_status_check;

ALTER TABLE balance_sheet_sessions
  ADD CONSTRAINT balance_sheet_sessions_status_check
  CHECK (status IN (
    'uploaded',
    'processing',
    'mapped',
    'validated',
    'approved',
    'rejected',
    'archived',
    'pending_review',
    'pending_cfo',
    'approved_by_manager',
    'rejected_by_manager',
    'submitted',
    'resubmitted'
  ));
