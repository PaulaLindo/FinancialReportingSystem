"""Metadata helpers — legacy rejection fallbacks and clerk submission counts."""
import unittest

from utils.session_metadata_helpers import (
    clerk_submission_account_counts,
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

    def test_resolve_rejection_reason_legacy_manager(self):
        md = {'manager_rejection': {'reason': 'TB out of balance'}}
        self.assertEqual(resolve_rejection_reason(md), 'TB out of balance')

    def test_resolve_rejection_reason_from_history(self):
        md = {'rejection_history': [{'reason': 'Remap revenue lines'}]}
        self.assertEqual(resolve_rejection_reason(md), 'Remap revenue lines')

    def test_clerk_submission_account_counts_grap_mapping(self):
        md = {'grap_mapping': {'mapped_accounts': [{}, {}], 'total_accounts': 5}}
        mapped, total = clerk_submission_account_counts(md)
        self.assertEqual(mapped, 2)
        self.assertEqual(total, 5)


if __name__ == '__main__':
    unittest.main()
