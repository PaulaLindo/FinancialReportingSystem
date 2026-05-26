"""Period management — timezone-safe date handling."""
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from models.period_models import FinancialPeriod, PeriodStatus
from services.period_management_service import PeriodManagementService


class PeriodDateParsingTests(unittest.TestCase):
    def setUp(self):
        self.svc = PeriodManagementService()

    def test_parse_date_only_is_utc_aware(self):
        parsed = self.svc._parse_date('2026-04-01')
        self.assertEqual(parsed.tzinfo, timezone.utc)
        self.assertEqual(parsed.date().isoformat(), '2026-04-01')

    def test_parse_iso_with_z_is_utc_aware(self):
        parsed = self.svc._parse_date('2026-04-01T00:00:00+00:00')
        self.assertEqual(parsed.tzinfo, timezone.utc)

    def test_utc_now_compare_with_parsed_dates_does_not_raise(self):
        start = self.svc._parse_date('2026-04-01')
        end = self.svc._end_of_day_utc(self.svc._parse_date('2026-04-30'))
        now = self.svc._utc_now()
        self.assertIsInstance(start <= now <= end, bool)


class OpenPeriodForUploadsTests(unittest.TestCase):
    def setUp(self):
        self.svc = PeriodManagementService()
        self.svc.model = MagicMock()

    def test_open_period_allows_outside_current_date_range(self):
        period = FinancialPeriod(
            id='p-april',
            name='April 2026',
            description='',
            start_date='2026-04-01T00:00:00+00:00',
            end_date='2026-04-30T00:00:00+00:00',
            due_date='2026-05-07',
            status=PeriodStatus.CLOSED.value,
            urgency='normal',
            required_uploads=3,
            uploaded_count=0,
            created_by='admin',
            created_at='2026-01-01',
            updated_at='2026-01-01',
            metadata={},
            is_locked=False,
        )
        opened = FinancialPeriod(
            id='p-april',
            name='April 2026',
            description='',
            start_date='2026-04-01T00:00:00+00:00',
            end_date='2026-04-30T00:00:00+00:00',
            due_date='2026-05-07',
            status=PeriodStatus.OPEN.value,
            urgency='normal',
            required_uploads=3,
            uploaded_count=0,
            created_by='admin',
            created_at='2026-01-01',
            updated_at='2026-01-01',
            metadata={},
            is_locked=False,
        )
        self.svc.model.get_period.return_value = period
        self.svc.model.update_period.return_value = opened

        result = self.svc.open_period_for_uploads('p-april')

        self.assertEqual(result.status, PeriodStatus.OPEN.value)
        self.svc.model.update_period.assert_called_once()


class RecordUploadForPeriodTests(unittest.TestCase):
    def setUp(self):
        self.svc = PeriodManagementService()
        self.svc.model = MagicMock()

    def test_record_upload_reconciles_from_sessions(self):
        synced = FinancialPeriod(
            id='p-april',
            name='April 2026',
            description='',
            start_date='2026-04-01T00:00:00+00:00',
            end_date='2026-04-30T00:00:00+00:00',
            due_date='2026-05-07',
            status=PeriodStatus.OPEN.value,
            urgency='normal',
            required_uploads=3,
            uploaded_count=1,
            created_by='admin',
            created_at='2026-01-01',
            updated_at='2026-01-01',
            metadata={'uploaded_document_types': ['income_statement']},
            is_locked=False,
        )
        self.svc.validate_upload_for_period = MagicMock(return_value=(True, 'Upload allowed'))
        self.svc.sync_period_upload_stats = MagicMock(return_value=synced)

        result = self.svc.record_upload_for_period('p-april', {
            'document_type': 'income_statement',
            'session_id': 'sess-1',
        })

        self.assertEqual(result.uploaded_count, 1)
        self.svc.sync_period_upload_stats.assert_called_once_with('p-april')


