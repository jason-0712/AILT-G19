# Staff accounts and university sign-in

## Current access model

Students can search/browse without an account and cannot write to the database.
Staff sign in with an administrator-provisioned Campus Find email/password.
This is a separate application password, not an HKU Portal password. There is no
public registration or automatic staff access based on an email suffix.

Passwords use salted PBKDF2-SHA256 (600,000 iterations). Only a hash is stored.
Five wrong attempts lock an account for 15 minutes, across sessions/processes.
Staff sessions expire after one hour and are revoked on logout. Every inventory
write and audit read checks the session and current account role in SQL.
Disabling an account takes effect on subsequent operations.

## Provision, reset or disable an account

Run from the repository root with the intended DATABASE_URL configured. These
are administrator commands, never student-facing endpoints:

```powershell
.\.venv\Scripts\python.exe -m scripts.manage_staff add worker@example.com
.\.venv\Scripts\python.exe -m scripts.manage_staff reset-password worker@example.com
.\.venv\Scripts\python.exe -m scripts.manage_staff disable worker@example.com
```

Password entry is hidden. Never pass passwords as command-line arguments.
Use the production connection only for intended production administration.
`storage/deployment.env` and `storage/staff-access.txt` are ignored local setup
artifacts; do not share them or include them in submissions.

## Microsoft / HKU integration (prepared, not activated)

A student's ability to sign in to Portal/Moodle does not grant permission to
register a new university application. Ask HKU ITS/the sponsoring department for
an approved single-tenant Microsoft Entra application registration, or guidance
on HKU's official authentication service. Campus Find does not reuse Portal
cookies, import university passwords or claim official HKU integration.

For an approved Microsoft Entra registration:

1. Register a Web redirect URI:
   `https://campus-find-g19.onrender.com/oauth2callback`.
2. Set server-only environment variables: MS_TENANT_ID, MS_CLIENT_ID,
   MS_CLIENT_SECRET, AUTH_COOKIE_SECRET (at least 32 random characters),
   AUTH_REDIRECT_URI.
3. Start with `python -m scripts.start`. It creates ignored
   `.streamlit/secrets.toml` for Streamlit's OIDC handler.
4. Provision each authorised staff identity by immutable tenant ID/object ID:
   `python -m scripts.manage_staff add worker@example.com --microsoft-identity TENANT_UUID:OBJECT_UUID`.
5. Verify sign-in, wrong-tenant rejection, unregistered-student rejection and
   logout using the actual university tenant before enabling for users.

Microsoft hosts credential entry. Streamlit/Authlib validates the OIDC response;
the app additionally checks tenant, issuer, expiration and an explicitly
registered staff identity. Email and display name are not used to grant staff
access. Students do not receive staff privileges by signing in to Microsoft.

This integration has unit coverage for identity authorization, but no live HKU
sign-in has been tested because registration/consent details are unavailable.
An HKU-specific non-Microsoft OIDC provider would require its approved metadata
and claim mapping; it is not assumed interchangeable.

Sources checked 2 October 2026:
- https://docs.streamlit.io/develop/api-reference/user/st.login
- https://learn.microsoft.com/en-us/entra/identity-platform/quickstart-register-app
- https://its.hku.hk/wp-content/uploads/CF-109i1.pdf
