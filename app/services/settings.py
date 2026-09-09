from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AppSetting


# ============================================================
# DEFAULT SETTINGS
# ============================================================
#
# Everything is stored as text in SQLite.
#
# The helpers below convert values back into:
#
# bool
# int
# str
#
# when the application needs them.
# ============================================================

DEFAULT_SETTINGS = {

    # --------------------------------------------------------
    # GENERAL
    # --------------------------------------------------------

    "cloud_name":
        "Vanta Cloud",

    "tagline":
        "Your files. Your space. Completely private.",


    # --------------------------------------------------------
    # APPEARANCE
    # --------------------------------------------------------

    # system / dark / light

    "theme":
        "system",


    # --------------------------------------------------------
    # MEMBER PERMISSIONS
    # --------------------------------------------------------

    "allow_member_uploads":
        "true",

    "allow_member_downloads":
        "true",

    "allow_member_previews":
        "true",

    "allow_member_trash_own":
        "true",

    "allow_member_rename_own":
        "false",


    # --------------------------------------------------------
    # UPLOAD SETTINGS
    # --------------------------------------------------------

    # Maximum size of ONE uploaded file.

    "max_upload_mb":
        "2048",


    # Allow selecting several files in one upload.

    "multiple_uploads":
        "true",


    # rename / reject

    "duplicate_behavior":
        "rename",


    # all for now.
    #
    # Later this could become:
    #
    # images
    # documents
    # media
    # custom

    "allowed_file_types":
        "all",


    # --------------------------------------------------------
    # TRASH SETTINGS
    # --------------------------------------------------------

    "trash_enabled":
        "true",


    # 0 = Never auto-delete.
    #
    # Later we can support:
    #
    # 7
    # 30
    # 90
    #
    # Actual automatic cleanup will be wired later.

    "trash_retention_days":
        "0",


    # --------------------------------------------------------
    # FILE CARD DISPLAY
    # --------------------------------------------------------

    "show_uploader":
        "true",

    "show_upload_time":
        "true",


    # --------------------------------------------------------
    # INTERFACE
    # --------------------------------------------------------

    # recent / Photos / Videos / Music / Documents

    "default_view":
        "recent",

}


# ============================================================
# VALID OPTIONS
# ============================================================

BOOLEAN_SETTINGS = {

    "allow_member_uploads",
    "allow_member_downloads",
    "allow_member_previews",
    "allow_member_trash_own",
    "allow_member_rename_own",
    "multiple_uploads",
    "trash_enabled",
    "show_uploader",
    "show_upload_time",

}


CHOICE_SETTINGS = {

    "theme": {
        "system",
        "dark",
        "light",
    },

    "duplicate_behavior": {
        "rename",
        "reject",
    },

    "allowed_file_types": {
        "all",
    },

    "default_view": {
        "recent",
        "Photos",
        "Videos",
        "Music",
        "Documents",
    },

}


INTEGER_SETTINGS = {

    "max_upload_mb": {
        "minimum": 1,
        "maximum": 10240,
    },

    "trash_retention_days": {
        "minimum": 0,
        "maximum": 365,
    },

}


TEXT_SETTINGS = {

    "cloud_name": {
        "minimum": 1,
        "maximum": 60,
    },

    "tagline": {
        "minimum": 1,
        "maximum": 140,
    },

}


# ============================================================
# BOOLEAN NORMALIZATION
# ============================================================

def normalize_boolean(
    value,
) -> str:

    if isinstance(
        value,
        bool,
    ):

        return (
            "true"
            if value
            else "false"
        )


    normalized = (
        str(value)
        .strip()
        .lower()
    )


    if normalized in {
        "true",
        "1",
        "yes",
        "on",
    }:

        return "true"


    if normalized in {
        "false",
        "0",
        "no",
        "off",
    }:

        return "false"


    raise ValueError(
        "Invalid boolean value"
    )


# ============================================================
# VALIDATE SETTING
# ============================================================

