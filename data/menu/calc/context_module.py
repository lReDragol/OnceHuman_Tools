import json
import time
import math
import random
import os
import dearpygui.dearpygui as dpg
from .player import Item, Mannequin, Player
from .mechanics import Weapon, MechanicsProcessor, normalize_effects, iter_stat_value_pairs
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

DISPLAY_TEXT = {
    "ru": {
        "stats_title": "Текущие параметры персонажа",
        "mannequin_hp": "HP манекена",
        "mannequin_status": "Статус манекена",
        "mannequin_enemy_type": "Тип врага манекена",
        "mannequin_effects": "Эффекты на манекене",
        "equipped_items": "Экипированные предметы",
        "stars": "Звёзд",
        "level": "Уровень",
        "calibration": "Калибровка",
        "weapon": "Оружие",
        "status_effects": "Статусные эффекты",
        "yes": "Да",
        "no": "Нет",
    },
    "en": {
        "stats_title": "Current character stats",
        "mannequin_hp": "Target dummy HP",
        "mannequin_status": "Target dummy status",
        "mannequin_enemy_type": "Target dummy enemy type",
        "mannequin_effects": "Effects on target dummy",
        "equipped_items": "Equipped items",
        "stars": "Stars",
        "level": "Level",
        "calibration": "Calibration",
        "weapon": "Weapon",
        "status_effects": "Status effects",
        "yes": "Yes",
        "no": "No",
    },
}

STAT_LABELS = {
    "ru": {
        "damage_per_projectile": "Урон за выстрел",
        "crit_rate_percent": "Шанс крит. попадания %",
        "crit_damage_percent": "Крит. урон %",
        "weapon_damage_percent": "Урон оружия %",
        "status_damage_percent": "Урон статуса %",
        "movement_speed_percent": "Скорость передвижения %",
        "elemental_damage_percent": "Элементальный урон %",
        "weakspot_damage_percent": "Урон по уязвимостям %",
        "reload_time_seconds": "Перезарядка (сек.)",
        "reload_speed_percent": "Скорость перезарядки %",
        "reload_speed_points": "Очки перезарядки",
        "magazine_capacity": "Ёмкость магазина",
        "magazine_capacity_percent": "Ёмкость магазина %",
        "damage_bonus_normal": "Урон по обычным %",
        "damage_bonus_elite": "Урон по элитным %",
        "damage_bonus_boss": "Урон по боссам %",
        "pollution_resist": "Сопротивление загрязнению",
        "psi_intensity": "Пси-интенсивность",
        "fire_rate": "Скорость стрельбы",
        "fire_rate_percent": "Скорость стрельбы %",
        "projectiles_per_shot": "Пуль за выстрел",
        "hp": "ОЗ",
        "attack": "Атака",
        "psi_intensity_damage_percent": "Урон от PSI %",
        "stability": "Стабильность",
        "accuracy": "Точность",
        "range": "Дальность",
        "mobility": "Мобильность",
        "ads_time_seconds": "Время ADS (сек.)",
        "bullet_speed": "Скорость пули",
        "min_damage_range_meters": "Начало падения урона (м)",
        "min_damage_percent": "Мин. урон %",
        "damage_reduction_percent": "Снижение урона %",
        "vulnerability_percent": "Уязвимость цели %",
        "explosion_elemental_damage_percent": "Урон взрыва %",
        "unstable_bomber_damage_percent": "Урон Unstable Bomber %",
        "unstable_bomber_final_damage_percent": "Финальный урон Unstable Bomber %",
        "shrapnel_damage_percent": "Урон Shrapnel %",
        "shrapnel_trigger_chance_percent": "Шанс Shrapnel %",
        "power_surge_damage_percent": "Урон Power Surge %",
        "power_surge_duration_percent": "Длительность Power Surge %",
        "shock_damage_percent": "Урон шока %",
        "burn_damage_percent": "Урон горения %",
        "burn_duration_percent": "Длительность горения %",
        "max_burn_stacks": "Макс. стаков горения",
        "frost_vortex_damage_percent": "Урон Frost Vortex %",
        "fortress_warfare_range_percent": "Радиус Fortress Warfare %",
        "max_lone_shadow_stacks": "Макс. стаков Lone Shadow",
        "max_deviant_energy_stacks": "Макс. стаков Deviant Energy",
        "can_deal_weakspot_damage": "Попадание по уязвимостям",
        "is_invincible": "Неуязвимость",
        "has_super_armor": "Суперброня",
    },
    "en": {
        "damage_per_projectile": "Damage per shot",
        "crit_rate_percent": "Critical hit chance %",
        "crit_damage_percent": "Critical damage %",
        "weapon_damage_percent": "Weapon damage %",
        "status_damage_percent": "Status damage %",
        "movement_speed_percent": "Movement speed %",
        "elemental_damage_percent": "Elemental damage %",
        "weakspot_damage_percent": "Weakspot damage %",
        "reload_time_seconds": "Reload time (sec.)",
        "reload_speed_percent": "Reload speed %",
        "reload_speed_points": "Reload points",
        "magazine_capacity": "Magazine capacity",
        "magazine_capacity_percent": "Magazine capacity %",
        "damage_bonus_normal": "Damage vs normal enemies %",
        "damage_bonus_elite": "Damage vs elite enemies %",
        "damage_bonus_boss": "Damage vs bosses %",
        "pollution_resist": "Pollution resistance",
        "psi_intensity": "PSI intensity",
        "fire_rate": "Fire rate",
        "fire_rate_percent": "Fire rate %",
        "projectiles_per_shot": "Projectiles per shot",
        "hp": "HP",
        "attack": "Attack",
        "psi_intensity_damage_percent": "PSI damage %",
        "stability": "Stability",
        "accuracy": "Accuracy",
        "range": "Range",
        "mobility": "Mobility",
        "ads_time_seconds": "ADS time (sec.)",
        "bullet_speed": "Bullet speed",
        "min_damage_range_meters": "Damage falloff start (m)",
        "min_damage_percent": "Minimum damage %",
        "damage_reduction_percent": "Damage reduction %",
        "vulnerability_percent": "Target vulnerability %",
        "explosion_elemental_damage_percent": "Explosion damage %",
        "unstable_bomber_damage_percent": "Unstable Bomber damage %",
        "unstable_bomber_final_damage_percent": "Unstable Bomber final damage %",
        "shrapnel_damage_percent": "Shrapnel damage %",
        "shrapnel_trigger_chance_percent": "Shrapnel trigger chance %",
        "power_surge_damage_percent": "Power Surge damage %",
        "power_surge_duration_percent": "Power Surge duration %",
        "shock_damage_percent": "Shock damage %",
        "burn_damage_percent": "Burn damage %",
        "burn_duration_percent": "Burn duration %",
        "max_burn_stacks": "Max burn stacks",
        "frost_vortex_damage_percent": "Frost Vortex damage %",
        "fortress_warfare_range_percent": "Fortress Warfare range %",
        "max_lone_shadow_stacks": "Max Lone Shadow stacks",
        "max_deviant_energy_stacks": "Max Deviant Energy stacks",
        "can_deal_weakspot_damage": "Weakspot damage enabled",
        "is_invincible": "Invincible",
        "has_super_armor": "Super armor",
    },
}

ENEMY_TYPE_LABELS = {
    "ru": {
        "Normal": "Обычный",
        "Elite": "Элитный",
        "Boss": "Босс",
        "Обычный": "Обычный",
        "Элитный": "Элитный",
        "Босс": "Босс",
    },
    "en": {
        "Normal": "Normal",
        "Elite": "Elite",
        "Boss": "Boss",
        "Обычный": "Normal",
        "Элитный": "Elite",
        "Босс": "Boss",
    },
}

