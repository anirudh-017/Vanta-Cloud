from datetime import (
    datetime,
    timedelta,
    timezone,
)
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
)

from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..csrf import (
    get_csrf_token,
    validate_csrf_token,
)
from ..database import get_db
from ..models import FileRecord, User

from ..services.settings import (
    get_int_setting,
)

from ..services.storage import (
    STORAGE_DIR,
    format_bytes,
    permanently_delete,
    resolve_trash_path,
    restore_file,
)
from ..services.activity import record_activity

# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/admin/trash",
    tags=["trash"],
)


# ============================================================
# TEMPLATES
# ============================================================

APP_DIR = (
    Path(__file__)
    .resolve()
    .parents[1]
)


templates = Jinja2Templates(
    directory=str(
        APP_DIR / "templates"
    )
)


# ============================================================
# DATETIME NORMALIZATION
# ============================================================

def normalize_datetime(
    value: datetime,
) -> datetime:

    """
    SQLite may return a datetime without timezone information
    even though our model stores UTC timestamps.

    Treat naive timestamps as UTC so comparisons remain safe.
    """

    if value.tzinfo is None:

        return value.replace(
            tzinfo=timezone.utc
        )


    return value.astimezone(
        timezone.utc
    )


# ============================================================
# AUTOMATIC TRASH RETENTION CLEANUP
# ============================================================

def cleanup_expired_trash(
    db: Session,
) -> dict:

    """
    Remove Trash entries older than the configured retention
    period.

    trash_retention_days:

        0  -> never automatically delete
        7  -> delete after seven days
        30 -> delete after thirty days
        90 -> delete after ninety days

    Cleanup runs when an Admin opens the Trash dashboard.

    This is intentional for Vanta v1. The application does not
    need a separate background worker running continuously.
    """

    retention_days = (
        get_int_setting(
            db,
            "trash_retention_days",
        )
    )


    result = {

        "retention_days":
            retention_days,

        "deleted":
            0,

        "missing":
            0,

        "skipped":
            0,

        "failed":
            0,

    }


    # ========================================================
    # ZERO MEANS KEEP FOREVER
    # ========================================================

    if retention_days <= 0:

        return result


    cutoff = (

        datetime.now(
            timezone.utc
        )

        -

        timedelta(
            days=retention_days
        )

    )


    # ========================================================
    # LOAD TRASH RECORDS
    # ========================================================

    records = db.scalars(

        select(
            FileRecord
        )

        .where(
            FileRecord.is_trashed.is_(
                True
            )
        )

    ).all()


    # ========================================================
    # CHECK EACH RECORD
    # ========================================================

    for record in records:

        # ====================================================
        # NO TRASH DATE
        # ====================================================
        #
        # If we do not know when a file entered Trash, do not
        # automatically destroy it.
        #
        # Manual deletion is still available to Admins.
        # ====================================================

        if record.trashed_at is None:

            result["skipped"] += 1

            continue


        trashed_at = (
            normalize_datetime(
                record.trashed_at
            )
        )


        # ====================================================
        # FILE IS NOT OLD ENOUGH
        # ====================================================

        if trashed_at > cutoff:

            continue


        # ====================================================
        # RESOLVE PHYSICAL TRASH PATH
        # ====================================================

        try:

            trash_path = (
                resolve_trash_path(
                    record.stored_path
                )
            )


        except HTTPException:

            # A malformed or unsafe path should never be
            # automatically acted on.

            result["skipped"] += 1

            continue


        # ====================================================
        # DELETE PHYSICAL FILE
        # ====================================================

        if trash_path.exists():

            if not trash_path.is_file():

                result["skipped"] += 1

                continue


            try:

                permanently_delete(
                    trash_path
                )


            except (
                HTTPException,
                OSError,
            ):

                result["failed"] += 1

                continue


        else:

            # The database says the file is in Trash but the
            # physical file is already gone.
            #
            # Since this record has also passed its retention
            # deadline, remove the stale database entry.

            result["missing"] += 1


        # ====================================================
        # DELETE DATABASE RECORD
        # ====================================================
        #
        # Commit one record at a time.
        #
        # This is slightly more database work, but Trash cleanup
        # happens infrequently and this limits how much state can
        # become inconsistent if one operation fails.
        # ====================================================

        try:

            db.delete(
                record
            )


            db.commit()


            result["deleted"] += 1


        except Exception:

            db.rollback()


            # If the physical file was deleted but SQLite failed,
            # the stale record will remain.
            #
            # On the next cleanup pass, Vanta sees the missing
            # physical file and can remove that stale record.

            result["failed"] += 1


    return result


# ============================================================
# TRASH DASHBOARD
# ============================================================

