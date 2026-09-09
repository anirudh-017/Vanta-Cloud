from fastapi import (
    Depends,
    HTTPException,
    Request,
    status,
)

from pwdlib import PasswordHash

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import get_db
from .models import User, UserRole


# ============================================================
# PASSWORD HASHER
# ============================================================

password_hash = PasswordHash.recommended()


# ============================================================
# HASH PASSWORD
# ============================================================

def hash_password(
    password: str,
) -> str:

    return password_hash.hash(
        password
    )


# ============================================================
# VERIFY PASSWORD
# ============================================================

def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:

    try:

        return password_hash.verify(
            plain_password,
            hashed_password,
        )

    except Exception:

        return False


# ============================================================
# AUTHENTICATE USER
# ============================================================
#
# Used during login.
#
# username + password
#        ↓
# find user in SQLite
#        ↓
# verify Argon2 password
#        ↓
# return User OR None
# ============================================================

def authenticate_user(
    db: Session,
    username: str,
    password: str,
) -> User | None:

    username = (
        username
        .strip()
        .lower()
    )


    user = db.scalar(

        select(User)
        .where(
            User.username == username
        )

    )


    if user is None:

        return None


    if not user.is_active:

        return None


    if not verify_password(
        password,
        user.password_hash,
    ):

        return None


    return user


# ============================================================
# LOGIN USER
# ============================================================
#
# We store ONLY the database user ID.
#
# We do NOT store:
#
# password
# password hash
# admin role
#
# Role is always loaded fresh from SQLite.
# ============================================================

def login_user(
    request: Request,
    user: User,
) -> None:

    # Clear any previous session first.

    request.session.clear()


    request.session[
        "user_id"
    ] = user.id


# ============================================================
# LOGOUT USER
# ============================================================

def logout_user(
    request: Request,
) -> None:

    request.session.clear()


# ============================================================
# GET CURRENT USER
# ============================================================
#
# Returns:
#
# User
#
# or:
#
# None
#
# if nobody is logged in.
# ============================================================

def get_current_user(

    request: Request,

    db: Session = Depends(
        get_db
    ),

) -> User | None:

    user_id = (
        request.session.get(
            "user_id"
        )
    )


    if user_id is None:

        return None


    # Reject strange/tampered session values.

    if not isinstance(
        user_id,
        int,
    ):

        request.session.clear()

        return None


    user = db.get(
        User,
        user_id,
    )


    if user is None:

        request.session.clear()

        return None


    if not user.is_active:

        request.session.clear()

        return None


    return user


# ============================================================
# REQUIRE LOGIN
# ============================================================
#
# Useful for protected API routes.
#
# If nobody is logged in:
#
# HTTP 401 Unauthorized
# ============================================================

def require_user(

    current_user: User | None = Depends(
        get_current_user
    ),

) -> User:

    if current_user is None:

        raise HTTPException(

            status_code=status.HTTP_401_UNAUTHORIZED,

            detail="Authentication required",

        )


    return current_user


# ============================================================
# REQUIRE ADMIN
# ============================================================
#
# This is REAL backend authorization.
#
# Hiding an Admin button in HTML is not security.
# This dependency checks the user's role in SQLite.
# ============================================================

def require_admin(

    current_user: User = Depends(
        require_user
    ),

) -> User:

    if (
        current_user.role
        !=
        UserRole.ADMIN.value
    ):

        raise HTTPException(

            status_code=status.HTTP_403_FORBIDDEN,

            detail="Administrator permission required",

        )


    return current_user


# ============================================================
# ROLE HELPER
# ============================================================

def is_admin(
    user: User,
) -> bool:

    return (
        user.role
        ==
        UserRole.ADMIN.value
    )