class CountPeriodSubmissionsTests(unittest.TestCase):
    def setUp(self):
        self.svc = PeriodManagementService()
        self.svc.model = MagicMock()

    def test_counts_unique_submitted_document_types(self):
        client = MagicMock()
        self.svc.model.client = client

        def table_side_effect(name):
            table = MagicMock()
            if name == 'balance_sheet_sessions':
                table.select.return_value.filter.return_value.execute.return_value = MagicMock(data=[])
            elif name == 'income_statement_sessions':
                table.select.return_value.filter.return_value.execute.return_value = MagicMock(data=[{
                    'id': 'sess-is',
                    'status': 'pending_review',
                    'metadata': {'period_id': 'p-april', 'workflow_status': 'pending_review'},
                    'updated_at': '2026-05-24T10:00:00',
                }])
            else:
                table.select.return_value.filter.return_value.execute.return_value = MagicMock(data=[])
            return table

        client.table.side_effect = table_side_effect

        stats = self.svc.count_period_submissions('p-april')

        self.assertEqual(stats['submitted_count'], 1)
        self.assertEqual(stats['document_types'], ['income_statement'])

    def test_completion_percentage_caps_at_100(self):
        period = FinancialPeriod(
            id='p-april',
            name='April 2026',
            description='',
            start_date='2026-04-01T00:00:00+00:00',
            end_date='2026-04-30T00:00:00+00:00',
            due_date='2026-05-07',
            status=PeriodStatus.OPEN.value,
            urgency='normal',
            required_uploads=1,
            uploaded_count=2,
            created_by='admin',
            created_at='2026-01-01',
            updated_at='2026-01-01',
            metadata={},
            is_locked=False,
        )
        self.assertEqual(period.completion_percentage, 100.0)


class CatchUpUploadTests(unittest.TestCase):
    def setUp(self):
        self.svc = PeriodManagementService()
        self.svc.model = MagicMock()

    def test_open_april_period_allows_upload_in_may(self):
        april = FinancialPeriod(
            id='p-april',
            name='April 2026 Financial Period',
            description='',
            start_date='2026-04-01T00:00:00+00:00',
            end_date='2026-04-30T23:59:59+00:00',
            due_date='2026-05-08T00:00:00+00:00',
            status=PeriodStatus.OPEN.value,
            urgency='normal',
            required_uploads=3,
            uploaded_count=0,
            created_by='admin',
            created_at='2026-01-01',
            updated_at='2026-01-01',
            metadata={},
            is_locked=False,
        )
        self.svc.model.get_period.return_value = april
        self.svc.count_period_submissions = MagicMock(return_value={
            'submitted_count': 0,
            'document_types': [],
            'session_ids': [],
            'last_upload': None,
        })

        allowed, message = self.svc.validate_upload_for_period('p-april')

        self.assertTrue(allowed, message)
        self.assertEqual(message, 'Upload allowed')


class DedupeOpenPeriodsTests(unittest.TestCase):
    def setUp(self):
        self.svc = PeriodManagementService()

    def _period(self, pid, name, uploaded=0, updated='2026-01-02'):
        return FinancialPeriod(
            id=pid,
            name=name,
            description='',
            start_date='2026-04-01T00:00:00+00:00',
            end_date='2026-04-30T00:00:00+00:00',
            due_date='2026-05-07',
            status=PeriodStatus.OPEN.value,
            urgency='normal',
            required_uploads=3,
            uploaded_count=uploaded,
            created_by='admin',
            created_at='2026-01-01',
            updated_at=updated,
            metadata={'uploaded_document_types': ['income_statement']} if uploaded else {},
            is_locked=False,
        )

    def test_dedupe_keeps_period_with_submissions(self):
        periods = [
            self._period('dup-empty', 'April 2026 Financial Period', uploaded=0),
            self._period('dup-active', 'April 2026 Financial Period', uploaded=1, updated='2026-05-20'),
        ]
        deduped = self.svc.dedupe_open_periods(periods)
        self.assertEqual(len(deduped), 1)
        self.assertEqual(deduped[0].id, 'dup-active')

    def test_create_rejects_conflicting_open_period(self):
        self.svc.model = MagicMock()
        existing = self._period('existing', 'April 2026 Financial Period')
        self.svc.model.get_all_periods.return_value = [existing]
        with self.assertRaises(Exception) as ctx:
            self.svc.create_financial_period({
                'name': 'April 2026 Financial Period',
                'start_date': '2026-04-01',
                'end_date': '2026-04-30',
                'due_date': '2026-05-07',
                'required_uploads': 3,
            }, 'admin-1')
        self.assertIn('already exists', str(ctx.exception).lower())


