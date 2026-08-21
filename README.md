# Dalton ECI Alumni Website — Render + Supabase Edition

This package is prepared for free-tier deployment using **Render** for the Flask website and **Supabase Postgres** for persistent alumni records.

## Included features
- Public Dalton ECI Alumni homepage
- Alumni registration form
- Joining fee displayed as **JMD $2,000**
- Registration status starts as **Pending Review**
- Payment status starts as **Pending**
- Optional payment/reference number field
- Private administrator login
- Private searchable admin dashboard
- Admin can mark payment **Pending / Verified / Not Received**
- Admin can mark membership **Pending Review / Active / Inactive / Declined**
- CSV export
- CSRF protection for submitted forms
- Render health-check endpoint at `/health`
- Supabase/PostgreSQL support through `DATABASE_URL`

## Important privacy rule
Do not put bank account numbers, passwords, Supabase credentials, or other secrets directly in the source code. Put secrets only in Render Environment Variables.

## A. Create the free Supabase database
1. Create a Supabase account and a new free project.
2. In the Supabase project, click **Connect**.
3. Copy a PostgreSQL connection string suitable for your hosting environment. The **Shared Pooler / Session mode** is a useful choice when IPv4 compatibility is needed.
4. Keep this connection string private. It contains your database password.
5. You do **not** need to manually create the `alumni` table. The website creates it automatically on first start.

## B. Put this project on GitHub
Render normally deploys source code from a Git repository.
1. Create a free GitHub account if needed.
2. Create a new repository, for example `dalton-eci-alumni`.
3. Upload the **contents of this ZIP** to the repository. Upload the files themselves, not one unopened ZIP file.
4. Do not upload a real `.env` file or any password/connection string.

## C. Deploy on Render
1. Create/sign in to Render.
2. Choose **New > Web Service**.
3. Connect the GitHub repository containing this project.
4. Use these settings:
   - Language: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
   - Instance Type: `Free` (if available on your account)
   - Health Check Path: `/health`
5. Add these Environment Variables:
   - `DATABASE_URL` = your private Supabase PostgreSQL connection string
   - `ADMIN_USERNAME` = your chosen admin username
   - `ADMIN_PASSWORD` = a strong private password
   - `SECRET_KEY` = a long random private string
   - `COOKIE_SECURE` = `1`
6. Create/deploy the Web Service.
7. When deployment finishes, Render will show the **real `onrender.com` URL**. That is the link to send to visitors.

## D. Your links after publishing
If Render gives you a URL such as:
`https://YOUR-SITE.onrender.com`

Then:
- Main website: `https://YOUR-SITE.onrender.com`
- Join the Alumni: `https://YOUR-SITE.onrender.com/register`
- Admin login: `https://YOUR-SITE.onrender.com/admin/login`

These are patterns only. Use the exact URL Render gives you after deployment.

## E. First test before sharing
1. Open `/register` and submit a test registration.
2. Log in at `/admin/login` using the credentials you placed in Render.
3. Confirm the test record appears.
4. Open the record and mark payment **Verified** and membership **Active**.
5. Export CSV and confirm the record is present.
6. Only after successful testing should you share the registration URL publicly.

## Local testing (optional)
If `DATABASE_URL` is not set, the application falls back to a local SQLite database for testing only. Do not rely on that SQLite file for persistent Render storage.
