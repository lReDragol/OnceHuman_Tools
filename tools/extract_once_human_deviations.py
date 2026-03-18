#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.extract_once_human_mod_attributes import (
    read_bindict_strings,
    read_bindict_top_level_records,
    scan_bindict_record,
)


DEVIATION_ID_RE = re.compile(r"^9900\d+$")
TID_SUFFIX_RE = re.compile(r"_\$S@TIDS\$_[^|]+\|.*$")
NUMERIC_FORMULA_RE = re.compile(r"^[0-9.+\-*/()deviation_degree ]+$")

COMBAT_NAME_ALIASES = {
    "黑猫": "凝视的黑猫",
}

DEVIATION_ALIAS_MAP = {
    "低语孤狼": ["Lonewolf's Whisper"],
    "远归之蝶": ["Butterfly's Emissary"],
    "冬灵": ["Snowsprite"],
    "红龙": ["Pyro Dino"],
    "永恒烈阳": ["Invincible Sun"],
    "迷你黄衣": ["Mini Feaster"],
    "破碎少女": ["Shattered Maiden"],
    "恶咒娃娃": ["Voodoo Doll"],
}

DEVIATION_LOCALIZATION_OVERRIDES = {
    "元素小子": {
        "ru": {"name": "Элементаль"},
        "en": {"name": "Elemental Sprite"},
    },
    "冬灵": {
        "ru": {"name": "Снежный спрайт"},
        "en": {"name": "Snowsprite"},
    },
    "低语孤狼": {
        "ru": {"name": "Шёпот одинокого волка"},
        "en": {"name": "Lonewolf's Whisper"},
    },
    "凝视的黑猫": {
        "ru": {"name": "Глядящий черный кот"},
        "en": {"name": "Gazing Black Cat"},
    },
    "匠师之手": {
        "ru": {"name": "Рука мастера"},
        "en": {"name": "Artisan's Hand"},
    },
    "发条青蛙": {
        "ru": {"name": "Часовая лягушка"},
        "en": {"name": "Clockwork Frog"},
    },
    "守夜灯": {
        "ru": {"name": "Ночной фонарь"},
        "en": {"name": "Nightlight"},
    },
    "快照": {
        "ru": {"name": "ZapCam"},
        "en": {"name": "ZapCam"},
    },
    "恶咒娃娃": {
        "ru": {"name": "Кукла вуду"},
        "en": {"name": "Voodoo Doll"},
    },
    "恶臭球根": {
        "ru": {"name": "Вонючая луковица"},
        "en": {"name": "Stink Bulb"},
    },
    "捕梦网": {
        "ru": {"name": "Ловец снов"},
        "en": {"name": "Dreamcatcher"},
    },
    "气球狗": {
        "ru": {"name": "Собака-шарик"},
        "en": {"name": "Balloon Dog"},
    },
    "活性凝胶": {
        "ru": {"name": "Живой гель"},
        "en": {"name": "Living Gel"},
    },
    "联合体": {
        "ru": {"name": "Коллектив"},
        "en": {"name": "Collective"},
    },
    "胡桃夹子": {
        "ru": {"name": "Щелкунчик"},
        "en": {"name": "Nutcracker"},
    },
    "蜂团团": {
        "ru": {"name": "Жужжащий рой"},
        "en": {"name": "Buzzy Bee"},
    },
    "蝶之梦": {
        "ru": {"name": "Сон бабочки"},
        "en": {"name": "Butterfly's Dream"},
    },
    "迷你奇点": {
        "ru": {"name": "Мини-сингулярность"},
        "en": {"name": "Mini Singularity"},
    },
    "迷你黄衣": {
        "ru": {"name": "Мини-Фистер"},
        "en": {"name": "Mini Feaster"},
    },
    "量子蜗牛": {
        "ru": {"name": "Квантовая улитка"},
        "en": {"name": "Quantum Snail"},
    },
    "门扉": {
        "ru": {"name": "Врата"},
        "en": {"name": "Gate"},
    },
    "雨人": {
        "ru": {"name": "Человек дождя"},
        "en": {"name": "Rain Man"},
    },
    "极寒水母": {
        "ru": {"name": "Полярная медуза"},
        "en": {"name": "Polar Jelly"},
    },
    "荣枯种子": {
        "ru": {"name": "Семя жатвы"},
        "en": {"name": "Harvest Seed"},
    },
    "青龙": {
        "ru": {"name": "Лазурный дракон"},
        "en": {"name": "Azure Dragon"},
    },
    "鲸狗": {
        "ru": {"name": "Китощенок"},
        "en": {"name": "Whalepup"},
    },
    "工号H37": {
        "ru": {"name": "Субъект H37"},
        "en": {"name": "Unit H37"},
    },
}

