#!/usr/bin/env python3
"""CLI: verify CFO period-lock Supabase migrations (registry + is_locked column probe)."""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

try:
    from dotenv import load_dotenv

    load_dotenv(os.path.join(ROOT, ".env"))
except ImportError:
    pass


def main() -> int:
    from services.schema_migration_service import check_cfo_period_lock_migrations

    report = check_cfo_period_lock_migrations()
    print(json.dumps(report, indent=2))

    if not report.get("success"):
        print("\n❌ Could not connect to Supabase.", file=sys.stderr)
        return 2

    if report.get("all_applied"):
        print("\n✅ All CFO period-lock migrations are registered and schema probes passed.")
        return 0

    print("\n⚠️  Migrations incomplete. Run in Supabase SQL Editor:", file=sys.stderr)
    print("   1. scripts/add_period_lock_and_variance_explanations.sql", file=sys.stderr)
    print("   2. scripts/enable_financial_periods_cfo_lock_rls.sql", file=sys.stderr)
    print("   (or scripts/consolidate_financial_periods_rls.sql if RLS already partially applied)", file=sys.stderr)
    print("   Then: scripts/verify_supabase_cfo_migrations.sql", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
