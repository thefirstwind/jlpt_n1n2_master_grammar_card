"""五十音排序键（无 OCR 等重依赖，供复习页构建使用）。"""

from __future__ import annotations

GOJUON_ROWS = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"


def gojuon_sort_key(pattern: str) -> tuple[int, str]:
    for ch in pattern:
        if ch in GOJUON_ROWS:
            return (GOJUON_ROWS.index(ch), pattern)
        if "\u3040" <= ch <= "\u309f":
            return (GOJUON_ROWS.index(ch) if ch in GOJUON_ROWS else 200, pattern)
    return (300, pattern)
