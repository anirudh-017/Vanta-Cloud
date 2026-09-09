from pathlib import Path
import secrets


# ============================================================
# PROJECT PATHS
# ============================================================

BASE_DIR = Path(
    __file__
).resolve().parent.parent


DATA_DIR = (
    BASE_DIR / "data"
)


DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# SESSION SECRET
# ============================================================
#
# Vanta Cloud needs a secret key to cryptographically sign
# login session cookies.
#
# We generate it once and keep it locally inside data/.
#
# IMPORTANT:
# data/ will later be excluded from Git so this secret
# never gets published on GitHub.
# ============================================================

SESSION_SECRET_FILE = (
    DATA_DIR / "session_secret.txt"
)


def get_session_secret() -> str:

    if SESSION_SECRET_FILE.exists():

        return (
            SESSION_SECRET_FILE
            .read_text(
                encoding="utf-8"
            )
            .strip()
        )


    secret = secrets.token_urlsafe(
        64
    )


    SESSION_SECRET_FILE.write_text(
        secret,
        encoding="utf-8",
    )


    return secret


SESSION_SECRET = (
    get_session_secret()
)