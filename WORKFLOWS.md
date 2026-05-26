# Approval workflows — Finance Clerk, Finance Manager & CFO

This document describes how **Finance Clerk**, **Finance Manager**, and **CFO** roles move universal-document sessions (balance sheet, income statement, budget report, and related uploads) through preparation, review, and final approval.

---

## Where each role works

| Role | Primary pages | What appears |
|------|----------------|--------------|
| **Finance Clerk** | `/dashboard`, `/upload`, `/mapping`, `/submission-history` | Open periods and tasks; upload/mapping for owned sessions; **Submission history** for own submissions |
| **Finance Manager** | `/finance-manager/review-queue` | Sessions in **`pending_review`** |
| **CFO** | Same URL as manager Review | Sessions in **`pending_cfo`** or **`approved_by_manager`** |
| **Manager & CFO** | `/finance-manager/history` | Settled outcomes (filters as implemented) |
| **Manager & CFO** | `/approvals?review=statement&transaction=<session_id>` | Full-page **statement review** (SFP/SFPER, formula modal). Visiting **`/approvals`** without `review=statement` redirects reviewers back to Review. |

Legacy bookmark **`/finance-manager/dashboard`** redirects to **`/finance-manager/review-queue`**.

---

## End-to-end flow (conceptual)

```mermaid
flowchart LR
  subgraph clerk [Finance Clerk]
    A[Upload / map / validate] --> B[Submit for review]
  end
  subgraph fm [Finance Manager]
    B --> C[pending_review]
    C --> D{Decision}
    D -->|Approve / forward| E[pending_cfo or approved_by_manager]
    D -->|Reject| R[rejected_by_manager]
  end
  subgraph cfo [CFO]
    E --> F{Decision}
    F -->|Final approve| G[approved / finalized]
    F -->|Reject| R2[rejected]
  end
  R --> clerk
  R2 --> clerk
```

Exact status strings can vary slightly by document type and backend version. Treat **`pending_review`** as the manager gate and **`pending_cfo`** / **`approved_by_manager`** as the CFO queue.

---

## Finance Clerk

### Purpose

Prepare trial balance data (or equivalent), map accounts where required, satisfy validation rules, then **submit for review** so a Finance Manager can perform quality control and forward toward the CFO where applicable.

### Typical journey

1. **Dashboard (`/dashboard`)** — Open periods and workload; **recently closed** periods (last 8) remain visible with progress after 3/3 auto-close or CFO lock. Use the status filter (**Closed only**) or **View submissions** on a card. **Open periods** depend on Supabase **`financial_periods`** (configured by System Admin). An empty period list is normal until periods are opened — then you can upload balance sheets, income statements, and budget reports.
2. **Upload (`/upload`)** — Import files (Excel/CSV where enabled). **Hard upload gates** block continue when validation fails:
   - **`balance_sheet`** — debits must equal credits
   - **`income_statement`** — at least one revenue/expense line; if the file has debit/credit columns, debits must equal credits
   - **`budget_report`** — at least one line with budget or actual amounts (variance is expected; GRAP 24 explanations are on the mapping page)
   **GRAP 1 / GRAP 24** mapping checks run again at submit for review.
3. **Mapping (`/mapping?session_id=…`)** — Map accounts to **GRAP-aligned** categories / statement lines for the document type. Users need **process** permission (`can_process`), typically clerks. Complete required mappings before submit. After submit (`pending_review`), mapping, GRAP panels, and variance explanations are **read-only** until rejection/correction.
4. **Submit for review** — From the mapping UI (`static/js/mapping-interface.js`), **`POST /api/submit-mapping`** with `session_id`, `document_type`, and `mapped_data`. Success message: *“Data forwarded to Finance Manager for review.”* Backend re-validates upload rules via **`require_balanced_session`**, then runs **`UniversalWorkflowService.submit_for_review`**, enforces role and **workflow conditions**, and sets **`pending_review`** on success.

### Statuses clerks may submit from

The service allows submission from typical **draft / staging** statuses (for example **`draft`**, **`uploaded`**, **`processing`**, **`mapped`**, **`validated`**) and from **`resubmitted`**, **`rejected`**, or **`rejected_by_manager`** so clerks can fix issues and send again. If the session is already locked (for example **`pending_review`**, **`pending_cfo`**, **`approved`**), submission is rejected until the workflow moves back to an editable state.

### After rejection

When a manager or CFO rejects with reason, the clerk updates data/mappings as needed and **submits for review** again via the same path, subject to status rules above. **View statement** on submission history opens a read-only statement review (same layout as FM/CFO history) without approve/finalize actions.

### Clerk-only navigation (reference)

| Nav / page | Role |
|------------|------|
| **History** (`/submission-history`) | Finance Clerk — own submission trail; **View statement** for read-only review |
| **Upload** | Users with upload permission |

Managers/CFOs use **`/finance-manager/history`** for cross-cutting settled submissions, not the clerk submission-history page.

### Clerk templates & scripts (orientation)

| Step | Templates / scripts (representative) |
|------|-------------------------------------|
| Dashboard | `templates/dashboard.html` |
| Upload | `templates/upload.html`, `static/js/upload.js` |
| Mapping | `templates/mapping_interface.html`, `static/js/mapping-interface.js`, `static/js/mapping-interface-init.js` |
| Submit / status | `static/js/mapping-interface.js` (primary); `static/js/submission-history.js`; `templates/submission-history.html`, `templates/submission_status.html` |

