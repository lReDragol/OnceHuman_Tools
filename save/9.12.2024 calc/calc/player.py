# player.py

import time
from mechanics import Weapon, add_stats

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
        self.mod_effects = []
        self.item_effects = []
        self.recalculate_stats()

    def equip_item(self, item):
        self.equipped_items[item.type] = item
        self.recalculate_stats()

    def remove_item(self, item_type):
        if item_type in self.equipped_items:
            del self.equipped_items[item_type]
            self.recalculate_stats()

    def equip_mod(self, mod, item_type):
        category = mod.get('category', item_type)
        self.equipped_mods[category] = mod
        self.recalculate_stats()

    def remove_mod(self, category):
        if category in self.equipped_mods:
            del self.equipped_mods[category]
            self.recalculate_stats()

    def equip_weapon(self, weapon):
        self.weapon = weapon
        self.recalculate_stats()

    def remove_weapon(self):
        self.weapon = None
        self.recalculate_stats()

    def recalculate_stats(self):
        self.stats = self.base_stats.copy()
        if self.weapon:
            weapon_stats = self.weapon.get_stats()
            add_stats(self.stats, weapon_stats)
        for item in self.equipped_items.values():
            item_stats = item.get_stats()
            add_stats(self.stats, item_stats)
        self.mod_effects = []
        for mod in self.equipped_mods.values():
            self.mod_effects.extend(mod.get('effects', []))
        for effect in self.mod_effects:
            self.process_effect(effect)

    def process_effect(self, effect):
        effect_type = effect['type']
        if effect_type == 'increase_stat':
            stat = effect['stat']
            value = effect['value']
            self.stats[stat] = self.stats.get(stat, 0) + value
        elif effect_type == 'decrease_stat':
            stat = effect['stat']
            value = effect['value']
            self.stats[stat] = self.stats.get(stat, 0) - value
        elif effect_type == 'set_flag':
            flag = effect['flag']
            self.stats[flag] = effect['value']

    def apply_stat_bonus(self, stat, value, duration, max_stacks=None):
        # Добавляем временный бонус к статистике игрока
        current_time = time.time()
        if stat not in self.active_stat_bonuses:
            self.active_stat_bonuses[stat] = []
        # Можно добавить логику для max_stacks, если нужно
        self.active_stat_bonuses[stat].append({'value': value, 'end_time': current_time + duration})
        self.stats[stat] = self.stats.get(stat, 0) + value

    def update_active_stat_bonuses(self):
        current_time = time.time()
        for stat, bonuses in list(self.active_stat_bonuses.items()):
            for bonus in bonuses[:]:
                if current_time >= bonus['end_time']:
                    self.stats[stat] -= bonus['value']
                    bonuses.remove(bonus)
            if not bonuses:
                del self.active_stat_bonuses[stat]

class Mannequin:
    def __init__(self):
        self.max_hp = 100000
        self.current_hp = self.max_hp
        self.status = 'normal'  # Возможные статусы: 'normal', 'elite', 'boss'
        self.enemy_type = 'Обычный'  # Тип врага: 'Обычный', 'Элитный', 'Босс'
        self.effects = {}  # Словарь активных эффектов: {effect_name: True}
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
        # Реализация применения статуса к манекену
        print(f"Манекен получил статус {status_name} на {duration} секунд с параметрами {kwargs}.")

    # Метод для обновления эффектов (например, уменьшение длительности)
    def update_effects(self, delta_time):
        effects_to_remove = []
        for effect_name, effect in self.effects.items():
            effect.duration -= delta_time
            if effect.duration <= 0:
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
            # Игнорируем значения, которые не являются числами или словарями
            pass
