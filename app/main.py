from datetime import datetime, timezone
from pathlib import Path
import mimetypes
import shutil

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Request,
    UploadFile,
)

from fastapi.responses import (
    FileResponse,
    JSONResponse,
    RedirectResponse,
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from starlette.middleware.sessions import SessionMiddleware

from .auth import (
    authenticate_user,
    get_current_user,
    hash_password,
    is_admin,
    login_user,
    logout_user,
    require_user,
)

from .config import SESSION_SECRET

from .csrf import (
    get_csrf_token,
    rotate_csrf_token,
    validate_csrf_token,
)

from .database import (
    get_db,
    init_db,
)

from .models import (
    FileRecord,
    User,
    UserPreference,
    UserRole,
)

from .routes.admin import (
    router as admin_router,
)

from .routes.files import (
    router as files_router,
)

from .routes.settings import (
    router as settings_router,
)

from .routes.trash import (
    router as trash_router,
)

from .services.settings import (
    get_bool_setting,
    get_int_setting,
    get_setting,
    get_template_settings,
)

from .services.storage import (
    STORAGE_DIR,
    TRASH_DIR,
    format_bytes,
    get_category,
    get_storage_stats,
    get_unique_destination,
    initialize_storage,
    resolve_storage_path,
    validate_filename,
)
from .services.activity import record_activity


# ============================================================
# APPLICATION CONSTANTS
# ============================================================

APP_NAME = "Vanta Cloud"

TAGLINE = (
    "Your files. Your space. Completely private."
)

HERO_TEXT = (
    "Securely yours, always."
)


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title=APP_NAME,
    description="Private local cloud storage",
)


# ============================================================
# SESSION MIDDLEWARE
# ============================================================

app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    session_cookie="vanta_session",
    max_age=60 * 60 * 24 * 7,
    same_site="lax",
    https_only=False,
)


# ============================================================
# ROUTERS
# ============================================================

app.include_router(
    admin_router
)

app.include_router(
    files_router
)

app.include_router(
    settings_router
)

app.include_router(
    trash_router
)


# ============================================================
# INITIALIZATION
# ============================================================

init_db()

initialize_storage()


# ============================================================
# DEVELOPMENT CACHE CONTROL
# ============================================================

@app.middleware("http")
async def disable_frontend_cache(
    request: Request,
    call_next,
):

    response = await call_next(
        request
    )

    path = request.url.path

    if (
        path == "/"
        or path == "/login"
        or path == "/setup"
        or path.startswith("/admin")
        or path.startswith("/static/")
    ):

        response.headers[
            "Cache-Control"
        ] = (
            "no-store, no-cache, "
            "must-revalidate, max-age=0"
        )

        response.headers[
            "Pragma"
        ] = "no-cache"

        response.headers[
            "Expires"
        ] = "0"

    return response


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
)


# ============================================================
# TEMPLATES
# ============================================================

templates = Jinja2Templates(
    directory=str(
        BASE_DIR / "templates"
    )
)


# ============================================================
# STATIC FILES
# ============================================================

app.mount(
    "/static",

    StaticFiles(
        directory=str(
            BASE_DIR / "static"
        )
    ),

    name="static",
)

# ============================================================
# FRIENDLY ERROR UX
# ============================================================

def request_wants_json(
    request: Request,
) -> bool:

    return (
        request.headers.get(
            "X-Requested-With"
        )
        ==
        "XMLHttpRequest"
        or
        request.url.path.startswith(
            "/api/"
        )
    )


def get_error_title(
    status_code: int,
) -> str:

    titles = {

        400:
            "Invalid request",

        401:
            "Session required",

        403:
            "Access denied",

        404:
            "Not found",

        405:
            "Action not allowed",

        409:
            "File conflict",

        413:
            "File too large",

        422:
            "Invalid information",

        500:
            "Something went wrong",

    }

    return titles.get(
        status_code,
        "Something went wrong",
    )


