#!/usr/bin/env python3
"""Batch-fetch Google Maps data for multiple restaurants.

Input sources (at least one required):
  --csv     : CSV file with restaurant seeds
  --packets : Directory of existing source-packet.json files

The script will:
  1. Read restaurants from CSV and/or existing packets
  2. Deduplicate by (name, address)
  3. Skip restaurants that already have Places API data
  4. Call Places API for each remaining restaurant
  5. Create or update source-packet.json files

Output goes to --output-dir (default: /Volumes/媒体/chopmap/data/restaurants/).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

# Import the single-restaurant fetcher
sys.path.insert(0, str(Path(__file__).resolve().parent))
from fetch_google_place import (
    canonicalize_packet,
    fetch_restaurant,
    get_api_key,
    mark_api_failure,
    merge_into_packet,
    write_packet,
)

DEFAULT_OUTPUT_DIR = "/Volumes/媒体/chopmap/data/restaurants"
DEFAULT_RATE_LIMIT = 5  # requests per second


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "restaurant"


def packet_filename(city: str, name: str) -> str:
    return f"{slugify(city)}__{slugify(name)}__source-packet.json"


def load_template() -> dict[str, Any]:
    template_path = (
        Path(__file__).resolve().parent.parent
        / "assets"
        / "restaurant-source-packet.template.json"
    )
    with template_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_seed_payload(
    seed_data: dict[str, Any],
    api_url: str | None = None,
) -> dict[str, Any]:
    extra_fields = seed_data.get("extra_fields", {}) or {}
    category = extra_fields.get("category") or seed_data.get("category")
    chain = extra_fields.get("chain") or seed_data.get("chain")
    neighborhood = (
        extra_fields.get("neighborhood")
        or extra_fields.get("district")
        or seed_data.get("neighborhood")
        or seed_data.get("district")
    )
    category_code = extra_fields.get("categoryCode")
    if not category_code:
        if category in {"小吃", "Snack", "snack"}:
            category_code = "snack"
        elif category in {"饭店", "Restaurant", "restaurant"}:
            category_code = "restaurant"
        elif category in {"面馆", "Noodle house", "noodle house", "noodle_house"}:
            category_code = "noodle_house"
        elif category:
            category_code = str(category).strip().lower().replace(" ", "-")
    chain_bool = extra_fields.get("chainBool")
    if chain_bool is None and chain is not None:
        chain_text = str(chain).strip()
        if chain_text in {"是", "yes", "true", "1"}:
            chain_bool = True
        elif chain_text in {"否", "no", "false", "0"}:
            chain_bool = False
    neighborhood_code = extra_fields.get("neighborhoodCode") or extra_fields.get("districtCode")
    if not neighborhood_code and neighborhood:
        neighborhood_code = (
            str(neighborhood)
            .strip()
            .lower()
            .replace(" ", "-")
            .replace("ä", "ae")
            .replace("ö", "oe")
            .replace("ü", "ue")
            .replace("ß", "ss")
        )
    return {
        "inputNameRaw": seed_data.get("inputNameRaw") or seed_data.get("nameZh") or seed_data.get("name_zh") or seed_data.get("nameEn") or seed_data.get("name_en"),
        "nameZh": seed_data.get("nameZh") or seed_data.get("name_zh"),
        "nameEn": seed_data.get("nameEn") or seed_data.get("name_en"),
        "nameDe": seed_data.get("nameDe") or seed_data.get("name_de") or seed_data.get("nameEn") or seed_data.get("name_en"),
        "addressRaw": seed_data.get("addressRaw") or seed_data.get("address", ""),
        "city": seed_data.get("city", "Berlin"),
        "country": seed_data.get("country", "Germany"),
        "googleMapsUrl": api_url or seed_data.get("googleMapsUrl") or seed_data.get("google_maps_url"),
        "extra_fields": {
            "category": category,
            "categoryCode": category_code,
            "chain": chain,
            "chainBool": chain_bool,
            "neighborhood": neighborhood,
            "neighborhoodCode": neighborhood_code,
        },
    }


def ensure_packet(item: dict[str, Any]) -> dict[str, Any]:
    packet = item.get("packet")
    if packet is not None:
        packet = canonicalize_packet(packet)
        item["packet"] = packet
        return packet

    packet = load_template()
    packet["seed"] = build_seed_payload(item["seed"])
    packet = canonicalize_packet(packet)
    item["packet"] = packet
    return packet


def has_api_data(packet: dict[str, Any]) -> bool:
    """Check if packet already has Google Maps API data."""
    packet = canonicalize_packet(packet)
    sources = packet.get("source_packet", [])
    return any(
        s.get("platform") == "google_places_api_new" and s.get("accessStatus") == "accessed"
        for s in sources
    )


# ---------------------------------------------------------------------------
# CSV reader
# ---------------------------------------------------------------------------

def read_csv(csv_path: Path) -> list[dict[str, str]]:
    """Read restaurant list from CSV.

    Preferred V2 seed columns:
      inputNameRaw
      nameZh
      nameEn
      nameDe
      addressRaw
      city
      country
      googleMapsUrl

    Legacy columns are still accepted for compatibility:
      name_zh / 中文名 / chinese_name
      name_en / 英文名 / english_name / name
      name_de / 德文名 / german_name
      address / 地址
      google_maps_url / google_maps

    Additional columns are preserved as extra_fields.
    """
    restaurants = []
    with csv_path.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            return []

        # Normalize column names
        col_map = {}
        for col in reader.fieldnames:
            col_lower = col.strip().lower()
            if col in ("inputNameRaw",):
                col_map[col] = "inputNameRaw"
            elif col in ("nameZh",) or col_lower in ("name_zh", "中文名", "chinese_name"):
                col_map[col] = "nameZh"
            elif col in ("nameEn",) or col_lower in ("name_en", "英文名", "english_name", "name"):
                col_map[col] = "nameEn"
            elif col in ("nameDe",) or col_lower in ("name_de", "德文名", "german_name"):
                col_map[col] = "nameDe"
            elif col in ("addressRaw",) or col_lower in ("address", "地址"):
                col_map[col] = "addressRaw"
            elif col_lower in ("city", "城市"):
                col_map[col] = "city"
            elif col_lower in ("country", "国家"):
                col_map[col] = "country"
            elif col in ("googleMapsUrl",) or col_lower in ("google_maps_url", "google_maps"):
                col_map[col] = "googleMapsUrl"
            elif col_lower in ("类别", "category"):
                col_map[col] = "category"
            elif col_lower in ("连锁", "chain"):
                col_map[col] = "chain"
            elif col_lower in ("城区", "neighborhood", "ortsteil"):
                col_map[col] = "neighborhood"
            else:
                col_map[col] = col  # preserve as-is

        for row in reader:
            normalized = {}
            extra = {}
            for orig_col, mapped_col in col_map.items():
                val = (row.get(orig_col) or "").strip()
                if mapped_col in (
                    "inputNameRaw", "nameZh", "nameEn", "nameDe",
                    "addressRaw", "city", "country", "googleMapsUrl",
                ):
                    normalized[mapped_col] = val
                else:
                    if val:
                        extra[mapped_col] = val

            # Defaults
            normalized.setdefault("city", "Berlin")
            normalized.setdefault("country", "Germany")
            normalized.setdefault("nameDe", normalized.get("nameEn", ""))
            normalized.setdefault("inputNameRaw", normalized.get("nameZh") or normalized.get("nameEn"))

            # Must have at least a name
            if not normalized.get("nameEn") and not normalized.get("nameZh"):
                continue

            if extra:
                normalized["extra_fields"] = extra

            restaurants.append(normalized)

    return restaurants


# ---------------------------------------------------------------------------
# Packet scanner
# ---------------------------------------------------------------------------

def scan_existing_packets(packets_dir: Path) -> list[tuple[Path, dict[str, Any]]]:
    """Scan directory for source-packet.json files. Return (path, data) pairs."""
    results = []
    for f in sorted(packets_dir.glob("*__source-packet.json")):
        try:
            with f.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            results.append((f, data))
        except (json.JSONDecodeError, OSError) as e:
            print(f"  ⚠ Skipping {f.name}: {e}", file=sys.stderr)
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Batch-fetch Google Maps data for restaurants.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch from CSV (new restaurants)
  python batch_fetch_google_maps.py --csv restaurants.csv

  # Update existing packets
  python batch_fetch_google_maps.py --packets /path/to/restaurants/

  # Both: CSV + existing packets
  python batch_fetch_google_maps.py --csv restaurants.csv --packets /path/to/restaurants/

  # Dry run (no API calls)
  python batch_fetch_google_maps.py --csv restaurants.csv --dry-run
        """,
    )
    parser.add_argument("--csv", help="Path to CSV file with restaurant list.")
    parser.add_argument("--packets", help="Directory containing existing source-packet.json files.")
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory for packets (default: {DEFAULT_OUTPUT_DIR}).",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=DEFAULT_RATE_LIMIT,
        help=f"Max API requests per second (default: {DEFAULT_RATE_LIMIT}).",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        default=True,
        help="Skip restaurants that already have API data (default: True).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch even if API data already exists.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be fetched without calling the API.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Process at most N restaurants (useful for testing).",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.csv and not args.packets:
        parser.error("At least one of --csv or --packets is required.")

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    delay = 1.0 / args.rate_limit if args.rate_limit > 0 else 0

    # Collect work items: (name, address, city, seed_data, existing_packet_path, existing_packet)
    work_items: list[dict[str, Any]] = []
    seen_keys: set[str] = set()

    # --- Scan existing packets ---
    if args.packets:
        packets_dir = Path(args.packets).resolve()
        print(f"\n📂 Scanning existing packets in: {packets_dir}", file=sys.stderr)
        for ppath, pdata in scan_existing_packets(packets_dir):
            pdata = canonicalize_packet(pdata)
            seed = pdata.get("seed", {})
            name = seed.get("nameEn") or seed.get("nameZh") or seed.get("nameDe") or ""
            address = seed.get("addressRaw", "")
            city = seed.get("city", "Berlin")
            key = f"{name.lower()}|{address.lower()}"

            if key in seen_keys:
                continue
            seen_keys.add(key)

            if has_api_data(pdata) and not args.force:
                continue  # Already has API data

            work_items.append({
                "name": name,
                "address": address,
                "city": city,
                "seed": seed,
                "packet_path": ppath,
                "packet": pdata,
            })

    # --- Read CSV ---
    if args.csv:
        csv_path = Path(args.csv).resolve()
        print(f"\n📄 Reading CSV: {csv_path}", file=sys.stderr)
        csv_restaurants = read_csv(csv_path)
        print(f"   Found {len(csv_restaurants)} restaurants in CSV", file=sys.stderr)

        for r in csv_restaurants:
            name = r.get("nameEn") or r.get("nameZh") or ""
            address = r.get("addressRaw", "")
            city = r.get("city", "Berlin")
            key = f"{name.lower()}|{address.lower()}"

            if key in seen_keys:
                continue
            seen_keys.add(key)

            # Check if packet already exists on disk
            fname = packet_filename(city, name)
            existing_path = output_dir / fname
            existing_packet = None

            if existing_path.is_file():
                try:
                    with existing_path.open("r", encoding="utf-8") as f:
                        existing_packet = json.load(f)
                    if has_api_data(existing_packet) and not args.force:
                        continue
                except (json.JSONDecodeError, OSError):
                    pass

            work_items.append({
                "name": name,
                "address": address,
                "city": city,
                "seed": r,
                "packet_path": existing_path if existing_packet else None,
                "packet": existing_packet,
            })

    # Apply limit
    if args.limit:
        work_items = work_items[: args.limit]

    # --- Summary ---
    print(f"\n{'=' * 60}", file=sys.stderr)
    print(f"  Restaurants to process: {len(work_items)}", file=sys.stderr)
    print(f"  Output directory:       {output_dir}", file=sys.stderr)
    print(f"  Rate limit:             {args.rate_limit} req/s", file=sys.stderr)
    print(f"  Dry run:                {args.dry_run}", file=sys.stderr)
    print(f"{'=' * 60}\n", file=sys.stderr)

    if not work_items:
        print("✅ Nothing to do — all restaurants already have API data.", file=sys.stderr)
        return

    if args.dry_run:
        for i, item in enumerate(work_items, 1):
            status = "UPDATE" if item["packet"] else "CREATE"
            print(f"  [{status}] {i:3d}. {item['name']} | {item['address']}")
        print(f"\n  Total: {len(work_items)} restaurants would be processed.")
        return

    # --- Fetch ---
    try:
        api_key = get_api_key()
    except RuntimeError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        for item in work_items:
            packet = ensure_packet(item)
            out_path = item.get("packet_path")
            if not out_path:
                out_path = output_dir / packet_filename(item["city"], item["name"])
            packet = mark_api_failure(
                packet,
                "api_key_not_configured",
                str(exc),
                url=packet.get("seed", {}).get("googleMapsUrl", "") or "",
            )
            write_packet(out_path, packet)
        sys.exit(1)

    stats = {"success": 0, "failed": 0, "skipped": 0}

    for i, item in enumerate(work_items, 1):
        name = item["name"]
        address = item["address"]
        city = item["city"]

        print(f"\n[{i}/{len(work_items)}] {name}", file=sys.stderr)

        try:
            api_data = fetch_restaurant(name, address, api_key)
        except Exception as e:
            print(f"  ✗ API error: {e}", file=sys.stderr)
            packet = ensure_packet(item)
            packet = mark_api_failure(
                packet,
                "api_call_failed",
                str(e),
                url=packet.get("seed", {}).get("googleMapsUrl", "") or "",
            )
            out_path = item.get("packet_path")
            if not out_path:
                out_path = output_dir / packet_filename(city, name)
            write_packet(out_path, packet)
            stats["failed"] += 1
            continue

        if not api_data:
            packet = ensure_packet(item)
            packet = mark_api_failure(
                packet,
                "api_no_results",
                f"No Google Maps Places API result for query: {name} | {address}",
                url=packet.get("seed", {}).get("googleMapsUrl", "") or "",
            )
            out_path = item.get("packet_path")
            if not out_path:
                out_path = output_dir / packet_filename(city, name)
            write_packet(out_path, packet)
            stats["failed"] += 1
            continue

        # Load or create packet
        packet = ensure_packet(item)
        packet["seed"] = build_seed_payload(item["seed"], api_data["details_en"].get("url"))
        packet = canonicalize_packet(packet)

        packet = merge_into_packet(packet, api_data)

        # Determine output path
        out_path = item.get("packet_path")
        if not out_path:
            fname = packet_filename(city, name)
            out_path = output_dir / fname

        write_packet(out_path, packet)

        print(f"  ✓ Saved: {out_path.name}", file=sys.stderr)
        stats["success"] += 1

        # Rate limiting
        if i < len(work_items):
            time.sleep(delay)

    # --- Report ---
    print(f"\n{'=' * 60}", file=sys.stderr)
    print(f"  ✅ Success: {stats['success']}", file=sys.stderr)
    print(f"  ❌ Failed:  {stats['failed']}", file=sys.stderr)
    print(f"  ⏭  Skipped: {stats['skipped']}", file=sys.stderr)
    print(f"{'=' * 60}", file=sys.stderr)


if __name__ == "__main__":
    main()