This file is the **single workflow reference** for clerks, managers, and CFOs.

---

## Finance Manager

Login redirects to **`/finance-manager/review-queue`**. Dashboard remains available from nav.

1. **Queue:** Open **Review** (`/finance-manager/review-queue`) from the nav or the **Dashboard** hero (**View Queue**); **Learn More** on the hero links to About. **Quick Actions** on the dashboard includes **Submission history** only (no duplicate review-queue card; **File Management** is hidden for Finance Manager). The queue loads **`GET /api/transactions/pending`** filtered to **`pending_review`**.
2. **Work:** Use **Review** on a card to open statement review (full-page or inline on the Review page, depending on navigation). Verify lines, formulas, and comments as implemented in the app. For **`budget_report`**, confirm **GRAP 24** variance explanations are present for line items exceeding 10% before forwarding.
3. **Approve:** **`POST /api/universal/approve`** with `session_id` and `document_type` — forwards the workflow toward CFO (session moves out of **`pending_review`**). For **budget reports**, the backend re-validates **GRAP 24** variance explanations at forward time (same gate as clerk submit and CFO finalize). Approve/reject from queue cards is disabled for FM — use statement review.
4. **Reject:** **`POST /api/universal/reject`** with a **mandatory reason** — typically **`rejected_by_manager`** so the clerk can fix and resubmit.
5. **History:** Settled items appear under **`/finance-manager/history`**, grouped by **reporting period** (filters and search still apply).
6. **Approval signatures:** Shown in statement review when `metadata.approval_signatures` is present.
7. **Line-item comments:** During active review (`pending_review`), use the **💬** button on statement rows to add per-account notes (calculation, mapping, data, or general). Comments are stored on `metadata.line_item_comments`, preserved on approve/reject, and visible in:
   - **Statement review** — audit panel grouped by account; **View** (💬) on flagged rows when read-only or settled
   - **FM/CFO History** — open **View Details** → statement review with `returnTo=/finance-manager/history` (read-only)
   - **Clerk submission history** — **View statement** opens read-only review with grouped line-item comments and rejection context

---

## CFO

Login redirects to **`/finance-manager/review-queue`** (same queue page as FM; client filters to CFO items).

1. **Queue:** Same **Review** page. The UI filters **`GET /api/transactions/pending`** to **`pending_cfo`** and **`approved_by_manager`**. Queue cards include **Finalize** / **Reject** quick actions; use **Batch finalization** to finalize multiple submissions via **`POST /api/universal/batch-approve`**.
2. **Work:** Same statement review entry points as the manager (session + document type).
3. **Approve:** **`POST /api/universal/approve`** — final approval step for the CFO stage. **The entire reporting period locks on the first final approval** (no further clerk uploads for that month, even if other document types are not yet CFO-approved). The finalize confirm dialog states this explicitly.
4. **Reject:** **`POST /api/universal/reject`** with reason — returns feedback toward submitter/workflow per backend rules.
5. **History:** Same **`/finance-manager/history`** page. On approved cards, **Finalized export** opens an in-app notice (does not navigate away) so you can keep final-approving other documents; open **Export Center** from the nav when ready to generate PDFs for all finalized submissions.
6. **Approval signatures:** Shown in statement review when prior approvers are recorded.
7. **Line-item comments:** View comments from FM review in statement review and **History** (read-only). CFO may add comments while finalizing; all comments remain on the audit trail after approval.

### CFO batch finalization and export

When finalizing **multiple documents** in one session:

1. **Review** — Approve (or reject) each FM-forwarded submission. The queue count should reach **0**.
2. **History** — Optional: click **Finalized export** on each approved card to acknowledge it is export-ready. Cards fade to **Export noted**; after PDF generation in Export Center they show **PDF exported**.
3. **Export Center** (nav **Export**) — When all approvals are done, select each finalized submission and **Generate PDF** (plus Excel / CSV / archive as needed). FM download depends on CFO generating PDF per session.

**Finalized export** on history cards is an **acknowledgment only** — it does **not** generate a PDF and does **not** deep-link to Export Center. Use the **Export** nav link when you are ready to export everything.

### Finalized export card states (History)

| State | UI | Meaning |
|-------|-----|---------|
| **Finalized export** (button) | Full card | CFO/FM has not acknowledged this finalized submission yet |
| **Export noted** (badge, faded card) | Acknowledged — continue batch review without leaving the page |
| **PDF exported** (badge, more faded) | Official PDF was generated in Export Center (tracked via export log) |

Acknowledgment is stored server-side (`metadata.export_ready_acknowledged_at`) and in the browser session. Re-export from Export Center is always allowed if needed; History simply stops prompting once PDF is logged.


## Shared mechanics