def get_error_message(
    status_code: int,
    detail=None,
) -> str:

    if (
        isinstance(detail, str)
        and
        detail.strip()
    ):

        return detail.strip()


    messages = {

        400:
            (
                "Vanta could not complete "
                "that request."
            ),

        401:
            (
                "Please log in again "
                "to continue."
            ),

        403:
            (
                "Your account does not have "
                "permission to perform this action."
            ),

        404:
            (
                "The requested file or page "
                "could not be found."
            ),

        405:
            (
                "That action is not supported."
            ),

        409:
            (
                "That action conflicts with "
                "an existing file or record."
            ),

        413:
            (
                "The selected file exceeds "
                "the allowed upload size."
            ),

        422:
            (
                "One or more submitted values "
                "were invalid or missing."
            ),

        500:
            (
                "Vanta encountered an unexpected "
                "error. Your files were not "
                "intentionally changed."
            ),

    }

    return messages.get(
        status_code,
        (
            "Vanta could not complete "
            "that request."
        ),
    )


def render_error_response(
    request: Request,
    status_code: int,
    detail=None,
):

    title = get_error_title(
        status_code
    )

    message = get_error_message(
        status_code,
        detail,
    )


    if request_wants_json(
        request
    ):

        return JSONResponse(

            status_code=
                status_code,

            content={
                "detail":
                    message,
            },

        )


    if (
        status_code
        ==
        401
    ):

        return RedirectResponse(
            url="/login",
            status_code=303,
        )


    return templates.TemplateResponse(

        request=request,

        name="error.html",

        context={

            "app_name":
                APP_NAME,

            "error_code":
                status_code,

            "error_title":
                title,

            "error_message":
                message,

        },

        status_code=
            status_code,

    )


@app.exception_handler(
    StarletteHTTPException
)
async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
):

    return render_error_response(

        request,

        exc.status_code,

        exc.detail,

    )


@app.exception_handler(
    RequestValidationError
)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):

    return render_error_response(

        request,

        400,

        (
            "One or more submitted values "
            "were invalid or missing."
        ),

    )


@app.exception_handler(
    Exception
)
async def unexpected_exception_handler(
    request: Request,
    exc: Exception,
):

    return render_error_response(

        request,

        500,

        None,

    )


# ============================================================
# ACCOUNT HELPERS
# ============================================================

def user_exists(
    db: Session,
) -> bool:

    existing_user = db.scalar(

        select(
            User.id
        ).limit(1)

    )

    return (
        existing_user
        is not None
    )


# ============================================================
# DATETIME NORMALIZATION
# ============================================================

def datetime_to_utc_iso(
    value: datetime | None,
) -> str | None:

    if value is None:

        return None


    if value.tzinfo is None:

        value = value.replace(
            tzinfo=timezone.utc
        )

    else:

        value = value.astimezone(
            timezone.utc
        )


    return value.isoformat()


# ============================================================
# USERNAME VALIDATION
# ============================================================

def validate_username(
    username: str,
) -> str:

    username = (
        username
        .strip()
        .lower()
    )

    if (
        len(username) < 3
        or
        len(username) > 30
    ):

        raise ValueError(
            "Username must be between "
            "3 and 30 characters."
        )

    allowed = set(
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789"
        "._-"
    )

    if not all(
        character in allowed
        for character in username
    ):

        raise ValueError(
            "Username can only contain letters, "
            "numbers, dots, underscores, "
            "and hyphens."
        )

    return username


# ============================================================
# BRANDING
# ============================================================

def get_branding(
    db: Session,
) -> dict:

    settings = get_template_settings(
        db
    )

    return {

        "app_name":
            settings[
                "cloud_name"
            ],

        "tagline":
            settings[
                "tagline"
            ],

        "hero_text":
            HERO_TEXT,

    }


# ============================================================
# MEMBER PERMISSION HELPER
# ============================================================

def member_permission_allowed(
    db: Session,
    current_user: User,
    setting_key: str,
) -> bool:

    if is_admin(
        current_user
    ):

        return True

    return get_bool_setting(
        db,
        setting_key,
    )


