import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent

@dataclass(frozen=True)
class Settings:
    database_url: str = field(default="sqlite:///storage/items.db", repr=False)
    api_key: str = field(default="", repr=False)
    base_url: str = ""
    model: str = ""
    provider: str = ""
    timeout: float = 20.0
    requests_per_minute: int = 10

    @property
    def ai_ready(self):
        url = urlsplit(self.base_url)
        return bool(self.api_key and self.model and self.provider and
                    url.scheme == "https" and url.netloc and not url.username
                    and not url.password and not url.query and not url.fragment)

def load_settings():
    load_dotenv(ROOT / ".env", override=False)
    try:
        timeout = min(60.0, max(1.0, float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))))
        limit = min(100, max(1, int(os.getenv("LLM_REQUESTS_PER_MINUTE", "10"))))
    except ValueError as exc:
        raise ValueError("LLM timeout and request limit must be numbers.") from exc
    return Settings(
        database_url=os.getenv("DATABASE_URL", "sqlite:///storage/items.db"),
        api_key=os.getenv("LLM_API_KEY", "").strip(),
        base_url=os.getenv("LLM_BASE_URL", "").strip().rstrip("/"),
        model=os.getenv("LLM_MODEL", "").strip(),
        provider=os.getenv("LLM_PROVIDER", "").strip(),
        timeout=timeout, requests_per_minute=limit)
