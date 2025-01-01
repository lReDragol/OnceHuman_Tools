import json
import re

def parse_damage_formula(formula_str):
    # Пример: "100% Psi Intensity" -> type: psi_intensity, multiplier: 1.0
    # "60% Attack" -> type: attack, multiplier: 0.6
    match = re.match(r"(\d+)%\s+(.*)", formula_str)
    if match:
        percent = int(match.group(1)) / 100.0
        formula_type = match.group(2).lower().replace(' ', '_')
        return {
            "type": formula_type,
            "multiplier": percent
        }
    # Если не подошло, вернуть как есть или None
    return None

def parse_decay(decay_str):
    # Пример: "50% over radius"
    match = re.match(r"(\d+)% over radius", decay_str)
    if match:
        value = int(match.group(1)) / 100.0
        return {
            "type": "over_radius",
            "value": value
        }
    return None

def parse_damage_bonus(bonus_str):
    # Пример: "Penetration: Dealing more DMG against Rosetta"
    # Допустим, всегда 'penetration', target 'rosetta', value вручную зададим 0.2
    if "Penetration" in bonus_str and "Rosetta" in bonus_str:
        return {
            "type": "penetration",
            "target": "rosetta",
            "value": 0.2
        }
    return None

def process_dict(d):
    for key, value in d.items():
        if isinstance(value, str):
            # Проверяем поля по ключам
            if key == "damage_formula":
                new_val = parse_damage_formula(value)
                if new_val:
                    d[key] = new_val
            elif key == "decay":
                new_val = parse_decay(value)
                if new_val:
                    d[key] = new_val
            elif key == "damage_bonus":
                new_val = parse_damage_bonus(value)
                if new_val:
                    d[key] = new_val
        elif isinstance(value, dict):
            process_dict(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    process_dict(item)

with open('weapon_list.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

# Обрабатываем весь список оружия
for weapon in data.get("weapons", []):
    process_dict(weapon)

with open('weapon_list.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)
