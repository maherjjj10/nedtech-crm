# NED Tech CRM/ERP — Product Requirements

## Original brief
Multi-tenant SaaS CRM/ERP for NED Tech Media. Modular architecture. Sellable as SaaS.

## Key decisions
- **DB**: MongoDB (repository pattern; swappable)
- **Auth**: JWT email/password + Google OAuth (dormant) + platform-owner seed
- **AI**: GPT-5.4 via Emergent LLM key
- **Payments**: Stripe subscriptions (platform sandbox, NL — SMP tax)
- **Email**: Emergent-managed Resend (falls back to copy-link when key missing)
- **API**: FastAPI, `/api/v1/*`; Stripe webhook at `/api/stripe/webhook`

## Role Hierarchy (6 tiers — implemented iteration 5)
| Rank | Role | Scope | Notes |
|------|------|-------|-------|
| 100 | platform_owner | platform | ONE global. Immutable (`protected=true`). Auto-seeded from `PLATFORM_OWNER_EMAIL` on startup. Cannot be deleted/demoted/suspended via API. Can impersonate any tenant. |
| 90 | super_admin | platform | Can view/manage all tenants + users. Can grant admin/manager/etc. Cannot grant super_admin (only platform_owner can). Cannot touch protected accounts. |
| 60 | admin | tenant | Full workspace access. Invites, module toggles, billing. |
| 40 | manager | tenant | Manages team + records within workspace. |
| 20 | employee | tenant | Standard user. |
| 10 | viewer | tenant | Read-only. |

`platform_role` and `tenant_role` (`role`) are stored separately on `users` documents — never collapsed into one enum.

## Impersonation
- POST `/api/v1/platform/impersonate {tenant_id, reason}` (super_admin+) → issues ephemeral JWT with `impersonating_from` + `original_tenant_id` claims.
- POST `/api/v1/platform/impersonate/stop` → restores original identity.
- Every start/stop written to `platform_audit` (`GET /api/v1/platform/audit`).
- Frontend shows a black sticky banner across every page during impersonation with an "Exit impersonation" button.
- Writes performed while impersonating go into the target tenant (correct scope); no data mutation on the platform_owner user.

## Modules shipped (V1–V5)
Dashboard · Clients + Client 360 (Timeline / Notes / Deals / Invoices) · Sales pipeline Kanban · Tasks (Kanban+list) · Projects · Finance (invoices/PDF + expenses + summary) · Products & Services · Employees + Team Invites · AI Assistant · Billing (Stripe subscriptions) · Google Calendar Sync (dormant scaffold) · Platform Admin (this iteration) · Settings.

## Backlog
- Object File Storage (drag-and-drop uploads on clients/projects)
- Feature gating by plan
- Excel report exports
- WhatsApp integration (Twilio)
- Full RBAC per-action across every module (currently baseline; deepen)

## Test state (iteration 10)
- **15/16 backend** passing on iter10; the one guard-order failure (convert-twice returned 400) has been fixed → now returns 409.
- Frontend E2E for both Quote Flow and Contracts passes end-to-end (login → create → share/send → public accept/sign → convert → invoice appears).
- Password self-service verified across backend restart
- Global search across tenants/users/invoices/clients
- 30-min impersonation TTL verified via JWT `exp - iat`
- super_admin grant permission ceiling enforced

## Iteration 10 — Quote Flow + Contracts (frontend wiring & bugfixes)
- Wired `/contracts`, `/public/quote/:token`, `/public/contract/:token` into `App.js`.
- Added **Contracts** link to Sidebar (`data-testid="nav-contracts"`).
- Added **Quotes tab** to `/finance` with New/Share/Convert/Copy/Delete actions and full line-item editor (all rows have data-testids `line-desc-N`, `line-qty-N`, …).
- Backend fixes in `quote_flow/routes.py`:
  - `POST /quotes/{qid}/share` now returns **409** if quote is already accepted/rejected/converted (no more silent status regression).
  - `POST /quotes/{qid}/convert` reorders guards so a second call returns **409** ("Already converted") instead of 400. Also now returns **201 Created**.
  - Added `GET /quotes/{qid}` for parity with invoices.
- All fixes curl-verified.

## Files added this iteration
- `/app/backend/app/core/roles.py` — hierarchy + normalize + can_grant
- `/app/backend/app/core/seed.py` — idempotent platform_owner bootstrap
- `/app/backend/app/modules/platform/routes.py` — cross-tenant super-admin surface + impersonation + audit
- `/app/frontend/src/pages/Platform.jsx` — Platform Admin panel (tenants / users / audit)
- `/app/frontend/src/components/layout/ImpersonationBanner.jsx`