- **Period lock:** After CFO final approval, `financial_periods.is_locked` is set and a global API guard blocks mutating **`POST`/`PUT`/`PATCH`/`DELETE`** on sessions in that period (`utils/period_lock_guard.py`). **CFO finalize is blocked** if no reporting period can be resolved (`period_id_unresolved`) or if the database lock write fails (`period_lock_db_sync_failed`) — finalize only succeeds when `financial_periods.is_locked` is persisted. **Official financial-statement PDF** generation and download require the locked period (`utils/pdf_availability.py`, `utils/pdf_download_guard.py`). Formula-breakdown PDFs and the Manager’s Certificate are **not** gated on period lock (see **PDF and export gates** below).
- **Supabase period-lock migrations:** Run in order in Supabase SQL Editor: `scripts/add_period_lock_and_variance_explanations.sql`, `scripts/enable_financial_periods_cfo_lock_rls.sql` (includes legacy RLS consolidation). Verify with `python scripts/check_supabase_migrations.py` or `GET /api/system/schema-migrations` (CFO / System Admin). Manual audit queries: `scripts/verify_supabase_cfo_migrations.sql`. Expected probe: `financial_periods.is_locked` readable; registry entries for all three migration IDs.
- **GRAP by document type** (`utils/grap_standards_scope.py`, `services/grap_compliance_service.py`):
  - **`budget_report`:** GRAP 24 — mandatory variance explanations when |variance/budget| > 10%. Enforced at **clerk submit**, **FM forward**, and **CFO finalize** (`grap24_variance_explanations` in `UniversalWorkflowService`). The **Budget vs Actual** comparison table and variance panel appear on **`/mapping`** (clerk) and **statement review** (FM/CFO) — there is no separate route; `budget_report` *is* the GRAP 24 statement.
  - **`balance_sheet`:** GRAP 1 (SFP) — mapping complete, trial balance, assets = liabilities + equity.
  - **`income_statement`:** GRAP 1 (performance) — mapping complete, trial balance, revenue/expense structure (no GRAP 24 narratives).
- **Approval:** Use **`GET /api/transactions/pending`**, **`POST /api/universal/approve`** / **`reject`**, and **`POST /api/universal/batch-approve`** (CFO batch finalize on Review page). Legacy `/api/finance-manager/*` routes removed.
- **Preferred APIs:** Upload `POST /api/universal/upload`, GRAP mapping `POST /api/universal/process-grap-mapping`, submit `POST /api/submit-mapping`, approve/reject `POST /api/universal/approve` and `/reject`. Legacy `/api/upload` returns **410**; `/api/processing` delegates to the universal mapping endpoint.
- **Clerk submit:** **`POST /api/submit-mapping`** → **`UniversalWorkflowService.submit_for_review`** (`controllers/routes_universal.py`).
- **Pending queue (reviewers):** **`GET /api/transactions/pending`** — FM/CFO filtering in **`static/js/finance-manager-review-queue.js`**.
- **Approve / reject (reviewers):** **`POST /api/universal/approve`**, **`POST /api/universal/reject`**.
- **Cards:** **`static/js/transaction-card-ui.js`** on FM/CFO Review and History.
- **Statement review:** **`static/js/financial-statement-review.js`** (SFP/SFPER, actions, `returnTo`).
- **Manager’s Certificate:** **`POST /api/certificate/generate/<session_id>`** where enabled after manager approval.
- **Line-item comments:** `GET/POST /api/comments/line-item/<session_id>` — stored on `metadata.line_item_comments`; clerks read own sessions via `process`, reviewers via `review`. **Legacy rejections:** archived comments are resolved from `rejection_history`, `rejection_snapshot`, or the stored rejection reason; eligible sessions are repaired on read (`utils/session_metadata_helpers.py`).
- **Clerk submission list API:** `GET /api/submissions/user` — **Finance Clerk only**; returns lean payloads (counts, status, resolved comments/rejection reason).
- **Status helpers:** **`utils/session_workflow.py`** — submitted-for-review vs clerk-actionable rejection sets.

### Formula transparency (review modal)

During statement review, **calculated cells** open the **formula modal** (`static/js/formula-modal.js`). Copy in the modal stays **user-facing**; implementers use the APIs below.

| Endpoint | Purpose |
|----------|---------|
| **`GET /api/universal/session/<session_id>?document_type=<type>`** | Full **saved session summary** used to render statements and totals: financial statement blocks, metadata (including mappings where stored), row lists (`budget_rows`, `income_rows`, etc.), and session-level aggregates. **`document_type` is required.** |
| **`GET /api/universal/session/<session_id>/formula-breakdown?document_type=<type>`** | Payload for the modal: ordered **steps**, **variables**, and **finalResult**. Query **`scope`**: **`session`** (default, overview), **`calculation`** (with **`calc_id`**), **`line`** (with **`account_code`**, optional **`grap_code`**). |
| **`POST /api/formula/export/formula-breakdown-pdf`** | Download PDF snapshot of the modal breakdown (requires **`review`**, **`final_approve`**, or **`export_audit`**). Implemented in **`controllers/routes_formula.py`**. |

Server-side assembly lives in **`services/session_formula_breakdown.py`** (`build_formula_breakdown_response`), wired from **`controllers/routes_universal.py`**.

**Variable links in the modal** (same origin): **saved submission JSON** uses the session GET URL above; **full-page statement review** uses **`/approvals?review=statement&transaction=<session_id>&type=<document_type>`**, with **`returnTo`** added when opened from the formula modal on Review so **Back** can return to the queue tab where the browser allows **`window.opener`** / **`window.close()`**.

---

## PDF and export gates

Permissions are defined in **`models/supabase_auth_models.py`**. There are **three distinct export paths** — do not confuse them.

### Role × export capability

| Role | Official AFS PDF (`generate_pdf`) | Export Center (`/export`) | Formula breakdown PDF | Manager’s Certificate |
|------|-----------------------------------|---------------------------|------------------------|------------------------|
| **Finance Clerk** | No | No | No | No |
| **Finance Manager** | Download only (`download_pdf`, after lock) | Yes — read-only PDF download | Yes (via review modal) | Yes (after forwarding to CFO) |
| **CFO** | Generate + download (after period lock) | Yes — full (PDF, Excel, CSV, archive) | Yes (via review modal) | No (FM-only) |
| **Auditor** | No | No | Yes (API permission) | No |

