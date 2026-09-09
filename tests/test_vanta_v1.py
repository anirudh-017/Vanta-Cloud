from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.models import FileRecord, User, UserRole
import app.main as main
import app.routes.trash as trash_routes
import app.services.settings as settings_service
import app.services.storage as storage

from conftest import (
    TEST_PASSWORD,
    TEST_STORAGE_DIR,
    TestSessionLocal,
    extract_csrf_token,
)


# ============================================================
# HELPERS USED BY TESTS
# ============================================================

def upload_one(
    client,
    csrf,
    *,
    name: str = "hello.txt",
    content: bytes = b"hello",
    content_type: str = "text/plain",
):

    token = csrf(client, "/")

    return client.post(
        "/upload",
        data={
            "csrf_token": token,
        },
        files={
            "file": (
                name,
                content,
                content_type,
            ),
        },
        follow_redirects=False,
    )


def valid_settings_form(
    csrf_token: str,
) -> dict[str, str]:

    return {
        "cloud_name": "Vanta Test",
        "tagline": "Private test cloud",
        "theme": "dark",
        "allow_member_uploads": "on",
        "allow_member_downloads": "on",
        "allow_member_previews": "on",
        "allow_member_trash_own": "on",
        "allow_member_rename_own": "on",
        "max_upload_mb": "25",
        "multiple_uploads": "on",
        "duplicate_behavior": "reject",
        "allowed_file_types": "all",
        "trash_enabled": "on",
        "trash_retention_days": "30",
        "show_uploader": "on",
        "show_upload_time": "on",
        "default_view": "Photos",
        "csrf_token": csrf_token,
    }


# ============================================================
# TEST HARNESS SAFETY
# ============================================================

def test_suite_uses_only_temporary_storage():

    resolved = storage.STORAGE_DIR.resolve()

    assert resolved == TEST_STORAGE_DIR.resolve()
    assert ".Trash" in str(
        storage.TRASH_DIR
    )
    assert "FamilyCloudStorage" not in str(
        resolved
    )


# ============================================================
# SETUP + AUTHENTICATION
# ============================================================