@router.get("")
def trash_dashboard(

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_admin: User = Depends(
        require_admin
    ),

):

    # ========================================================
    # APPLY RETENTION POLICY
    # ========================================================

    cleanup_result = (
        cleanup_expired_trash(
            db
        )
    )


    # ========================================================
    # LOAD REMAINING TRASH FILES
    # ========================================================

    rows = db.execute(

        select(
            FileRecord,
            User,
        )

        .outerjoin(
            User,
            FileRecord.uploaded_by_id
            ==
            User.id,
        )

        .where(
            FileRecord.is_trashed.is_(
                True
            )
        )

        .order_by(
            FileRecord.trashed_at.desc()
        )

    ).all()


    files = []


    for record, owner in rows:

        try:

            physical_path = (
                resolve_trash_path(
                    record.stored_path
                )
            )


            exists = (
                physical_path.exists()
                and
                physical_path.is_file()
            )


        except HTTPException:

            exists = False


        files.append({

            "id":
                record.id,

            "name":
                record.original_name,

            "category":
                record.category,

            "stored_path":
                record.stored_path,

            "size_bytes":
                record.size_bytes,

            "size_text":
                format_bytes(
                    record.size_bytes
                ),

            "owner_name":
                (
                    owner.display_name
                    if owner
                    else "Unknown"
                ),

            "trashed_at":
                (
                    normalize_datetime(
                        record.trashed_at
                    ).isoformat()
                    if record.trashed_at
                    else None
                ),

            "exists":
                exists,

        })


    return templates.TemplateResponse(

        request=request,

        name="trash.html",

        context={

            "files":
                files,

            "current_user":
                current_admin,

            "csrf_token":
                get_csrf_token(
                    request
                ),

            "app_name":
                "Vanta Cloud",

            "trash_retention_days":
                cleanup_result[
                    "retention_days"
                ],

            "cleanup_result":
                cleanup_result,

        },

    )


# ============================================================
# RESTORE FILE
# ============================================================

@router.post(
    "/{file_id}/restore"
)
def restore_trashed_file(

    file_id: int,

    request: Request,

    csrf_token: str | None = Form(
        None
    ),

    db: Session = Depends(
        get_db
    ),

    current_admin: User = Depends(
        require_admin
    ),

):

    validate_csrf_token(
        request,
        csrf_token,
    )

    # ========================================================
    # FIND DATABASE RECORD
    # ========================================================

    record = db.get(
        FileRecord,
        file_id,
    )


    if record is None:

        raise HTTPException(
            status_code=404,
            detail="File record not found",
        )


    if not record.is_trashed:

        raise HTTPException(
            status_code=400,
            detail="File is not in Trash",
        )


    # ========================================================
    # FIND PHYSICAL TRASH FILE
    # ========================================================

    trash_path = (
        resolve_trash_path(
            record.stored_path
        )
    )


    if (
        not trash_path.exists()
        or
        not trash_path.is_file()
    ):

        raise HTTPException(
            status_code=404,
            detail="Physical Trash file not found",
        )


    # ========================================================
    # RESTORE PHYSICAL FILE
    # ========================================================

    destination = restore_file(

        trash_path=
            trash_path,

        category=
            record.category,

        preferred_name=
            record.original_name,

    )


    storage_root = (
        STORAGE_DIR.resolve()
    )


    old_stored_path = (
        record.stored_path
    )


    old_trashed_at = (
        record.trashed_at
    )


    # ========================================================
    # UPDATE DATABASE
    # ========================================================

    try:

        record.stored_path = (
            destination
            .relative_to(
                storage_root
            )
            .as_posix()
        )


        record.is_trashed = False

        record.trashed_at = None


        db.commit()
        record_activity(
    db,
    current_admin,
    action="restore",
    target_name=record.original_name,
    details=f"Restored {record.original_name}",
)

    except Exception:

        db.rollback()


        # ====================================================
        # DATABASE FAILED AFTER FILE RESTORE
        # ====================================================
        #
        # Try to return the physical file to Trash so the disk
        # and database continue agreeing.
        # ====================================================

        try:

            if (
                destination.exists()
                and
                not trash_path.exists()
            ):

                trash_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )


                destination.rename(
                    trash_path
                )


        except OSError:

            pass


        record.stored_path = (
            old_stored_path
        )


        record.is_trashed = True


        record.trashed_at = (
            old_trashed_at
        )


        raise


    return RedirectResponse(

        url="/admin/trash?restored=1",

        status_code=303,

    )


# ============================================================
# PERMANENT DELETE
# ============================================================

@router.post(
    "/{file_id}/delete"
)
def delete_trashed_file(

    file_id: int,

    request: Request,

    csrf_token: str | None = Form(
        None
    ),

    db: Session = Depends(
        get_db
    ),

    current_admin: User = Depends(
        require_admin
    ),

):

    validate_csrf_token(
        request,
        csrf_token,
    )

    # ========================================================
    # FIND DATABASE RECORD
    # ========================================================

    record = db.get(
        FileRecord,
        file_id,
    )


    if record is None:

        raise HTTPException(
            status_code=404,
            detail="File record not found",
        )


    if not record.is_trashed:

        raise HTTPException(
            status_code=400,
            detail=(
                "Only Trash files can be "
                "permanently deleted"
            ),
        )


    # ========================================================
    # RESOLVE TRASH FILE
    # ========================================================

    trash_path = (
        resolve_trash_path(
            record.stored_path
        )
    )


    # ========================================================
    # DELETE PHYSICAL FILE
    # ========================================================
    #
    # Missing physical files are not an error here.
    #
    # The database record is stale and should still be removed.
    # ========================================================

    if (
        trash_path.exists()
        and
        trash_path.is_file()
    ):

        permanently_delete(
            trash_path
        )


    # ========================================================
    # DELETE DATABASE RECORD
    # ========================================================
    deleted_name = (
        record.original_name
    )

    db.delete(
        record
    )

    db.commit()

    record_activity(
        db,
        current_admin,
        action="permanent_delete",
        target_name=deleted_name,
        details=f"Permanently deleted {deleted_name}",
    )


    return RedirectResponse(

        url="/admin/trash?deleted=1",

        status_code=303,

    )