class RequiredUploadsValidationTests(unittest.TestCase):
    def setUp(self):
        self.svc = PeriodManagementService()

    def test_accepts_standard_required_uploads(self):
        self.assertEqual(self.svc.validate_required_uploads_count(3), 3)

    def test_rejects_non_standard_required_uploads(self):
        with self.assertRaises(ValueError) as ctx:
            self.svc.validate_required_uploads_count(2)
        self.assertIn('3', str(ctx.exception))
        self.assertIn('balance sheet', str(ctx.exception).lower())


class FixAndDeletePeriodTests(unittest.TestCase):
    def setUp(self):
        self.svc = PeriodManagementService()
        self.svc.model = MagicMock()

    def test_fix_period_required_uploads_updates_count(self):
        period = FinancialPeriod(
            id='p-april',
            name='April 2026',
            description='',
            start_date='2026-04-01T00:00:00+00:00',
            end_date='2026-04-30T00:00:00+00:00',
            due_date='2026-05-07',
            status=PeriodStatus.OPEN.value,
            urgency='normal',
            required_uploads=2,
            uploaded_count=1,
            created_by='admin',
            created_at='2026-01-01',
            updated_at='2026-01-01',
            metadata={},
            is_locked=False,
        )
        fixed = FinancialPeriod(
            id='p-april',
            name='April 2026',
            description='',
            start_date='2026-04-01T00:00:00+00:00',
            end_date='2026-04-30T00:00:00+00:00',
            due_date='2026-05-07',
            status=PeriodStatus.OPEN.value,
            urgency='normal',
            required_uploads=3,
            uploaded_count=1,
            created_by='admin',
            created_at='2026-01-01',
            updated_at='2026-01-01',
            metadata={'uploaded_document_types': ['income_statement']},
            is_locked=False,
        )
        self.svc.model.get_period.return_value = period
        self.svc.model.update_period.return_value = fixed
        self.svc.sync_period_upload_stats = MagicMock(return_value=fixed)

        result = self.svc.fix_period_required_uploads('p-april')

        self.assertEqual(result.required_uploads, 3)
        self.svc.model.update_period.assert_called_once()
        self.svc.sync_period_upload_stats.assert_called_once_with('p-april')

    def test_delete_period_blocked_when_submissions_exist(self):
        period = FinancialPeriod(
            id='p-april',
            name='April 2026',
            description='',
            start_date='2026-04-01T00:00:00+00:00',
            end_date='2026-04-30T00:00:00+00:00',
            due_date='2026-05-07',
            status=PeriodStatus.OPEN.value,
            urgency='normal',
            required_uploads=2,
            uploaded_count=1,
            created_by='admin',
            created_at='2026-01-01',
            updated_at='2026-01-01',
            metadata={},
            is_locked=False,
        )
        self.svc.model.get_period.return_value = period
        self.svc.count_period_submissions = MagicMock(return_value={
            'submitted_count': 1,
            'document_types': ['income_statement'],
            'session_ids': ['sess-1'],
            'last_upload': '2026-05-24T10:00:00',
        })

        with self.assertRaises(Exception) as ctx:
            self.svc.delete_financial_period('p-april')
        self.assertIn('Cannot delete', str(ctx.exception))
        self.svc.model.delete_period.assert_not_called()


