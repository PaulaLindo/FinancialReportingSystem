"""
Database Migration: Approval Workflow Comments and Audit Logging

This migration adds the necessary tables for:
1. Storing approval workflow comments
2. Comprehensive audit logging
3. Approval history tracking

To run this migration:
1. Copy the SQL statements below
2. Execute in Supabase SQL editor
3. Update config/settings.py with new table names
"""

# SQL Migration Script

MIGRATION_SQL = """
-- ============================================
-- APPROVAL WORKFLOW COMMENTS TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS approval_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID NOT NULL REFERENCES approval_workflows(id) ON DELETE CASCADE,
    author_id UUID NOT NULL,
    author_name VARCHAR(255) NOT NULL,
    author_role VARCHAR(50) NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    parent_comment_id UUID REFERENCES approval_comments(id) ON DELETE CASCADE
);

-- Index for fast lookup of comments by workflow
CREATE INDEX IF NOT EXISTS idx_approval_comments_workflow_id ON approval_comments(workflow_id);
CREATE INDEX IF NOT EXISTS idx_approval_comments_author_id ON approval_comments(author_id);
CREATE INDEX IF NOT EXISTS idx_approval_comments_created_at ON approval_comments(created_at DESC);

-- Enable row-level security
ALTER TABLE approval_comments ENABLE ROW LEVEL SECURITY;

-- ============================================
-- APPROVAL AUDIT LOG TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS approval_audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID NOT NULL REFERENCES approval_workflows(id) ON DELETE CASCADE,
    step_id UUID REFERENCES approval_steps(id) ON DELETE SET NULL,
    action VARCHAR(50) NOT NULL,
    actor_id UUID NOT NULL,
    actor_name VARCHAR(255),
    actor_role VARCHAR(50),
    previous_status VARCHAR(50),
    new_status VARCHAR(50),
    notes TEXT,
    metadata JSONB,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices for audit log queries
CREATE INDEX IF NOT EXISTS idx_audit_workflow_id ON approval_audit_logs(workflow_id);
CREATE INDEX IF NOT EXISTS idx_audit_actor_id ON approval_audit_logs(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON approval_audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_created_at ON approval_audit_logs(created_at DESC);

-- Enable row-level security
ALTER TABLE approval_audit_logs ENABLE ROW LEVEL SECURITY;

-- ============================================
-- APPROVAL HISTORY TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS approval_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID NOT NULL REFERENCES approval_workflows(id) ON DELETE CASCADE,
    step_order INT NOT NULL,
    approver_id UUID,
    approver_name VARCHAR(255),
    approver_role VARCHAR(50),
    action VARCHAR(50) NOT NULL, -- 'approved', 'rejected', 'delegated', 'escalated'
    status VARCHAR(50) NOT NULL,
    notes TEXT,
    delegation_from_id UUID,
    delegation_from_name VARCHAR(255),
    sla_deadline TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices for history queries
CREATE INDEX IF NOT EXISTS idx_history_workflow_id ON approval_history(workflow_id);
CREATE INDEX IF NOT EXISTS idx_history_approver_id ON approval_history(approver_id);
CREATE INDEX IF NOT EXISTS idx_history_action ON approval_history(action);

-- Enable row-level security
ALTER TABLE approval_history ENABLE ROW LEVEL SECURITY;

-- ============================================
-- NOTIFICATION PREFERENCES TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS notification_preferences (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL UNIQUE,
    email_on_submission BOOLEAN DEFAULT TRUE,
    email_on_approval BOOLEAN DEFAULT TRUE,
    email_on_rejection BOOLEAN DEFAULT TRUE,
    email_on_comment BOOLEAN DEFAULT TRUE,
    email_on_sla_warning BOOLEAN DEFAULT TRUE,
    in_app_notifications BOOLEAN DEFAULT TRUE,
    digest_frequency VARCHAR(20) DEFAULT 'immediate', -- 'immediate', 'daily', 'weekly'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for preferences lookup
CREATE INDEX IF NOT EXISTS idx_notification_prefs_user_id ON notification_preferences(user_id);

-- Enable row-level security
ALTER TABLE notification_preferences ENABLE ROW LEVEL SECURITY;

-- ============================================
-- APPROVAL DELEGATION TABLE
-- ============================================

CREATE TABLE IF NOT EXISTS approval_delegations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID NOT NULL REFERENCES approval_workflows(id) ON DELETE CASCADE,
    step_id UUID NOT NULL REFERENCES approval_steps(id) ON DELETE CASCADE,
    delegated_from_id UUID NOT NULL,
    delegated_to_id UUID NOT NULL,
    delegated_from_name VARCHAR(255),
    delegated_to_name VARCHAR(255),
    delegated_from_role VARCHAR(50),
    delegated_to_role VARCHAR(50),
    reason TEXT,
    delegation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expiry_date TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    revoked_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indices for delegation queries
CREATE INDEX IF NOT EXISTS idx_delegations_workflow_id ON approval_delegations(workflow_id);
CREATE INDEX IF NOT EXISTS idx_delegations_from_id ON approval_delegations(delegated_from_id);
CREATE INDEX IF NOT EXISTS idx_delegations_to_id ON approval_delegations(delegated_to_id);
CREATE INDEX IF NOT EXISTS idx_delegations_active ON approval_delegations(is_active);

-- Enable row-level security
ALTER TABLE approval_delegations ENABLE ROW LEVEL SECURITY;

-- ============================================
-- ROW-LEVEL SECURITY POLICIES
-- ============================================

-- Approval Comments RLS
CREATE POLICY approval_comments_select ON approval_comments
    FOR SELECT
    USING (
        -- Users can see comments on workflows they have access to
        workflow_id IN (
            SELECT id FROM approval_workflows WHERE 
            creator_id = auth.uid() OR 
            id IN (SELECT workflow_id FROM approval_steps WHERE approver_id = auth.uid())
        )
    );

CREATE POLICY approval_comments_insert ON approval_comments
    FOR INSERT
    WITH CHECK (
        author_id = auth.uid() AND
        workflow_id IN (
            SELECT id FROM approval_workflows WHERE 
            creator_id = auth.uid() OR 
            id IN (SELECT workflow_id FROM approval_steps WHERE approver_id = auth.uid())
        )
    );

CREATE POLICY approval_comments_delete ON approval_comments
    FOR DELETE
    USING (author_id = auth.uid());

-- Audit Logs RLS (read-only for users)
CREATE POLICY approval_audit_logs_select ON approval_audit_logs
    FOR SELECT
    USING (
        workflow_id IN (
            SELECT id FROM approval_workflows WHERE 
            creator_id = auth.uid() OR 
            id IN (SELECT workflow_id FROM approval_steps WHERE approver_id = auth.uid())
        )
    );

-- History RLS (read-only for users)
CREATE POLICY approval_history_select ON approval_history
    FOR SELECT
    USING (
        workflow_id IN (
            SELECT id FROM approval_workflows WHERE 
            creator_id = auth.uid() OR 
            id IN (SELECT workflow_id FROM approval_steps WHERE approver_id = auth.uid())
        )
    );

-- Notification Preferences RLS
CREATE POLICY notification_preferences_select ON notification_preferences
    FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY notification_preferences_update ON notification_preferences
    FOR UPDATE
    USING (user_id = auth.uid());

-- ============================================
-- TRIGGERS AND FUNCTIONS
-- ============================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for approval_comments
CREATE TRIGGER approval_comments_updated_at
    BEFORE UPDATE ON approval_comments
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Trigger for notification_preferences
CREATE TRIGGER notification_preferences_updated_at
    BEFORE UPDATE ON notification_preferences
    FOR EACH ROW
    EXECUTE FUNCTION update_timestamp();

-- Function to log approval actions
CREATE OR REPLACE FUNCTION log_approval_action()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO approval_audit_logs (
        workflow_id,
        step_id,
        action,
        actor_id,
        previous_status,
        new_status,
        metadata,
        created_at
    ) VALUES (
        NEW.workflow_id,
        NEW.id,
        'step_' || CASE 
            WHEN NEW.status = 'approved' THEN 'approved'
            WHEN NEW.status = 'rejected' THEN 'rejected'
            ELSE 'updated'
        END,
        NEW.approver_id,
        OLD.status,
        NEW.status,
        jsonb_build_object(
            'approval_notes', NEW.approval_notes,
            'rejection_reason', NEW.rejection_reason
        ),
        CURRENT_TIMESTAMP
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for approval_steps (logs status changes)
CREATE TRIGGER approval_steps_audit_trigger
    AFTER UPDATE ON approval_steps
    FOR EACH ROW
    WHEN (OLD.status IS DISTINCT FROM NEW.status)
    EXECUTE FUNCTION log_approval_action();

-- ============================================
-- VIEWS
-- ============================================

-- View for approval workflow statistics
CREATE OR REPLACE VIEW approval_workflow_stats AS
SELECT 
    w.id,
    w.document_type,
    w.status,
    COUNT(*) as count,
    AVG(EXTRACT(EPOCH FROM (w.completed_at - w.created_at))/3600) as avg_hours_to_complete
FROM approval_workflows w
GROUP BY w.id, w.document_type, w.status;

-- View for approval performance by role
CREATE OR REPLACE VIEW approval_performance_by_role AS
SELECT 
    h.approver_role,
    COUNT(*) as total_approvals,
    SUM(CASE WHEN h.action = 'approved' THEN 1 ELSE 0 END) as approved,
    SUM(CASE WHEN h.action = 'rejected' THEN 1 ELSE 0 END) as rejected,
    AVG(EXTRACT(EPOCH FROM (h.completed_at - h.created_at))/3600) as avg_hours_to_approve
FROM approval_history h
GROUP BY h.approver_role;

-- View for pending approvals by user
CREATE OR REPLACE VIEW pending_approvals_by_user AS
SELECT 
    s.approver_id,
    COUNT(*) as pending_count,
    COUNT(CASE WHEN s.created_at < CURRENT_TIMESTAMP - INTERVAL '24 hours' THEN 1 END) as overdue_count
FROM approval_steps s
WHERE s.status = 'pending'
GROUP BY s.approver_id;

-- ============================================
-- GRANTS AND PERMISSIONS
-- ============================================

-- Grant appropriate permissions to authenticated users
GRANT SELECT ON approval_comments TO authenticated;
GRANT INSERT ON approval_comments TO authenticated;
GRANT DELETE ON approval_comments TO authenticated;
GRANT SELECT ON approval_audit_logs TO authenticated;
GRANT SELECT ON approval_history TO authenticated;
GRANT SELECT, UPDATE ON notification_preferences TO authenticated;
GRANT SELECT ON approval_workflow_stats TO authenticated;
GRANT SELECT ON approval_performance_by_role TO authenticated;
GRANT SELECT ON pending_approvals_by_user TO authenticated;

-- Grant sequence permissions
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO authenticated;
"""

