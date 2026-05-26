# Maroon Traceability × Varydian Financial Reporting

**Maroon:** [lungelomyamya-rgb/maroon_traceability](https://github.com/lungelomyamya-rgb/maroon_traceability) — supply-chain traceability (farm → retail).  
**Varydian:** this repo — GRAP-aligned municipal / SOE financial reporting.

## Product answer: add Varydian to Maroon’s *offer*, not inside Maroon’s *codebase*

Maroon’s pricing matrix is **marketing**. The **Government & SOEs** column already promises:

- GRAP & SITA aligned  
- Unlimited records / users  
- Custom ERP integration  

**Varydian is how you deliver that promise** — as a linked product (integration), not by rewriting Maroon in Flask or moving finance into Next.js.

| Maroon tier | Traceability (Maroon) | Financial reporting (Varydian) |
|-------------|-------------------------|--------------------------------|
| Individual Farmer | ✅ Core product | ❌ Not in scope |
| SMME / Co-op | ✅ + basic API | ❌ |
| Commercial Farmers | ✅ + API access | Optional add-on later |
| **Government & SOEs** | ✅ Compliance / oversight | ✅ **Varydian** (primary) |

Lower tiers show **Integrations** struck through on the free plan — that refers to **external** systems (ERP, finance), not “build finance inside Maroon.”

## Roles are different (do not merge role lists)

| Maroon roles (examples) | Varydian roles |
|-------------------------|----------------|
| Individual / Commercial Farmer, Retailer, Inspector, Logistics, Packaging, Government (traceability) | Finance Clerk, Finance Manager, CFO, Asset Manager, Auditor, System Admin |

A **Government** user in Maroon might **open Varydian** for GRAP workflows. They still need a Varydian account (or future SSO) with roles like **Finance Clerk** / **CFO** / **Auditor**.

## Recommended user journey

```text
Maroon marketing site (pricing)
    → Government & SOEs → "Contact Sales" / "Open financial reporting"
        → Varydian on Render (login)
            → Clerk upload → FM review → CFO finalize → Auditor read-only
    → Farmer tiers → stay in Maroon only
```

## Technical integration (Phase 1 — current)

| Item | Where |
|------|--------|
| Varydian hosted | Render (`render.yaml`) |
| Maroon hosted | Vercel / GitHub Pages |
| Link Maroon → Varydian | `NEXT_PUBLIC_FINANCE_APP_URL` in Maroon → Render URL |
| Link Varydian → Maroon | `MAROON_APP_URL` in Render → Maroon URL |
| Auth | Separate logins until shared Supabase Auth is designed |
| Data | Same Supabase project optional; **separate tables** |

## What to change in Maroon (pricing / Government card)

On the **Government & SOEs** plan (and optionally Contact Sales):

1. Add feature line: **Varydian GRAP reporting** (6 finance roles, period lock, audit pack).  
2. Change CTA or add secondary link: **Open financial reporting** → `NEXT_PUBLIC_FINANCE_APP_URL/login`.  
3. Keep traceability features on Maroon; do not duplicate Varydian screens in Next.js.

Example env in Maroon:

```env
NEXT_PUBLIC_FINANCE_APP_URL=https://varydian-financial-reporting.onrender.com
```

## What Varydian already provides (Government tier fulfillment)

- GRAP 1 / 24 mapping and statements  
- Clerk → FM → CFO approval with period lock  
- Asset register (GRAP 17) + material journal escalation  
- Auditor read-only workspace + CSV / formula audit PDF  
- System Admin periods and users  

See `WORKFLOWS.md` for full UAT sign-off.

## Phase 2+ (optional)

- Shared Supabase + profile flag `has_finance_module`  
- Maroon Government dashboard widget: count of locked periods / audit-ready packs (`GET /api/export/sessions` with API key)  
- SSO: Supabase Auth for both apps  

---

**Summary:** Yes — **offer** Varydian under Maroon’s Government & SOEs tier. No — **do not** rebuild Varydian inside Maroon or replace Varydian roles with Farmer/Retailer roles.