SKILL_LOCALIZATION_OVERRIDES = {
    "火焰弹": {
        "ru": {"name": "Огненная пуля"},
        "en": {"name": "Flame Bullet"},
    },
    "爆炎弹": {
        "ru": {"name": "Зажигательный снаряд"},
        "en": {"name": "Incendiary Bullet"},
    },
    "雷击": {
        "ru": {"name": "Удар молнии"},
        "en": {"name": "Lightning Strike"},
    },
    "高速连射": {
        "ru": {"name": "Быстрая очередь"},
        "en": {"name": "Rapid Fire"},
    },
    "魔法火焰飞行": {
        "ru": {"name": "Огненный полет"},
        "en": {"name": "Flame Flight"},
    },
    "震荡跃迁": {
        "ru": {
            "name": "Телепорт-удар",
            "description": "Телепортируется к цели, наносит физический урон и отбрасывает ее.",
        },
        "en": {
            "name": "Teleport Strike",
            "description": "Teleports to the target, deals P.ATK DMG, and knocks it back.",
        },
    },
    "自我疗愈": {
        "ru": {"name": "Самоисцеление"},
        "en": {"name": "Self-Healing"},
    },
    "冰霜漩涡": {
        "ru": {"name": "Морозный вихрь"},
        "en": {"name": "Frost Vortex"},
    },
}

KNOWN_COMBAT_DEVIATION_NAMES = {
    "低语孤狼",
    "冬灵",
    "凝视的黑猫",
    "匠师之手",
    "发条青蛙",
    "唤生灵",
    "姜饼屋",
    "守夜灯",
    "异维大猫",
    "快照",
    "恶咒娃娃",
    "恶臭球根",
    "愿望先生",
    "愿望箱",
    "捕梦网",
    "杜宾",
    "极寒水母",
    "气球狗",
    "永恒烈阳",
    "活性凝胶",
    "焦油布丁",
    "熊医生",
    "球状闪电",
    "电蝾螈",
    "皆斩",
    "破碎少女",
    "空之子",
    "红龙",
    "联合体",
    "荣枯种子",
    "蜂团团",
    "远归之蝶",
    "迪斯科球",
    "迷你奇点",
    "迷你黄衣",
    "门扉",
    "雨人",
    "青龙",
    "鲸狗",
    "黑医",
}

ME_CODE_RE = re.compile(r"(me\d{2,})", re.IGNORECASE)
PERCENT_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)%")
DURATION_SECONDS_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)秒")
EXACT_PERCENT_RE = re.compile(r"#\[k=b8\]([0-9]+(?:\.[0-9]+)?)%#l")
METER_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)米")
PLACEHOLDER_RE = re.compile(r"\{\d+\}")
NUMBER_RE = re.compile(r"[0-9]+(?:\.[0-9]+)?")
CJK_RE = re.compile(r"[\u3400-\u9FFF]")
CYRILLIC_RE = re.compile(r"[А-Яа-яЁё]")
TID_TOKEN_RE = re.compile(r"_\$S@TIDS\$_[^|]+\|.*$")
TRANSLATION_LOOKAHEAD = 8
DEVIATION_RUNTIME_HINTS = ("战斗型", "战斗表")


def clean_tid_text(text: str) -> str:
    return TID_SUFFIX_RE.sub("", text or "").strip()


def has_cjk(text: str) -> bool:
    return bool(CJK_RE.search(text or ""))


def has_cyrillic(text: str) -> bool:
    return bool(CYRILLIC_RE.search(text or ""))


def looks_like_asset_or_code(text: str) -> bool:
    lowered = str(text or "").casefold()
    return any(
        marker in lowered
        for marker in (
            ".gim",
            ".animation",
            ".png",
            ".pvr",
            "\\",
            "/",
            "player.gim",
            "boss_icon_",
            "icon_containments_",
            "containments_cbt2_",
        )
    )


def clean_translation_candidate(text: str) -> str:
    cleaned = clean_tid_text(text)
    cleaned = TID_TOKEN_RE.sub("", cleaned)
    return cleaned.strip()


def is_name_like_text(text: str) -> bool:
    cleaned = clean_tid_text(text)
    return bool(
        cleaned
        and len(cleaned) <= 20
        and not any(marker in cleaned for marker in ("\n", "。", "，", "：", ":", "%", "{", "}"))
    )


