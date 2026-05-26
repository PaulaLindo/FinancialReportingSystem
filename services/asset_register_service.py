"""
GRAP 17 asset register — persistence, lifecycle journals, and GL reconciliation.

Asset journals (useful life review, impairment, disposal) queue for Finance Manager
approval without modifying the trial balance workflow.

Persistence: Supabase only (scripts/create_asset_register_tables.sql).
"""

from __future__ import annotations

import csv
import io
import logging
import re
import threading
from copy import deepcopy
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from models.asset_lifecycle_models import AssetLifecycleModel
from models.asset_register_models import AssetRegisterModel, InMemoryAssetRegisterModel, get_asset_register_model
from utils.asset_journal_materiality import (
    escalation_reason_label,
    journal_materiality_amount,
    materiality_threshold,
    requires_cfo_escalation,
)

_LOCK = threading.Lock()

JOURNAL_PENDING = 'pending_review'
JOURNAL_PENDING_CFO = 'pending_cfo'
JOURNAL_APPROVED = 'approved'
JOURNAL_REJECTED = 'rejected'

VALID_JOURNAL_TYPES = frozenset({'useful_life_review', 'impairment', 'disposal'})
SETTLED_JOURNAL_STATUSES = frozenset({JOURNAL_APPROVED, JOURNAL_REJECTED})

# GL account codes / GRAP lines used when syncing from trial balance
_PPE_GRAP_CODES = {'NCA-001'}
_INTANGIBLE_GRAP_CODES = {'NCA-002'}
_INVESTMENT_GRAP_CODES = {'NCA-003'}
_FIXED_ASSET_GRAP_LABELS = {
    'PROPERTY, PLANT AND EQUIPMENT',
    'INTANGIBLE ASSETS',
    'INVESTMENTS',
}
# Standard GRAP chart account codes (scripts/seed_grap_accounts.py)
_FIXED_ASSET_GRAP_ACCOUNT_CODES = {'2100', '2200', '2300'}
_FIXED_ASSET_DESC_KEYWORDS = (
    'property, plant and equipment',
    'fixed asset',
    'capital asset',
    'intangible asset',
    'long-term investment',
    'investment portfolio',
    'ppe',
)
_GL_SOURCE_LABELS = {
    'manual': 'Manual entry',
    'trial_balance': 'Trial balance',
}

logger = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now().isoformat()


def _journal_id() -> str:
    return f"AJ_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"


def _account_code_numeric(code: str) -> Optional[int]:
    if not code:
        return None
    digits = re.sub(r'\D', '', str(code))
    if not digits:
        return None
    try:
        return int(digits[:6])
    except ValueError:
        return None


def _gl_balance_source_label(source: Optional[str]) -> str:
    key = str(source or 'manual').strip().lower()
    if key in _GL_SOURCE_LABELS:
        return _GL_SOURCE_LABELS[key]
    return key.replace('_', ' ').title()


def _short_session_id(session_id: Optional[str]) -> str:
    sid = str(session_id or '').strip()
    if not sid:
        return '—'
    if len(sid) <= 12:
        return sid
    return f'{sid[:8]}…'


def _format_gl_sync_note(session_label: str, session_id: str, matched_lines: int) -> str:
    label = str(session_label or '').strip() or 'approved trial balance'
    lines = int(matched_lines)
    line_word = 'line' if lines == 1 else 'lines'
    return (
        f'Synced from {label} (session {_short_session_id(session_id)}) — '
        f'{lines} fixed-asset GL {line_word} (PPE, intangibles, investments).'
    )


def _row_net_balance(row: Dict[str, Any]) -> float:
    net = row.get('net_balance')
    if net is not None and float(net) != 0:
        return float(net)
    debit = float(row.get('debit_balance') or 0)
    credit = float(row.get('credit_balance') or 0)
    if debit or credit:
        return debit - credit
    period = row.get('period_1')
    if period is not None:
        return float(period)
    return 0.0


def _balance_sheet_row_to_gl_dict(row: Any) -> Dict[str, Any]:
    """Normalize a balance sheet data row for fixed-asset GL matching."""
    processed = getattr(row, 'processed_data', None) or {}
    raw = getattr(row, 'raw_data', None) or {}
    if not isinstance(processed, dict):
        processed = {}
    if not isinstance(raw, dict):
        raw = {}

    account_code = (
        getattr(row, 'account_code', '')
        or processed.get('account_code')
        or raw.get('account_code')
        or raw.get('Account Code')
        or ''
    )
    account_number = getattr(row, 'account_number', '') or processed.get('account_number') or ''
    account_description = (
        getattr(row, 'account_description', '')
        or processed.get('account_description')
        or raw.get('account_description')
        or raw.get('Account Description')
        or ''
    )
    grap_account_code = (
        processed.get('grap_account_code')
        or raw.get('grap_account_code')
        or ''
    )

    return {
        'account_code': str(account_code or '').strip(),
        'account_number': str(account_number or '').strip(),
        'account_description': str(account_description or '').strip(),
        'grap_account': getattr(row, 'grap_account', '') or processed.get('grap_account') or '',
        'grap_category': getattr(row, 'grap_category', '') or processed.get('grap_category') or '',
        'grap_subcategory': getattr(row, 'grap_subcategory', '') or processed.get('grap_subcategory') or '',
        'grap_account_code': str(grap_account_code or '').strip(),
        'net_balance': _row_net_balance({
            'net_balance': getattr(row, 'net_balance', None),
            'debit_balance': getattr(row, 'debit_balance', None),
            'credit_balance': getattr(row, 'credit_balance', None),
            'period_1': getattr(row, 'period_1', None),
        }),
    }


