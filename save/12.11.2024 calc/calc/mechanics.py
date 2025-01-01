# mechanics.py

import json
import os
import time

# Функции для загрузки и сохранения модов
def load_mods():
    try:
        with open('mods_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_mods(mods):
    with open('mods_config.json', 'w', encoding='utf-8') as f:
        json.dump(mods, f, ensure_ascii=False, indent=2)

# Списки категорий и соответствий
mod_categories = [
    "Оружие",
    "Шлем",
    "Маска",
    "Нагрудник",
    "Перчатки",
    "Штаны",
    "Ботинки"
]


category_key_mapping = {
    "Шлем": "mod_helmet",
    "Маска": "mod_mask",
    "Нагрудник": "mod_top",
    "Перчатки": "mod_gloves",
    "Штаны": "mod_bottoms",
    "Ботинки": "mod_boots",
    "Оружие": "mod_weapon",
    # Добавьте другие категории, если необходимо
}

# Функции для обработки эффектов модов
def apply_mods(mods, context):
    for mod in mods:
        for effect in mod['effects']:
            process_effect(effect, context)

def process_effect(effect, context):
    effect_type = effect['type']
    if effect_type == 'increase_stat':
        stats = effect['stat']
        value = effect['value']
        if isinstance(stats, list):
            for stat in stats:
                context[stat] = context.get(stat, 0) + value
        else:
            context[stats] = context.get(stats, 0) + value
    elif effect_type == 'decrease_stat':
        stats = effect['stat']
        value = effect['value']
        if isinstance(stats, list):
            for stat in stats:
                context[stat] = context.get(stat, 0) - value
        else:
            context[stats] = context.get(stats, 0) - value
    elif effect_type == 'set_flag':
        flag = effect['flag']
        context[flag] = effect['value']
    elif effect_type == 'damage_multiplier':
        multiplier = effect['multiplier']
        context['damage'] *= multiplier
    elif effect_type == 'conditional_effect':
        condition = effect['condition']
        if check_condition(condition, context):
            for conditional_effect in effect['effects']:
                process_effect(conditional_effect, context)
    # Добавьте другие типы эффектов по мере необходимости

def check_condition(condition, context):
    try:
        # Используем eval для вычисления условия
        return eval(condition, {}, context)
    except Exception as e:
        print(f"Ошибка в условии '{condition}': {e}")
        return False

# Функции для расчета урона и обновления статусов
def calculate_damage(context):
    apply_mods(context['selected_mods'], context)

    damage = context['damage']
    # Шаг 2: Применяем бонус к урону оружия
    damage *= 1 + context.get('weapon_damage_percent', 0) / 100

    # Шаг 3: Применяем бонус к урону по слабым местам, если применимо
    if context['is_weak_spot'] and context.get('can_deal_weakspot_damage', True):
        damage *= 1 + context.get('weakspot_multiplier', 0)

    # Шаг 4: Применяем бонус к урону против определенного типа врага
    damage *= 1 + context.get('damage_bonus_vs_enemy', 0) / 100

    # Шаг 5: Применяем критический бонус, если критический удар
    if context['is_crit']:
        damage *= 1 + context.get('crit_damage_percent', 0) / 100

    return damage

def apply_damage(context):
    current_time = time.time()
    if context['reloading']:
        return None
    if context['current_ammo'] <= 0:
        context['reloading'] = True
        reload_speed = context['reload_speed']
        context['reload_end_time'] = current_time + reload_speed
        return None
    context['last_damage_time'] = current_time
    context['current_ammo'] -= 1
    damage = calculate_damage(context)
    context['total_damage'] += damage
    context['max_total_damage'] = max(context['max_total_damage'], context['total_damage'])
    context['damage_history'].append((time.time(), damage))
    context['dps'] = calculate_dps(context)
    context['max_dps'] = max(context['max_dps'], context['dps'])
    return damage

def calculate_dps(context):
    current_time = time.time()
    recent_damage = [d for t, d in context['damage_history'] if current_time - t <= 1.0]
    context['damage_history'][:] = [(t, d) for t, d in context['damage_history'] if current_time - t <= 1.0]
    return sum(recent_damage)

def update_status_effects(context):
    selected_status = context.get('selected_status')
    if selected_status:
        if selected_status == "Заморозка":
            context['mannequin_status_effects']["Уязвимость"] = 4
            context['mannequin_status_effects']["Скорость движения"] = -10
        elif selected_status == "Горение":
            if context['status_stack_counts']["Fire"] < context['max_fire_stacks']:
                context['status_stack_counts']["Fire"] += 1
            context['mannequin_status_effects']["Урон от огня"] = context['status_stack_counts']["Fire"] * 2
    else:
        context['mannequin_status_effects'].clear()
        context['status_stack_counts']["Fire"] = 0

# Загрузка данных модов
mods_data = load_mods()
