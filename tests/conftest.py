from __future__ import annotations

import re
import shutil
import sys
import tempfile
import types
from pathlib import Path
from typing import Callable

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import DeclarativeBase, sessionmaker


# ============================================================
# PROJECT PATH
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# ISOLATED TEST ENVIRONMENT
# ============================================================
#
# IMPORTANT:
# These tests never use the real Vanta SQLite database and never
# use C:\\FamilyCloudStorage.
#
# A temporary database module is installed BEFORE app.models,
# app.auth, app.main, or any routes are imported.
# ============================================================

TEST_ROOT = Path(
    tempfile.mkdtemp(prefix="vanta-v1-tests-")
)

TEST_DATABASE_PATH = TEST_ROOT / "vanta-test.db"
TEST_STORAGE_DIR = TEST_ROOT / "storage"
TEST_TRASH_DIR = TEST_STORAGE_DIR / ".Trash"


class TestBase(DeclarativeBase):
    pass


TEST_ENGINE = create_engine(
    f"sqlite:///{TEST_DATABASE_PATH.as_posix()}",
    connect_args={
        "check_same_thread": False,
    },
)


TestSessionLocal = sessionmaker(
    bind=TEST_ENGINE,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def test_get_db():
    db = TestSessionLocal()

    try:
        yield db

    finally:
        db.close()


def test_init_db():
    import app.models  # noqa: F401

    TestBase.metadata.create_all(
        bind=TEST_ENGINE
    )


# Replace app.database before anything imports it.

database_module = types.ModuleType(
    "app.database"
)

database_module.Base = TestBase
database_module.engine = TEST_ENGINE
database_module.SessionLocal = TestSessionLocal
database_module.get_db = test_get_db
database_module.init_db = test_init_db

sys.modules["app.database"] = database_module


# Replace app.config so tests do not read/write the real session
# secret file.

config_module = types.ModuleType(
    "app.config"
)

config_module.SESSION_SECRET = (
    "vanta-test-session-secret-"
    "this-value-is-only-for-tests-1234567890"
)

sys.modules["app.config"] = config_module


# Import models against the temporary SQLAlchemy Base.

from app.models import FileRecord, User, UserRole  # noqa: E402


# Patch storage BEFORE app.main and the routers import constants
# from app.services.storage.

import app.services.storage as storage  # noqa: E402

storage.STORAGE_DIR = TEST_STORAGE_DIR
storage.TRASH_DIR = TEST_TRASH_DIR


# Now it is safe to import the rest of Vanta.

import app.auth as auth  # noqa: E402
import app.main as main  # noqa: E402
import app.routes.trash as trash_routes  # noqa: E402
import app.services.settings as settings_service  # noqa: E402


TEST_PASSWORD = "VantaTestPassword123!"
TEST_PASSWORD_HASH = auth.hash_password(
    TEST_PASSWORD
)


# ============================================================
# HELPERS
# ============================================================

def extract_csrf_token(
    html: str,
) -> str:

    patterns = [
        (
            r'name=["\']csrf_token["\']'
            r'[^>]*value=["\']([^"\']+)["\']'
        ),
        (
            r'value=["\']([^"\']+)["\']'
            r'[^>]*name=["\']csrf_token["\']'
        ),
        (
            r'name=["\']csrf-token["\']'
            r'[^>]*content=["\']([^"\']+)["\']'
        ),
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            html,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1)

    raise AssertionError(
        "Could not find a CSRF token in rendered HTML."
    )


def create_user_record(
    *,
    username: str,
    role: str = UserRole.MEMBER.value,
    active: bool = True,
    display_name: str | None = None,
) -> User:

    with TestSessionLocal() as db:
        user = User(
            username=username.lower(),
            display_name=(
                display_name
                or username.title()
            ),
            password_hash=TEST_PASSWORD_HASH,
            role=role,
            is_active=active,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        return user


def login_client(
    client: TestClient,
    username: str,
    password: str = TEST_PASSWORD,
) -> str:

    page = client.get(
        "/login",
        follow_redirects=False,
    )

    assert page.status_code == 200

    pre_login_token = extract_csrf_token(
        page.text
    )

    response = client.post(
        "/login",
        data={
            "username": username,
            "password": password,
            "csrf_token": pre_login_token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"

    return pre_login_token


def page_csrf(
    client: TestClient,
    path: str = "/",
) -> str:

    response = client.get(
        path,
        follow_redirects=False,
    )

    assert response.status_code == 200

    return extract_csrf_token(
        response.text
    )


def set_setting(
    key: str,
    value,
) -> None:

    with TestSessionLocal() as db:
        settings_service.set_setting(
            db,
            key,
            value,
        )
        db.commit()


def create_physical_record(
    *,
    filename: str,
    owner_id: int | None,
    category: str = "Documents",
    content: bytes = b"test-data",
) -> FileRecord:

    directory = (
        storage.STORAGE_DIR / category
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = directory / filename
    path.write_bytes(content)

    relative = path.relative_to(
        storage.STORAGE_DIR
    ).as_posix()

    with TestSessionLocal() as db:
        record = FileRecord(
            stored_path=relative,
            original_name=filename,
            category=category,
            size_bytes=len(content),
            uploaded_by_id=owner_id,
            is_trashed=False,
        )

        db.add(record)
        db.commit()
        db.refresh(record)

        return record


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture(autouse=True)
def reset_vanta_state():

    TestBase.metadata.drop_all(
        bind=TEST_ENGINE
    )

    TestBase.metadata.create_all(
        bind=TEST_ENGINE
    )

    shutil.rmtree(
        TEST_STORAGE_DIR,
        ignore_errors=True,
    )

    storage.initialize_storage()

    main.app.dependency_overrides.clear()

    yield


@pytest.fixture
def client():

    with TestClient(
        main.app,
        raise_server_exceptions=False,
    ) as test_client:
        yield test_client


@pytest.fixture
def db_session():

    db = TestSessionLocal()

    try:
        yield db

    finally:
        db.close()


@pytest.fixture
def make_user() -> Callable[..., User]:
    return create_user_record


@pytest.fixture
def login() -> Callable[..., str]:
    return login_client


@pytest.fixture
def csrf() -> Callable[..., str]:
    return page_csrf


@pytest.fixture
def set_app_setting() -> Callable[..., None]:
    return set_setting


@pytest.fixture
def make_file_record() -> Callable[..., FileRecord]:
    return create_physical_record


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_root():
    yield

    shutil.rmtree(
        TEST_ROOT,
        ignore_errors=True,
    )
