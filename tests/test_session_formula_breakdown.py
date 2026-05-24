"""Formula breakdown aligns with GRAP approval calculations."""

from services.session_formula_breakdown import compute_calculations_from_summary


def test_breakdown_includes_grap_mapped_equation():
    summary = {
        "document_type": "balance_sheet",
        "session_id": "sess-1",
        "metadata": {
            "mapped_data": [
                {"account_code": "1001", "grap_code": "CA100", "net_balance": 25000},
                {"account_code": "2001", "grap_code": "CL200", "net_balance": -18000},
                {"account_code": "3001", "grap_code": "EQ300", "net_balance": -7000},
                {"account_code": "5001", "grap_code": "CA130", "net_balance": 45000},
            ],
        },
    }
    calcs = compute_calculations_from_summary(summary)
    by_id = {c["id"]: c for c in calcs}
    assert "grap-mapped-assets" in by_id
    assert "grap-mapped-diff" in by_id
    assert by_id["grap-mapped-assets"]["result"] == 25000
    assert by_id["grap-mapped-diff"]["result"] == 0
    assert by_id["grap-mapped-diff"]["verified"] is True
