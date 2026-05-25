"""
Supabase persistence for GRAP 17 asset register (assets, journals, GL balances).
"""

from __future__ import annotations

import logging
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

ASSETS_TABLE = 'assets'
JOURNALS_TABLE = 'asset_journals'
GL_BALANCES_TABLE = 'asset_gl_balances'


def _float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _int(val: Any, default: int = 0) -> int:
    if val is None:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _iso(val: Any) -> Optional[str]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.isoformat()
    return str(val)


class AssetRegisterModel:
    """Load/save asset register store via Supabase (service role)."""

    def __init__(self):
        self._client = None
        self._client_checked = False

    @property
    def client(self):
        if not self._client_checked:
            self._client_checked = True
            try:
                from utils.supabase_client import create_admin_supabase_client

                self._client = create_admin_supabase_client()
            except Exception as exc:
                logger.debug('Asset register Supabase client unavailable: %s', exc)
                self._client = None
        return self._client

    def is_available(self) -> bool:
        return self.client is not None

    def is_empty(self) -> bool:
        if not self.is_available():
            return True
        try:
            assets = self.client.table(ASSETS_TABLE).select('asset_id', count='exact').limit(1).execute()
            count = getattr(assets, 'count', None)
            if count is not None:
                return count == 0
            return not (assets.data or [])
        except Exception as exc:
            logger.warning('Could not probe assets table: %s', exc)
            return True

    def _asset_row_to_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'asset_id': row.get('asset_id'),
            'asset_name': row.get('asset_name'),
            'asset_category': row.get('asset_category'),
            'category_details': row.get('category_details') or {},
            'purchase_date': str(row.get('purchase_date') or '')[:10],
            'purchase_cost': _float(row.get('purchase_cost')),
            'residual_value': _float(row.get('residual_value')),
            'useful_life_years': _int(row.get('useful_life_years')),
            'remaining_useful_life': _int(row.get('remaining_useful_life')),
            'depreciation_method': row.get('depreciation_method') or 'straight_line',
            'depreciation_start_date': str(row.get('depreciation_start_date') or row.get('purchase_date') or '')[:10],
            'carrying_value': _float(row.get('carrying_value')),
            'accumulated_depreciation': _float(row.get('accumulated_depreciation')),
            'status': row.get('status') or 'active',
            'created_at': _iso(row.get('created_at')),
            'created_by': row.get('created_by'),
            'last_reviewed': _iso(row.get('last_reviewed')),
            'review_history': row.get('review_history') or [],
            'impairment_history': row.get('impairment_history') or [],
            'disposal_history': row.get('disposal_history') or [],
            'depreciation_schedule': row.get('depreciation_schedule') or {},
        }

    def _asset_dict_to_row(self, asset: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'asset_id': asset.get('asset_id'),
            'asset_name': asset.get('asset_name'),
            'asset_category': asset.get('asset_category'),
            'category_details': asset.get('category_details') or {},
            'purchase_date': str(asset.get('purchase_date') or '')[:10],
            'purchase_cost': _float(asset.get('purchase_cost')),
            'residual_value': _float(asset.get('residual_value')),
            'useful_life_years': _int(asset.get('useful_life_years')),
            'remaining_useful_life': _int(asset.get('remaining_useful_life')),
            'depreciation_method': asset.get('depreciation_method') or 'straight_line',
            'depreciation_start_date': str(
                asset.get('depreciation_start_date') or asset.get('purchase_date') or ''
            )[:10],
            'carrying_value': _float(asset.get('carrying_value')),
            'accumulated_depreciation': _float(asset.get('accumulated_depreciation')),
            'status': asset.get('status') or 'active',
            'review_history': asset.get('review_history') or [],
            'impairment_history': asset.get('impairment_history') or [],
            'disposal_history': asset.get('disposal_history') or [],
            'depreciation_schedule': asset.get('depreciation_schedule') or {},
            'created_by': asset.get('created_by'),
            'created_at': asset.get('created_at') or datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'last_reviewed': asset.get('last_reviewed'),
        }

    def _journal_row_to_dict(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'journal_id': row.get('journal_id'),
            'journal_type': row.get('journal_type'),
            'asset_id': row.get('asset_id'),
            'asset_name': row.get('asset_name'),
            'status': row.get('status'),
            'description': row.get('description'),
            'reason': row.get('reason'),
            'amount': _float(row.get('amount')),
            'debit_account': row.get('debit_account'),
            'credit_account': row.get('credit_account'),
            'metadata': row.get('metadata') or {},
            'submitted_at': _iso(row.get('submitted_at')),
            'submitted_by': row.get('submitted_by'),
            'submitter_name': row.get('submitter_name'),
            'reviewed_at': _iso(row.get('reviewed_at')),
            'reviewed_by': row.get('reviewed_by'),
            'reviewer_name': row.get('reviewer_name'),
            'rejection_reason': row.get('rejection_reason'),
        }

    def _journal_dict_to_row(self, journal: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'journal_id': journal.get('journal_id'),
            'journal_type': journal.get('journal_type'),
            'asset_id': journal.get('asset_id'),
            'asset_name': journal.get('asset_name'),
            'status': journal.get('status'),
            'description': journal.get('description'),
            'reason': journal.get('reason'),
            'amount': _float(journal.get('amount')),
            'debit_account': journal.get('debit_account'),
            'credit_account': journal.get('credit_account'),
            'metadata': journal.get('metadata') or {},
            'submitted_at': journal.get('submitted_at') or datetime.now().isoformat(),
            'submitted_by': journal.get('submitted_by'),
            'submitter_name': journal.get('submitter_name'),
            'reviewed_at': journal.get('reviewed_at'),
            'reviewed_by': journal.get('reviewed_by'),
            'reviewer_name': journal.get('reviewer_name'),
            'rejection_reason': journal.get('rejection_reason'),
        }

    def load_store(self) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError('Supabase asset register unavailable')

        assets_result = self.client.table(ASSETS_TABLE).select('*').execute()
        assets: Dict[str, Any] = {}
        for row in assets_result.data or []:
            asset = self._asset_row_to_dict(row)
            assets[asset['asset_id']] = asset

        journals_result = (
            self.client.table(JOURNALS_TABLE).select('*').order('submitted_at', desc=True).execute()
        )
        journals = [self._journal_row_to_dict(row) for row in (journals_result.data or [])]

        gl_row = self._get_current_gl_balance_row()
        gl_balance = _float(gl_row.get('balance')) if gl_row else 0.0
        gl_note = (gl_row or {}).get('note') or ''
        gl_updated = _iso((gl_row or {}).get('updated_at'))
        gl_source = (gl_row or {}).get('source') or 'manual'
        gl_session = (gl_row or {}).get('source_session_id')

        return {
            'version': 1,
            'gl_ppe_control_balance': gl_balance,
            'gl_balance_note': gl_note,
            'gl_balance_updated_at': gl_updated,
            'gl_balance_source': gl_source,
            'gl_balance_session_id': gl_session,
            'assets': assets,
            'journals': journals,
        }

    def _get_current_gl_balance_row(self) -> Optional[Dict[str, Any]]:
        try:
            result = (
                self.client.table(GL_BALANCES_TABLE)
                .select('*')
                .eq('is_current', True)
                .is_('period_id', 'null')
                .order('updated_at', desc=True)
                .limit(1)
                .execute()
            )
            rows = result.data or []
            return rows[0] if rows else None
        except Exception as exc:
            logger.warning('Could not load GL balance: %s', exc)
            return None

    def save_store(self, store: Dict[str, Any]) -> None:
        if not self.is_available():
            raise RuntimeError('Supabase asset register unavailable')

        assets = store.get('assets') or {}
        for asset_id, asset in assets.items():
            row = self._asset_dict_to_row({**asset, 'asset_id': asset_id})
            self.client.table(ASSETS_TABLE).upsert(row, on_conflict='asset_id').execute()

        journals = store.get('journals') or []
        for journal in journals:
            row = self._journal_dict_to_row(journal)
            self.client.table(JOURNALS_TABLE).upsert(row, on_conflict='journal_id').execute()

        gl_balance = store.get('gl_ppe_control_balance')
        if gl_balance is not None:
            self.set_gl_balance(
                _float(gl_balance),
                note=store.get('gl_balance_note') or '',
                source=store.get('gl_balance_source') or 'manual',
                source_session_id=store.get('gl_balance_session_id'),
                updated_by=store.get('gl_balance_updated_by'),
            )

    def set_gl_balance(
        self,
        balance: float,
        *,
        note: str = '',
        source: str = 'manual',
        source_session_id: Optional[str] = None,
        updated_by: Optional[str] = None,
        period_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError('Supabase asset register unavailable')

        try:
            self.client.table(GL_BALANCES_TABLE).update({'is_current': False}).eq(
                'is_current', True
            ).is_('period_id', 'null').execute()
        except Exception:
            pass

        row = {
            'gl_account_range': '1200-1799',
            'balance': balance,
            'note': note,
            'source': source,
            'source_session_id': source_session_id,
            'updated_by': updated_by,
            'updated_at': datetime.now().isoformat(),
            'is_current': True,
            'period_id': period_id,
        }
        result = self.client.table(GL_BALANCES_TABLE).insert(row).execute()
        return (result.data or [row])[0]

    def import_store(self, store: Dict[str, Any]) -> None:
        """One-time import from JSON file store."""
        self.save_store(store)

    def upsert_asset(self, asset: Dict[str, Any]) -> None:
        if not self.is_available():
            return
        row = self._asset_dict_to_row(asset)
        self.client.table(ASSETS_TABLE).upsert(row, on_conflict='asset_id').execute()

    def upsert_journal(self, journal: Dict[str, Any]) -> None:
        if not self.is_available():
            return
        row = self._journal_dict_to_row(journal)
        self.client.table(JOURNALS_TABLE).upsert(row, on_conflict='journal_id').execute()


def _empty_store() -> Dict[str, Any]:
    return {
        'version': 1,
        'gl_ppe_control_balance': 0.0,
        'gl_balance_note': '',
        'gl_balance_updated_at': None,
        'gl_balance_source': 'manual',
        'gl_balance_session_id': None,
        'assets': {},
        'journals': [],
    }


class InMemoryAssetRegisterModel:
    """In-process store for unit tests (same interface as AssetRegisterModel)."""

    def __init__(self, initial: Optional[Dict[str, Any]] = None):
        self._store = deepcopy(initial) if initial else _empty_store()

    def is_available(self) -> bool:
        return True

    def is_empty(self) -> bool:
        store = self._store
        return not (store.get('assets') or store.get('journals'))

    def load_store(self) -> Dict[str, Any]:
        return deepcopy(self._store)

    def save_store(self, store: Dict[str, Any]) -> None:
        self._store = deepcopy(store)

    def set_gl_balance(
        self,
        balance: float,
        *,
        note: str = '',
        source: str = 'manual',
        source_session_id: Optional[str] = None,
        updated_by: Optional[str] = None,
        period_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        self._store['gl_ppe_control_balance'] = balance
        self._store['gl_balance_note'] = note
        self._store['gl_balance_source'] = source
        self._store['gl_balance_session_id'] = source_session_id
        self._store['gl_balance_updated_at'] = datetime.now().isoformat()
        self._store['gl_balance_updated_by'] = updated_by
        return {'balance': balance, 'period_id': period_id}

    def import_store(self, store: Dict[str, Any]) -> None:
        self.save_store(store)


_asset_register_model: Optional[AssetRegisterModel] = None


def get_asset_register_model() -> AssetRegisterModel:
    global _asset_register_model
    if _asset_register_model is None:
        _asset_register_model = AssetRegisterModel()
    return _asset_register_model
