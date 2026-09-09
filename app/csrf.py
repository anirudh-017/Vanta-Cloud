import secrets

from fastapi import (
    HTTPException,
    Request,
)


# ============================================================
# CSRF CONSTANTS
# ============================================================

CSRF_SESSION_KEY = "_csrf_token"


# ============================================================
# CREATE / GET CSRF TOKEN
# ============================================================

def get_csrf_token(
    request: Request,
) -> str:

    """
    Return the CSRF token stored in the user's signed session.

    If the session does not have one yet, create a fresh
    cryptographically secure token.

    The token is allowed to appear inside HTML forms.
    Its security comes from an attacker not being able to read
    the user's Vanta page/session from another website.
    """

    token = request.session.get(
        CSRF_SESSION_KEY
    )


    if (
        not isinstance(token, str)
        or
        len(token) < 32
    ):

        token = secrets.token_urlsafe(
            32
        )


        request.session[
            CSRF_SESSION_KEY
        ] = token


    return token


# ============================================================
# VALIDATE CSRF TOKEN
# ============================================================

def validate_csrf_token(
    request: Request,
    submitted_token: str | None,
) -> None:

    """
    Compare a submitted token with the token stored in the
    signed session.

    Missing or incorrect tokens are rejected with HTTP 403.
    """

    expected_token = (
        request.session.get(
            CSRF_SESSION_KEY
        )
    )


    if (
        not isinstance(
            expected_token,
            str,
        )
        or
        not isinstance(
            submitted_token,
            str,
        )
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "Invalid or missing "
                "CSRF token"
            ),
        )


    if not secrets.compare_digest(
        expected_token,
        submitted_token,
    ):

        raise HTTPException(
            status_code=403,
            detail=(
                "Invalid or missing "
                "CSRF token"
            ),
        )


# ============================================================
# ROTATE CSRF TOKEN
# ============================================================

def rotate_csrf_token(
    request: Request,
) -> str:

    """
    Replace the current CSRF token with a fresh one.

    We will use this after successful authentication so an old
    pre-login token is not carried forward unnecessarily.
    """

    token = secrets.token_urlsafe(
        32
    )


    request.session[
        CSRF_SESSION_KEY
    ] = token


    return token