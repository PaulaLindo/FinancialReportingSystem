-- Durable application audit + user inbox (run in Supabase SQL editor).
-- Flask uses the service role JWT to insert/select; RLS can stay enabled with no policies (deny direct PostgREST anon).

CREATE TABLE IF NOT EXISTS app_audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    audit_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL,
    user_id UUID REFERENCES public.users (id) ON DELETE SET NULL,
    reason TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_app_audit_events_entity
    ON app_audit_events (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_app_audit_events_user_created
    ON app_audit_events (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_app_audit_events_created
    ON app_audit_events (created_at DESC);

COMMENT ON TABLE app_audit_events IS 'Append-only financial / workflow audit trail (Flask service role).';


CREATE TABLE IF NOT EXISTS user_inbox_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES public.users (id) ON DELETE CASCADE,
    message_type TEXT NOT NULL,
    severity TEXT NOT NULL DEFAULT 'info',
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    read_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actor_id UUID REFERENCES public.users (id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_user_inbox_user_unread
    ON user_inbox_messages (user_id, read_at, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_inbox_created
    ON user_inbox_messages (created_at DESC);

COMMENT ON TABLE user_inbox_messages IS 'In-app inbox; rows created when notify target user (service role).';


ALTER TABLE app_audit_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_inbox_messages ENABLE ROW LEVEL SECURITY;