### 1. Official financial-statement PDF (CFO generates; FM may download, period-locked)

**Who generates:** CFO only (`generate_pdf` permission).

**Who downloads:** CFO and Finance Manager (`download_pdf` or `generate_pdf`) after period lock.

**When:** Only after the CFO **final-approves** a submission and the linked reporting period is **locked** (`financial_periods.is_locked` or session `metadata.period_locked`).

**Where in the UI:**

| Location | Nav / entry |
|----------|-------------|
| **Export Center** | Nav **Export** → **`/export`** — CFO: generate Excel/CSV/archive/PDF; FM: read-only PDF download |
| **Dashboard** | **Export Center** / **Finalized exports** quick-action card (navigates to `/export`) |
| **Submission history / FM history** | **Finalized export** on approved cards — acknowledgment popup; card fades to **Export noted**, then **PDF exported** after Export Center generation |
| **Results / statement pages** | **Download PDF** on statement pages and **`/results`** (CFO may also **Generate PDF**) |

**Mechanics:**

- UI uses **`static/js/pdf-period-gate.js`**: **`GET /api/pdf/availability`** returns **`can_generate_pdf`** (CFO) and **`can_download_pdf`** (CFO + FM) when the period is locked.
- Session-backed generation: **`POST /api/export/generate-pdf`** (CFO) builds PDF from finalized session summary — no legacy `results_file` required.
- Legacy generation: **`POST /api/generate-pdf`** (CFO, upload flow with `results_file`).
- Structured exports: **`POST /api/export/excel`**, **`/csv`**, **`/archive`** (CFO; CSV also Auditor via `export_audit`).
- Session list: **`GET /api/export/sessions`** — finalized, locked submissions.
- Download: **`/download/<filename>`** — period lock check; any user with **`download_pdf`** may download (not limited to the user who generated the file).
- Front-end wiring: **`static/js/export-center.js`**, **`templates/export.html`**. **`static/js/transaction-card-ui.js`** — **Finalized export** on history cards (acknowledgment, fade states, export log integration).
- Export acknowledgment API: **`POST /api/universal/session/<session_id>/export-acknowledged`**

**Finance Clerk** has no export path. **Auditor** has formula-breakdown PDF only (not official AFS PDF).

### 2. Formula breakdown PDF (reviewers / auditor, not period-locked)

**Who:** Finance Manager, CFO, or Auditor — API requires **`review`**, **`final_approve`**, or **`export_audit`**.

**When:** During statement review (any workflow status where review is allowed). **Does not** require CFO finalization or period lock.

**Where in the UI:**

| Location | How to reach |
|----------|--------------|
| **Review queue / statement review** | **`/finance-manager/review-queue`** or **`/approvals?review=statement&transaction=<id>`** → **View Calculations** (or click a calculated cell) → formula modal → **Export This Breakdown (PDF)** |
| **Formula modal** | Loaded from **`templates/base.html`** when the user has **`review`** or **`export_audit`** |

**API:** **`POST /api/formula/export/formula-breakdown-pdf`** (`controllers/routes_formula.py`).

This is an **audit/transparency** export of calculation steps, not the sealed annual financial statements package.

### 3. Manager’s Certificate (Finance Manager only)

**Who:** Finance Manager only.

**When:** After the manager **approves and forwards** to the CFO (`approved_by_manager` / `pending_cfo`, or `metadata.manager_approval.at` set).

**Where in the UI:**

- **Statement review** header → **Manager’s certificate** button (`static/js/financial-statement-review.js`).
- Optional prompt immediately after FM approve.

**API:** **`POST /api/certificate/generate/<session_id>`** → download via **`/api/certificate/download/<certificate_id>`** (`controllers/routes_certificate.py`). Certificate routes are **exempt** from the period-lock mutation guard.

### Export Center extras (CFO full; FM read-only PDF)

**`/export`** accepts users with **`export`** or **`download_pdf`**. Cards:

| Card | Permission | Period lock? |
|------|------------|--------------|
| PDF Report — Generate | `generate_pdf` (CFO) | Yes |
| PDF Report — Download | `download_pdf` (FM read-only) | Yes |
| Excel Workbook | `export` (CFO) | Enforced via export API on finalized sessions |
| CSV Data | `export_audit` (CFO, Auditor API) | Same |
| Archive Package | `export` (CFO) | Same — ZIP with JSON, CSV, Excel, PDF if present |

Excel, CSV, and Archive are wired via **`controllers/routes_export.py`** and **`services/export_center_service.py`**.

### Workflow nuances (exports)

1. **Clerk has no export path** — prepare and submit only; no PDF or Export nav.
2. **FM can download finalized AFS PDF** after CFO lock (Export Center, history link, statement pages) but cannot generate official PDF or Excel/archive.
3. **CFO unlocks official PDF and structured exports** — period lock is the business gate.
4. **Auditor** has **`export_audit`** for formula-breakdown PDF and CSV API but **no** `/export` page or official AFS PDF.
5. **Two PDF types** — formula breakdown (anytime in review) vs official statements (post–CFO lock).
6. **Upload/submit balance gates** apply to all three document types via **`require_balanced_session`** (balance sheet trial balance; income performance lines ± debit/credit; budget line capture). Official PDF/export still depends on CFO finalization.

---

## Related code (orientation)

