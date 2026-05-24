"""Clerk correction workspace — mapped account reload and reviewer feedback."""

import unittest

from services.statement_validation_service import mapped_lines_from_metadata
from services.workflow_timeline_service import correction_workspace_payload


class MappedLinesFromMetadataTests(unittest.TestCase):
    def test_mapped_data_list_preferred(self):
        md = {
            'mapped_accounts': 9,
            'mapped_data': [
                {'account_code': '1000', 'grap_code': 'CA100', 'net_balance': 100},
            ],
        }
        lines = mapped_lines_from_metadata(md)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['account_code'], '1000')

    def test_grap_mapping_mapping_data(self):
        md = {
            'grap_mapping': {
                'mapping_data': [
                    {'account_code': '4015', 'grap_code': 'CL200', 'net_balance': 50},
                ],
            }
        }
        lines = mapped_lines_from_metadata(md)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]['grap_code'], 'CL200')

    def test_integer_mapped_accounts_count_ignored(self):
        md = {'mapped_accounts': 9}
        self.assertEqual(mapped_lines_from_metadata(md), [])


class CorrectionWorkspacePayloadTests(unittest.TestCase):
    def test_includes_line_item_comments(self):
        session = type('S', (), {
            'id': 'sess-1',
            'user_id': 'clerk-1',
            'metadata': {
                'workflow_status': 'rejected_by_manager',
                'rejection_reason': 'Not mapped correctly',
                'line_item_comments': [
                    {
                        'account_code': '4015',
                        'comment_text': 'Remap to GRAP 23 liability',
                        'author_name': 'Finance Manager',
                        'comment_type': 'mapping',
                        'urgency_level': 'high',
                    }
                ],
            },
            'filename': 'tb.xlsx',
            'original_filename': 'tb.xlsx',
        })()
        payload = correction_workspace_payload(
            session, document_type='balance_sheet', user_id='clerk-1'
        )
        self.assertEqual(len(payload['line_item_comments']), 1)
        self.assertEqual(payload['line_item_comments'][0]['account_code'], '4015')
        self.assertTrue(payload['is_correction_mode'])


if __name__ == '__main__':
    unittest.main()
