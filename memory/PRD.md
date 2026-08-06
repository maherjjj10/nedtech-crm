# NED Tech CRM/ERP — Product Requirements

## Original brief (verbatim)
Multi-tenant SaaS CRM/ERP for NED Tech Media. Modules: CRM, Sales pipeline, Tasks/Projects, Finance (quotes/invoices/expenses/reports), Products, HR/Employees, Files, Calendar, Communication, Reports, Settings, AI Assistant. UI like HubSpot/Linear/Stripe/Notion. Modular (each module toggleable). Multi-tenant. Sellable as SaaS.

## Decisions
- **DB**: MongoDB (repository pattern in place; swappable)
- **Auth**: JWT email/password + Google OAuth ready (needs client id/secret)
- **AI**: GPT-5.4 via Emergent LLM key
- **Payments**: Stripe (keys not yet provided)
- **Email**: Resend (managed, keys not yet provided)
- **API**: FastAPI, `/api/v1/*`
- **Architecture**: Clean Architecture — `core/` (config, db, security, deps, repository, module registry) + `modules/` (auth, tenants, dashboard, clients, pipeline, tasks, finance, products, employees, ai). Business logic never touches Mongo directly — always through `BaseRepository`.
- **Multi-tenant**: `tenant_id` on every doc; compound indexes; module_gate dep blocks disabled modules per tenant.

## Personas
- **Owner** (default role on registration) — full access, billing, module toggles
- **Admin / Manager / Member** — role-gated actions (baseline in place; per-endpoint hardening deferred)

## Implemented in V1 (2026-02)
- Registration + login with JWT; auto workspace creation
- Google OAuth endpoints (`/auth/google/{login,callback}`) wired via Authlib (activates when GOOGLE_CLIENT_ID/SECRET are set)
- Dashboard with KPIs, 6-month revenue trend, upcoming invoices, activity feed
- Clients: CRUD, search, tags, notes; activity log entries
- Sales pipeline: Kanban with 6 default stages, deal CRUD, per-stage summary
- Tasks: Kanban + list view, priorities, statuses
- Projects: basic CRUD
- Finance: invoices (auto-numbered, tax computation, PDF export via reportlab), expenses, revenue/expense/profit summary
- Products & services: CRUD with SKU, category, price, cost, tax
- Employees: profile CRUD with role, salary, department
- AI Assistant: GPT-5.4 via emergentintegrations with 6 tasks (summarize, quote, email, sales analysis, follow-up, chat) — verified working
- Settings: company info + module toggle grid (11 current + 7 future modules) 
- Dark & light theme, Cabinet Grotesk headings + Satoshi body

## Backlog (P1)
- Client detail page (timeline, notes tab, files tab, related deals/invoices)
- Calendar view for tasks + Google Calendar sync
- Team invites (invite existing tenant), full RBAC enforcement per module action
- Stripe subscription billing (checkout + webhook) — playbook received
- Resend email templates (invoice-sent, welcome) — playbook received
- File manager with object storage
- Reports export to Excel
- Advanced RBAC roles editor

## Backlog (P2 — future modules)
- Inventory, POS, Restaurant orders (NED Order)
- Marketing automation, Website builder
- Customer Portal, Document Management
- Accounting depth, HR & Payroll depth, AI Automation, API Marketplace
- WhatsApp integration (Twilio)

## Known state
- All backend endpoints verified via testing agent (94% pass, 1 HIGH bug fixed: users.google_sub partial index).
- Auth via `Authorization: Bearer <token>`; module gating via `tenants.modules.<code>` boolean.