| Area | Location |
|------|-----------|
| Clerk dashboard / upload / mapping routes | `controllers/routes.py` (`/dashboard`, `/upload`, `/mapping`, `/submission-history`) |
| Clerk submit API | `POST /api/submit-mapping` in `controllers/routes_universal.py` |
| FM routes & redirects | `controllers/routes_finance_manager.py` |
| Universal workflow | `services/universal_workflow_service.py` |
| Universal approve/reject / pending API | `controllers/routes_universal.py` |
| Clerk submission UI | `static/js/mapping-interface.js`, `static/js/upload.js`, `static/js/submission-history.js`, `templates/mapping_interface.html` |
| FM/CFO Review UI | `templates/finance_manager_review_queue.html`, `static/js/finance-manager-review-queue.js` |
| FM/CFO History UI | `templates/finance_manager_history.html`, `static/js/finance-manager-history.js` |
| Statement review shell | `templates/approvals.html`, `static/js/financial-statement-review.js` |
| Formula modal & session breakdown API | `static/js/formula-modal.js`, `services/session_formula_breakdown.py`, `GET /api/universal/session/...` in `controllers/routes_universal.py` |
| PDF period gate (UI) | `static/js/pdf-period-gate.js`, `GET /api/pdf/availability` in `controllers/routes.py` |
| Official PDF generate/download | `POST /api/generate-pdf`, `/download/<filename>`, `utils/pdf_availability.py`, `utils/pdf_download_guard.py` |
| Export Center page | `templates/export.html`, `/export` in `controllers/routes.py` (CFO-only) |
| Manager’s Certificate | `controllers/routes_certificate.py`, button in `static/js/financial-statement-review.js` |
| Schema migration check | `scripts/check_supabase_migrations.py`, `GET /api/system/schema-migrations`, `services/schema_migration_service.py` |
| Period RLS (Supabase) | `scripts/enable_financial_periods_cfo_lock_rls.sql`, `scripts/consolidate_financial_periods_rls.sql` |
| Line-item comment modal | `templates/components/line-item-comment-modal.html`, `static/js/line-item-comment-system.js` |
| Metadata helpers (legacy comments / counts) | `utils/session_metadata_helpers.py` |

---

## UAT sign-off checklist

Use this checklist for user acceptance testing before production sign-off. Record **Pass / Fail / N/A** and tester initials. Run `python scripts/check_supabase_migrations.py` first — all migrations should report `"all_applied": true`.

### Environment prerequisites

- [ ] Supabase migrations applied (`add_period_lock_and_variance_explanations`, `enable_financial_periods_cfo_lock_rls`, `consolidate_financial_periods_rls`)
- [ ] `python scripts/check_supabase_migrations.py` → `all_applied: true`, probe `financial_periods.is_locked` passed
- [ ] Test users exist for **Finance Clerk**, **Finance Manager**, and **CFO**
- [ ] At least one open reporting period linked to uploads (or date-range resolution works)

### Finance Clerk

| # | Test | Pass |
|---|------|------|
| C1 | Upload **balance sheet** with unbalanced debits/credits — **Continue** disabled | Pass |
| C2 | Upload valid balance sheet → map all accounts → **Submit for review** succeeds | Pass |
| C3 | Success toast: *“Data forwarded to Finance Manager for review.”* | Pass |
| C4 | After submit, mapping and GRAP panels are **read-only** | Pass |
| C5 | Clerk **cannot** see Approve / Finalize on any page | Pass |
| C6 | **Income statement** and **budget report** upload gates behave per doc type | Pass |
| C7 | **Submission history** shows own submissions with correct document-type badge colours | Pass |
| C8 | After FM rejection → **Correct** opens correction workspace with reviewer feedback and per-account comments | Pass |
| C9 | Resubmit requires mandatory clerk note (≥10 chars) + balanced + mapped + GRAP checks | Pass |
| C10 | Clerk **View statement** shows read-only review with line-item comments and rejection context when applicable | Pass |
| C11 | Clerk **View statement** opens read-only statement review (`/approvals?review=statement&returnTo=/submission-history`) | Pass |

### Finance Manager

| # | Test | Pass |
|---|------|------|
| M1 | **Review queue** shows only `pending_review` (not CFO items) | Pass |
| M2 | Queue cards have **Review** only (no Approve/Reject on card) | Pass |
| M3 | Statement review: click line → **Formula Transparency** modal opens | Pass |
| M4 | Budget report: GRAP 24 table rows clickable; variance explanations visible | Pass |
| M5 | **💬** on line adds comment; comment appears in audit panel | Pass |
| M6 | **Reject** requires mandatory reason → status `rejected_by_manager` | Pass |
| M7 | **Approve** forwards to CFO; `approval_signatures` shows FM entry | Pass |
| M8 | Optional manager’s certificate prompt after approve | Pass |
| M9 | **History** → View Details on approved item: statement read-only, **line item comments** visible | Pass |
| M10 | Rejected item in history shows rejection reason + line-item comments | Pass |

### CFO

| # | Test | Pass |
|---|------|------|
| F1 | **Review queue** shows `pending_cfo` / `approved_by_manager` only | Pass |
| F2 | **Finalize** disabled until manager approved | Pass |
| F3 | Finalize confirm dialog warns about **period lock / audit trail** | Pass |
| F4 | **Batch finalization** works for multiple selected items | Pass |
| F5 | GRAP 24: finalize blocked when >10% variance lines lack explanations | Pass |
| F6 | After finalize: period `is_locked = true`; mutating API calls blocked | Pass |
| F7 | **Dashboard KPI strip** shows pending finalization / surplus-deficit / budget variance | Pass |
| F8 | **Export Center**: Generate PDF only after period lock | Pass |
| F9 | **History** → approved submission: line-item comments visible (read-only) | Pass |
| F10 | FM can download PDF after lock; clerk cannot export | Pass |

