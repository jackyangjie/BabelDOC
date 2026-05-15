"""Discover CJK fonts available on the system for image text rendering."""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Known CJK font file names (TrueType/OpenType), ordered by preference.
_CJK_FONT_CANDIDATES = [
    "NotoSansCJK-Regular.ttc",
    "NotoSansSC-Regular.otf",
    "NotoSansCJKsc-Regular.otf",
    "wqy-zenhei.ttc",
    "wqy-microhei.ttc",
    "arphicuming.ttc",
    "AR PL UMing CN.ttf",
    "DroidSansFallbackFull.ttf",
]

# Common system font directories to search.
_FONT_DIRS = [
    "/usr/share/fonts",
    "/usr/local/share/fonts",
    str(Path("~/.fonts").expanduser()),
    str(Path("~/.local/share/fonts").expanduser()),
    "/System/Library/Fonts",
    "/Library/Fonts",
]


def find_cjk_font() -> str | None:
    """Return path to the first CJK-capable system font found, or None."""
    searched: list[str] = []

    for font_dir in _FONT_DIRS:
        d = Path(font_dir)
        if not d.is_dir():
            continue
        for candidate in _CJK_FONT_CANDIDATES:
            for found in d.rglob(candidate):
                logger.debug("Found CJK font: %s", found)
                return str(found)
        searched.append(font_dir)

    # Broader fallback: any .ttf/.ttc/.otf containing CJK keywords
    for font_dir in _FONT_DIRS:
        d = Path(font_dir)
        if not d.is_dir():
            continue
        for ext in ("*.ttf", "*.ttc", "*.otf"):
            for font_path in d.rglob(ext):
                name_lower = font_path.stem.lower()
                if any(
                    kw in name_lower
                    for kw in (
                        "cjk",
                        "chinese",
                        "sc",
                        "cn",
                        "uming",
                        "ukai",
                        "wqy",
                        "noto",
                    )
                ):
                    logger.debug("Found CJK font (fallback): %s", font_path)
                    return str(font_path)

    logger.warning(
        "No CJK font found on system. Image text overlay may not render CJK characters correctly."
    )
    return None