def _is_fixed_asset_account_row(row: Dict[str, Any]) -> bool:
    """True when a TB row maps to PPE / intangibles / investment property GL."""
    grap = str(row.get('grap_account') or '').strip().upper()
    grap_sub = str(row.get('grap_subcategory') or '').strip().upper()
    if grap in _PPE_GRAP_CODES | _INTANGIBLE_GRAP_CODES | _INVESTMENT_GRAP_CODES:
        return True
    if grap in _FIXED_ASSET_GRAP_LABELS:
        return True
    if grap and any(
        token in grap
        for token in ('PROPERTY, PLANT', 'INTANGIBLE ASSET', 'INVESTMENTS')
    ):
        if 'CURRENT' in grap_sub and 'NON-CURRENT' not in grap_sub:
            return False
        return True

    grap_code = str(row.get('grap_account_code') or '').strip()
    if grap_code in _FIXED_ASSET_GRAP_ACCOUNT_CODES:
        return True

    desc = str(row.get('account_description') or '').lower()
    if desc and any(keyword in desc for keyword in _FIXED_ASSET_DESC_KEYWORDS):
        return True

    num = _account_code_numeric(row.get('account_code') or row.get('account_number') or '')
    if num is None:
        return False

    # Municipal chart: 1600–1799 non-current assets; seed chart: 2100–2399 NCA block
    if (1600 <= num <= 1799) or (2100 <= num <= 2399):
        return True

    # Legacy municipal PPE control 1200–1299 — exclude receivables-style rows
    if 1200 <= num <= 1299:
        if grap and 'RECEIVABLE' in grap:
            return False
        if desc and any(token in desc for token in ('receivable', 'debtor', 'trade receivable')):
            return False
        if not grap and not desc:
            return True
        return any(keyword in desc for keyword in _FIXED_ASSET_DESC_KEYWORDS)

    return False