### Cross-role / audit

| # | Test | Pass |
|---|------|------|
| X1 | End-to-end: Clerk submit → FM approve → CFO finalize → PDF export | Pass |
| X2 | Rejection loop: FM reject with line comments → clerk corrects → resubmit → FM approve | Pass |
| X3 | Workflow timeline tab shows submit, rejection, resubmission events | Pass |
| X4 | Line-item comments persist on metadata after approve (not cleared) | Pass |
| X5 | Formula breakdown PDF available in review (not gated on period lock) | Pass |

---

## Asset Manager (GRAP 17)

**Primary goal:** Maintain the asset register; submit lifecycle changes as **asset journals** for Finance Manager approval (separate from the trial balance workflow).

**Out of scope (by design):** Depreciation and asset lifecycle changes do **not** post to the trial balance / balance sheet workflow. Reconciliation compares register totals to a GL control balance synced from an approved balance sheet or entered manually.

### Where the Asset Manager works

| Nav / page | Purpose |
|------------|---------|
| **Dashboard** (`/dashboard`) | Overview panel: active assets, carrying value, pending journals, GL variance, quick actions |
| **Asset Register** (`/asset-manager/register`) | Summary strip, list, register, export CSV, run annual depreciation |
| **My journals** (`/asset-manager/journals`) | All journals you submitted (filter by status); nav badge shows your pending FM approvals |
| **Asset detail** (`/asset-manager/assets/<id>`) | Useful life, impairment, and disposal journals |
| **Reconciliation** (`/asset-manager/reconciliation`) | Register vs GL; preview + sync from approved trial balance or manual override |

Finance Manager: **Asset journals** (`/finance-manager/asset-journals`) — approve or reject pending asset journals (nav badge shows pending count). **Materiality escalation:** routine useful-life reviews are FM-only; **disposals** and **impairments ≥ threshold** (default R 100,000, `ASSET_JOURNAL_MATERIALITY_THRESHOLD`) are forwarded by FM to **CFO** (`pending_cfo`) for final sign-off. Settled asset journal decisions appear under **History → Asset journals**.

**Persistence:** Supabase only — tables `assets`, `asset_journals`, `asset_gl_balances`. No JSON file fallback.

**SQL run order (Supabase SQL Editor):**

1. If `financial_periods.id` is `text` (demo slugs like `may-2026-period`), run `scripts/migrate_financial_periods_id_to_uuid.sql` first. It assigns UUIDs, keeps old slugs in `period_code` / `metadata.legacy_id`, and updates `metadata.period_id` on session rows.
2. Run `scripts/create_asset_register_tables.sql`.

```sql
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'financial_periods' AND column_name = 'id';
-- Expected after step 1: data_type = uuid
```

### Notifications (inbox)

| Event | Who is notified | Inbox action |
|-------|-----------------|--------------|
| Asset Manager submits useful life / impairment / disposal journal | Finance Manager | Open **Asset journals** |
| FM forwards material journal (disposal or impairment ≥ threshold) | CFO | Open **Asset journals** (CFO queue) |
| FM approves routine journal | Asset Manager (submitter) | View asset detail |
| CFO approves material journal | Asset Manager (submitter) | View asset detail |
| FM or CFO rejects journal | Asset Manager (submitter) | View asset detail (includes rejection reason) |

Asset Manager sees journal status on each asset’s **Asset journals** section (pending / approved / rejected, reviewer, date, FM rejection reason when applicable).

### Typical journey

1. **Register** — Add assets (GRAP 17 category, cost, useful life). Demo seed on first register visit if empty. Money fields use live **en-ZA** formatting (thousands + cents).
2. **Lifecycle** — Submit **Useful life review** (GRAP 17.16), **Impairment**, or **Disposal** with mandatory reason.
3. **FM approval** — Status `pending_review` until FM approves/rejects or forwards material items to CFO (`pending_cfo`). Register updates **only on final approval** (FM for routine; CFO for material).
4. **Depreciation** — **Run depreciation** on the register page applies annual charges for the **current calendar year** to active assets whose schedule row is still `projected`. Re-running the same year processes **0** assets (no double-charge).
5. **Reconciliation** — Compare register carrying value total to GL PPE control balance.
   - **Sync from trial balance** — previews first (`GET .../sync-tb/preview`), shows current vs proposed balance and line count, then confirms before writing.
   - If already synced from the same approved session with the same total, shows *no changes* and skips the write.
   - **Fixed-asset GL matching** — rows mapped to PPE / intangibles / investments (GRAP labels such as *Property, Plant and Equipment*, chart codes 2100–2399, municipal 1600–1799, or matching account descriptions).
   - Sync audit note example: `Synced from sample_balanced_trial_balance.xlsx (session 86be47f2…) — 1 fixed-asset GL line (PPE, intangibles, investments).`
   - **Manual GL override** — separate form; note field is not pre-filled from sync text. Sync details stay on the GL card above.
6. **Export** — **Export CSV** downloads the GRAP 17 asset register report (logged in export audit).

### Verify depreciation applied

