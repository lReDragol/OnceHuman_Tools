#!/usr/bin/env python3
"""Download Once Human calculator icons from the synced datamined dataset.

This fills the local icon folders expected by the calculator:

- data/icons/weapons/{weapon_id}.png
- data/icons/armor/{slot}/{item_id}.png
- data/icons/mods/{mod_key}/{mod_name}.png

The pages and image URLs come from Once Human DB, which exposes images derived
from game assets. This gives the app real in-game icons without waiting for the
full local NPK texture-path mapping workflow.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen
from xml.etree import ElementTree


BASE_URL = "https://www.oncehumandb.com"
REPO_ROOT = Path(__file__).resolve().parents[1]
CALC_JSON_DIR = REPO_ROOT / "data" / "menu" / "calc" / "bd_json"
ICONS_DIR = REPO_ROOT / "data" / "icons"
SITEMAPS = {
    "weapons": f"{BASE_URL}/sitemap/weapons.xml",
    "armor": f"{BASE_URL}/sitemap/armor.xml",
    "mods": f"{BASE_URL}/sitemap/mods.xml",
}
ARMOR_SLUG_ALIASES = {
    # Legacy local item ids that map to the current public OnceHumanDB pages.
    "lonewolf_hood": ["lonewolf-hat"],
}
WEAPON_SLUG_ALIASES = {
    # The local calculator still has a few legacy/base entries that do not have
    # exact OnceHumanDB pages. Use the closest family page so the UI still gets
    # a real in-game icon instead of an empty placeholder.
    "kam": ["kam-pioneer"],
    "sn700": ["sn700-dark-snowflake"],
}
MOD_SLUG_ALIASES = {
    "mod_pants": {
        # Legacy calculator names vs current OnceHumanDB naming.
        "Abnormal Increase": ["status-amplification"],
        "Precision Charge": ["precise-charge", "precision-charge"],
        "Unstoppable": ["distant-strike"],
    },
    "mod_weapon": {
        # These two old entries are not present by name in the public DB.
        # Fall back to the closest Bounce-family icons instead of showing blanks.
        "Not Throw Away Your Shot": ["boomerang-bullet"],
        "Targeted Bounce": ["multi-bounce"],
        "Vortex Multiplier": ["cryo-catalyst"],
    },
}


def fetch_bytes(url: str) -> bytes:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as response:
        return response.read()


def fetch_text(url: str) -> str:
    return fetch_bytes(url).decode("utf-8")


def parse_image_sitemap(url: str) -> dict[str, str]:
    root = ElementTree.fromstring(fetch_text(url))
    ns = {
        "s": "http://www.sitemaps.org/schemas/sitemap/0.9",
        "image": "http://www.google.com/schemas/sitemap-image/1.1",
    }
    out: dict[str, str] = {}
    for url_node in root.findall("s:url", ns):
        loc = url_node.findtext("s:loc", default="", namespaces=ns).strip()
        image_loc = url_node.findtext("image:image/image:loc", default="", namespaces=ns).strip()
        if loc and image_loc:
            out[loc] = image_loc
    return out


def safe_display_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', "_", name).strip().rstrip(".")
    return cleaned or "unnamed"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def slugify(value: str) -> str:
    value = value.lower().replace("&", " and ").replace("'", "")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def loc_to_slug(loc: str) -> str:
    return loc.rstrip("/").rsplit("/", 1)[-1].lower()


def build_slug_index(image_map: dict[str, str]) -> dict[str, str]:
    return {loc_to_slug(loc): image for loc, image in image_map.items()}


def choose_best_slug(
    slug_index: dict[str, str],
    candidates: list[str],
    preferred_suffixes: list[str] | None = None,
) -> str | None:
    preferred_suffixes = [suffix for suffix in (preferred_suffixes or []) if suffix]

    seen: set[str] = set()
    cleaned_candidates: list[str] = []
    for candidate in candidates:
        if candidate and candidate not in seen:
            seen.add(candidate)
            cleaned_candidates.append(candidate)

    for candidate in cleaned_candidates:
        if candidate in slug_index:
            return candidate

    matching_slugs: list[str] = []
    for candidate in cleaned_candidates:
        prefix = candidate + "-"
        matching_slugs.extend(slug for slug in slug_index if slug.startswith(prefix))
        matching_slugs.extend(slug for slug in slug_index if slug.endswith("-" + candidate))

    ordered_matches = sorted(set(matching_slugs))
    for suffix in preferred_suffixes:
        suffix = slugify(suffix)
        for slug in ordered_matches:
            if slug.endswith("-" + suffix):
                return slug
    if ordered_matches:
        return ordered_matches[0]
    return None


def resolve_weapon_image_url(weapon: dict[str, Any], slug_index: dict[str, str], direct_images: dict[str, str]) -> str | None:
    source_url = weapon.get("source_url")
    if source_url and source_url in direct_images:
        return direct_images[source_url]

    family_name = weapon.get("name", "").split(" - ", 1)[0]
    candidates = [
        *WEAPON_SLUG_ALIASES.get(weapon["id"], []),
        slugify(weapon["id"]),
        slugify(weapon.get("name", "")),
        slugify(family_name),
    ]
    best_slug = choose_best_slug(slug_index, candidates)
    return slug_index.get(best_slug) if best_slug else None


def resolve_armor_image_url(item: dict[str, Any], slug_index: dict[str, str], direct_images: dict[str, str]) -> str | None:
    source_url = item.get("source_url")
    if source_url and source_url in direct_images:
        return direct_images[source_url]

    candidates = [
        *ARMOR_SLUG_ALIASES.get(item["id"], []),
        slugify(item["id"]),
        slugify(item.get("name", "")),
    ]
    best_slug = choose_best_slug(slug_index, candidates)
    return slug_index.get(best_slug) if best_slug else None


def resolve_mod_image_url(mod_key: str, mod: dict[str, Any], slug_index: dict[str, str], direct_images: dict[str, str]) -> str | None:
    source_url = mod.get("source_url")
    if source_url and source_url in direct_images:
        return direct_images[source_url]

    preferred_suffixes = [mod.get("category"), "general"]
    candidates = [
        *MOD_SLUG_ALIASES.get(mod_key, {}).get(mod["name"], []),
        slugify(mod["name"]),
    ]
    best_slug = choose_best_slug(slug_index, candidates, preferred_suffixes)
    return slug_index.get(best_slug) if best_slug else None


def build_download_plan() -> list[tuple[str, Path]]:
    weapon_images = parse_image_sitemap(SITEMAPS["weapons"])
    armor_images = parse_image_sitemap(SITEMAPS["armor"])
    mod_images = parse_image_sitemap(SITEMAPS["mods"])
    weapon_slug_index = build_slug_index(weapon_images)
    armor_slug_index = build_slug_index(armor_images)
    mod_slug_index = build_slug_index(mod_images)

    weapons_data = load_json(CALC_JSON_DIR / "weapon_list.json")["weapons"]
    items_data = load_json(CALC_JSON_DIR / "items_and_sets.json")["items"]
    mods_data = load_json(CALC_JSON_DIR / "mods_config.json")

    plan: list[tuple[str, Path]] = []

    for weapon in weapons_data:
        image_url = resolve_weapon_image_url(weapon, weapon_slug_index, weapon_images)
        if image_url:
            destination = ICONS_DIR / "weapons" / f"{weapon['id']}.png"
            plan.append((image_url, destination))

    for item in items_data:
        image_url = resolve_armor_image_url(item, armor_slug_index, armor_images)
        if image_url:
            destination = ICONS_DIR / "armor" / item["type"] / f"{item['id']}.png"
            plan.append((image_url, destination))

    for mod_key, entries in mods_data.items():
        if not isinstance(entries, list):
            continue
        for mod in entries:
            image_url = resolve_mod_image_url(mod_key, mod, mod_slug_index, mod_images)
            if image_url:
                filename = safe_display_filename(mod["name"]) + ".png"
                destination = ICONS_DIR / "mods" / mod_key / filename
                plan.append((image_url, destination))

    return plan


def download_one(image_url: str, destination: Path, force: bool) -> tuple[str, bool]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        return str(destination), False
    destination.write_bytes(fetch_bytes(image_url))
    return str(destination), True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Overwrite already downloaded images")
    parser.add_argument("--workers", type=int, default=12, help="Parallel downloads")
    args = parser.parse_args()

    plan = build_download_plan()
    unique_plan = {(url, str(path)) for url, path in plan}

    downloaded = 0
    skipped = 0
    failures: list[str] = []

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as executor:
        future_map = {
            executor.submit(download_one, url, Path(path), args.force): (url, path)
            for url, path in unique_plan
        }
        for future in concurrent.futures.as_completed(future_map):
            url, path = future_map[future]
            try:
                _, changed = future.result()
            except Exception as exc:
                failures.append(f"{path} <- {url}: {exc}")
                continue
            if changed:
                downloaded += 1
            else:
                skipped += 1

    summary = {
        "planned": len(unique_plan),
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": len(failures),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if failures:
        print("\n".join(failures[:50]))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