class RelatedPeriodIdsTests(unittest.TestCase):
    def setUp(self):
        self.svc = PeriodManagementService()
        self.svc.model = MagicMock()

    def test_related_period_ids_includes_duplicate_rows(self):
        april_a = FinancialPeriod(
            id='april-a',
            name='April 2026 Financial Period',
            description='',
            start_date='2026-04-01T00:00:00+00:00',
            end_date='2026-04-30T00:00:00+00:00',
            due_date='2026-05-07',
            status=PeriodStatus.OPEN.value,
            urgency='normal',
            required_uploads=3,
            uploaded_count=0,
            created_by='admin',
            created_at='2026-01-01',
            updated_at='2026-01-01',
            metadata={},
            is_locked=False,
        )
        april_b = FinancialPeriod(
            id='april-b',
            name='April 2026 Financial Period',
            description='',
            start_date='2026-04-01T00:00:00+00:00',
            end_date='2026-04-30T00:00:00+00:00',
            due_date='2026-05-07',
            status=PeriodStatus.OPEN.value,
            urgency='normal',
            required_uploads=3,
            uploaded_count=0,
            created_by='admin',
            created_at='2026-01-02',
            updated_at='2026-01-02',
            metadata={},
            is_locked=False,
        )
        self.svc.model.get_period.return_value = april_a
        self.svc.model.get_all_periods.return_value = [april_a, april_b]

        ids = self.svc.related_period_ids('april-a')
        self.assertEqual(sorted(ids), ['april-a', 'april-b'])

    def test_resolve_canonical_period_id_prefers_row_with_submissions(self):
        april_a = FinancialPeriod(
            id='april-a',
            name='April 2026 Financial Period',
            description='',
            start_date='2026-04-01T00:00:00+00:00',
            end_date='2026-04-30T00:00:00+00:00',
            due_date='2026-05-07',
            status=PeriodStatus.OPEN.value,
            urgency='normal',
            required_uploads=3,
            uploaded_count=0,
            created_by='admin',
            created_at='2026-01-01',
            updated_at='2026-01-01',
            metadata={},
            is_locked=False,
        )
        april_b = FinancialPeriod(
            id='april-b',
            name='April 2026 Financial Period',
            description='',
            start_date='2026-04-01T00:00:00+00:00',
            end_date='2026-04-30T00:00:00+00:00',
            due_date='2026-05-07',
            status=PeriodStatus.OPEN.value,
            urgency='normal',
            required_uploads=3,
            uploaded_count=2,
            created_by='admin',
            created_at='2026-01-02',
            updated_at='2026-01-02',
            metadata={'uploaded_document_types': ['balance_sheet']},
            is_locked=False,
        )
        self.svc.model.get_period.return_value = april_a
        self.svc.model.get_open_periods.return_value = [april_a, april_b]

        canonical = self.svc.resolve_canonical_period_id('april-a')
        self.assertEqual(canonical, 'april-b')


class ConsolidateDuplicatePeriodsTests(unittest.TestCase):
    def setUp(self):
        self.svc = PeriodManagementService()
        self.svc.model = MagicMock()
        self.svc.model.client = MagicMock()

    def _period(self, pid, uploaded=0, locked=False):
        return FinancialPeriod(
            id=pid,
            name='May 2026 Financial Period',
            description='Monthly financial reporting for May 2026',
            start_date='2026-05-01T00:00:00+00:00',
            end_date='2026-05-31T00:00:00+00:00',
            due_date='2026-06-07',
            status=PeriodStatus.OPEN.value,
            urgency='normal',
            required_uploads=3,
            uploaded_count=uploaded,
            created_by='admin',
            created_at='2026-01-01',
            updated_at='2026-01-02',
            metadata={'uploaded_document_types': ['income_statement']} if uploaded else {},
            is_locked=locked,
        )

    def test_consolidate_removes_empty_duplicate_row(self):
        canonical = self._period('may-a', uploaded=1)
        duplicate = self._period('may-b', uploaded=0)
        self.svc.model.get_all_periods.return_value = [canonical, duplicate]
        self.svc.model.get_period.side_effect = lambda pid: {
            'may-a': canonical,
            'may-b': duplicate,
        }.get(str(pid))
        self.svc.model.delete_period.return_value = True
        self.svc.count_period_submissions_for_row = MagicMock(return_value={
            'submitted_count': 0,
            'document_types': [],
            'session_ids': [],
            'last_upload': None,
        })
        self.svc._relink_sessions_from_period = MagicMock(return_value=0)
        self.svc.reconcile_period_upload_counts = MagicMock(return_value=canonical)

        result = self.svc.consolidate_duplicate_periods()

        self.assertEqual(result['removed_ids'], ['may-b'])
        self.svc.model.delete_period.assert_called_once_with('may-b')

    def test_consolidate_skips_locked_duplicate(self):
        canonical = self._period('may-a', uploaded=1)
        duplicate = self._period('may-b', uploaded=0, locked=True)
        self.svc.model.get_all_periods.return_value = [canonical, duplicate]
        self.svc.model.get_period.side_effect = lambda pid: {
            'may-a': canonical,
            'may-b': duplicate,
        }.get(str(pid))
        self.svc._relink_sessions_from_period = MagicMock(return_value=0)
        self.svc.reconcile_period_upload_counts = MagicMock(return_value=canonical)

        result = self.svc.consolidate_duplicate_periods()

        self.assertEqual(result['removed_ids'], [])
        self.svc.model.delete_period.assert_not_called()