def score_translation_candidate(source_text: str, candidate_text: str, distance: int, language: str) -> float:
    candidate = clean_translation_candidate(candidate_text)
    source = clean_translation_candidate(source_text)
    if not source or not candidate or candidate == source:
        return float("-inf")
    if has_cjk(candidate) or looks_like_asset_or_code(candidate):
        return float("-inf")

    is_name_like = is_name_like_text(source)
    score = 0.0
    if language == "ru":
        if has_cyrillic(candidate):
            score += 20.0
        elif re.search(r"[A-Za-z]", candidate):
            score += 6.0
        else:
            score -= 4.0
    else:
        if re.search(r"[A-Za-z]", candidate):
            score += 18.0
        else:
            score -= 6.0

    score -= distance * (1.3 if is_name_like else 2.4)
    if is_name_like:
        expected_length = min(max(len(source) * 4, 6), 28)
        score -= abs(len(candidate) - expected_length) * 0.45
        if len(candidate) > 42:
            score -= 12.0
        if candidate[:1].isupper():
            score += 2.0
    else:
        source_placeholders = PLACEHOLDER_RE.findall(source)
        candidate_placeholders = PLACEHOLDER_RE.findall(candidate)
        if source_placeholders == candidate_placeholders and source_placeholders:
            score += 12.0
        else:
            score -= abs(len(source_placeholders) - len(candidate_placeholders)) * 5.0
        if source.count("\n") == candidate.count("\n"):
            score += 2.0
        if source.count("%") == candidate.count("%"):
            score += 2.0
        score -= abs(len(candidate) - len(source)) / max(30.0, float(len(source) or 1))

    source_numbers = NUMBER_RE.findall(source)
    candidate_numbers = NUMBER_RE.findall(candidate)
    score -= abs(len(source_numbers) - len(candidate_numbers)) * 1.5
    score -= abs(math.log((len(candidate) + 1) / (len(source) + 1))) * (1.6 if is_name_like else 0.8)
    return score


def choose_translation(strings: list[str], source_text: str, positions: list[int], language: str) -> str:
    best_score = float("-inf")
    best_value = ""
    for index in positions:
        for distance in range(1, TRANSLATION_LOOKAHEAD + 1):
            probe_index = index + distance
            if probe_index >= len(strings):
                break
            candidate = strings[probe_index]
            score = score_translation_candidate(source_text, candidate, distance, language)
            if score > best_score:
                best_score = score
                best_value = clean_translation_candidate(candidate)
    threshold = 4.0 if is_name_like_text(source_text) else 7.5
    return best_value if best_score >= threshold else ""


def build_translation_map(translate_path: Path, targets: set[str], language: str) -> dict[str, str]:
    strings = read_bindict_strings(translate_path)
    positions: dict[str, list[int]] = defaultdict(list)
    normalized_targets = {clean_tid_text(text) for text in targets if has_cjk(clean_tid_text(text))}
    for index, value in enumerate(strings):
        cleaned = clean_translation_candidate(value)
        if cleaned in normalized_targets:
            positions[cleaned].append(index)

    translations: dict[str, str] = {}
    for target in sorted(normalized_targets):
        chosen = choose_translation(strings, target, positions.get(target, []), language)
        if chosen:
            translations[target] = chosen
    return translations


def nearest_match(strings: list[str], index: int, predicate, radius: int = 10) -> str | None:
    best_value = None
    best_distance = None
    for offset in range(max(0, index - radius), min(len(strings), index + radius + 1)):
        value = strings[offset]
        if not predicate(value):
            continue
        distance = abs(offset - index)
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_value = value
    return best_value


def extract_asset_map(strings: list[str]) -> dict[str, dict[str, str]]:
    asset_map: dict[str, dict[str, str]] = {}
    for index, value in enumerate(strings):
        if not DEVIATION_ID_RE.fullmatch(value):
            continue
        asset_map[value] = {
            "icon_asset": nearest_match(strings, index, lambda entry: entry.startswith("icon_containments_cbt2_")) or "",
            "boss_icon_asset": nearest_match(strings, index, lambda entry: entry.startswith("boss_icon_") or entry.startswith("npc_icon_")) or "",
            "model_path": nearest_match(strings, index, lambda entry: entry.endswith(".gim")) or "",
            "animation_path": nearest_match(strings, index, lambda entry: entry.endswith(".animation")) or "",
        }
    return asset_map


def extract_me_code(*candidates: str | None) -> str:
    for candidate in candidates:
        match = ME_CODE_RE.search(candidate or "")
        if match:
            return match.group(1).lower()
    return ""