| Check | What to look for |
|-------|------------------|
| Toast | e.g. *Annual depreciation for 2026 applied to N asset(s)* |
| Register / detail | Lower carrying value, higher accumulated depreciation, remaining life −1 |
| API | `POST /api/asset-manager/depreciation/run` → `success: true`, `depreciation_results.assets_processed` |
| Supabase | `assets.updated_at` recent; schedule entry for year → `processed` |
| Idempotency | Second run same year → **0** assets processed |

### APIs

| Endpoint | Purpose |
|----------|---------|
| `GET/POST /api/asset-manager/assets` | List / register |
| `POST .../useful-life-journal` \| `.../impairment-journal` \| `.../disposal-journal` | Queue lifecycle change |
| `POST /api/asset-manager/depreciation/run` | Annual depreciation run |
| `GET /api/asset-manager/reconciliation` | Register vs GL |
| `GET /api/asset-manager/reconciliation/sync-tb/preview` | Preview TB sync (no write) |
| `POST /api/asset-manager/reconciliation/sync-tb` | Apply GL from approved balance sheet |
| `PUT /api/asset-manager/reconciliation/gl-balance` | Manual GL override |
| `GET /api/asset-manager/dashboard-stats` | Dashboard KPIs |
| `GET /api/asset-manager/export/register.csv` | CSV export |
| `GET /api/asset-manager/journals` | Asset Manager’s journals (scoped by role) |
| `GET /api/asset-journals/pending` | FM queue |
| `GET /api/asset-journals/history` | FM/CFO settled asset journals |
| `POST /api/asset-journals/<id>/approve` \| `/reject` | FM decision |

### UAT checklist (Asset Manager)

| # | Test | Pass |
|---|------|------|
| A1 | Login as Asset Manager → **Dashboard** KPIs and quick actions | Pass |
| A2 | Register asset → appears with carrying value | Pass |
| A3 | Useful life journal pending until FM approves | Pass |
| A4 | Impairment reduces carrying value only after FM approve | Pass |
| A5 | Disposal journal marks asset disposed only after FM approve | Pass |
| A6 | FM **Asset journals** approve/reject (nav badge) | Pass |
| A7 | **Reconciliation** preview sync, confirm apply, or manual GL; source shows *Trial balance* / *Manual entry* | Pass |
| A8 | **Run depreciation** updates carrying values; second run same year → 0 assets | Pass |
| A9 | **Export CSV** downloads register | Pass |
| A10 | FM **History → Asset journals** shows settled decisions | Pass |
| A11 | Inbox: FM notified on submit; Asset Manager on approve/reject | Pass |

---

## Auditor (AGSA read-only)

**Primary goal:** Review **CFO-finalized** submissions in **locked** reporting periods. Inspect statements, formula breakdowns, and audit CSV exports. **No edits, approvals, or official AFS PDF generation.**

**Out of scope (by design):** Upload, mapping, approve/reject, official AFS PDF (`generate_pdf` / Export Center for CFO/FM), asset lifecycle changes.

### Where the Auditor works

| Nav / page | Purpose |
|------------|---------|
| **Dashboard** (`/dashboard`) | Finalized submission count; links to audit workspace |
| **Audit workspace** (`/audit`) | Pick finalized submission → read-only review or audit CSV |
| **Statement review** (`/approvals?review=statement&transaction=<id>&type=<doc>&returnTo=/audit`) | Read-only SFP/SFPER, line comments, formula modal |
| **Asset register** (`/audit/asset-register`) | Read-only GRAP 17 register list |
| **Material journal trail** (`/audit/asset-journals`) | Read-only CFO-approved disposals and material impairments |
| **Asset reconciliation** (`/audit/reconciliation`) | Read-only register vs GL variance |

Login redirects to **`/audit`**. Demo user: `auditor@agsa.gov.za`.

**Inbox:** When a reporting period is **locked for the first time** on CFO finalization, auditors receive **“Reporting period locked — audit pack ready”** with a link to the audit workspace.

### Access rules

- Session must be **CFO-approved** (`workflow_status` effective = `approved`) **and** reporting period **locked**.
- Same gate as Export Center finalized list (`export_center_service.is_auditor_viewable`).
- If not finalized/locked → session API returns 403 for auditor.

### Typical journey

1. **Audit workspace** — Select a finalized submission from the dropdown.
2. **Read-only review** — **Open review** → full statement, existing FM/CFO line comments, **View Calculations** → formula modal → **Export This Breakdown (PDF)**.
3. **Audit CSV** — Download mapped line data for working papers (`POST /api/export/csv`).
4. **Asset register / reconciliation** — Read-only GRAP 17 views (separate from trial balance workflow).
5. **Material journal trail** — Read-only log of CFO-approved disposals and material impairments from the asset register.

### APIs (Auditor)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/export/sessions` | List finalized, locked submissions |
| `POST /api/export/csv` | Audit CSV export |
| `GET /api/export/log` | CSV export log (auditor-scoped) |
| `GET /api/universal/session/<id>` | Read-only session (finalized + locked only) |
| `GET /api/universal/session/<id>/formula-breakdown` | Formula transparency |
| `POST /api/formula/export/formula-breakdown-pdf` | Calculation audit PDF |
| `GET /api/asset-manager/assets` | Read-only asset list (`view_assets`) |
| `GET /api/asset-manager/reconciliation` | Read-only reconciliation (`view_assets`) |
| `GET /api/audit/asset-journals` | Read-only material asset journal audit trail |

### UAT checklist (Auditor)

