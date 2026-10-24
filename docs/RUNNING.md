# Running Campus Find

[Application](https://campus-find-g19.onrender.com) 路
[Project page](https://campus-find-g19-project.onrender.com)

An AILT9019 Group 19 lost-and-found project. Students search; authorised centre
staff record items and photos, then confirm collection to remove them.
Independent student work, not an official HKU service.

## Use the app

- **Search:** describe an item; optionally filter by category and found place.
- **Catalogue:** browse available records/photos with the same filters.
- **Staff:** sign in with a separate administrator-provisioned app account.
  Record category, colour, description, place and optional photo. To remove an
  item, select it under Confirm collection and confirm the in-person handover.

Locations follow the supplied campus map: MW, HW, MB, JCT, etc.; facilities
without supplied abbreviations retain their names. Older seed records are
marked "Not recorded"; their found locations have not been invented.

Microsoft sign-in is prepared but needs HKU-approved registration. Do not use
your HKU password in the app's password form. See
[staff/sign-in setup](STAFF_AND_SIGNIN.md).

## Run locally

Python 3.13, Windows PowerShell:

```powershell
# Open a terminal in the project root
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m streamlit run app.py --server.address=127.0.0.1
```

Open http://localhost:8501. If busy, append --server.port=18501.
On macOS/Linux use .venv/bin/python. SQLite storage/items.db is created
automatically. For an empty initial catalogue set SEED_DEMO_DATA=false before
first startup; otherwise 30 fictional examples are seeded exactly once.

Use DATABASE_URL for PostgreSQL. The deployed app uses Neon PostgreSQL to retain
records/photos across Render restarts. Render's ephemeral SQLite is read-only.
See [deployment](DEPLOYMENT.md) and [architecture](ARCHITECTURE.md).

To provision staff, run:
`python -m scripts.manage_staff add worker@example.com`.
This prompts for a separate app password. There is no public staff registration.

## Verify and evaluate

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m evaluation.run --mode keyword
```

Set TEST_DATABASE_URL only to a dedicated test database for PostgreSQL tests.
Tests cover persistence, legacy migration, photo handling, staff/student roles,
session expiry, lockout, collection, search and the UI workflow. CI also builds
the Docker image.

Try "black insulated bottle with a silver lid"; the fictional LF-001 is first.
The synthetic query set is maintained in `evaluation/queries.json`. The runner
writes reports to ignored `evaluation/results/`. AI evaluation requires a
configured provider and makes real model requests; keyword evaluation runs
locally. Treat results as development checks, not independent accuracy estimates.

## Optional model and Microsoft configuration

Qwen Flash uses the Beijing workspace endpoint in non-thinking JSON mode.
Copy .env.example to ignored .env and configure the LLM fields for local use;
production secrets belong in Render environment settings. See [Qwen setup](QWEN_SETUP.md).
AI mode stays explicitly unavailable without credentials.

Microsoft OIDC requires approved registration and the server-only MS_* and AUTH_*
variables. Use `python -m scripts.start` to generate the private auth configuration.
The Microsoft page handles university credentials; only registered staff
identities receive inventory permissions.

Never commit .env, database files, staff credentials or .streamlit/secrets.toml.

## Standalone HTML

Open [website/index.html](../website/index.html) directly in a browser. It explains
the application and includes an embedded running screenshot, with no external
assets or build step. Update the labelled repository-link placeholder when
publishing the page.
