#!/usr/bin/env python3
"""Helpers for controlled seed category/categoryCode normalization."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

CATEGORY_TAXONOMY_PATH = (
    Path(__file__).resolve().parent.parent / "assets" / "category-taxonomy.json"
)


@lru_cache(maxsize=1)
def load_category_taxonomy() -> dict[str, Any]:
    with CATEGORY_TAXONOMY_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _normalize_alias_key(value: str) -> str:
    return re.sub(r"[\s\-]+", "_", value.strip().casefold())


def resolve_category_code(category: Any = None, category_code: Any = None) -> str | None:
    taxonomy = load_category_taxonomy()
    categories = taxonomy.get("categories") or {}
    aliases = taxonomy.get("aliases") or {}

    normalized_aliases = {
        _normalize_alias_key(str(alias)): str(code)
        for alias, code in aliases.items()
        if isinstance(alias, str) and isinstance(code, str)
    }

    for raw_value in (category_code, category):
        if not isinstance(raw_value, str):
            continue
        value = raw_value.strip()
        if not value:
            continue
        if value in categories:
            return value
        code = normalized_aliases.get(_normalize_alias_key(value))
        if code in categories:
            return code
    return None


def canonicalize_category_fields(
    category: Any = None,
    category_code: Any = None,
) -> tuple[str | None, str | None]:
    taxonomy = load_category_taxonomy()
    code = resolve_category_code(category=category, category_code=category_code)
    if not code:
        return None, None

    categories = taxonomy.get("categories") or {}
    entry = categories.get(code) or {}
    label_zh = entry.get("zh")
    return (str(label_zh) if isinstance(label_zh, str) and label_zh.strip() else None, code)
