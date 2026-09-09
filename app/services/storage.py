import os
from pathlib import Path
import mimetypes
import shutil

from fastapi import HTTPException


# ============================================================
# STORAGE CONFIGURATION
# ============================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parents[2]
)

DEFAULT_STORAGE_DIR = (
    BASE_DIR / "storage"
)

STORAGE_DIR = Path(
    os.getenv(
        "VANTA_STORAGE_DIR",
        str(DEFAULT_STORAGE_DIR),
    )
).expanduser().resolve()

TRASH_DIR = (
    STORAGE_DIR / ".Trash"
)


# ============================================================
# FILE CATEGORIES
# ============================================================

FILE_CATEGORIES = {

    "Photos": {
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".webp",
        ".bmp",
        ".heic",
    },

    "Videos": {
        ".mp4",
        ".mkv",
        ".mov",
        ".avi",
        ".webm",
        ".m4v",
    },

    "Music": {
        ".mp3",
        ".wav",
        ".flac",
        ".aac",
        ".m4a",
        ".ogg",
    },

    "Documents": {
        ".pdf",
        ".txt",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".csv",
    },

}


MAIN_CATEGORIES = {
    "Photos",
    "Videos",
    "Music",
    "Documents",
    "Other",
}


# ============================================================
# INITIALIZE STORAGE
# ============================================================

def initialize_storage() -> None:

    STORAGE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    TRASH_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )


    for category in MAIN_CATEGORIES:

        (
            STORAGE_DIR / category
        ).mkdir(
            parents=True,
            exist_ok=True,
        )


# ============================================================
# CATEGORY DETECTION
# ============================================================

def get_category(
    filename: str,
) -> str:

    extension = (
        Path(filename)
        .suffix
        .lower()
    )


    for category, extensions in FILE_CATEGORIES.items():

        if extension in extensions:

            return category


    return "Other"


# ============================================================
# FORMAT BYTES
# ============================================================

def format_bytes(
    size: int,
) -> str:

    units = [
        "B",
        "KB",
        "MB",
        "GB",
        "TB",
    ]


    value = float(size)


    for unit in units:

        if (
            value < 1024
            or
            unit == "TB"
        ):

            if unit == "B":

                return f"{int(value)} B"


            return f"{value:.1f} {unit}"


        value /= 1024


    return f"{size} B"


# ============================================================
# SAFE FILENAME VALIDATION
# ============================================================

def validate_filename(
    filename: str | None,
) -> str:

    if not filename:

        raise HTTPException(
            status_code=400,
            detail="No filename provided",
        )


    safe_name = Path(
        filename
    ).name


    if safe_name != filename:

        raise HTTPException(
            status_code=400,
            detail="Invalid filename",
        )


    if safe_name in {
        ".",
        "..",
    }:

        raise HTTPException(
            status_code=400,
            detail="Invalid filename",
        )


    forbidden_characters = (
        '<>:"/\\|?*'
    )


    if any(
        character in safe_name
        for character in forbidden_characters
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid filename",
        )


    if (
        safe_name.rstrip(" .")
        != safe_name
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid filename",
        )


    reserved_names = {

        "CON",
        "PRN",
        "AUX",
        "NUL",

        "COM1",
        "COM2",
        "COM3",
        "COM4",
        "COM5",
        "COM6",
        "COM7",
        "COM8",
        "COM9",

        "LPT1",
        "LPT2",
        "LPT3",
        "LPT4",
        "LPT5",
        "LPT6",
        "LPT7",
        "LPT8",
        "LPT9",

    }


    if (
        Path(safe_name)
        .stem
        .upper()
        in reserved_names
    ):

        raise HTTPException(
            status_code=400,
            detail="Reserved filename",
        )


    if len(safe_name) > 240:

        raise HTTPException(
            status_code=400,
            detail="Filename is too long",
        )


    return safe_name


# ============================================================
# UNIQUE DESTINATION
# ============================================================

def get_unique_destination(
    directory: Path,
    filename: str,
) -> Path:

    original = Path(
        filename
    )


    stem = (
        original.stem
    )


    suffix = (
        original.suffix
    )


    destination = (
        directory / filename
    )


    counter = 1


    while destination.exists():

        destination = (

            directory
            /
            f"{stem} ({counter}){suffix}"

        )


        counter += 1


    return destination


# ============================================================
# NORMAL STORAGE PATH
# ============================================================

def resolve_storage_path(
    relative_path: str,
) -> Path:

    storage_root = (
        STORAGE_DIR.resolve()
    )


    candidate = (

        storage_root
        /
        relative_path

    ).resolve()


    try:

        candidate.relative_to(
            storage_root
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Invalid file path",
        )


    trash_root = (
        TRASH_DIR.resolve()
    )


    try:

        candidate.relative_to(
            trash_root
        )

    except ValueError:

        pass

    else:

        raise HTTPException(
            status_code=400,
            detail="Trash files require a Trash route",
        )


    return candidate