| # | Test | Pass |
|---|------|------|
| U1 | Login as Auditor → lands on **Audit workspace** | Pass |
| U2 | Dashboard shows finalized submission count | Pass |
| U3 | Audit workspace lists only CFO-finalized, locked submissions | Pass |
| U4 | **Open review** — read-only statement; no Approve/Reject | Pass |
| U5 | Formula modal → **Export This Breakdown (PDF)** works | Pass |
| U6 | **Export CSV** downloads mapped data | Pass |
| U7 | Non-finalized session → 403 on session API | Pass |
| U8 | Read-only **Asset register** and **Reconciliation** | Pass |
| U9 | **Material journal trail** lists CFO-approved disposals/impairments only | Pass |
| U10 | Mobile nav includes **Journal trail** (parity with desktop) | Pass |
| U11 | Inbox **audit pack ready** when period first locked on CFO finalize | Pass |

---

## System Admin

**Primary goal:** Configure **`financial_periods`** and user accounts. **No financial workflow access** (no upload, review, export, or asset mutations).

### Where the System Admin works

| Nav / page | Purpose |
|------------|---------|
| **Admin panel** (`/admin`) | Overview, period management, user CRUD, schema migration status |
| **Dashboard** (`/dashboard`) | KPI strip — active users, open/locked periods, link to admin panel |

Login redirects to **`/admin`**. Demo user: `system.admin@sadpmr.gov.za` / `demo123`.

### Typical journey

1. **Schema migrations** — Confirm all checks pass on the Admin panel (or `GET /api/system/schema-migrations`). Run SQL scripts in Supabase if any are missing.
2. **Create period** — `POST /api/periods` with name, start/end/due dates, required uploads.
3. **Open period** — `POST /api/periods/<id>/open` so Finance Clerks see it on their dashboard.
4. **Users** — Create accounts and assign roles via Admin panel (`POST /api/admin/users`). Deactivate leavers with `POST /api/admin/users/<id>/deactivate`.

**Clerk dependency:** Until a period is **created and opened**, the Finance Clerk dashboard shows an empty period list.

### APIs (System Admin)

| Endpoint | Purpose |
|----------|---------|
| `GET /api/admin/overview` | User/period counts + migration report |
| `GET /api/admin/periods` | List all `financial_periods` |
| `POST /api/periods` | Create period (`manage_users`) |
| `POST /api/periods/<id>/open` \| `/close` | Open/close for clerk uploads |
| `GET /api/admin/users` | List users (no password hashes) |
| `POST /api/admin/users` | Create user with role |
| `POST /api/admin/users/<id>/deactivate` | Deactivate account |
| `GET /api/system/schema-migrations` | Schema health (CFO + System Admin) |

### UAT checklist (System Admin)

| # | Test | Pass |
|---|------|------|
| S1 | Login as System Admin → lands on **`/admin`** | Pass |
| S2 | Dashboard shows user/period KPIs | Pass |
| S3 | Create reporting period → appears in list | Pass |
| S4 | Open period → Finance Clerk dashboard shows it | Pass |
| S5 | Create user with role → can log in | Pass |
| S6 | Deactivate user → login denied | Pass |
| S7 | Schema migration panel shows status | Pass |
| S8 | System Admin cannot access review queue / upload / export | Pass |

### Sign-off

| Role | Name | Date | Signature / OK |
|------|------|------|----------------|
| Finance Clerk (UAT) | Paula | 25/05/2026 | OK |
| Finance Manager (UAT) | Paula | 25/05/2026 | OK |
| CFO (UAT) | Paula | 25/05/2026 | OK |
| Asset Manager (UAT) | Paula | 25/05/2026 | OK |
| Auditor (UAT) | Paula | 25/05/2026 | OK |
| System Admin (UAT) | Paula | 26/05/2026 | OK |
| Technical / Dev | Paula | 25/05/2026 | OK |

---

## Operator notes (known behaviour)

| Topic | Behaviour |
|-------|-----------|
| **Clerk dashboard** | **Open periods** shown first for uploads. **Closed periods** sit in a collapsible archive (hidden by default); **Load all closed periods** fetches older months. CFO-locked months appear only in closed. |
| **System Admin first** | Clerks cannot upload until a period is **created and opened** in Admin — empty dashboard is expected before that. |
| **FM/CFO history** | Submissions are **grouped by reporting period**, then **by document type** (Balance Sheet, Income Statement, Budget Report); older items without `period_name` appear under **Other submissions**. |
| **CFO first finalize** | Locks the **whole reporting month** immediately — confirm dialog explains this; finish all reviews before finalizing if uploads must stay open (they will not after lock). |
| **Auditor exports** | No **Export** nav — use **Audit workspace** CSV and formula-breakdown PDF from statement review (`export_audit` permission). |
| **Admin duplicate rows** | Legacy duplicate `financial_periods` rows may remain if **CFO locked**; admin list dedupes display. Use **Merge duplicate rows** on the card to relink sessions and delete empty duplicates (including locked empties). |
| **Admin system tools** | **Database cleanup** at `/admin/cleanup` (System Admin only). Inbox hidden for System Admin. Audit log UI planned — use Supabase dashboard for now. |
| **FM export nav** | Labelled **Export PDFs** — read-only download; CFO uses full Export Center to generate outputs. |
| **History export ack** | **Mark export ready** on approved cards is acknowledgment only — open **Export** nav to download or generate PDFs. |
| **Asset workflow** | Self-contained GRAP 17 path — apply `scripts/create_asset_register_tables.sql` in Supabase before first use. |
