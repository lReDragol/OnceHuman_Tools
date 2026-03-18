import argparse
import ast
import json
import re
from collections import Counter
from pathlib import Path


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def collect_registered_names(module_ast, decorator_name):
    names = set()
    for node in ast.walk(module_ast):
        if not isinstance(node, ast.FunctionDef):
            continue
        for decorator in node.decorator_list:
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Name)
                and decorator.func.id == decorator_name
                and decorator.args
                and isinstance(decorator.args[0], ast.Constant)
                and isinstance(decorator.args[0].value, str)
            ):
                names.add(decorator.args[0].value)
    return names


def collect_player_effect_types(module_ast):
    effect_types = set()
    for node in ast.walk(module_ast):
        if not isinstance(node, ast.Compare):
            continue
        if not isinstance(node.left, ast.Name) or node.left.id != "effect_type":
            continue
        for comparator in node.comparators:
            if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
                effect_types.add(comparator.value)
    return effect_types


def walk_effects(effects):
    for effect in effects or []:
        if not isinstance(effect, dict):
            continue
        yield effect
        nested_effects = effect.get("effects")
        if isinstance(nested_effects, list):
            yield from walk_effects(nested_effects)
        nested_effect = effect.get("effect")
        if isinstance(nested_effect, dict):
            yield nested_effect
            if isinstance(nested_effect.get("effects"), list):
                yield from walk_effects(nested_effect["effects"])


def is_placeholder_weapon(weapon):
    text = " ".join(
        str(part or "")
        for part in [
            (weapon.get("mechanics") or {}).get("description"),
            weapon.get("description"),
        ]
    )
    return (
        "Imported base weapon data from Once Human DB" in text
        or "Direct local mechanic extraction from game files is still pending" in text
    )


def normalize_weapon_name(name):
    normalized = str(name or "").strip().lower()
    normalized = re.sub(r"^[a-z0-9-]+\s*-\s*", "", normalized)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def build_report(repo_root: Path):
    mechanics_path = repo_root / "data" / "menu" / "calc" / "mechanics.py"
    player_path = repo_root / "data" / "menu" / "calc" / "player.py"
    data_root = repo_root / "data" / "menu" / "calc" / "bd_json"

    mechanics_ast = ast.parse(mechanics_path.read_text(encoding="utf-8"))
    player_ast = ast.parse(player_path.read_text(encoding="utf-8"))

    effect_handlers = collect_registered_names(mechanics_ast, "register_effect_handler")
    condition_handlers = collect_registered_names(mechanics_ast, "register_condition_checker")
    player_effect_types = collect_player_effect_types(player_ast)
    supported_effect_types = sorted(effect_handlers | player_effect_types | {"on_event"})

    weapons = load_json(data_root / "weapon_list.json").get("weapons", [])
    mods_by_category = load_json(data_root / "mods_config.json")
    sets_payload = load_json(data_root / "items_and_sets.json")
    deviations_payload = load_json(data_root / "deviations.json") if (data_root / "deviations.json").exists() else {"deviations": []}
    items = sets_payload.get("items", [])
    sets = sets_payload.get("sets", [])
    deviations = deviations_payload.get("deviations", [])
    armor_items = [item for item in items if item.get("type") in {"helmet", "mask", "top", "gloves", "pants", "boots"}]
    mods = [mod for entries in mods_by_category.values() for mod in entries]

    unknown_effects = Counter()
    unknown_conditions = Counter()

    def scan_effect_block(source_kind, effects):
        for effect in walk_effects(effects):
            effect_type = effect.get("type")
            if effect_type not in supported_effect_types:
                unknown_effects[f"{source_kind}:{effect_type}"] += 1
            conditions = effect.get("conditions")
            if isinstance(conditions, dict):
                for key in conditions:
                    if key not in condition_handlers:
                        unknown_conditions[f"{source_kind}:{key}"] += 1

    for weapon in weapons:
        scan_effect_block("weapon", (weapon.get("mechanics") or {}).get("effects", []))
    for mod in mods:
        scan_effect_block("mod", mod.get("effects", []))
    for game_set in sets:
        for bonus in game_set.get("bonuses", []):
            scan_effect_block("set", bonus.get("effects", []))

    inherited_alias_candidates = []
    weapons_by_key = {}
    for weapon in weapons:
        key = (weapon.get("type"), normalize_weapon_name(weapon.get("name")))
        weapons_by_key.setdefault(key, []).append(weapon)
    for group in weapons_by_key.values():
        source_weapon = next(
            (
                weapon for weapon in group
                if (weapon.get("mechanics") or {}).get("effects")
            ),
            None,
        )
        if not source_weapon:
            continue
        for weapon in group:
            if weapon is source_weapon:
                continue
            if (weapon.get("mechanics") or {}).get("effects"):
                continue
            if not is_placeholder_weapon(weapon):
                continue
            inherited_alias_candidates.append(
                {
                    "target_id": weapon.get("id"),
                    "target_name": weapon.get("name"),
                    "source_id": source_weapon.get("id"),
                    "source_name": source_weapon.get("name"),
                }
            )

    report = {
        "engine_coverage": {
            "supported_effect_types_count": len(supported_effect_types),
            "supported_effect_types": supported_effect_types,
            "supported_condition_types_count": len(condition_handlers),
            "supported_condition_types": sorted(condition_handlers),
            "unknown_effects": dict(unknown_effects),
            "unknown_conditions": dict(unknown_conditions),
        },
        "weapons": {
            "total": len(weapons),
            "with_mechanics": sum(1 for weapon in weapons if (weapon.get("mechanics") or {}).get("effects")),
            "without_mechanics": sum(1 for weapon in weapons if not (weapon.get("mechanics") or {}).get("effects")),
            "placeholder_pending_extraction": sum(1 for weapon in weapons if is_placeholder_weapon(weapon)),
            "runtime_inherited_aliases": inherited_alias_candidates,
            "runtime_inherited_aliases_count": len(inherited_alias_candidates),
            "sample_missing": [
                {
                    "id": weapon.get("id"),
                    "name": weapon.get("name"),
                    "type": weapon.get("type"),
                    "source_url": weapon.get("source_url"),
                }
                for weapon in weapons
                if not (weapon.get("mechanics") or {}).get("effects")
            ][:30],
        },
        "mods": {
            "total": len(mods),
            "with_explicit_effects": sum(1 for mod in mods if mod.get("effects")),
            "without_explicit_effects": sum(1 for mod in mods if not mod.get("effects")),
            "categories": {category: len(entries) for category, entries in mods_by_category.items()},
            "sample_without_explicit_effects": [
                {
                    "category": category,
                    "name": mod.get("name"),
                }
                for category, entries in mods_by_category.items()
                for mod in entries
                if not mod.get("effects")
            ][:30],
        },
        "armor": {
            "items_total": len(armor_items),
            "items_with_direct_effects": sum(1 for item in armor_items if item.get("effects")),
            "sets_total": len(sets),
            "sets_with_bonuses": sum(1 for game_set in sets if game_set.get("bonuses")),
            "bonuses_total": sum(len(game_set.get("bonuses", [])) for game_set in sets),
            "sample_sets": [
                {
                    "id": game_set.get("set_id") or game_set.get("id"),
                    "name": game_set.get("name"),
                    "bonuses": len(game_set.get("bonuses", [])),
                }
                for game_set in sets[:20]
            ],
        },
        "deviations": {
            "total": len(deviations),
            "with_explicit_runtime": sum(
                1
                for deviation in deviations
                if (deviation.get("combat_profile") or {}).get("supported_runtime")
            ),
            "with_skill_entries": sum(1 for deviation in deviations if deviation.get("skill_entries")),
            "sample_without_explicit_runtime": [
                {
                    "id": deviation.get("id"),
                    "name": deviation.get("name"),
                    "aliases": deviation.get("aliases") or [],
                }
                for deviation in deviations
                if not (deviation.get("combat_profile") or {}).get("supported_runtime")
            ][:20],
        },
    }
    return report


