from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
)
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from ..services.activity import record_activity
from ..auth import require_user
from ..csrf import validate_csrf_token
from ..database import get_db
from ..models import (
    FileRecord,
    User,
    UserRole,
)
from ..services.settings import get_bool_setting
from ..services.storage import (
    STORAGE_DIR,
    rename_file,
    resolve_storage_path,
    validate_filename,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/files",
    tags=["files"],
)


# ============================================================
# RENAME FILE
# ============================================================

@router.post(
    "/{file_id}/rename"
)
def rename_vanta_file(

    file_id: int,

    request: Request,

    new_name: str = Form(
        ...
    ),

    csrf_token: str | None = Form(
        None
    ),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_user
    ),

):

    # ========================================================
    # CSRF
    # ========================================================

    validate_csrf_token(
        request,
        csrf_token,
    )


    # ========================================================
    # DATABASE RECORD
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


    if record.is_trashed:

        raise HTTPException(
            status_code=400,
            detail="Restore the file before renaming it",
        )


    # ========================================================
    # PERMISSION
    # ========================================================

    user_is_admin = (
        current_user.role
        ==
        UserRole.ADMIN.value
    )


    if not user_is_admin:

        member_rename_allowed = (
            get_bool_setting(
                db,
                "allow_member_rename_own",
            )
        )


        if not member_rename_allowed:

            raise HTTPException(
                status_code=403,
                detail=(
                    "Renaming files is disabled "
                    "for Member accounts"
                ),
            )


        if (
            record.uploaded_by_id
            !=
            current_user.id
        ):

            raise HTTPException(
                status_code=403,
                detail=(
                    "You can only rename "
                    "files you uploaded"
                ),
            )


    # ========================================================
    # VALIDATE NEW NAME
    # ========================================================

    safe_new_name = (
        validate_filename(
            new_name
        )
    )


    # ========================================================
    # CURRENT PHYSICAL FILE
    # ========================================================

    current_path = (
        resolve_storage_path(
            record.stored_path
        )
    )


    if (
        not current_path.exists()
        or
        not current_path.is_file()
    ):

        raise HTTPException(
            status_code=404,
            detail="Physical file not found",
        )


    # ========================================================
    # EXTENSION MUST STAY THE SAME
    # ========================================================

    current_extension = (
        current_path
        .suffix
        .lower()
    )


    new_extension = (
        Path(
            safe_new_name
        )
        .suffix
        .lower()
    )


    if (
        current_extension
        !=
        new_extension
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "File extension cannot be "
                "changed during rename"
            ),
        )


    # ========================================================
    # NO-OP
    # ========================================================

    if (
        safe_new_name
        ==
        current_path.name
    ):

        return RedirectResponse(
            url="/?renamed=1",
            status_code=303,
        )


    # ========================================================
    # SAVE ORIGINAL DATABASE VALUES
    # ========================================================

    old_stored_path = (
        record.stored_path
    )

    old_name = (
        record.original_name
    )


    # ========================================================
    # PHYSICAL RENAME
    # ========================================================

    renamed_path = (
        rename_file(
            current_path,
            safe_new_name,
        )
    )


    storage_root = (
        STORAGE_DIR.resolve()
    )


    # ========================================================
    # NEW STORAGE PATH
    # ========================================================

    try:

        new_stored_path = (
            renamed_path
            .relative_to(
                storage_root
            )
            .as_posix()
        )

    except ValueError:

        try:

            if renamed_path.exists():

                renamed_path.rename(
                    current_path
                )

        except OSError:

            pass


        raise HTTPException(
            status_code=500,
            detail=(
                "Rename produced an invalid "
                "storage path"
            ),
        )


    # ========================================================
    # DATABASE UPDATE
    # ========================================================

    try:

        record.stored_path = (
            new_stored_path
        )

        record.original_name = (
            safe_new_name
        )

        db.commit()
        record_activity(
    db,
    current_user,
    action="rename",
    target_name=safe_new_name,
    details=(
        f"Renamed {old_name} "
        f"to {safe_new_name}"
    ),
)


    except Exception:

        db.rollback()


        if renamed_path.exists():

            try:

                renamed_path.rename(
                    current_path
                )

            except OSError:

                pass


        record.stored_path = (
            old_stored_path
        )

        record.original_name = (
            old_name
        )

        raise


    return RedirectResponse(
        url="/?renamed=1",
        status_code=303,
    )
