"""Server-side staff authorization. No self-registration or email-domain role grants."""
import hashlib
import hmac
import os
import re
import secrets
import time
import uuid
from sqlalchemy import select, update, delete
from .database import accounts_table, sessions_table
SESSION_SECONDS = 3600
ITERATIONS = 600_000

def hash_password(password):
    if not 12 <= len(password) <= 128:
        raise ValueError("Use a separate app password of 12 to 128 characters.")
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS).hex()
    return "$".join(["pbkdf2-sha256", str(ITERATIONS), salt, digest])

def verify_password(password, encoded):
    try:
        kind, rounds, salt, expected = encoded.split("$")
        if kind != "pbkdf2-sha256" or not 1 <= int(rounds) <= 1_000_000 or len(password) > 128:
            return False
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(rounds)).hex()
        return hmac.compare_digest(actual, expected)
    except (AttributeError, ValueError, TypeError):
        return False

DUMMY_HASH = hash_password(secrets.token_urlsafe(24))

def provision_account(engine, email, password=None, identity_key=None, role="staff"):
    """Administrative CLI only: never exposed through student-facing forms."""
    email = email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or len(email) > 254:
        raise ValueError("Enter a valid email address.")
    if role not in {"staff", "student"}:
        raise ValueError("Unknown role.")
    if not password and not identity_key:
        raise ValueError("A password or approved Microsoft identity is required.")
    if identity_key:
        parts = identity_key.split(":")
        if len(parts) != 2 or any(str(uuid.UUID(p)) != p.lower() for p in parts):
            raise ValueError("Microsoft identity must be tenant UUID:object UUID.")
        identity_key = identity_key.lower()
    row = dict(id=uuid.uuid4().hex, email=email,
               password_hash=hash_password(password) if password else None,
               identity_key=identity_key, role=role, active=1, failed_attempts=0, locked_until=0)
    with engine.begin() as conn:
        conn.execute(accounts_table.insert().values(**row))
    return row["id"]

def _issue_session(conn, account_id):
    token = secrets.token_urlsafe(32)
    now = int(time.time())
    conn.execute(delete(sessions_table).where(sessions_table.c.expires_at <= now))
    conn.execute(sessions_table.insert().values(token_hash=hashlib.sha256(token.encode()).hexdigest(),
                 account_id=account_id, expires_at=now + SESSION_SECONDS))
    return token

def authenticate(engine, email, password):
    if len(email) > 254 or len(password) > 128:
        return None
    with engine.begin() as conn:
        if engine.dialect.name == "sqlite":
            conn.exec_driver_sql("BEGIN IMMEDIATE")
        row = conn.execute(select(accounts_table).where(
            accounts_table.c.email == email.strip().lower()).with_for_update()).mappings().first()
        now = int(time.time())
        valid = verify_password(password, row["password_hash"] if row else DUMMY_HASH)
        if not row or not row["active"] or row["locked_until"] > now:
            return None
        if not valid:
            attempts = row["failed_attempts"] + 1
            conn.execute(update(accounts_table).where(accounts_table.c.id == row["id"]).values(
                failed_attempts=attempts, locked_until=now + 900 if attempts >= 5 else 0))
            return None
        conn.execute(update(accounts_table).where(accounts_table.c.id == row["id"]).values(
            failed_attempts=0, locked_until=0))
        return _issue_session(conn, row["id"])

def account_for_session(conn, token):
    if not isinstance(token, str) or not token:
        return None
    return conn.execute(select(accounts_table).join(sessions_table,
        sessions_table.c.account_id == accounts_table.c.id).where(
        sessions_table.c.token_hash == hashlib.sha256(token.encode()).hexdigest(),
        sessions_table.c.expires_at > int(time.time()), accounts_table.c.active == 1
    )).mappings().first()

def require_staff(conn, token):
    account = account_for_session(conn, token)
    if not account or account["role"] != "staff":
        raise PermissionError("An active staff sign-in is required.")
    return account

def staff_account(engine, token):
    with engine.connect() as conn:
        try:
            return dict(require_staff(conn, token))
        except PermissionError:
            return None

def logout(engine, token):
    if isinstance(token, str):
        with engine.begin() as conn:
            conn.execute(delete(sessions_table).where(
                sessions_table.c.token_hash == hashlib.sha256(token.encode()).hexdigest()))

def authenticate_microsoft(engine, claims, tenant_id):
    """Only accept st.user's verified OIDC claims, never form/query parameter data."""
    try:
        expected = str(uuid.UUID(tenant_id)).lower()
        tenant = str(uuid.UUID(claims.get("tid", ""))).lower()
        oid = str(uuid.UUID(claims.get("oid", ""))).lower()
        valid_until = int(claims.get("exp", 0))
    except (ValueError, TypeError, AttributeError):
        return None
    if tenant != expected or claims.get("iss") != f"https://login.microsoftonline.com/{tenant}/v2.0":
        return None
    if valid_until <= time.time():
        return None
    with engine.begin() as conn:
        row = conn.execute(select(accounts_table).where(
            accounts_table.c.identity_key == tenant + ":" + oid,
            accounts_table.c.active == 1, accounts_table.c.role == "staff")).mappings().first()
        return _issue_session(conn, row["id"]) if row else None

def microsoft_configured():
    return all(os.getenv(key, "").strip() for key in
               ("MS_TENANT_ID", "MS_CLIENT_ID", "MS_CLIENT_SECRET", "AUTH_COOKIE_SECRET", "AUTH_REDIRECT_URI"))