# ============================================================
# GET ACTIVE FILES
# ============================================================

def get_all_files(
    db: Session,
):

    files = []

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
            FileRecord.is_trashed
            ==
            False
        )

    ).all()


    record_map = {

        record.stored_path:
        (
            record,
            owner,
        )

        for record, owner in rows

    }


    for item in STORAGE_DIR.rglob(
        "*"
    ):

        if not item.is_file():

            continue


        try:

            relative_path = (
                item.relative_to(
                    STORAGE_DIR
                )
            )

        except ValueError:

            continue


        if (
            ".Trash"
            in relative_path.parts
        ):

            continue


        try:

            stats = item.stat()

        except OSError:

            continue


        relative_path_text = (
            relative_path
            .as_posix()
        )


        metadata = (
            record_map.get(
                relative_path_text
            )
        )


        record_id = None
        uploaded_by_id = None


        if metadata:

            record, owner = (
                metadata
            )

            record_id = (
                record.id
            )

            uploaded_by_id = (
                record.uploaded_by_id
            )

            owner_name = (

                owner.display_name

                if owner

                else "Unknown user"

            )

            uploaded_at_iso = (
                datetime_to_utc_iso(
                    record.created_at
                )
            )


        else:

            owner_name = (
                "Legacy file"
            )

            uploaded_at_iso = None


        if (
            len(
                relative_path.parts
            )
            ==
            1
        ):

            category = (
                "Unsorted"
            )

        else:

            category = (
                relative_path.parts[
                    0
                ]
            )


        files.append({

            "id":
                record_id,

            "name":
                item.name,

            "category":
                category,

            "relative_path":
                relative_path_text,

            "size":
                stats.st_size,

            "size_text":
                format_bytes(
                    stats.st_size
                ),

            "modified":
                stats.st_mtime,

            "owner_name":
                owner_name,

            "uploaded_at_iso":
                uploaded_at_iso,

            "uploaded_by_id":
                uploaded_by_id,

            "has_owner_record":
                metadata is not None,

        })


    files.sort(
        key=lambda file:
            file[
                "modified"
            ],
        reverse=True,
    )


    return files


# ============================================================
# FIRST-TIME SETUP PAGE
# ============================================================

@app.get("/setup")
def setup_page(

    request: Request,

    db: Session = Depends(
        get_db
    ),

):

    if user_exists(
        db
    ):

        return RedirectResponse(
            url="/login",
            status_code=303,
        )


    context = {

        "error":
            None,

        "csrf_token":
            get_csrf_token(
                request
            ),

        **get_branding(
            db
        ),

    }


    return templates.TemplateResponse(
        request=request,
        name="setup.html",
        context=context,
    )


# ============================================================
# CREATE FIRST ADMIN
# ============================================================

