# Deployment & hosting guide

Varydian Financial Reporting System — **client demos (free)** and **growth to ~10,000 users**.

---

## Choose hosting for your goal

| Goal | Recommended | Why |
|------|-------------|-----|
| **Show clients upload → map → approve → PDF** (no budget yet) | **[Render.com](https://render.com) free Web Service** + **Supabase free** | Full Flask app, **16 MB uploads**, PDF download, long requests (120s timeout) |
| **Quick static-style demo only** (tiny files, no PDF) | Vercel Hobby | Easy Git deploy, but **~4.5 MB upload limit** and short serverless timeouts |
| **Production / 10k users** (when funded) | Azure App Service or Railway **paid** + Supabase Pro | Always-on workers, pooling, SA region option |

**Do not use Vercel as the main demo host** if you need clerks to upload trial-balance Excel files and managers to download PDFs. The app allows uploads up to **16 MB** (`utils/constants.py`); Vercel serverless often rejects or times out on that workflow.

---

## Free client demo (recommended): Render + Supabase

### What stays free

| Service | Free tier | Role |
|---------|-----------|------|
| **Supabase** | Free project | Database, auth, optional storage |
| **Render** | Free web service | Runs Flask (`gunicorn`) for demos |
| **GitHub** | Public/private repo | Source for Render deploy |

### Render limitations (plan for demos)

- Service **sleeps after ~15 minutes** of no traffic — first visit can take **30–60 seconds** to wake.
- **Before a client meeting:** open the site once and wait until the login page loads.
- Disk is **ephemeral** — fine for demo sessions; production should use Supabase storage for files later.
- Free tier is **not** for 10,000 real users — only for proving the workflow.

### Deploy to Render (one-time setup)

1. Push the repo to GitHub.
2. Sign in at [render.com](https://render.com) → **New** → **Blueprint** (or **Web Service**).
3. Connect the repo. Render reads `render.yaml` in the project root.
4. Set environment variables in the Render dashboard:

   ```
   SUPABASE_URL=https://xxxx.supabase.co
   SUPABASE_ANON_KEY=your_anon_key
   SECRET_KEY=long_random_string_at_least_32_chars
   FLASK_ENV=production
   ```

   Optional (if you use service-role features in code):

   ```
   SUPABASE_SECRET_KEY=your_service_role_key
   ```

5. Deploy. Your URL will look like: `https://varydian-financial-reporting.onrender.com`

### Local demo fallback (100% free, no sleep)

For important presentations when Render is cold:

```bash
pip install -r requirements.txt
python run.py
```

Share your machine on the LAN, or use a free tunnel (e.g. Cloudflare Tunnel / ngrok) so clients can reach `http://localhost:5000`.

### Demo checklist for clients

1. Wake the Render URL **2 minutes** before the meeting.
2. Log in as **Finance Clerk** → upload sample trial balance → map → submit.
3. Log in as **Finance Manager** → Review queue → approve.
4. Log in as **CFO** → final approve → download PDF if enabled.
5. Show **Assets / Liabilities / Equity / Difference** on mapping and review screens.

---

## Vercel (optional, limited demo)

`vercel.json` remains for teams who only need a **light** preview.

| Works on Vercel free | Problem on Vercel free |
|----------------------|-------------------------|
| Login, navigation, UI | Excel upload **> ~4.5 MB** often fails |
| Small API calls | PDF generation may **timeout** |
| | No reliable `uploads/` folder on disk |

Use Vercel only if demos use **very small** sample files and you skip heavy PDF steps.

---

## Railway vs Azure (when you have budget)

Neither is a good **long-term free** host for this stack today.

| Platform | Free? | Fit for this app |
|----------|-------|------------------|
| **Railway** | Small monthly credit, then paid | Excellent DX; same as Render but paid for always-on |
| **Azure App Service** | F1 free tier (limited CPU, can sleep) | Good for **South Africa North** latency; best **production** path for SA clients |
| **Render** | Free web tier with sleep | **Best free demo** |

**Suggested path:** Render (demo) → when funded, **Azure App Service B1+** (Johannesburg) or **Railway Pro** + **Supabase Pro**.

### Target production sketch (~10,000 users)

```
[Browser]
    → [CDN / static] (optional)
    → [App Service or containers: Gunicorn × N workers]
    → [Supabase Postgres + connection pooler]
    → [Background worker: PDF / large Excel] (later: Redis + RQ/Celery)
```

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_ANON_KEY` | Yes | Public API key |
| `SECRET_KEY` | Yes | Flask session signing (random, 32+ chars) |
| `SUPABASE_SECRET_KEY` | If used in code | Service role — **never** expose to browser |
| `FLASK_ENV` | Recommended | `production` on Render/Azure |

Copy from `.env.example` for local development.

---

## Database performance (run before scale)

In Supabase SQL editor, run:

`scripts/add_session_queue_indexes.sql`

Indexes on `status` + `updated_at` for balance sheet, income statement, and budget session tables.

---

## API pagination (FM/CFO queue)

Pending queue supports paging (ready for growth):

```
GET /api/transactions/pending?limit=50&offset=0
```

Response includes `total_count`, `has_more`, `limit`, `offset`.

---

## Roadmap to ~10,000 users

### Phase 0 — Now (free demo)

- [x] Render + Supabase free
- [x] Session queue indexes (SQL script)
- [x] Pending API pagination
- [ ] Run index SQL on your Supabase project
- [ ] Deploy to Render and rehearse wake-up + full workflow

### Phase 1 — Pilot (first paying clients)

- Supabase **Pro**
- Render **Starter** or Azure **B1** (always on)
- Custom domain + HTTPS
- Monitor upload size and PDF duration

### Phase 2 — Growth (toward 10k registered users)

- Azure App Service scale-out **or** Railway with multiple instances
- Supabase connection **pooling** (Supavisor)
- Background jobs for PDF / large imports
- Rate limits on login and upload
- Archive old audit rows

### Phase 3 — 10k+ active usage

- Read replicas if reporting load is heavy
- Per-tenant RLS audit
- CDN for `/static`
- Load testing on month-end peaks (concurrent clerks + FMs)

---

## Files in this repo for deployment

| File | Purpose |
|------|---------|
| `render.yaml` | Render Blueprint (free web service) |
| `Procfile` | `gunicorn` start command (Render/Heroku-style) |
| `requirements.txt` | Includes `gunicorn` |
| `app.py` | WSGI entry (`app:app`) |
| `vercel.json` | Optional Vercel deploy (limited) |
| `scripts/add_session_queue_indexes.sql` | DB indexes for queues |

---

## Troubleshooting

### Upload fails on cloud but works locally

- Check host **request body size** (Render allows much more than Vercel).
- Check Supabase row limits and RLS policies.
- Try a smaller `.xlsx` first (under 5 MB) to isolate network vs file issues.

### Render “Application failed to respond”

- Service may be waking — wait 60s and refresh.
- Check Render logs for missing `SUPABASE_URL` / `SECRET_KEY`.
- Increase timeout: `gunicorn` already uses `--timeout 120` in `render.yaml`.

### PDF download empty or errors

- Confirm session reached **approved** state and period lock rules allow export.
- Check Render logs for ReportLab errors; demo PDFs need warm instance (not cold start mid-request).

---

## Security (all environments)

- Never commit `.env` or service keys.
- Use Supabase **RLS** on session tables.
- Rotate `SECRET_KEY` if leaked.
- Use `FLASK_ENV=production` on public hosts.

---

## Summary

- **For client demos with no budget:** deploy on **Render (free)** + **Supabase (free)**. Avoid Vercel for upload/PDF demos.
- **Railway/Azure:** use when you can pay; Azure is stronger for **South Africa** production.
- **10,000 users:** achievable later with always-on app hosting, Supabase Pro, indexes, pagination, and background jobs — not on free tiers alone.