class NormalizeLockedPeriodStatusTests(unittest.TestCase):
    def setUp(self):
        self.svc = PeriodManagementService()
        self.svc.model = MagicMock()

    def test_normalizes_open_locked_period_to_closed(self):
        period = FinancialPeriod(
            id='may-2026',
            name='May 2026 Financial Period',
            description='',
            start_date='2026-05-01T00:00:00+00:00',
            end_date='2026-05-31T00:00:00+00:00',
            due_date='2026-06-07',
            status=PeriodStatus.OPEN.value,
            urgency='normal',
            required_uploads=3,
            uploaded_count=3,
            created_by='admin',
            created_at='2026-01-01',
            updated_at='2026-01-02',
            metadata={'is_locked': True},
            is_locked=True,
        )
        closed = FinancialPeriod(
            id='may-2026',
            name='May 2026 Financial Period',
            description='',
            start_date='2026-05-01T00:00:00+00:00',
            end_date='2026-05-31T00:00:00+00:00',
            due_date='2026-06-07',
            status=PeriodStatus.CLOSED.value,
            urgency='normal',
            required_uploads=3,
            uploaded_count=3,
            created_by='admin',
            created_at='2026-01-01',
            updated_at='2026-01-02',
            metadata={'is_locked': True},
            is_locked=True,
        )
        self.svc.model.get_period.return_value = period
        self.svc.model.update_period.return_value = closed

        result = self.svc.normalize_locked_period_status('may-2026')

        self.assertEqual(result.status, PeriodStatus.CLOSED.value)
        self.svc.model.update_period.assert_called_once_with('may-2026', {'status': PeriodStatus.CLOSED.value})


class ClerkDashboardClosedPeriodsTests(unittest.TestCase):
    def setUp(self):
        self.svc = PeriodManagementService()
        self.svc.model = MagicMock()

    def test_dashboard_includes_recent_closed_periods(self):
        open_period = FinancialPeriod(
            id='april-open',
            name='April 2026 Financial Period',
            description='',
            start_date='2026-04-01T00:00:00+00:00',
            end_date='2026-04-30T00:00:00+00:00',
            due_date='2026-05-07',
            status=PeriodStatus.OPEN.value,
            urgency='normal',
            required_uploads=3,
            uploaded_count=1,
            created_by='admin',
            created_at='2026-01-01',
            updated_at='2026-01-02',
            metadata={},
            is_locked=False,
        )
        closed_period = FinancialPeriod(
            id='march-closed',
            name='March 2026 Financial Period',
            description='',
            start_date='2026-03-01T00:00:00+00:00',
            end_date='2026-03-31T00:00:00+00:00',
            due_date='2026-04-07',
            status=PeriodStatus.CLOSED.value,
            urgency='normal',
            required_uploads=3,
            uploaded_count=3,
            created_by='admin',
            created_at='2026-01-01',
            updated_at='2026-02-01',
            metadata={},
            is_locked=False,
        )
        self.svc.model.get_open_periods.return_value = [open_period]
        self.svc.model.get_all_periods.return_value = [open_period, closed_period]
        self.svc.get_available_periods_for_upload = MagicMock(return_value=[open_period])
        self.svc.sync_period_upload_stats = MagicMock(side_effect=lambda pid: {
            'april-open': open_period,
        }.get(str(pid), open_period))
        self.svc.reconcile_period_upload_counts = MagicMock(return_value=closed_period)
        self.svc.is_period_locked = MagicMock(return_value=False)

        data = self.svc.get_dashboard_data()

        self.assertEqual(data['stats']['open_periods'], 1)
        self.assertEqual(data['stats']['closed_periods'], 1)
        self.assertEqual(len(data['periods']), 2)
        self.assertEqual(data['periods'][0]['id'], 'april-open')
        self.assertEqual(data['periods'][1]['id'], 'march-closed')

    def test_dashboard_preview_limits_closed_periods(self):
        open_period = FinancialPeriod(
            id='april-open',
            name='April 2026 Financial Period',
            description='',
            start_date='2026-04-01T00:00:00+00:00',
            end_date='2026-04-30T00:00:00+00:00',
            due_date='2026-05-07',
            status=PeriodStatus.OPEN.value,
            urgency='normal',
            required_uploads=3,
            uploaded_count=1,
            created_by='admin',
            created_at='2026-01-01',
            updated_at='2026-01-02',
            metadata={},
            is_locked=False,
        )
        closed_periods = []
        for month in range(1, 11):
            closed_periods.append(FinancialPeriod(
                id=f'closed-{month}',
                name=f'Month {month} 2026 Financial Period',
                description='',
                start_date=f'2026-{month:02d}-01T00:00:00+00:00',
                end_date=f'2026-{month:02d}-28T00:00:00+00:00',
                due_date=f'2026-{month+1:02d}-07',
                status=PeriodStatus.CLOSED.value,
                urgency='normal',
                required_uploads=3,
                uploaded_count=3,
                created_by='admin',
                created_at='2026-01-01',
                updated_at='2026-02-01',
                metadata={},
                is_locked=False,
            ))
        self.svc.model.get_open_periods.return_value = [open_period]
        self.svc.model.get_all_periods.return_value = [open_period] + closed_periods
        self.svc.get_available_periods_for_upload = MagicMock(return_value=[open_period])
        self.svc.sync_period_upload_stats = MagicMock(return_value=open_period)
        self.svc.reconcile_period_upload_counts = MagicMock(side_effect=lambda pid: next(
            (p for p in closed_periods if str(p.id) == str(pid)), open_period,
        ))
        self.svc.is_period_locked = MagicMock(return_value=False)

        preview = self.svc.get_dashboard_data(closed_scope='preview')
        all_data = self.svc.get_dashboard_data(closed_scope='all')

        self.assertEqual(preview['stats']['closed_periods'], 10)
        self.assertTrue(preview['stats']['has_more_closed'])
        self.assertEqual(preview['stats']['older_closed_count'], 2)
        self.assertEqual(len(preview['periods']), 1 + 8)
        self.assertEqual(len(all_data['periods']), 1 + 10)
        self.assertFalse(all_data['stats']['has_more_closed'])