def test_first_launch_setup_creates_admin(
    client,
    db_session,
):

    page = client.get(
        "/setup",
        follow_redirects=False,
    )

    assert page.status_code == 200

    token = extract_csrf_token(
        page.text
    )

    response = client.post(
        "/setup",
        data={
            "display_name": "First Admin",
            "username": "firstadmin",
            "password": TEST_PASSWORD,
            "confirm_password": TEST_PASSWORD,
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"

    user = db_session.scalar(
        select(User).where(
            User.username == "firstadmin"
        )
    )

    assert user is not None
    assert user.role == UserRole.ADMIN.value
    assert user.is_active is True

    second_setup = client.get(
        "/setup",
        follow_redirects=False,
    )

    assert second_setup.status_code == 303
    assert second_setup.headers["location"] == "/login"


@pytest.mark.parametrize(
    "display_name,username,password,confirm",
    [
        ("", "adminuser", TEST_PASSWORD, TEST_PASSWORD),
        ("Admin", "ab", TEST_PASSWORD, TEST_PASSWORD),
        ("Admin", "bad user", TEST_PASSWORD, TEST_PASSWORD),
        ("Admin", "adminuser", "short", "short"),
        ("Admin", "adminuser", TEST_PASSWORD, "Different123!"),
    ],
)
def test_setup_rejects_invalid_input(
    client,
    display_name,
    username,
    password,
    confirm,
):

    page = client.get("/setup")
    token = extract_csrf_token(page.text)

    response = client.post(
        "/setup",
        data={
            "display_name": display_name,
            "username": username,
            "password": password,
            "confirm_password": confirm,
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 400



def test_login_success_wrong_password_and_inactive_user(
    client,
    make_user,
    login,
):

    make_user(
        username="activeuser",
        role=UserRole.MEMBER.value,
    )

    login_page = client.get("/login")
    token = extract_csrf_token(login_page.text)

    bad = client.post(
        "/login",
        data={
            "username": "activeuser",
            "password": "WrongPassword123!",
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert bad.status_code == 400

    login(client, "activeuser")

    me = client.get("/api/me")

    assert me.status_code == 200
    assert me.json()["username"] == "activeuser"

    client.cookies.clear()

    make_user(
        username="inactiveuser",
        active=False,
    )

    inactive_page = client.get("/login")
    inactive_token = extract_csrf_token(
        inactive_page.text
    )

    inactive = client.post(
        "/login",
        data={
            "username": "inactiveuser",
            "password": TEST_PASSWORD,
            "csrf_token": inactive_token,
        },
        follow_redirects=False,
    )

    assert inactive.status_code == 400



def test_login_rotates_csrf_and_logout_requires_csrf(
    client,
    make_user,
    login,
    csrf,
):

    make_user(
        username="adminuser",
        role=UserRole.ADMIN.value,
    )

    pre_login_token = login(
        client,
        "adminuser",
    )

    authenticated_token = csrf(
        client,
        "/",
    )

    assert authenticated_token != pre_login_token

    missing = client.post(
        "/logout",
        data={},
        follow_redirects=False,
    )

    assert missing.status_code == 403
    assert client.get("/api/me").status_code == 200

    invalid = client.post(
        "/logout",
        data={
            "csrf_token": "not-the-right-token",
        },
        follow_redirects=False,
    )

    assert invalid.status_code == 403

    success = client.post(
        "/logout",
        data={
            "csrf_token": authenticated_token,
        },
        follow_redirects=False,
    )

    assert success.status_code == 303
    assert success.headers["location"] == "/login"

    me = client.get("/api/me")
    assert me.status_code == 401



def test_member_cannot_open_admin_pages(
    client,
    make_user,
    login,
):

    make_user(
        username="memberuser",
        role=UserRole.MEMBER.value,
    )

    login(client, "memberuser")

    assert client.get("/admin").status_code == 403
    assert client.get("/admin/settings").status_code == 403
    assert client.get("/admin/trash").status_code == 403


# ============================================================
# ERROR UX
# ============================================================

def test_friendly_404_and_json_error_mode(
    client,
):

    page = client.get(
        "/this-page-does-not-exist"
    )

    assert page.status_code == 404
    assert "Vanta" in page.text
    assert "Not found" in page.text

    xhr = client.get(
        "/this-page-does-not-exist",
        headers={
            "X-Requested-With": "XMLHttpRequest",
        },
    )

    assert xhr.status_code == 404
    assert xhr.headers["content-type"].startswith(
        "application/json"
    )
    assert "detail" in xhr.json()



def test_validation_error_uses_friendly_response(
    client,
):

    response = client.post(
        "/login",
        data={},
        follow_redirects=False,
    )

    assert response.status_code == 400
    assert "invalid" in response.text.lower()



def test_unexpected_error_uses_vanta_500_page(
    client,
    make_user,
    login,
    monkeypatch,
):

    make_user(
        username="erroradmin",
        role=UserRole.ADMIN.value,
    )

    login(client, "erroradmin")

    def explode():
        raise RuntimeError("test-only failure")

    monkeypatch.setattr(
        main,
        "get_storage_stats",
        explode,
    )

    response = client.get("/")

    assert response.status_code == 500
    assert "Something went wrong" in response.text
    assert "test-only failure" not in response.text


# ============================================================
# STORAGE SAFETY
# ============================================================

@pytest.mark.parametrize(
    "filename",
    [
        "../escape.txt",
        "..\\escape.txt",
        "CON.txt",
        "name.",
        "name ",
        "bad:name.txt",
    ],
)
def test_filename_validation_rejects_unsafe_names(
    filename,
):

    with pytest.raises(HTTPException):
        storage.validate_filename(
            filename
        )



def test_category_detection_and_duplicate_safe_name():

    assert storage.get_category("photo.JPG") == "Photos"
    assert storage.get_category("movie.mp4") == "Videos"
    assert storage.get_category("song.flac") == "Music"
    assert storage.get_category("notes.pdf") == "Documents"
    assert storage.get_category("archive.xyz") == "Other"

    directory = storage.STORAGE_DIR / "Documents"
    directory.mkdir(parents=True, exist_ok=True)

    (directory / "report.txt").write_text(
        "first",
        encoding="utf-8",
    )

    destination = storage.get_unique_destination(
        directory,
        "report.txt",
    )

    assert destination.name == "report (1).txt"



def test_storage_path_traversal_and_trash_boundary_are_blocked():

    with pytest.raises(HTTPException):
        storage.resolve_storage_path(
            "../outside.txt"
        )

    with pytest.raises(HTTPException):
        storage.resolve_storage_path(
            ".Trash/Documents/secret.txt"
        )

    with pytest.raises(HTTPException):
        storage.resolve_trash_path(
            "Documents/not-trash.txt"
        )



def test_rename_collision_is_rejected():

    directory = storage.STORAGE_DIR / "Documents"
    directory.mkdir(parents=True, exist_ok=True)

    first = directory / "first.txt"
    second = directory / "second.txt"

    first.write_text("one", encoding="utf-8")
    second.write_text("two", encoding="utf-8")

    with pytest.raises(HTTPException) as exc_info:
        storage.rename_file(
            first,
            "second.txt",
        )

    assert exc_info.value.status_code == 409
    assert first.exists()
    assert second.exists()


# ============================================================
# UPLOAD + DOWNLOAD + PREVIEW
# ============================================================

def test_admin_upload_creates_disk_file_and_database_record(
    client,
    make_user,
    login,
    csrf,
    db_session,
):

    admin = make_user(
        username="uploadadmin",
        role=UserRole.ADMIN.value,
    )

    login(client, "uploadadmin")

    response = upload_one(
        client,
        csrf,
        name="report.txt",
        content=b"hello-vanta",
    )

    assert response.status_code == 303

    record = db_session.scalar(
        select(FileRecord).where(
            FileRecord.original_name == "report.txt"
        )
    )

    assert record is not None
    assert record.uploaded_by_id == admin.id
    assert record.size_bytes == len(b"hello-vanta")
    assert record.category == "Documents"

    physical = (
        storage.STORAGE_DIR
        / record.stored_path
    )

    assert physical.read_bytes() == b"hello-vanta"



def test_duplicate_upload_renames_by_default(
    client,
    make_user,
    login,
    csrf,
):

    make_user(
        username="duplicateadmin",
        role=UserRole.ADMIN.value,
    )

    login(client, "duplicateadmin")

    first = upload_one(
        client,
        csrf,
        name="same.txt",
        content=b"one",
    )

    second = upload_one(
        client,
        csrf,
        name="same.txt",
        content=b"two",
    )

    assert first.status_code == 303
    assert second.status_code == 303

    directory = storage.STORAGE_DIR / "Documents"

    assert (directory / "same.txt").exists()
    assert (directory / "same (1).txt").exists()



def test_duplicate_reject_setting_blocks_second_upload(
    client,
    make_user,
    login,
    csrf,
    set_app_setting,
):

    make_user(
        username="rejectadmin",
        role=UserRole.ADMIN.value,
    )

    set_app_setting(
        "duplicate_behavior",
        "reject",
    )

    login(client, "rejectadmin")

    assert upload_one(
        client,
        csrf,
        name="same.txt",
        content=b"one",
    ).status_code == 303

    response = upload_one(
        client,
        csrf,
        name="same.txt",
        content=b"two",
    )

    assert response.status_code == 409

    directory = storage.STORAGE_DIR / "Documents"
    assert not (directory / "same (1).txt").exists()



def test_upload_size_limit_and_multiple_upload_setting(
    client,
    make_user,
    login,
    csrf,
    set_app_setting,
):

    make_user(
        username="limitsadmin",
        role=UserRole.ADMIN.value,
    )

    login(client, "limitsadmin")

    set_app_setting(
        "max_upload_mb",
        1,
    )

    too_large = upload_one(
        client,
        csrf,
        name="large.bin",
        content=b"x" * (1024 * 1024 + 1),
        content_type="application/octet-stream",
    )

    assert too_large.status_code == 413
    assert not (
        storage.STORAGE_DIR
        / "Other"
        / "large.bin"
    ).exists()

    set_app_setting(
        "multiple_uploads",
        False,
    )

    token = csrf(client, "/")

    multiple = client.post(
        "/upload",
        data={
            "csrf_token": token,
        },
        files=[
            (
                "file",
                ("a.txt", b"a", "text/plain"),
            ),
            (
                "file",
                ("b.txt", b"b", "text/plain"),
            ),
        ],
        follow_redirects=False,
    )

    assert multiple.status_code == 400



def test_member_upload_download_and_preview_permissions(
    client,
    make_user,
    login,
    csrf,
    set_app_setting,
    make_file_record,
):

    member = make_user(
        username="limitedmember",
        role=UserRole.MEMBER.value,
    )

    record = make_file_record(
        filename="private.txt",
        owner_id=member.id,
        content=b"private",
    )

    set_app_setting(
        "allow_member_uploads",
        False,
    )
    set_app_setting(
        "allow_member_downloads",
        False,
    )
    set_app_setting(
        "allow_member_previews",
        False,
    )

    login(client, "limitedmember")

    upload = upload_one(
        client,
        csrf,
        name="blocked.txt",
    )

    assert upload.status_code == 403

    download = client.get(
        "/download",
        params={
            "path": record.stored_path,
        },
    )

    preview = client.get(
        "/preview",
        params={
            "path": record.stored_path,
        },
    )

    assert download.status_code == 403
    assert preview.status_code == 403



def test_download_and_preview_work_when_allowed(
    client,
    make_user,
    login,
    make_file_record,
):

    member = make_user(
        username="allowedmember",
        role=UserRole.MEMBER.value,
    )

    record = make_file_record(
        filename="view.txt",
        owner_id=member.id,
        content=b"view-me",
    )

    login(client, "allowedmember")

    download = client.get(
        "/download",
        params={
            "path": record.stored_path,
        },
    )

    preview = client.get(
        "/preview",
        params={
            "path": record.stored_path,
        },
    )

    assert download.status_code == 200
    assert download.content == b"view-me"

    assert preview.status_code == 200
    assert preview.content == b"view-me"


# ============================================================
# RENAME
# ============================================================

def test_admin_rename_updates_disk_and_database(
    client,
    make_user,
    login,
    csrf,
    make_file_record,
    db_session,
):

    admin = make_user(
        username="renameadmin",
        role=UserRole.ADMIN.value,
    )

    record = make_file_record(
        filename="before.txt",
        owner_id=admin.id,
    )

    login(client, "renameadmin")
    token = csrf(client, "/")

    response = client.post(
        f"/files/{record.id}/rename",
        data={
            "new_name": "after.txt",
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    db_session.expire_all()

    updated = db_session.get(
        FileRecord,
        record.id,
    )

    assert updated.original_name == "after.txt"
    assert updated.stored_path.endswith("after.txt")

    assert not (
        storage.STORAGE_DIR
        / "Documents"
        / "before.txt"
    ).exists()

    assert (
        storage.STORAGE_DIR
        / "Documents"
        / "after.txt"
    ).exists()



def test_rename_blocks_extension_change_collision_and_other_owner(
    client,
    make_user,
    login,
    csrf,
    make_file_record,
    set_app_setting,
):

    member = make_user(
        username="renameowner",
        role=UserRole.MEMBER.value,
    )

    other = make_user(
        username="otherowner",
        role=UserRole.MEMBER.value,
    )

    own = make_file_record(
        filename="mine.txt",
        owner_id=member.id,
    )

    make_file_record(
        filename="taken.txt",
        owner_id=member.id,
    )

    foreign = make_file_record(
        filename="foreign.txt",
        owner_id=other.id,
    )

    set_app_setting(
        "allow_member_rename_own",
        True,
    )

    login(client, "renameowner")
    token = csrf(client, "/")

    extension = client.post(
        f"/files/{own.id}/rename",
        data={
            "new_name": "mine.exe",
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert extension.status_code == 400

    collision = client.post(
        f"/files/{own.id}/rename",
        data={
            "new_name": "taken.txt",
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert collision.status_code == 409

    forbidden = client.post(
        f"/files/{foreign.id}/rename",
        data={
            "new_name": "changed.txt",
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert forbidden.status_code == 403


# ============================================================
# TRASH
# ============================================================

def test_member_can_trash_own_file_but_not_another_users(
    client,
    make_user,
    login,
    csrf,
    make_file_record,
    db_session,
):

    member = make_user(
        username="trashmember",
        role=UserRole.MEMBER.value,
    )

    other = make_user(
        username="trashother",
        role=UserRole.MEMBER.value,
    )

    own = make_file_record(
        filename="own.txt",
        owner_id=member.id,
    )

    foreign = make_file_record(
        filename="other.txt",
        owner_id=other.id,
    )

    login(client, "trashmember")
    token = csrf(client, "/")

    own_response = client.post(
        "/trash",
        data={
            "path": own.stored_path,
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert own_response.status_code == 200

    db_session.expire_all()

    own_updated = db_session.get(
        FileRecord,
        own.id,
    )

    assert own_updated.is_trashed is True
    assert own_updated.trashed_at is not None
    assert own_updated.stored_path.startswith(
        ".Trash/"
    )

    token = csrf(client, "/")

    forbidden = client.post(
        "/trash",
        data={
            "path": foreign.stored_path,
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert forbidden.status_code == 403



def test_admin_restore_and_permanent_delete(
    client,
    make_user,
    login,
    csrf,
    make_file_record,
):

    admin = make_user(
        username="trashadmin",
        role=UserRole.ADMIN.value,
    )

    first = make_file_record(
        filename="restore.txt",
        owner_id=admin.id,
    )

    second = make_file_record(
        filename="delete.txt",
        owner_id=admin.id,
    )

    login(client, "trashadmin")

    for record in (first, second):
        token = csrf(client, "/")

        moved = client.post(
            "/trash",
            data={
                "path": record.stored_path,
                "csrf_token": token,
            },
            follow_redirects=False,
        )

        assert moved.status_code == 200

    trash_token = csrf(
        client,
        "/admin/trash",
    )

    restored = client.post(
        f"/admin/trash/{first.id}/restore",
        data={
            "csrf_token": trash_token,
        },
        follow_redirects=False,
    )

    assert restored.status_code == 303

    trash_token = csrf(
        client,
        "/admin/trash",
    )

    deleted = client.post(
        f"/admin/trash/{second.id}/delete",
        data={
            "csrf_token": trash_token,
        },
        follow_redirects=False,
    )

    assert deleted.status_code == 303

    with TestSessionLocal() as db:
        restored_record = db.get(
            FileRecord,
            first.id,
        )

        deleted_record = db.get(
            FileRecord,
            second.id,
        )

        assert restored_record is not None
        assert restored_record.is_trashed is False
        assert restored_record.trashed_at is None
        assert deleted_record is None

    assert (
        storage.STORAGE_DIR
        / "Documents"
        / "restore.txt"
    ).exists()



def test_trash_retention_deletes_only_expired_items(
    make_user,
    set_app_setting,
):

    owner = make_user(
        username="retentionadmin",
        role=UserRole.ADMIN.value,
    )

    set_app_setting(
        "trash_retention_days",
        7,
    )

    trash_directory = (
        storage.TRASH_DIR
        / "Documents"
    )

    trash_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    old_file = trash_directory / "old.txt"
    recent_file = trash_directory / "recent.txt"

    old_file.write_bytes(b"old")
    recent_file.write_bytes(b"recent")

    with TestSessionLocal() as db:
        old_record = FileRecord(
            stored_path=(
                old_file
                .relative_to(storage.STORAGE_DIR)
                .as_posix()
            ),
            original_name="old.txt",
            category="Documents",
            size_bytes=3,
            uploaded_by_id=owner.id,
            is_trashed=True,
            trashed_at=(
                datetime.now(timezone.utc)
                - timedelta(days=8)
            ),
        )

        recent_record = FileRecord(
            stored_path=(
                recent_file
                .relative_to(storage.STORAGE_DIR)
                .as_posix()
            ),
            original_name="recent.txt",
            category="Documents",
            size_bytes=6,
            uploaded_by_id=owner.id,
            is_trashed=True,
            trashed_at=(
                datetime.now(timezone.utc)
                - timedelta(days=2)
            ),
        )

        db.add_all([
            old_record,
            recent_record,
        ])
        db.commit()

        old_id = old_record.id
        recent_id = recent_record.id

        result = trash_routes.cleanup_expired_trash(
            db
        )

        assert result["deleted"] == 1
        assert db.get(FileRecord, old_id) is None
        assert db.get(FileRecord, recent_id) is not None

    assert not old_file.exists()
    assert recent_file.exists()



def test_trash_retention_zero_keeps_files_forever(
    make_user,
):

    owner = make_user(
        username="foreveradmin",
        role=UserRole.ADMIN.value,
    )

    trash_directory = (
        storage.TRASH_DIR
        / "Documents"
    )

    trash_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    old_file = trash_directory / "forever.txt"
    old_file.write_bytes(b"keep")

    with TestSessionLocal() as db:
        record = FileRecord(
            stored_path=(
                old_file
                .relative_to(storage.STORAGE_DIR)
                .as_posix()
            ),
            original_name="forever.txt",
            category="Documents",
            size_bytes=4,
            uploaded_by_id=owner.id,
            is_trashed=True,
            trashed_at=(
                datetime.now(timezone.utc)
                - timedelta(days=500)
            ),
        )

        db.add(record)
        db.commit()

        result = trash_routes.cleanup_expired_trash(
            db
        )

        assert result["retention_days"] == 0
        assert result["deleted"] == 0
        assert db.get(FileRecord, record.id) is not None

    assert old_file.exists()


# ============================================================
# ADMIN ACCOUNTS
# ============================================================

def test_admin_can_create_user_and_duplicate_is_rejected(
    client,
    make_user,
    login,
    csrf,
    db_session,
):

    make_user(
        username="accountsadmin",
        role=UserRole.ADMIN.value,
    )

    login(client, "accountsadmin")
    token = csrf(client, "/admin")

    created = client.post(
        "/admin/users",
        data={
            "display_name": "New Member",
            "username": "newmember",
            "password": TEST_PASSWORD,
            "role": UserRole.MEMBER.value,
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert created.status_code == 303
    assert "created=1" in created.headers["location"]

    db_session.expire_all()

    user = db_session.scalar(
        select(User).where(
            User.username == "newmember"
        )
    )

    assert user is not None
    assert user.role == UserRole.MEMBER.value

    token = csrf(client, "/admin")

    duplicate = client.post(
        "/admin/users",
        data={
            "display_name": "Duplicate",
            "username": "newmember",
            "password": TEST_PASSWORD,
            "role": UserRole.MEMBER.value,
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert duplicate.status_code == 303
    assert "error=username_exists" in duplicate.headers["location"]



def test_admin_cannot_disable_or_demote_self(
    client,
    make_user,
    login,
    csrf,
):

    admin = make_user(
        username="selfadmin",
        role=UserRole.ADMIN.value,
    )

    login(client, "selfadmin")

    token = csrf(client, "/admin")

    disable = client.post(
        f"/admin/users/{admin.id}/toggle-active",
        data={
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert disable.status_code == 303
    assert "error=self_disable" in disable.headers["location"]

    token = csrf(client, "/admin")

    demote = client.post(
        f"/admin/users/{admin.id}/role",
        data={
            "role": UserRole.MEMBER.value,
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert demote.status_code == 303
    assert "error=self_role" in demote.headers["location"]



def test_admin_can_change_other_users_role_and_active_state(
    client,
    make_user,
    login,
    csrf,
):

    make_user(
        username="manageradmin",
        role=UserRole.ADMIN.value,
    )

    member = make_user(
        username="managedmember",
        role=UserRole.MEMBER.value,
    )

    login(client, "manageradmin")

    token = csrf(client, "/admin")

    promote = client.post(
        f"/admin/users/{member.id}/role",
        data={
            "role": UserRole.ADMIN.value,
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert promote.status_code == 303
    assert "role_changed=1" in promote.headers["location"]

    token = csrf(client, "/admin")

    toggle = client.post(
        f"/admin/users/{member.id}/toggle-active",
        data={
            "csrf_token": token,
        },
        follow_redirects=False,
    )

    assert toggle.status_code == 303
    assert "deactivated=1" in toggle.headers["location"]

    with TestSessionLocal() as db:
        updated = db.get(User, member.id)
        assert updated.role == UserRole.ADMIN.value
        assert updated.is_active is False


# ============================================================
# SETTINGS
# ============================================================

def test_admin_can_save_settings(
    client,
    make_user,
    login,
    csrf,
):

    make_user(
        username="settingsadmin",
        role=UserRole.ADMIN.value,
    )

    login(client, "settingsadmin")

    token = csrf(
        client,
        "/admin/settings",
    )

    response = client.post(
        "/admin/settings",
        data=valid_settings_form(
            token
        ),
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "saved=1" in response.headers["location"]

    with TestSessionLocal() as db:
        settings = (
            settings_service.get_template_settings(
                db
            )
        )

        assert settings["cloud_name"] == "Vanta Test"
        assert settings["theme"] == "dark"
        assert settings["max_upload_mb"] == 25
        assert settings["duplicate_behavior"] == "reject"
        assert settings["trash_retention_days"] == 30
        assert settings["default_view"] == "Photos"
        assert settings["allow_member_rename_own"] is True



def test_invalid_setting_rolls_back(
    client,
    make_user,
    login,
    csrf,
):

    make_user(
        username="invalidsettingsadmin",
        role=UserRole.ADMIN.value,
    )

    login(client, "invalidsettingsadmin")
    token = csrf(client, "/admin/settings")

    form = valid_settings_form(token)
    form["max_upload_mb"] = "0"

    response = client.post(
        "/admin/settings",
        data=form,
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert "error=invalid" in response.headers["location"]

    with TestSessionLocal() as db:
        value = settings_service.get_int_setting(
            db,
            "max_upload_mb",
        )

        assert value == 2048


# ============================================================
# CSRF COVERAGE FOR STATE-CHANGING ROUTES
# ============================================================

def test_state_changing_routes_reject_missing_csrf(
    client,
    make_user,
    login,
    make_file_record,
):

    admin = make_user(
        username="csrfadmin",
        role=UserRole.ADMIN.value,
    )

    record = make_file_record(
        filename="csrf.txt",
        owner_id=admin.id,
    )

    login(client, "csrfadmin")

    upload = client.post(
        "/upload",
        files={
            "file": (
                "blocked.txt",
                b"x",
                "text/plain",
            ),
        },
        follow_redirects=False,
    )

    rename = client.post(
        f"/files/{record.id}/rename",
        data={
            "new_name": "renamed.txt",
        },
        follow_redirects=False,
    )

    move = client.post(
        "/trash",
        data={
            "path": record.stored_path,
        },
        follow_redirects=False,
    )

    create_user = client.post(
        "/admin/users",
        data={
            "display_name": "Blocked",
            "username": "blockeduser",
            "password": TEST_PASSWORD,
            "role": UserRole.MEMBER.value,
        },
        follow_redirects=False,
    )

    settings = valid_settings_form(
        "placeholder"
    )
    settings.pop("csrf_token")

    save_settings = client.post(
        "/admin/settings",
        data=settings,
        follow_redirects=False,
    )

    logout = client.post(
        "/logout",
        data={},
        follow_redirects=False,
    )

    assert upload.status_code == 403
    assert rename.status_code == 403
    assert move.status_code == 403
    assert create_user.status_code == 403
    assert save_settings.status_code == 403
    assert logout.status_code == 403


# ============================================================
# TIMEZONE SERIALIZATION
# ============================================================

def test_upload_timestamp_serialization_marks_utc():

    naive = datetime(
        2026,
        8,
        26,
        8,
        26,
        0,
    )

    serialized = main.datetime_to_utc_iso(
        naive
    )

    assert serialized is not None
    assert serialized.endswith("+00:00")
