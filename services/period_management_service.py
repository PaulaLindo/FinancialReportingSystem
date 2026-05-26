"""
Period Management Service
Business logic for financial period management and workflow operations

**Uses:** ``financial_periods`` through ``models.period_models.period_model`` (not the
``periods`` table used by ``models.workflow_models`` for submission workflow).

When adding features that tie uploads to a calendar period, prefer this service and
``financial_periods`` unless you explicitly need ``WorkflowModel`` / ``submissions``.
"""

from datetime import datetime, timedelta, timezone, time
from typing import Dict, List, Optional, Any, Tuple
import logging
from dataclasses import asdict

from models.period_models import (
    period_model, FinancialPeriod, PeriodStatus, PeriodUrgency
)
from models.supabase_auth_models import supabase_auth

# Set up logging
logger = logging.getLogger(__name__)

# Municipal clerk workflow expects one submission per document type per period.
STANDARD_REQUIRED_UPLOADS = 3
STANDARD_REQUIRED_DOCUMENT_TYPES = (
    'balance_sheet',
    'income_statement',
    'budget_report',
)

CLOSED_PERIOD_PREVIEW_LIMIT = 8

_PERIOD_SESSION_TABLES = (
    ('balance_sheet_sessions', 'balance_sheet'),
    ('income_statement_sessions', 'income_statement'),
    ('budget_report_sessions', 'budget_report'),
)