class DamageCalculator:
    def __init__(self, player, context):
        self.player = player
        self.context = context

    def calculate_damage_per_projectile(self, weakspot_hit=False):
        damage = self.get_base_damage()
        damage = self.apply_weapon_and_status_bonus(damage)
        damage = self.apply_enemy_type_bonus(damage)
        is_crit, damage = self.apply_crit_bonus(damage)
        if weakspot_hit:
            damage = self.apply_weakspot_bonus(damage)
        return damage, is_crit

    def get_base_damage(self):
        damage = self.player.stats.get('damage_per_projectile', 0)
        return damage

    def apply_weapon_and_status_bonus(self, damage):
        weapon_damage_bonus = self.player.stats.get('weapon_damage_percent', 0)
        status_damage_bonus = self.player.stats.get('status_damage_percent', 0)
        total_bonus = (weapon_damage_bonus + status_damage_bonus) / 100.0
        logging.debug(f"Weapon+status bonus. Total bonus: {total_bonus*100}%. Damage now: {damage * (1 + total_bonus)}")
        return damage * (1 + total_bonus)

    def apply_enemy_type_bonus(self, damage):
        enemy_type = self.context.mannequin.enemy_type
        if enemy_type == 'Обычный':
            bonus = self.player.stats.get('damage_bonus_normal', 0)
        elif enemy_type == 'Элитный':
            bonus = self.player.stats.get('damage_bonus_elite', 0)
        elif enemy_type == 'Босс':
            bonus = self.player.stats.get('damage_bonus_boss', 0)
        else:
            bonus = 0
        damage *= (1 + bonus / 100.0)
        logging.debug(f"Enemy type bonus {bonus}%. Damage now: {damage}")
        return damage

    def apply_crit_bonus(self, damage):
        crit_rate = self.player.stats.get('crit_rate_percent', 0)
        is_crit = (random.uniform(0, 100) <= crit_rate)
        self.context.last_hit_crit = is_crit
        logging.debug(f"Critical roll: {'Yes' if is_crit else 'No'}.")
        if is_crit:
            crit_damage_bonus = self.player.stats.get('crit_damage_percent', 0)
            damage *= (1 + crit_damage_bonus / 100.0)
            logging.debug(f"Crit dmg bonus {crit_damage_bonus}%. Damage now: {damage}")
        return is_crit, damage

    def apply_weakspot_bonus(self, damage):
        weakspot_bonus = self.player.stats.get('weakspot_damage_percent', 0)
        damage *= (1 + weakspot_bonus / 100.0)
        self.context.last_hit_weakspot = True
        logging.debug(f"Weakspot bonus {weakspot_bonus}%. Damage now: {damage}")
        return damage


