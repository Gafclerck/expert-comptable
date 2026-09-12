import os

TEST_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_api.db").replace("\\", "/")
TEST_DB_URL = f"sqlite:///{TEST_DB_PATH}"

os.environ["DATABASE_URL"] = TEST_DB_URL
# Neutralise le LlmiInterpreter par defaut : les tests doivent passer par les
# regles FR, sans appeler un vrai LLM. Un developeur qui teste le LLM reel peut
# redefinir la cle explicitement dans son environnement avant de lancer pytest.
os.environ.setdefault("ASSISTANT_LLM_API_KEY", "")
os.environ.setdefault("SECRET_KEY", "cle-de-test-tres-longue-pour-hmac-sha256-0123456789")
os.environ.setdefault("SUPER_USER_EMAIL", "root@example.com")
os.environ.setdefault("SUPER_USER_PASSWORD", "mot-de-passe-root")

import pytest
from fastapi.testclient import TestClient

# import app.modules.identity.models  # noqa: F401
# import app.modules.ledger.models  # noqa: F401
# import app.modules.audit.models  # noqa: F401
# import app.modules.insurance.models  # noqa: F401
from app.core.config import settings
from app.core.base import Base
from app.core.db import engine, init_db, session as session_factory
from app.core.deps import limiter
from app.main import app

from app.modules.identity.models import Business, BusinessStatus, Person, User

from tests.helpers import auth_headers, link_person_to_business, make_user  # noqa: F401


@pytest.fixture(scope="session", autouse=True)
def _database():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    Base.metadata.create_all(bind=engine)
    with session_factory() as s:
        init_db(s)
    yield
    engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture(autouse=True)
def _isolate_test():
    yield
    with session_factory() as s:
        for table in reversed(Base.metadata.sorted_tables):
            s.execute(table.delete())
        s.commit()
        init_db(s)
    storage = getattr(limiter, "_storage", None)
    if storage is not None and hasattr(storage, "reset"):
        storage.reset()


@pytest.fixture
def db():
    s = session_factory()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def headers():
    return auth_headers


@pytest.fixture
def root(db):
    user = db.query(User).filter(User.email == "root@example.com").first()
    return user


@pytest.fixture
def co_owner(db):
    person = Person(full_name="Co-owner")
    db.add(person)
    return make_user(db, email="coowner@example.com", person=person)


@pytest.fixture
def assurance(db):
    business = db.query(Business).filter(Business.code == "assurance").first()
    return business or Business(code="assurance", name="Assurance", status=BusinessStatus.ACTIVE)


@pytest.fixture
def poulets(db):
    business = db.query(Business).filter(Business.code == "poulets").first()
    return business or Business(code="poulets", name="Poulets", status=BusinessStatus.ACTIVE)


@pytest.fixture
def vtc(db):
    business = db.query(Business).filter(Business.code == "vtc").first()
    return business or Business(code="vtc", name="VTC", status=BusinessStatus.ACTIVE)