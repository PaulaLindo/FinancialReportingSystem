"""Metadata helpers — legacy rejection fallbacks and clerk submission counts."""
import unittest

from utils.session_metadata_helpers import (
    clerk_submission_account_counts,
    maybe_persist_legacy_rejection_repair,
    metadata_indicates_rejection,
    repair_legacy_rejection_metadata,
    resolve_line_item_comments,
    resolve_rejection_reason,
)


class SessionMetadataHelpersTests(unittest.TestCase):
    def test_resolve_line_item_comments_primary(self):
        md = {'line_item_comments': [{'account_code': '4015', 'comment_text': 'Fix mapping'}]}
        self.assertEqual(len(resolve_line_item_comments(md)), 1)

    def test_resolve_line_item_comments_from_rejection_history(self):
        md = {
            'line_item_comments': [],
            'rejection_history': [
                {'reason': 'old', 'line_item_comments': []},
                {
                    'reason': 'new',
                    'line_item_comments': [{'account_code': '1000', 'comment_text': 'Legacy archived'}],
                },
            ],
        }
        comments = resolve_line_item_comments(md)
        self.assertEqual(comments[0]['account_code'], '1000')

    def test_resolve_line_item_comments_from_snapshot(self):
        md = {
            'rejection_history': [
                {
                    'reason': 'snap',
                    'snapshot': {'line_item_comments': [{'account_code': '2000', 'comment_text': 'From snap'}]},
                },
            ],
        }
        self.assertEqual(resolve_line_item_comments(md)[0]['account_code'], '2000')

    def test_resolve_line_item_comments_from_top_level_rejection_snapshot(self):
        md = {
            'manager_rejection': {'reason': 'Remap liabilities'},
            'rejection_snapshot': {
                'line_item_comments': [{'account_code': '3000', 'comment_text': 'Top-level snapshot'}],
            },
        }
        comments = resolve_line_item_comments(md)
        self.assertEqual(comments[0]['account_code'], '3000')

    def test_resolve_line_item_comments_synthetic_from_rejection_reason(self):
        md = {
            'workflow_status': 'rejected_by_manager',
            'manager_rejection': {'reason': 'Account 4015 mapped incorrectly.'},
        }
        comments = resolve_line_item_comments(md)
        self.assertEqual(len(comments), 1)
        self.assertEqual(comments[0]['comment_text'], 'Account 4015 mapped incorrectly.')
        self.assertEqual(comments[0]['legacy_source'], 'rejection_reason')

    def test_resolve_rejection_reason_legacy_manager(self):
        md = {'manager_rejection': {'reason': 'TB out of balance'}}
        self.assertEqual(resolve_rejection_reason(md), 'TB out of balance')

    def test_resolve_rejection_reason_from_cfo_rejection(self):
        md = {'cfo_rejection': {'reason': 'Variance explanations missing'}}
        self.assertEqual(resolve_rejection_reason(md), 'Variance explanations missing')

    def test_resolve_rejection_reason_from_history(self):
        md = {'rejection_history': [{'reason': 'Remap revenue lines'}]}
        self.assertEqual(resolve_rejection_reason(md), 'Remap revenue lines')

    def test_repair_legacy_rejection_metadata_promotes_comments(self):
        md = {
            'workflow_status': 'rejected_by_manager',
            'manager_rejection': {'reason': 'Fix mapping', 'at': '2026-05-01T10:00:00'},
            'rejection_snapshot': {
                'line_item_comments': [{'account_code': '4015', 'comment_text': 'Wrong GRAP code'}],
            },
        }
        repaired, changed = repair_legacy_rejection_metadata(md)
        self.assertTrue(changed)
        self.assertEqual(repaired['line_item_comments'][0]['account_code'], '4015')
        self.assertEqual(repaired['rejection_reason'], 'Fix mapping')
        self.assertEqual(len(repaired['rejection_history']), 1)
        self.assertEqual(repaired['rejection_history'][0]['line_item_comments'][0]['account_code'], '4015')

    def test_maybe_persist_legacy_rejection_repair_updates_session(self):
        class FakeModel:
            def __init__(self):
                self.updated = False

            def update_session(self, session):
                self.updated = True

        session = type('S', (), {
            'metadata': {
                'workflow_status': 'rejected_by_manager',
                'manager_rejection': {'reason': 'Legacy only reason'},
            },
        })()
        model = FakeModel()
        changed = maybe_persist_legacy_rejection_repair(session, model)
        self.assertTrue(changed)
        self.assertTrue(model.updated)
        self.assertEqual(len(session.metadata['line_item_comments']), 1)

    def test_metadata_indicates_rejection(self):
        self.assertTrue(metadata_indicates_rejection({'workflow_status': 'rejected_by_cfo'}))
        self.assertFalse(metadata_indicates_rejection({'workflow_status': 'pending_review'}))

    def test_clerk_submission_account_counts_grap_mapping(self):
        md = {'grap_mapping': {'mapped_accounts': [{}, {}], 'total_accounts': 5}}
        mapped, total = clerk_submission_account_counts(md)
        self.assertEqual(mapped, 2)
        self.assertEqual(total, 5)


if __name__ == '__main__':
    unittest.main()