# ============================================================
# TRASH PATH
# ============================================================

def resolve_trash_path(
    relative_path: str,
) -> Path:

    trash_root = (
        TRASH_DIR.resolve()
    )


    candidate = (

        STORAGE_DIR
        /
        relative_path

    ).resolve()


    try:

        candidate.relative_to(
            trash_root
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Invalid Trash path",
        )


    return candidate


# ============================================================
# MOVE TO TRASH
# ============================================================

def move_file_to_trash(
    file_path: Path,
) -> Path:

    storage_root = (
        STORAGE_DIR.resolve()
    )


    relative_path = (
        file_path
        .relative_to(
            storage_root
        )
    )


    destination_directory = (

        TRASH_DIR
        /
        relative_path.parent

    ).resolve()


    trash_root = (
        TRASH_DIR.resolve()
    )


    try:

        destination_directory.relative_to(
            trash_root
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Invalid Trash destination",
        )


    destination_directory.mkdir(
        parents=True,
        exist_ok=True,
    )


    destination = (
        get_unique_destination(
            destination_directory,
            file_path.name,
        )
    )


    shutil.move(
        str(file_path),
        str(destination),
    )


    return destination


# ============================================================
# RESTORE FROM TRASH
# ============================================================

def restore_file(
    trash_path: Path,
    category: str,
    preferred_name: str,
) -> Path:

    if category not in MAIN_CATEGORIES:

        category = (
            get_category(
                preferred_name
            )
        )


    destination_directory = (

        STORAGE_DIR
        /
        category

    ).resolve()


    storage_root = (
        STORAGE_DIR.resolve()
    )


    try:

        destination_directory.relative_to(
            storage_root
        )

    except ValueError:

        raise HTTPException(
            status_code=400,
            detail="Invalid restore destination",
        )


    destination_directory.mkdir(
        parents=True,
        exist_ok=True,
    )


    safe_name = (
        validate_filename(
            preferred_name
        )
    )


    destination = (
        get_unique_destination(
            destination_directory,
            safe_name,
        )
    )


    shutil.move(
        str(trash_path),
        str(destination),
    )


    return destination


# ============================================================
# RENAME FILE
# ============================================================

def rename_file(
    file_path: Path,
    new_filename: str,
) -> Path:

    safe_name = (
        validate_filename(
            new_filename
        )
    )


    destination = (
        file_path.parent
        /
        safe_name
    ).resolve()


    if (
        destination.parent
        != file_path.parent.resolve()
    ):

        raise HTTPException(
            status_code=400,
            detail="Invalid rename destination",
        )


    if (
        destination.exists()
        and
        destination != file_path
    ):

        raise HTTPException(
            status_code=409,
            detail="A file with that name already exists",
        )


    file_path.rename(
        destination
    )


    return destination


# ============================================================
# PERMANENT DELETE
# ============================================================

def permanently_delete(
    file_path: Path,
) -> None:

    if (
        not file_path.exists()
        or
        not file_path.is_file()
    ):

        raise HTTPException(
            status_code=404,
            detail="File not found",
        )


    file_path.unlink()


# ============================================================
# MIME TYPE
# ============================================================

def get_media_type(
    filename: str,
) -> str:

    media_type, _ = (
        mimetypes.guess_type(
            filename
        )
    )


    return (
        media_type
        or
        "application/octet-stream"
    )


# ============================================================
# STORAGE STATS
# ============================================================

def get_storage_stats():

    active_used = 0
    trash_used = 0


    for item in STORAGE_DIR.rglob("*"):

        if not item.is_file():

            continue


        try:

            relative_path = (
                item.relative_to(
                    STORAGE_DIR
                )
            )


            size = (
                item.stat().st_size
            )

        except (
            ValueError,
            OSError,
        ):

            continue


        if ".Trash" in relative_path.parts:

            trash_used += size

        else:

            active_used += size


    drive = shutil.disk_usage(
        STORAGE_DIR
    )


    drive_percent = (

        round(
            drive.used
            /
            drive.total
            *
            100,
            1,
        )

        if drive.total

        else 0

    )


    return {

        "vanta_used":
            active_used,

        "vanta_used_text":
            format_bytes(
                active_used
            ),

        "trash_used":
            trash_used,

        "trash_used_text":
            format_bytes(
                trash_used
            ),

        "drive_total":
            drive.total,

        "drive_total_text":
            format_bytes(
                drive.total
            ),

        "drive_used":
            drive.used,

        "drive_used_text":
            format_bytes(
                drive.used
            ),

        "drive_free":
            drive.free,

        "drive_free_text":
            format_bytes(
                drive.free
            ),

        "drive_percent":
            drive_percent,

    }