class PeriodManagementService:
    """Service for managing financial periods and workflow operations"""
    
    def __init__(self):
        self.model = period_model

    @staticmethod
    def validate_required_uploads_count(required_uploads: Any) -> int:
        """Each open period expects balance sheet, income statement, and budget report."""
        try:
            count = int(required_uploads)
        except (TypeError, ValueError):
            raise ValueError(
                f"Required uploads must be {STANDARD_REQUIRED_UPLOADS} "
                f"(balance sheet, income statement, budget report)."
            )
        if count != STANDARD_REQUIRED_UPLOADS:
            raise ValueError(
                f"Required uploads must be {STANDARD_REQUIRED_UPLOADS} for municipal reporting "
                f"(balance sheet, income statement, budget report). Received {count}."
            )
        return count

    @staticmethod
    def _period_identity_key(period: FinancialPeriod) -> str:
        name = (period.name or '').strip().lower()
        start = str(period.start_date or '')[:10]
        end = str(period.end_date or '')[:10]
        return f"{name}|{start}|{end}"

    @classmethod
    def _period_identity_key_from_data(cls, period_data: Dict[str, Any]) -> str:
        name = str(period_data.get('name') or '').strip().lower()
        start = str(period_data.get('start_date') or '')[:10]
        end = str(period_data.get('end_date') or '')[:10]
        return f"{name}|{start}|{end}"

    @staticmethod
    def _canonical_period_score(period: FinancialPeriod) -> tuple:
        meta = period.metadata or {}
        submission_signals = int(period.uploaded_count or 0)
        submission_signals += len(meta.get('uploaded_document_types') or [])
        submission_signals += len(meta.get('upload_session_ids') or [])
        return (
            submission_signals,
            period.updated_at or '',
            period.created_at or '',
        )

    def dedupe_periods(self, periods: List[FinancialPeriod]) -> List[FinancialPeriod]:
        """Keep one canonical row per reporting month when duplicates exist in Supabase."""
        groups: Dict[str, List[FinancialPeriod]] = {}
        for period in periods:
            groups.setdefault(self._period_identity_key(period), []).append(period)

        deduped: List[FinancialPeriod] = []
        for key, group in groups.items():
            if len(group) == 1:
                deduped.append(group[0])
                continue
            canonical = max(group, key=self._canonical_period_score)
            duplicate_ids = [p.id for p in group if p.id != canonical.id]
            logger.warning(
                "Duplicate periods for %s: keeping %s, hiding %s",
                key,
                canonical.id,
                duplicate_ids,
            )
            deduped.append(canonical)

        deduped.sort(key=lambda p: p.due_date or '')
        return deduped

    def dedupe_open_periods(self, periods: List[FinancialPeriod]) -> List[FinancialPeriod]:
        return self.dedupe_periods(periods)

    def find_conflicting_period(self, period_data: Dict[str, Any]) -> Optional[FinancialPeriod]:
        key = self._period_identity_key_from_data(period_data)
        for period in self.model.get_all_periods():
            if self._period_identity_key(period) == key:
                return period
        return None

    def find_conflicting_open_period(self, period_data: Dict[str, Any]) -> Optional[FinancialPeriod]:
        return self.find_conflicting_period(period_data)

    def related_period_ids(self, period_id: str) -> List[str]:
        """All period row IDs that represent the same reporting month (including duplicates)."""
        period = self.model.get_period(period_id)
        if not period:
            return [str(period_id)]
        key = self._period_identity_key(period)
        ids: List[str] = []
        for candidate in self.model.get_all_periods():
            if self._period_identity_key(candidate) == key:
                ids.append(str(candidate.id))
        return ids or [str(period_id)]

    def resolve_canonical_period_id(self, period_id: str) -> str:
        """Map a period id (including duplicate rows) to the canonical dashboard card id."""
        period = self.model.get_period(period_id)
        if not period:
            return str(period_id)
        matches = [
            p for p in self.model.get_open_periods()
            if self._period_identity_key(p) == self._period_identity_key(period)
        ]
        if not matches:
            return self.canonical_period_id_for_month(str(period_id))
        if len(matches) == 1:
            return str(matches[0].id)
        canonical = max(matches, key=self._canonical_period_score)
        return str(canonical.id)

    def canonical_period_id_for_month(self, period_id: str) -> str:
        """Pick the best row to keep when duplicate financial_periods exist for one month."""
        period = self.model.get_period(period_id)
        if not period:
            return str(period_id)
        key = self._period_identity_key(period)
        group = [
            p for p in self.model.get_all_periods()
            if self._period_identity_key(p) == key
        ]
        if len(group) <= 1:
            return str(group[0].id) if group else str(period_id)
        canonical = max(group, key=self._canonical_period_score)
        return str(canonical.id)

    def _session_row_submitted(self, row: Dict[str, Any]) -> bool:
        from utils.session_workflow import SUBMITTED_FOR_REVIEW_STATUSES, effective_workflow_status

        class _RowSession:
            pass

        session = _RowSession()
        session.status = row.get('status') or ''
        metadata = row.get('metadata') or {}
        session.metadata = metadata if isinstance(metadata, dict) else {}
        return effective_workflow_status(session) in SUBMITTED_FOR_REVIEW_STATUSES

    def count_period_submissions(self, period_id: str) -> Dict[str, Any]:
        """Count unique submitted document types linked to a financial period."""
        related_ids = self.related_period_ids(period_id)
        client = self.model.client
        document_types: List[str] = []
        session_ids: List[str] = []
        last_upload: Optional[str] = None
        seen_session_ids: set = set()

        for table, doc_type in _PERIOD_SESSION_TABLES:
            submitted_for_type = False
            for pid in related_ids:
                try:
                    result = (
                        client.table(table)
                        .select('id,status,metadata,updated_at')
                        .filter('metadata->>period_id', 'eq', pid)
                        .execute()
                    )
                except Exception as exc:
                    logger.warning("Could not query %s for period %s: %s", table, pid, exc)
                    continue

                for row in result.data or []:
                    row_id = str(row.get('id') or '')
                    if row_id in seen_session_ids:
                        continue
                    if not self._session_row_submitted(row):
                        continue
                    seen_session_ids.add(row_id)
                    submitted_for_type = True
                    session_ids.append(row_id)
                    updated = row.get('updated_at')
                    if updated and (last_upload is None or str(updated) > str(last_upload)):
                        last_upload = str(updated)
            if submitted_for_type and doc_type not in document_types:
                document_types.append(doc_type)

        return {
            'submitted_count': len(document_types),
            'document_types': document_types,
            'session_ids': [sid for sid in session_ids if sid],
            'last_upload': last_upload,
        }

    def count_period_submissions_for_row(self, period_id: str) -> Dict[str, Any]:
        """Count submitted document types linked only to this period row (not duplicate siblings)."""
        client = self.model.client
        document_types: List[str] = []
        session_ids: List[str] = []
        last_upload: Optional[str] = None
        seen_session_ids: set = set()

        for table, doc_type in _PERIOD_SESSION_TABLES:
            submitted_for_type = False
            try:
                result = (
                    client.table(table)
                    .select('id,status,metadata,updated_at')
                    .filter('metadata->>period_id', 'eq', str(period_id))
                    .execute()
                )
            except Exception as exc:
                logger.warning("Could not query %s for period %s: %s", table, period_id, exc)
                continue

            for row in result.data or []:
                row_id = str(row.get('id') or '')
                if row_id in seen_session_ids:
                    continue
                if not self._session_row_submitted(row):
                    continue
                seen_session_ids.add(row_id)
                submitted_for_type = True
                session_ids.append(row_id)
                updated = row.get('updated_at')
                if updated and (last_upload is None or str(updated) > str(last_upload)):
                    last_upload = str(updated)
            if submitted_for_type and doc_type not in document_types:
                document_types.append(doc_type)

        return {
            'submitted_count': len(document_types),
            'document_types': document_types,
            'session_ids': [sid for sid in session_ids if sid],
            'last_upload': last_upload,
        }

    def _relink_sessions_from_period(self, from_period_id: str, to_period_id: str) -> int:
        """Move session metadata.period_id from a duplicate row to the canonical period."""
        client = self.model.client
        canonical = self.model.get_period(str(to_period_id))
        canonical_name = canonical.name if canonical else None
        relinked = 0

        for table, _doc_type in _PERIOD_SESSION_TABLES:
            try:
                result = (
                    client.table(table)
                    .select('id,metadata')
                    .filter('metadata->>period_id', 'eq', str(from_period_id))
                    .execute()
                )
            except Exception as exc:
                logger.warning(
                    "Could not query %s to relink sessions from %s: %s",
                    table,
                    from_period_id,
                    exc,
                )
                continue

            for row in result.data or []:
                row_id = str(row.get('id') or '')
                if not row_id:
                    continue
                metadata = dict(row.get('metadata') or {})
                metadata['period_id'] = str(to_period_id)
                if canonical_name:
                    metadata['period_name'] = canonical_name
                    metadata.setdefault('reporting_period', canonical_name)
                try:
                    client.table(table).update({'metadata': metadata}).eq('id', row_id).execute()
                    relinked += 1
                except Exception as exc:
                    logger.warning(
                        "Could not relink session %s in %s from %s to %s: %s",
                        row_id,
                        table,
                        from_period_id,
                        to_period_id,
                        exc,
                    )

        return relinked

    def consolidate_duplicate_periods(self) -> Dict[str, Any]:
        """Relink uploads and remove extra Supabase rows for the same reporting month."""
        all_periods = self.model.get_all_periods()
        groups: Dict[str, List[FinancialPeriod]] = {}
        for period in all_periods:
            groups.setdefault(self._period_identity_key(period), []).append(period)

        removed_ids: List[str] = []
        relinked_sessions = 0
        reconciled_ids: set = set()

        for group in groups.values():
            if len(group) <= 1:
                continue

            canonical = max(group, key=self._canonical_period_score)
            canonical_id = str(canonical.id)

            for duplicate in group:
                if str(duplicate.id) == canonical_id:
                    continue

                dup_id = str(duplicate.id)
                relinked_sessions += self._relink_sessions_from_period(dup_id, canonical_id)

                if getattr(duplicate, 'is_locked', False) or (duplicate.metadata or {}).get('is_locked'):
                    logger.warning("Skipping delete of locked duplicate period %s", dup_id)
                    continue

                row_stats = self.count_period_submissions_for_row(dup_id)
                if row_stats['submitted_count'] > 0:
                    logger.warning(
                        "Duplicate period %s still has %s submission(s) after relink",
                        dup_id,
                        row_stats['submitted_count'],
                    )
                    continue

                if self.model.delete_period(dup_id):
                    removed_ids.append(dup_id)
                    logger.info(
                        "Removed duplicate period row %s; canonical period is %s",
                        dup_id,
                        canonical_id,
                    )

            reconciled_ids.add(canonical_id)

        for period_id in reconciled_ids:
            try:
                self.reconcile_period_upload_counts(period_id)
            except Exception as exc:
                logger.warning("Could not reconcile canonical period %s after dedupe: %s", period_id, exc)

        return {
            'removed_ids': removed_ids,
            'relinked_sessions': relinked_sessions,
        }

    def merge_duplicate_period_rows(self, period_id: str) -> Dict[str, Any]:
        """Relink sessions and delete duplicate rows for the same reporting month (including locked empties)."""
        period = self.model.get_period(period_id)
        if not period:
            raise Exception("Period not found")

        canonical_id = self.canonical_period_id_for_month(str(period_id))
        canonical = self.model.get_period(canonical_id)
        if not canonical:
            raise Exception("Canonical period not found")

        related_ids = self.related_period_ids(canonical_id)
        duplicate_ids = [str(pid) for pid in related_ids if str(pid) != str(canonical_id)]
        if not duplicate_ids:
            return {
                'success': True,
                'canonical_id': str(canonical_id),
                'canonical_name': canonical.name,
                'removed_ids': [],
                'relinked_sessions': 0,
                'skipped': [],
                'message': 'No duplicate rows found for this reporting month.',
            }

        removed_ids: List[str] = []
        skipped: List[Dict[str, str]] = []
        relinked_sessions = 0

        for dup_id in duplicate_ids:
            relinked_sessions += self._relink_sessions_from_period(dup_id, str(canonical_id))
            row_stats = self.count_period_submissions_for_row(dup_id)
            if row_stats['submitted_count'] > 0:
                skipped.append({
                    'id': dup_id,
                    'reason': (
                        f"Still has {row_stats['submitted_count']} submitted document(s) on this row after relink."
                    ),
                })
                continue
            try:
                if self.model.delete_period(dup_id):
                    removed_ids.append(dup_id)
                    logger.info(
                        "Merged duplicate period row %s into canonical %s",
                        dup_id,
                        canonical_id,
                    )
                else:
                    skipped.append({'id': dup_id, 'reason': 'Delete returned no rows.'})
            except Exception as exc:
                skipped.append({'id': dup_id, 'reason': str(exc)})

        try:
            self.reconcile_period_upload_counts(str(canonical_id))
            self.normalize_locked_period_status(str(canonical_id))
        except Exception as exc:
            logger.warning("Could not reconcile canonical period %s after merge: %s", canonical_id, exc)

        message = f"Merged {len(removed_ids)} duplicate row(s) into {canonical.name}."
        if skipped:
            message += f" {len(skipped)} row(s) could not be removed — see skipped details."

        return {
            'success': True,
            'canonical_id': str(canonical_id),
            'canonical_name': canonical.name,
            'removed_ids': removed_ids,
            'relinked_sessions': relinked_sessions,
            'skipped': skipped,
            'message': message,
        }

    def reconcile_period_upload_counts(self, period_id: str) -> FinancialPeriod:
        """Refresh upload counters from submitted sessions without changing period status."""
        period = self.model.get_period(period_id)
        if not period:
            raise Exception("Period not found")

        stats = self.count_period_submissions(period_id)
        metadata = dict(period.metadata or {})
        metadata['uploaded_document_types'] = stats['document_types']
        if stats['session_ids']:
            metadata['upload_session_ids'] = stats['session_ids'][-20:]
        if stats['last_upload']:
            metadata['last_upload'] = stats['last_upload']

        return self.model.update_period(period_id, {
            'uploaded_count': stats['submitted_count'],
            'metadata': metadata,
        })

    def sync_period_upload_stats(self, period_id: str) -> FinancialPeriod:
        """Reconcile upload counters and auto open/close when clerk upload quotas change."""
        period = self.reconcile_period_upload_counts(period_id)

        stats = self.count_period_submissions(period_id)
        if (
            period.status == PeriodStatus.OPEN.value
            and stats['submitted_count'] >= period.required_uploads
            and period.required_uploads > 0
        ):
            logger.info("Period %s reached upload limit after sync, auto-closing", period.name)
            period = self.model.close_period(period_id)
        elif (
            period.status == PeriodStatus.CLOSED.value
            and stats['submitted_count'] < period.required_uploads
            and not (period.metadata or {}).get('admin_closed')
        ):
            logger.info("Period %s has open upload slots after sync, reopening", period.name)
            period = self.model.open_period(period_id)

        return period

    def fix_period_required_uploads(self, period_id: str) -> FinancialPeriod:
        """Correct a period configured with the wrong required upload count."""
        period = self.model.get_period(period_id)
        if not period:
            raise Exception("Period not found")
        if getattr(period, "is_locked", False) or (period.metadata or {}).get("is_locked"):
            raise Exception("Locked periods cannot be edited. Contact the CFO if a correction is needed.")

        period = self.model.update_period(period_id, {
            'required_uploads': STANDARD_REQUIRED_UPLOADS,
        })
        period = self.sync_period_upload_stats(period_id)
        logger.info("Corrected required_uploads for period %s to %s", period.name, STANDARD_REQUIRED_UPLOADS)
        return period

    def delete_financial_period(self, period_id: str) -> None:
        """Delete a reporting period when it has no submitted documents and is not locked."""
        period = self.model.get_period(period_id)
        if not period:
            raise Exception("Period not found")
        if getattr(period, "is_locked", False) or (period.metadata or {}).get("is_locked"):
            raise Exception("Locked periods cannot be deleted.")
        stats = self.count_period_submissions(period_id)
        if stats['submitted_count'] > 0:
            raise Exception(
                f"Cannot delete '{period.name}' — {stats['submitted_count']} document(s) already submitted "
                f"({', '.join(stats['document_types']) or 'unknown'}). "
                f"Use “Fix to 3 uploads” instead, or ask the CFO after workflow is complete."
            )

        if not self.model.delete_period(period_id):
            raise Exception("Failed to delete period")
        logger.info("Deleted financial period %s (%s)", period.name, period_id)

    def create_financial_period(self, period_data: Dict[str, Any], created_by: str) -> FinancialPeriod:
        """Create a new financial period with validation"""
        try:
            # Validate required fields
            required_fields = ['name', 'start_date', 'end_date', 'due_date', 'required_uploads']
            for field in required_fields:
                if field not in period_data or not period_data[field]:
                    raise ValueError(f"Required field '{field}' is missing or empty")
            
            # Validate dates
            start_date = self._parse_date(period_data['start_date'])
            end_date = self._parse_date(period_data['end_date'])
            due_date = self._parse_date(period_data['due_date'])
            
            if start_date >= end_date:
                raise ValueError("Start date must be before end date")
            
            if due_date < end_date:
                raise ValueError("Due date must be on or after end date")

            conflict = self.find_conflicting_period(period_data)
            if conflict:
                raise ValueError(
                    f"A reporting period already exists for "
                    f"{period_data['name']} ({str(period_data['start_date'])[:10]} to "
                    f"{str(period_data['end_date'])[:10]}). "
                    f"Delete the existing period before creating another."
                )
            
            # Validate required uploads
            period_data['required_uploads'] = self.validate_required_uploads_count(
                period_data['required_uploads']
            )
            
            # Prepare period data
            full_period_data = {
                **period_data,
                'created_by': created_by,
                'description': period_data.get('description', ''),
                'status': PeriodStatus.DRAFT.value,
                'urgency': PeriodUrgency.NORMAL.value,
                'uploaded_count': 0,
                'metadata': {}
            }
            
            # Create period
            period = self.model.create_period(full_period_data)
            logger.info(f"Created financial period: {period.name} ({period.id})")
            
            return period
            
        except Exception as e:
            logger.error(f"Error creating financial period: {str(e)}")
            raise Exception(f"Failed to create financial period: {str(e)}")

    def get_available_periods_for_upload(self) -> List[FinancialPeriod]:
        """Open periods available for clerk uploads (includes catch-up months)."""
        try:
            return self.dedupe_open_periods(self.model.get_open_periods())
        except Exception as e:
            logger.error(f"Error getting available periods: {str(e)}")
            raise Exception(f"Failed to get available periods: {str(e)}")

    def validate_upload_for_period(self, period_id: str) -> Tuple[bool, str]:
        """Validate if upload is allowed for a period"""
        try:
            period = self.model.get_period(period_id)
            if not period:
                return False, "Period not found"
            
            # Check if period is open
            if period.status != PeriodStatus.OPEN.value:
                return False, f"Period is {period.status}. Uploads not allowed."

            if getattr(period, "is_locked", False) or (period.metadata or {}).get("is_locked"):
                return False, f"Period '{period.name}' is locked. No uploads or edits are permitted."
            
            # Open periods accept catch-up uploads after the reporting month ends.
            # Calendar dates on the period describe the report, not the upload window.
            
            # Check if upload limit reached (derive from sessions, not stale counter)
            stats = self.count_period_submissions(period_id)
            if stats['submitted_count'] >= period.required_uploads:
                return False, f"Upload limit reached ({period.required_uploads} uploads)"
            
            return True, "Upload allowed"
            
        except Exception as e:
            logger.error(f"Error validating upload for period: {str(e)}")
            return False, f"Validation error: {str(e)}"

    def record_upload_for_period(self, period_id: str, upload_info: Dict[str, Any]) -> FinancialPeriod:
        """Record an upload for a period by reconciling submitted sessions."""
        try:
            can_upload, message = self.validate_upload_for_period(period_id)
            if not can_upload:
                raise Exception(message)

            period = self.sync_period_upload_stats(period_id)
            logger.info(
                "Synced upload stats for period %s: %s/%s",
                period.name,
                period.uploaded_count,
                period.required_uploads,
            )
            return period

        except Exception as e:
            logger.error(f"Error recording upload for period: {str(e)}")
            raise Exception(f"Failed to record upload: {str(e)}")

    def remove_upload_from_period(self, period_id: str) -> FinancialPeriod:
        """Remove an upload from a period (for deleted/cancelled uploads)"""
        try:
            period = self.model.get_period(period_id)
            if not period:
                raise Exception("Period not found")
            
            # Decrement upload count
            period = self.model.decrement_upload_count(period_id)
            
            # If period was closed and uploads were removed, reopen it
            if period.status == PeriodStatus.CLOSED.value and period.uploaded_count < period.required_uploads:
                logger.info(f"Period {period.name} has available slots, reopening")
                period = self.model.open_period(period_id)
            
            logger.info(f"Removed upload from period {period.name}: {period.uploaded_count}/{period.required_uploads}")
            
            return period
            
        except Exception as e:
            logger.error(f"Error removing upload from period: {str(e)}")
            raise Exception(f"Failed to remove upload: {str(e)}")

    def link_session_to_period(
        self,
        session_id: str,
        document_type: str,
        period_id: str,
    ) -> None:
        """Attach a reporting period to an existing submission and refresh period counters."""
        from utils.period_lock import attach_period_to_session_metadata

        canonical_period_id = self.resolve_canonical_period_id(str(period_id))
        model = None
        if document_type == 'balance_sheet':
            from models.balance_sheet_models import BalanceSheetModel
            model = BalanceSheetModel()
        elif document_type == 'income_statement':
            from models.income_statement_models import income_statement_model
            model = income_statement_model
        elif document_type == 'budget_report':
            from models.budget_report_models import budget_report_model
            model = budget_report_model
        else:
            raise ValueError(f"Unsupported document type: {document_type}")

        session = model.get_session(session_id)
        if not session:
            raise Exception(f"Session {session_id} not found")

        attach_period_to_session_metadata(session, canonical_period_id)
        model.update_session(session)
        self.sync_period_upload_stats(canonical_period_id)
        logger.info(
            "Linked %s session %s to period %s",
            document_type,
            session_id,
            canonical_period_id,
        )

    def open_period_for_uploads(self, period_id: str) -> FinancialPeriod:
        """Open a period for uploads"""
        try:
            period = self.model.get_period(period_id)
            if not period:
                raise Exception("Period not found")
            
            if period.status == PeriodStatus.OPEN.value:
                logger.warning(f"Period {period.name} is already open")
                return period

            metadata = dict(period.metadata or {})
            metadata.pop('admin_closed', None)
            metadata.pop('admin_closed_at', None)
            period = self.model.update_period(period_id, {
                'status': PeriodStatus.OPEN.value,
                'urgency': PeriodUrgency.NORMAL.value,
                'metadata': metadata,
            })
            logger.info(f"Opened period {period.name} for uploads")

            return period
            
        except Exception as e:
            logger.error(f"Error opening period: {str(e)}")
            raise Exception(f"Failed to open period: {str(e)}")

    def close_period(self, period_id: str) -> FinancialPeriod:
        """Close a period"""
        try:
            period = self.model.get_period(period_id)
            if not period:
                raise Exception("Period not found")
            
            if period.status == PeriodStatus.CLOSED.value:
                logger.warning(f"Period {period.name} is already closed")
                return period
            
            metadata = dict(period.metadata or {})
            metadata['admin_closed'] = True
            metadata['admin_closed_at'] = datetime.now(timezone.utc).isoformat()
            period = self.model.update_period(period_id, {
                'status': PeriodStatus.CLOSED.value,
                'metadata': metadata,
            })
            logger.info(f"Closed period {period.name}")
            
            return period
            
        except Exception as e:
            logger.error(f"Error closing period: {str(e)}")
            raise Exception(f"Failed to close period: {str(e)}")

    def lock_period(self, period_id: str, locked_by: str) -> FinancialPeriod:
        """Lock a period after CFO finalization."""
        try:
            period = self.model.get_period(period_id)
            if not period:
                raise Exception("Period not found")
            if getattr(period, "is_locked", False) or (period.metadata or {}).get("is_locked"):
                logger.info(f"Period {period.name} is already locked")
                return period
            period = self.model.lock_period(period_id, locked_by)
            logger.info(f"Locked period {period.name} by {locked_by}")
            return period
        except Exception as e:
            logger.error(f"Error locking period: {str(e)}")
            raise Exception(f"Failed to lock period: {str(e)}")

    def is_period_locked(self, period_id: str) -> bool:
        period = self.model.get_period(period_id)
        if not period:
            return False
        return bool(getattr(period, "is_locked", False) or (period.metadata or {}).get("is_locked"))

    def normalize_locked_period_status(self, period_id: str) -> FinancialPeriod:
        """Locked reporting periods must not remain status=open in Supabase."""
        period = self.model.get_period(period_id)
        if not period:
            raise Exception("Period not found")
        if not self.is_period_locked(period_id):
            return period
        if period.status == PeriodStatus.OPEN.value:
            logger.info("Normalizing locked period %s from open to closed", period.name)
            return self.model.update_period(period_id, {'status': PeriodStatus.CLOSED.value})
        return period

    def get_dashboard_data(self, closed_scope: str = 'preview') -> Dict[str, Any]:
        """Get dashboard data for finance clerks (open + closed periods).

        closed_scope:
            preview — open periods plus the most recent closed periods (default)
            all — open periods plus every closed period
        """
        try:
            open_periods = self.dedupe_open_periods(self.model.get_open_periods())
            available_periods = self.dedupe_open_periods(self.get_available_periods_for_upload())
            available_ids = {str(p.id) for p in available_periods}

            formatted_periods: List[Dict[str, Any]] = []
            open_ids: set = set()

            for period in open_periods:
                if self.is_period_locked(str(period.id)):
                    continue
                try:
                    period = self.sync_period_upload_stats(period.id)
                except Exception as sync_err:
                    logger.warning("Could not sync upload stats for period %s: %s", period.id, sync_err)
                row = self._format_period_for_dashboard(period, available_ids)
                formatted_periods.append(row)
                open_ids.add(str(period.id))

            all_deduped = self.dedupe_periods(self.model.get_all_periods())
            closed_periods = [
                p for p in all_deduped
                if str(p.id) not in open_ids
                and (
                    p.status == PeriodStatus.CLOSED.value
                    or self.is_period_locked(str(p.id))
                )
            ]
            closed_periods.sort(
                key=lambda p: str(p.end_date or p.start_date or ''),
                reverse=True,
            )
            if closed_scope == 'all':
                closed_to_show = closed_periods
            else:
                closed_to_show = closed_periods[:CLOSED_PERIOD_PREVIEW_LIMIT]

            for period in closed_to_show:
                try:
                    period = self.reconcile_period_upload_counts(period.id)
                except Exception as sync_err:
                    logger.warning("Could not reconcile closed period %s: %s", period.id, sync_err)
                row = self._format_period_for_dashboard(period, available_ids)
                row['is_locked'] = self.is_period_locked(str(period.id))
                formatted_periods.append(row)

            older_closed_count = max(0, len(closed_periods) - CLOSED_PERIOD_PREVIEW_LIMIT)

            stats = {
                'open_periods': len(open_periods),
                'closed_periods': len(closed_periods),
                'recent_closed_periods': min(len(closed_periods), CLOSED_PERIOD_PREVIEW_LIMIT),
                'older_closed_count': older_closed_count,
                'has_more_closed': older_closed_count > 0 and closed_scope != 'all',
                'closed_scope': closed_scope,
                'available_periods': len(available_periods),
                'total_periods': len(all_deduped),
                'urgent_periods': len([p for p in open_periods if p.is_urgent]),
                'overdue_periods': len([p for p in open_periods if p.is_overdue]),
            }

            return {
                'periods': formatted_periods,
                'stats': stats,
            }

        except Exception as e:
            logger.error(f"Error getting dashboard data: {str(e)}")
            raise Exception(f"Failed to get dashboard data: {str(e)}")

    def _format_period_for_dashboard(
        self,
        period: FinancialPeriod,
        available_ids: set,
    ) -> Dict[str, Any]:
        period_data = period.to_dict()
        period_data['can_upload'] = str(period.id) in available_ids
        period_data['upload_slots_remaining'] = max(0, period.required_uploads - period.uploaded_count)
        period_data['is_locked'] = self.is_period_locked(str(period.id))
        if period_data['is_locked'] and period_data.get('status') == PeriodStatus.OPEN.value:
            period_data['status'] = PeriodStatus.CLOSED.value
        return period_data

    def update_period_urgency(self) -> Dict[str, int]:
        """Update urgency flags for all periods"""
        try:
            updated_count = self.model.update_urgency_flags()
            
            logger.info(f"Updated urgency flags for {updated_count} periods")
            
            return {
                'updated_periods': updated_count,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error updating period urgency: {str(e)}")
            raise Exception(f"Failed to update period urgency: {str(e)}")

    def get_period_summary(self, period_id: str) -> Dict[str, Any]:
        """Get detailed summary of a period"""
        try:
            period = self.model.get_period(period_id)
            if not period:
                raise Exception("Period not found")
            
            # Get upload validation
            can_upload, upload_message = self.validate_upload_for_period(period_id)
            
            # Build summary
            summary = {
                **period.to_dict(),
                'can_upload': can_upload,
                'upload_message': upload_message,
                'upload_slots_remaining': max(0, period.required_uploads - period.uploaded_count),
                'is_past_due': period.is_overdue,
                'days_overdue': max(0, -period.days_remaining) if period.is_overdue else 0
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting period summary: {str(e)}")
            raise Exception(f"Failed to get period summary: {str(e)}")

    def create_sample_periods(self, created_by: str) -> List[FinancialPeriod]:
        """Create sample financial periods for testing/demo"""
        try:
            sample_periods = []
            now = datetime.now()
            
            # Create current month period (open)
            current_start = now.replace(day=1)
            current_end = (current_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            current_due = current_end + timedelta(days=7)
            
            current_period = self.create_financial_period({
                'name': f"{now.strftime('%B %Y')} Financial Period",
                'description': f"Monthly financial reporting for {now.strftime('%B %Y')}",
                'start_date': current_start.isoformat(),
                'end_date': current_end.isoformat(),
                'due_date': current_due.isoformat(),
                'required_uploads': 3
            }, created_by)
            
            # Open the current period
            current_period = self.open_period_for_uploads(current_period.id)
            sample_periods.append(current_period)
            
            # Create next month period (draft)
            next_start = current_end + timedelta(days=1)
            next_end = (next_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            next_due = next_end + timedelta(days=7)
            
            next_period = self.create_financial_period({
                'name': f"{(now + timedelta(days=32)).strftime('%B %Y')} Financial Period",
                'description': f"Monthly financial reporting for {(now + timedelta(days=32)).strftime('%B %Y')}",
                'start_date': next_start.isoformat(),
                'end_date': next_end.isoformat(),
                'due_date': next_due.isoformat(),
                'required_uploads': 3
            }, created_by)
            
            sample_periods.append(next_period)
            
            # Create previous month period (closed)
            prev_start = (current_start - timedelta(days=1)).replace(day=1)
            prev_end = current_start - timedelta(days=1)
            prev_due = prev_end + timedelta(days=7)
            
            prev_period = self.create_financial_period({
                'name': f"{(now - timedelta(days=32)).strftime('%B %Y')} Financial Period",
                'description': f"Monthly financial reporting for {(now - timedelta(days=32)).strftime('%B %Y')}",
                'start_date': prev_start.isoformat(),
                'end_date': prev_end.isoformat(),
                'due_date': prev_due.isoformat(),
                'required_uploads': 3
            }, created_by)
            
            # Close the previous period
            prev_period = self.close_period(prev_period.id)
            sample_periods.append(prev_period)
            
            logger.info(f"Created {len(sample_periods)} sample periods")
            
            return sample_periods
            
        except Exception as e:
            logger.error(f"Error creating sample periods: {str(e)}")
            raise Exception(f"Failed to create sample periods: {str(e)}")

    def _utc_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _end_of_day_utc(self, dt: datetime) -> datetime:
        day = dt.astimezone(timezone.utc).date()
        return datetime.combine(day, time(23, 59, 59, 999999), tzinfo=timezone.utc)

    def _parse_date(self, date_string: str) -> datetime:
        """Parse date/datetime strings to timezone-aware UTC (start of day for YYYY-MM-DD)."""
        if not date_string:
            raise ValueError("Empty date")
        raw = str(date_string).strip()
        try:
            if 'T' in raw:
                parsed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
            else:
                parsed = datetime.strptime(raw[:10], '%Y-%m-%d')
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except Exception as exc:
            raise ValueError(f"Invalid date format: {date_string}") from exc


# Create global period management service instance
period_management_service = PeriodManagementService()