def extract_book_deviations(book_path: Path) -> list[dict[str, Any]]:
    strings, data, records = read_bindict_top_level_records(book_path)
    asset_map = extract_asset_map(strings)
    deviations: dict[str, dict[str, Any]] = {}

    for index, (_, offset) in enumerate(records):
        rel = offset - 4
        next_rel = records[index + 1][1] - 4 if index + 1 < len(records) else len(data)
        arrays, refs = scan_bindict_record(data[rel:next_rel], strings)

        deviation_ids: list[str] = []
        for subtype, values in arrays:
            if subtype != 5:
                continue
            for value in values:
                if isinstance(value, int) and 0 <= value < len(strings):
                    candidate = strings[value]
                    if DEVIATION_ID_RE.fullmatch(candidate):
                        deviation_ids.append(candidate)

        if not deviation_ids:
            continue

        cleaned_refs = [clean_tid_text(entry) for entry in refs if entry]
        name = next(
            (
                entry
                for entry in cleaned_refs
                if entry
                and len(entry) <= 16
                and "\n" not in entry
                and "·" not in entry
                and "战斗表" not in entry
            ),
            "",
        )
        if not name:
            continue
        description = next(
            (
                entry
                for entry in cleaned_refs
                if entry
                and entry != name
                and ("\n" in entry or len(entry) > 24)
            ),
            "",
        )

        deviation_id = deviation_ids[0]
        entry = deviations.setdefault(
            deviation_id,
            {
                "id": deviation_id,
                "name": name,
                "description": description,
                "book_record_index": index,
            },
        )
        if description and not entry.get("description"):
            entry["description"] = description
        entry.update({key: value for key, value in asset_map.get(deviation_id, {}).items() if value})
        entry["me_code"] = extract_me_code(
            entry.get("icon_asset"),
            entry.get("boss_icon_asset"),
            entry.get("model_path"),
            entry.get("animation_path"),
        )
        if entry.get("me_code") and not entry.get("icon_asset"):
            entry["icon_asset"] = f"icon_containments_cbt2_sco_{entry['me_code']}.png"
        aliases = DEVIATION_ALIAS_MAP.get(entry["name"], [])
        if aliases:
            entry["aliases"] = aliases

    return sorted(deviations.values(), key=lambda item: item["name"])


def extract_deviation_base_classification(base_path: Path, known_names: set[str]) -> dict[str, dict[str, Any]]:
    strings, data, records = read_bindict_top_level_records(base_path)
    results: dict[str, dict[str, Any]] = {}
    for index, (_, offset) in enumerate(records):
        rel = offset - 4
        next_rel = records[index + 1][1] - 4 if index + 1 < len(records) else len(data)
        _, refs = scan_bindict_record(data[rel:next_rel], strings)
        cleaned_refs = [clean_tid_text(entry) for entry in refs if entry]
        ref_set = set(cleaned_refs)
        matched_names = sorted(ref_set.intersection(known_names), key=len, reverse=True)
        if not matched_names:
            continue
        matched_name = matched_names[0]
        is_combat = any(any(hint in ref for hint in DEVIATION_RUNTIME_HINTS) for ref in cleaned_refs)
        role_hints = [
            ref
            for ref in cleaned_refs
            if any(marker in ref for marker in ("战斗", "采集", "伐木", "采矿", "种植", "领地", "制造"))
        ][:8]
        current = results.get(matched_name)
        if current and current.get("is_combat") and not is_combat:
            continue
        results[matched_name] = {
            "record_index": index,
            "is_combat": is_combat,
            "role_hints": role_hints,
        }
    return results


def collect_localizable_texts(deviations: list[dict[str, Any]]) -> set[str]:
    texts: set[str] = set()
    for deviation in deviations:
        for key in ("name", "description"):
            value = clean_tid_text(str(deviation.get(key, "") or ""))
            if has_cjk(value):
                texts.add(value)
        for skill in deviation.get("skill_entries") or deviation.get("preview_skills") or []:
            for key in ("name", "description", "preview_description", "exact_description"):
                value = clean_tid_text(str(skill.get(key, "") or ""))
                if has_cjk(value):
                    texts.add(value)
            for variant in skill.get("exact_variants") or []:
                for key in ("name", "description"):
                    value = clean_tid_text(str(variant.get(key, "") or ""))
                    if has_cjk(value):
                        texts.add(value)
    return texts


def select_localized_value(
    translation_maps: dict[str, dict[str, str]],
    text: str,
    language: str,
    *,
    fallback_values: list[str] | None = None,
) -> str:
    cleaned = clean_tid_text(text)
    if not cleaned:
        return ""
    value = translation_maps.get(language, {}).get(cleaned, "").strip()
    if value:
        return value
    fallback_language = "en" if language != "en" else "ru"
    value = translation_maps.get(fallback_language, {}).get(cleaned, "").strip()
    if value:
        return value
    for fallback in fallback_values or []:
        fallback = str(fallback or "").strip()
        if fallback:
            return fallback
    return cleaned


def apply_localization_bundle(
    payload: dict[str, Any],
    translation_maps: dict[str, dict[str, str]],
    field_names: tuple[str, ...],
    *,
    fallback_values_by_field: dict[str, list[str]] | None = None,
) -> None:
    localization = payload.setdefault("localization", {})
    for language in ("ru", "en"):
        localized_payload = localization.setdefault(language, {})
        for field_name in field_names:
            fallback_values = (fallback_values_by_field or {}).get(field_name, [])
            localized_payload[field_name] = select_localized_value(
                translation_maps,
                str(payload.get(field_name, "") or ""),
                language,
                fallback_values=fallback_values,
            )
    for field_name in field_names:
        mirrored_localized = payload.setdefault(f"{field_name}_localized", {})
        if not isinstance(mirrored_localized, dict):
            mirrored_localized = {}
            payload[f"{field_name}_localized"] = mirrored_localized
        for language in ("ru", "en"):
            localized_value = str((localization.get(language) or {}).get(field_name) or "").strip()
            if localized_value:
                mirrored_localized[language] = localized_value


