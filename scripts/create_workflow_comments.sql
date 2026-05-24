-- Approval workflow discussion comments (run in Supabase SQL editor).
CREATE TABLE IF NOT EXISTS workflow_comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workflow_id TEXT NOT NULL,
    author_id UUID REFERENCES public.users (id) ON DELETE SET NULL,
    author_name TEXT NOT NULL DEFAULT '',
    author_role TEXT NOT NULL DEFAULT 'USER',
    text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_workflow_comments_workflow
    ON workflow_comments (workflow_id, created_at);

COMMENT ON TABLE workflow_comments IS 'Threaded comments on approval workflows (Flask service role).';

ALTER TABLE workflow_comments ENABLE ROW LEVEL SECURITY;
