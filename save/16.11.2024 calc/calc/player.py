# player.py

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
            'damage': 0,
            'crit_rate_percent': 0,
            'crit_damage_percent': 0,
            'magazine_capacity': 0,
            'fire_rate': 0,
            'reload_speed': 0,
            'status_damage_percent': 0,
            'weakspot_damage_percent': 0,
            'damage_bonus_normal': 0,
            'damage_bonus_elite': 0,
            'damage_bonus_boss': 0,
            # Добавьте другие необходимые параметры
        }
        self.equipped_items = {}
        self.equipped_mods = []
        self.stats = self.base_stats.copy()
        self.context = None  # Инициализируем context как None

    def set_context(self, context):
        self.context = context  # Метод для установки контекста после инициализации

    def equip_item(self, item):
        self.equipped_items[item.type] = item
        self.recalculate_stats()

    def remove_item(self, item_type):
        if item_type in self.equipped_items:
            del self.equipped_items[item_type]
            self.recalculate_stats()

    def equip_mod(self, mod):
        self.equipped_mods.append(mod)
        self.recalculate_stats()

    def remove_mod(self, item_type):
        self.equipped_mods = [mod for mod in self.equipped_mods if mod.get('category') != item_type]
        self.recalculate_stats()

    def recalculate_stats(self):
        self.stats = self.base_stats.copy()
        for item in self.equipped_items.values():
            item_stats = item.get_stats()
            for stat, value in item_stats.items():
                self.stats[stat] = self.stats.get(stat, 0) + value
        # Применяем бонусы от сетов и модов после обновления предметов
        self.apply_set_bonuses()
        self.apply_mods()

    def apply_set_bonuses(self):
        if not self.context:
            return
        set_counts = {}
        for item in self.equipped_items.values():
            if item.set_id:
                set_counts[item.set_id] = set_counts.get(item.set_id, 0) + 1
        for set_id, count in set_counts.items():
            game_set = self.context.get_set_by_id(set_id)
            if game_set:
                for bonus in game_set.get('bonuses', []):
                    if count >= bonus['required_items']:
                        self.context.apply_effects(bonus['effects'], self.stats)

    def apply_mods(self):
        if not self.context:
            return
        for mod in self.equipped_mods:
            for effect in mod['effects']:
                self.context.process_effect(effect, self.stats)