@app.post("/setup")
def create_first_admin(

    request: Request,

    display_name: str = Form(
        ...
    ),

    username: str = Form(
        ...
    ),

    password: str = Form(
        ...
    ),

    confirm_password: str = Form(
        ...
    ),

    csrf_token: str = Form(
        ...
    ),

    db: Session = Depends(
        get_db
    ),

):

    if user_exists(
        db
    ):

        return RedirectResponse(
            url="/login",
            status_code=303,
        )


    # ========================================================
    # CSRF VALIDATION
    # ========================================================

    validate_csrf_token(
        request,
        csrf_token,
    )


    display_name = (
        display_name.strip()
    )


    branding = get_branding(
        db
    )


    # ========================================================
    # DISPLAY NAME VALIDATION
    # ========================================================

    if (
        len(display_name) < 1
        or
        len(display_name) > 100
    ):

        return templates.TemplateResponse(

            request=request,

            name="setup.html",

            context={

                "error":
                    (
                        "Display name must be "
                        "between 1 and 100 characters."
                    ),

                "csrf_token":
                    get_csrf_token(
                        request
                    ),

                **branding,

            },

            status_code=400,

        )


    # ========================================================
    # USERNAME VALIDATION
    # ========================================================

    try:

        username = validate_username(
            username
        )

    except ValueError as error:

        return templates.TemplateResponse(

            request=request,

            name="setup.html",

            context={

                "error":
                    str(
                        error
                    ),

                "csrf_token":
                    get_csrf_token(
                        request
                    ),

                **branding,

            },

            status_code=400,

        )


    # ========================================================
    # PASSWORD LENGTH
    # ========================================================

    if len(password) < 10:

        return templates.TemplateResponse(

            request=request,

            name="setup.html",

            context={

                "error":
                    (
                        "Password must contain "
                        "at least 10 characters."
                    ),

                "csrf_token":
                    get_csrf_token(
                        request
                    ),

                **branding,

            },

            status_code=400,

        )


    # ========================================================
    # PASSWORD MATCH
    # ========================================================

    if (
        password
        !=
        confirm_password
    ):

        return templates.TemplateResponse(

            request=request,

            name="setup.html",

            context={

                "error":
                    "Passwords do not match.",

                "csrf_token":
                    get_csrf_token(
                        request
                    ),

                **branding,

            },

            status_code=400,

        )


    # ========================================================
    # CREATE ADMIN
    # ========================================================

    admin = User(

        username=
            username,

        display_name=
            display_name,

        password_hash=
            hash_password(
                password
            ),

        role=
            UserRole.ADMIN.value,

        is_active=
            True,

    )


    db.add(
        admin
    )


    try:

        db.commit()

    except IntegrityError:

        db.rollback()


        return templates.TemplateResponse(

            request=request,

            name="setup.html",

            context={

                "error":
                    (
                        "That username "
                        "already exists."
                    ),

                "csrf_token":
                    get_csrf_token(
                        request
                    ),

                **branding,

            },

            status_code=400,

        )


    return RedirectResponse(
        url="/login",
        status_code=303,
    )


# ============================================================
# LOGIN PAGE
# ============================================================

@app.get("/login")
def login_page(

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User | None = Depends(
        get_current_user
    ),

):

    if not user_exists(
        db
    ):

        return RedirectResponse(
            url="/setup",
            status_code=303,
        )


    if (
        current_user
        is not None
    ):

        return RedirectResponse(
            url="/",
            status_code=303,
        )


    return templates.TemplateResponse(

        request=request,

        name="login.html",

        context={

            "error":
                None,

            "csrf_token":
                get_csrf_token(
                    request
                ),

            **get_branding(
                db
            ),

        },

    )


# ============================================================
# LOGIN
# ============================================================

@app.post("/login")
def login(

    request: Request,

    username: str = Form(
        ...
    ),

    password: str = Form(
        ...
    ),

    csrf_token: str = Form(
        ...
    ),

    db: Session = Depends(
        get_db
    ),

):

    if not user_exists(
        db
    ):

        return RedirectResponse(
            url="/setup",
            status_code=303,
        )


    # ========================================================
    # CSRF VALIDATION
    # ========================================================

    validate_csrf_token(
        request,
        csrf_token,
    )


    user = authenticate_user(
        db,
        username,
        password,
    )


    if user is None:

        return templates.TemplateResponse(

            request=request,

            name="login.html",

            context={

                "error":
                    (
                        "Invalid username "
                        "or password."
                    ),

                "csrf_token":
                    get_csrf_token(
                        request
                    ),

                **get_branding(
                    db
                ),

            },

            status_code=400,

        )


    # ========================================================
    # CREATE AUTHENTICATED SESSION
    # ========================================================

    login_user(
        request,
        user,
    )


    # Replace the pre-login CSRF token with a fresh token.

    rotate_csrf_token(
        request
    )


    return RedirectResponse(
        url="/",
        status_code=303,
    )


# ============================================================
# LOGOUT
# ============================================================

