from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models import (
    ActivityLog,
    User,
)


# ============================================================
# RECORD ACTIVITY
# ============================================================

def record_activity(
    db: Session,
    actor: User | None,
    action: str,
    target_name: str | None = None,
    details: str | None = None,
) -> None:

    """
    Best-effort activity logging.

    Call this only AFTER the main operation has succeeded.
    A logging failure must not undo the user's completed action.
    """

    entry = ActivityLog(

        actor_user_id=
            (
                actor.id
                if actor is not None
                else None
            ),

        actor_username=
            (
                actor.username
                if actor is not None
                else "system"
            ),

        action=
            action,

        target_name=
            target_name,

        details=
            details,

    )

    try:

        db.add(
            entry
        )

        db.commit()

    except SQLAlchemyError:

        db.rollback()