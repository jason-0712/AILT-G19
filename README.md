# Campus Find — AILT9019 Group 19

Campus Find is a campus lost-and-found application. Students can search
for items using natural-language descriptions and location filters.
Authorised staff can record found items, attach photos, and confirm collection.

This is an independent student project, not an official HKU service.

## Project Links

- Public project webpage: https://campus-find-g19-project.onrender.com/
- Live application: https://campus-find-g19.onrender.com/
- Presentation: https://youtu.be/TaAfxf5Tf-U
- Demo: https://youtu.be/Nzw9wq_CKsU

## Main Features

- Keyword search and optional AI matching using Qwen.
- Category and campus-location filters.
- AI result checks against item IDs and quoted source text.
- Staff inventory management, photos, and collection records.
- SQLite for local development and PostgreSQL for hosted storage.

## Installation

Requirements: Python 3.13 and Git.

```bash
git clone https://github.com/jason-0712/AILT-G19.git
cd AILT-G19
python -m venv .venv
```

Activate the virtual environment:

**Windows PowerShell**
```powershell
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run the Application

```bash
python -m streamlit run app.py --server.address=127.0.0.1
```

Open http://localhost:8501 in your browser.

The local SQLite database is created automatically. By default,
30 fictional example records are seeded on first startup.
Set `SEED_DEMO_DATA=false` before the first startup to begin with an empty catalogue.

Keyword search works without model credentials. AI matching requires
provider configuration; see [Qwen setup](docs/QWEN_SETUP.md).
Never commit API keys, passwords, `.env`, or Streamlit secrets.

For staff-account setup, see [Staff and sign-in](docs/STAFF_AND_SIGNIN.md).

## Testing

Install the development dependencies and run the tests:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

The tests cover database persistence, inventory operations, photo handling,
access control, search, and application workflows.

PostgreSQL tests require `TEST_DATABASE_URL` pointing to a dedicated test database.

## Evaluation

Run the keyword-search evaluation:

```bash
python -m evaluation.run --mode keyword
```

With AI credentials configured, run:

```bash
python -m evaluation.run --mode ai
```

The evaluation uses fictional records and synthetic queries from
`evaluation/queries.json`. Reports are written to `evaluation/results/`.

Results are development checks on a small synthetic dataset, not independent
estimates of real-world accuracy. AI evaluation makes real model requests.

## Limitations and Privacy

- Matching suggestions do not establish ownership.
- Keyword search may return items that share words but differ in meaning.
- AI matching may fail or return unsuitable suggestions.
- Staff must verify ownership in person before handing over an item.
- Users should omit names, contact details, and ID numbers from search queries.

## Further Documentation

- [Installation, execution and testing details](docs/RUNNING.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Qwen configuration](docs/QWEN_SETUP.md)
- [Staff accounts and sign-in](docs/STAFF_AND_SIGNIN.md)