class MergeDuplicatePeriodRowsTests(unittest.TestCase):
    def setUp(self):
        self.svc = PeriodManagementService()
        self.svc.model = MagicMock()

    def _period(self, pid, uploaded=0, locked=False):
        return FinancialPeriod(
            id=pid,
            name='May 2026 Financial Period',
            description='Monthly financial reporting for May 2026',
            start_date='2026-05-01T00:00:00+00:00',
            end_date='2026-05-31T00:00:00+00:00',
            due_date='2026-06-07',
            status=PeriodStatus.CLOSED.value if locked else PeriodStatus.OPEN.value,
            urgency='normal',
            required_uploads=3,
            uploaded_count=uploaded,
            created_by='admin',
            created_at='2026-01-01',
            updated_at='2026-01-02',
            metadata={'uploaded_document_types': ['income_statement']} if uploaded else {},
            is_locked=locked,
        )

    def test_merge_removes_locked_empty_duplicate(self):
        canonical = self._period('may-a', uploaded=2)
        duplicate = self._period('may-b', uploaded=0, locked=True)
        self.svc.model.get_all_periods.return_value = [canonical, duplicate]
        self.svc.model.get_period.side_effect = lambda pid: {
            'may-a': canonical,
            'may-b': duplicate,
        }.get(str(pid))
        self.svc.model.delete_period.return_value = True
        self.svc.count_period_submissions_for_row = MagicMock(return_value={
            'submitted_count': 0,
            'document_types': [],
            'session_ids': [],
            'last_upload': None,
        })
        self.svc._relink_sessions_from_period = MagicMock(return_value=1)
        self.svc.reconcile_period_upload_counts = MagicMock(return_value=canonical)
        self.svc.normalize_locked_period_status = MagicMock(return_value=canonical)

        result = self.svc.merge_duplicate_period_rows('may-b')

        self.assertEqual(result['canonical_id'], 'may-a')
        self.assertEqual(result['removed_ids'], ['may-b'])
        self.assertEqual(result['relinked_sessions'], 1)
        self.svc.model.delete_period.assert_called_once_with('may-b')


if __name__ == '__main__':
    unittest.main()