@app.post("/logout")
def logout(

    request: Request,

    csrf_token: str | None = Form(
        None
    ),

):

    validate_csrf_token(
        request,
        csrf_token,
    )


    logout_user(
        request
    )


    return RedirectResponse(
        url="/login",
        status_code=303,
    )

# ============================================================
# PERSONAL THEME PREFERENCE
# ============================================================

@app.post("/account/theme")
def update_account_theme(

    request: Request,

    theme: str = Form(...),

    csrf_token: str | None = Form(None),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_user
    ),

):

    validate_csrf_token(
        request,
        csrf_token,
    )


    allowed_themes = {
        "default",
        "system",
        "dark",
        "light",
    }


    if theme not in allowed_themes:

        raise HTTPException(
            status_code=400,
            detail="Invalid theme preference",
        )


    preference = db.get(
        UserPreference,
        current_user.id,
    )


    if theme == "default":

        if preference is not None:

            db.delete(
                preference
            )

    else:

        if preference is None:

            preference = UserPreference(
                user_id=current_user.id,
                theme=theme,
            )

            db.add(
                preference
            )

        else:

            preference.theme = theme


    try:

        db.commit()

    except Exception:

        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=(
                "Could not save "
                "theme preference"
            ),
        )


    return RedirectResponse(
        url="/",
        status_code=303,
    )

# ============================================================
# HOME PAGE
# ============================================================

@app.get("/")
def home(

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User | None = Depends(
        get_current_user
    ),

):

    if not user_exists(
        db
    ):

        return RedirectResponse(
            url="/setup",
            status_code=303,
        )


    if (
        current_user
        is None
    ):

        return RedirectResponse(
            url="/login",
            status_code=303,
        )


    settings = (
        get_template_settings(
            db
        )
    )


    user_preference = db.get(
        UserPreference,
        current_user.id,
    )


    theme_preference = (
        user_preference.theme
        if user_preference is not None
        else "default"
    )


    effective_theme = (
        user_preference.theme
        if user_preference is not None
        else settings[
            "theme"
        ]
    )


    files = get_all_files(
        db
    )


    # ========================================================
    # DISPLAY SETTINGS
    # ========================================================

    if not settings[
        "show_uploader"
    ]:

        for file_item in files:

            file_item[
                "owner_name"
            ] = None


    if not settings[
        "show_upload_time"
    ]:

        for file_item in files:

            file_item[
                "uploaded_at_iso"
            ] = None


    storage = (
        get_storage_stats()
    )


    user_is_admin = is_admin(
        current_user
    )


    can_upload = (
        user_is_admin
        or
        settings[
            "allow_member_uploads"
        ]
    )


    can_download = (
        user_is_admin
        or
        settings[
            "allow_member_downloads"
        ]
    )


    can_preview = (
        user_is_admin
        or
        settings[
            "allow_member_previews"
        ]
    )


    can_trash = (
        settings[
            "trash_enabled"
        ]
        and
        (
            user_is_admin
            or
            settings[
                "allow_member_trash_own"
            ]
        )
    )


    can_rename = (
        user_is_admin
        or
        settings[
            "allow_member_rename_own"
        ]
    )


    return templates.TemplateResponse(

        request=request,

        name="home.html",

        context={

            "files":
                files,

            "storage":
                storage,

            "current_user":
                current_user,

            "csrf_token":
                get_csrf_token(
                    request
                ),

            "current_user_is_admin":
                user_is_admin,

            "settings":
                settings,

            "can_upload":
                can_upload,

            "can_download":
                can_download,

            "can_preview":
                can_preview,

            "can_trash":
                can_trash,

            "can_rename":
                can_rename,

            "app_name":
                settings[
                    "cloud_name"
                ],

            "tagline":
                settings[
                    "tagline"
                ],

            "hero_text":
                HERO_TEXT,

            "theme":
                effective_theme,

            "theme_preference":
                theme_preference,

            "default_view":
                settings[
                    "default_view"
                ],

        },

    )


# ============================================================
# CURRENT ACCOUNT API
# ============================================================

