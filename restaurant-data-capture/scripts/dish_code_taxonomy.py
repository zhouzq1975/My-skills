"""Helpers for using dish-code taxonomy as lookup input for source packets.

The taxonomy is not a packet output schema. Packet writers should store only the
selected ``normalized.dishEntities[].dishCode`` and keep taxonomy-only metadata
such as labels, facets, mergeFrom, avoid, and pinyin outside the source packet.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any


DEFAULT_DISH_CODE_TAXONOMY_PATH = Path(
    "/Volumes/媒体/chopmap/data/taxonomies/dish-code-taxonomy.json"
)


def normalize_match_key(value: Any) -> str:
    """Normalize a dish label/code for conservative exact matching."""
    return re.sub(
        r"\s+",
        " ",
        re.sub(r"[^0-9a-z\u4e00-\u9fff]+", " ", str(value or "").casefold()),
    ).strip()


@lru_cache(maxsize=4)
def load_dish_code_taxonomy(
    taxonomy_path: str | Path = DEFAULT_DISH_CODE_TAXONOMY_PATH,
) -> dict[str, Any]:
    path = Path(taxonomy_path)
    if not path.is_file():
        return {"schemaVersion": None, "entries": []}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def allowed_dish_codes(
    taxonomy_path: str | Path = DEFAULT_DISH_CODE_TAXONOMY_PATH,
) -> set[str]:
    taxonomy = load_dish_code_taxonomy(taxonomy_path)
    return {
        str(entry.get("dishCode")).strip()
        for entry in taxonomy.get("entries") or []
        if str(entry.get("dishCode") or "").strip()
    }


def dish_code_match_index(
    taxonomy_path: str | Path = DEFAULT_DISH_CODE_TAXONOMY_PATH,
) -> dict[str, str]:
    """Build a conservative exact-match index from codes, labels, pinyin, and mergeFrom."""
    taxonomy = load_dish_code_taxonomy(taxonomy_path)
    index: dict[str, str] = {}
    ambiguous: set[str] = set()
    for entry in taxonomy.get("entries") or []:
        dish_code = str(entry.get("dishCode") or "").strip()
        if not dish_code:
            continue
        raw_terms: list[Any] = [dish_code, entry.get("canonicalName")]
        for values in (entry.get("labels") or {}).values():
            raw_terms.extend(values or [])
        raw_terms.extend(entry.get("pinyin") or [])
        raw_terms.extend(entry.get("mergeFrom") or [])
        for raw in raw_terms:
            key = normalize_match_key(raw)
            if not key:
                continue
            existing = index.get(key)
            if existing and existing != dish_code:
                ambiguous.add(key)
                index.pop(key, None)
            elif key not in ambiguous:
                index[key] = dish_code
    return index


def infer_global_dish_code(
    dish: dict[str, Any],
    taxonomy_path: str | Path = DEFAULT_DISH_CODE_TAXONOMY_PATH,
) -> str | None:
    """Return a taxonomy dishCode only for exact, unambiguous label/code matches."""
    index = dish_code_match_index(taxonomy_path)
    terms: list[Any] = [
        dish.get("dishCode"),
        dish.get("canonicalName"),
        dish.get("nameZh"),
        dish.get("nameEn"),
        dish.get("nameDe"),
    ]
    terms.extend(dish.get("aliases") or [])
    for term in terms:
        match = index.get(normalize_match_key(term))
        if match:
            return match
    return None


def unknown_dish_codes(
    dish_entities: list[dict[str, Any]],
    taxonomy_path: str | Path = DEFAULT_DISH_CODE_TAXONOMY_PATH,
) -> list[str]:
    allowed = allowed_dish_codes(taxonomy_path)
    if not allowed:
        return []
    unknown: list[str] = []
    seen: set[str] = set()
    for dish in dish_entities:
        dish_code = str(dish.get("dishCode") or "").strip()
        if dish_code and dish_code not in allowed and dish_code not in seen:
            seen.add(dish_code)
            unknown.append(dish_code)
    return unknown
