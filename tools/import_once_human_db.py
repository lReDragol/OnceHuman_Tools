#!/usr/bin/env python3
"""Import public Once Human DB data into calculator JSON datasets.

This importer is a pragmatic bridge while direct bindict extraction from the
game client is still incomplete. It expands:

- weapon_list.json
- items_and_sets.json
- mods_config.json

The importer preserves existing hand-authored mechanics/effects where present
and only fills gaps or appends new records.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import html
import json
import re
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from xml.etree import ElementTree


BASE_URL = "https://www.oncehumandb.com"
SITEMAPS = {
    "weapons": f"{BASE_URL}/sitemap/weapons.xml",
    "armor": f"{BASE_URL}/sitemap/armor.xml",
    "armor_sets": f"{BASE_URL}/sitemap/armor-sets.xml",
    "mods": f"{BASE_URL}/sitemap/mods.xml",
}

REPO_ROOT = Path(__file__).resolve().parents[1]
CALC_JSON_DIR = REPO_ROOT / "data" / "menu" / "calc" / "bd_json"
DEFAULT_CACHE_DIR = Path(tempfile.gettempdir()) / "once_human_db_cache"

CONDITIONAL_MARKERS = (
    "after ",
    "before ",
    "can stack",
    "chance",
    "cooldown",
    "every ",
    "for every",
    "for the first",
    "for the next",
    "if ",
    "lasts",
    "lasting",
    "recover",
    "refill",
    "reloads",
    "stack",
    "stacks",
    "until ",
    "when ",
    "while ",
)

WEAPON_TYPE_MAP = {
    "assault rifle": "assault_rifl",
    "bow": "crossbows",
    "crossbow": "crossbows",
    "flamethrower": "heavy_weapon",
    "heavy weapon": "heavy_weapon",
    "lmg": "lmgs",
    "light machine gun": "lmgs",
    "melee": "melee",
    "pistol": "pistol",
    "rocket launcher": "heavy_weapon",
    "shotgun": "shotgun",
    "smg": "smgs",
    "sniper rifle": "sniper_rifles",
    "submachine gun": "smgs",
}

ARMOR_SLOT_MAP = {
    "boots": "boots",
    "bottoms": "pants",
    "gloves": "gloves",
    "helmet": "helmet",
    "mask": "mask",
    "pants": "pants",
    "shoes": "boots",
    "top": "top",
}

MOD_SLOT_MAP = {
    "bottoms": "mod_pants",
    "gloves": "mod_gloves",
    "helmet": "mod_helmet",
    "mask": "mod_mask",
    "pants": "mod_pants",
    "shoes": "mod_boots",
    "top": "mod_top",
    "weapon": "mod_weapon",
}

SIMPLE_STAT_PATTERNS = (
    (r"\bCrit Rate \+([0-9]+(?:\.[0-9]+)?)%", ("crit_rate_percent",)),
    (r"\bCrit DMG \+([0-9]+(?:\.[0-9]+)?)%", ("crit_damage_percent",)),
    (r"\bWeakspot DMG \+([0-9]+(?:\.[0-9]+)?)%", ("weakspot_damage_percent",)),
    (r"\bWeapon DMG \+([0-9]+(?:\.[0-9]+)?)%", ("weapon_damage_percent",)),
    (r"\bStatus DMG \+([0-9]+(?:\.[0-9]+)?)%", ("status_damage_percent",)),
    (r"\bElement(?:al)? DMG \+([0-9]+(?:\.[0-9]+)?)%", ("elemental_damage_percent",)),
    (r"\bMovement Speed \+([0-9]+(?:\.[0-9]+)?)%", ("movement_speed_percent",)),
    (r"\bFire Rate \+([0-9]+(?:\.[0-9]+)?)%", ("fire_rate_percent",)),
    (r"\bReload (?:Efficiency|Speed) \+([0-9]+(?:\.[0-9]+)?)%", ("reload_speed_percent",)),
    (r"\bDMG Reduction \+?([0-9]+(?:\.[0-9]+)?)%", ("damage_reduction_percent",)),
    (r"\bHead DMG Reduction \+([0-9]+(?:\.[0-9]+)?)%", ("head_damage_reduction_percent",)),
)


def slug_to_title(slug: str) -> str:
    parts = [part for part in slug.split("-") if part]
    keep_upper = {"aa12", "aa1", "acs12", "akm", "awm", "bar", "dbsg", "db12", "de", "dp12", "g17", "kv", "lmg", "m416", "m870", "mg4", "mg42", "mk14", "mp5", "mp7", "p90", "r500", "scar", "sks", "tec9", "wa2000", "xm8"}
    rendered = []
    for part in parts:
        if part in keep_upper:
            rendered.append(part.upper())
        elif re.fullmatch(r"[0-9]+", part):
            rendered.append(part)
        else:
            rendered.append(part.replace("_", " ").title())
    return " ".join(rendered)


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def normalize_id(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def parse_percent(value: str) -> float | None:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", value)
    return float(match.group(1)) if match else None


def parse_seconds(value: str) -> float | None:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*s", value.lower())
    return float(match.group(1)) if match else None


def parse_number(value: str) -> float | None:
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", value.replace(",", ""))
    return float(match.group(1)) if match else None


def strip_tags(value: str) -> str:
    value = re.sub(r"<!--.*?-->", "", value, flags=re.S)
    value = re.sub(r"<[^>]+>", "", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def fetch_text(url: str, cache_dir: Path, ttl_hours: float = 24.0) -> str:
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_name = normalize_id(url.removeprefix("https://").removeprefix("http://")) + ".html"
    cache_path = cache_dir / cache_name
    if cache_path.exists():
        age_hours = (time.time() - cache_path.stat().st_mtime) / 3600.0
        if age_hours <= ttl_hours:
            return cache_path.read_text(encoding="utf-8")

    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as response:
        text = response.read().decode("utf-8")
    cache_path.write_text(text, encoding="utf-8")
    return text


def load_sitemap_urls(url: str, cache_dir: Path) -> list[str]:
    xml_text = fetch_text(url, cache_dir)
    root = ElementTree.fromstring(xml_text)
    urls: list[str] = []
    for loc in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
        if loc.text:
            urls.append(loc.text.strip())
    return urls


def extract_json_ld_blocks(page: str) -> list[dict[str, Any]]:
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
    parsed: list[dict[str, Any]] = []
    for block in blocks:
        try:
            data = json.loads(html.unescape(block))
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            parsed.append(data)
    return parsed


def get_item_page_json(page: str) -> dict[str, Any]:
    for block in extract_json_ld_blocks(page):
        if block.get("@type") == "ItemPage":
            return block
    raise ValueError("ItemPage JSON-LD block not found")


def parse_table_section(page: str, heading: str) -> dict[str, str]:
    pattern = rf'<h2 class="section-label[^"]*">{re.escape(heading)}</h2><table class="w-full text-sm"><tbody><tr>(.*?)</tr><tr>(.*?)</tr>'
    match = re.search(pattern, page, re.S)
    if not match:
        return {}
    headers = [strip_tags(raw) for raw in re.findall(r"<th[^>]*>(.*?)</th>", match.group(1), re.S)]
    values = [strip_tags(raw) for raw in re.findall(r"<td[^>]*>(.*?)</td>", match.group(2), re.S)]
    return dict(zip(headers, values))


def parse_paragraph_section(page: str, heading: str) -> str:
    pattern = rf'<h2 class="section-label[^"]*">{re.escape(heading)}</h2><p[^>]*>(.*?)</p>'
    match = re.search(pattern, page, re.S)
    return strip_tags(match.group(1)) if match else ""


def parse_set_bonuses(page: str, heading: str) -> list[dict[str, Any]]:
    pattern = rf'<h2[^>]*>{re.escape(heading)}</h2><div class="space-y-2">(.*?)</div></div>'
    match = re.search(pattern, page, re.S)
    if not match:
        return []
    bonuses: list[dict[str, Any]] = []
    for required_items, description in re.findall(r"<span[^>]*>(\d+)</span><p[^>]*>(.*?)</p>", match.group(1), re.S):
        clean_description = strip_tags(description)
        bonuses.append(
            {
                "required_items": int(required_items),
                "description": clean_description,
                "effects": parse_simple_effects(clean_description),
            }
        )
    return bonuses


def parse_armor_set_ref(page: str) -> tuple[str | None, str | None, list[dict[str, Any]]]:
    pattern = r'<h2[^>]*>Set Bonus</h2><div class="font-display[^"]*"><a[^>]*href="([^"]+)"[^>]*>(.*?)</a></div><div class="space-y-2">(.*?)</div></div>'
    match = re.search(pattern, page, re.S)
    if not match:
        return None, None, []
    href = match.group(1).strip()
    set_name = strip_tags(match.group(2))
    bonuses = []
    for required_items, description in re.findall(r"<span[^>]*>(\d+)</span><p[^>]*>(.*?)</p>", match.group(3), re.S):
        clean_description = strip_tags(description)
        bonuses.append(
            {
                "required_items": int(required_items),
                "description": clean_description,
                "effects": parse_simple_effects(clean_description),
            }
        )
    return href.rsplit("/", 1)[-1], set_name, bonuses


def parse_simple_effects(description: str) -> list[dict[str, Any]]:
    effects: list[dict[str, Any]] = []
    segments = [segment.strip() for segment in re.split(r"[.;]", description) if segment.strip()]
    for segment in segments:
        lower = segment.lower()
        if any(marker in lower for marker in CONDITIONAL_MARKERS):
            continue
        if "weapon and status dmg" in lower:
            number = parse_percent(segment)
            if number is not None:
                effects.append({"type": "increase_stat", "stat": "weapon_damage_percent", "value": number})
                effects.append({"type": "increase_stat", "stat": "status_damage_percent", "value": number})
            continue
        if "melee, weapon, and status dmg" in lower or "melee, weapon, status dmg" in lower:
            number = parse_percent(segment)
            if number is not None:
                effects.append({"type": "increase_stat", "stat": "weapon_damage_percent", "value": number})
                effects.append({"type": "increase_stat", "stat": "status_damage_percent", "value": number})
            continue
        for pattern, stats in SIMPLE_STAT_PATTERNS:
            match = re.search(pattern, segment, re.I)
            if not match:
                continue
            value = float(match.group(1))
            for stat in stats:
                effects.append({"type": "increase_stat", "stat": stat, "value": value})
            break
    return effects


def parse_weapon_page(url: str, page: str) -> dict[str, Any]:
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    item_page = get_item_page_json(page)
    props = {
        prop["name"]: prop["value"]
        for prop in item_page.get("mainEntity", {}).get("additionalProperty", [])
        if isinstance(prop, dict) and "name" in prop
    }
    combat = parse_table_section(page, "Combat")
    details = parse_table_section(page, "Details")
    falloff = parse_table_section(page, "Damage Falloff")

    site_type = str(props.get("Type", "")).strip()
    base_stats: dict[str, Any] = {}
    damage = parse_number(str(props.get("Damage", "")))
    fire_rate = parse_number(str(props.get("Fire Rate", "")))
    magazine = parse_number(str(props.get("Magazine Size", "")))
    crit_rate = parse_percent(combat.get("Crit Rate", ""))
    crit_damage = parse_percent(combat.get("Crit DMG", ""))
    weakspot = parse_percent(combat.get("Weakspot DMG", ""))
    reload_time = parse_seconds(details.get("Reload", ""))
    reload_points = parse_number(details.get("Reload", ""))
    range_full = parse_number(falloff.get("Full Damage Range", ""))
    range_min = parse_number(falloff.get("Min Damage Range", ""))
    min_damage_percent = parse_percent(falloff.get("Min Damage", ""))
    mobility = parse_number(details.get("Mobility", ""))
    ads_time = parse_seconds(details.get("ADS Time", ""))
    bullet_speed = parse_number(details.get("Bullet Speed", ""))

    if damage is not None:
        base_stats["damage_per_projectile"] = damage
    if fire_rate is not None:
        base_stats["fire_rate"] = fire_rate
    if magazine is not None:
        base_stats["magazine_capacity"] = int(magazine)
    if crit_rate is not None:
        base_stats["crit_rate_percent"] = crit_rate
    if crit_damage is not None:
        base_stats["crit_damage_percent"] = crit_damage
    if weakspot is not None:
        base_stats["weakspot_damage_percent"] = weakspot
    if reload_time is not None:
        base_stats["reload_time_seconds"] = reload_time
    if reload_points is not None:
        base_stats["reload_speed_points"] = reload_points
    if range_full is not None:
        base_stats["range"] = range_full
    if mobility is not None:
        base_stats["mobility"] = mobility
    if ads_time is not None:
        base_stats["ads_time_seconds"] = ads_time
    if bullet_speed is not None:
        base_stats["bullet_speed"] = bullet_speed
    if range_min is not None:
        base_stats["min_damage_range_meters"] = range_min
    if min_damage_percent is not None:
        base_stats["min_damage_percent"] = min_damage_percent
    base_stats.setdefault("projectiles_per_shot", 1)

    return {
        "site_slug": slug,
        "site_name": item_page["name"],
        "type": WEAPON_TYPE_MAP.get(site_type.lower(), normalize_id(site_type) or "unknown"),
        "rarity": str(props.get("Rarity", "")).strip().lower() or "unknown",
        "description": parse_paragraph_section(page, "Description"),
        "base_stats": base_stats,
        "ammo_type": details.get("Ammo") or props.get("Ammo Type", ""),
        "source_url": url,
    }


def parse_armor_page(url: str, page: str) -> dict[str, Any]:
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    item_page = get_item_page_json(page)
    props = {
        prop["name"]: prop["value"]
        for prop in item_page.get("mainEntity", {}).get("additionalProperty", [])
        if isinstance(prop, dict) and "name" in prop
    }
    set_slug, set_name, bonuses = parse_armor_set_ref(page)
    slot = ARMOR_SLOT_MAP.get(str(props.get("Type", "")).strip().lower())
    if not slot:
        raise ValueError(f"Unknown armor type on {url}: {props.get('Type')}")
    base_stat_hint: dict[str, Any] = {}
    hp = parse_number(str(props.get("HP", "")))
    pollution = parse_number(str(props.get("Pollution Resist", "")))
    psi = parse_number(str(props.get("PSI Intensity", "")))
    if hp is not None:
        base_stat_hint["hp"] = hp
    if pollution is not None:
        base_stat_hint["pollution_resist"] = pollution
    if psi is not None:
        base_stat_hint["psi_intensity"] = psi
    return {
        "site_slug": slug,
        "site_name": item_page["name"],
        "type": slot,
        "rarity": str(props.get("Rarity", "")).strip().lower() or "unknown",
        "set_id": normalize_id(set_slug) if set_slug else None,
        "set_name": set_name,
        "set_bonuses": bonuses,
        "base_stat_hint": base_stat_hint,
        "description": item_page.get("description", ""),
        "source_url": url,
    }


def parse_armor_set_page(url: str, page: str) -> dict[str, Any]:
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    item_page = get_item_page_json(page)
    props = {
        prop["name"]: prop["value"]
        for prop in item_page.get("mainEntity", {}).get("additionalProperty", [])
        if isinstance(prop, dict) and "name" in prop
    }
    bonuses = parse_set_bonuses(page, "Set Bonuses")
    description = " | ".join(
        f"{bonus['required_items']}-Piece: {bonus['description']}"
        for bonus in bonuses
    )
    return {
        "set_id": normalize_id(slug),
        "name": item_page["name"],
        "rarity": str(props.get("Rarity", "")).strip().lower() or "unknown",
        "max_items": int(parse_number(str(props.get("Pieces", ""))) or 0) or 6,
        "bonuses": bonuses,
        "description": description,
        "source_url": url,
    }


def parse_mod_page(url: str, page: str) -> dict[str, Any]:
    slug = url.rstrip("/").rsplit("/", 1)[-1]
    item_page = get_item_page_json(page)
    props = {
        prop["name"]: prop["value"]
        for prop in item_page.get("mainEntity", {}).get("additionalProperty", [])
        if isinstance(prop, dict) and "name" in prop
    }
    mod_type = str(props.get("Mod Type", "")).strip()
    mod_key = MOD_SLOT_MAP.get(mod_type.lower())
    if not mod_key:
        raise ValueError(f"Unknown mod type on {url}: {mod_type}")

    site_name = item_page["name"]
    slug_name = slug_to_title(slug)
    if normalize_key(site_name) == normalize_key(slug_name):
        display_name = site_name
    elif normalize_key(slug_name).startswith(normalize_key(site_name)):
        display_name = slug_name
    else:
        display_name = site_name

    description = parse_paragraph_section(page, "Description") or parse_paragraph_section(page, "Core Effect")
    return {
        "mod_key": mod_key,
        "name": display_name,
        "rarity": str(props.get("Rarity", "")).strip().lower() or "unknown",
        "slot": mod_type,
        "description": description,
        "effects": parse_simple_effects(description),
        "source_url": url,
    }


def fetch_and_parse(kind: str, url: str, cache_dir: Path) -> dict[str, Any] | None:
    try:
        page = fetch_text(url, cache_dir)
        if kind == "weapons":
            return parse_weapon_page(url, page)
        if kind == "armor":
            return parse_armor_page(url, page)
        if kind == "armor_sets":
            return parse_armor_set_page(url, page)
        if kind == "mods":
            return parse_mod_page(url, page)
        raise ValueError(f"Unsupported kind: {kind}")
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        print(f"[warn] {kind} {url}: {exc}")
        return None


def merge_weapons(existing_weapons: list[dict[str, Any]], scraped_weapons: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_name = {normalize_key(weapon["name"]): weapon for weapon in existing_weapons}
    for weapon in scraped_weapons:
        if not weapon:
            continue
        match = by_name.get(normalize_key(weapon["site_name"]))
        if match:
            match["type"] = weapon["type"]
            match["rarity"] = weapon["rarity"]
            match["description"] = weapon["description"] or match.get("description", "")
            match["source_url"] = weapon["source_url"]
            base_stats = match.setdefault("base_stats", {})
            base_stats.update(weapon["base_stats"])
            match["ammo_type"] = weapon["ammo_type"]
            if not (isinstance(match.get("mechanics"), dict) and match["mechanics"].get("effects")):
                match["mechanics"] = {
                    "description": "Imported base weapon data from Once Human DB. Direct local mechanic extraction from game files is still pending.",
                    "effects": [],
                }
            continue

        new_entry = {
            "id": normalize_id(weapon["site_slug"]),
            "name": weapon["site_name"],
            "type": weapon["type"],
            "rarity": weapon["rarity"],
            "base_stats": weapon["base_stats"],
            "mechanics": {
                "description": "Imported base weapon data from Once Human DB. Direct local mechanic extraction from game files is still pending.",
                "effects": [],
            },
            "description": weapon["description"],
            "ammo_type": weapon["ammo_type"],
            "source_url": weapon["source_url"],
        }
        existing_weapons.append(new_entry)
        by_name[normalize_key(new_entry["name"])] = new_entry

    return sorted(existing_weapons, key=lambda item: (item.get("type", ""), item.get("rarity", ""), item["name"]))


def merge_items_and_sets(
    existing_data: dict[str, Any],
    scraped_items: list[dict[str, Any]],
    scraped_sets: list[dict[str, Any]],
) -> dict[str, Any]:
    items = list(existing_data.get("items", []))
    sets = list(existing_data.get("sets", []))
    items_by_name = {normalize_key(item["name"]): item for item in items}
    sets_by_id = {(game_set.get("set_id") or game_set.get("id")): game_set for game_set in sets}

    for scraped_set in scraped_sets:
        if not scraped_set:
            continue
        existing_set = sets_by_id.get(scraped_set["set_id"])
        if existing_set:
            existing_set.setdefault("description", scraped_set["description"])
            if scraped_set["description"]:
                existing_set["description"] = scraped_set["description"]
            existing_set["max_items"] = scraped_set["max_items"]
            existing_set["source_url"] = scraped_set["source_url"]
            if not existing_set.get("bonuses"):
                existing_set["bonuses"] = scraped_set["bonuses"]
            else:
                existing_bonus_map = {
                    int(bonus.get("required_items", 0)): bonus
                    for bonus in existing_set["bonuses"]
                }
                for scraped_bonus in scraped_set["bonuses"]:
                    required_items = int(scraped_bonus.get("required_items", 0))
                    existing_bonus = existing_bonus_map.get(required_items)
                    if existing_bonus is None:
                        existing_set["bonuses"].append(scraped_bonus)
                        continue
                    if scraped_bonus.get("description") and not existing_bonus.get("description"):
                        existing_bonus["description"] = scraped_bonus["description"]
                    existing_bonus.setdefault("effects", [])
                    if not existing_bonus["effects"] and scraped_bonus.get("effects"):
                        existing_bonus["effects"] = scraped_bonus["effects"]
            continue

        sets.append(scraped_set)
        sets_by_id[scraped_set["set_id"]] = scraped_set

    for scraped_item in scraped_items:
        if not scraped_item:
            continue
        existing_item = items_by_name.get(normalize_key(scraped_item["site_name"]))
        if existing_item:
            existing_item["type"] = scraped_item["type"]
            existing_item["rarity"] = scraped_item["rarity"]
            if scraped_item["set_id"]:
                existing_item["set_id"] = scraped_item["set_id"]
            if scraped_item["base_stat_hint"]:
                existing_item["base_stat_hint"] = scraped_item["base_stat_hint"]
            existing_item["source_url"] = scraped_item["source_url"]
            continue

        items.append(
            {
                "id": normalize_id(scraped_item["site_slug"]),
                "name": scraped_item["site_name"],
                "type": scraped_item["type"],
                "rarity": scraped_item["rarity"],
                "set_id": scraped_item["set_id"],
                "base_stat_hint": scraped_item["base_stat_hint"],
                "source_url": scraped_item["source_url"],
            }
        )

    existing_data["items"] = sorted(items, key=lambda item: (item.get("type", ""), item.get("rarity", ""), item["name"]))
    existing_data["sets"] = sorted(sets, key=lambda game_set: game_set["name"])
    return existing_data


def merge_mods(existing_mods: dict[str, list[dict[str, Any]]], scraped_mods: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    for key in ("mod_helmet", "mod_mask", "mod_top", "mod_gloves", "mod_pants", "mod_boots", "mod_weapon"):
        existing_mods.setdefault(key, [])

    lookup = {
        mod_key: {normalize_key(mod["name"]): mod for mod in mod_list}
        for mod_key, mod_list in existing_mods.items()
        if isinstance(mod_list, list)
    }

    for mod in scraped_mods:
        if not mod:
            continue
        mod_key = mod["mod_key"]
        current = lookup.setdefault(mod_key, {})
        existing = current.get(normalize_key(mod["name"]))
        if existing:
            existing.setdefault("description", mod["description"])
            if mod["description"]:
                existing["description"] = mod["description"]
            existing.setdefault("effects", [])
            if not existing["effects"] and mod["effects"]:
                existing["effects"] = mod["effects"]
            existing["source_url"] = mod["source_url"]
            existing["slot"] = mod["slot"]
            existing["rarity"] = mod["rarity"]
            continue

        new_entry = {
            "name": mod["name"],
            "description": mod["description"],
            "effects": mod["effects"],
            "slot": mod["slot"],
            "rarity": mod["rarity"],
            "source_url": mod["source_url"],
        }
        existing_mods[mod_key].append(new_entry)
        current[normalize_key(new_entry["name"])] = new_entry

    for mod_key, mod_list in existing_mods.items():
        if isinstance(mod_list, list):
            mod_list.sort(key=lambda mod: mod["name"])
    return existing_mods


def run_import(cache_dir: Path, workers: int = 8) -> dict[str, Any]:
    sitemap_urls = {kind: load_sitemap_urls(url, cache_dir) for kind, url in SITEMAPS.items()}
    scraped: dict[str, list[dict[str, Any]]] = {kind: [] for kind in SITEMAPS}
    tasks: list[tuple[str, str]] = [
        (kind, url)
        for kind, urls in sitemap_urls.items()
        for url in urls
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_map = {
            executor.submit(fetch_and_parse, kind, url, cache_dir): (kind, url)
            for kind, url in tasks
        }
        for future in concurrent.futures.as_completed(future_map):
            kind, _url = future_map[future]
            result = future.result()
            if result is not None:
                scraped[kind].append(result)

    weapon_path = CALC_JSON_DIR / "weapon_list.json"
    items_sets_path = CALC_JSON_DIR / "items_and_sets.json"
    mods_path = CALC_JSON_DIR / "mods_config.json"

    weapons_data = json.loads(weapon_path.read_text(encoding="utf-8"))
    items_sets_data = json.loads(items_sets_path.read_text(encoding="utf-8"))
    mods_data = json.loads(mods_path.read_text(encoding="utf-8"))

    merged_weapons = merge_weapons(weapons_data.get("weapons", []), scraped["weapons"])
    merged_items_sets = merge_items_and_sets(items_sets_data, scraped["armor"], scraped["armor_sets"])
    merged_mods = merge_mods(mods_data, scraped["mods"])

    return {
        "weapons": {"weapons": merged_weapons},
        "items_and_sets": merged_items_sets,
        "mods": merged_mods,
        "stats": {
            "scraped_weapon_pages": len(scraped["weapons"]),
            "scraped_armor_pages": len(scraped["armor"]),
            "scraped_armor_set_pages": len(scraped["armor_sets"]),
            "scraped_mod_pages": len(scraped["mods"]),
            "merged_weapons": len(merged_weapons),
            "merged_items": len(merged_items_sets.get("items", [])),
            "merged_sets": len(merged_items_sets.get("sets", [])),
            "merged_mods": sum(len(entries) for entries in merged_mods.values() if isinstance(entries, list)),
        },
    }


def write_outputs(result: dict[str, Any]) -> None:
    (CALC_JSON_DIR / "weapon_list.json").write_text(
        json.dumps(result["weapons"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (CALC_JSON_DIR / "items_and_sets.json").write_text(
        json.dumps(result["items_and_sets"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (CALC_JSON_DIR / "mods_config.json").write_text(
        json.dumps(result["mods"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR, help="HTTP cache directory")
    parser.add_argument("--workers", type=int, default=8, help="Parallel page fetch workers")
    parser.add_argument("--write", action="store_true", help="Write merged JSON files back into the repo")
    parser.add_argument("--summary-only", action="store_true", help="Only print summary without JSON preview")
    args = parser.parse_args()

    result = run_import(cache_dir=args.cache_dir, workers=max(1, args.workers))
    if args.write:
        write_outputs(result)

    print(json.dumps(result["stats"], ensure_ascii=False, indent=2))
    if not args.summary_only:
        preview = {
            "weapon_sample": [weapon["name"] for weapon in result["weapons"]["weapons"][:5]],
            "item_sample": [item["name"] for item in result["items_and_sets"]["items"][:5]],
            "set_sample": [game_set["name"] for game_set in result["items_and_sets"]["sets"][:5]],
            "mod_sample": [mod["name"] for mod in result["mods"].get("mod_weapon", [])[:5]],
        }
        print(json.dumps(preview, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
