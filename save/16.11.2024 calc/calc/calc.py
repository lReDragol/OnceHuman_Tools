#файл calc.py

import json
import time

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
    "helmet": "mod_helmet",
    "mask": "mod_mask",
    "top": "mod_top",
    "gloves": "mod_gloves",
    "pants": "mod_pants",
    "boots": "mod_boots",
    "weapon": "mod_weapon",
}

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


def load_mods():
    try:
        with open('mods_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def load_all_armor_stats():
    try:
        with open('all_armor_stats.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def load_armor_sets():
    try:
        with open('armor_sets.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            'items': [],
            'sets': [],
            'multipliers': {}
        }


mods_data = load_mods()
all_armor_stats = load_all_armor_stats()
armor_sets_data = load_armor_sets()
base_stats = all_armor_stats.get('items', {})
calibration_bonuses = all_armor_stats.get('calibration_bonuses', {})
multipliers = armor_sets_data.get('multipliers', {})
items_data = armor_sets_data.get('items', [])
sets_data = armor_sets_data.get('sets', [])

class Item:
    def __init__(self, data, base_stats, calibration_bonuses):
        self.id = data['id']
        self.name = data['name']
        self.type = data['type']
        self.rarity = data['rarity']
        self.set_id = data.get('set_id')
        self.star = 1
        self.level = 1
        self.calibration = 0
        self.base_stats_data = base_stats.get(self.type, {}).get(self.rarity, {}).get('stars', {})
        if not self.base_stats_data:
            raise ValueError(f"No base stats for type '{self.type}' and rarity '{self.rarity}'")
        self.max_stars = {
            'legendary': 6,
            'epic': 5,
            'rare': 4,
            'common': 3
        }[self.rarity]
        self.calibration_bonuses = calibration_bonuses

    def get_stats(self):
        stats = {}
        star_data = self.base_stats_data.get(str(self.star), {}).get('levels', {})
        level_data = star_data.get(str(self.level), {})

        if not level_data:
            raise ValueError(f"No data for level {self.level} for item '{self.name}' at star level {self.star}")

        stats = level_data.copy()

        for stat_name in ['hp', 'psi_intensity']:
            base_value = stats.get(stat_name, 0)
            calibration_bonus = self.calibration_bonuses.get(stat_name, {}).get(str(self.calibration), 0.0)
            stats[stat_name] = round(base_value * (1 + calibration_bonus))
        return stats

    def can_calibrate(self):
        max_calibration = self.get_max_calibration()
        return self.calibration < max_calibration

    def get_max_calibration(self):
        if self.level in [1, 2]:
            return 2
        elif self.level in [3, 4]:
            return 4
        elif self.level == 5:
            return 6
        else:
            return 0


class Player:
    def __init__(self):
        self.base_stats = {
            'hp': 0,
            'pollution_resist': 0,
            'psi_intensity': 0,
        }
        self.equipped_items = {}
        self.equipped_mods = []
        self.stats = self.base_stats.copy()

    def equip_item(self, item, context):
        self.equipped_items[item.type] = item
        self.recalculate_stats(context)

    def equip_mod(self, mod, context):
        self.equipped_mods.append(mod)
        self.recalculate_stats(context)

    def recalculate_stats(self, context):
        self.stats = self.base_stats.copy()
        for item in self.equipped_items.values():
            item_stats = item.get_stats()
            for stat, value in item_stats.items():
                self.stats[stat] = self.stats.get(stat, 0) + value
        apply_set_bonuses(self, context)
        apply_mods(self.equipped_mods, self.stats, context)

    def remove_mod(self, item_type, context):
        self.equipped_mods = [mod for mod in self.equipped_mods if mod.get('category') != item_type]
        self.recalculate_stats(context)


def apply_set_bonuses(player, context):
    set_counts = {}
    for item in player.equipped_items.values():
        if item.set_id:
            set_counts[item.set_id] = set_counts.get(item.set_id, 0) + 1
    for set_id, count in set_counts.items():
        game_set = get_set_by_id(set_id)
        if game_set:
            for bonus in game_set.get('bonuses', []):
                if count >= bonus['required_items']:
                    apply_effects(bonus['effects'], player.stats, context)


def get_set_by_id(set_id):
    for game_set in sets_data:
        if game_set['set_id'] == set_id:
            return game_set
    return None


def apply_mods(mods, context_stats, context):
    for mod in mods:
        for effect in mod['effects']:
            process_effect(effect, context_stats, context)


def apply_effects(effects, context_stats, context):
    for effect in effects:
        process_effect(effect, context_stats, context)


def process_effect(effect, context_stats, context):
    effect_type = effect['type']
    if effect_type == 'increase_stat':
        stats = effect['stat']
        value = effect['value']
        if isinstance(stats, list):
            for stat in stats:
                context_stats[stat] = context_stats.get(stat, 0) + value
        else:
            context_stats[stats] = context_stats.get(stats, 0) + value
    elif effect_type == 'decrease_stat':
        stats = effect['stat']
        value = effect['value']
        if isinstance(stats, list):
            for stat in stats:
                context_stats[stat] = context_stats.get(stat, 0) - value
        else:
            context_stats[stats] = context_stats.get(stats, 0) - value
    elif effect_type == 'set_flag':
        flag = effect['flag']
        context_stats[flag] = effect['value']
    elif effect_type == 'conditional_effect':
        condition = effect['condition']
        if check_condition(condition, context_stats):
            for conditional_effect in effect['effects']:
                process_effect(conditional_effect, context_stats, context)
    elif effect_type == 'on_event':
        event = effect['event']
        if 'event_effects' not in context:
            context['event_effects'] = {}
        if event not in context['event_effects']:
            context['event_effects'][event] = []
        context['event_effects'][event].append(effect['effects'])
    elif effect_type == 'apply_status':
        status_name = effect['status']
        status_effects = effect.get('effects', [])
        duration = effect.get('duration_seconds', 0)
        max_stacks = effect.get('max_stacks', 1)
        apply_status(status_name, status_effects, duration, max_stacks, context)
    elif effect_type == 'set_duration':
        pass
    elif effect_type == 'set_max_stacks':
        pass


def apply_status(status_name, status_effects, duration, max_stacks, context):
    if 'statuses' not in context:
        context['statuses'] = {}
    if status_name not in context['statuses']:
        context['statuses'][status_name] = {
            'effects': status_effects,
            'duration': duration,
            'max_stacks': max_stacks,
            'stacks': 0,
            'start_time': 0
        }
    status = context['statuses'][status_name]
    status['start_time'] = time.time()
    if status['stacks'] < status['max_stacks']:
        status['stacks'] += 1


def check_condition(condition, context_stats):
    try:
        safe_context = context_stats.copy()
        safe_context.setdefault('hp', 100)
        safe_context.setdefault('max_hp', 100)
        safe_context.setdefault('enemies_within_distance', 0)
        safe_context.setdefault('target_distance', 0)
        return eval(condition, {}, safe_context)
    except Exception as e:
        print(f"Ошибка в условии '{condition}': {e}")
        return False


def apply_active_statuses(context):
    current_time = time.time()
    if 'statuses' in context:
        for status_name, status in context['statuses'].items():
            elapsed_time = current_time - status['start_time']
            if elapsed_time <= status['duration']:
                for effect in status['effects']:
                    for _ in range(status['stacks']):
                        process_effect(effect, context, context)
            else:
                status['stacks'] = 0


def calculate_damage(context):
    local_context = context.copy()
    apply_mods(local_context.get('selected_mods', []), local_context, local_context)
    apply_active_statuses(local_context)
    damage = local_context['damage']
    damage *= 1 + local_context.get('weapon_damage_percent', 0) / 100
    if local_context['is_weak_spot'] and local_context.get('can_deal_weakspot_damage', True):
        damage *= 1 + local_context.get('weakspot_multiplier', 0)
    damage *= 1 + local_context.get('damage_bonus_vs_enemy', 0) / 100
    if local_context['is_crit']:
        damage *= 1 + local_context.get('crit_damage_percent', 0) / 100
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

    if context['is_crit']:
        context['crit_hits'] = context.get('crit_hits', 0) + 1
        if context['crit_hits'] % 2 == 0:
            handle_events('every_2_weapon_crit_hits', context, context)
    else:
        context['crit_hits'] = 0

    damage = calculate_damage(context)
    context['total_damage'] += damage
    context['max_total_damage'] = max(context['max_total_damage'], context['total_damage'])
    context['damage_history'].append((time.time(), damage))
    context['dps'] = calculate_dps(context)
    context['max_dps'] = max(context['max_dps'], context['dps'])
    return damage


def handle_events(event_name, context_stats, context):
    if 'event_effects' in context and event_name in context['event_effects']:
        for effects in context['event_effects'][event_name]:
            for effect in effects:
                process_effect(effect, context_stats, context)


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
