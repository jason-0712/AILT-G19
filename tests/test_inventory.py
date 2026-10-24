from io import BytesIO
import time
import uuid
import pytest
from PIL import Image
from sqlalchemy import text, update, select
from lostfound.database import (connect_database, initialize, add_item, collect_item,
 list_items, get_photo, list_audit, items_table, accounts_table, sessions_table)
from lostfound.auth import (authenticate, provision_account, logout, staff_account,
 authenticate_microsoft, verify_password, hash_password)
from lostfound.photos import prepare_photo, MAX_UPLOAD
from lostfound.matching import keyword_matches

PASSWORD = "Test-only-passphrase-4319"

@pytest.fixture
def inventory(tmp_path):
    engine = connect_database("sqlite:///" + str(tmp_path / "inventory.db"))
    initialize(engine, seed_demo=False)
    provision_account(engine, "staff@example.test", PASSWORD)
    token = authenticate(engine, "staff@example.test", PASSWORD)
    yield engine, token
    engine.dispose()

def photo():
    buf = BytesIO()
    image = Image.new("RGB", (64, 40), "green")
    exif = Image.Exif()
    exif[270] = "private metadata"
    image.save(buf, "JPEG", exif=exif)
    return buf.getvalue()

def record(engine, token, **extra):
    return add_item(engine, token, item_type="Bottle", colour="black",
                    description="Black metal bottle with a silver lid", place="MW", **extra)

def test_save_photo_reopen_collect_and_restart(inventory):
    engine, token = inventory
    item = record(engine, token, photo=photo())
    stored_photo = get_photo(engine, item.id)
    assert stored_photo and not Image.open(BytesIO(stored_photo)).getexif()
    url = engine.url
    engine.dispose()
    reopened = connect_database(str(url))
    initialize(reopened)
    assert list_items(reopened, place="MW")[0].id == item.id
    assert not list_items(reopened, place="HW")
    assert get_photo(reopened, item.id) == stored_photo
    collect_item(reopened, token, item.id)
    initialize(reopened)
    assert list_items(reopened) == []
    assert get_photo(reopened, item.id) is None
    assert {r["action"] for r in list_audit(reopened, token)} == {"added","collected"}
    with pytest.raises(ValueError):
        collect_item(reopened, token, item.id)
    reopened.dispose()

def test_student_and_anonymous_cannot_modify(inventory):
    engine, staff = inventory
    item = record(engine, staff)
    provision_account(engine, "student@example.test", PASSWORD, role="student")
    student = authenticate(engine, "student@example.test", PASSWORD)
    for token in [None, "forged-token", student]:
        with pytest.raises(PermissionError):
            record(engine, token)
        with pytest.raises(PermissionError):
            collect_item(engine, token, item.id)
        with pytest.raises(PermissionError):
            list_audit(engine, token)
    assert len(list_items(engine)) == 1

def test_expiry_revocation_and_disabled_account(inventory):
    engine, token = inventory
    logout(engine, token)
    assert staff_account(engine, token) is None
    with pytest.raises(PermissionError):
        record(engine, token)
    token = authenticate(engine, "staff@example.test", PASSWORD)
    with engine.begin() as conn:
        conn.execute(update(sessions_table).values(expires_at=0))
    assert staff_account(engine, token) is None
    token = authenticate(engine, "staff@example.test", PASSWORD)
    with engine.begin() as conn:
        conn.execute(update(accounts_table).values(active=0))
    assert staff_account(engine, token) is None

def test_passwords_and_persistent_lockout(inventory):
    engine, _ = inventory
    encoded = hash_password(PASSWORD)
    assert PASSWORD not in encoded and verify_password(PASSWORD, encoded)
    assert not verify_password("wrong", encoded)
    for _ in range(5):
        assert authenticate(engine, "staff@example.test", "wrong") is None
    assert authenticate(engine, "staff@example.test", PASSWORD) is None
    with engine.begin() as conn:
        conn.execute(update(accounts_table).values(locked_until=0))
    assert authenticate(engine, "STAFF@example.test", PASSWORD)

def test_invalid_photo_or_place_never_creates_record(inventory):
    engine, token = inventory
    for data in [b"not an image", b"x"*(MAX_UPLOAD+1)]:
        with pytest.raises(ValueError):
            record(engine, token, photo=data)
    with pytest.raises(ValueError):
        add_item(engine, token, item_type="Bottle", colour="black",
                 description="Black bottle with silver lid", place="made-up")
    assert not list_items(engine)
    assert not list_audit(engine, token)

def test_place_full_name_and_abbreviation_search(inventory):
    engine, token = inventory
    item = record(engine, token)
    assert keyword_matches("Meng Wah", list_items(engine))[0].id == item.id
    assert keyword_matches("MW", list_items(engine))[0].id == item.id

def test_ephemeral_render_writes_fail_closed(inventory, monkeypatch):
    engine, token = inventory
    monkeypatch.setenv("RENDER", "true")
    with pytest.raises(PermissionError):
        record(engine, token)
    assert not list_items(engine)

def test_migrate_original_schema_without_resetting_data(tmp_path):
    engine = connect_database("sqlite:///" + str(tmp_path / "old.db"))
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE items (id VARCHAR(16) PRIMARY KEY, type VARCHAR(80) NOT NULL, colour VARCHAR(60) NOT NULL, features JSON NOT NULL, description VARCHAR(600) NOT NULL)"))
        conn.execute(text("""INSERT INTO items VALUES ('LF-001', 'Bottle', 'black', '["metal"]', 'An existing edited record')"""))
    initialize(engine)
    assert list_items(engine)[0].description == "An existing edited record"
    assert list_items(engine)[0].place == "Not recorded"
    provision_account(engine,"worker@example.test",PASSWORD)
    token = authenticate(engine,"worker@example.test",PASSWORD)
    collect_item(engine,token,"LF-001")
    initialize(engine)
    assert "LF-001" not in {r.id for r in list_items(engine)}
    engine.dispose()

def test_microsoft_requires_registered_immutable_identity(inventory):
    engine, _ = inventory
    tenant, oid = str(uuid.uuid4()), str(uuid.uuid4())
    claims = {"tid":tenant,"oid":oid,"iss":f"https://login.microsoftonline.com/{tenant}/v2.0",
              "exp":int(time.time())+300,"email":"staff@example.test"}
    assert authenticate_microsoft(engine,claims,tenant) is None
    provision_account(engine,"sso@example.test",identity_key=tenant+":"+oid)
    assert authenticate_microsoft(engine,claims,tenant)
    assert authenticate_microsoft(engine,claims,str(uuid.uuid4())) is None
    assert authenticate_microsoft(engine,{**claims,"exp":0},tenant) is None
    assert authenticate_microsoft(engine,{**claims,"iss":"https://attacker.test"},tenant) is None
