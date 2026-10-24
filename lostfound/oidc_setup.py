"""Generate Streamlit's server-side auth settings from deployment environment."""
import json
import os
import uuid
from urllib.parse import urlsplit
from .config import ROOT
from .auth import microsoft_configured

def configure_microsoft():
    if not microsoft_configured():
        return False
    tenant = str(uuid.UUID(os.environ["MS_TENANT_ID"]))
    client = str(uuid.UUID(os.environ["MS_CLIENT_ID"]))
    redirect = os.environ["AUTH_REDIRECT_URI"].strip()
    url = urlsplit(redirect)
    if url.scheme != "https" and not (url.scheme == "http" and url.hostname in {"localhost","127.0.0.1"}):
        raise ValueError("Microsoft redirect must use HTTPS (except localhost).")
    if url.path != "/oauth2callback" or url.query or url.fragment:
        raise ValueError("Microsoft redirect must end with /oauth2callback.")
    secret = os.environ["AUTH_COOKIE_SECRET"]
    if len(secret) < 32:
        raise ValueError("AUTH_COOKIE_SECRET must contain at least 32 random characters.")
    values = {"redirect_uri": redirect, "cookie_secret": secret}
    provider = {"client_id": client, "client_secret": os.environ["MS_CLIENT_SECRET"],
                "server_metadata_url": f"https://login.microsoftonline.com/{tenant}/v2.0/.well-known/openid-configuration"}
    content = "[auth]\n" + "\n".join(k+" = "+json.dumps(v) for k,v in values.items())
    content += "\n[auth.microsoft]\n" + "\n".join(k+" = "+json.dumps(v) for k,v in provider.items()) + "\n"
    path = ROOT / ".streamlit/secrets.toml"
    path.parent.mkdir(exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return True