class Context:
    def __init__(self, player):
        self.player = player
        self.player.context = self
        self.player.effect_sources_dirty = True
        self.language = "ru"
        self.total_damage = 0
        self.dps = 0
        self.max_dps = 0
        self.max_total_damage = 0
        self.damage_history = []
        self.mouse_pressed = False
        self.scheduled_deletions = []
        self.last_fire_time = 0.0
        self.base_hp = 700
        self.bonus_hp = 0
        self.max_hp = self.base_hp + self.bonus_hp
        self.current_hp = self.max_hp
        self.enemies_within_distance = 0
        self.target_distance = 0
        self.current_ammo = 0
        self.reloading = False
        self.reload_end_time = 0
        self.last_damage_time = 0
        self.last_shot_time = None
        self.selected_mods = []
        self.selected_items = {}
        self.mannequin_status_effects = {}
        self.mannequin_status_expirations = []
        self.mannequin_status_stacks = {}
        self.mannequin_status_payloads = {}
        self.player_status_expirations = []
        self.status_stack_counts = {}
        self.max_fire_stacks = 16
        self.stats_display_timer = 0.0
        self.selected_status = None
        self.event_effects = {}
        self.counters = {}
        self.stacks = {}
        self.buffs = {}
        self.trigger_factors = {}
        self.event_chance_modifiers = {}
        self.infinite_ammo_until = 0.0
        self.alternate_ammo = None
        self.alternate_ammo_until_reload = False
        self.charge_stacks = 0
        self.current_mode = None
        self.mode_expirations = {}
        self.magazine_bullets_fired = 0
        self.magazine_weakspot_hits = 0
        self.last_magazine_weakspot_rate = 0.0
        self.enemy_defeated_pending_reset = False
        self.current_shield = 0.0
        self.shield_end_time = 0.0

        # Путь с JSON
        self.bd_json_path = os.path.join(CURRENT_DIR, 'bd_json')

        # Загружаем данные (items, sets, и т.д.)
        items_and_sets = self.load_items_and_sets()
        self.items_data = items_and_sets['items']
        self.sets_data = items_and_sets['sets']
        self.multipliers = items_and_sets.get('multipliers', {})

        self.mods_data = self.load_mods()
        self.base_stats_data = self.load_all_armor_stats()
        self.base_stats = self.base_stats_data.get('items', {})
        self.calibration_bonuses = self.base_stats_data.get('calibration_bonuses', {})

        self.weapons_data = self.load_weapons()
        self.attachments_data = self.load_weapon_attachments()

        self.current_mod = {'effects': []}
        self.stats_stack = [self.current_mod['effects']]

        self.mod_categories = ["weapon", "helmet", "mask", "top", "gloves", "pants", "boots"]
        self.category_key_mapping = {
            "helmet": "mod_helmet",
            "mask": "mod_mask",
            "top": "mod_top",
            "gloves": "mod_gloves",
            "pants": "mod_pants",
            "boots": "mod_boots",
            "weapon": "mod_weapon",
        }

        self.stats_options = [
            'damage_per_projectile', 'crit_rate_percent', 'crit_damage_percent', 'weapon_damage_percent',
            'status_damage_percent', 'movement_speed_percent', 'elemental_damage_percent',
            'weakspot_damage_percent', 'reload_time_seconds', 'magazine_capacity', 'damage_bonus_normal',
            'damage_bonus_elite', 'damage_bonus_boss', 'pollution_resist', 'psi_intensity',
            'fire_rate', 'projectiles_per_shot'
        ]
        self.flags_options = ['can_deal_weakspot_damage', 'is_invincible', 'has_super_armor']
        self.conditions_options = [
            'hp / max_hp > 0.5', 'enemies_within_distance == 0', 'is_crit', 'is_weak_spot',
            'target_is_marked', 'hp / max_hp < 0.3'
        ]

        self.last_damage_dealt = 0
        self.last_hit_weakspot = False
        self.last_hit_crit = False
        self.enemy_type = 'Обычный'
        self.last_shot_mouse_pos = (0, 0)

        self.damage_calculator = DamageCalculator(self.player, self)
        self.mechanics_processor = MechanicsProcessor(self)

        self.mannequin = Mannequin()
        self.last_update_time = time.time()
        self.damage_text_settings = {
            'speed': 100,
            'fade_delay': 1.0,
            'angle_min': 45,
            'angle_max': 135,
            'crit_weakspot_color': [0, 255, 0, 255],
            'crit_color': [255, 165, 0, 255],
            'weakspot_color': [255, 0, 0, 255],
            'normal_color': [255, 255, 255, 255]
        }
        self.ability_icons = {}

        icons_path = os.path.join('data', 'icons', 'weapons')
        if os.path.exists(icons_path):
            for fname in os.listdir(icons_path):
                if fname.endswith('.png'):
                    ability_id = os.path.splitext(fname)[0]
                    w, h, c, data = dpg.load_image(os.path.join(icons_path, fname))
                    with dpg.texture_registry():
                        tex_id = dpg.add_static_texture(w, h, data)
                    self.ability_icons[ability_id] = tex_id

    def load_mods(self):
        path_mods = os.path.join(self.bd_json_path, 'mods_config.json')
        try:
            with open(path_mods, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.warning("mods_config.json not found!")
            return {}

    def load_all_armor_stats(self):
        path_stats = os.path.join(self.bd_json_path, 'all_armor_stats.json')
        try:
            with open(path_stats, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.warning("all_armor_stats.json not found!")
            return {}

    def load_items_and_sets(self):
        path_items_sets = os.path.join(self.bd_json_path, 'items_and_sets.json')
        try:
            with open(path_items_sets, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for game_set in data.get('sets', []):
                    game_set.setdefault('description', '')
                return data
        except FileNotFoundError:
            logging.warning("items_and_sets.json not found!")
            return {
                'items': [],
                'sets': [],
                'multipliers': {}
            }

    def load_weapons(self):
        path_weapons = os.path.join(self.bd_json_path, 'weapon_list.json')
        try:
            with open(path_weapons, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('weapons', [])
        except FileNotFoundError:
            logging.warning("weapon_list.json not found!")
            return []

    def load_weapon_attachments(self):
        path_attachments = os.path.join(self.bd_json_path, 'weapon_attachments.json')
        try:
            with open(path_attachments, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('attachments', [])
        except FileNotFoundError:
            logging.warning("weapon_attachments.json not found!")
            return []

    def update_selected_status(self, status):
        self.selected_status = status

    def update_parameter(self, parameter, value):
        if parameter == "enemies_within_distance_input":
            self.enemies_within_distance = value
        elif parameter == "target_distance_input":
            self.target_distance = value
        elif parameter == "base_damage_input":
            self.player.base_stats['damage_per_projectile'] = value
        elif parameter == "crit_chance_input":
            self.player.base_stats['crit_rate_percent'] = value
        elif parameter == "crit_dmg_input":
            self.player.base_stats['crit_damage_percent'] = value
        elif parameter == "psi_intensity_input":
            self.player.base_stats['psi_intensity'] = value
        elif parameter == "magazine_capacity_input":
            self.player.base_stats['magazine_capacity'] = value
        elif parameter == "fire_rate_input":
            self.player.base_stats['fire_rate'] = value
        elif parameter == "reload_speed_input":
            self.player.base_stats['reload_time_seconds'] = value
        elif parameter == "weapon_damage_bonus_input":
            self.player.base_stats['weapon_damage_percent'] = value
        elif parameter == "status_damage_bonus_input":
            self.player.base_stats['status_damage_percent'] = value
        elif parameter == "weakspot_damage_bonus_input":
            self.player.base_stats['weakspot_damage_percent'] = value
        elif parameter == "damage_reduction_input":
            self.player.base_stats['damage_reduction_percent'] = value
        elif parameter in {"contamination_resistance_input", "resistance_to_pollution"}:
            self.player.base_stats['pollution_resist'] = value
        elif parameter == "damage_bonus_normal_input":
            self.player.base_stats['damage_bonus_normal'] = value
        elif parameter == "damage_bonus_elite_input":
            self.player.base_stats['damage_bonus_elite'] = value
        elif parameter == "damage_bonus_boss_input":
            self.player.base_stats['damage_bonus_boss'] = value
        elif parameter == "enemy_type_combo":
            self.enemy_type = value
        elif parameter == "hp_input":
            self.base_hp = value
            self.update_max_hp()
        else:
            setattr(self, parameter, value)
        self.refresh_player_stats()
        self.current_ammo = self.player.stats.get('magazine_capacity', 0)
        self.update_max_hp()

    def update_max_hp(self):
        self.bonus_hp = self.player.stats.get('hp', 0)
        self.max_hp = self.base_hp + self.bonus_hp

    def set_language(self, language):
        self.language = language if language in DISPLAY_TEXT else "ru"

    def get_text(self, key, fallback):
        return DISPLAY_TEXT.get(self.language, DISPLAY_TEXT["ru"]).get(key, fallback)

    def format_enemy_type(self, enemy_type):
        return ENEMY_TYPE_LABELS.get(self.language, ENEMY_TYPE_LABELS["ru"]).get(enemy_type, enemy_type)

    def format_stat_name(self, stat_key):
        label_map = STAT_LABELS.get(self.language, STAT_LABELS["ru"])
        if stat_key in label_map:
            return label_map[stat_key]
        return stat_key.replace("_", " ").strip().capitalize()

    def format_value(self, value, digits=2, hp_value=False):
        if isinstance(value, bool):
            return self.get_text("yes", "Yes") if value else self.get_text("no", "No")
        if isinstance(value, (int, float)):
            if hp_value:
                return str(int(round(value)))
            rounded = round(float(value), digits)
            if rounded.is_integer():
                return str(int(rounded))
            return f"{rounded:.{digits}f}".rstrip("0").rstrip(".")
        return str(value)

    def get_status_remaining(self, status):
        now = time.time()
        target_remaining = max(
            [entry['end_time'] - now for entry in self.mannequin_status_expirations if entry['status'] == status] or [0.0]
        )
        player_remaining = max(
            [entry['end_time'] - now for entry in self.player_status_expirations if entry['status'] == status] or [0.0]
        )
        mode_remaining = max(self.mode_expirations.get(status, 0.0) - now, 0.0)
        return max(target_remaining, player_remaining, mode_remaining, 0.0)

    def get_active_status_payloads(self):
        now = time.time()
        payloads = []
        seen = set()
        for status, end_time in self.mannequin_status_effects.items():
            payloads.append({
                'status': status,
                'target': 'mannequin',
                'stacks': self.mannequin_status_stacks.get(status, 1),
                'remaining': max(end_time - now, 0.0),
            })
            seen.add(('mannequin', status))
        for status, count in self.status_stack_counts.items():
            key = ('player', status)
            if key in seen:
                continue
            payloads.append({
                'status': status,
                'target': 'player',
                'stacks': count,
                'remaining': self.get_status_remaining(status),
            })
        if self.current_mode:
            key = ('player', self.current_mode)
            if key not in seen:
                payloads.append({
                    'status': self.current_mode,
                    'target': 'player',
                    'stacks': 1,
                    'remaining': self.get_status_remaining(self.current_mode),
                })
        if self.current_shield > 0 and self.shield_end_time > now:
            payloads.append({
                'status': 'shielded',
                'target': 'player',
                'stacks': 1,
                'remaining': max(self.shield_end_time - now, 0.0),
            })
        return payloads

    def build_effect_context(self, event_name=None, **overrides):
        target_statuses = [{'status': status} for status in self.mannequin.effects.keys()]
        for status in self.mannequin_status_effects.keys():
            if {'status': status} not in target_statuses:
                target_statuses.append({'status': status})
        for status in self.mannequin_status_stacks.keys():
            if {'status': status} not in target_statuses:
                target_statuses.append({'status': status})

        effect_context = {
            'mechanics_context': self,
            'target_statuses': target_statuses,
            'all_projectiles_hit': getattr(self, 'all_projectiles_hit', False),
            'last_extra_ammo_consumed': getattr(self, 'last_extra_ammo_consumed', False),
            'ice_crystal_shattered': getattr(self, 'ice_crystal_shattered', False),
            'player_hp_ratio': self.get_player_hp_ratio(),
            'target_hp_ratio': (self.mannequin.current_hp / self.mannequin.max_hp) if self.mannequin.max_hp else 1.0,
            'enemy_type': self.mannequin.enemy_type,
            'current_mode': self.current_mode,
            'current_shield': self.current_shield,
            'event_name': event_name,
        }
        effect_context.update(overrides)
        return effect_context

    def is_status_active(self, status):
        if not status:
            return False
        return (
            status in self.mannequin_status_effects
            or status in self.mannequin.effects
            or self.mannequin_status_stacks.get(status, 0) > 0
            or self.status_stack_counts.get(status, 0) > 0
            or self.stacks.get(status, 0) > 0
            or status in self.buffs
            or status == self.current_mode
            or (status == 'shielded' and self.current_shield > 0)
        )

    def get_stack_count(self, stack_source):
        return self.status_stack_counts.get(
            stack_source,
            self.mannequin_status_stacks.get(stack_source, self.stacks.get(stack_source, 0)),
        )

    def refresh_player_stats(self):
        self.player.recalculate_stats(self)
        self.update_max_hp()
        max_mag = self.player.stats.get('magazine_capacity', 0)
        if self.current_ammo > max_mag:
            self.current_ammo = max_mag

    def refill_magazine_percent(self, percent):
        if percent <= 0:
            return
        max_mag = self.player.stats.get('magazine_capacity', 0)
        amount = max(1, int(math.ceil(max_mag * percent / 100.0)))
        self.current_ammo = min(max_mag, self.current_ammo + amount)

    def restore_hp_percent(self, percent):
        if percent <= 0:
            return
        healed = self.max_hp * (percent / 100.0)
        self.current_hp = min(self.max_hp, self.current_hp + healed)

    def apply_shield(self, percent_of_max_hp=None, flat_value=None, duration_seconds=0, max_percent=None):
        shield_value = 0.0
        if percent_of_max_hp:
            shield_value += self.max_hp * (percent_of_max_hp / 100.0)
        if flat_value:
            shield_value += float(flat_value)
        if shield_value <= 0:
            return
        max_cap = self.max_hp * (max_percent / 100.0) if max_percent else None
        self.current_shield += shield_value
        if max_cap is not None:
            self.current_shield = min(self.current_shield, max_cap)
        self.shield_end_time = max(self.shield_end_time, time.time() + duration_seconds)
        self.status_stack_counts['shielded'] = 1
        self.player_status_expirations = [
            entry for entry in self.player_status_expirations if entry['status'] != 'shielded'
        ]
        self.player_status_expirations.append({'status': 'shielded', 'end_time': self.shield_end_time})
        self.refresh_player_stats()

    def reduce_status_stacks_percent(self, status, percent):
        count = self.mannequin_status_stacks.get(status, 0)
        if count <= 0:
            return
        keep_count = max(0, int(math.floor(count * max(0.0, 100.0 - percent) / 100.0)))
        if keep_count <= 0:
            self.mannequin_status_stacks.pop(status, None)
            self.mannequin_status_effects.pop(status, None)
            self.mannequin.effects.pop(status, None)
            self.mannequin_status_expirations = [
                entry for entry in self.mannequin_status_expirations if entry['status'] != status
            ]
        else:
            self.mannequin_status_stacks[status] = keep_count
            entries = [entry for entry in self.mannequin_status_expirations if entry['status'] == status]
            entries.sort(key=lambda entry: entry['end_time'], reverse=True)
            kept_entries = entries[:keep_count]
            self.mannequin_status_expirations = [
                entry for entry in self.mannequin_status_expirations if entry['status'] != status
            ] + kept_entries

    def extend_status_duration(self, status, duration_seconds):
        if duration_seconds <= 0:
            return
        updated = False
        for entry in self.mannequin_status_expirations:
            if entry['status'] == status:
                entry['end_time'] += duration_seconds
                updated = True
        for entry in self.player_status_expirations:
            if entry['status'] == status:
                entry['end_time'] += duration_seconds
                updated = True
        if updated:
            self.mannequin_status_effects[status] = max(
                [entry['end_time'] for entry in self.mannequin_status_expirations if entry['status'] == status] or [0]
            )

    def extend_mode_duration(self, mode_name, duration_seconds):
        if duration_seconds <= 0 or not mode_name:
            return
        self.mode_expirations[mode_name] = max(
            self.mode_expirations.get(mode_name, 0.0),
            time.time(),
        ) + duration_seconds
        self.current_mode = mode_name

    def set_mode(self, mode_name, duration_seconds):
        if not mode_name:
            return
        self.current_mode = mode_name
        self.mode_expirations[mode_name] = time.time() + max(duration_seconds, 0)
        self.refresh_player_stats()

    def clear_mode(self, mode_name=None):
        if mode_name and self.current_mode != mode_name:
            return
        ended_mode = self.current_mode
        if ended_mode:
            self.mode_expirations.pop(ended_mode, None)
        self.current_mode = None
        self.refresh_player_stats()
        if ended_mode:
            self.process_combat_event(f'{ended_mode}_end')

    def get_stats_display_text(self, player):
        stats_text = f"{self.get_text('stats_title', 'Current character stats')}:\n\n"
        stats_text += (
            f"{self.get_text('mannequin_hp', 'Target dummy HP')}: "
            f"{self.format_value(self.mannequin.current_hp, hp_value=True)}/"
            f"{self.format_value(self.mannequin.max_hp, hp_value=True)}\n"
        )
        stats_text += f"{self.get_text('mannequin_status', 'Target dummy status')}: {self.mannequin.status}\n"
        stats_text += (
            f"{self.get_text('mannequin_enemy_type', 'Target dummy enemy type')}: "
            f"{self.format_enemy_type(self.mannequin.enemy_type)}\n"
        )
        if self.mannequin.effects:
            stats_text += f"{self.get_text('mannequin_effects', 'Effects on target dummy')}:\n"
            for effect in self.mannequin.effects:
                stats_text += f"- {effect}\n"
        stats_to_display = [
            'damage_per_projectile', 'crit_rate_percent', 'crit_damage_percent',
            'weapon_damage_percent', 'status_damage_percent', 'movement_speed_percent',
            'elemental_damage_percent', 'weakspot_damage_percent', 'reload_time_seconds',
            'magazine_capacity', 'damage_bonus_normal', 'damage_bonus_elite',
            'damage_bonus_boss', 'pollution_resist', 'psi_intensity', 'fire_rate',
            'projectiles_per_shot'
        ]
        for stat in stats_to_display:
            value = player.stats.get(stat, getattr(self, stat, 0))
            stats_text += f"{self.format_stat_name(stat)}: {self.format_value(value)}\n"
        stats_text += f"\n{self.get_text('equipped_items', 'Equipped items')}:\n"
        for item_type, item in player.equipped_items.items():
            stats_text += (
                f"{item.name} ({item_type.capitalize()}): "
                f"{self.get_text('stars', 'Stars')}: {item.star}, "
                f"{self.get_text('level', 'Level')}: {item.level}, "
                f"{self.get_text('calibration', 'Calibration')}: {item.calibration}\n"
            )
            item_stats = item.get_stats()
            for stat_name, stat_value in item_stats.items():
                stats_text += f"  {self.format_stat_name(stat_name)}: {self.format_value(stat_value)}\n"
        if player.weapon:
            stats_text += f"\n{self.get_text('weapon', 'Weapon')}: {player.weapon.name}\n"
            for stat_name, stat_value in player.weapon.get_stats().items():
                stats_text += f"  {self.format_stat_name(stat_name)}: {self.format_value(stat_value)}\n"
        if self.mannequin_status_effects:
            stats_text += f"\n{self.get_text('status_effects', 'Status effects')}:\n"
            for key, val in self.mannequin_status_effects.items():
                stats_text += f"{key}: {self.format_value(val)}\n"
        return stats_text

    def initialize(self):
        self.player.effect_sources_dirty = True
        self.mannequin_status_effects.clear()
        self.mannequin_status_expirations.clear()
        self.mannequin_status_stacks.clear()
        self.mannequin_status_payloads.clear()
        self.player_status_expirations.clear()
        self.status_stack_counts.clear()
        self.counters.clear()
        self.stacks.clear()
        self.buffs.clear()
        self.current_mode = None
        self.mode_expirations.clear()
        self.current_shield = 0.0
        self.shield_end_time = 0.0
        self.refresh_player_stats()
        self.update_max_hp()
        self.current_hp = self.max_hp
        self.current_ammo = self.player.stats.get('magazine_capacity', 0)

    def update(self):
        self.mannequin.update_effects(delta_time=time.time() - self.last_update_time)
        self.last_update_time = time.time()
        self.update_status_effects()
        if self.reloading and time.time() >= self.reload_end_time:
            self.reloading = False
            self.current_ammo = self.player.stats.get('magazine_capacity', 0)
            logging.info(f"Reload complete. Ammo replenished to {self.current_ammo}")
        self.dps = self.calculate_dps()
        self.player.update_active_stat_bonuses()
        self.update_max_hp()

    def update_dps_display(self):
        dps_text = f"DPS: {int(self.dps)}    Total DMG: {int(self.total_damage)}"
        dpg.set_value("dps_text", dps_text)
        ammo_text = (f"Патроны: {self.current_ammo}/"
                     f"{self.player.stats.get('magazine_capacity', 0)}")
        dpg.set_value("ammo_text", ammo_text)

    def update_damage_layer(self):
        current_time = time.time()
        for item in self.scheduled_deletions[:]:
            elapsed = current_time - item['start_time']
            if elapsed > item['duration']:
                try:
                    dpg.delete_item(item['id'])
                except Exception as e:
                    logging.error(f"Error deleting damage text {item['id']}: {e}")
                self.scheduled_deletions.remove(item)
            else:
                dx = item['velocity'][0] * (1 / 60)
                dy = item['velocity'][1] * (1 / 60)
                new_pos = [
                    item['start_pos'][0] + dx,
                    item['start_pos'][1] + dy
                ]
                alpha = max(0, int(255 * (1 - elapsed / item['duration'])))
                color = item['color'][:3] + [alpha]
                try:
                    dpg.configure_item(item['id'], pos=new_pos, color=color)
                    item['start_pos'] = new_pos
                except Exception as e:
                    logging.error(f"Error updating damage text {item['id']}: {e}")

    def try_fire_weapon(self):
        if not self.player.weapon:
            return
        if self.mouse_pressed:
            current_time = time.time()
            fire_rate = self.player.stats.get('fire_rate', 600.0)
            time_between_shots = 60.0 / fire_rate
            if current_time - self.last_fire_time >= time_between_shots:
                if self.current_ammo <= 0:
                    self.reload_weapon()
                    return
                self.current_ammo -= 1
                self.magazine_bullets_fired += 1
                self.last_fire_time = current_time
                self.process_combat_event('shot_fired')
                if self.current_ammo == 0:
                    self.process_combat_event('mag_empty')
                projectiles_per_shot = int(self.player.weapon.get_stats().get('projectiles_per_shot', 1))
                total_shot_damage = 0
                damage_list = []
                for _ in range(projectiles_per_shot):
                    current_mouse_pos = dpg.get_mouse_pos(local=False)
                    self.last_shot_mouse_pos = current_mouse_pos
                    hit_pos = self.simulate_projectile_hit(current_mouse_pos)
                    weakspot_hit = self.is_weakspot_hit(hit_pos)
                    damage, is_crit = self.damage_calculator.calculate_damage_per_projectile(weakspot_hit)
                    total_shot_damage += damage
                    damage_list.append((damage, hit_pos, is_crit, weakspot_hit))
                self.all_projectiles_hit = all(self.is_within_target_area(entry[1]) for entry in damage_list)
                if self.all_projectiles_hit:
                    self.process_combat_event('all_projectiles_hit')
                if any(entry[3] for entry in damage_list):
                    self.magazine_weakspot_hits += 1
                self.total_damage += total_shot_damage
                self.damage_history.append((current_time, total_shot_damage))
                if self.mannequin.show_unified_shotgun_damage:
                    center_pos = self.get_center_of_hit_area()
                    self.display_damage_number(total_shot_damage, center_pos,
                                               any(d[2] for d in damage_list),
                                               any(d[3] for d in damage_list))
                else:
                    for dmg_val, hit_pos, is_crit, weakspot_hit in damage_list:
                        self.display_damage_number(dmg_val, hit_pos, is_crit, weakspot_hit)
                self.mannequin.receive_damage(total_shot_damage)
                self.process_hit(any(d[2] for d in damage_list), any(d[3] for d in damage_list))
                self.handle_target_defeat(any(d[2] for d in damage_list), any(d[3] for d in damage_list))

    def get_center_of_hit_area(self):
        normal_zone = {
            'left': 90,
            'right': 210,
            'top': 80,
            'bottom': 320
        }
        x_center = (normal_zone['left'] + normal_zone['right']) / 2
        y_center = (normal_zone['top'] + normal_zone['bottom']) / 2
        if not dpg.does_item_exist("damage_layer"):
            return (x_center, y_center)
        window_pos = dpg.get_item_rect_min("damage_layer")
        return (window_pos[0] + x_center, window_pos[1] + y_center)

    def process_hit(self, is_crit, is_weakspot):
        self.process_combat_event('hit_target', is_crit=is_crit, is_weakspot=is_weakspot)
        if self.is_status_active('the_bulls_eye'):
            self.process_combat_event('hit_marked_enemy', is_crit=is_crit, is_weakspot=is_weakspot)
        if self.is_status_active('burn'):
            self.process_combat_event('hit_burned_target', is_crit=is_crit, is_weakspot=is_weakspot)
        if is_crit:
            self.process_combat_event('crit_hit', is_crit=True, is_weakspot=is_weakspot)
        if is_weakspot:
            self.process_combat_event('weakspot_hit', is_crit=is_crit, is_weakspot=True)
            if self.is_status_active('burn'):
                self.process_combat_event('weakspot_hit_burned_target', is_crit=is_crit, is_weakspot=True)

    def process_combat_event(self, event_name, **kwargs):
        self.mechanics_processor.process_event(event_name, **kwargs)
        self.refresh_player_stats()

    def is_within_target_area(self, mouse_pos):
        normal_zone = {
            'left': 90,
            'right': 210,
            'top': 80,
            'bottom': 320
        }
        weakspot_rect = {
            'left': 130,
            'right': 170,
            'top': 40,
            'bottom': 80
        }
        x, y = mouse_pos
        window_pos = dpg.get_item_rect_min("damage_layer")
        local_x = x - window_pos[0]
        local_y = y - window_pos[1]
        if ((normal_zone['left'] <= local_x <= normal_zone['right']
             and normal_zone['top'] <= local_y <= normal_zone['bottom']) or
            (weakspot_rect['left'] <= local_x <= weakspot_rect['right']
             and weakspot_rect['top'] <= local_y <= weakspot_rect['bottom'])):
            return True
        else:
            return False

    def is_weakspot_hit(self, mouse_pos):
        weakspot_rect = {
            'left': 130,
            'right': 170,
            'top': 40,
            'bottom': 80
        }
        x, y = mouse_pos
        window_pos = dpg.get_item_rect_min("damage_layer")
        local_x = x - window_pos[0]
        local_y = y - window_pos[1]
        return (weakspot_rect['left'] <= local_x <= weakspot_rect['right']
                and weakspot_rect['top'] <= local_y <= weakspot_rect['bottom'])

    def reload_weapon(self):
        if not self.reloading:
            reload_time = self.player.stats.get('reload_time_seconds', 1.0)
            if self.magazine_bullets_fired > 0:
                self.last_magazine_weakspot_rate = (self.magazine_weakspot_hits / self.magazine_bullets_fired) * 100.0
            else:
                self.last_magazine_weakspot_rate = 0.0
            self.reloading = True
            self.reload_end_time = time.time() + reload_time
            self.current_ammo = 0
            self.process_combat_event('reload_weapon')
            self.process_combat_event('reload')
            self.process_combat_event('reload_empty_magazine')
            self.process_combat_event('reload_empty_mag')
            self.magazine_bullets_fired = 0
            self.magazine_weakspot_hits = 0
            logging.info(f"Reloading weapon. It will take {reload_time} seconds.")

    def calculate_dps(self):
        current_time = time.time()
        recent_damage = [d for t, d in self.damage_history if current_time - t <= 1.0]
        self.damage_history[:] = [(t, d) for t, d in self.damage_history if current_time - t <= 1.0]
        return sum(recent_damage)

    def update_status_effects(self):
        current_time = time.time()
        changed = False
        for status, payload in list(self.mannequin_status_payloads.items()):
            if status not in self.mannequin_status_effects:
                continue
            damage_formula = payload.get('damage_formula')
            if not damage_formula:
                continue
            tick_interval = max(payload.get('tick_interval', 1.0), 0.1)
            next_tick = payload.get('next_tick', 0.0)
            if current_time < next_tick:
                continue
            stacks = max(1, self.mannequin_status_stacks.get(status, 1))
            damage_type = payload.get('damage_type', status)
            if damage_type == 'burn':
                dmg = self.calculate_status_damage(
                    self.resolve_damage_formula(damage_formula),
                    damage_type,
                    ['burn_damage_percent'],
                ) * stacks
                self.apply_direct_damage(dmg, is_crit=False, weakspot_hit=False, ability_name='burn')
                self.process_combat_event('deal_burn_damage', is_crit=False, is_weakspot=False)
            elif damage_type == 'frost':
                dmg = self.calculate_status_damage(
                    self.resolve_damage_formula(damage_formula),
                    damage_type,
                    ['frost_vortex_damage_percent'],
                ) * stacks
                self.apply_direct_damage(dmg, is_crit=False, weakspot_hit=False, ability_name='frost_vortex')
            elif damage_type == 'shock':
                dmg = self.calculate_status_damage(
                    self.resolve_damage_formula(damage_formula),
                    damage_type,
                    ['shock_damage_percent', 'power_surge_damage_percent'],
                ) * stacks
                self.apply_direct_damage(dmg, is_crit=False, weakspot_hit=False, ability_name='power_surge')
                self.process_combat_event('deal_power_surge_damage', is_crit=False, is_weakspot=False)
            payload['next_tick'] = current_time + tick_interval
        expired_target_effects = [entry for entry in self.mannequin_status_expirations if current_time >= entry['end_time']]
        for entry in expired_target_effects:
            status = entry['status']
            self.mannequin_status_expirations.remove(entry)
            current_stacks = self.mannequin_status_stacks.get(status, 0)
            if current_stacks <= 1:
                self.mannequin_status_stacks.pop(status, None)
                self.mannequin_status_effects.pop(status, None)
                self.mannequin.effects.pop(status, None)
                self.mannequin_status_payloads.pop(status, None)
                if status == 'burn':
                    self.process_combat_event('burn_removed', is_crit=False, is_weakspot=False)
                elif status == 'frost_vortex':
                    self.process_combat_event('frost_vortex_disappear', is_crit=False, is_weakspot=False)
            else:
                self.mannequin_status_stacks[status] = current_stacks - 1
                remaining = max(
                    [item['end_time'] for item in self.mannequin_status_expirations if item['status'] == status] or [0.0]
                )
                if remaining > 0:
                    self.mannequin_status_effects[status] = remaining
            changed = True

        expired_player_effects = [entry for entry in self.player_status_expirations if current_time >= entry['end_time']]
        for entry in expired_player_effects:
            status = entry['status']
            self.player_status_expirations.remove(entry)
            current_stacks = self.status_stack_counts.get(status, 0)
            if current_stacks <= 1:
                self.status_stack_counts.pop(status, None)
            else:
                self.status_stack_counts[status] = current_stacks - 1
            changed = True
        if self.current_shield > 0 and current_time >= self.shield_end_time:
            self.current_shield = 0.0
            self.status_stack_counts.pop('shielded', None)
            self.player_status_expirations = [
                entry for entry in self.player_status_expirations if entry['status'] != 'shielded'
            ]
            changed = True
        if self.current_mode:
            mode_end = self.mode_expirations.get(self.current_mode, 0.0)
            if mode_end and current_time >= mode_end:
                self.process_combat_event(f'{self.current_mode}_end', is_crit=False, is_weakspot=False)
                self.clear_mode(self.current_mode)
                changed = True
        if changed:
            self.refresh_player_stats()

    def simulate_projectile_hit(self, mouse_pos):
        spread_radius = 15
        angle = random.uniform(0, 2 * math.pi)
        radius = random.uniform(0, spread_radius)
        offset_x = radius * math.cos(angle)
        offset_y = radius * math.sin(angle)
        hit_pos = (mouse_pos[0] + offset_x, mouse_pos[1] + offset_y)
        logging.info(f"Simulated projectile hit at {hit_pos}")
        return hit_pos

    def display_damage_number(self, damage, hit_pos, is_crit, weakspot_hit, ability_name=None):
        if not dpg.does_item_exist("damage_layer"):
            return
        window_pos = dpg.get_item_rect_min("damage_layer")
        local_x = hit_pos[0] - window_pos[0]
        local_y = hit_pos[1] - window_pos[1]
        damage_text_id = dpg.generate_uuid()

        speed = self.damage_text_settings.get('speed', 100)
        fade_delay = self.damage_text_settings.get('fade_delay', 1.0)
        angle_min = math.radians(self.damage_text_settings.get('angle_min', 45))
        angle_max = math.radians(self.damage_text_settings.get('angle_max', 135))

        if weakspot_hit and is_crit:
            color = self.damage_text_settings.get('crit_weakspot_color', [0, 255, 0, 255])
        elif is_crit:
            color = self.damage_text_settings.get('crit_color', [255, 165, 0, 255])
        elif weakspot_hit:
            color = self.damage_text_settings.get('weakspot_color', [255, 0, 0, 255])
        else:
            color = self.damage_text_settings.get('normal_color', [255, 255, 255, 255])

        current_time = time.time()

        dpg.draw_text(
            pos=[local_x, local_y],
            text=str(int(damage)),
            color=color,
            size=20,
            parent="damage_layer",
            tag=damage_text_id
        )

        if ability_name:
            icon_x = local_x - 20
            icon_y = local_y
            tex_id = self.ability_icons.get(ability_name, None)
            if tex_id:
                dpg.draw_image(tex_id,
                               pmin=[icon_x, icon_y],
                               pmax=[icon_x + 10, icon_y + 10],
                               parent="damage_layer")

        angle = random.uniform(angle_min, angle_max)
        vx = speed * math.cos(angle)
        vy = speed * math.sin(angle)

        self.scheduled_deletions.append({
            'id': damage_text_id,
            'start_time': current_time,
            'duration': fade_delay + 1.0,
            'start_pos': [local_x, local_y],
            'velocity': (vx, -vy),
            'color': color
        })

    def create_weapon_instance(self, weapon_data):
        weapon = Weapon(weapon_data)
        return weapon

    def create_item_instance(self, item_data):
        from .player import Item
        item = Item(item_data, self.base_stats, self.calibration_bonuses)
        return item

    def get_attachment_by_id(self, attachment_id):
        return next((attachment for attachment in self.attachments_data if attachment.get('id') == attachment_id), None)

    def get_attachments_for_weapon(self, weapon, slot=None):
        if not weapon:
            return []
        result = []
        for attachment in self.attachments_data:
            if slot and attachment.get('slot') != slot:
                continue
            allowed_types = attachment.get('allowed_weapon_types') or []
            if allowed_types and weapon.type not in allowed_types:
                continue
            result.append(attachment)
        return result

    def create_item_instance_by_id(self, item_id):
        for item_data in self.items_data:
            if item_data.get('id') == item_id:
                return self.create_item_instance(item_data)
        logging.warning(f"Item with id '{item_id}' was not found in items data.")
        return None

    def get_set_by_id(self, set_id):
        for game_set in self.sets_data:
            game_set_id = game_set.get('set_id') or game_set.get('id')
            if game_set_id == set_id:
                return game_set
        return None

    def apply_status(self, status, duration, **kwargs):
        nested_effects = kwargs.get('effects', [])
        normalized_effects = normalize_effects(nested_effects) if nested_effects else []
        if not normalized_effects and kwargs.get('stat_bonuses'):
            normalized_effects = []
            for stat_name, stat_value in kwargs['stat_bonuses'].items():
                if isinstance(stat_value, bool):
                    normalized_effects.append({
                        'type': 'set_flag',
                        'flag': stat_name,
                        'value': stat_value,
                    })
                else:
                    normalized_effects.append({
                        'type': 'increase_stat',
                        'stat': stat_name,
                        'value': stat_value,
                    })
        if normalized_effects:
            end_time = time.time() + duration
            max_stacks = kwargs.get('max_stacks')
            stat_cap = self.player.stats.get(f"max_{status}_stacks")
            if stat_cap is not None:
                max_stacks = max(max_stacks or 0, int(stat_cap))

            current_stacks = self.status_stack_counts.get(status, 0)
            if max_stacks and current_stacks >= max_stacks:
                matching_entries = [entry for entry in self.player_status_expirations if entry['status'] == status]
                if matching_entries:
                    oldest_entry = min(matching_entries, key=lambda entry: entry['end_time'])
                    oldest_entry['end_time'] = end_time
                return

            applied_bonus = False
            for effect in normalized_effects:
                if effect.get('type') == 'increase_stat':
                    source_name = effect.get('source', status)
                    for stat, value in iter_stat_value_pairs(effect):
                        if stat:
                            was_added = self.player.apply_stat_bonus(
                                stat,
                                value,
                                duration,
                                max_stacks=max_stacks,
                                source=source_name,
                            )
                            applied_bonus = applied_bonus or was_added
                elif effect.get('type') == 'set_flag':
                    source_name = effect.get('source', status)
                    flag_name = effect.get('flag')
                    if flag_name:
                        was_added = self.player.apply_stat_bonus(
                            flag_name,
                            1 if effect.get('value') else 0,
                            duration,
                            max_stacks=max_stacks,
                            source=source_name,
                        )
                        applied_bonus = applied_bonus or was_added
            if applied_bonus or status not in self.status_stack_counts:
                self.status_stack_counts[status] = min(current_stacks + 1, max_stacks or current_stacks + 1)
                self.player_status_expirations.append({'status': status, 'end_time': end_time})
            logging.debug(f"Player status {status} applied for {duration} seconds.")
            return

        end_time = time.time() + duration
        max_stacks = kwargs.get('max_stacks')
        current_stacks = self.mannequin_status_stacks.get(status, 0)
        if max_stacks and current_stacks >= max_stacks:
            matching_entries = [entry for entry in self.mannequin_status_expirations if entry['status'] == status]
            if matching_entries:
                oldest_entry = min(matching_entries, key=lambda entry: entry['end_time'])
                oldest_entry['end_time'] = end_time
        else:
            self.mannequin_status_expirations.append({'status': status, 'end_time': end_time})
            self.mannequin_status_stacks[status] = min(current_stacks + 1, max_stacks or current_stacks + 1)
        self.mannequin_status_effects[status] = max(
            [entry['end_time'] for entry in self.mannequin_status_expirations if entry['status'] == status] or [end_time]
        )
        payload = self.mannequin_status_payloads.get(status, {}).copy()
        payload.update(kwargs)
        self.mannequin_status_payloads[status] = payload
        self.mannequin.effects[status] = True
        self.mannequin.apply_status(status, duration, **payload)
        logging.debug(f"Status {status} applied for {duration} seconds.")
        if status == 'the_bulls_eye':
            self.process_combat_event('trigger_bulls_eye')

    def remove_buff(self, buff_name):
        if buff_name in self.buffs:
            del self.buffs[buff_name]
            self.refresh_player_stats()
            logging.info(f"Buff {buff_name} removed.")

    def calculate_status_damage(self, base_damage, damage_type, bonus_stats=None):
        damage = float(base_damage)
        bonus_stats = bonus_stats or []
        damage *= 1 + self.player.stats.get('status_damage_percent', 0) / 100.0
        damage *= 1 + self.player.stats.get('elemental_damage_percent', 0) / 100.0
        for stat_name in bonus_stats:
            damage *= 1 + self.player.stats.get(stat_name, 0) / 100.0
        return damage

    def trigger_ability(self, ability_name, **kwargs):
        ability_lower = ability_name.lower()
        logging.info(f"Triggered ability: {ability_name} with {kwargs}")
        if ability_lower == 'unstable_bomber':
            damage_formula = kwargs.get('damage_formula', {'type': 'psi_intensity', 'multiplier': 1.0})
            self.process_combat_event('unstable_bomber_hits_one_enemy', is_crit=False, is_weakspot=False)
            dmg = self.calculate_status_damage(
                self.resolve_damage_formula(damage_formula),
                'blast',
                [
                    'psi_intensity_damage_percent',
                    'explosion_elemental_damage_percent',
                    'unstable_bomber_damage_percent',
                    'unstable_bomber_final_damage_percent',
                ],
            )

            trigger_bonus = self.trigger_factors.get(ability_lower) or self.trigger_factors.get(ability_name)
            if trigger_bonus:
                end_time = trigger_bonus.get('end_time')
                if end_time is None or end_time >= time.time():
                    dmg *= 1 + trigger_bonus.get('bonus', 0) / 100.0

            additional_info = kwargs.get('additional_info', {})
            can_crit = kwargs.get('can_crit', additional_info.get('can_crit', False)) or self.player.stats.get('can_crit', False)
            is_crit = False
            if can_crit and random.uniform(0, 100) <= self.player.stats.get('crit_rate_percent', 0):
                is_crit = True
                dmg *= 1 + self.player.stats.get('crit_damage_percent', 0) / 100.0

            self.apply_direct_damage(dmg, is_crit=is_crit, weakspot_hit=False, ability_name='unstable_bomber')
            self.apply_status('unstable_bomber', 5)
            self.process_combat_event('trigger_unstable_bomber', is_crit=is_crit, is_weakspot=False)
            self.process_combat_event('deal_explosion_damage', is_crit=is_crit, is_weakspot=False)
            self.counters['shots_towards_bomber_trigger'] = 0
            return

        if ability_lower == 'shrapnel':
            damage_formula = kwargs.get('damage_formula', {'type': 'attack', 'multiplier': 0.5})
            dmg = self.resolve_damage_formula(damage_formula)
            dmg *= 1 + self.player.stats.get('weapon_damage_percent', 0) / 100.0
            dmg *= 1 + self.player.stats.get('shrapnel_damage_percent', 0) / 100.0
            is_crit = kwargs.get('can_crit', False) and random.uniform(0, 100) <= self.player.stats.get('crit_rate_percent', 0)
            if is_crit:
                dmg *= 1 + self.player.stats.get('crit_damage_percent', 0) / 100.0
            self.apply_direct_damage(dmg, is_crit=is_crit, weakspot_hit=False, ability_name='shrapnel')
            self.process_combat_event('trigger_shrapnel', is_crit=is_crit, is_weakspot=False)
            return

        if ability_lower == 'power_surge':
            damage_formula = kwargs.get('damage_formula', {'type': 'psi_intensity', 'multiplier': 0.5})
            dmg = self.calculate_status_damage(
                self.resolve_damage_formula(damage_formula),
                'shock',
                ['shock_damage_percent', 'power_surge_damage_percent'],
            )
            trigger_bonus = self.trigger_factors.get(ability_lower) or self.trigger_factors.get(ability_name)
            if trigger_bonus:
                end_time = trigger_bonus.get('end_time')
                if end_time is None or end_time >= time.time():
                    dmg *= 1 + trigger_bonus.get('bonus', 0) / 100.0
            self.apply_direct_damage(dmg, is_crit=False, weakspot_hit=False, ability_name='power_surge')
            duration = 6.0 * (1 + self.player.stats.get('power_surge_duration_percent', 0) / 100.0)
            self.apply_status('power_surge', max(duration, 0.5))
            self.process_combat_event('trigger_power_surge', is_crit=False, is_weakspot=False)
            self.process_combat_event('deal_power_surge_damage', is_crit=False, is_weakspot=False)
            self.process_combat_event('shock_damage_dealt', is_crit=False, is_weakspot=False)
            return

        if ability_lower == 'celestial_thunder':
            damage_formula = kwargs.get('damage_formula', {'type': 'psi_intensity', 'multiplier': 2.0})
            dmg = self.calculate_status_damage(
                self.resolve_damage_formula(damage_formula),
                'shock',
                ['shock_damage_percent', 'power_surge_damage_percent'],
            )
            self.apply_direct_damage(dmg, is_crit=False, weakspot_hit=False, ability_name='power_surge')
            self.process_combat_event('deal_power_surge_damage', is_crit=False, is_weakspot=False)
            return

        if ability_lower == 'burn':
            damage_formula = kwargs.get('damage_formula', {'type': 'psi_intensity', 'multiplier': 0.4})
            duration = kwargs.get('duration_seconds', 6.0)
            payload = {
                'damage_formula': damage_formula,
                'damage_type': 'burn',
                'tick_interval': kwargs.get('tick_interval_seconds', 1.0),
            }
            self.apply_status('burn', duration, max_stacks=kwargs.get('max_stacks'), **payload)
            self.process_combat_event('trigger_burn', is_crit=False, is_weakspot=False)
            return

        if ability_lower == 'frost_vortex':
            damage_formula = kwargs.get('damage_formula', {'type': 'psi_intensity', 'multiplier': 0.6})
            dmg = self.calculate_status_damage(
                self.resolve_damage_formula(damage_formula),
                'frost',
                ['frost_vortex_damage_percent'],
            )
            self.apply_direct_damage(dmg, is_crit=False, weakspot_hit=False, ability_name='frost_vortex')
            self.apply_status('frost_vortex', kwargs.get('duration_seconds', 6.0))
            self.process_combat_event('trigger_frost_vortex', is_crit=False, is_weakspot=False)
            self.process_combat_event('frost_vortex_triggered', is_crit=False, is_weakspot=False)
            return

        if ability_lower == 'fortress_warfare':
            self.set_mode('fortress_warfare', kwargs.get('duration_seconds', 8.0))
            self.apply_status('fortress_warfare', kwargs.get('duration_seconds', 8.0))
            self.process_combat_event('fortress_warfare_triggered', is_crit=False, is_weakspot=False)
            return

    def check_status_on_target(self, status_to_check):
        return status_to_check in self.mannequin_status_effects or status_to_check in self.mannequin.effects

    def get_player_hp_ratio(self):
        if self.max_hp > 0:
            return self.current_hp / self.max_hp
        return 1.0

    def get_count_for_event(self, event_name):
        return self.counters.get(event_name, 0)

    def modify_event_chance(self, base_event, new_chance_percent):
        self.event_chance_modifiers[base_event] = new_chance_percent
        logging.debug(f"Event {base_event} chance changed to {new_chance_percent}%")

    def increment_counter(self, counter, value=1):
        self.counters[counter] = self.counters.get(counter, 0) + value
        logging.debug(f"Counter {counter} incremented by {value}. New value: {self.counters[counter]}")

    def increment_hit_count(self, value):
        self.increment_counter('hit_count', value)

    def check_counter(self, event_name, n):
        current_val = self.counters.get(event_name, 0)
        if current_val >= n:
            self.counters[event_name] = 0
            return True
        return False

    def apply_temporary_stat_bonus(self, stat, value, duration, max_stacks=None, source=None):
        self.player.apply_stat_bonus(stat, value, duration, max_stacks, source=source)

    def gain_stacks(self, stack_type, count):
        current = self.stacks.get(stack_type, 0)
        max_from_stats = self.player.stats.get(f'max_{stack_type}_stacks')
        new_value = current + count
        if isinstance(max_from_stats, (int, float)) and max_from_stats > 0:
            new_value = min(new_value, int(max_from_stats))
        self.stacks[stack_type] = new_value
        self.refresh_player_stats()
        logging.debug(f"Stacks {stack_type} gained {count}, total: {self.stacks[stack_type]}")

    def reduce_stacks(self, stack_type, value):
        current = self.stacks.get(stack_type, 0)
        new_val = max(0, current - value)
        self.stacks[stack_type] = new_val
        self.refresh_player_stats()
        logging.debug(f"Stacks {stack_type} reduced by {value}, total: {new_val}")

    def reduce_stacks_percent(self, stack_type, percent):
        current = self.stacks.get(stack_type, 0)
        new_val = max(0, int(current * max(0.0, 100.0 - percent) / 100.0))
        self.stacks[stack_type] = new_val
        self.refresh_player_stats()
        logging.debug(f"Stacks {stack_type} reduced by {percent}%, total: {new_val}")

    def spread_effect(self, radius_meters, effect_data):
        logging.info(f"Spread effect in {radius_meters}m with {effect_data}")

    def generate_ice_crystal(self, cooldown_seconds):
        logging.info(f"Generated Ice Crystal, cooldown: {cooldown_seconds}s")

    def deal_status_damage(self, damage_formula, damage_type, radius_meters):
        logging.info(f"Deal status dmg {damage_formula} of type {damage_type} in radius {radius_meters}m")

    def shatter_ice_crystal(self, damage_formula, damage_type):
        logging.info(f"Shatter Ice Crystal, dmg: {damage_formula}, type: {damage_type}")

    def grant_infinite_ammo(self, duration_seconds):
        self.infinite_ammo_until = time.time() + duration_seconds
        logging.debug(f"Infinite ammo granted for {duration_seconds} s")

    def increase_projectiles_per_shot(self, additional_projectiles):
        self.player.stats['projectiles_per_shot'] = (self.player.stats.get('projectiles_per_shot', 1)
                                                     + additional_projectiles)
        logging.debug(f"Projectiles per shot increased by {additional_projectiles}")

    def apply_buff(self, buff_name, duration_bullets=None, stat_bonuses=None):
        if stat_bonuses:
            for stat, val in stat_bonuses.items():
                self.apply_temporary_stat_bonus(stat, val, 5)
        self.buffs[buff_name] = {'duration_bullets': duration_bullets, 'stat_bonuses': stat_bonuses}
        logging.info(f"Buff {buff_name} applied with {stat_bonuses}")

    def modify_behavior(self, behavior, enabled):
        logging.info(f"Behavior {behavior} set to {enabled}")

    def reload_ammo(self, amount=1):
        max_mag = self.player.stats.get('magazine_capacity', 0)
        self.current_ammo = min(self.current_ammo + amount, max_mag)
        logging.info(f"Reload ammo by {amount}, current ammo: {self.current_ammo}/{max_mag}")

    def restore_bullet(self, amount=1):
        max_mag = self.player.stats.get('magazine_capacity', 0)
        self.current_ammo = min(self.current_ammo + amount, max_mag)
        logging.info(f"Restored {amount} bullet(s), current ammo: {self.current_ammo}/{max_mag}")

    def refill_bullet(self):
        self.restore_bullet(1)

    def consume_extra_ammo(self, amount):
        self.current_ammo = max(0, self.current_ammo - amount)
        logging.info(f"Consumed extra ammo: {amount}, current ammo: {self.current_ammo}")

    def spawn_pickup(self, pickup_type):
        logging.info(f"Spawned pickup {pickup_type}")

    def modify_ammo_type(self, ammo_type, duration_until_reload):
        self.alternate_ammo = ammo_type
        self.alternate_ammo_until_reload = duration_until_reload
        logging.info(f"Ammo type changed to {ammo_type}, revert on reload: {duration_until_reload}")

    def consume_charge(self, effect_data):
        if self.charge_stacks > 0:
            self.charge_stacks -= 1
            logging.info(f"Consumed one charge stack. {effect_data}")
        else:
            logging.info("No charges to consume.")

    def area_damage(self, damage_percent, damage_type):
        logging.info(f"Dealt area damage {damage_percent}% {damage_type}")

    def modify_trigger_factor(self, ability, bonus_percent, duration_seconds=None):
        self.trigger_factors[ability] = {'bonus': bonus_percent,
                                         'end_time': (time.time() + duration_seconds
                                                      if duration_seconds else None)}
        logging.info(f"Trigger factor for {ability} modified by {bonus_percent}% for {duration_seconds} s")

    def check_custom_condition(self, condition):
        return True

    def apply_direct_damage(self, damage, is_crit=False, weakspot_hit=False, ability_name=None):
        center_pos = self.get_center_of_hit_area()
        self.mannequin.receive_damage(damage)
        self.total_damage += damage
        self.damage_history.append((time.time(), damage))
        self.display_damage_number(damage, center_pos, is_crit, weakspot_hit, ability_name=ability_name)
        self.handle_target_defeat(is_crit, weakspot_hit)

    def resolve_damage_formula(self, damage_formula):
        if not isinstance(damage_formula, dict):
            return float(self.player.stats.get('psi_intensity', 100))
        formula_type = damage_formula.get('type', 'psi_intensity')
        multiplier = damage_formula.get('multiplier', 1.0)
        alias_map = {
            'attack': 'damage_per_projectile',
            'weapon_attack': 'damage_per_projectile',
        }
        formula_type = alias_map.get(formula_type, formula_type)
        if formula_type == 'psi_intensity':
            return float(self.player.stats.get('psi_intensity', 100)) * multiplier
        stat_value = self.player.stats.get(formula_type, self.player.stats.get('psi_intensity', 100))
        return float(stat_value) * multiplier

    def handle_target_defeat(self, is_crit=False, weakspot_hit=False):
        if self.mannequin.current_hp > 0 or self.enemy_defeated_pending_reset:
            return
        was_marked = self.is_status_active('the_bulls_eye')
        had_burn = self.is_status_active('burn')
        self.enemy_defeated_pending_reset = True
        self.process_combat_event('kill', is_crit=is_crit, is_weakspot=weakspot_hit)
        self.process_combat_event('defeat_enemy', is_crit=is_crit, is_weakspot=weakspot_hit)
        if weakspot_hit:
            self.process_combat_event('defeat_enemy_with_weakspot_hit', is_crit=is_crit, is_weakspot=True)
        if was_marked:
            self.process_combat_event('defeat_marked_enemy', is_crit=is_crit, is_weakspot=weakspot_hit)
        if had_burn:
            self.process_combat_event('kill_enemy_with_burn', is_crit=is_crit, is_weakspot=weakspot_hit)
            self.process_combat_event('defeat_enemy_with_burn', is_crit=is_crit, is_weakspot=weakspot_hit)

    # ------------------------- Добавлен фикс: --------------------------
    def get_mod_texture_id(self, mod_key, mod_name_key):
        """
        Возвращает texture_id для модификатора, если он загружен;
        иначе None (тогда будет использован fallback).
        Предполагается, что self.mod_images хранится где-то в CalcAndModTab
        или нужно загружать изображения прямо тут.
        Для примера используем локальную папку data/icons/mods/.
        """
        # Попробуем найти файл "[mod_name_key].png" в папке data/icons/mods/[mod_key]
        folder = os.path.join('data', 'icons', 'mods', mod_key)
        if not os.path.isdir(folder):
            return None

        candidates = [
            mod_name_key + '.png',
            mod_name_key.replace('_', ' ') + '.png',
        ]
        for filename in os.listdir(folder):
            normalized = os.path.splitext(filename)[0].lower().replace(' ', '_')
            if normalized == mod_name_key:
                candidates.append(filename)
                break

        for filename in candidates:
            full_path = os.path.join(folder, filename)
            if not os.path.isfile(full_path):
                continue
            width, height, channels, data = dpg.load_image(full_path)
            with dpg.texture_registry():
                texture_id = dpg.add_static_texture(width, height, data)
            return texture_id

        return None

    def remove_mod_from_slot(self, sender, app_data, user_data):
        """
        Вызывается при нажатии "Ничего/Убрать" в окне выбора мода.
        Убираем мод из слота (item_type).
        """
        item_type = user_data
        self.player.remove_mod(item_type)
        logging.debug(f"Mod removed from slot '{item_type}'")

        if dpg.does_item_exist("mod_selection_window"):
            dpg.configure_item("mod_selection_window", show=False)

    def select_mod_for_slot(self, sender, app_data, user_data):
        """При выборе конкретного мода в таблице."""
        mod = user_data['mod']
        item_type = user_data['type']
        self.player.equip_mod(mod, item_type)
        logging.debug(f"Mod '{mod['name']}' equipped to slot '{item_type}'")

        if dpg.does_item_exist("mod_selection_window"):
            dpg.configure_item("mod_selection_window", show=False)

    def open_mod_config_window(self, sender, app_data, user_data):
        """По правому клику на иконку мода — открываем окно с описанием."""
        mod = user_data['mod']
        item_type = user_data['type']
        window_tag = f"{mod['name']}_config_window"
        if dpg.does_item_exist(window_tag):
            dpg.delete_item(window_tag)
        window_width = 400
        window_height = 300
        main_window_pos = dpg.get_viewport_pos()
        main_window_width = dpg.get_viewport_width()
        main_window_height = dpg.get_viewport_height()
        x_pos = main_window_pos[0] + (main_window_width - window_width) / 2
        y_pos = main_window_pos[1] + (main_window_height - window_height) / 2 - 100
        with dpg.window(label=f"Настройка мода {mod['name']}",
                        modal=True, show=True, tag=window_tag,
                        width=window_width, height=window_height,
                        pos=(x_pos, y_pos)):
            dpg.add_text(f"Мод: {mod['name']}")
            if 'description' in mod:
                dpg.add_text(mod['description'], wrap=380)
            dpg.add_button(label="Закрыть", callback=lambda: dpg.delete_item(window_tag))

    def populate_mod_selection_list(self, item_type):
        """
        Заполняет окно выбора мода (mod_selection_window).
        """
        dpg.delete_item("mod_selection_list", children_only=True)
        mod_key = self.category_key_mapping.get(item_type, 'mod_weapon')
        mods = self.mods_data.get(mod_key, [])

        dpg.add_button(label="Ничего/Убрать",
                       callback=self.remove_mod_from_slot,
                       user_data=item_type,
                       parent="mod_selection_list")

        with dpg.table(header_row=False, resizable=True,
                       policy=dpg.mvTable_SizingStretchProp,
                       parent="mod_selection_list"):
            dpg.add_table_column(width=60)
            dpg.add_table_column(width=150)
            dpg.add_table_column()

            for mod in mods:
                mod_name = mod['name']
                mod_name_key = mod_name.lower().replace(' ', '_')
                texture_id = self.get_mod_texture_id(mod_key, mod_name_key)

                # Если нет текстуры, создаём fallback:
                if not texture_id:
                    fallback_tag = f"fallback_{mod_name_key}_{dpg.generate_uuid()}"
                    width, height = 50, 50
                    data = [255, 255, 255, 255] * (width * height)
                    with dpg.texture_registry():
                        dpg.add_static_texture(width, height, data, tag=fallback_tag)
                    texture_id = fallback_tag

                with dpg.table_row():
                    image_tag = f"{mod_name_key}_image_{dpg.generate_uuid()}"
                    dpg.add_image_button(texture_id,
                                         width=85, height=85,
                                         callback=self.select_mod_for_slot,
                                         user_data={'mod': mod, 'type': item_type},
                                         tag=image_tag)

                    handler_tag = f"{mod_name_key}_handler_{dpg.generate_uuid()}"
                    with dpg.item_handler_registry(tag=handler_tag) as handler_id:
                        dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Right,
                                                     callback=self.open_mod_config_window,
                                                     user_data={'mod': mod, 'type': item_type})
                    dpg.bind_item_handler_registry(image_tag, handler_id)

                    dpg.add_button(label=mod_name,
                                   callback=self.select_mod_for_slot,
                                   user_data={'mod': mod, 'type': item_type})
                    if 'description' in mod:
                        dpg.add_text(mod['description'], wrap=300)