# Python migration helper class

from datetime import datetime
from typing import List, Dict, Optional

class MigrationHelper:
    """Helper class for managing database migrations"""
    
    def __init__(self, supabase_client):
        self.client = supabase_client
        self.migration_log = []
    
    def check_table_exists(self, table_name: str) -> bool:
        """Check if table exists in database"""
        try:
            result = self.client.table(table_name).select('*').limit(1).execute()
            return True
        except Exception as e:
            if 'not found' in str(e).lower():
                return False
            raise
    
    def create_comment(self, workflow_id: str, author_id: str, author_name: str, 
                      author_role: str, text: str) -> Optional[str]:
        """Create a new approval comment"""
        try:
            result = self.client.table('approval_comments').insert({
                'workflow_id': workflow_id,
                'author_id': author_id,
                'author_name': author_name,
                'author_role': author_role,
                'text': text,
                'created_at': datetime.now().isoformat()
            }).execute()
            
            if result.data:
                return result.data[0]['id']
            return None
        except Exception as e:
            self.migration_log.append(f"Error creating comment: {str(e)}")
            return None
    
    def log_audit_action(self, workflow_id: str, action: str, actor_id: str,
                        actor_name: str, actor_role: str, notes: str = None) -> bool:
        """Log an approval action to audit trail"""
        try:
            self.client.table('approval_audit_logs').insert({
                'workflow_id': workflow_id,
                'action': action,
                'actor_id': actor_id,
                'actor_name': actor_name,
                'actor_role': actor_role,
                'notes': notes,
                'created_at': datetime.now().isoformat()
            }).execute()
            return True
        except Exception as e:
            self.migration_log.append(f"Error logging audit: {str(e)}")
            return False
    
    def create_delegation(self, workflow_id: str, step_id: str, from_id: str,
                         to_id: str, from_name: str, to_name: str,
                         from_role: str, to_role: str, reason: str = None) -> Optional[str]:
        """Create an approval delegation"""
        try:
            result = self.client.table('approval_delegations').insert({
                'workflow_id': workflow_id,
                'step_id': step_id,
                'delegated_from_id': from_id,
                'delegated_to_id': to_id,
                'delegated_from_name': from_name,
                'delegated_to_name': to_name,
                'delegated_from_role': from_role,
                'delegated_to_role': to_role,
                'reason': reason,
                'is_active': True
            }).execute()
            
            if result.data:
                return result.data[0]['id']
            return None
        except Exception as e:
            self.migration_log.append(f"Error creating delegation: {str(e)}")
            return None
    
    def get_migration_status(self) -> Dict:
        """Get status of all database tables"""
        tables = [
            'approval_comments',
            'approval_audit_logs',
            'approval_history',
            'notification_preferences',
            'approval_delegations'
        ]
        
        status = {}
        for table in tables:
            status[table] = self.check_table_exists(table)
        
        return status

# Example usage in Flask app
def apply_database_migrations(app):
    """Apply all database migrations on app startup"""
    try:
        from config.settings import supabase
        
        helper = MigrationHelper(supabase)
        status = helper.get_migration_status()
        
        all_ready = all(status.values())
        if not all_ready:
            app.logger.warning("Not all approval workflow tables exist. Please run migration SQL manually.")
        else:
            app.logger.info("All approval workflow tables ready.")
        
        return status
    except Exception as e:
        app.logger.error(f"Error checking database migrations: {str(e)}")
        return {}

if __name__ == "__main__":
    print("=" * 70)
    print("APPROVAL WORKFLOW DATABASE MIGRATION")
    print("=" * 70)
    print("\nTo apply this migration:")
    print("1. Go to Supabase SQL Editor")
    print("2. Create a new query")
    print("3. Paste the SQL statements below")
    print("4. Execute the query")
    print("\n" + "=" * 70)
    print("SQL MIGRATION SCRIPT:")
    print("=" * 70)
    print(MIGRATION_SQL)
