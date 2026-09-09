from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    Form,
    Request,
)

from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from sqlalchemy import (
    func,
    select,
)

from sqlalchemy.exc import (
    IntegrityError,
    SQLAlchemyError,
)

from sqlalchemy.orm import Session

from ..auth import (
    hash_password,
    require_admin,
)

from ..csrf import (
    get_csrf_token,
    validate_csrf_token,
)

from ..database import get_db

from ..models import (
    ActivityLog,
    User,
    UserRole,
)
from ..services.activity import record_activity


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
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
            "Username must be between 3 and 30 characters."
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
            "Username contains invalid characters."
        )


    return username


# ============================================================
# DISPLAY NAME VALIDATION
# ============================================================

def validate_display_name(
    display_name: str,
) -> str:

    display_name = (
        display_name.strip()
    )


    if not display_name:

        raise ValueError(
            "Display name is required."
        )


    if len(display_name) > 100:

        raise ValueError(
            "Display name is too long."
        )


    return display_name


# ============================================================
# PASSWORD VALIDATION
# ============================================================

def validate_password(
    password: str,
) -> str:

    # Do NOT strip passwords.
    #
    # Leading/trailing spaces may intentionally be part
    # of a password.

    if len(password) < 10:

        raise ValueError(
            "Password must contain at least 10 characters."
        )


    # Prevent absurdly large inputs from wasting CPU during
    # password hashing.

    if len(password) > 256:

        raise ValueError(
            "Password is too long."
        )


    return password


# ============================================================
# ROLE VALIDATION
# ============================================================

def validate_role(
    role: str,
) -> str:

    if role not in {

        UserRole.ADMIN.value,
        UserRole.MEMBER.value,

    }:

        raise ValueError(
            "Invalid account role."
        )


    return role


# ============================================================
# COUNT ACTIVE ADMINS
# ============================================================