def apply_override_bundle(payload: dict[str, Any], overrides: dict[str, dict[str, dict[str, str]]], key_name: str = "name") -> None:
    payload_key = str(payload.get(key_name, "") or "").strip()
    if not payload_key:
        return
    for language, values in (overrides.get(payload_key) or {}).items():
        localized_payload = payload.setdefault("localization", {}).setdefault(language, {})
        for field_name, field_value in values.items():
            localized_payload[field_name] = field_value
            mirrored_localized = payload.setdefault(f"{field_name}_localized", {})
            if isinstance(mirrored_localized, dict):
                mirrored_localized[language] = field_value


def apply_deviation_localization(
    deviations: list[dict[str, Any]],
    translation_maps: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    for deviation in deviations:
        fallback_name_values = []
        aliases = [str(alias or "").strip() for alias in deviation.get("aliases") or [] if str(alias or "").strip()]
        if aliases:
            fallback_name_values.extend(aliases)
        apply_localization_bundle(
            deviation,
            translation_maps,
            ("name", "description"),
            fallback_values_by_field={"name": fallback_name_values},
        )
        apply_override_bundle(deviation, DEVIATION_LOCALIZATION_OVERRIDES)
        for skill in deviation.get("preview_skills") or []:
            apply_localization_bundle(skill, translation_maps, ("name", "description"))
            apply_override_bundle(skill, SKILL_LOCALIZATION_OVERRIDES)
        for skill in deviation.get("skill_entries") or []:
            apply_localization_bundle(skill, translation_maps, ("name", "description", "preview_description", "exact_description"))
            apply_override_bundle(skill, SKILL_LOCALIZATION_OVERRIDES)
            for variant in skill.get("exact_variants") or []:
                apply_localization_bundle(variant, translation_maps, ("name", "description"))
                apply_override_bundle(variant, SKILL_LOCALIZATION_OVERRIDES)
        english_name = str((deviation.get("localization") or {}).get("en", {}).get("name") or "").strip()
        if english_name and english_name not in deviation.get("aliases", []):
            deviation.setdefault("aliases", []).append(english_name)
    return deviations


def guess_combat_name(texts: list[str]) -> str | None:
    for text in texts:
        match = re.search(r"指定(.+?)的攻击目标", text)
        if match:
            return COMBAT_NAME_ALIASES.get(match.group(1), match.group(1))
        match = re.search(r"指定(.+?)生效目标", text)
        if match:
            return COMBAT_NAME_ALIASES.get(match.group(1), match.group(1))
        match = re.search(r"(.+?)形态", text)
        if match:
            return COMBAT_NAME_ALIASES.get(match.group(1), match.group(1))
    for text in texts:
        cleaned = clean_tid_text(text)
        if cleaned in COMBAT_NAME_ALIASES:
            return COMBAT_NAME_ALIASES[cleaned]
    return None


def detect_behavior(name: str | None, description: str) -> str:
    desc = description or ""
    normalized_name = name or ""
    if normalized_name == "凝视的黑猫" or "手持近战武器" in desc:
        return "melee_companion"
    if normalized_name == "冬灵" or "冰晶被子弹命中后破碎" in desc:
        return "ice_crystal_orbit"
    if normalized_name == "远归之蝶" or "弱点部位" in desc:
        return "mark_weakspot"
    if normalized_name == "低语孤狼" or "枪械伤害" in desc:
        return "weapon_vulnerability"
    if normalized_name == "永恒烈阳" or "灼烧时，永恒烈阳会获得一层灼烧" in desc:
        return "burn_bombard"
    if normalized_name == "红龙" or "额外造成一次燃爆" in desc:
        return "burn_vulnerability"
    if normalized_name == "迷你黄衣" or "触手拍击" in desc:
        return "tentacle_status"
    if normalized_name == "破碎少女" or "爆炸伤害增加" in desc:
        return "explosion_vulnerability"
    if normalized_name == "电蝾螈" or "电涌伤害提升" in desc:
        return "shock_vulnerability"
    if normalized_name == "迷你奇点" or "子弹吸收" in desc:
        return "ammo_refill"
    if normalized_name == "恶咒娃娃" or "分担伤害" in desc:
        return "damage_share"
    if normalized_name in {"皆斩"} or "瞬移至目标身边发动近战攻击" in desc:
        return "melee_blink"
    if "复活附近倒下的玩家" in desc or "定期治疗附近受到伤害的玩家" in desc:
        return "healing_support"
    if normalized_name in {"鲸狗", "唤生灵"} or "后续受到的枪械伤害提升" in desc:
        return "weapon_vulnerability"
    return "generic"


def map_placeholder_values(behavior: str, values: list[str]) -> dict[str, str]:
    if behavior == "ice_crystal_orbit":
        keys = ["interval_seconds_formula", "frost_damage_percent_formula", "frost_bonus_percent_formula"]
    elif behavior == "mark_weakspot":
        keys = ["weakspot_bonus_percent_formula", "duration_seconds_formula"]
    elif behavior == "weapon_vulnerability":
        keys = ["weapon_bonus_percent_formula", "extra_vulnerability_percent_formula"]
    elif behavior == "burn_bombard":
        keys = [
            "interval_seconds_formula",
            "burn_damage_percent_formula",
            "burn_trigger_chance_formula",
            "stack_damage_bonus_formula",
            "burn_bonus_percent_formula",
        ]
    elif behavior == "tentacle_status":
        keys = [
            "interval_seconds_formula",
            "tentacles_per_attack_formula",
            "stacks_per_attack_formula",
            "status_damage_bonus_formula",
            "status_damage_bonus_cap_formula",
        ]
    elif behavior == "explosion_vulnerability":
        keys = ["explosion_bonus_percent_formula"]
    elif behavior == "shock_vulnerability":
        keys = ["shock_bonus_percent_formula"]
    else:
        keys = []
    return {key: value for key, value in zip(keys, values)}


def extract_placeholder_values(arrays: list[tuple[int, list[int | float]]], strings: list[str]) -> list[str]:
    results: list[str] = []
    for subtype, values in arrays:
        if subtype != 5:
            continue
        for value in values:
            if not isinstance(value, int) or not (0 <= value < len(strings)):
                continue
            candidate = strings[value]
            if NUMERIC_FORMULA_RE.fullmatch(candidate):
                results.append(candidate)
    return results


def extract_combat_profiles(combat_path: Path) -> dict[str, dict[str, Any]]:
    strings, data, records = read_bindict_top_level_records(combat_path)
    profiles_by_name: dict[str, dict[str, Any]] = {}

    for index, (record_key, offset) in enumerate(records):
        rel = offset - 4
        next_rel = records[index + 1][1] - 4 if index + 1 < len(records) else len(data)
        arrays, refs = scan_bindict_record(data[rel:next_rel], strings)
        cleaned_refs = [clean_tid_text(entry) for entry in refs if entry]
        name = guess_combat_name(cleaned_refs)
        if not name:
            continue
        description = next(
            (
                entry
                for entry in cleaned_refs
                if entry
                and ("攻击" in entry or "恢复" in entry or "提升" in entry or "伤害" in entry or "生成" in entry)
                and "指定" not in entry
            ),
            "",
        )
        behavior = detect_behavior(name, description)
        placeholder_values = extract_placeholder_values(arrays, strings)
        profile = {
            "combat_record_key": str(record_key),
            "name": name,
            "behavior": behavior,
            "description": description,
            "parameter_formulas": map_placeholder_values(behavior, placeholder_values),
            "supported_runtime": behavior in {
                "ice_crystal_orbit",
                "mark_weakspot",
                "weapon_vulnerability",
                "burn_bombard",
                "burn_vulnerability",
                "tentacle_status",
                "explosion_vulnerability",
                "shock_vulnerability",
                "ammo_refill",
                "damage_share",
                "melee_blink",
                "melee_companion",
                "healing_support",
            },
        }

        existing = profiles_by_name.get(name)
        current_score = len(profile["parameter_formulas"]) + (4 if profile["supported_runtime"] else 0)
        existing_score = -1
        if existing:
            existing_score = len(existing.get("parameter_formulas", {})) + (4 if existing.get("supported_runtime") else 0)
        if existing is None or current_score > existing_score:
            profiles_by_name[name] = profile

    return profiles_by_name


def clean_preview_name(text: str) -> str:
    text = clean_tid_text(text)
    return text.replace("·", " ").strip()


def parse_preview_skills(preview_refs: list[str]) -> list[dict[str, Any]]:
    cleaned_refs = [clean_preview_name(entry) for entry in preview_refs if entry]
    if not cleaned_refs:
        return []

    names = [
        entry for entry in cleaned_refs
        if entry
        and len(entry) <= 28
        and not any(mark in entry for mark in ("\n", "。", "，", "："))
    ]
    descriptions = [
        entry for entry in cleaned_refs
        if entry
        and (
            len(entry) > 28
            or any(mark in entry for mark in ("\n", "。", "，", "："))
        )
    ]

    if not names and len(cleaned_refs) >= 2:
        split_index = len(cleaned_refs) // 2
        names = cleaned_refs[:split_index]
        descriptions = cleaned_refs[split_index:]

    preview_skills: list[dict[str, Any]] = []
    for name, description in zip(names, descriptions):
        if not name or not description:
            continue
        coefficients = [float(value) for value in PERCENT_RE.findall(description)]
        durations = [float(value) for value in DURATION_SECONDS_RE.findall(description)]
        preview_skills.append(
            {
                "name": name,
                "description": description,
                "coefficients_percent": coefficients,
                "durations_seconds": durations,
            }
        )
    return preview_skills


def extract_preview_skill_catalog(preview_path: Path) -> dict[str, list[dict[str, Any]]]:
    strings, data, records = read_bindict_top_level_records(preview_path)
    catalog: dict[str, list[dict[str, Any]]] = {}
    for index, (record_key, offset) in enumerate(records):
        rel = offset - 4
        next_rel = records[index + 1][1] - 4 if index + 1 < len(records) else len(data)
        _, refs = scan_bindict_record(data[rel:next_rel], strings)
        preview_skills = parse_preview_skills(refs)
        if preview_skills:
            catalog[str(record_key)] = preview_skills
    return catalog


def extract_exact_skill_catalog(skill_path: Path) -> dict[str, list[dict[str, Any]]]:
    strings, data, records = read_bindict_top_level_records(skill_path)
    catalog: dict[str, list[dict[str, Any]]] = {}
    for index, (record_key, offset) in enumerate(records):
        rel = offset - 4
        next_rel = records[index + 1][1] - 4 if index + 1 < len(records) else len(data)
        _, refs = scan_bindict_record(data[rel:next_rel], strings)
        cleaned_refs = [clean_preview_name(entry) for entry in refs if entry]
        if len(cleaned_refs) < 2:
            continue
        description = next(
            (
                entry
                for entry in cleaned_refs
                if entry
                and (
                    len(entry) > 18
                    or any(mark in entry for mark in ("\n", "。", "，", "："))
                )
            ),
            "",
        )
        name = next(
            (
                entry
                for entry in cleaned_refs
                if entry
                and entry != description
                and len(entry) <= 28
                and not any(mark in entry for mark in ("\n", "。", "，", "："))
            ),
            "",
        )
        if not name or not description:
            continue
        coefficients = [
            float(value)
            for value in (
                EXACT_PERCENT_RE.findall(description)
                or PERCENT_RE.findall(description)
            )
        ]
        durations = [float(value) for value in DURATION_SECONDS_RE.findall(description)]
        ranges = [float(value) for value in METER_RE.findall(description)]
        entry = {
            "record_key": str(record_key),
            "name": name,
            "description": description,
            "coefficients_percent": coefficients,
            "durations_seconds": durations,
            "ranges_meters": ranges,
            "max_coefficient_percent": max(coefficients) if coefficients else 0.0,
        }
        catalog.setdefault(name, []).append(entry)

    for entries in catalog.values():
        entries.sort(
            key=lambda item: (
                item.get("max_coefficient_percent", 0.0),
                len(item.get("durations_seconds") or []),
                len(item.get("description") or ""),
            ),
            reverse=True,
        )
    return catalog


def merge_skill_catalog(
    preview_skills: list[dict[str, Any]],
    exact_skill_catalog: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for preview_skill in preview_skills:
        skill_name = clean_preview_name(preview_skill.get("name", ""))
        exact_variants = copy_skill_variants(exact_skill_catalog.get(skill_name, []))
        primary_variant = exact_variants[0] if exact_variants else {}
        coefficients = preview_skill.get("coefficients_percent") or primary_variant.get("coefficients_percent") or []
        durations = preview_skill.get("durations_seconds") or primary_variant.get("durations_seconds") or []
        merged.append(
            {
                "name": skill_name,
                "description": preview_skill.get("description") or primary_variant.get("description", ""),
                "preview_description": preview_skill.get("description", ""),
                "exact_description": primary_variant.get("description", ""),
                "coefficients_percent": coefficients,
                "durations_seconds": durations,
                "exact_variants": exact_variants,
                "exact_record_keys": [variant.get("record_key") for variant in exact_variants],
            }
        )
    return merged


def copy_skill_variants(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "record_key": entry.get("record_key"),
            "name": entry.get("name"),
            "description": entry.get("description"),
            "coefficients_percent": list(entry.get("coefficients_percent") or []),
            "durations_seconds": list(entry.get("durations_seconds") or []),
            "ranges_meters": list(entry.get("ranges_meters") or []),
            "max_coefficient_percent": float(entry.get("max_coefficient_percent", 0.0) or 0.0),
        }
        for entry in entries
    ]


def merge_deviations_with_combat(
    deviations: list[dict[str, Any]],
    combat_profiles: dict[str, dict[str, Any]],
    preview_skill_catalog: dict[str, list[dict[str, Any]]],
    exact_skill_catalog: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    for deviation in deviations:
        combat_profile = combat_profiles.get(deviation["name"])
        if combat_profile:
            deviation["combat_profile"] = combat_profile
        preview_skills = preview_skill_catalog.get(str(deviation["id"]))
        if preview_skills:
            deviation["preview_skills"] = preview_skills
            deviation["skill_entries"] = merge_skill_catalog(preview_skills, exact_skill_catalog)
    return deviations


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract Once Human deviation/pet metadata from local decompile cache.")
    parser.add_argument("--decompile-dir", type=Path, required=True, help="Path to Once Human/decompile")
    parser.add_argument("--output", type=Path, required=True, help="Output JSON file")
    args = parser.parse_args()

    decompile_dir = args.decompile_dir
    book_path = decompile_dir / "root_script" / "raw" / "client_data" / "book_collect_model_data.pyc"
    preview_path = decompile_dir / "root_script" / "raw" / "client_data" / "deviation_preview_skill_data.pyc"
    combat_path = decompile_dir / "root_script" / "raw" / "game_common" / "data" / "deviation_combat_config_data.pyc"
    skill_path = decompile_dir / "root_script" / "raw" / "game_common" / "data" / "deviation_skills_data.pyc"
    base_path = decompile_dir / "root_script" / "raw" / "game_common" / "data" / "deviation_base_data.pyc"
    translate_ru_path = decompile_dir / "root_script" / "raw" / "translate" / "translate_data_ru.pyc"
    translate_en_path = decompile_dir / "root_script" / "raw" / "translate" / "translate_data_en.pyc"
    if not book_path.exists():
        raise FileNotFoundError(f"book_collect_model_data.pyc not found: {book_path}")
    if not preview_path.exists():
        raise FileNotFoundError(f"deviation_preview_skill_data.pyc not found: {preview_path}")
    if not combat_path.exists():
        raise FileNotFoundError(f"deviation_combat_config_data.pyc not found: {combat_path}")
    if not skill_path.exists():
        raise FileNotFoundError(f"deviation_skills_data.pyc not found: {skill_path}")
    if not base_path.exists():
        raise FileNotFoundError(f"deviation_base_data.pyc not found: {base_path}")
    if not translate_ru_path.exists():
        raise FileNotFoundError(f"translate_data_ru.pyc not found: {translate_ru_path}")
    if not translate_en_path.exists():
        raise FileNotFoundError(f"translate_data_en.pyc not found: {translate_en_path}")

    deviations = extract_book_deviations(book_path)
    combat_profiles = extract_combat_profiles(combat_path)
    preview_skill_catalog = extract_preview_skill_catalog(preview_path)
    exact_skill_catalog = extract_exact_skill_catalog(skill_path)
    deviations = merge_deviations_with_combat(deviations, combat_profiles, preview_skill_catalog, exact_skill_catalog)
    base_classification = extract_deviation_base_classification(base_path, {entry["name"] for entry in deviations})
    for deviation in deviations:
        classification = base_classification.get(deviation["name"], {})
        deviation["is_combat"] = bool(
            classification.get("is_combat")
            or deviation["name"] in KNOWN_COMBAT_DEVIATION_NAMES
            or deviation["name"] in combat_profiles
        )
        if classification.get("role_hints"):
            deviation["role_hints"] = list(classification["role_hints"])
    localizable_texts = collect_localizable_texts(deviations)
    translation_maps = {
        "ru": build_translation_map(translate_ru_path, localizable_texts, "ru"),
        "en": build_translation_map(translate_en_path, localizable_texts, "en"),
    }
    deviations = apply_deviation_localization(deviations, translation_maps)

    payload = {
        "source": {
            "decompile_dir": str(decompile_dir),
            "book_collect_model_data": str(book_path),
            "deviation_preview_skill_data": str(preview_path),
            "deviation_combat_config_data": str(combat_path),
            "deviation_skills_data": str(skill_path),
            "deviation_base_data": str(base_path),
            "translate_data_ru": str(translate_ru_path),
            "translate_data_en": str(translate_en_path),
        },
        "counts": {
            "deviations": len(deviations),
            "combat_deviations": sum(1 for deviation in deviations if deviation.get("is_combat")),
            "combat_profiles": len(combat_profiles),
            "runtime_supported": sum(1 for profile in combat_profiles.values() if profile.get("supported_runtime")),
            "preview_skill_catalog_entries": len(preview_skill_catalog),
            "exact_skill_catalog_entries": len(exact_skill_catalog),
            "localized_texts": len(localizable_texts),
            "ru_localized_entries": len(translation_maps["ru"]),
            "en_localized_entries": len(translation_maps["en"]),
        },
        "deviations": deviations,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload["counts"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