@app.get("/api/me")
def current_account(

    current_user: User = Depends(
        require_user
    ),

):

    return {

        "id":
            current_user.id,

        "username":
            current_user.username,

        "display_name":
            current_user.display_name,

        "role":
            current_user.role,

        "is_active":
            current_user.is_active,

    }


# ============================================================
# FILE LIST API
# ============================================================

@app.get("/files")
def list_files(

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_user
    ),

):

    return {

        "files":
            get_all_files(
                db
            )

    }


# ============================================================
# STORAGE STATUS API
# ============================================================

@app.get("/storage-status")
def storage_status(

    current_user: User = Depends(
        require_user
    ),

):

    return {

        "exists":
            STORAGE_DIR.exists(),

        "is_directory":
            STORAGE_DIR.is_dir(),

        "storage":
            get_storage_stats(),

    }


# ============================================================
# DOWNLOAD FILE
# ============================================================

@app.get("/download")
def download_file(

    path: str,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_user
    ),

):

    if not member_permission_allowed(
        db,
        current_user,
        "allow_member_downloads",
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "Downloads are disabled "
                "for Member accounts"
            ),
        )


    file_path = (
        resolve_storage_path(
            path
        )
    )


    if (
        not file_path.exists()
        or
        not file_path.is_file()
    ):

        raise HTTPException(
            status_code=404,
            detail="File not found",
        )
    record_activity(
    db,
    current_user,
    action="download",
    target_name=file_path.name,
    details=f"Downloaded {file_path.name}",
)
    record_activity(
    db,
    current_user,
    action="preview",
    target_name=file_path.name,
    details=f"Previewed {file_path.name}",
)


    return FileResponse(

        path=file_path,

        filename=
            file_path.name,

        media_type=
            "application/octet-stream",

    )


# ============================================================
# PREVIEW FILE
# ============================================================

@app.get("/preview")
def preview_file(

    path: str,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_user
    ),

):

    if not member_permission_allowed(
        db,
        current_user,
        "allow_member_previews",
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "File previews are disabled "
                "for Member accounts"
            ),
        )


    file_path = (
        resolve_storage_path(
            path
        )
    )


    if (
        not file_path.exists()
        or
        not file_path.is_file()
    ):

        raise HTTPException(
            status_code=404,
            detail="File not found",
        )


    media_type, _ = (
        mimetypes.guess_type(
            file_path.name
        )
    )


    if not media_type:

        media_type = (
            "application/octet-stream"
        )


    return FileResponse(

        path=file_path,

        filename=
            file_path.name,

        media_type=
            media_type,

        content_disposition_type=
            "inline",

    )


# ============================================================
# FILE UPLOAD
# ============================================================

