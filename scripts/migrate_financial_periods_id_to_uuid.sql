-- Convert financial_periods.id from TEXT slugs (e.g. may-2026-period) to UUID.
-- Preserves each old id in period_code and metadata.legacy_id.
-- Rewrites metadata.period_id on workflow session tables.
--
-- Run BEFORE scripts/create_asset_register_tables.sql
-- Run once. Re-run after success will error (id already UUID).

CREATE TABLE IF NOT EXISTS schema_migrations (
    id TEXT PRIMARY KEY,
    description TEXT NOT NULL,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    applied_by TEXT DEFAULT current_user
);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'financial_periods'
          AND column_name = 'id'
          AND data_type = 'uuid'
    ) THEN
        RAISE EXCEPTION 'financial_periods.id is already UUID — migration already applied.';
    END IF;
END $$;

DROP TABLE IF EXISTS asset_gl_balances CASCADE;

DROP TABLE IF EXISTS _period_id_map_migration;
CREATE TABLE _period_id_map_migration (
    old_id TEXT PRIMARY KEY,
    new_id UUID NOT NULL
);

INSERT INTO _period_id_map_migration (old_id, new_id)
SELECT id, gen_random_uuid()
FROM financial_periods;

ALTER TABLE financial_periods
    ADD COLUMN IF NOT EXISTS period_code TEXT;

UPDATE financial_periods fp
SET period_code = COALESCE(NULLIF(fp.period_code, ''), fp.id);

ALTER TABLE financial_periods
    ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;

UPDATE financial_periods fp
SET metadata = COALESCE(fp.metadata, '{}'::jsonb) || jsonb_build_object('legacy_id', fp.id)
WHERE NOT (COALESCE(fp.metadata, '{}'::jsonb) ? 'legacy_id');

ALTER TABLE financial_periods
    ADD COLUMN IF NOT EXISTS id_uuid UUID;

UPDATE financial_periods fp
SET id_uuid = m.new_id
FROM _period_id_map_migration m
WHERE fp.id = m.old_id;

DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOREACH tbl IN ARRAY ARRAY[
        'balance_sheet_sessions',
        'income_statement_sessions',
        'budget_report_sessions'
    ]
    LOOP
        IF EXISTS (
            SELECT 1 FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = tbl
        ) THEN
            EXECUTE format(
                $sql$
                UPDATE %I bs
                SET metadata = jsonb_set(
                    COALESCE(bs.metadata, '{}'::jsonb),
                    '{period_id}',
                    to_jsonb(m.new_id::text),
                    true
                )
                FROM _period_id_map_migration m
                WHERE bs.metadata->>'period_id' = m.old_id
                $sql$,
                tbl
            );
        END IF;
    END LOOP;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = 'public' AND table_name = 'app_audit_events'
    ) THEN
        UPDATE app_audit_events ae
        SET payload = jsonb_set(
            COALESCE(ae.payload, '{}'::jsonb),
            '{period_id}',
            to_jsonb(m.new_id::text),
            true
        )
        FROM _period_id_map_migration m
        WHERE ae.payload->>'period_id' = m.old_id;
    END IF;
END $$;

ALTER TABLE financial_periods DROP CONSTRAINT IF EXISTS financial_periods_pkey;

ALTER TABLE financial_periods DROP COLUMN id;

ALTER TABLE financial_periods RENAME COLUMN id_uuid TO id;

ALTER TABLE financial_periods ALTER COLUMN id SET NOT NULL;

ALTER TABLE financial_periods ADD PRIMARY KEY (id);

CREATE UNIQUE INDEX IF NOT EXISTS idx_financial_periods_period_code
    ON financial_periods (period_code)
    WHERE period_code IS NOT NULL;

DROP TABLE _period_id_map_migration;

INSERT INTO schema_migrations (id, description)
VALUES (
    'migrate_financial_periods_id_to_uuid',
    'Convert financial_periods.id from TEXT slugs to UUID; preserve slugs in period_code'
)
ON CONFLICT (id) DO UPDATE
SET applied_at = NOW(), description = EXCLUDED.description;

-- Verify:
-- SELECT id, period_code, metadata->>'legacy_id' AS legacy_id FROM financial_periods;