def render_markdown(report):
    lines = [
        "# Mechanics Audit",
        "",
        "## Engine Coverage",
        f"- Supported effect types: {report['engine_coverage']['supported_effect_types_count']}",
        f"- Supported condition types: {report['engine_coverage']['supported_condition_types_count']}",
        f"- Unknown effect types in data: {len(report['engine_coverage']['unknown_effects'])}",
        f"- Unknown condition types in data: {len(report['engine_coverage']['unknown_conditions'])}",
        "",
        "## Weapons",
        f"- Total: {report['weapons']['total']}",
        f"- With mechanics: {report['weapons']['with_mechanics']}",
        f"- Without mechanics: {report['weapons']['without_mechanics']}",
        f"- Placeholder / pending extraction: {report['weapons']['placeholder_pending_extraction']}",
        f"- Runtime alias inheritance candidates: {report['weapons']['runtime_inherited_aliases_count']}",
        "",
        "## Mods",
        f"- Total: {report['mods']['total']}",
        f"- With explicit effects: {report['mods']['with_explicit_effects']}",
        f"- Without explicit effects: {report['mods']['without_explicit_effects']}",
        "",
        "## Armor And Sets",
        f"- Armor items: {report['armor']['items_total']}",
        f"- Armor items with direct effects: {report['armor']['items_with_direct_effects']}",
        f"- Sets: {report['armor']['sets_total']}",
        f"- Sets with bonuses: {report['armor']['sets_with_bonuses']}",
        f"- Total set bonuses: {report['armor']['bonuses_total']}",
        "",
        "## Deviations",
        f"- Total: {report['deviations']['total']}",
        f"- With explicit combat runtime: {report['deviations']['with_explicit_runtime']}",
        f"- With skill entries from game files: {report['deviations']['with_skill_entries']}",
        "",
        "## Runtime Alias Inheritance",
    ]
    for alias in report["weapons"]["runtime_inherited_aliases"]:
        lines.append(
            f"- {alias['target_id']} <= {alias['source_id']} ({alias['target_name']} <= {alias['source_name']})"
        )
    lines.extend([
        "",
        "## Sample Missing Weapons",
    ])
    for weapon in report["weapons"]["sample_missing"]:
        lines.append(f"- {weapon['id']}: {weapon['name']} [{weapon['type']}]")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="Audit calculator mechanics coverage and data completeness.")
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="Path to repository root.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        type=Path,
        help="Directory for generated report files. Defaults to <repo>/local_artifacts.",
    )
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    output_dir = args.output_dir.resolve() if args.output_dir else repo_root / "local_artifacts"
    output_dir.mkdir(parents=True, exist_ok=True)

    report = build_report(repo_root)
    json_path = output_dir / "mechanics_audit_report.json"
    md_path = output_dir / "mechanics_audit_report.md"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")

    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")


if __name__ == "__main__":
    main()
