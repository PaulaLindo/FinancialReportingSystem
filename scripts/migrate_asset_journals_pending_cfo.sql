-- Add pending_cfo status for material asset journal escalation (FM → CFO).
-- Run once in Supabase SQL editor after create_asset_register_tables.sql.

ALTER TABLE asset_journals
    DROP CONSTRAINT IF EXISTS asset_journals_status_check;

ALTER TABLE asset_journals
    ADD CONSTRAINT asset_journals_status_check CHECK (
        status IN ('pending_review', 'pending_cfo', 'approved', 'rejected')
    );

INSERT INTO schema_migrations (id, description)
VALUES (
    'migrate_asset_journals_pending_cfo',
    'Asset journal pending_cfo status for materiality escalation'
)
ON CONFLICT (id) DO UPDATE
SET applied_at = NOW(), description = EXCLUDED.description;
