"""Transactional SQLite/PostgreSQL inventory, photos, identities and audit history."""
import hashlib
import json
import os
import time
import uuid
from pathlib import Path
from sqlalchemy import (create_engine, MetaData, Table, Column, String, JSON,
                        Integer, BigInteger, LargeBinary, select, inspect, text, delete)
from sqlalchemy.engine import make_url
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from .config import ROOT
from .models import Item
from .locations import PLACES, UNSPECIFIED
from .photos import prepare_photo

metadata = MetaData()
items_table = Table("items", metadata,
 Column("id", String(16), primary_key=True),
 Column("type", String(80), nullable=False, index=True),
 Column("colour", String(60), nullable=False),
 Column("features", JSON, nullable=False),
 Column("description", String(600), nullable=False),
 Column("place", String(160), nullable=False, server_default=UNSPECIFIED),
 Column("created_at", BigInteger, nullable=False, server_default="0"))
photos_table = Table("item_photos", metadata,
 Column("item_id", String(16), primary_key=True), Column("data", LargeBinary, nullable=False))
meta_table = Table("app_meta", metadata, Column("key", String(60), primary_key=True))
accounts_table = Table("accounts", metadata,
 Column("id", String(32), primary_key=True),
 Column("email", String(254), nullable=False, unique=True),
 Column("password_hash", String(300)), Column("identity_key", String(100), unique=True),
 Column("role", String(16), nullable=False),
 Column("active", Integer, nullable=False, server_default="1"),
 Column("failed_attempts", Integer, nullable=False, server_default="0"),
 Column("locked_until", BigInteger, nullable=False, server_default="0"))
sessions_table = Table("staff_sessions", metadata,
 Column("token_hash", String(64), primary_key=True),
 Column("account_id", String(32), nullable=False),
 Column("expires_at", BigInteger, nullable=False))
audit_table = Table("inventory_audit", metadata,
 Column("id", String(32), primary_key=True), Column("item_id", String(16), nullable=False),
 Column("action", String(20), nullable=False), Column("account_id", String(32), nullable=False),
 Column("timestamp", BigInteger, nullable=False))

def read_seed():
    data = json.loads((ROOT / "data/items.json").read_text(encoding="utf-8"))
    records = [Item.model_validate(row) for row in data]
    if len(records) != 30 or len({r.id for r in records}) != 30:
        raise ValueError("Seed must contain exactly 30 unique fictional items.")
    return records

def dataset_hash(records):
    raw = json.dumps([r.model_dump() for r in sorted(records, key=lambda r: r.id)],
                     sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()

def connect_database(database_url):
    if database_url.startswith("postgres://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgres://"):]
    elif database_url.startswith("postgresql://"):
        database_url = "postgresql+psycopg://" + database_url[len("postgresql://"):]
    url = make_url(database_url)
    if url.get_backend_name() == "sqlite":
        if url.database and url.database != ":memory:":
            path = Path(url.database)
            if not path.is_absolute():
                path = ROOT / path
            path.parent.mkdir(parents=True, exist_ok=True)
            url = url.set(database=str(path))
        return create_engine(url, connect_args={"check_same_thread": False, "timeout": 15})
    if url.drivername != "postgresql+psycopg":
        raise ValueError("Use SQLite or PostgreSQL with psycopg.")
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 10})

def initialize(engine, seed_demo=None):
    """Migrate v1 without replacing records. Seed once; deleted items stay deleted."""
    if seed_demo is None:
        seed_demo = os.getenv("SEED_DEMO_DATA", "true").lower() == "true"
    with engine.begin() as conn:
        if engine.dialect.name == "postgresql":
            conn.execute(text("SELECT pg_advisory_xact_lock(7191902)"))
        else:
            conn.exec_driver_sql("BEGIN IMMEDIATE")
        metadata.create_all(conn)
        columns = {c["name"] for c in inspect(conn).get_columns("items")}
        if "place" not in columns:
            conn.execute(text("ALTER TABLE items ADD COLUMN place VARCHAR(160) NOT NULL DEFAULT 'Not recorded'"))
        if "created_at" not in columns:
            conn.execute(text("ALTER TABLE items ADD COLUMN created_at BIGINT NOT NULL DEFAULT 0"))
        if not conn.execute(select(meta_table).where(meta_table.c.key == "seed-v1")).first():
            if seed_demo:
                insert = sqlite_insert if engine.dialect.name == "sqlite" else pg_insert
                conn.execute(insert(items_table).values([r.model_dump() for r in read_seed()])
                             .on_conflict_do_nothing(index_elements=["id"]))
            conn.execute(meta_table.insert().values(key="seed-v1"))
    return len(list_items(engine))

def list_items(engine, category=None, place=None):
    stmt = select(items_table).order_by(items_table.c.id)
    if category and category != "All items":
        stmt = stmt.where(items_table.c.type == category)
    if place and place != "All places":
        stmt = stmt.where(items_table.c.place == place)
    with engine.connect() as conn:
        return [Item.model_validate(dict(row)) for row in conn.execute(stmt).mappings()]

def inventory_writes_allowed(engine):
    return not (os.getenv("RENDER") and engine.dialect.name == "sqlite")

def _authorize(conn, engine, token):
    from .auth import require_staff
    account = require_staff(conn, token)
    if not inventory_writes_allowed(engine):
        raise PermissionError("Connect persistent PostgreSQL before recording items on Render.")
    return account

def add_item(engine, token, *, item_type, colour, description, place, photo=None, item_id=None):
    item = Item(id=item_id or "LF-" + uuid.uuid4().hex[:12],
                type=item_type.strip(), colour=colour.strip(),
                description=description.strip(), features=[item_type.strip()],
                place=place, created_at=int(time.time()))
    if place not in PLACES:
        raise ValueError("Select a listed place.")
    with engine.begin() as conn:
        account = _authorize(conn, engine, token)
        image = prepare_photo(photo)
        conn.execute(items_table.insert().values(**item.model_dump()))
        if image:
            conn.execute(photos_table.insert().values(item_id=item.id, data=image))
        conn.execute(audit_table.insert().values(id=uuid.uuid4().hex, item_id=item.id,
                     action="added", account_id=account["id"], timestamp=int(time.time())))
    return item

def get_photo(engine, item_id):
    with engine.connect() as conn:
        return conn.execute(select(photos_table.c.data).join(
            items_table, items_table.c.id == photos_table.c.item_id
        ).where(photos_table.c.item_id == item_id)).scalar_one_or_none()

def collect_item(engine, token, item_id):
    """Delete active record/photo and append audit event in one transaction."""
    with engine.begin() as conn:
        account = _authorize(conn, engine, token)
        removed = conn.execute(delete(items_table).where(items_table.c.id == item_id))
        if removed.rowcount != 1:
            raise ValueError("This item is no longer available. Refresh the catalogue.")
        conn.execute(delete(photos_table).where(photos_table.c.item_id == item_id))
        conn.execute(audit_table.insert().values(id=uuid.uuid4().hex, item_id=item_id,
                     action="collected", account_id=account["id"], timestamp=int(time.time())))

def list_audit(engine, token):
    from .auth import require_staff
    with engine.connect() as conn:
        require_staff(conn, token)
        return list(conn.execute(select(audit_table.c.item_id, audit_table.c.action,
                         audit_table.c.timestamp).order_by(audit_table.c.timestamp.desc()).limit(100)).mappings())

if __name__ == "__main__":
    from .config import load_settings
    engine = connect_database(load_settings().database_url)
    initialize(engine)
    print(f"Database ready: {len(list_items(engine))} active items.")