class AssetRegisterService:
    """Asset register with FM-queued asset journals (Supabase persistence)."""

    def __init__(self, model: Optional[AssetRegisterModel | InMemoryAssetRegisterModel] = None):
        self._lifecycle = AssetLifecycleModel()
        self._db_model = model if model is not None else get_asset_register_model()

    @property
    def uses_database(self) -> bool:
        return isinstance(self._db_model, AssetRegisterModel) and self._db_model.is_available()

    def _require_store(self) -> None:
        if not self._db_model.is_available():
            raise RuntimeError(
                'Asset register requires Supabase. Run scripts/create_asset_register_tables.sql '
                'and set SUPABASE_URL and SUPABASE_SECRET_KEY in .env.'
            )

    def _read_store(self) -> Dict[str, Any]:
        self._require_store()
        return self._db_model.load_store()

    def _write_store(self, store: Dict[str, Any]) -> None:
        self._require_store()
        self._db_model.save_store(store)

    def _sync_lifecycle_from_store(self, store: Dict[str, Any]) -> None:
        self._lifecycle.asset_register = dict(store.get('assets') or {})
        for asset_id, asset in self._lifecycle.asset_register.items():
            sched = (asset.get('depreciation_schedule') or {}) if isinstance(asset, dict) else {}
            if sched:
                self._lifecycle.depreciation_schedules[asset_id] = deepcopy(sched)
            elif asset_id not in self._lifecycle.depreciation_schedules:
                try:
                    self._lifecycle._initialize_depreciation_schedule(asset_id)
                except Exception:
                    pass

    def _snapshot_schedules_to_assets(self, store: Dict[str, Any]) -> None:
        assets = dict(self._lifecycle.asset_register)
        for asset_id, asset in assets.items():
            sched = self._lifecycle.depreciation_schedules.get(asset_id)
            if sched:
                asset['depreciation_schedule'] = deepcopy(sched)
        store['assets'] = assets

    def _with_store(self, mutator):
        with _LOCK:
            store = self._read_store()
            self._sync_lifecycle_from_store(store)
            result = mutator(store)
            self._snapshot_schedules_to_assets(store)
            self._write_store(store)
            return result

    def list_assets(self) -> List[Dict[str, Any]]:
        with _LOCK:
            store = self._read_store()
            self._sync_lifecycle_from_store(store)
            return self._lifecycle.list_assets()

    def get_asset(self, asset_id: str) -> Optional[Dict[str, Any]]:
        assets = self.list_assets()
        for asset in assets:
            if asset.get('asset_id') == asset_id:
                details = self._lifecycle.get_asset_details(asset_id)
                if details.get('error'):
                    return asset
                return {
                    **asset,
                    'depreciation_schedule': details.get('depreciation_schedule'),
                    'depreciation_history': details.get('depreciation_history'),
                }
        return None

    def register_asset(self, asset_data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        def mutate(store):
            payload = dict(asset_data or {})
            payload['created_by'] = user_id
            result = self._lifecycle.register_asset(payload)
            if not result.get('success'):
                return result
            return result

        return self._with_store(mutate)

    def create_useful_life_journal(
        self,
        asset_id: str,
        *,
        new_useful_life: int,
        reason: str,
        user_id: str,
        user_name: str = '',
        effective_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        def mutate(store):
            asset = self._lifecycle.asset_register.get(asset_id)
            if not asset:
                return {'success': False, 'error': 'Asset not found'}
            if asset.get('status') == 'disposed':
                return {'success': False, 'error': 'Cannot review useful life on a disposed asset'}

            eff = effective_date
            parsed_date = None
            if eff:
                try:
                    parsed_date = date.fromisoformat(str(eff)[:10])
                except ValueError:
                    return {'success': False, 'error': 'Invalid effective_date (use YYYY-MM-DD)'}

            category = self._lifecycle.asset_categories.get(asset.get('asset_category') or '')
            if category:
                min_l = category['useful_life_range']['min']
                max_l = category['useful_life_range']['max']
                if new_useful_life < min_l or new_useful_life > max_l:
                    return {
                        'success': False,
                        'error': f'Useful life must be between {min_l} and {max_l} years for this category',
                    }

            journal = {
                'journal_id': _journal_id(),
                'journal_type': 'useful_life_review',
                'asset_id': asset_id,
                'asset_name': asset.get('asset_name'),
                'status': JOURNAL_PENDING,
                'submitted_at': _now_iso(),
                'submitted_by': user_id,
                'submitter_name': user_name or user_id,
                'description': f'Useful life review: {asset.get("remaining_useful_life")} → {new_useful_life} years',
                'reason': str(reason or '').strip(),
                'amount': 0.0,
                'debit_account': None,
                'credit_account': None,
                'metadata': {
                    'new_useful_life': int(new_useful_life),
                    'old_useful_life': asset.get('remaining_useful_life'),
                    'effective_date': (parsed_date.isoformat() if parsed_date else None),
                    'grap_reference': 'GRAP 17.16 — Review of Useful Life',
                },
                'reviewed_at': None,
                'reviewed_by': None,
                'rejection_reason': None,
            }
            if not journal['reason']:
                return {'success': False, 'error': 'Reason is required for useful life review'}

            store.setdefault('journals', []).append(journal)
            return {'success': True, 'journal': journal, 'message': 'Useful life journal submitted for Finance Manager approval'}

        result = self._with_store(mutate)
        if result.get('success') and result.get('journal'):
            self._notify_journal_submitted(result['journal'], user_id)
        return result

    def create_impairment_journal(
        self,
        asset_id: str,
        *,
        impairment_amount: float,
        reason: str,
        user_id: str,
        user_name: str = '',
        recoverable_amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        def mutate(store):
            asset = self._lifecycle.asset_register.get(asset_id)
            if not asset:
                return {'success': False, 'error': 'Asset not found'}
            if asset.get('status') == 'disposed':
                return {'success': False, 'error': 'Cannot impair a disposed asset'}

            amount = float(impairment_amount or 0)
            carrying = float(asset.get('carrying_value') or 0)
            if amount <= 0:
                return {'success': False, 'error': 'Impairment amount must be greater than zero'}
            if amount > carrying:
                return {
                    'success': False,
                    'error': f'Impairment exceeds carrying value (R {carrying:,.2f})',
                }
            if not str(reason or '').strip():
                return {'success': False, 'error': 'Impairment reason is required'}

            journal = {
                'journal_id': _journal_id(),
                'journal_type': 'impairment',
                'asset_id': asset_id,
                'asset_name': asset.get('asset_name'),
                'status': JOURNAL_PENDING,
                'submitted_at': _now_iso(),
                'submitted_by': user_id,
                'submitter_name': user_name or user_id,
                'description': f'Impairment — R {amount:,.2f} on {asset.get("asset_name")}',
                'reason': str(reason).strip(),
                'amount': amount,
                'debit_account': 'Impairment loss (GRAP 17)',
                'credit_account': 'Accumulated impairment / PPE',
                'metadata': {
                    'impairment_amount': amount,
                    'carrying_value_before': carrying,
                    'recoverable_amount': recoverable_amount,
                    'grap_reference': 'GRAP 17 — Impairment of Assets',
                },
                'reviewed_at': None,
                'reviewed_by': None,
                'rejection_reason': None,
            }
            store.setdefault('journals', []).append(journal)
            return {'success': True, 'journal': journal, 'message': 'Impairment journal submitted for Finance Manager approval'}

        result = self._with_store(mutate)
        if result.get('success') and result.get('journal'):
            self._notify_journal_submitted(result['journal'], user_id)
        return result

    def create_disposal_journal(
        self,
        asset_id: str,
        *,
        disposal_proceeds: float,
        reason: str,
        user_id: str,
        user_name: str = '',
        disposal_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        def mutate(store):
            asset = self._lifecycle.asset_register.get(asset_id)
            if not asset:
                return {'success': False, 'error': 'Asset not found'}
            if asset.get('status') == 'disposed':
                return {'success': False, 'error': 'Asset is already disposed'}

            proceeds = float(disposal_proceeds or 0)
            carrying = float(asset.get('carrying_value') or 0)
            if proceeds < 0:
                return {'success': False, 'error': 'Disposal proceeds cannot be negative'}
            if not str(reason or '').strip():
                return {'success': False, 'error': 'Disposal reason is required'}

            parsed_date = None
            if disposal_date:
                try:
                    parsed_date = date.fromisoformat(str(disposal_date)[:10])
                except ValueError:
                    return {'success': False, 'error': 'Invalid disposal_date (use YYYY-MM-DD)'}

            gain_loss = proceeds - carrying
            journal = {
                'journal_id': _journal_id(),
                'journal_type': 'disposal',
                'asset_id': asset_id,
                'asset_name': asset.get('asset_name'),
                'status': JOURNAL_PENDING,
                'submitted_at': _now_iso(),
                'submitted_by': user_id,
                'submitter_name': user_name or user_id,
                'description': f'Disposal — {asset.get("asset_name")} (proceeds R {proceeds:,.2f})',
                'reason': str(reason).strip(),
                'amount': proceeds,
                'debit_account': 'Cash / receivable on disposal',
                'credit_account': 'PPE / accumulated depreciation',
                'metadata': {
                    'disposal_proceeds': proceeds,
                    'carrying_value_before': carrying,
                    'gain_loss_on_disposal': gain_loss,
                    'disposal_date': parsed_date.isoformat() if parsed_date else None,
                    'grap_reference': 'GRAP 17 — Derecognition of Assets',
                },
                'reviewed_at': None,
                'reviewed_by': None,
                'rejection_reason': None,
            }
            store.setdefault('journals', []).append(journal)
            return {'success': True, 'journal': journal, 'message': 'Disposal journal submitted for Finance Manager approval'}

        result = self._with_store(mutate)
        if result.get('success') and result.get('journal'):
            self._notify_journal_submitted(result['journal'], user_id)
        return result

    def process_annual_depreciation(self, fiscal_year: int, user_id: str = 'system') -> Dict[str, Any]:
        def mutate(store):
            result = self._lifecycle.process_annual_depreciation(int(fiscal_year))
            if result.get('errors') and not result.get('assets_processed'):
                return {'success': False, 'error': 'No depreciation processed', 'details': result}
            store['last_depreciation_run'] = {
                'fiscal_year': fiscal_year,
                'run_at': _now_iso(),
                'run_by': user_id,
                'total_depreciation': result.get('total_depreciation'),
                'assets_processed_count': len(result.get('assets_processed') or []),
            }
            return {
                'success': True,
                'depreciation_results': result,
                'message': f"Annual depreciation for {fiscal_year} applied to {len(result.get('assets_processed') or [])} asset(s)",
            }

        return self._with_store(mutate)

    def list_journals(
        self,
        *,
        status: Optional[str] = None,
        asset_id: Optional[str] = None,
        submitter_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        with _LOCK:
            store = self._read_store()
            journals = list(store.get('journals') or [])
        if status:
            journals = [j for j in journals if j.get('status') == status]
        if asset_id:
            journals = [j for j in journals if j.get('asset_id') == asset_id]
        if submitter_id:
            journals = [j for j in journals if str(j.get('submitted_by')) == str(submitter_id)]
        journals.sort(key=lambda j: j.get('submitted_at') or '', reverse=True)
        return journals

    @staticmethod
    def is_asset_journal_record(journal: Dict[str, Any]) -> bool:
        if not journal or not isinstance(journal, dict):
            return False
        if not journal.get('journal_id'):
            return False
        return (journal.get('journal_type') or '') in VALID_JOURNAL_TYPES

    def list_settled_journals(self, *, status_filter: str = 'all') -> List[Dict[str, Any]]:
        journals = self.list_journals()
        settled = [
            j for j in journals
            if j.get('status') in SETTLED_JOURNAL_STATUSES and self.is_asset_journal_record(j)
        ]
        if status_filter == 'approved':
            settled = [j for j in settled if j.get('status') == JOURNAL_APPROVED]
        elif status_filter == 'rejected':
            settled = [j for j in settled if j.get('status') == JOURNAL_REJECTED]
        settled.sort(key=lambda j: j.get('reviewed_at') or j.get('submitted_at') or '', reverse=True)
        return [self.enrich_journal_for_display(j) for j in settled]

    def enrich_journal_for_display(self, journal: Dict[str, Any]) -> Dict[str, Any]:
        row = dict(journal)
        meta = dict(row.get('metadata') or {})
        fm_forward = meta.get('fm_forward') if isinstance(meta.get('fm_forward'), dict) else None
        row['requires_cfo_escalation'] = bool(meta.get('requires_cfo') or requires_cfo_escalation(row))
        row['materiality_amount'] = journal_materiality_amount(row)
        row['materiality_threshold'] = materiality_threshold()
        row['escalation_reason'] = meta.get('escalation_reason') or (
            escalation_reason_label(row) if row['requires_cfo_escalation'] else ''
        )
        row['fm_forwarded_at'] = (fm_forward or {}).get('at')
        row['fm_reviewer_name'] = (fm_forward or {}).get('name')
        return row

    def list_pending_journals_for_role(self, role: str) -> List[Dict[str, Any]]:
        status = JOURNAL_PENDING_CFO if role == 'CFO' else JOURNAL_PENDING
        journals = [self.enrich_journal_for_display(j) for j in self.list_journals(status=status)]
        return [j for j in journals if self.is_asset_journal_record(j)]

    def count_pending_journals(self) -> int:
        return len(self.list_journals(status=JOURNAL_PENDING))

    def count_pending_cfo_journals(self) -> int:
        return len(self.list_journals(status=JOURNAL_PENDING_CFO))

    def count_pending_journals_for_user(self, user_id: str) -> int:
        pending = self.list_journals(status=JOURNAL_PENDING)
        uid = str(user_id)
        return len([j for j in pending if str(j.get('submitted_by') or '') == uid])

    def list_material_journal_audit_trail(self) -> List[Dict[str, Any]]:
        """CFO-approved material asset journals (disposals / material impairments) for auditor read-only trail."""
        settled = self.list_settled_journals(status_filter='approved')
        return [j for j in settled if j.get('requires_cfo_escalation')]

    def _notify_journal_submitted(self, journal: Dict[str, Any], submitter_id: str) -> None:
        try:
            from services.inbox_service import notify_asset_journal_pending_review

            notify_asset_journal_pending_review(
                journal_id=journal.get('journal_id', ''),
                journal_type=journal.get('journal_type', ''),
                asset_id=journal.get('asset_id', ''),
                asset_name=journal.get('asset_name') or '',
                submitter_id=submitter_id,
                submitter_name=journal.get('submitter_name') or '',
            )
        except Exception as exc:
            logger.warning('Could not notify FM of asset journal submission: %s', exc)

    def _notify_journal_forwarded_to_cfo(self, journal: Dict[str, Any], fm_reviewer_id: str, fm_reviewer_name: str) -> None:
        try:
            from services.inbox_service import (
                notify_asset_journal_forwarded_to_cfo,
                notify_asset_journal_pending_cfo,
            )

            notify_asset_journal_pending_cfo(
                journal_id=journal.get('journal_id', ''),
                journal_type=journal.get('journal_type', ''),
                asset_id=journal.get('asset_id', ''),
                asset_name=journal.get('asset_name') or '',
                fm_reviewer_id=fm_reviewer_id,
                fm_reviewer_name=fm_reviewer_name or '',
                escalation_reason=escalation_reason_label(journal),
            )
            notify_asset_journal_forwarded_to_cfo(
                journal.get('submitted_by'),
                journal_id=journal.get('journal_id', ''),
                journal_type=journal.get('journal_type', ''),
                asset_id=journal.get('asset_id', ''),
                asset_name=journal.get('asset_name') or '',
                fm_reviewer_name=fm_reviewer_name or '',
            )
        except Exception as exc:
            logger.warning('Could not notify CFO of asset journal escalation: %s', exc)

    def _notify_journal_approved(self, journal: Dict[str, Any], reviewer_id: str, reviewer_name: str) -> None:
        try:
            from services.inbox_service import notify_asset_journal_approved

            notify_asset_journal_approved(
                journal.get('submitted_by'),
                journal_id=journal.get('journal_id', ''),
                journal_type=journal.get('journal_type', ''),
                asset_id=journal.get('asset_id', ''),
                asset_name=journal.get('asset_name') or '',
                reviewer_id=reviewer_id,
                reviewer_name=reviewer_name,
            )
        except Exception as exc:
            logger.warning('Could not notify Asset Manager of journal approval: %s', exc)

    def _notify_journal_rejected(
        self,
        journal: Dict[str, Any],
        reviewer_id: str,
        reviewer_name: str,
        reason: str,
    ) -> None:
        try:
            from services.inbox_service import notify_asset_journal_rejected

            notify_asset_journal_rejected(
                journal.get('submitted_by'),
                journal_id=journal.get('journal_id', ''),
                journal_type=journal.get('journal_type', ''),
                asset_id=journal.get('asset_id', ''),
                asset_name=journal.get('asset_name') or '',
                reason=reason,
                reviewer_id=reviewer_id,
                reviewer_name=reviewer_name,
            )
        except Exception as exc:
            logger.warning('Could not notify Asset Manager of journal rejection: %s', exc)

    def get_journal(self, journal_id: str) -> Optional[Dict[str, Any]]:
        for journal in self.list_journals():
            if journal.get('journal_id') == journal_id:
                return journal
        return None

    def _apply_journal_to_register(self, journal: Dict[str, Any], reviewer_id: str) -> Dict[str, Any]:
        asset_id = journal.get('asset_id')
        jtype = journal.get('journal_type')

        if jtype == 'useful_life_review':
            meta = journal.get('metadata') or {}
            eff_raw = meta.get('effective_date')
            eff_date = None
            if eff_raw:
                try:
                    eff_date = date.fromisoformat(str(eff_raw)[:10])
                except ValueError:
                    eff_date = None
            return self._lifecycle.review_useful_life(
                asset_id,
                int(meta.get('new_useful_life')),
                journal.get('reason') or '',
                reviewer_id,
                effective_date=eff_date,
            )
        if jtype == 'impairment':
            meta = journal.get('metadata') or {}
            return self._lifecycle.record_impairment(
                asset_id,
                float(meta.get('impairment_amount') or journal.get('amount') or 0),
                journal.get('reason') or '',
                reviewer_id,
                recoverable_amount=meta.get('recoverable_amount'),
            )
        if jtype == 'disposal':
            meta = journal.get('metadata') or {}
            eff_raw = meta.get('disposal_date')
            disp_date = None
            if eff_raw:
                try:
                    disp_date = date.fromisoformat(str(eff_raw)[:10])
                except ValueError:
                    disp_date = None
            return self._lifecycle.dispose_asset(
                asset_id,
                disposal_proceeds=float(meta.get('disposal_proceeds') or journal.get('amount') or 0),
                reason=journal.get('reason') or '',
                user_id=reviewer_id,
                disposal_date=disp_date,
            )
        return {'success': False, 'error': f'Unknown journal type: {jtype}'}

    def approve_journal(
        self,
        journal_id: str,
        reviewer_id: str,
        reviewer_name: str = '',
        *,
        reviewer_role: str = 'FINANCE_MANAGER',
    ) -> Dict[str, Any]:
        role = (reviewer_role or '').upper()

        def mutate(store):
            journals = store.setdefault('journals', [])
            journal = next((j for j in journals if j.get('journal_id') == journal_id), None)
            if not journal:
                return {'success': False, 'error': 'Journal not found'}
            if not self.is_asset_journal_record(journal):
                return {'success': False, 'error': 'Invalid asset journal record'}

            status = journal.get('status')

            if status == JOURNAL_PENDING:
                if role != 'FINANCE_MANAGER':
                    return {
                        'success': False,
                        'error': 'Only the Finance Manager can approve at this stage',
                    }
                if requires_cfo_escalation(journal):
                    meta = dict(journal.get('metadata') or {})
                    meta['requires_cfo'] = True
                    meta['materiality_amount'] = journal_materiality_amount(journal)
                    meta['materiality_threshold'] = materiality_threshold()
                    meta['escalation_reason'] = escalation_reason_label(journal)
                    meta['fm_forward'] = {
                        'at': _now_iso(),
                        'by': reviewer_id,
                        'name': reviewer_name or reviewer_id,
                    }
                    journal['metadata'] = meta
                    journal['status'] = JOURNAL_PENDING_CFO
                    return {
                        'success': True,
                        'journal': journal,
                        'forwarded_to_cfo': True,
                        'message': 'Journal forwarded to CFO for materiality sign-off',
                    }

                result = self._apply_journal_to_register(journal, reviewer_id)
                if not result.get('success'):
                    return result

                journal['status'] = JOURNAL_APPROVED
                journal['reviewed_at'] = _now_iso()
                journal['reviewed_by'] = reviewer_id
                journal['reviewer_name'] = reviewer_name or reviewer_id
                return {
                    'success': True,
                    'journal': journal,
                    'application_result': result,
                    'message': 'Asset journal approved and applied to the register',
                }

            if status == JOURNAL_PENDING_CFO:
                if role != 'CFO':
                    return {
                        'success': False,
                        'error': 'Only the CFO can give final approval on material asset journals',
                    }
                result = self._apply_journal_to_register(journal, reviewer_id)
                if not result.get('success'):
                    return result

                journal['status'] = JOURNAL_APPROVED
                journal['reviewed_at'] = _now_iso()
                journal['reviewed_by'] = reviewer_id
                journal['reviewer_name'] = reviewer_name or reviewer_id
                meta = dict(journal.get('metadata') or {})
                meta['cfo_final_approval'] = {
                    'at': journal['reviewed_at'],
                    'by': reviewer_id,
                    'name': reviewer_name or reviewer_id,
                }
                journal['metadata'] = meta
                return {
                    'success': True,
                    'journal': journal,
                    'application_result': result,
                    'message': 'Asset journal approved by CFO and applied to the register',
                }

            return {'success': False, 'error': f'Journal is not pending review (status: {status})'}

        outcome = self._with_store(mutate)
        if not outcome.get('success') or not outcome.get('journal'):
            return outcome

        journal = outcome['journal']
        if outcome.get('forwarded_to_cfo'):
            self._notify_journal_forwarded_to_cfo(journal, reviewer_id, reviewer_name)
        else:
            self._notify_journal_approved(journal, reviewer_id, reviewer_name)
        return outcome

    def reject_journal(
        self,
        journal_id: str,
        reviewer_id: str,
        reason: str,
        reviewer_name: str = '',
        *,
        reviewer_role: str = 'FINANCE_MANAGER',
    ) -> Dict[str, Any]:
        role = (reviewer_role or '').upper()

        def mutate(store):
            if not str(reason or '').strip():
                return {'success': False, 'error': 'Rejection reason is required'}
            journals = store.setdefault('journals', [])
            journal = next((j for j in journals if j.get('journal_id') == journal_id), None)
            if not journal:
                return {'success': False, 'error': 'Journal not found'}
            if not self.is_asset_journal_record(journal):
                return {'success': False, 'error': 'Invalid asset journal record'}

            status = journal.get('status')
            if status == JOURNAL_PENDING:
                if role != 'FINANCE_MANAGER':
                    return {'success': False, 'error': 'Only the Finance Manager can reject at this stage'}
            elif status == JOURNAL_PENDING_CFO:
                if role != 'CFO':
                    return {'success': False, 'error': 'Only the CFO can reject at this stage'}
            else:
                return {'success': False, 'error': f'Journal is not pending review (status: {status})'}

            journal['status'] = JOURNAL_REJECTED
            journal['reviewed_at'] = _now_iso()
            journal['reviewed_by'] = reviewer_id
            journal['reviewer_name'] = reviewer_name or reviewer_id
            journal['rejection_reason'] = str(reason).strip()
            return {'success': True, 'journal': journal, 'message': 'Asset journal rejected'}

        outcome = self._with_store(mutate)
        if outcome.get('success') and outcome.get('journal'):
            self._notify_journal_rejected(outcome['journal'], reviewer_id, reviewer_name, reason)
        return outcome

    def get_reconciliation(self) -> Dict[str, Any]:
        with _LOCK:
            store = self._read_store()
            self._sync_lifecycle_from_store(store)
            summary = self._lifecycle._calculate_asset_summary()

        register_total = float(summary.get('total_carrying_value') or 0)
        gl_total = float(store.get('gl_ppe_control_balance') or 0)
        variance = register_total - gl_total
        tolerance = max(1.0, gl_total * 0.001) if gl_total else 1.0
        reconciled = abs(variance) <= tolerance

        return {
            'success': True,
            'register_total_carrying_value': register_total,
            'register_total_cost': float(summary.get('total_purchase_cost') or 0),
            'register_asset_count': int(summary.get('total_assets') or 0),
            'gl_ppe_control_balance': gl_total,
            'gl_balance_note': store.get('gl_balance_note') or '',
            'gl_balance_updated_at': store.get('gl_balance_updated_at'),
            'gl_balance_source': store.get('gl_balance_source') or 'manual',
            'gl_balance_source_label': _gl_balance_source_label(store.get('gl_balance_source')),
            'gl_balance_session_id': store.get('gl_balance_session_id'),
            'variance': variance,
            'reconciled': reconciled,
            'tolerance': tolerance,
            'grap_reference': 'GRAP 17 — Asset register reconciliation to general ledger',
            'persistence': 'supabase',
        }

    def update_gl_balance_manual(
        self,
        balance: float,
        *,
        note: str = '',
        user_id: str = '',
    ) -> Dict[str, Any]:
        def mutate(store):
            store['gl_ppe_control_balance'] = float(balance)
            note_text = str(note or '').strip()
            store['gl_balance_note'] = note_text or 'Manual GL balance override'
            store['gl_balance_updated_at'] = _now_iso()
            store['gl_balance_source'] = 'manual'
            store['gl_balance_session_id'] = None
            store['gl_balance_updated_by'] = user_id
            return {'success': True, 'message': 'GL balance updated', 'balance': float(balance)}

        return self._with_store(mutate)

    def _resolve_balance_sheet_session(
        self,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            from models.balance_sheet_models import balance_sheet_model
        except Exception as exc:
            return {'success': False, 'error': f'Balance sheet model unavailable: {exc}'}

        session = None
        if session_id:
            session = balance_sheet_model.get_session(session_id)
            if not session:
                return {'success': False, 'error': 'Balance sheet session not found'}
        else:
            for status in ('approved', 'finalized', 'approved_by_manager'):
                sessions = balance_sheet_model.get_sessions_by_status(status, limit=5)
                if sessions:
                    session = sessions[0]
                    break
            if not session:
                return {
                    'success': False,
                    'error': 'No approved or finalized balance sheet session found. Upload and approve a trial balance first.',
                }

        return {'success': True, 'session': session, 'balance_sheet_model': balance_sheet_model}

    def compute_gl_sync_from_trial_balance(
        self,
        *,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Preview fixed-asset GL total from an approved balance-sheet session (no write)."""
        resolved = self._resolve_balance_sheet_session(session_id)
        if not resolved.get('success'):
            return resolved

        session = resolved['session']
        balance_sheet_model = resolved['balance_sheet_model']
        sid = session.id
        rows = balance_sheet_model.get_session_data(sid, limit=5000)

        proposed_total = 0.0
        matched_lines = 0
        for row in rows:
            row_dict = _balance_sheet_row_to_gl_dict(row)
            if _is_fixed_asset_account_row(row_dict):
                proposed_total += abs(row_dict['net_balance'])
                matched_lines += 1

        with _LOCK:
            store = self._read_store()
            current_balance = float(store.get('gl_ppe_control_balance') or 0)
            current_session_id = store.get('gl_balance_session_id')
            current_source = store.get('gl_balance_source') or 'manual'

        balance_delta = proposed_total - current_balance
        same_session = str(current_session_id or '') == str(sid)
        already_synced = (
            matched_lines > 0
            and same_session
            and current_source == 'trial_balance'
            and abs(balance_delta) < 0.005
        )
        would_change = matched_lines > 0 and not already_synced

        session_label = (
            getattr(session, 'original_filename', None)
            or getattr(session, 'filename', None)
            or str(sid)[:8]
        )

        return {
            'success': True,
            'session_id': sid,
            'session_label': session_label,
            'current_gl_balance': current_balance,
            'proposed_gl_balance': proposed_total,
            'balance_delta': balance_delta,
            'matched_lines': matched_lines,
            'would_change': would_change,
            'already_synced': already_synced,
            'current_session_id': current_session_id,
            'current_source': current_source,
        }

    def preview_gl_sync_from_trial_balance(
        self,
        *,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        return self.compute_gl_sync_from_trial_balance(session_id=session_id)

    def sync_gl_from_trial_balance(
        self,
        *,
        session_id: Optional[str] = None,
        user_id: str = '',
    ) -> Dict[str, Any]:
        """Sum fixed-asset GL lines from an approved balance-sheet session."""
        preview = self.compute_gl_sync_from_trial_balance(session_id=session_id)
        if not preview.get('success'):
            return preview

        sid = preview['session_id']
        gl_total = float(preview['proposed_gl_balance'])
        matched_lines = int(preview['matched_lines'])

        if preview.get('already_synced'):
            return {
                'success': True,
                'no_change': True,
                'message': 'GL balance already matches the latest approved trial balance (no changes).',
                'gl_ppe_control_balance': gl_total,
                'matched_lines': matched_lines,
                'session_id': sid,
            }

        note = _format_gl_sync_note(
            preview.get('session_label') or '',
            sid,
            matched_lines,
        )

        def mutate(store):
            store['gl_ppe_control_balance'] = gl_total
            store['gl_balance_note'] = note
            store['gl_balance_updated_at'] = _now_iso()
            store['gl_balance_source'] = 'trial_balance'
            store['gl_balance_session_id'] = sid
            store['gl_balance_updated_by'] = user_id
            message = 'GL balance synced from trial balance'
            if matched_lines == 0:
                message = (
                    'Sync completed but no fixed-asset GL lines matched. '
                    'Ensure PPE accounts are mapped in the balance sheet session, or use manual override.'
                )
            else:
                message = f'GL balance synced from trial balance ({matched_lines} fixed-asset line(s))'

            return {
                'success': True,
                'message': message,
                'gl_ppe_control_balance': gl_total,
                'matched_lines': matched_lines,
                'session_id': sid,
            }

        return self._with_store(mutate)

    def get_dashboard_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        recon = self.get_reconciliation()
        pending = self.list_journals(status=JOURNAL_PENDING)
        my_pending = [j for j in pending if not user_id or str(j.get('submitted_by')) == str(user_id)]
        assets = self.list_assets()
        active = [a for a in assets if a.get('status') not in ('disposed',)]
        return {
            'success': True,
            'asset_count': len(assets),
            'active_asset_count': len(active),
            'total_carrying_value': recon.get('register_total_carrying_value', 0),
            'total_purchase_cost': recon.get('register_total_cost', 0),
            'pending_journals_total': len(pending),
            'pending_journals_mine': len(my_pending),
            'reconciled': recon.get('reconciled', False),
            'variance': recon.get('variance', 0),
            'gl_balance': recon.get('gl_ppe_control_balance', 0),
            'gl_balance_source': recon.get('gl_balance_source'),
            'gl_balance_source_label': recon.get('gl_balance_source_label'),
            'persistence': recon.get('persistence'),
        }

    def generate_register_report(self) -> Dict[str, Any]:
        with _LOCK:
            store = self._read_store()
            self._sync_lifecycle_from_store(store)
        return self._lifecycle.generate_asset_register_report()

    def export_register_csv(self) -> str:
        report = self.generate_register_report()
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(['GRAP 17 Asset Register Export', report.get('generated_at', '')])
        writer.writerow([])
        summary = report.get('summary') or {}
        writer.writerow(['Summary'])
        writer.writerow(['Total assets', summary.get('total_assets', 0)])
        writer.writerow(['Total purchase cost', summary.get('total_purchase_cost', 0)])
        writer.writerow(['Total carrying value', summary.get('total_carrying_value', 0)])
        writer.writerow([])
        writer.writerow([
            'Asset ID', 'Name', 'Category', 'Status', 'Purchase cost',
            'Accumulated depreciation', 'Carrying value', 'Remaining life (years)',
        ])
        for row in report.get('asset_details') or []:
            writer.writerow([
                row.get('asset_id'),
                row.get('asset_name'),
                row.get('category'),
                row.get('status'),
                row.get('purchase_cost'),
                row.get('accumulated_depreciation'),
                row.get('carrying_value'),
                row.get('remaining_useful_life'),
            ])
        return buf.getvalue()

    def seed_demo_assets_if_empty(self, user_id: str = 'system') -> bool:
        if self.list_assets():
            return False

        samples = [
            {
                'asset_name': 'Municipal fleet vehicle — Toyota Hilux',
                'asset_category': 'property_plant_equipment',
                'purchase_date': '2022-04-01',
                'purchase_cost': 485_000,
                'residual_value': 48_500,
                'useful_life_years': 8,
            },
            {
                'asset_name': 'Office building — Main administration block',
                'asset_category': 'property_plant_equipment',
                'purchase_date': '2018-07-01',
                'purchase_cost': 12_500_000,
                'residual_value': 0,
                'useful_life_years': 40,
            },
            {
                'asset_name': 'Accounting software licence',
                'asset_category': 'intangible_assets',
                'purchase_date': '2024-01-15',
                'purchase_cost': 185_000,
                'residual_value': 0,
                'useful_life_years': 5,
            },
        ]
        for sample in samples:
            self.register_asset(sample, user_id)
        return True


asset_register_service = AssetRegisterService()
