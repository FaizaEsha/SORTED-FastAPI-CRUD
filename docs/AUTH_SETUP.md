# FlyRank A4: authentication setup and verification

This extends SORTED with Supabase Auth. The original dashboard, SQLite task table,
task URLs and their behavior are preserved. Tasks remain the original shared public
CRUD exercise; they are **not private per user**. User ownership is a later assignment.
Protected profile and dashboard endpoints demonstrate the new authentication guard.

## 1. Create your Supabase project

1. Visit https://supabase.com/dashboard and sign in.
2. Create a free organization if needed, then click **New project**.
3. Name it `SORTED Auth`, generate and privately save the database password, select
   a nearby region and wait for provisioning.
4. Find the Project URL in **Connect** or **Settings → API**.
5. Find the public anon/publishable key in **Settings → API Keys**. Never use a
   service_role or secret key. This application does not need elevated privileges.
6. In the repository folder, copy `.env.example` to `.env`. Replace the two placeholder
   values with your own URL and public key. Do not commit `.env`.
7. Email confirmation can stay enabled: use a real test email, confirm the signup
   email, then log in. For the assignment's immediate signup/login exercise only,
   you may disable Confirm email under **Authentication → Sign In / Providers → Email**.
   Restore it before using the project beyond practice.

## 2. Install and run (Windows PowerShell)

Open PowerShell in the repository folder:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env with your project URL and public key before continuing.
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Do not overwrite an existing `.env` when repeating setup. The final line is the
single command that runs the whole application at http://127.0.0.1:8000.
Existing CRUD and `/app` still work without Supabase configuration; auth requests
return a clear 503 until configured. Successful auth requests verify connectivity.

## 3. Authentication API

| Method | Endpoint | Bearer token? | Success |
|---|---|---|---|
| POST | `/auth/signup` | No | 201: id, email, created_at |
| POST | `/auth/login` | No | 200: access_token, refresh_token, token_type |
| GET | `/public/info` | No | 200: public welcome message |
| GET | `/protected/profile` | Yes | 200: id, email, created_at |
| GET | `/protected/dashboard` | Yes | 200: welcome and verified user ID |
| POST | `/auth/logout` | Yes | 204: empty body |

Signup/login accept JSON with `email` and `password`. Missing, empty or malformed
input returns 400. Wrong login credentials return 401 with
`{"error":"Invalid login credentials"}`. Missing/malformed bearer headers return
401 with `{"error":"Access token required"}`. Invalid/expired tokens return 401
with `{"error":"Invalid or expired token"}`. Network failures return 503.

The reusable FastAPI dependency calls Supabase `get_user(token)`; it never trusts
an unverified JWT payload. Each request gets its own non-persistent client.
Logout uses the caller's verified JWT with Supabase's logout endpoint via the SDK,
and scope `local` so other sessions are not signed out. Despite the SDK namespace
`auth.admin.sign_out`, this call sends the caller JWT and requires no service key.
Passwords are forwarded to Supabase, never stored or hashed locally.

Logout revokes the current session's refresh capability. An already-issued access
JWT can remain valid until expiry: do not claim immediate JWT invalidation.
401 means identity could not be verified; 403 means a verified identity lacks
permission. No role-restricted 403 route is implemented in this required-scope build.

## 4. Live PowerShell checks

With the server running, open a second PowerShell window in this folder. Use a
dedicated test account; do not paste passwords or returned tokens into issues.

```powershell
$testEmail = Read-Host 'Your test email'
$testPassword = Read-Host 'Test password' -AsSecureString
$plainPassword = [System.Net.NetworkCredential]::new('', $testPassword).Password
$body = @{ email = $testEmail; password = $plainPassword } | ConvertTo-Json
$plainPassword = $null
# curl -i prints response headers/status as requested by the assignment.
$body | curl.exe -i -X POST http://127.0.0.1:8000/auth/signup -H 'Content-Type: application/json' --data-binary '@-'
# Confirm the email first if email confirmation is enabled.
$login = Invoke-RestMethod http://127.0.0.1:8000/auth/login -Method Post -ContentType 'application/json' -Body $body
$body = $null
$headers = @{ Authorization = "Bearer $($login.access_token)" }
curl.exe -i http://127.0.0.1:8000/public/info
curl.exe -i http://127.0.0.1:8000/protected/profile
curl.exe -i http://127.0.0.1:8000/protected/profile -H "Authorization: Bearer $($login.access_token)"
curl.exe -i http://127.0.0.1:8000/protected/dashboard -H "Authorization: Bearer $($login.access_token)"
curl.exe -i http://127.0.0.1:8000/protected/profile -H "Authorization: Bearer x$($login.access_token)"
curl.exe -i -X POST http://127.0.0.1:8000/auth/logout -H "Authorization: Bearer $($login.access_token)"
```

Expected statuses: signup 201; login 200; public 200; missing token 401; profile and
dashboard with the real token 200; tampered token 401; logout 204. Reuse the old
token after logout and record the actual response and the expiry caveat above.

## 5. Swagger check and screenshot

1. Open http://127.0.0.1:8000/docs.
2. Expand **POST /auth/login**, click **Try it out**, fill in the test credentials,
   then click **Execute**.
3. Copy only `access_token` from the response.
4. Click **Authorize**, paste the token without the word Bearer, click **Authorize**,
   and close the dialog.
5. Execute **GET /protected/profile**, then **GET /protected/dashboard**. Both should
   return 200. Each protected endpoint, including logout, has a padlock.
6. Collapse login so its password and tokens are hidden. Capture the profile's 200
   response and lock icon with Windows+Shift+S. Save as `docs/swagger_auth.png`.
7. Add `![Authorized Swagger profile](docs/swagger_auth.png)` to the root README
   only once that real screenshot exists. Never publish a screenshot of a token.

## 6. Automated checks and honest submission status

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
```

31 offline tests pass, with a mocked provider and isolated SQLite files. They cover
CRUD preservation, public routes, credential validation, safe responses, bad tokens,
the reused guard, caller-specific logout, outages and OpenAPI bearer declarations.
GitHub Actions runs the same checks on pushes and pull requests.

Live verification on October 30, 2026: signup returned 201, the owner confirmed the
email, login returned 200 with access and refresh tokens, both protected routes
returned 200, missing/tampered tokens returned 401, and a wrong password returned
401. Logout returned 204 with an empty body; token reuse after logout returned 401
in this project. That observation does not guarantee every Supabase configuration
immediately rejects every revoked JWT. A separate curl login/protected/tamper/logout
flow passed, and Swagger Authorize + Try it out returned 200 for both protected routes.
The root README includes real screenshots of locked routes and the authorized HTTP
200 result, cropped to exclude passwords, bearer tokens and account metadata.

The implementation was AI-assisted; no claim is made that stages were completed by
hand. Six meaningful implementation commits separate configuration, authentication,
integration, tests, CI and documentation. They do not fabricate the PDF's historical
stage-by-stage learning checkpoints. The optional AI-rematch exercise and stretch
features have not been submitted or claimed.

## 7. GitHub access

Run `gh auth login`, select GitHub.com → HTTPS → Login with a web browser, and sign
in as the repository owner. Never send a personal access token in chat. This change
was developed on `feature/flyrank-a4-supabase-auth` and submitted as pull request #1,
with automated checks and live verification before merge.
Existing Git history and ZIP backups are preserved. No force push is needed.
