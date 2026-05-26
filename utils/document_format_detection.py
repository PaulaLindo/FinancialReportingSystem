"""
Detect whether an uploaded file matches the document type selected in the UI.
"""

from __future__ import annotations

import os
import re
from typing import Any, Iterable, List, Optional

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    pd = None

DOCUMENT_TYPE_LABELS = {
    'balance_sheet': 'Balance Sheet',
    'budget_report': 'Budget Report',
    'income_statement': 'Income Statement',
}


def document_type_label(document_type: Optional[str]) -> str:
    """Human-readable document name for errors and UI (no snake_case)."""
    key = (document_type or '').strip().lower()
    if key in DOCUMENT_TYPE_LABELS:
        return DOCUMENT_TYPE_LABELS[key]
    if not key:
        return 'Document'
    return key.replace('_', ' ').title()


def _normalize_column_names(column_names: Iterable[str]) -> list[str]:
    return [str(name).strip().lower() for name in column_names if name]


def _column_matches(names: list[str], keywords: tuple[str, ...]) -> bool:
    return any(any(keyword in name for keyword in keywords) for name in names)


def infer_document_format_from_columns(column_names: Iterable[str]) -> Optional[str]:
    """
    Infer the most likely document type from header / column names.
    Returns None when the format is ambiguous.
    """
    names = _normalize_column_names(column_names)
    if not names:
        return None

    has_budget = _column_matches(
        names, ('budget', 'planned', 'projected', 'forecast', 'allocation', 'target amount')
    )
    has_actual = _column_matches(
        names, ('actual', 'spent', 'incurred', 'achieved', 'real amount')
    )
    has_variance = _column_matches(names, ('variance', 'deviation', 'delta'))
    has_debit = _column_matches(names, ('debit', ' dr', 'debit balance', 'debit amt'))
    has_credit = _column_matches(names, ('credit', ' cr', 'credit balance', 'credit amt'))
    has_net_balance = _column_matches(names, ('net balance', 'net_balance')) or any(
        name == 'balance' for name in names
    )
    has_revenue = _column_matches(
        names, ('revenue', 'income', 'sales', 'turnover', 'fees earned')
    )
    has_expense = _column_matches(
        names, ('expense', 'expenditure', 'cost of sales', 'operating cost')
    )

    if has_budget and (has_actual or has_variance):
        return 'budget_report'

    if has_revenue and has_expense:
        return 'income_statement'

    if (has_debit or has_credit or has_net_balance) and not (has_budget and has_actual):
        return 'balance_sheet'

    return None


def column_names_from_data_rows(data_rows: Iterable[Any]) -> list[str]:
    """Collect column names from the first row's raw_data / processed_data."""
    import json

    for row in data_rows:
        for attr in ('raw_data', 'processed_data'):
            source = getattr(row, attr, None)
            if source is None:
                continue
            if isinstance(source, str):
                try:
                    source = json.loads(source)
                except (json.JSONDecodeError, TypeError):
                    continue
            if isinstance(source, dict) and source:
                return [str(key) for key in source.keys()]
    return []


def peek_file_column_names(file_path: str) -> List[str]:
    """Read column headers from a CSV/Excel file without full processing."""
    if not file_path or not os.path.isfile(file_path):
        return []
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if pd is None:
            return []
        if ext == '.csv':
            df = pd.read_csv(file_path, nrows=0)
        elif ext == '.tsv':
            df = pd.read_csv(file_path, sep='\t', nrows=0)
        elif ext in ('.xlsx', '.xlsm', '.xlsb'):
            df = pd.read_excel(file_path, nrows=0, engine='openpyxl')
        elif ext == '.xls':
            df = pd.read_excel(file_path, nrows=0)
        else:
            return []
        return [str(col).strip() for col in df.columns if str(col).strip()]
    except Exception:
        return []


def infer_document_format_from_filename(filename: str) -> Optional[str]:
    """Weak hint from filename when column headers are inconclusive."""
    if not filename:
        return None
    name = filename.lower().replace('-', '_').replace(' ', '_')
    if 'budget' in name and 'report' in name:
        return 'budget_report'
    if 'income' in name and 'statement' in name:
        return 'income_statement'
    if 'trial' in name and 'balance' in name:
        return 'balance_sheet'
    if 'balance' in name and 'sheet' in name:
        return 'balance_sheet'
    if name.endswith('_budget.csv') or '_budget.' in name:
        return 'budget_report'
    return None


def column_names_from_upload_result(upload_result: dict) -> list[str]:
    """Extract original column names from upload service results."""
    file_columns = upload_result.get('file_columns') or []
    if file_columns:
        return [str(col) for col in file_columns]

    names: list[str] = []

    structure = upload_result.get('structure_info') or {}
    structure_mapping = structure.get('column_mapping') or {}
    for entry in structure_mapping.values():
        if isinstance(entry, dict):
            original = entry.get('original_name')
            if original:
                names.append(str(original))

    flat_mapping = upload_result.get('column_mapping') or {}
    for value in flat_mapping.values():
        if isinstance(value, str) and value.strip():
            names.append(value.strip())

    if names:
        return names

    columns = upload_result.get('columns') or []
    for col in columns:
        if isinstance(col, dict):
            name = col.get('column_name') or col.get('original_column_name')
            if name:
                names.append(str(name))
    return names


def document_type_mismatch_message(selected: str, detected: str) -> str:
    selected_label = DOCUMENT_TYPE_LABELS.get(
        selected, selected.replace('_', ' ').title()
    )
    detected_label = DOCUMENT_TYPE_LABELS.get(
        detected, detected.replace('_', ' ').title()
    )
    return (
        f'This file looks like a {detected_label}, but you selected {selected_label}. '
        f'Please choose {detected_label} as the document type above, '
        f'or upload a file that matches {selected_label}.'
    )


def resolve_document_type_mismatch(
    selected_document_type: str,
    column_names: Iterable[str],
    balance_results: Optional[dict] = None,
    filename: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """
    Return (detected_type, user_message) when selected type does not match the file.
    """
    detected = infer_document_format_from_columns(column_names)

    if not detected and filename:
        detected = infer_document_format_from_filename(filename)

    if not detected and balance_results:
        balance_type = balance_results.get('balance_type')
        if balance_type == 'budget_vs_actual' and selected_document_type == 'balance_sheet':
            detected = 'budget_report'
        elif balance_type == 'debits_vs_credits' and selected_document_type == 'budget_report':
            detected = 'balance_sheet'

    if detected and detected != selected_document_type:
        return detected, document_type_mismatch_message(selected_document_type, detected)

    return None, None
