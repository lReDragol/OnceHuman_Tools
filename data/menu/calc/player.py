# player.py

import time
import copy
import logging
import re
from .mechanics import add_stats, check_conditions, normalize_effects

logging.basicConfig(level=logging.DEBUG)

class Item:
    def __init__(self, item_data, base_stats, calibration_bonuses):
        self.id = item_data['id']
        self.name = item_data['name']
        self.type = item_data['type']
        self.rarity = item_data['rarity']
        self.set_id = item_data.get('set_id')
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

    def calculate_stats(self):
        stats = {}
        add_stats(stats, self.base_stats)
        star_multipliers = {
            1: 1.0,
            2: 1.1,
            3: 1.2,
            4: 1.3,
            5: 1.4,
            6: 1.5
        }
        level_multipliers = {
            1: 1.0,
            2: 1.05,
            3: 1.10,
            4: 1.15,
            5: 1.20
        }
        calibration_bonuses = {
            0: 0.0,
            1: 0.02,
            2: 0.04,
            3: 0.06,
            4: 0.08,
            5: 0.10,
            6: 0.12
        }
        star_multiplier = star_multipliers.get(self.star, 1.0)
        level_multiplier = level_multipliers.get(self.level, 1.0)
        calibration_bonus = calibration_bonuses.get(self.calibration, 0.0)
        for stat in stats:
            base_value = stats[stat]
            if isinstance(base_value, (int, float)):
                new_value = base_value * star_multiplier * level_multiplier * (1 + calibration_bonus)
                if stat in ['projectiles_per_shot', 'magazine_capacity', 'some_other_integer_stat']:
                    stats[stat] = int(round(new_value))
                else:
                    stats[stat] = new_value
        return stats

    def get_stats(self):
        stats = {}
        star_data = self.base_stats_data.get(str(self.star), {})
        levels_data = star_data.get('levels', {})
        level_data = levels_data.get(str(self.level), {})

        if not level_data:
            raise ValueError(f"No data for level {self.level} for item '{self.name}' at star level {self.star}")

        stats = level_data.copy()
        for stat_name in ['hp', 'psi_intensity', 'pollution_resist']:
            base_value = stats.get(stat_name, 0)
            calibration_bonus = self.calibration_bonuses.get(stat_name, {}).get(str(self.calibration), 0.0)
            stats[stat_name] = round(base_value * (1 + calibration_bonus))
        return stats

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
        self.base_stats = {}
        self.stats = {}
        self.equipped_items = {}
        self.equipped_mods = {}
        self.weapon = None
        self.active_stat_bonuses = {}
        self.context = None
        self.mod_effects = []
        self.set_effects = []
        self.static_effects = []
        self.active_set_bonuses = []
        self.event_effect_sources = []
        self.effect_sources_dirty = True
        self.recalculate_stats()

    def equip_item(self, item):
        self.equipped_items[item.type] = item
        self.effect_sources_dirty = True
        self.recalculate_stats()

    def remove_item(self, item_type):
        if item_type in self.equipped_items:
            del self.equipped_items[item_type]
            self.effect_sources_dirty = True
            self.recalculate_stats()

    def equip_mod(self, mod, item_type):
        category = mod.get('category', item_type)
        self.equipped_mods[category] = mod
        self.effect_sources_dirty = True
        self.recalculate_stats()

    def remove_mod(self, category):
        if category in self.equipped_mods:
            del self.equipped_mods[category]
            self.effect_sources_dirty = True
            self.recalculate_stats()

    def equip_weapon(self, weapon):
        self.weapon = weapon
        self.effect_sources_dirty = True
        self.recalculate_stats()

    def remove_weapon(self):
        self.weapon = None
        self.effect_sources_dirty = True
        self.recalculate_stats()

    def refresh_effect_sources(self, context=None):
        context = context or self.context
        self.mod_effects = []
        self.set_effects = []
        self.active_set_bonuses = []
        self.event_effect_sources = []
        self.static_effects = []

        effect_groups = []
        for mod in self.equipped_mods.values():
            effects = normalize_effects(mod.get('effects', []))
            self.mod_effects.extend(effects)
            effect_groups.append({
                'source': f"mod:{mod.get('name', 'unknown')}",
                'effects': effects,
            })

        if context:
            set_counts = {}
            for item in self.equipped_items.values():
                if item.set_id:
                    set_counts[item.set_id] = set_counts.get(item.set_id, 0) + 1

            for set_id, count in set_counts.items():
                game_set = context.get_set_by_id(set_id)
                if not game_set:
                    continue
                for bonus in sorted(game_set.get('bonuses', []), key=lambda entry: entry.get('required_items', 0)):
                    if count >= bonus.get('required_items', 0):
                        bonus_effects = normalize_effects(bonus.get('effects', []))
                        self.active_set_bonuses.append({
                            'set_id': set_id,
                            'set_name': game_set.get('name', set_id),
                            'required_items': bonus.get('required_items', 0),
                            'effects': bonus_effects,
                        })
                        self.set_effects.extend(bonus_effects)
                        effect_groups.append({
                            'source': f"set:{set_id}:{bonus.get('required_items', 0)}",
                            'effects': bonus_effects,
                        })

        for group in effect_groups:
            on_event_effects = [effect for effect in group['effects'] if effect.get('type') == 'on_event']
            static_effects = [effect for effect in group['effects'] if effect.get('type') != 'on_event']
            if on_event_effects:
                self.event_effect_sources.append({
                    'source': group['source'],
                    'effects': on_event_effects,
                })
            self.static_effects.extend(static_effects)

        if self.weapon and isinstance(self.weapon.mechanics_data, dict):
            weapon_effects = normalize_effects(self.weapon.mechanics_data.get('effects', []))
            self.static_effects.extend([effect for effect in weapon_effects if effect.get('type') != 'on_event'])

        if context and hasattr(context, 'mechanics_processor'):
            context.mechanics_processor.set_external_mechanics(self.event_effect_sources)

        self.effect_sources_dirty = False

    def recalculate_stats(self, context=None):
        context = context or self.context
        if self.effect_sources_dirty:
            self.refresh_effect_sources(context)

        self.stats = self.base_stats.copy()
        if self.weapon:
            weapon_stats = self.weapon.get_stats()
            add_stats(self.stats, weapon_stats)
        for item in self.equipped_items.values():
            item_stats = item.get_stats()
            add_stats(self.stats, item_stats)

        for effect in self.static_effects:
            self.process_effect(effect, context)

        for stat, bonuses in self.active_stat_bonuses.items():
            self.stats[stat] = self.stats.get(stat, 0) + sum(bonus['value'] for bonus in bonuses)

        self.apply_derived_stats()

    def process_effect(self, effect, context=None):
        effect_type = effect.get('type')
        if effect_type == 'increase_stat':
            self.apply_stat_delta(effect.get('stat'), effect.get('value', 0))
        elif effect_type == 'decrease_stat':
            self.apply_stat_delta(effect.get('stat'), effect.get('value', 0), negative=True)
        elif effect_type == 'set_flag':
            flags = effect.get('flag')
            values = effect.get('value')
            alias_map = {
                'super_armor': 'has_super_armor',
            }
            if isinstance(flags, list):
                if not isinstance(values, list):
                    values = [values] * len(flags)
                for flag, flag_value in zip(flags, values):
                    flag = alias_map.get(flag, flag)
                    self.stats[flag] = flag_value
            elif flags:
                flags = alias_map.get(flags, flags)
                self.stats[flags] = values
        elif effect_type == 'passive_effect':
            conditions = effect.get('conditions', {})
            effect_context = context.build_effect_context() if context and hasattr(context, 'build_effect_context') else {'mechanics_context': context}
            if conditions and not check_conditions(conditions, effect_context):
                return
            for stat, value in effect.get('properties', {}).items():
                if isinstance(value, (int, float)):
                    self.stats[stat] = self.stats.get(stat, 0) + value
                elif isinstance(value, bool):
                    self.stats[stat] = value
        elif effect_type == 'conditional_effect':
            if self.evaluate_condition(effect.get('condition'), context):
                for nested_effect in normalize_effects(effect.get('effects', [])):
                    self.process_effect(nested_effect, context)
        elif effect_type == 'while_active':
            if context and context.is_status_active(effect.get('status')):
                for nested_effect in normalize_effects(effect.get('effects', [])):
                    self.process_effect(nested_effect, context)
        elif effect_type == 'per_stack':
            if context:
                stack_count = context.get_stack_count(effect.get('stack_source'))
                if stack_count > 0:
                    self.apply_scaled_effects(effect, stack_count, context)
        elif effect_type == 'per_hp_loss':
            if context:
                every_percent = max(effect.get('every_percent', 0), 1)
                hp_lost_percent = max(0.0, 100.0 - context.get_player_hp_ratio() * 100.0)
                stacks = int(hp_lost_percent // every_percent)
                if stacks > 0:
                    self.apply_scaled_effects(effect, stacks, context)
        elif effect_type == 'per_bullets_consumed':
            if context:
                bullets = max(effect.get('bullets', 0), 1)
                stacks = context.magazine_bullets_fired // bullets
                if stacks > 0:
                    self.apply_scaled_effects(effect, stacks, context)
        elif effect_type == 'per_weakspot_hit_rate':
            if context:
                every_percent = max(effect.get('every_percent', 0), 1)
                stacks = int(context.last_magazine_weakspot_rate // every_percent)
                if stacks > 0:
                    self.apply_scaled_effects(effect, stacks, context)
        elif effect_type == 'per_stat':
            stat_name = effect.get('stat')
            step = max(effect.get('value', 0), 1)
            stat_value = self.stats.get(stat_name, 0)
            stacks = int(stat_value // step)
            if stacks > 0:
                self.apply_scaled_effects(effect, stacks, context)

    def apply_scaled_effects(self, effect, stacks, context=None):
        for nested_effect in normalize_effects(effect.get('effects', [])):
            scaled_effect = copy.deepcopy(nested_effect)
            value = scaled_effect.get('value')
            max_value = scaled_effect.get('max_value')
            if isinstance(value, list):
                scaled_values = [entry * stacks for entry in value]
                if max_value is not None:
                    scaled_values = [max(-max_value, min(max_value, scaled)) for scaled in scaled_values]
                scaled_effect['value'] = scaled_values
            elif isinstance(value, (int, float)):
                scaled_value = value * stacks
                if max_value is not None:
                    scaled_value = max(-max_value, min(max_value, scaled_value))
                scaled_effect['value'] = scaled_value
            self.process_effect(scaled_effect, context)

    def apply_stat_delta(self, stat_name, value, negative=False):
        if isinstance(stat_name, list):
            if not isinstance(value, list):
                value = [value] * len(stat_name)
            for single_stat, single_value in zip(stat_name, value):
                self.apply_stat_delta(single_stat, single_value, negative=negative)
            return

        if not stat_name:
            return

        alias_map = {
            'weapon_damage_bonus_percent': 'weapon_damage_percent',
            'super_armor': 'has_super_armor',
        }
        stat_name = alias_map.get(stat_name, stat_name)

        delta = -value if negative else value
        self.stats[stat_name] = self.stats.get(stat_name, 0) + delta

    def evaluate_condition(self, condition, context=None):
        if not condition:
            return True
        if context is None:
            return False

        normalized = condition.strip().lower()
        if normalized == 'target_is_marked':
            return context.is_status_active('the_bulls_eye') or context.is_status_active('bulls_eye')
        if normalized == 'enemy_has_burn':
            return context.is_status_active('burn')
        if normalized == 'enemy_without_power_surge':
            return not context.is_status_active('power_surge')

        ratio_conditions = {
            r'^hp / max_hp ([<>]=?) ([0-9.]+)$': context.get_player_hp_ratio(),
            r'^target_hp / target_max_hp ([<>]=?) ([0-9.]+)$': (
                context.mannequin.current_hp / context.mannequin.max_hp if context.mannequin.max_hp else 1.0
            ),
            r'^enemies_within_distance ([<>]=?|==) ([0-9.]+)$': context.enemies_within_distance,
            r'^target_distance ([<>]=?|==) ([0-9.]+)$': context.target_distance,
        }
        for pattern, current_value in ratio_conditions.items():
            match = re.match(pattern, normalized)
            if match:
                operator = match.group(1)
                threshold = float(match.group(2))
                return self.compare_values(current_value, threshold, operator)
        return False

    @staticmethod
    def compare_values(current_value, threshold, operator):
        if operator == '>':
            return current_value > threshold
        if operator == '>=':
            return current_value >= threshold
        if operator == '<':
            return current_value < threshold
        if operator == '<=':
            return current_value <= threshold
        if operator == '==':
            return current_value == threshold
        return False

    def apply_derived_stats(self):
        if 'magazine_capacity_percent' in self.stats and 'magazine_capacity' in self.stats:
            self.stats['magazine_capacity'] = int(round(
                self.stats['magazine_capacity'] * (1 + self.stats['magazine_capacity_percent'] / 100.0)
            ))
        if 'fire_rate_percent' in self.stats and 'fire_rate' in self.stats:
            self.stats['fire_rate'] = self.stats['fire_rate'] * (1 + self.stats['fire_rate_percent'] / 100.0)
        if 'reload_speed_percent' in self.stats and 'reload_time_seconds' in self.stats and self.stats['reload_time_seconds'] > 0:
            self.stats['reload_time_seconds'] = self.stats['reload_time_seconds'] / (
                1 + self.stats['reload_speed_percent'] / 100.0
            )
        for flag_name in ['has_super_armor', 'can_deal_weakspot_damage', 'is_invincible', 'can_crit']:
            if flag_name in self.stats and isinstance(self.stats[flag_name], (int, float)):
                self.stats[flag_name] = self.stats[flag_name] > 0

    def apply_stat_bonus(self, stat, value, duration, max_stacks=None, source=None):
        current_time = time.time()
        if stat not in self.active_stat_bonuses:
            self.active_stat_bonuses[stat] = []
        bonuses = self.active_stat_bonuses[stat]

        if max_stacks is not None:
            matching_bonuses = [bonus for bonus in bonuses if source is None or bonus.get('source') == source]
            if len(matching_bonuses) >= max_stacks:
                oldest_bonus = min(matching_bonuses, key=lambda bonus: bonus['end_time'])
                oldest_bonus['end_time'] = max(oldest_bonus['end_time'], current_time + duration)
                self.recalculate_stats()
                return False

        bonuses.append({
            'value': value,
            'end_time': current_time + duration,
            'source': source,
        })
        self.recalculate_stats()
        return True

    def update_active_stat_bonuses(self):
        current_time = time.time()
        updated = False
        for stat, bonuses in list(self.active_stat_bonuses.items()):
            for bonus in bonuses[:]:
                if current_time >= bonus['end_time']:
                    bonuses.remove(bonus)
                    updated = True
            if not bonuses:
                del self.active_stat_bonuses[stat]
                updated = True
        if updated:
            self.recalculate_stats()


class Mannequin:
    def __init__(self):
        self.max_hp = 100000
        self.current_hp = self.max_hp
        self.status = 'normal'
        self.enemy_type = 'Обычный'
        self.effects = {}
        self.show_hotbar = True
        self.show_unified_shotgun_damage = False

    def apply_effect(self, effect_name):
        self.effects[effect_name] = True
        print(f"Эффект {effect_name} применён к манекену.")

    def remove_effect(self, effect_name):
        if effect_name in self.effects:
            del self.effects[effect_name]
            print(f"Эффект {effect_name} удалён с манекена.")

    def set_hp(self, hp):
        self.max_hp = hp
        self.current_hp = min(self.current_hp, hp)
        print(f"HP манекена установлено на {self.max_hp}.")

    def toggle_hotbar(self):
        self.show_hotbar = not self.show_hotbar
        state = "включено" if self.show_hotbar else "выключено"
        print(f"Отображение хотбара {state}.")

    def toggle_unified_shotgun_damage(self):
        self.show_unified_shotgun_damage = not self.show_unified_shotgun_damage
        state = "включено" if self.show_unified_shotgun_damage else "выключено"
        print(f"Отображение суммарного урона дробовика {state}.")

    def set_status(self, status):
        self.status = status
        print(f"Статус манекена установлен на {self.status}.")

    def set_enemy_type(self, enemy_type):
        self.enemy_type = enemy_type
        print(f"Тип врага манекена установлен на {self.enemy_type}.")

    def receive_damage(self, damage):
        self.current_hp -= damage
        self.current_hp = max(self.current_hp, 0)
        print(f"Манекен получил {damage} урона. Текущее HP: {self.current_hp}/{self.max_hp}.")

    def apply_status(self, status_name, duration, **kwargs):
        print(f"Манекен получил статус {status_name} на {duration} секунд с параметрами {kwargs}.")

    def update_effects(self, delta_time):
        effects_to_remove = []
        for effect_name, effect_data in self.effects.items():
            if isinstance(effect_data, dict) and 'duration' in effect_data:
                effect_data['duration'] -= delta_time
                if effect_data['duration'] <= 0:
                    effects_to_remove.append(effect_name)
        for effect_name in effects_to_remove:
            self.remove_effect(effect_name)

def add_stats(stats_dict, new_stats):
    for stat, value in new_stats.items():
        if isinstance(value, dict):
            if stat not in stats_dict:
                stats_dict[stat] = {}
            add_stats(stats_dict[stat], value)
        elif isinstance(value, (int, float)):
            current_value = stats_dict.get(stat, 0)
            stats_dict[stat] = current_value + value
        else:
            pass
