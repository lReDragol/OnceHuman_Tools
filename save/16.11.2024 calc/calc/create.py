#файл create.py

import json
import os


stats_options = [
    'damage', 'crit_rate_percent', 'crit_damage_percent', 'weapon_damage_percent',
    'status_damage_percent', 'max_hp', 'movement_speed_percent',
    'elemental_damage_percent', 'weakspot_damage_percent', 'reload_speed_percent',
    'magazine_capacity_percent', 'damage_bonus_normal', 'damage_bonus_elite',
    'damage_bonus_boss'
]
flags_options = ['can_deal_weakspot_damage', 'is_invincible', 'has_super_armor']
conditions_options = [
    'hp / max_hp > 0.5', 'enemies_within_distance == 0', 'is_crit', 'is_weak_spot',
    'target_is_marked', 'hp / max_hp < 0.3'
]

mod_categories = ["weapon", "helmet", "mask", "top", "gloves", "pants", "boots"]

category_key_mapping = {
    "helmet": "mod_helmet",
    "mask": "mod_mask",
    "top": "mod_top",
    "gloves": "mod_gloves",
    "pants": "mod_pants",
    "boots": "mod_boots",
    "weapon": "mod_weapon",
}


def load_mods():
    try:
        with open('mods_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_mods(mods):
    with open('mods_config.json', 'w', encoding='utf-8') as f:
        json.dump(mods, f, ensure_ascii=False, indent=2)

def load_items_and_sets():
    try:
        with open('items_and_sets.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            'items': [],
            'sets': [],
            'base_stats': {}
        }

def save_items_and_sets(data):
    with open('items_and_sets.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_category(new_category):
    new_category = new_category.strip()
    if new_category and new_category not in mod_categories:
        mod_categories.append(new_category)
        return True
    else:
        return False

def add_new_stat(new_stat):
    new_stat = new_stat.strip()
    if new_stat and new_stat not in stats_options:
        stats_options.append(new_stat)
        return True
    else:
        return False

def add_new_flag(new_flag):
    new_flag = new_flag.strip()
    if new_flag and new_flag not in flags_options:
        flags_options.append(new_flag)
        return True
    else:
        return False

def add_new_condition(new_condition):
    new_condition = new_condition.strip()
    if new_condition and new_condition not in conditions_options:
        conditions_options.append(new_condition)
        return True
    else:
        return False

def create_mod(mod_name, mod_category, effects, mods_data):
    mod_name = mod_name.strip()
    mod_category = mod_category.strip()
    if not mod_name:
        return False, "Пожалуйста, введите название модификатора."
    mod_data = {
        "id": mod_name.lower().replace(" ", "_"),
        "name": mod_name,
        "effects": effects,
        "category": mod_category
    }
    mod_key = category_key_mapping.get(mod_category, "mod_others")
    if mod_key not in mods_data:
        mods_data[mod_key] = []
    mods_data[mod_key].append(mod_data)
    save_mods(mods_data)
    return True, f"Модификатор '{mod_name}' успешно сохранен."


def delete_mod(mod, mod_key, mods_data):
    if mod_key in mods_data:
        if mod in mods_data[mod_key]:
            mods_data[mod_key].remove(mod)
            save_mods(mods_data)
            return True, "Модификатор удален."
    return False, "Модификатор не найден."

def create_item(item_name, item_type, item_rarity, item_set_id, items_and_sets_data):
    item_name = item_name.strip()
    item_type = item_type.strip()
    item_rarity = item_rarity.strip()
    item_set_id = item_set_id.strip()
    if item_name and item_type and item_rarity:
        new_item = {
            "id": item_name.lower().replace(" ", "_"),
            "name": item_name,
            "type": item_type,
            "rarity": item_rarity,
            "set_id": item_set_id or None
        }
        items_and_sets_data['items'].append(new_item)
        save_items_and_sets(items_and_sets_data)
        return True, "Предмет успешно сохранен!"
    else:
        return False, "Пожалуйста, заполните все поля для создания предмета."

def add_effect(effect_type, effect_stat, effect_value, effect_flag, effect_flag_value, effect_condition, current_mod, stats_stack):
    effect_type = effect_type.strip()
    if not effect_type:
        return False, "Пожалуйста, выберите тип эффекта."
    effect = {"type": effect_type}
    if effect_type in ['increase_stat', 'decrease_stat']:
        stat = effect_stat.strip()
        value = effect_value.strip()
        if not stat or not value:
            return False, "Пожалуйста, заполните стат и значение для эффекта."
        try:
            value = float(value)
        except ValueError:
            return False, "Значение должно быть числом."
        effect['stat'] = stat
        effect['value'] = value
    elif effect_type == 'set_flag':
        flag = effect_flag.strip()
        if not flag:
            return False, "Пожалуйста, выберите флаг для эффекта."
        effect['flag'] = flag
        effect['value'] = bool(effect_flag_value)
    elif effect_type == 'conditional_effect':
        condition = effect_condition.strip()
        if not condition:
            return False, "Пожалуйста, введите условие для условного эффекта."
        effect['condition'] = condition
        effect['effects'] = []
        stats_stack.append(effect['effects'])
    else:
        return False, "Неизвестный тип эффекта."
    stats_stack[-1].append(effect)
    return True, "Эффект успешно добавлен."

def end_conditional_effect(stats_stack):
    if len(stats_stack) > 1:
        stats_stack.pop()
        return True, "Условный эффект завершен."
    else:
        return False, "Нет условных эффектов для завершения."

def edit_mod(mod, current_mod, stats_stack):
    current_mod.clear()
    current_mod.update(mod)
    stats_stack.clear()
    stats_stack.append(current_mod['effects'])

def reset_mod_form(current_mod, stats_stack):
    current_mod['effects'] = []
    stats_stack.clear()
    stats_stack.append(current_mod['effects'])


if __name__ == "__main__":
    mods_data = load_mods()
    items_and_sets_data = load_items_and_sets()
    current_mod = {}
    current_mod['effects'] = []
    stats_stack = [current_mod['effects']]
    add_category("Новая Категория")
    add_new_stat("новый_стат")
    add_new_flag("новый_флаг")
    add_new_condition("hp / max_hp < 0.2")

    success, message = add_effect(
        effect_type='increase_stat',
        effect_stat='damage',
        effect_value='15',
        effect_flag='',
        effect_flag_value=False,
        effect_condition='',
        current_mod=current_mod,
        stats_stack=stats_stack
    )
    print(message)

    success, message = end_conditional_effect(stats_stack)
    if not success:
        print(message)

    success, message = create_mod('Мой новый мод', 'Оружие', current_mod['effects'], mods_data)
    print(message)

    success, message = create_item(
        item_name='Новый Шлем',
        item_type='helmet',
        item_rarity='legendary',
        item_set_id='',
        items_and_sets_data=items_and_sets_data
    )
    print(message)
