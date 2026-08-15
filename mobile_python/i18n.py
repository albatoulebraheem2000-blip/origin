from __future__ import annotations

import re

try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except ImportError:  # API-only development can run before mobile extras exist.
    arabic_reshaper = None
    get_display = None


ARABIC = re.compile(r"[\u0600-\u06ff]")


def rtl(value: object) -> str:
    """Shape Arabic for Kivy's SDL2 text provider, line by line."""
    text = "" if value is None else str(value)
    if not ARABIC.search(text) or arabic_reshaper is None or get_display is None:
        return text
    output: list[str] = []
    for line in text.split("\n"):
        output.append(get_display(arabic_reshaper.reshape(line), base_dir="R") if ARABIC.search(line) else line)
    return "\n".join(output)