def validate_setting(
    key: str,
    value,
) -> str:

    if key not in DEFAULT_SETTINGS:

        raise ValueError(
            f"Unknown setting: {key}"
        )


    # --------------------------------------------------------
    # BOOLEAN
    # --------------------------------------------------------

    if key in BOOLEAN_SETTINGS:

        return normalize_boolean(
            value
        )


    # --------------------------------------------------------
    # CHOICE
    # --------------------------------------------------------

    if key in CHOICE_SETTINGS:

        normalized = (
            str(value)
            .strip()
        )


        if normalized not in CHOICE_SETTINGS[key]:

            raise ValueError(
                f"Invalid value for setting: {key}"
            )


        return normalized


    # --------------------------------------------------------
    # INTEGER
    # --------------------------------------------------------

    if key in INTEGER_SETTINGS:

        try:

            number = int(
                value
            )

        except (
            TypeError,
            ValueError,
        ):

            raise ValueError(
                f"{key} must be a number"
            )


        rules = (
            INTEGER_SETTINGS[key]
        )


        if number < rules["minimum"]:

            raise ValueError(
                f"{key} is below the minimum value"
            )


        if number > rules["maximum"]:

            raise ValueError(
                f"{key} exceeds the maximum value"
            )


        return str(
            number
        )


    # --------------------------------------------------------
    # TEXT
    # --------------------------------------------------------

    if key in TEXT_SETTINGS:

        normalized = (
            str(value)
            .strip()
        )


        rules = (
            TEXT_SETTINGS[key]
        )


        if (
            len(normalized)
            <
            rules["minimum"]
        ):

            raise ValueError(
                f"{key} is too short"
            )


        if (
            len(normalized)
            >
            rules["maximum"]
        ):

            raise ValueError(
                f"{key} is too long"
            )


        return normalized


    raise ValueError(
        f"No validation rule exists for: {key}"
    )


# ============================================================
# CREATE DEFAULT SETTINGS
# ============================================================

def ensure_default_settings(
    db: Session,
) -> None:

    existing_keys = set(

        db.scalars(

            select(
                AppSetting.key
            )

        ).all()

    )


    created_any = False


    for key, value in DEFAULT_SETTINGS.items():

        if key in existing_keys:

            continue


        db.add(

            AppSetting(
                key=key,
                value=value,
            )

        )


        created_any = True


    if created_any:

        db.commit()


# ============================================================
# GET RAW SETTING
# ============================================================

def get_setting(
    db: Session,
    key: str,
) -> str:

    if key not in DEFAULT_SETTINGS:

        raise KeyError(
            f"Unknown setting: {key}"
        )


    setting = db.get(
        AppSetting,
        key,
    )


    if setting is None:

        default_value = (
            DEFAULT_SETTINGS[key]
        )


        setting = AppSetting(
            key=key,
            value=default_value,
        )


        db.add(
            setting
        )


        db.commit()


        return default_value


    return setting.value


# ============================================================
# GET BOOLEAN SETTING
# ============================================================

def get_bool_setting(
    db: Session,
    key: str,
) -> bool:

    value = get_setting(
        db,
        key,
    )


    return (
        value.lower()
        ==
        "true"
    )


# ============================================================
# GET INTEGER SETTING
# ============================================================

def get_int_setting(
    db: Session,
    key: str,
) -> int:

    value = get_setting(
        db,
        key,
    )


    return int(
        value
    )


# ============================================================
# SET SETTING
# ============================================================

def set_setting(
    db: Session,
    key: str,
    value,
) -> None:

    normalized_value = (
        validate_setting(
            key,
            value,
        )
    )


    setting = db.get(
        AppSetting,
        key,
    )


    if setting is None:

        setting = AppSetting(
            key=key,
            value=normalized_value,
        )


        db.add(
            setting
        )


    else:

        setting.value = (
            normalized_value
        )


# ============================================================
# GET ALL SETTINGS
# ============================================================

def get_all_settings(
    db: Session,
) -> dict[str, str]:

    ensure_default_settings(
        db
    )


    rows = db.scalars(

        select(
            AppSetting
        )

    ).all()


    settings = {

        row.key:
            row.value

        for row in rows

    }


    # Guarantee defaults even if the database
    # somehow contains an incomplete settings set.

    for key, value in DEFAULT_SETTINGS.items():

        settings.setdefault(
            key,
            value,
        )


    return settings


# ============================================================
# CONVERT SETTINGS FOR TEMPLATES
# ============================================================

def get_template_settings(
    db: Session,
) -> dict:

    raw = get_all_settings(
        db
    )


    result = {}


    for key, value in raw.items():

        if key in BOOLEAN_SETTINGS:

            result[key] = (
                value.lower()
                ==
                "true"
            )


        elif key in INTEGER_SETTINGS:

            try:

                result[key] = int(
                    value
                )

            except ValueError:

                result[key] = int(
                    DEFAULT_SETTINGS[key]
                )


        else:

            result[key] = value


    return result