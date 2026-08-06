# NED Tech CRM/ERP — Product Requirements

## Original brief
Multi-tenant SaaS CRM/ERP. Modules: CRM, Sales, Tasks, Finance, HR, AI, Files, Calendar, Reports, Settings. UI like HubSpot/Linear/Stripe/Notion. Modular (each toggleable). Multi-tenant, sellable as SaaS.

## Decisions
- **DB**: MongoDB (repository pattern; swappable to Postgres later)
- **Auth**: JWT email/password + Google OAuth (dormant until keys set)
- **AI**: GPT-5.4 via Emergent LLM key
- **Payments**: Stripe subscriptions on platform-managed sandbox — LIVE
- **Email**: Emergent-managed Resend (graceful fallback if key not provisioned)
- **API**: FastAPI, `/api/v1/*`; Stripe webhook at `/api/stripe/webhook`
- **Architecture**: Clean Architecture — `core/` (config, db, security, deps, repository, module registry) + `modules/` (auth, tenants, dashboard, clients, client_notes, pipeline, tasks, finance, products, employees, ai, invites, billing, calendar). Business logic never touches Mongo directly — always through `BaseRepository`.

## Personas
- Owner, Admin, Manager, Member (invite carries role)

## Implemented in V1 + V2 (2026-02)
- Registration + login (JWT); auto workspace creation
- Google OAuth endpoints wired (dormant when keys empty)
- Dashboard: KPIs, revenue trend, upcoming invoices, activity feed
- Clients: CRUD, search, tags, notes
- **Client 360**: detail page with tabs (Timeline / Notes / Deals / Invoices) and stats
- Sales pipeline: Kanban, 6 stages, deal CRUD, summary
- Tasks & Projects: Kanban + list, priorities, statuses
- Finance: invoices with auto-numbering + PDF export, expenses, revenue/expense/profit summary
- Products & Services: CRUD
- Employees / Team: CRUD
- **Team Invites**: token-based invite flow — email sends via Emergent-managed Resend; graceful copy-link fallback if email key missing
- **Stripe Subscriptions**: 3 plans (Starter $19/Pro $49/Business $129), Checkout Session flow, webhook at `/api/stripe/webhook`, status endpoint, `billing/` table per tenant. Uses SMP (Stripe manages tax) in NL sandbox.
- **Google Calendar Sync**: full scaffolding (`/calendar/status|connect|callback|sync-task`) — dormant with 503 until keys set; front-end shows "not configured" state
- AI Assistant: GPT-5.4 with 6 preset tasks
- Settings: company info, module toggle grid (11 current + 7 future), Google Calendar connect card

## Backlog (P1)
- File manager with object storage
- Full-tenant RBAC per-action enforcement (currently: owner/admin can invite; others need extending)
- Reports export to Excel
- Refactor billing gate to also invalidate feature access when plan expires
- Full Google Calendar sync ↔ tasks bi-directional
- WhatsApp integration (Twilio)

## Backlog (P2 — future modules)
- Inventory, POS, Restaurant orders, Marketing automation, Website builder, Customer Portal, Document Management, Accounting depth, Payroll depth, AI Automation, API Marketplace

## Test state (2026-02)
- Backend test suite: **28/28 passing** (`/app/backend/tests/test_iteration2.py`, iteration 3 report)
- Key CRITICAL bug fixed this iteration: `register_module` was overwriting duplicate `code` entries — clients_router had been evicted by client_notes_router. Fix: mount client_notes_router directly from server.py; keep MODULES list unique per code.