@app.post("/upload")
async def upload_files(

    request: Request,

    file: list[UploadFile] = File(
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
    # CSRF VALIDATION
    # ========================================================

    validate_csrf_token(
        request,
        csrf_token,
    )

    
    # ========================================================
    # MEMBER UPLOAD PERMISSION
    # ========================================================

    if not member_permission_allowed(
        db,
        current_user,
        "allow_member_uploads",
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "Uploads are disabled "
                "for Member accounts"
            ),
        )


    # ========================================================
    # SETTINGS
    # ========================================================

    multiple_uploads = (
        get_bool_setting(
            db,
            "multiple_uploads",
        )
    )


    if (
        not multiple_uploads
        and
        len(file) > 1
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Multiple file uploads "
                "are disabled"
            ),
        )


    max_upload_mb = (
        get_int_setting(
            db,
            "max_upload_mb",
        )
    )


    max_upload_bytes = (
        max_upload_mb
        *
        1024
        *
        1024
    )


    duplicate_behavior = (
        get_setting(
            db,
            "duplicate_behavior",
        )
    )


    storage_root = (
        STORAGE_DIR.resolve()
    )


    created_destinations: list[
        Path
    ] = []


    try:

        for uploaded_file in file:

            destination = None


            try:

                # ============================================
                # VALIDATE FILE
                # ============================================

                safe_name = (
                    validate_filename(
                        uploaded_file.filename
                    )
                )


                category = (
                    get_category(
                        safe_name
                    )
                )


                target_directory = (

                    storage_root
                    /
                    category

                ).resolve()


                target_directory.mkdir(
                    parents=True,
                    exist_ok=True,
                )


                try:

                    target_directory.relative_to(
                        storage_root
                    )

                except ValueError:

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Invalid upload directory"
                        ),
                    )


                # ============================================
                # DUPLICATE BEHAVIOR
                # ============================================

                if (
                    duplicate_behavior
                    ==
                    "reject"
                ):

                    destination = (

                        target_directory
                        /
                        safe_name

                    ).resolve()


                    if destination.exists():

                        raise HTTPException(
                            status_code=409,
                            detail=(
                                f"A file named "
                                f"'{safe_name}' "
                                f"already exists"
                            ),
                        )


                else:

                    destination = (
                        get_unique_destination(
                            target_directory,
                            safe_name,
                        )
                    ).resolve()


                if (
                    destination.parent
                    !=
                    target_directory
                ):

                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Invalid upload path"
                        ),
                    )


                # ============================================
                # STREAM FILE TO DISK
                # ============================================

                try:

                    with destination.open(
                        "xb"
                    ) as output:

                        created_destinations.append(
                            destination
                        )


                        bytes_written = 0


                        while True:

                            chunk = (
                                await uploaded_file.read(
                                    1024
                                    *
                                    1024
                                )
                            )


                            if not chunk:

                                break


                            bytes_written += (
                                len(
                                    chunk
                                )
                            )


                            if (
                                bytes_written
                                >
                                max_upload_bytes
                            ):

                                raise HTTPException(

                                    status_code=413,

                                    detail=(
                                        f"'{safe_name}' "
                                        f"exceeds the "
                                        f"{max_upload_mb} MB "
                                        f"upload limit"
                                    ),

                                )


                            output.write(
                                chunk
                            )


                except FileExistsError:

                    raise HTTPException(
                        status_code=409,
                        detail=(
                            "A file with that name "
                            "was created during upload. "
                            "Please try again."
                        ),
                    )


                # ============================================
                # DATABASE RECORD
                # ============================================

                relative_path = (

                    destination
                    .relative_to(
                        storage_root
                    )
                    .as_posix()

                )


                file_record = FileRecord(

                    stored_path=
                        relative_path,

                    original_name=
                        safe_name,

                    category=
                        category,

                    size_bytes=
                        bytes_written,

                    uploaded_by_id=
                        current_user.id,

                    is_trashed=
                        False,

                )


                db.add(
                    file_record
                )


            finally:

                await uploaded_file.close()


        # ====================================================
        # COMMIT WHOLE UPLOAD BATCH
        # ====================================================

                db.commit()

        for destination in created_destinations:

            record_activity(
                db,
                current_user,
                action="upload",
                target_name=destination.name,
                details=f"Uploaded {destination.name}",
            )


    except Exception:

        db.rollback()


        for destination in (
            created_destinations
        ):

            try:

                destination.unlink(
                    missing_ok=True
                )

            except OSError:

                pass


        raise


    return RedirectResponse(
        url="/",
        status_code=303,
    )


# ============================================================
# MOVE FILE TO TRASH
# ============================================================

