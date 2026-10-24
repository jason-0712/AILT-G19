"""Deployment entry point; supports Render's injected PORT."""
import os
import sys
from pathlib import Path
from streamlit.web import cli
from lostfound.config import load_settings
from lostfound.database import connect_database, initialize

def main():
    root = Path(__file__).resolve().parent.parent
    os.chdir(root)
    engine = connect_database(load_settings().database_url)
    try:
        initialize(engine)
    finally:
        engine.dispose()
    from lostfound.oidc_setup import configure_microsoft
    configure_microsoft()
    port = int(os.getenv("PORT", "8501"))
    if not 1 <= port <= 65535:
        raise ValueError("PORT must be between 1 and 65535")
    sys.argv = ["streamlit", "run", str(root / "app.py"),
                "--server.address=0.0.0.0", f"--server.port={port}",
                "--server.headless=true", "--browser.gatherUsageStats=false"]
    cli.main()

if __name__ == "__main__":
    main()
