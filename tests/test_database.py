import os
import pytest
from sqlalchemy import inspect
from lostfound.database import connect_database, initialize, list_items, dataset_hash, read_seed

def test_sqlite_persistence_and_idempotent_seed(tmp_path):
    url = "sqlite:///" + str(tmp_path / "items.db")
    engine = connect_database(url)
    initialize(engine)
    initialize(engine)
    records = list_items(engine)
    assert len(records) == 30
    assert list_items(engine, "Bottle")[0].id == "LF-001"
    assert len(list_items(engine, "Bottle")) == 3
    assert {"items", "item_photos", "accounts", "staff_sessions", "app_meta", "inventory_audit"} == set(inspect(engine).get_table_names())
    engine.dispose()
    reopened = connect_database(url)
    assert dataset_hash(list_items(reopened)) == dataset_hash(read_seed())
    reopened.dispose()

@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Requires a dedicated PostgreSQL test database")
def test_postgresql_roundtrip():
    engine = connect_database(os.environ["TEST_DATABASE_URL"])
    assert engine.dialect.name == "postgresql"
    initialize(engine)
    initialize(engine)
    assert len(list_items(engine)) == 30
    assert len(list_items(engine, "Bottle")) == 3
    engine.dispose()

@pytest.mark.skipif(not os.getenv("TEST_DATABASE_URL"), reason="Requires a dedicated PostgreSQL test database")
def test_postgresql_staff_photo_collection():
    import uuid
    from io import BytesIO
    from PIL import Image
    from lostfound.database import add_item, collect_item, get_photo, list_audit
    from lostfound.auth import provision_account, authenticate
    engine = connect_database(os.environ["TEST_DATABASE_URL"])
    initialize(engine)
    email = uuid.uuid4().hex + "@example.test"
    provision_account(engine,email,"Postgres-test-password-123")
    token = authenticate(engine,email,"Postgres-test-password-123")
    image = BytesIO()
    Image.new("RGB",(16,16),"blue").save(image,"PNG")
    item = add_item(engine,token,item_type="Bottle",colour="blue",
        description="A blue bottle with a white screw lid",place="HW",photo=image.getvalue())
    assert get_photo(engine,item.id)
    engine.dispose()
    engine = connect_database(os.environ["TEST_DATABASE_URL"])
    initialize(engine)
    assert item.id in {r.id for r in list_items(engine,place="HW")}
    collect_item(engine,token,item.id)
    initialize(engine)
    assert item.id not in {r.id for r in list_items(engine)}
    assert get_photo(engine,item.id) is None
    assert any(r["item_id"]==item.id and r["action"]=="collected" for r in list_audit(engine,token))
    engine.dispose()