@app.post("/trash")
def move_to_trash(

    request: Request,

    path: str = Form(
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
    # CSRF VALIDATION
    # ========================================================

    validate_csrf_token(
        request,
        csrf_token,
    )


    # ========================================================
    # GLOBAL TRASH SETTING
    # ========================================================

    if not get_bool_setting(
        db,
        "trash_enabled",
    ):

        raise HTTPException(
            status_code=403,
            detail="Trash is disabled",
        )


    # ========================================================
    # MEMBER TRASH PERMISSION
    # ========================================================

    user_is_admin = is_admin(
        current_user
    )


    if (
        not user_is_admin
        and
        not get_bool_setting(
            db,
            "allow_member_trash_own",
        )
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "Members are not allowed "
                "to Trash files"
            ),
        )


    file_path = (
        resolve_storage_path(
            path
        )
    )


    if (
        not file_path.exists()
        or
        not file_path.is_file()
    ):

        raise HTTPException(
            status_code=404,
            detail="File not found",
        )


    # ========================================================
    # FILE RECORD
    # ========================================================

    file_record = db.scalar(

        select(
            FileRecord
        )

        .where(
            FileRecord.stored_path
            ==
            path
        )

    )


    # ========================================================
    # OWNERSHIP
    # ========================================================

    if not user_is_admin:

        if (
            file_record
            is None
        ):

            raise HTTPException(
                status_code=403,
                detail=(
                    "You cannot Trash "
                    "an untracked file"
                ),
            )


        if (
            file_record.uploaded_by_id
            !=
            current_user.id
        ):

            raise HTTPException(
                status_code=403,
                detail=(
                    "You can only Trash "
                    "files you uploaded"
                ),
            )


    storage_root = (
        STORAGE_DIR.resolve()
    )


    relative_path = (
        file_path.relative_to(
            storage_root
        )
    )


    original_parent = (
        relative_path.parent
    )


    trash_target_directory = (

        TRASH_DIR
        /
        original_parent

    ).resolve()


    trash_target_directory.mkdir(
        parents=True,
        exist_ok=True,
    )


    trash_root = (
        TRASH_DIR.resolve()
    )


    try:

        trash_target_directory.relative_to(
            trash_root
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Invalid Trash path",
        )


    destination = (
        get_unique_destination(
            trash_target_directory,
            file_path.name,
        )
    )


    # ========================================================
    # SAVE ORIGINAL METADATA
    # ========================================================

    original_size = (
        file_path.stat()
        .st_size
    )


    original_category = (

        relative_path.parts[
            0
        ]

        if len(
            relative_path.parts
        ) > 1

        else get_category(
            file_path.name
        )

    )


    # ========================================================
    # PHYSICAL MOVE
    # ========================================================

    shutil.move(
        str(
            file_path
        ),
        str(
            destination
        ),
    )


    try:

        trash_relative_path = (

            destination
            .relative_to(
                storage_root
            )
            .as_posix()

        )


        # ====================================================
        # UPDATE EXISTING RECORD
        # ====================================================

        if (
            file_record
            is not None
        ):

            file_record.stored_path = (
                trash_relative_path
            )

            file_record.is_trashed = (
                True
            )

            file_record.trashed_at = (
                datetime.now(
                    timezone.utc
                )
            )


        # ====================================================
        # ADMIN TRASHING UNTRACKED FILE
        # ====================================================

        else:

            file_record = FileRecord(

                stored_path=
                    trash_relative_path,

                original_name=
                    file_path.name,

                category=
                    original_category,

                size_bytes=
                    original_size,

                uploaded_by_id=
                    None,

                is_trashed=
                    True,

                trashed_at=
                    datetime.now(
                        timezone.utc
                    ),

            )


            db.add(
                file_record
            )


        db.commit()
        record_activity(
    db,
    current_user,
    action="trash",
    target_name=file_path.name,
    details=f"Moved {file_path.name} to Trash",
)



    except Exception:

        db.rollback()


        # Try to put physical file back if DB update fails.

        try:

            if (
                destination.exists()
                and
                not file_path.exists()
            ):

                file_path.parent.mkdir(
                    parents=True,
                    exist_ok=True,
                )


                shutil.move(
                    str(
                        destination
                    ),
                    str(
                        file_path
                    ),
                )


        except OSError:

            pass


        raise


    return {

        "success":
            True,

        "message":
            "File moved to Trash",

        "filename":
            file_path.name,

    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {

        "status":
            "ok",

        "app":
            APP_NAME,

    }