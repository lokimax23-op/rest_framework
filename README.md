# HiiT Student Course Management & Resource Portal

## Local setup

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Edit `.env` with provider credentials. Never commit `.env` or share provider
secrets in chat.

## Deploy to Render

1. Push this repository to GitHub, then choose **New + → Blueprint** in Render
   and select the repository. Render reads [render.yaml](./render.yaml) to
   create the Django web service and PostgreSQL database, and connect the
   database through `DATABASE_URL`.
2. Wait for the first deployment to finish. The blueprint generates a
   production `SECRET_KEY`, sets `DEBUG=False`, collects static assets, and
   applies migrations during build.
3. In the Render web service's **Environment** settings, add any optional
   Google, Paystack, Stripe, and email variables from `.env.example`. Save and
   redeploy after changing environment variables.
   Django automatically trusts Render's `RENDER_EXTERNAL_HOSTNAME` for host
   validation and CSRF, including when Render assigns a generated `onrender.com`
   hostname.
4. Set the Google OAuth authorized redirect URI to
   `https://hiit-learning-hub.onrender.com/accounts/google/login/callback/`.
   Update `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` if using a custom domain.
5. Create the first production admin from the service's Shell:

   ```sh
   python manage.py createsuperuser
   ```

   Then visit `https://hiit-learning-hub.onrender.com/admin/`.

The included Blueprint uses Render's free web-service and database plans for
evaluation. Free databases are temporary and can expire; choose a paid,
persistent PostgreSQL plan for real users. SQLite and the checked-in local
database are not used on Render. Uploaded profile images are stored on the
service filesystem by default and may not persist across deploys; use persistent
object storage or a paid persistent disk before relying on profile uploads.

If deploying an existing manually-created Render service, configure its
`DATABASE_URL` to point to a persistent PostgreSQL database, then run
`python manage.py migrate` from the service Shell. A fresh database will have
empty tables until migrations are applied; any data stored in a previous
ephemeral SQLite database is separate and is not migrated automatically.

## Deploy to Vercel

1. Import the GitHub repository into Vercel. Vercel detects Django from the
   root-level `manage.py` and serves the WSGI application in
   `rest/wsgi.py`; no custom `vercel.json` is needed. Vercel also runs
   `collectstatic` during the build and serves static files from its CDN.
2. Before the first deploy, configure these **Production** environment
   variables in the Vercel project:
   - `SECRET_KEY`: a unique, private Django secret.
   - `DEBUG`: `False`.
   - `DATABASE_URL`: a persistent PostgreSQL connection string. Use the
     provider's pooled connection URL when available; production does not fall
     back to SQLite.
3. Deploy the project. Vercel's `VERCEL_URL` is added automatically to
   `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS`. If you use a custom domain, add
   its hostname to `ALLOWED_HOSTS` and its full `https://` origin to
   `CSRF_TRUSTED_ORIGINS`, then redeploy.
4. Apply database migrations after the database and environment variables are
   configured. From a Vercel-linked local checkout with the Vercel CLI
   installed, run:

   ```sh
   vercel env run --environment=production -- python manage.py migrate
   ```

   This runs migrations against the linked project's environment without
   copying its secrets into a file. Run it again after adding new migrations.
5. Add optional Google, Paystack, Stripe, and email settings from
   `.env.example` to Vercel's Production environment as needed. Set the Google
   OAuth callback and payment webhooks to your deployed domain.

Vercel runs Django as a serverless function. Use persistent PostgreSQL and
external object storage for profile uploads: files written to the function's
local filesystem are not durable. Static assets are handled separately by the
Vercel CDN. Serverless database connections are not kept open between requests.

## Gmail SMTP

Set `EMAIL_HOST_USER` and `EMAIL_HOST_PASSWORD` in `.env`. Use a Google
App Password (with 2-Step Verification enabled), not your regular Google
account password. SMTP uses `smtp.gmail.com:587` with TLS by default. If no
SMTP password is configured, development email is printed to the console.

Student registration sends an email verification link; the account cannot log
in until the link is used. Every password or Google sign-in then requires a
six-digit email code that expires after 10 minutes. The login page uses the
configured email backend, so set `EMAIL_HOST_PASSWORD` before enabling this for
real users.

## Google sign-in

Create a Google OAuth web client and set `GOOGLE_OAUTH_CLIENT_ID` and
`GOOGLE_OAUTH_CLIENT_SECRET` in `.env`. Add this authorized redirect URI to the
Google client (adjust the host/port for your deployment):

```text
http://127.0.0.1:8000/accounts/google/login/callback/
```

The Google sign-in button appears when both values are configured. First-time
Google users are asked for their HiiT phone number and registration number to
create their student profile.

## Newsletter

The homepage newsletter form saves a unique email subscription in the portal
database. Manage subscriber records from Django admin. Email campaign delivery
is not configured by this feature.

## Paid HiiT Plus membership

The monthly membership is **₦5,000**. Course browsing and course enrollment are
separate from the optional portal membership.

### Paystack test mode

1. In the Paystack test dashboard, create a recurring monthly plan for
   **₦5,000** and copy its plan code.
2. Put the test secret key in `PAYSTACK_SECRET_KEY` and that plan code in
   `PAYSTACK_PLAN_CODE`.
3. Configure the Paystack webhook URL as
   `https://<your-host>/webhooks/paystack/`.

### Stripe test mode

1. Set a Stripe test secret key (`sk_test_...`) as `STRIPE_SECRET_KEY`.
2. Configure a webhook endpoint at `https://<your-host>/webhooks/stripe/` for
   `checkout.session.completed`, `invoice.payment_failed`,
   `customer.subscription.updated`, and `customer.subscription.deleted`.
3. Set its signing secret as `STRIPE_WEBHOOK_SECRET`.

The checkout endpoints reject live-mode secret keys. Payment provider
credentials are required before checkout can be enabled; without them, the
membership page explains which configuration is missing.

## Portal URLs

- `/` — portal home and newsletter signup
- `/courses/` — searchable course catalog
- `/membership/` — paid membership status and checkout
- `/accounts/login/` — username/password login and configured Google sign-in
- `/accounts/google/login/` — Google OAuth initiation
- `/dashboard/` — student dashboard
- `/admin/` — staff course and subscriber administration
