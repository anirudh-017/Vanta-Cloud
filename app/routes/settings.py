from pathlib import Path
import sys

import fastapi

from fastapi import (
    APIRouter,
    Depends,
    Form,
    Request,
)
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..auth import require_admin
from ..csrf import (
    get_csrf_token,
    validate_csrf_token,
)
from ..database import get_db
from ..models import User
from ..services.settings import (
    ensure_default_settings,
    get_template_settings,
    set_setting,
)
from ..services.storage import (
    STORAGE_DIR,
    get_storage_stats,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/admin/settings",
    tags=["settings"],
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
# SETTINGS PAGE
# ============================================================

@router.get("")
def settings_page(

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_admin: User = Depends(
        require_admin
    ),

):

    ensure_default_settings(
        db
    )


    settings = (
        get_template_settings(
            db
        )
    )


    storage = (
        get_storage_stats()
    )


    return templates.TemplateResponse(

        request=request,

        name="settings.html",

        context={

            "current_user":
                current_admin,

            "csrf_token":
                get_csrf_token(
                    request
                ),

            "settings":
                settings,

            "storage":
                storage,

            "storage_path":
                str(
                    STORAGE_DIR
                ),

            "python_version":
                (
                    f"{sys.version_info.major}."
                    f"{sys.version_info.minor}."
                    f"{sys.version_info.micro}"
                ),

            "fastapi_version":
                fastapi.__version__,

            "app_name":
                "Vanta Cloud",

        },

    )


# ============================================================
# SAVE SETTINGS
# ============================================================

@router.post("")
def save_settings(

    request: Request,

    # --------------------------------------------------------
    # GENERAL
    # --------------------------------------------------------

    cloud_name: str = Form(
        ...
    ),

    tagline: str = Form(
        ...
    ),


    # --------------------------------------------------------
    # APPEARANCE
    # --------------------------------------------------------

    theme: str = Form(
        ...
    ),


    # --------------------------------------------------------
    # MEMBER PERMISSIONS
    # --------------------------------------------------------

    allow_member_uploads: str | None = Form(
        None
    ),

    allow_member_downloads: str | None = Form(
        None
    ),

    allow_member_previews: str | None = Form(
        None
    ),

    allow_member_trash_own: str | None = Form(
        None
    ),

    allow_member_rename_own: str | None = Form(
        None
    ),


    # --------------------------------------------------------
    # UPLOAD SETTINGS
    # --------------------------------------------------------

    max_upload_mb: str = Form(
        ...
    ),

    multiple_uploads: str | None = Form(
        None
    ),

    duplicate_behavior: str = Form(
        ...
    ),

    allowed_file_types: str = Form(
        "all"
    ),


    # --------------------------------------------------------
    # TRASH SETTINGS
    # --------------------------------------------------------

    trash_enabled: str | None = Form(
        None
    ),

    trash_retention_days: str = Form(
        ...
    ),


    # --------------------------------------------------------
    # FILE DISPLAY
    # --------------------------------------------------------

    show_uploader: str | None = Form(
        None
    ),

    show_upload_time: str | None = Form(
        None
    ),


    # --------------------------------------------------------
    # INTERFACE
    # --------------------------------------------------------

    default_view: str = Form(
        ...
    ),


    # --------------------------------------------------------
    # SECURITY
    # --------------------------------------------------------

    csrf_token: str | None = Form(
        None
    ),


    # --------------------------------------------------------
    # DEPENDENCIES
    # --------------------------------------------------------

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


    try:

        # ====================================================
        # GENERAL
        # ====================================================

        set_setting(
            db,
            "cloud_name",
            cloud_name,
        )

        set_setting(
            db,
            "tagline",
            tagline,
        )


        # ====================================================
        # APPEARANCE
        # ====================================================

        set_setting(
            db,
            "theme",
            theme,
        )


        # ====================================================
        # MEMBER PERMISSIONS
        # ====================================================

        set_setting(
            db,
            "allow_member_uploads",
            allow_member_uploads
            is not None,
        )

        set_setting(
            db,
            "allow_member_downloads",
            allow_member_downloads
            is not None,
        )

        set_setting(
            db,
            "allow_member_previews",
            allow_member_previews
            is not None,
        )

        set_setting(
            db,
            "allow_member_trash_own",
            allow_member_trash_own
            is not None,
        )

        set_setting(
            db,
            "allow_member_rename_own",
            allow_member_rename_own
            is not None,
        )


        # ====================================================
        # UPLOAD SETTINGS
        # ====================================================

        set_setting(
            db,
            "max_upload_mb",
            max_upload_mb,
        )

        set_setting(
            db,
            "multiple_uploads",
            multiple_uploads
            is not None,
        )

        set_setting(
            db,
            "duplicate_behavior",
            duplicate_behavior,
        )

        set_setting(
            db,
            "allowed_file_types",
            allowed_file_types,
        )


        # ====================================================
        # TRASH SETTINGS
        # ====================================================

        set_setting(
            db,
            "trash_enabled",
            trash_enabled
            is not None,
        )

        set_setting(
            db,
            "trash_retention_days",
            trash_retention_days,
        )


        # ====================================================
        # FILE DISPLAY
        # ====================================================

        set_setting(
            db,
            "show_uploader",
            show_uploader
            is not None,
        )

        set_setting(
            db,
            "show_upload_time",
            show_upload_time
            is not None,
        )


        # ====================================================
        # INTERFACE
        # ====================================================

        set_setting(
            db,
            "default_view",
            default_view,
        )


        # ====================================================
        # COMMIT
        # ====================================================

        db.commit()


    except ValueError:

        db.rollback()


        return RedirectResponse(
            url="/admin/settings?error=invalid",
            status_code=303,
        )


    except Exception:

        db.rollback()

        raise


    return RedirectResponse(
        url="/admin/settings?saved=1",
        status_code=303,
    )
