# TrainBook — Online Training Booking App

Django full-stack app for booking seats in live online training sessions — course catalogue, scheduled sessions with seat capacity, manual bank-transfer payment with admin verification, a REST API, SEO, and basic security hardening (CSRF, login lockout).

## Contents
- [Project structure](#project-structure)
- [Roles](#roles)
- [Quick start](#quick-start)
- [Payment flow](#payment-flow)
- [REST API](#rest-api-django-ninja)
- [SEO](#seo)
- [Security](#security)
- [Notes](#notes)

## Project structure
- **`training_booking/`** — project settings, root URLs, the REST API mount (`api.py`)
- **`accounts/`** — signup/login/logout, admin dashboard, admin CRUD for users
- **`courses/`** — Course + Session (scheduled batch with trainer/capacity), public browse pages, admin CRUD for courses & sessions, SEO settings
- **`bookings/`** — user booking of a session seat, bank-transfer payment + admin verification, reschedule, cancel
- **`templates/`** — shared base template + partials (Bootstrap 5)
- **`static/`** — site CSS

## Roles
- **Staff/admin** (`is_staff=True`): full CRUD on Users, Courses, and Sessions via `/accounts/admin-panel/`, plus payment verification and bank/QR settings via `/bookings/admin-panel/`
- **Regular user**: browse courses, book a session seat, pay via bank transfer, view/reschedule/cancel own bookings via `/bookings/`

## Payment flow
1. User books a session → booking status `pending_payment`.
2. Payment page shows the bank's QR code + account details (set once by admin under **Bank / QR settings**). User pays manually via their banking app, then clicks "I've made the payment" → status becomes `awaiting_verification`.
3. Admin opens **Payment verification** in the admin dashboard, checks the bank account received the money, and clicks **Approve** (or **Reject** to bounce it back to `pending_payment`).
4. On approval, status becomes `confirmed` and the user is emailed the session's meeting link + date/time (acts as the reminder). The link also appears on their "My Bookings" page and the payment page.

Emails are currently printed to the `runserver` console (`EMAIL_BACKEND = console`, see `training_booking/settings.py`). Point `EMAIL_BACKEND`/`EMAIL_HOST*` at a real SMTP server to send them for real.

Set each session's meeting link (Zoom/Meet/Teams URL) when creating/editing it under **Sessions** in the admin dashboard.

## Quick start

```bash
git clone https://github.com/faizbek3991/djangobookingclass.git
cd djangobookingclass

python -m venv venv
venv\Scripts\activate        # Windows — use `source venv/bin/activate` on macOS/Linux

pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Then visit:
- **http://127.0.0.1:8000/** — public site (course list → course detail → book a session, requires login)
- **http://127.0.0.1:8000/accounts/admin-panel/** — admin dashboard (staff users only — use the superuser you just created)
- **http://127.0.0.1:8000/admin/** — Django's built-in admin (extra, not required for day-to-day use)
- **http://127.0.0.1:8000/api/docs** — REST API docs (see [REST API](#rest-api-django-ninja) below)

> On Windows PowerShell, if `venv\Scripts\Activate.ps1` is blocked by execution policy, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or just call `venv\Scripts\python.exe manage.py runserver` directly without activating.

## Notes
- Payment is a mock confirmation step — no real payment gateway is integrated.
- A booking is "cancelled" (soft state), not deleted, so history is kept.
- Session capacity is enforced: booking fails once a session is full.

## REST API (django-ninja)

A full REST API lives alongside the Django template views at `/api/` — same database, same business logic, so the web pages and the API stay in sync. Interactive docs (Swagger UI) are at **http://127.0.0.1:8000/api/docs**; the raw OpenAPI schema is at `/api/openapi.json`.

**Auth**: Django session-cookie based (reuses the same login as the web app, including the [login lockout](#security)). Flow for a JS client:
1. `GET /api/auth/csrf/` — sets the `csrftoken` cookie.
2. `POST /api/auth/login/` (or `/signup/`) with `{"username", "password"}` — sets the session cookie.
3. On every following `POST`/`PUT`/`DELETE`, send header `X-CSRFToken: <value of the csrftoken cookie>` and include cookies (`credentials: "include"` in fetch).

> **Gotcha that will make requests silently fail (403 "CSRF check Failed"):** Django rotates the CSRF token whenever a user logs in — it's a deliberate security feature, not a bug. So the token you read *before* calling `/auth/login/` is no longer valid afterward. **Never cache the CSRF token in a variable** — always read it fresh from the `csrftoken` cookie immediately before each mutating request:
> ```js
> function getCsrfToken() {
>   return document.cookie.split("; ").find(r => r.startsWith("csrftoken="))?.split("=")[1];
> }
> // call getCsrfToken() again right before every POST/PUT/DELETE — don't reuse an old value
> fetch("/api/bookings/", {
>   method: "POST",
>   credentials: "include",
>   headers: { "Content-Type": "application/json", "X-CSRFToken": getCsrfToken() },
>   body: JSON.stringify({ session_id: 1 }),
> });
> ```
> If a create/update call returns 403 and the thing you created doesn't show up afterward, check this first — the request never actually succeeded.

**Endpoints** (all under `/api/`):
| Area | Path | Auth |
|---|---|---|
| Auth | `auth/csrf/`, `auth/signup/`, `auth/login/`, `auth/logout/`, `auth/me/` | public / self |
| Courses (public) | `courses/`, `courses/{slug}/` | public |
| My bookings | `bookings/`, `bookings/{id}/`, `bookings/{id}/submit-payment/`, `bookings/{id}/reschedule/`, `bookings/payment-settings/` | logged-in user, own bookings only |
| Admin: users | `admin/users/`, `admin/users/{id}/` | staff |
| Admin: courses | `admin/courses/`, `admin/courses/{id}/`, `admin/courses/{id}/image/` | staff |
| Admin: sessions | `admin/sessions/`, `admin/sessions/{id}/` | staff |
| Admin: SEO | `admin/seo/`, `admin/seo/image/` | staff |
| Admin: payment verification | `admin/payments/`, `admin/payments/{id}/approve/`, `admin/payments/{id}/reject/` | staff |
| Admin: payment settings | `admin/payment-settings/`, `admin/payment-settings/image/` | staff |

Image fields (course social-share image, SEO default image, bank QR code) are set via their own `POST .../image/` endpoint as `multipart/form-data` (field name `image`), separate from the main JSON create/update body.

Not yet added: pagination on list endpoints (all return the full list — fine at this scale, revisit with `@paginate` if course/user counts grow large) and a non-cookie (token) auth mode for a fully separate frontend origin or a mobile app.

## SEO
- **Per-course**: each course's edit page (**Courses → edit**) has optional "meta title", "meta description" and a social-share image. Left blank, they fall back to the course's title/description automatically.
- **Site-wide defaults**: admin dashboard → **SEO settings** — site name, default title/description, default social-share image, and a Google Search Console verification code. Used on pages without their own SEO fields (course list/home).
- `/sitemap.xml` — auto-generated from active courses (no admin action needed).
- `/robots.txt` — auto-generated, blocks the admin-panel/booking/Django-admin paths from being crawled.
- Every page also gets a `<link rel="canonical">` and Open Graph/Twitter card tags automatically from the above.

## Security
- **XSS**: Django template auto-escaping is on everywhere (no `|safe`/`mark_safe`/`autoescape off` used anywhere in the app), so user-supplied text (names, course descriptions, etc.) is always HTML-escaped on render.
- **SQL injection**: all queries go through the Django ORM (no `.raw()`/`.extra()`/hand-built SQL anywhere in the app), so query parameters are always sent separately from the SQL, not string-interpolated.
- **CSRF**: every POST form includes `{% csrf_token %}` and `CsrfViewMiddleware` is enabled.
- **Login rate limiting**: `accounts/forms.py` (`TrainingLoginForm`) locks an account out for `LOGIN_ATTEMPT_LOCKOUT_MINUTES` (default 15) after `LOGIN_ATTEMPT_LIMIT` (default 5) failed attempts from the same IP, keyed per username so it can't be used to lock out every account platform-wide. Tune both in `settings.py`. The counter lives in Django's default cache (in-memory, per-process) — fine for one dev/app-server process; if you ever run multiple worker processes, point `CACHES` at a shared backend (e.g. Redis) so the lockout is shared across workers.
- **Before deploying for real**: `settings.py` still has `DEBUG = True` and the auto-generated dev `SECRET_KEY` committed in the file — move both to environment variables (`DEBUG = False`, a fresh random `SECRET_KEY`) and set `ALLOWED_HOSTS` before putting this anywhere public.