def count_active_admins(
    db: Session,
) -> int:

    count = db.scalar(

        select(
            func.count(
                User.id
            )
        )

        .where(
            User.role
            ==
            UserRole.ADMIN.value
        )

        .where(
            User.is_active.is_(
                True
            )
        )

    )


    return int(
        count or 0
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@router.get("")
def admin_dashboard(

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_admin: User = Depends(
        require_admin
    ),

):

    users = db.scalars(

        select(User)

        .order_by(
            User.created_at.asc()
        )

    ).all()


    active_admin_count = (
        count_active_admins(
            db
        )
    )
    activity_logs = db.scalars(

    select(ActivityLog)

    .order_by(
        ActivityLog.created_at.desc()
    )

    .limit(100)

).all()
    


    return templates.TemplateResponse(

        request=request,

        name="admin.html",

        context={

            "users":
                users,

            "current_user":
                current_admin,

            "csrf_token":
                get_csrf_token(
                    request
                ),

            "active_admin_count":
                active_admin_count,

            "app_name":
                "Vanta Cloud",
                "activity_logs":
                    activity_logs,

            # These codes can be used by admin.html
            # when we clean up its status messages.

            "error":
                request.query_params.get(
                    "error"
                ),

            "created":
                (
                    request
                    .query_params
                    .get("created")
                    ==
                    "1"
                ),

            "activated":
                (
                    request
                    .query_params
                    .get("activated")
                    ==
                    "1"
                ),

            "deactivated":
                (
                    request
                    .query_params
                    .get("deactivated")
                    ==
                    "1"
                ),

            "role_changed":
                (
                    request
                    .query_params
                    .get("role_changed")
                    ==
                    "1"
                ),

        },

    )


# ============================================================
# CREATE USER
# ============================================================

@router.post(
    "/users"
)
def create_user(

    request: Request,

    display_name: str = Form(...),

    username: str = Form(...),

    password: str = Form(...),

    role: str = Form(
        UserRole.MEMBER.value
    ),

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
    # DISPLAY NAME
    # ========================================================

    try:

        display_name = (
            validate_display_name(
                display_name
            )
        )


    except ValueError:

        return RedirectResponse(

            url=(
                "/admin"
                "?error=invalid_name"
            ),

            status_code=303,

        )


    # ========================================================
    # USERNAME
    # ========================================================

    try:

        username = (
            validate_username(
                username
            )
        )


    except ValueError:

        return RedirectResponse(

            url=(
                "/admin"
                "?error=invalid_username"
            ),

            status_code=303,

        )


    # ========================================================
    # PASSWORD
    # ========================================================

    try:

        password = (
            validate_password(
                password
            )
        )


    except ValueError:

        return RedirectResponse(

            url=(
                "/admin"
                "?error=invalid_password"
            ),

            status_code=303,

        )


    # ========================================================
    # ROLE
    # ========================================================

    try:

        role = (
            validate_role(
                role
            )
        )


    except ValueError:

        return RedirectResponse(

            url=(
                "/admin"
                "?error=invalid_role"
            ),

            status_code=303,

        )


    # ========================================================
    # CHECK USERNAME BEFORE INSERT
    # ========================================================
    #
    # The database UNIQUE constraint remains the final defence.
    #
    # This early query simply gives us cleaner UX.
    # ========================================================

    existing_user_id = db.scalar(

        select(
            User.id
        )

        .where(
            User.username
            ==
            username
        )

    )


    if existing_user_id is not None:

        return RedirectResponse(

            url=(
                "/admin"
                "?error=username_exists"
            ),

            status_code=303,

        )


    # ========================================================
    # CREATE ACCOUNT
    # ========================================================

    new_user = User(

        username=
            username,

        display_name=
            display_name,

        password_hash=
            hash_password(
                password
            ),

        role=
            role,

        is_active=
            True,

    )


    db.add(
        new_user
    )


    try:

        db.commit()
        record_activity(
    db,
    current_admin,
    action="user_created",
    target_name=username,
    details=(
        f"Created {role} account "
        f"{username}"
    ),
)


    except IntegrityError:

        # Another request may have created the same username
        # between our check and commit.

        db.rollback()


        return RedirectResponse(

            url=(
                "/admin"
                "?error=username_exists"
            ),

            status_code=303,

        )


    except SQLAlchemyError:

        db.rollback()


        return RedirectResponse(

            url=(
                "/admin"
                "?error=database"
            ),

            status_code=303,

        )


    return RedirectResponse(

        url=(
            "/admin"
            "?created=1"
        ),

        status_code=303,

    )


# ============================================================
# ENABLE / DISABLE USER
# ============================================================

@router.post(
    "/users/{user_id}/toggle-active"
)
def toggle_user_active(

    user_id: int,

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
    # FIND USER
    # ========================================================

    user = db.get(
        User,
        user_id,
    )


    if user is None:

        return RedirectResponse(

            url=(
                "/admin"
                "?error=user_not_found"
            ),

            status_code=303,

        )


    # ========================================================
    # BLOCK SELF-DEACTIVATION
    # ========================================================

    if (
        user.id
        ==
        current_admin.id
    ):

        return RedirectResponse(

            url=(
                "/admin"
                "?error=self_disable"
            ),

            status_code=303,

        )


    # ========================================================
    # PROTECT LAST ACTIVE ADMIN
    # ========================================================
    #
    # Only relevant when:
    #
    # - target is currently active
    # - target is an Admin
    # - action would deactivate them
    #
    # If there is only one active Admin left, this operation
    # must not be allowed.
    # ========================================================

    if (
        user.is_active
        and
        user.role
        ==
        UserRole.ADMIN.value
    ):

        if (
            count_active_admins(
                db
            )
            <=
            1
        ):

            return RedirectResponse(

                url=(
                    "/admin"
                    "?error=last_admin"
                ),

                status_code=303,

            )


    # ========================================================
    # CHANGE STATE
    # ========================================================

    user.is_active = (
        not user.is_active
    )


    new_state = (
        user.is_active
    )


    try:

        db.commit()
        record_activity(
    db,
    current_admin,
    action=(
        "user_activated"
        if new_state
        else "user_deactivated"
    ),
    target_name=user.username,
    details=(
        f"{'Activated' if new_state else 'Deactivated'} "
        f"account {user.username}"
    ),
)


    except SQLAlchemyError:

        db.rollback()


        return RedirectResponse(

            url=(
                "/admin"
                "?error=database"
            ),

            status_code=303,

        )


    # ========================================================
    # SUCCESS
    # ========================================================

    if new_state:

        destination = (
            "/admin"
            "?activated=1"
        )

    else:

        destination = (
            "/admin"
            "?deactivated=1"
        )


    return RedirectResponse(

        url=
            destination,

        status_code=303,

    )


# ============================================================
# CHANGE ROLE
# ============================================================

@router.post(
    "/users/{user_id}/role"
)
def change_user_role(

    user_id: int,

    request: Request,

    role: str = Form(...),

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
    # VALIDATE REQUESTED ROLE FIRST
    # ========================================================

    try:

        role = (
            validate_role(
                role
            )
        )


    except ValueError:

        return RedirectResponse(

            url=(
                "/admin"
                "?error=invalid_role"
            ),

            status_code=303,

        )


    # ========================================================
    # FIND USER
    # ========================================================

    user = db.get(
        User,
        user_id,
    )


    if user is None:

        return RedirectResponse(

            url=(
                "/admin"
                "?error=user_not_found"
            ),

            status_code=303,

        )


    # ========================================================
    # NO CHANGE REQUIRED
    # ========================================================

    if (
        user.role
        ==
        role
    ):

        return RedirectResponse(

            url="/admin",

            status_code=303,

        )


    # ========================================================
    # BLOCK SELF-DEMOTION
    # ========================================================

    if (
        user.id
        ==
        current_admin.id
    ):

        return RedirectResponse(

            url=(
                "/admin"
                "?error=self_role"
            ),

            status_code=303,

        )


    # ========================================================
    # PROTECT LAST ACTIVE ADMIN
    # ========================================================
    #
    # An inactive Admin does not count toward the active Admin
    # safety requirement.
    #
    # An active Admin cannot be converted to Member if they
    # are the final active administrator.
    # ========================================================

    if (
        user.is_active
        and
        user.role
        ==
        UserRole.ADMIN.value
        and
        role
        !=
        UserRole.ADMIN.value
    ):

        if (
            count_active_admins(
                db
            )
            <=
            1
        ):

            return RedirectResponse(

                url=(
                    "/admin"
                    "?error=last_admin"
                ),

                status_code=303,

            )


    # ========================================================
    # CHANGE ROLE
    # ========================================================

    user.role = (
        role
    )


    try:

        db.commit()
        record_activity(
    db,
    current_admin,
    action="role_changed",
    target_name=user.username,
    details=(
        f"Changed account {user.username} "
        f"to role {role}"
    ),
)


    except SQLAlchemyError:

        db.rollback()


        return RedirectResponse(

            url=(
                "/admin"
                "?error=database"
            ),

            status_code=303,

        )


    return RedirectResponse(

        url=(
            "/admin"
            "?role_changed=1"
        ),

        status_code=303,

    )