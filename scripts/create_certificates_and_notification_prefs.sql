-- Certificates registry + notification preferences (run after users table exists).

CREATE TABLE IF NOT EXISTS certificates_registry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sequence_number INTEGER NOT NULL,
    certificate_id TEXT NOT NULL UNIQUE,
    session_id TEXT NOT NULL,
    document_type TEXT NOT NULL,
    issued_by UUID REFERENCES public.users (id) ON DELETE SET NULL,
    signature_hash TEXT NOT NULL,
    file_path TEXT NOT NULL,
    issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_certificates_session ON certificates_registry (session_id);
CREATE INDEX IF NOT EXISTS idx_certificates_issued ON certificates_registry (issued_at DESC);

CREATE TABLE IF NOT EXISTS notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL UNIQUE REFERENCES public.users (id) ON DELETE CASCADE,
    email_on_submission BOOLEAN NOT NULL DEFAULT TRUE,
    email_on_approval BOOLEAN NOT NULL DEFAULT TRUE,
    email_on_rejection BOOLEAN NOT NULL DEFAULT TRUE,
    email_on_comment BOOLEAN NOT NULL DEFAULT TRUE,
    email_on_sla_warning BOOLEAN NOT NULL DEFAULT TRUE,
    in_app_notifications BOOLEAN NOT NULL DEFAULT TRUE,
    digest_frequency TEXT NOT NULL DEFAULT 'immediate',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notification_prefs_user ON notification_preferences (user_id);

ALTER TABLE certificates_registry ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification_preferences ENABLE ROW LEVEL SECURITY;
