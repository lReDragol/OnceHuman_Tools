import json
import time
import math
import random
import os
import copy
import re
import dearpygui.dearpygui as dpg
from .player import Item, Mannequin, Player
from .mechanics import Weapon, MechanicsProcessor, normalize_effects, iter_stat_value_pairs
from .mod_secondary_attributes import ModSecondaryAttributeCatalog
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DEVIATION_FORMULA_ALLOWED_CHARS = set("0123456789.+-*/() deviation_degree")
DEVIATION_TEXT_PERCENT_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)%")
DEVIATION_TEXT_DURATION_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)秒")
DEVIATION_TEXT_INTERVAL_RE = re.compile(r"每隔([0-9]+(?:\.[0-9]+)?)秒")
DEVIATION_TEXT_TICK_DAMAGE_RE = re.compile(
    r"每(?:(\d+(?:\.\d+)?)秒|秒)[^#\n]{0,120}#\[k=b8\]([0-9]+(?:\.[0-9]+)?)%#l"
)
DEVIATION_TEXT_COOLDOWN_RE = re.compile(
    r"(?:冷却|CD)[:： ]*#?\[?k=b8\]?([0-9]+(?:\.[0-9]+)?)#?l?秒?"
)
DEVIATION_TEXT_STACK_LIMIT_RE = re.compile(
    r"最多叠加#?\[?k=b8\]?([0-9]+(?:\.[0-9]+)?)#?l?层"
)
DEVIATION_TEXT_STACK_GAIN_RE = re.compile(
    r"(?:添加|附加)([0-9]+(?:\.[0-9]+)?)层"
)
DEVIATION_TEXT_MULTI_HIT_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)次")
DEVIATION_TEXT_DIRECT_DAMAGE_RE = re.compile(
    r"造成[^#\n]{0,120}#\[k=b8\]([0-9]+(?:\.[0-9]+)?)%#l"
)
DISPLAY_CJK_RE = re.compile(r"[\u3400-\u9FFF]")

TARGET_BODY_RECT = {
    'left': 90,
    'right': 210,
    'top': 80,
    'bottom': 320,
}

TARGET_WEAKSPOT_RECT = {
    'left': 130,
    'right': 170,
    'top': 40,
    'bottom': 80,
}

PERSISTENT_MANNEQUIN_EFFECT_DEFINITIONS = {
    'burn': {
        'max_stacks': 16,
        'payload': {
            'damage_formula': {'type': 'psi_intensity', 'multiplier': 0.4},
            'damage_type': 'burn',
            'tick_interval': 1.0,
        },
    },
    'special_burn': {
        'max_stacks': 16,
        'payload': {
            'damage_formula': {'type': 'psi_intensity', 'multiplier': 0.4},
            'damage_type': 'burn',
            'tick_interval': 1.0,
        },
    },
    'frost_vortex': {
        'max_stacks': 1,
    },
    'frostbite': {
        'max_stacks': 5,
    },
    'power_surge': {
        'max_stacks': 1,
    },
    'the_bulls_eye': {
        'max_stacks': 1,
    },
    'unstable_bomber': {
        'max_stacks': 1,
    },
    'shielded': {
        'max_stacks': 1,
    },
}

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
        "sprint_speed_percent": "Скорость спринта %",
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
        "ads_stability_percent": "Стабильность при ADS %",
        "raise_weapon_speed_percent": "Скорость вскидывания оружия %",
        "draw_speed_percent": "Скорость доставания оружия %",
        "holster_speed_percent": "Скорость убирания оружия %",
        "bullet_speed": "Скорость пули",
        "min_damage_range_meters": "Начало падения урона (м)",
        "min_damage_percent": "Мин. урон %",
        "damage_reduction_percent": "Снижение урона %",
        "weapon_damage_reduction_percent": "Снижение урона от оружия %",
        "status_damage_reduction_percent": "Снижение статусного урона %",
        "head_damage_reduction_percent": "Снижение урона по голове %",
        "torso_damage_reduction_percent": "Снижение урона по торсу %",
        "limb_damage_reduction_percent": "Снижение урона по конечностям %",
        "weakspot_damage_reduction_percent": "Снижение урона по weakspot %",
        "crit_damage_reduction_percent": "Снижение крит. урона %",
        "burn_elemental_damage_reduction_percent": "Снижение burn-урона %",
        "frost_elemental_damage_reduction_percent": "Снижение frost-урона %",
        "shock_elemental_damage_reduction_percent": "Снижение shock-урона %",
        "fire_explosion_damage_reduction_percent": "Снижение burn/explosion-урона %",
        "frost_shock_damage_reduction_percent": "Снижение frost/shock-урона %",
        "vulnerability_percent": "Уязвимость цели %",
        "explosion_elemental_damage_percent": "Урон взрыва %",
        "tactical_item_damage_percent": "Урон тактических предметов %",
        "unstable_bomber_damage_percent": "Урон Unstable Bomber %",
        "unstable_bomber_final_damage_percent": "Финальный урон Unstable Bomber %",
        "shrapnel_damage_percent": "Урон Shrapnel %",
        "shrapnel_trigger_chance_percent": "Шанс Shrapnel %",
        "bounce_damage_percent": "Урон Bounce %",
        "bounce_trigger_chance_percent": "Шанс Bounce %",
        "bounce_trigger_factor_percent": "Фактор шанса Bounce %",
        "bounce_trigger_count": "Доп. Bounce-триггеры",
        "bounce_targets": "Доп. цели Bounce",
        "bounce_weakspot_damage_percent": "Урон Bounce по weakspot %",
        "bounce_crit_rate_percent": "Шанс крита Bounce %",
        "bounce_crit_dmg_percent": "Крит. урон Bounce %",
        "power_surge_damage_percent": "Урон Power Surge %",
        "power_surge_duration_percent": "Длительность Power Surge %",
        "shock_damage_percent": "Урон шока %",
        "shock_trigger_chance_percent": "Шанс Power Surge %",
        "shock_crit_damage_percent": "Крит. урон Power Surge %",
        "shock_elemental_damage_percent": "Урон shock-элемента %",
        "burn_damage_percent": "Урон горения %",
        "burn_duration_percent": "Длительность горения %",
        "burn_trigger_chance_percent": "Шанс Burn %",
        "burn_elemental_damage_percent": "Урон burn-элемента %",
        "max_burn_stacks": "Макс. стаков горения",
        "frost_vortex_damage_percent": "Урон Frost Vortex %",
        "frost_vortex_duration_percent": "Длительность Frost Vortex %",
        "frost_vortex_trigger_chance_percent": "Шанс Frost Vortex %",
        "frost_elemental_damage_percent": "Урон frost-элемента %",
        "fortress_warfare_range_percent": "Радиус Fortress Warfare %",
        "fortress_warfare_duration_percent": "Длительность Fortress Warfare %",
        "fortress_warfare_trigger_chance_percent": "Шанс Fortress Warfare %",
        "fast_gunner_duration_percent": "Длительность Fast Gunner %",
        "fast_gunner_trigger_chance_percent": "Шанс Fast Gunner %",
        "fast_gunner_weapon_damage_percent": "Урон в Fast Gunner %",
        "unstable_bomber_trigger_chance_percent": "Шанс Unstable Bomber %",
        "unstable_bomber_crit_damage_percent": "Крит. урон Unstable Bomber %",
        "shrapnel_crit_damage_percent": "Крит. урон Shrapnel %",
        "shrapnel_weakspot_damage_percent": "Урон Shrapnel по weakspot %",
        "marked_duration_percent": "Длительность The Bull's Eye %",
        "the_bulls_eye_trigger_chance_percent": "Шанс The Bull's Eye %",
        "marked_target_damage_percent": "Урон по marked target %",
        "marked_target_weakspot_damage_percent": "Урон по weakspot marked target %",
        "marked_target_crit_damage_percent": "Крит. урон по marked target %",
        "damage_to_shocked_target_percent": "Урон по Power Surge target %",
        "hp_percent_bonus": "Бонус HP %",
        "psi_intensity_percent_bonus": "Бонус PSI %",
        "healing_received_percent": "Получаемое лечение %",
        "medicine_healing_percent": "Эффективность медикаментов %",
        "max_stamina": "Макс. выносливость",
        "max_stamina_percent": "Макс. выносливость %",
        "stamina_recovery_percent": "Восстановление выносливости %",
        "stamina_cost_reduction_percent": "Снижение расхода выносливости %",
        "melee_damage_percent": "Урон ближнего боя %",
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
        "sprint_speed_percent": "Sprint speed %",
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
        "ads_stability_percent": "ADS stability %",
        "raise_weapon_speed_percent": "Raise weapon speed %",
        "draw_speed_percent": "Draw speed %",
        "holster_speed_percent": "Holster speed %",
        "bullet_speed": "Bullet speed",
        "min_damage_range_meters": "Damage falloff start (m)",
        "min_damage_percent": "Minimum damage %",
        "damage_reduction_percent": "Damage reduction %",
        "weapon_damage_reduction_percent": "Weapon damage reduction %",
        "status_damage_reduction_percent": "Status damage reduction %",
        "head_damage_reduction_percent": "Head damage reduction %",
        "torso_damage_reduction_percent": "Torso damage reduction %",
        "limb_damage_reduction_percent": "Limb damage reduction %",
        "weakspot_damage_reduction_percent": "Weakspot damage reduction %",
        "crit_damage_reduction_percent": "Critical damage reduction %",
        "burn_elemental_damage_reduction_percent": "Burn damage reduction %",
        "frost_elemental_damage_reduction_percent": "Frost damage reduction %",
        "shock_elemental_damage_reduction_percent": "Shock damage reduction %",
        "fire_explosion_damage_reduction_percent": "Burn and explosion damage reduction %",
        "frost_shock_damage_reduction_percent": "Frost and shock damage reduction %",
        "vulnerability_percent": "Target vulnerability %",
        "explosion_elemental_damage_percent": "Explosion damage %",
        "tactical_item_damage_percent": "Tactical item damage %",
        "unstable_bomber_damage_percent": "Unstable Bomber damage %",
        "unstable_bomber_final_damage_percent": "Unstable Bomber final damage %",
        "shrapnel_damage_percent": "Shrapnel damage %",
        "shrapnel_trigger_chance_percent": "Shrapnel trigger chance %",
        "bounce_damage_percent": "Bounce damage %",
        "bounce_trigger_chance_percent": "Bounce trigger chance %",
        "bounce_trigger_factor_percent": "Bounce trigger factor %",
        "bounce_trigger_count": "Extra Bounce triggers",
        "bounce_targets": "Extra Bounce targets",
        "bounce_weakspot_damage_percent": "Bounce weakspot damage %",
        "bounce_crit_rate_percent": "Bounce crit rate %",
        "bounce_crit_dmg_percent": "Bounce crit damage %",
        "power_surge_damage_percent": "Power Surge damage %",
        "power_surge_duration_percent": "Power Surge duration %",
        "shock_damage_percent": "Shock damage %",
        "shock_trigger_chance_percent": "Power Surge trigger chance %",
        "shock_crit_damage_percent": "Power Surge crit damage %",
        "shock_elemental_damage_percent": "Shock elemental damage %",
        "burn_damage_percent": "Burn damage %",
        "burn_duration_percent": "Burn duration %",
        "burn_trigger_chance_percent": "Burn trigger chance %",
        "burn_elemental_damage_percent": "Burn elemental damage %",
        "max_burn_stacks": "Max burn stacks",
        "frost_vortex_damage_percent": "Frost Vortex damage %",
        "frost_vortex_duration_percent": "Frost Vortex duration %",
        "frost_vortex_trigger_chance_percent": "Frost Vortex trigger chance %",
        "frost_elemental_damage_percent": "Frost elemental damage %",
        "fortress_warfare_range_percent": "Fortress Warfare range %",
        "fortress_warfare_duration_percent": "Fortress Warfare duration %",
        "fortress_warfare_trigger_chance_percent": "Fortress Warfare trigger chance %",
        "fast_gunner_duration_percent": "Fast Gunner duration %",
        "fast_gunner_trigger_chance_percent": "Fast Gunner trigger chance %",
        "fast_gunner_weapon_damage_percent": "Damage in Fast Gunner %",
        "unstable_bomber_trigger_chance_percent": "Unstable Bomber trigger chance %",
        "unstable_bomber_crit_damage_percent": "Unstable Bomber crit damage %",
        "shrapnel_crit_damage_percent": "Shrapnel crit damage %",
        "shrapnel_weakspot_damage_percent": "Shrapnel weakspot damage %",
        "marked_duration_percent": "The Bull's Eye duration %",
        "the_bulls_eye_trigger_chance_percent": "The Bull's Eye trigger chance %",
        "marked_target_damage_percent": "Damage vs marked target %",
        "marked_target_weakspot_damage_percent": "Weakspot damage vs marked target %",
        "marked_target_crit_damage_percent": "Crit damage vs marked target %",
        "damage_to_shocked_target_percent": "Damage vs shocked target %",
        "hp_percent_bonus": "HP bonus %",
        "psi_intensity_percent_bonus": "PSI bonus %",
        "healing_received_percent": "Healing received %",
        "medicine_healing_percent": "Medicine healing bonus %",
        "max_stamina": "Max stamina",
        "max_stamina_percent": "Max stamina %",
        "stamina_recovery_percent": "Stamina recovery %",
        "stamina_cost_reduction_percent": "Stamina cost reduction %",
        "melee_damage_percent": "Melee damage %",
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
        damage = self.context.apply_dynamic_damage_bonuses(
            damage,
            is_crit=is_crit,
            weakspot_hit=weakspot_hit,
            damage_kind='weapon',
        )
        return damage, is_crit

    def get_base_damage(self):
        damage = self.player.stats.get('damage_per_projectile', 0)
        return damage

    def apply_weapon_and_status_bonus(self, damage):
        weapon_damage_bonus = self.player.stats.get('weapon_damage_percent', 0)
        status_damage_bonus = self.player.stats.get('status_damage_percent', 0)
        melee_bonus = 0
        if self.player.weapon and getattr(self.player.weapon, 'type', None) == 'melee':
            melee_bonus = self.player.stats.get('melee_damage_percent', 0)
        total_bonus = (weapon_damage_bonus + status_damage_bonus + melee_bonus) / 100.0
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
        self.max_stamina = 100.0
        self.current_stamina = self.max_stamina
        self.enemies_within_distance = 0
        self.players_in_fortress = 1
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
        self.temporary_flags = {}
        self.trigger_factors = {}
        self.event_chance_modifiers = {}
        self.infinite_ammo_until = 0.0
        self.free_ammo_shots_remaining = 0
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
        self.hits_taken_count = 0
        self.kills_count = 0
        self.status_started_at = {}
        self.reset_sources_by_event = {}
        self.effect_cooldowns = {}
        self.next_time_tick_at = 0.0
        self.first_hit_after_reload_pending = False
        self.pending_projectiles_per_shot_bonus = 0
        self.continuous_fire_start_time = None
        self.next_continuous_fire_second = 1
        self.active_bounce_chain_depth = 0
        self.ice_crystals = []
        self.next_ice_crystal_available_at = 0.0
        self.ice_crystal_shattered = False
        self.last_ice_crystal_hit_pos = None
        self.persistent_mannequin_effects = {}
        self.weapon_switch_pending = False
        self.same_target_hit_streak = 0
        self.aim_started_at = None
        self.next_aiming_tick_at = 0.0
        self.aim_complete_emitted = False

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
        self.deviations_payload = self.load_deviations()
        self.deviations_data = self.deviations_payload.get('deviations', [])
        self.deviation_lookup = self.build_deviation_lookup(self.deviations_data)
        self.mod_secondary_catalog = ModSecondaryAttributeCatalog.load(self.bd_json_path)
        self.selected_deviation = None
        self.selected_deviation_degree = 0
        self.deviation_state = {}

        self.current_mod = {'effects': []}
        self.stats_stack = [self.current_mod['effects']]
        self.current_mod_source = None
        self.current_item = None
        self.current_set = None

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
            'fire_rate', 'projectiles_per_shot', 'accuracy', 'stability', 'range',
            'damage_reduction_percent', 'weapon_damage_reduction_percent', 'status_damage_reduction_percent',
            'max_stamina', 'stamina_recovery_percent', 'stamina_cost_reduction_percent',
            'healing_received_percent', 'medicine_healing_percent', 'melee_damage_percent'
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
            try:
                for fname in os.listdir(icons_path):
                    if fname.endswith('.png'):
                        ability_id = os.path.splitext(fname)[0]
                        w, h, c, data = dpg.load_image(os.path.join(icons_path, fname))
                        with dpg.texture_registry():
                            tex_id = dpg.add_static_texture(w, h, data)
                        self.ability_icons[ability_id] = tex_id
            except Exception as exc:
                logging.debug("Skipping ability icon preloading outside DearPyGui context: %s", exc)

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
                weapons = data.get('weapons', [])
                return self.normalize_weapon_dataset(weapons)
        except FileNotFoundError:
            logging.warning("weapon_list.json not found!")
            return []

    @staticmethod
    def normalize_weapon_name_for_dataset(name):
        normalized = str(name or "").strip().lower()
        normalized = re.sub(r'^[a-z0-9-]+\s*-\s*', '', normalized)
        normalized = re.sub(r'[^a-z0-9]+', ' ', normalized)
        return " ".join(normalized.split())

    def normalize_weapon_dataset(self, weapons):
        weapons = [copy.deepcopy(entry) for entry in (weapons or []) if isinstance(entry, dict)]
        weapons_by_key = {}
        for weapon in weapons:
            weapon_key = (
                weapon.get('type'),
                self.normalize_weapon_name_for_dataset(weapon.get('name')),
            )
            weapons_by_key.setdefault(weapon_key, []).append(weapon)

        placeholder_marker = "Direct local mechanic extraction from game files is still pending."
        for group in weapons_by_key.values():
            source_weapon = next(
                (
                    weapon for weapon in group
                    if (weapon.get('mechanics') or {}).get('effects')
                ),
                None,
            )
            if not source_weapon:
                continue
            source_mechanics = copy.deepcopy(source_weapon.get('mechanics') or {})
            source_description = source_weapon.get('description')
            for weapon in group:
                mechanics = weapon.setdefault('mechanics', {})
                if mechanics.get('effects'):
                    continue
                if placeholder_marker not in str(mechanics.get('description') or ''):
                    continue
                weapon['mechanics'] = copy.deepcopy(source_mechanics)
                if not weapon.get('description') and source_description:
                    weapon['description'] = source_description

        return weapons

    def load_weapon_attachments(self):
        path_attachments = os.path.join(self.bd_json_path, 'weapon_attachments.json')
        try:
            with open(path_attachments, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('attachments', [])
        except FileNotFoundError:
            logging.warning("weapon_attachments.json not found!")
            return []

    def load_deviations(self):
        path_deviations = os.path.join(self.bd_json_path, 'deviations.json')
        try:
            with open(path_deviations, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logging.warning("deviations.json not found!")
            return {"deviations": []}

    def build_deviation_lookup(self, deviations):
        lookup = {}
        for entry in deviations or []:
            if not isinstance(entry, dict):
                continue
            localized_names = []
            localization = entry.get('localization') or {}
            for lang in ('ru', 'en'):
                localized_name = str((localization.get(lang) or {}).get('name') or '').strip()
                if localized_name:
                    localized_names.append(localized_name)
            for candidate in [entry.get('name'), *localized_names, *(entry.get('aliases') or [])]:
                candidate = str(candidate or '').strip()
                if candidate:
                    lookup[candidate] = entry
        return lookup

    def get_mod_secondary_attribute_options(self):
        return self.mod_secondary_catalog.get_attribute_options()

    def get_mod_secondary_attribute(self, attribute_id):
        return self.mod_secondary_catalog.get_attribute(attribute_id)

    def get_mod_secondary_tier_codes(self, attribute_id):
        return self.mod_secondary_catalog.get_tier_codes(attribute_id)

    def build_mod_secondary_effects(self, mod):
        return self.mod_secondary_catalog.build_effects(mod)

    def build_mod_secondary_roll(self, attribute_id, tier_code):
        return self.mod_secondary_catalog.build_roll(attribute_id, tier_code)

    def get_deviations(self):
        return self.deviations_data

    def get_combat_deviations(self):
        return [
            entry
            for entry in self.deviations_data
            if entry.get('is_combat') or (entry.get('combat_profile') or {}).get('supported_runtime')
        ]

    def find_deviation(self, name=None, deviation_id=None):
        if name:
            candidate = str(name).strip()
            if candidate in self.deviation_lookup:
                return self.deviation_lookup[candidate]
            lowered_candidate = candidate.casefold()
            for key, entry in self.deviation_lookup.items():
                if str(key).casefold() == lowered_candidate:
                    return entry
        if deviation_id:
            for entry in self.deviations_data:
                if str(entry.get('id')) == str(deviation_id):
                    return entry
        return None

    def get_deviation_aliases(self, deviation=None):
        payload = deviation or self.selected_deviation or {}
        return list(payload.get('aliases') or [])

    @staticmethod
    def text_contains_cjk(text):
        return bool(DISPLAY_CJK_RE.search(str(text or '')))

    def get_localized_payload_text(self, payload, field_name, *, language=None):
        if not isinstance(payload, dict):
            return ""
        current_language = language or self.language
        mirrored_localization = payload.get(f'{field_name}_localized')
        if isinstance(mirrored_localization, dict):
            preferred = str(mirrored_localization.get(current_language) or '').strip()
            if preferred:
                return preferred
            fallback_en = str(mirrored_localization.get('en') or '').strip()
            if fallback_en:
                return fallback_en
            fallback_ru = str(mirrored_localization.get('ru') or '').strip()
            if fallback_ru:
                return fallback_ru
        localization = payload.get('localization') or {}
        preferred = str((localization.get(current_language) or {}).get(field_name) or '').strip()
        if preferred:
            return preferred
        fallback_en = str((localization.get('en') or {}).get(field_name) or '').strip()
        if fallback_en:
            return fallback_en
        fallback_ru = str((localization.get('ru') or {}).get(field_name) or '').strip()
        if fallback_ru:
            return fallback_ru
        return str(payload.get(field_name, '') or '').strip()

    @staticmethod
    def is_suspicious_display_name(raw_name, localized_name):
        raw_name = str(raw_name or '').strip()
        localized_name = str(localized_name or '').strip()
        if not raw_name or not localized_name:
            return False
        if not DISPLAY_CJK_RE.search(raw_name):
            return False
        if len(raw_name) <= 4 and len(localized_name) > 18:
            return True
        if len(localized_name) > max(24, len(raw_name) * 6):
            return True
        return False

    def get_deviation_display_name(self, deviation=None):
        payload = deviation or self.selected_deviation or {}
        localized_name = self.get_localized_payload_text(payload, 'name')
        raw_name = str(payload.get('name', '') or '').strip()
        if localized_name and not self.is_suspicious_display_name(raw_name, localized_name):
            return localized_name
        aliases = self.get_deviation_aliases(payload)
        if aliases:
            return aliases[0]
        return raw_name or localized_name

    def get_deviation_display_description(self, deviation=None):
        payload = deviation or self.selected_deviation or {}
        localized_description = self.get_localized_payload_text(payload, 'description')
        raw_description = str(payload.get('description', '') or '').strip()
        return localized_description or raw_description

    def get_deviation_skill_display_entries(self, deviation=None):
        entries = copy.deepcopy(self.get_deviation_skill_entries(deviation))
        for entry in entries:
            entry['display_name'] = self.get_localized_payload_text(entry, 'name')
            if self.is_suspicious_display_name(str(entry.get('name', '') or '').strip(), entry['display_name']):
                fallback_name = self.get_localized_payload_text(entry, 'name', language='en')
                entry['display_name'] = fallback_name or str(entry.get('name', '') or '').strip()
            entry['display_description'] = self.get_localized_payload_text(entry, 'description') or str(entry.get('description', '') or '').strip()
            entry['display_preview_description'] = self.get_localized_payload_text(entry, 'preview_description') or str(entry.get('preview_description', '') or '').strip()
            entry['display_exact_description'] = self.get_localized_payload_text(entry, 'exact_description') or str(entry.get('exact_description', '') or '').strip()
            for variant in entry.get('exact_variants') or []:
                variant['display_name'] = self.get_localized_payload_text(variant, 'name')
                if self.is_suspicious_display_name(str(variant.get('name', '') or '').strip(), variant['display_name']):
                    fallback_name = self.get_localized_payload_text(variant, 'name', language='en')
                    variant['display_name'] = fallback_name or str(variant.get('name', '') or '').strip()
                variant['display_description'] = self.get_localized_payload_text(variant, 'description') or str(variant.get('description', '') or '').strip()
        return entries

    def get_deviation_skill_entries(self, deviation=None):
        payload = deviation or self.selected_deviation or {}
        skill_entries = payload.get('skill_entries')
        if skill_entries:
            return list(skill_entries)
        return list(payload.get('preview_skills') or [])

    def get_deviation_preview_skills(self, deviation=None):
        return self.get_deviation_skill_entries(deviation)

    def get_deviation_combat_summary(self, deviation=None):
        payload = deviation or self.selected_deviation or {}
        combat_profile = payload.get('combat_profile') or {}
        return {
            'behavior': combat_profile.get('behavior'),
            'description': combat_profile.get('description', ''),
            'parameter_formulas': combat_profile.get('parameter_formulas') or {},
        }

    def get_deviation_skill_texts(self, deviation=None):
        texts = []
        for skill in self.get_deviation_skill_entries(deviation):
            for key in ('name', 'description', 'preview_description', 'exact_description'):
                value = str(skill.get(key, '') or '').strip()
                if value:
                    texts.append(value)
            for variant in skill.get('exact_variants') or []:
                description = str(variant.get('description', '') or '').strip()
                if description:
                    texts.append(description)
        return texts

    def find_deviation_percent(
        self,
        texts,
        keywords,
        default=0.0,
        *,
        require_bonus_words=False,
        max_value=100.0,
        ignored_keywords=None,
    ):
        lowered_keywords = [str(keyword or '').casefold() for keyword in keywords if str(keyword or '').strip()]
        lowered_ignored_keywords = [
            str(keyword or '').casefold()
            for keyword in (ignored_keywords or [])
            if str(keyword or '').strip()
        ]
        candidates = []
        for text in texts:
            lowered_text = str(text or '').casefold()
            if lowered_keywords and not any(keyword in lowered_text for keyword in lowered_keywords):
                continue
            if lowered_ignored_keywords and any(keyword in lowered_text for keyword in lowered_ignored_keywords):
                continue
            if require_bonus_words and not any(word in lowered_text for word in ('提升', '增加', '加深', 'bonus', 'damage +', 'dmg +')):
                continue
            for value in DEVIATION_TEXT_PERCENT_RE.findall(str(text or '')):
                numeric_value = float(value)
                if 0.0 < numeric_value <= max_value:
                    candidates.append(numeric_value)
        return max(candidates) if candidates else float(default)

    def _build_deviation_skill_text_candidates(self, skill):
        candidates = []
        seen_texts = set()

        def normalize_values(values):
            normalized = []
            for value in values or []:
                if not isinstance(value, (int, float)):
                    continue
                numeric_value = float(value)
                if 0.0 < numeric_value <= 400.0:
                    normalized.append(numeric_value)
            return normalized

        base_coefficients = normalize_values(skill.get('coefficients_percent'))
        base_durations = normalize_values(skill.get('durations_seconds'))
        for key in ('exact_description', 'description', 'preview_description', 'name'):
            value = str(skill.get(key, '') or '').strip()
            if value and value not in seen_texts:
                candidates.append({
                    'text': value,
                    'coefficients': list(base_coefficients),
                    'durations': list(base_durations),
                })
                seen_texts.add(value)
        for variant in skill.get('exact_variants') or []:
            description = str(variant.get('description', '') or '').strip()
            if description and description not in seen_texts:
                candidates.append({
                    'text': description,
                    'coefficients': normalize_values(variant.get('coefficients_percent')),
                    'durations': normalize_values(variant.get('durations_seconds')),
                })
                seen_texts.add(description)
        return candidates

    def extract_deviation_skill_runtime_metrics(self, skill):
        best_metrics = {
            'skill_name': str(skill.get('name', '') or ''),
            'damage_kind': 'status',
            'status_kind': None,
            'direct_damage_multiplier': 0.0,
            'secondary_damage_multiplier': 0.0,
            'periodic_damage_multiplier': 0.0,
            'status_tick_multiplier': 0.0,
            'tick_interval_seconds': 0.0,
            'duration_seconds': 0.0,
            'cooldown_seconds': 0.0,
            'action_interval_seconds': 3.0,
            'stack_gain': 1,
            'max_stacks': 0,
            'estimated_total_damage_multiplier': 0.0,
            'text': '',
        }
        text_candidates = self._build_deviation_skill_text_candidates(skill) or [{
            'text': '',
            'coefficients': [],
            'durations': [],
        }]

        for candidate in text_candidates:
            text = str(candidate.get('text', '') or '')
            lowered_text = text.casefold()
            coefficient_candidates = list(candidate.get('coefficients') or [])
            duration_values = [
                float(value)
                for value in [*candidate.get('durations', []), *DEVIATION_TEXT_DURATION_RE.findall(text)]
                if 0.25 <= float(value) <= 20.0
            ]
            cooldown_values = [
                float(value)
                for value in DEVIATION_TEXT_COOLDOWN_RE.findall(text)
                if 1.0 <= float(value) <= 60.0
            ]

            periodic_coefficients = []
            periodic_intervals = []
            for match in DEVIATION_TEXT_TICK_DAMAGE_RE.finditer(text):
                interval_seconds = float(match.group(1) or 1.0)
                coefficient_percent = float(match.group(2))
                context_window = text[max(0, match.start() - 24):min(len(text), match.end() + 24)]
                if '治疗' in context_window or '恢复' in context_window:
                    continue
                periodic_coefficients.append(coefficient_percent)
                if 0.2 <= interval_seconds <= 5.0:
                    periodic_intervals.append(interval_seconds)

            direct_coefficients = [
                float(value)
                for value in DEVIATION_TEXT_DIRECT_DAMAGE_RE.findall(text)
                if 0.0 < float(value) <= 400.0
            ]
            if not direct_coefficients and coefficient_candidates and any(
                token in text for token in ('造成', '命中', '每次', '碰撞', '爆炸', '落雷', '喷射', '投掷', '冲锋', '冰晶', '漩涡')
            ):
                direct_coefficients = list(coefficient_candidates)

            remaining_coefficients = list(direct_coefficients)
            for periodic_percent in periodic_coefficients:
                for index, candidate in enumerate(remaining_coefficients):
                    if abs(candidate - periodic_percent) <= 0.11:
                        remaining_coefficients.pop(index)
                        break

            multi_hit_count = 0
            if any(token in text for token in ('每次', '连续', '随机投掷', '扫射')):
                multi_hit_values = [
                    int(float(value))
                    for value in DEVIATION_TEXT_MULTI_HIT_RE.findall(text)
                    if 1.0 < float(value) <= 24.0
                ]
                if multi_hit_values:
                    multi_hit_count = max(multi_hit_values)

            direct_damage_multiplier = 0.0
            secondary_damage_multiplier = 0.0
            if remaining_coefficients:
                if multi_hit_count and any(token in text for token in ('每次', '连续', '随机投掷', '扫射')):
                    direct_damage_multiplier = max(remaining_coefficients) / 100.0 * multi_hit_count
                elif len(remaining_coefficients) > 1 and '冰晶' in text and any(
                    token in text for token in ('延迟', '爆炸', '碰撞后')
                ):
                    direct_damage_multiplier = remaining_coefficients[0] / 100.0
                    secondary_damage_multiplier = sum(value / 100.0 for value in remaining_coefficients[1:])
                elif len(remaining_coefficients) > 1 and any(
                    token in text for token in ('延迟', '碰撞后', '爆炸', '落雷', '击飞', '之后', '再次')
                ):
                    direct_damage_multiplier = sum(value / 100.0 for value in remaining_coefficients)
                else:
                    direct_damage_multiplier = max(remaining_coefficients) / 100.0

            tick_interval_seconds = min(periodic_intervals) if periodic_intervals else 0.0
            duration_seconds = max(duration_values) if duration_values else 0.0
            periodic_hits = 0
            if tick_interval_seconds and duration_seconds:
                periodic_hits = max(1, min(60, int(round(duration_seconds / tick_interval_seconds))))
            elif multi_hit_count and periodic_coefficients:
                periodic_hits = multi_hit_count
            periodic_damage_multiplier = (
                sum(value / 100.0 for value in periodic_coefficients) * (periodic_hits or 1)
                if periodic_coefficients else 0.0
            )
            if (
                periodic_damage_multiplier <= 0.0
                and duration_seconds > 0.0
                and '每次' in text
                and any(token in text for token in ('光环', '漩涡'))
                and remaining_coefficients
            ):
                aura_hits = max(1, min(20, int(round(duration_seconds))))
                periodic_damage_multiplier = max(remaining_coefficients) / 100.0 * aura_hits
                direct_damage_multiplier = 0.0

            status_kind = None
            if '灼烧' in text or 'burn' in lowered_text:
                status_kind = 'burn'
            elif '电涌' in text or 'power surge' in lowered_text:
                status_kind = 'power_surge'
            elif '冰霜漩涡' in text or 'frost vortex' in lowered_text:
                status_kind = 'frost_vortex'

            damage_kind = 'status'
            if status_kind == 'burn':
                damage_kind = 'burn'
            elif status_kind == 'power_surge' or any(token in text for token in ('电', '雷')):
                damage_kind = 'shock'
            elif status_kind == 'frost_vortex' or '冰' in text or 'freeze' in lowered_text:
                damage_kind = 'frost'
            elif any(token in text for token in ('爆炸', '爆炎', '陨石')):
                damage_kind = 'explosion'
            elif any(token in text for token in ('物攻', '近战', '斩', '拳', '刀', '突进')):
                damage_kind = 'weapon'

            status_tick_multiplier = 0.0
            estimated_total_damage_multiplier = direct_damage_multiplier + secondary_damage_multiplier + periodic_damage_multiplier
            if status_kind == 'burn' and periodic_coefficients:
                status_tick_multiplier = max(value / 100.0 for value in periodic_coefficients)
                estimated_total_damage_multiplier = direct_damage_multiplier
                if duration_seconds and tick_interval_seconds:
                    estimated_total_damage_multiplier += status_tick_multiplier * periodic_hits

            stack_gain_values = [
                int(float(value))
                for value in DEVIATION_TEXT_STACK_GAIN_RE.findall(text)
                if 0.0 < float(value) <= 50.0
            ]
            stack_limit_values = [
                int(float(value))
                for value in DEVIATION_TEXT_STACK_LIMIT_RE.findall(text)
                if 0.0 < float(value) <= 100.0
            ]
            stack_gain = max(stack_gain_values) if stack_gain_values else 1
            max_stacks = max(stack_limit_values) if stack_limit_values else 0

            if cooldown_values:
                action_interval_seconds = min(cooldown_values)
            elif duration_seconds and (
                periodic_coefficients or any(token in text for token in ('光环', '漩涡', '链接', '持续'))
            ):
                action_interval_seconds = max(duration_seconds, 3.0)
            elif any(token in text for token in ('治疗', '护盾', '恢复')):
                action_interval_seconds = 4.0
            elif any(token in text for token in ('近战', '突进', '斩', '拳', '刀')):
                action_interval_seconds = 2.5
            else:
                action_interval_seconds = 3.0

            current_metrics = {
                'skill_name': str(skill.get('name', '') or ''),
                'damage_kind': damage_kind,
                'status_kind': status_kind,
                'direct_damage_multiplier': direct_damage_multiplier,
                'secondary_damage_multiplier': secondary_damage_multiplier,
                'periodic_damage_multiplier': periodic_damage_multiplier,
                'status_tick_multiplier': status_tick_multiplier,
                'tick_interval_seconds': tick_interval_seconds,
                'duration_seconds': duration_seconds,
                'cooldown_seconds': min(cooldown_values) if cooldown_values else 0.0,
                'action_interval_seconds': max(0.5, action_interval_seconds),
                'stack_gain': stack_gain,
                'max_stacks': max_stacks,
                'estimated_total_damage_multiplier': estimated_total_damage_multiplier,
                'text': text,
            }
            if current_metrics['estimated_total_damage_multiplier'] >= best_metrics['estimated_total_damage_multiplier']:
                best_metrics = current_metrics

        return best_metrics

    def get_primary_deviation_skill_metrics(self, deviation=None):
        best_metrics = None
        best_score = -1.0
        for skill in self.get_deviation_skill_entries(deviation):
            metrics = self.extract_deviation_skill_runtime_metrics(skill)
            score = float(metrics.get('estimated_total_damage_multiplier', 0.0) or 0.0)
            if score > best_score:
                best_metrics = metrics
                best_score = score
        return best_metrics or {
            'skill_name': '',
            'damage_kind': 'status',
            'status_kind': None,
            'direct_damage_multiplier': 0.0,
            'secondary_damage_multiplier': 0.0,
            'periodic_damage_multiplier': 0.0,
            'status_tick_multiplier': 0.0,
            'tick_interval_seconds': 0.0,
            'duration_seconds': 0.0,
            'cooldown_seconds': 0.0,
            'action_interval_seconds': 3.0,
            'stack_gain': 1,
            'max_stacks': 0,
            'estimated_total_damage_multiplier': 0.0,
            'text': '',
        }

    def extract_deviation_damage_multiplier(self, deviation=None, default=0.65):
        primary_metrics = self.get_primary_deviation_skill_metrics(deviation)
        estimated_total = float(primary_metrics.get('estimated_total_damage_multiplier', 0.0) or 0.0)
        if estimated_total > 0:
            return estimated_total
        return float(default)

    def infer_generic_deviation_profile(self, deviation):
        skill_entries = self.get_deviation_skill_entries(deviation)
        if not skill_entries:
            return {
                'behavior': 'generic_runtime',
                'description': 'Fallback runtime profile generated from available deviation metadata.',
                'parameter_formulas': {'interval_seconds_formula': '3.0'},
                'runtime_payload': {
                    'damage_multiplier': 0.65,
                    'damage_kind': 'weapon',
                    'duration_seconds': 3.0,
                },
                'supported_runtime': True,
            }

        texts = self.get_deviation_skill_texts(deviation)
        joined_text = " ".join(texts)
        lowered_text = joined_text.casefold()
        primary_metrics = self.get_primary_deviation_skill_metrics(deviation)
        primary_text = str(primary_metrics.get('text', '') or joined_text)
        primary_lowered_text = primary_text.casefold()

        candidate_intervals = [
            float(value)
            for value in DEVIATION_TEXT_INTERVAL_RE.findall(joined_text)
            if 1.5 <= float(value) <= 15.0
        ]
        primary_action_interval = float(primary_metrics.get('action_interval_seconds', 0.0) or 0.0)
        if primary_action_interval >= 0.5:
            candidate_intervals.append(primary_action_interval)
        if candidate_intervals:
            interval_seconds = min(candidate_intervals)
        elif any(token in lowered_text for token in ('近战', '冲锋', 'slash', 'punch', 'melee', '拳', '斩', '刀')):
            interval_seconds = 2.5
        elif any(token in lowered_text for token in ('治疗', 'heal', '护盾', 'shield', '光环', 'aura')):
            interval_seconds = 4.0
        else:
            interval_seconds = 3.0

        damage_multiplier = float(primary_metrics.get('estimated_total_damage_multiplier', 0.0) or 0.0)
        if damage_multiplier <= 0.0:
            damage_multiplier = self.extract_deviation_damage_multiplier(deviation, default=0.65)
        elif primary_metrics.get('status_kind') == 'burn' and float(primary_metrics.get('status_tick_multiplier', 0.0) or 0.0) > 0.0:
            damage_multiplier = float(primary_metrics.get('direct_damage_multiplier', 0.0) or 0.0)
        payload = {
            'damage_multiplier': damage_multiplier,
            'duration_seconds': max(
                interval_seconds + 0.25,
                float(primary_metrics.get('duration_seconds', 0.0) or 0.0),
            ),
            'damage_kind': str(primary_metrics.get('damage_kind', '') or '') or (
                'weapon' if any(token in lowered_text for token in ('物攻', '枪械', '近战', 'slash', 'punch', '刀', '拳')) else 'status'
            ),
            'ability_name': f"deviation_{deviation.get('me_code') or deviation.get('id') or 'generic'}",
            'skill_name': str(primary_metrics.get('skill_name', '') or ''),
            'ice_crystal_damage_multiplier': 0.0,
            'heal_percent': 0.0,
            'shield_percent': 0.0,
            'weapon_bonus_percent': 0.0,
            'status_bonus_percent': 0.0,
            'mark_duration_seconds': 0.0,
            'mark_weakspot_bonus_percent': 0.0,
            'burn_duration_seconds': 0.0,
            'burn_tick_multiplier': 0.0,
            'power_surge_duration_seconds': 0.0,
            'frost_vortex_duration_seconds': 0.0,
            'status_stack_gain': max(1, int(primary_metrics.get('stack_gain', 1) or 1)),
            'status_max_stacks': int(primary_metrics.get('max_stacks', 0) or 0),
            'apply_burn': False,
            'apply_power_surge': False,
            'apply_frost_vortex': False,
            'generate_ice_crystal': False,
        }

        if any(token in primary_lowered_text for token in ('冰晶', 'ice crystal')):
            payload['generate_ice_crystal'] = True
            payload['damage_kind'] = 'frost'
            direct_ice_crystal_damage = float(primary_metrics.get('direct_damage_multiplier', 0.0) or 0.0)
            if direct_ice_crystal_damage > 0.0:
                payload['damage_multiplier'] = direct_ice_crystal_damage
            payload['ice_crystal_damage_multiplier'] = max(
                0.2,
                float(primary_metrics.get('secondary_damage_multiplier', 0.0) or 0.0)
                or float(primary_metrics.get('direct_damage_multiplier', 0.0) or 0.0)
                or 0.35,
            )
            payload['frost_vortex_duration_seconds'] = max(
                4.0,
                self.find_deviation_percent(texts, ['冰晶', '霜寒'], default=6.0, max_value=20.0),
            )
        elif primary_metrics.get('status_kind') == 'frost_vortex' or any(token in primary_lowered_text for token in ('冰霜漩涡', 'frost vortex')):
            payload['damage_kind'] = 'frost'
            payload['apply_frost_vortex'] = True
            payload['frost_vortex_duration_seconds'] = max(
                4.0,
                float(primary_metrics.get('duration_seconds', 0.0) or 5.0),
            )
        elif primary_metrics.get('status_kind') == 'power_surge' or any(token in primary_lowered_text for token in ('电涌', 'power surge')):
            payload['damage_kind'] = 'shock'
            payload['apply_power_surge'] = True
            payload['power_surge_duration_seconds'] = max(
                3.0,
                float(primary_metrics.get('duration_seconds', 0.0) or 6.0),
            )
        elif primary_metrics.get('status_kind') == 'burn' or any(token in primary_lowered_text for token in ('灼烧', 'burn')):
            payload['damage_kind'] = 'burn'
            payload['apply_burn'] = True
            payload['burn_duration_seconds'] = max(
                3.0,
                float(primary_metrics.get('duration_seconds', 0.0) or 6.0),
            )
            payload['burn_tick_multiplier'] = float(primary_metrics.get('status_tick_multiplier', 0.0) or 0.0)
        elif any(token in lowered_text for token in ('爆', 'bomb', 'explosion')):
            payload['damage_kind'] = 'explosion'
        elif any(token in lowered_text for token in ('近战', '冲锋', 'slash', 'punch', 'melee', '拳', '斩', '刀')):
            payload['damage_kind'] = 'weapon'

        if any(token in lowered_text for token in ('标记', '弱点', 'bull', 'knife', '飞刀')):
            payload['mark_duration_seconds'] = max(
                4.0,
                max(
                    [
                        float(value)
                        for value in DEVIATION_TEXT_DURATION_RE.findall(joined_text)
                        if 2.0 <= float(value) <= 20.0
                    ] or [5.0]
                ),
            )
            payload['mark_weakspot_bonus_percent'] = self.find_deviation_percent(
                texts,
                ['弱点', '标记'],
                default=15.0,
                require_bonus_words=False,
            )

        if any(token in lowered_text for token in ('治疗', 'heal', '疗愈', '恢复生命')):
            payload['heal_percent'] = self.find_deviation_percent(
                texts,
                ['治疗', 'heal', '恢复'],
                default=0.0,
                max_value=50.0,
                ignored_keywords=['攻击力'],
            )

        if any(token in lowered_text for token in ('护盾', 'shield')):
            payload['shield_percent'] = self.find_deviation_percent(
                texts,
                ['护盾', 'shield'],
                default=0.0,
                max_value=50.0,
            )

        if any(token in lowered_text for token in ('枪械伤害', '物攻伤害', 'weapon damage')):
            payload['weapon_bonus_percent'] = self.find_deviation_percent(
                texts,
                ['枪械伤害', '物攻伤害', 'weapon damage'],
                default=0.0,
                require_bonus_words=True,
                max_value=30.0,
                ignored_keywords=['献祭', '生命', '治疗'],
            )

        if any(token in lowered_text for token in ('特攻伤害', '异常伤害', '元素强化', 'status damage', 'elemental damage')):
            payload['status_bonus_percent'] = self.find_deviation_percent(
                texts,
                ['特攻伤害', '异常伤害', '元素强化', 'status damage', 'elemental damage'],
                default=0.0,
                require_bonus_words=True,
                max_value=30.0,
                ignored_keywords=['献祭', '生命', '治疗'],
            )

        return {
            'behavior': 'generic_runtime',
            'description': 'Auto-generated runtime profile derived from local deviation skill strings.',
            'parameter_formulas': {'interval_seconds_formula': f'{interval_seconds:.2f}'},
            'runtime_payload': payload,
            'supported_runtime': True,
        }

    def get_deviation_damage_multiplier(self, preferred_terms=None, default=0.45):
        preferred_terms = [str(term or '').casefold() for term in (preferred_terms or []) if str(term or '').strip()]
        matching_values = []
        fallback_values = []
        for skill in self.get_deviation_skill_entries():
            coefficients = [
                float(value) / 100.0
                for value in (skill.get('coefficients_percent') or [])
                if isinstance(value, (int, float)) and 0 < float(value) <= 400
            ]
            if not coefficients:
                continue
            fallback_values.extend(coefficients)
            if preferred_terms:
                haystack = " ".join(
                    str(skill.get(key, '')).casefold()
                    for key in ('name', 'description')
                )
                if any(term in haystack for term in preferred_terms):
                    matching_values.extend(coefficients)
        if matching_values:
            return max(matching_values)
        if fallback_values:
            return max(fallback_values)
        return float(default)

    def evaluate_deviation_formula(self, formula, default=0.0):
        if formula in (None, ""):
            return float(default)
        if isinstance(formula, (int, float)):
            return float(formula)
        text = str(formula).strip()
        if not text or any(char not in DEVIATION_FORMULA_ALLOWED_CHARS for char in text):
            return float(default)
        try:
            return float(eval(text, {"__builtins__": {}}, {"deviation_degree": float(self.selected_deviation_degree)}))
        except Exception:
            return float(default)

    def set_deviation_bonus(self, stat, value, duration_seconds, source):
        self.player.remove_stat_bonus_source(source)
        if value:
            self.apply_temporary_stat_bonus(stat, value, max(duration_seconds, 0.1), 1, source=source)

    def get_selected_deviation_profile(self):
        if not self.selected_deviation:
            return {}
        combat_profile = self.selected_deviation.get('combat_profile') or {}
        if combat_profile.get('supported_runtime'):
            return combat_profile
        generated_profile = self.infer_generic_deviation_profile(self.selected_deviation)
        self.selected_deviation['combat_profile'] = generated_profile
        return generated_profile

    def reset_selected_deviation_runtime(self):
        profile = self.get_selected_deviation_profile()
        parameter_formulas = profile.get('parameter_formulas', {})
        interval = max(0.5, self.evaluate_deviation_formula(parameter_formulas.get('interval_seconds_formula'), 3.0))
        self.deviation_state = {
            'next_action_at': time.time() + interval,
            'status_bonus_total': 0.0,
            'burn_stacks': 0,
            'pending_ice_crystal_auto_shatter': False,
        }

    def select_deviation(self, deviation_name):
        deviation = self.find_deviation(name=deviation_name)
        self.selected_deviation = copy.deepcopy(deviation) if deviation else None
        if self.selected_deviation:
            self.selected_deviation['combat_profile'] = self.get_selected_deviation_profile()
        self.selected_deviation_degree = 0
        self.reset_selected_deviation_runtime()
        self.refresh_player_stats()
        return self.selected_deviation

    def clear_selected_deviation(self):
        self.selected_deviation = None
        self.selected_deviation_degree = 0
        self.deviation_state = {}
        for source in (
            'deviation:mark_weakspot',
            'deviation:weapon_vulnerability',
            'deviation:frost_bonus',
            'deviation:burn_bonus',
            'deviation:status_bonus',
            'deviation:explosion_bonus',
            'deviation:shock_bonus',
            'deviation:damage_share',
            'deviation:melee_companion',
            'deviation:healing_support',
        ):
            self.player.remove_stat_bonus_source(source)
        self.refresh_player_stats()

    def format_mod_secondary_roll(self, roll):
        return self.mod_secondary_catalog.format_roll(roll, self.language)

    def summarize_mod_secondary_rolls(self, mod):
        return self.mod_secondary_catalog.summarize_rolls(mod, self.language)

    def resolve_mod_key(self, category_or_key):
        if not category_or_key:
            return None
        if category_or_key in self.mods_data:
            return category_or_key
        if category_or_key in self.category_key_mapping:
            return self.category_key_mapping[category_or_key]
        normalized = str(category_or_key).strip().lower()
        if normalized in self.category_key_mapping:
            return self.category_key_mapping[normalized]
        if normalized.startswith('mod_'):
            return normalized
        candidate = f"mod_{normalized}"
        if candidate in self.mods_data or normalized in self.mod_categories:
            return candidate
        return candidate

    def resolve_slot_from_mod_key(self, mod_key):
        for slot_name, mapped_key in self.category_key_mapping.items():
            if mapped_key == mod_key:
                return slot_name
        if isinstance(mod_key, str) and mod_key.startswith("mod_"):
            return mod_key[4:]
        return mod_key

    @staticmethod
    def build_item_id(name):
        return "_".join(str(name or "").lower().replace("-", " ").split())

    @staticmethod
    def parse_effect_value(raw_value):
        if isinstance(raw_value, (int, float)):
            return raw_value
        text = str(raw_value or "").strip()
        if not text:
            return 0
        try:
            numeric = float(text.replace(",", "."))
        except ValueError:
            return text
        if numeric.is_integer():
            return int(numeric)
        return numeric

    def save_mods_config(self):
        path_mods = os.path.join(self.bd_json_path, 'mods_config.json')
        with open(path_mods, 'w', encoding='utf-8') as fh:
            json.dump(self.mods_data, fh, ensure_ascii=False, indent=2)
            fh.write('\n')

    def save_items_and_sets(self):
        path_items_sets = os.path.join(self.bd_json_path, 'items_and_sets.json')
        payload = {
            'items': self.items_data,
            'sets': self.sets_data,
            'multipliers': self.multipliers,
        }
        with open(path_items_sets, 'w', encoding='utf-8') as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)
            fh.write('\n')

    def add_category(self, category_name):
        category_name = str(category_name or '').strip().lower()
        if not category_name or category_name in self.mod_categories:
            return False
        self.mod_categories.append(category_name)
        return True

    def add_new_stat(self, stat_name):
        stat_name = str(stat_name or '').strip()
        if not stat_name or stat_name in self.stats_options:
            return False
        self.stats_options.append(stat_name)
        self.stats_options.sort()
        return True

    def add_new_flag(self, flag_name):
        flag_name = str(flag_name or '').strip()
        if not flag_name or flag_name in self.flags_options:
            return False
        self.flags_options.append(flag_name)
        self.flags_options.sort()
        return True

    def add_new_condition(self, condition_name):
        condition_name = str(condition_name or '').strip()
        if not condition_name or condition_name in self.conditions_options:
            return False
        self.conditions_options.append(condition_name)
        self.conditions_options.sort()
        return True

    def reset_mod_form(self):
        self.current_mod = {'effects': []}
        self.stats_stack = [self.current_mod['effects']]
        self.current_mod_source = None

    def add_effect(self, effect_type, effect_stat, effect_value, effect_flag, effect_flag_value, effect_condition):
        effect_type = str(effect_type or '').strip()
        if not effect_type:
            return False, "Effect type is required."
        active_effects = self.stats_stack[-1] if self.stats_stack else self.current_mod.setdefault('effects', [])
        normalized_condition = str(effect_condition or '').strip()

        if effect_type == 'conditional_effect':
            if not normalized_condition:
                return False, "Condition is required for conditional effect."
            conditional_block = {
                'type': 'conditional_effect',
                'condition': normalized_condition,
                'effects': [],
            }
            active_effects.append(conditional_block)
            self.stats_stack.append(conditional_block['effects'])
            return True, "Conditional effect started."

        if effect_type in {'increase_stat', 'decrease_stat'}:
            if not effect_stat:
                return False, "Stat is required."
            base_effect = {
                'type': effect_type,
                'stat': effect_stat,
                'value': self.parse_effect_value(effect_value),
            }
        elif effect_type == 'set_flag':
            if not effect_flag:
                return False, "Flag is required."
            base_effect = {
                'type': 'set_flag',
                'flag': effect_flag,
                'value': bool(effect_flag_value),
            }
        else:
            return False, f"Unsupported editor effect type: {effect_type}"

        if normalized_condition:
            active_effects.append({
                'type': 'conditional_effect',
                'condition': normalized_condition,
                'effects': [base_effect],
            })
        else:
            active_effects.append(base_effect)
        return True, "Effect added."

    def end_conditional_effect(self):
        if len(self.stats_stack) <= 1:
            return False, "No active conditional effect."
        self.stats_stack.pop()
        return True, "Conditional effect completed."

    def create_mod(self, mod_name, category):
        mod_name = str(mod_name or '').strip()
        if not mod_name:
            return False, "Mod name is required."
        mod_key = self.resolve_mod_key(category)
        if not mod_key:
            return False, "Mod category is required."

        target_list = self.mods_data.setdefault(mod_key, [])
        source_meta = self.current_mod_source or {}
        original_key = source_meta.get('mod_key', mod_key)
        original_name = source_meta.get('original_name', mod_name)

        new_mod = copy.deepcopy(self.current_mod)
        new_mod['name'] = mod_name
        new_mod.setdefault('description', source_meta.get('description', new_mod.get('description', '')))
        new_mod.setdefault('effects', [])

        if original_key in self.mods_data:
            self.mods_data[original_key] = [
                entry for entry in self.mods_data[original_key]
                if entry.get('name') != original_name
            ]
        self.mods_data.setdefault(mod_key, []).append(new_mod)
        self.mods_data[mod_key].sort(key=lambda entry: entry.get('name', '').lower())
        self.save_mods_config()
        self.reset_mod_form()
        return True, f"Mod '{mod_name}' saved."

    def delete_mod(self, mod, mod_key):
        target_key = self.resolve_mod_key(mod_key)
        if target_key not in self.mods_data:
            return False, "Mod category was not found."
        original_count = len(self.mods_data[target_key])
        self.mods_data[target_key] = [
            entry for entry in self.mods_data[target_key]
            if entry.get('name') != mod.get('name')
        ]
        if len(self.mods_data[target_key]) == original_count:
            return False, "Mod was not found."
        self.save_mods_config()
        return True, f"Mod '{mod.get('name', '')}' deleted."

    def create_item_data(self, name, item_type, rarity, set_id):
        name = str(name or '').strip()
        item_type = str(item_type or '').strip()
        rarity = str(rarity or '').strip()
        set_id = str(set_id or '').strip()
        if not name or not item_type or not rarity:
            return False, "Item name, type, and rarity are required."

        item_id = self.build_item_id(name)
        new_item = {
            'id': item_id,
            'name': name,
            'type': item_type,
            'rarity': rarity,
        }
        if set_id:
            new_item['set_id'] = set_id

        self.items_data = [entry for entry in self.items_data if entry.get('id') != item_id]
        self.items_data.append(new_item)
        self.items_data.sort(key=lambda entry: entry.get('name', '').lower())
        self.save_items_and_sets()
        return True, f"Item '{name}' saved."

    def delete_item(self, item):
        item_id = item.get('id')
        original_count = len(self.items_data)
        self.items_data = [entry for entry in self.items_data if entry.get('id') != item_id]
        if len(self.items_data) == original_count:
            return False, "Item was not found."
        self.save_items_and_sets()
        return True, f"Item '{item.get('name', '')}' deleted."

    def create_set_data(self, set_name, set_id, description):
        set_name = str(set_name or '').strip()
        set_id = str(set_id or '').strip()
        description = str(description or '').strip()
        if not set_name or not set_id:
            return False, "Set name and set id are required."

        new_set = {
            'name': set_name,
            'set_id': set_id,
            'description': description,
            'bonuses': self.current_set.get('bonuses', []) if isinstance(self.current_set, dict) else [],
        }
        self.sets_data = [entry for entry in self.sets_data if (entry.get('set_id') or entry.get('id')) != set_id]
        self.sets_data.append(new_set)
        self.sets_data.sort(key=lambda entry: entry.get('name', '').lower())
        self.save_items_and_sets()
        return True, f"Set '{set_name}' saved."

    def update_selected_status(self, status):
        self.selected_status = status

    def update_parameter(self, parameter, value):
        if parameter == "enemies_within_distance_input":
            self.enemies_within_distance = value
        elif parameter == "target_distance_input":
            if value != self.target_distance:
                self.process_combat_event('moving', is_crit=False, is_weakspot=False)
            self.target_distance = value
        elif parameter == "players_in_fortress_input":
            self.players_in_fortress = max(1, int(value))
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
        self.max_stamina = max(1.0, float(self.player.stats.get('max_stamina', 100.0)))
        self.current_hp = min(self.current_hp, self.max_hp)
        self.current_stamina = min(self.current_stamina, self.max_stamina)

    def set_language(self, language):
        self.language = language if language in DISPLAY_TEXT else "ru"

    def get_text(self, key, fallback):
        return DISPLAY_TEXT.get(self.language, DISPLAY_TEXT["ru"]).get(key, fallback)

    def format_enemy_type(self, enemy_type):
        return ENEMY_TYPE_LABELS.get(self.language, ENEMY_TYPE_LABELS["ru"]).get(enemy_type, enemy_type)

    def format_stat_name(self, stat_key):
        if isinstance(stat_key, (list, tuple, set)):
            return " / ".join(
                self.format_stat_name(entry)
                for entry in stat_key
                if entry is not None and str(entry).strip()
            )
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

    def get_status_uptime(self, status):
        if not status:
            return 0.0
        if not self.is_status_active(status):
            return 0.0
        started_at = self.status_started_at.get(status)
        if started_at is None:
            return 0.0
        return max(0.0, time.time() - started_at)

    def get_mannequin_effect_definitions(self):
        return PERSISTENT_MANNEQUIN_EFFECT_DEFINITIONS

    def get_mannequin_effect_ids(self):
        return list(self.get_mannequin_effect_definitions().keys())

    def get_mannequin_effect_max_stacks(self, status):
        definition = self.get_mannequin_effect_definitions().get(status, {})
        return max(1, int(definition.get('max_stacks', 1) or 1))

    def get_mannequin_effect_config(self, status):
        config = self.persistent_mannequin_effects.get(status)
        if not config:
            return {'enabled': False, 'stacks': 1}
        return {
            'enabled': True,
            'stacks': max(1, int(config.get('stacks', 1) or 1)),
        }

    def set_persistent_mannequin_effect(self, status, enabled, stacks=1):
        status = str(status or '').strip()
        if not status:
            return
        if not enabled:
            self.clear_persistent_mannequin_effect(status)
            return
        max_stacks = self.get_mannequin_effect_max_stacks(status)
        self.persistent_mannequin_effects[status] = {
            'stacks': max(1, min(int(stacks or 1), max_stacks)),
        }
        self.sync_persistent_mannequin_effects(time.time())
        self.refresh_player_stats()

    def clear_persistent_mannequin_effect(self, status):
        status = str(status or '').strip()
        if not status:
            return
        self.persistent_mannequin_effects.pop(status, None)
        self.mannequin_status_effects.pop(status, None)
        self.mannequin_status_stacks.pop(status, None)
        self.mannequin_status_payloads.pop(status, None)
        self.mannequin.effects.pop(status, None)
        self.status_started_at.pop(status, None)
        self.mannequin_status_expirations = [
            entry for entry in self.mannequin_status_expirations
            if entry.get('status') != status
        ]
        self.refresh_player_stats()

    def build_mannequin_effect_payload(self, status):
        definition = self.get_mannequin_effect_definitions().get(status, {})
        payload = copy.deepcopy(definition.get('payload', {}) or {})
        if payload and 'next_tick' not in payload:
            payload['next_tick'] = time.time()
        return payload

    def sync_persistent_mannequin_effects(self, current_time=None):
        current_time = current_time or time.time()
        if not self.persistent_mannequin_effects:
            return
        for status, config in self.persistent_mannequin_effects.items():
            max_stacks = self.get_mannequin_effect_max_stacks(status)
            stacks = max(1, min(int(config.get('stacks', 1) or 1), max_stacks))
            end_time = current_time + 86400.0
            payload = self.build_mannequin_effect_payload(status)
            existing_payload = self.mannequin_status_payloads.get(status, {})
            if existing_payload.get('next_tick') is not None and payload.get('next_tick') is not None:
                payload['next_tick'] = max(existing_payload.get('next_tick', current_time), current_time)
            self.mannequin_status_effects[status] = end_time
            self.mannequin_status_stacks[status] = stacks
            self.mannequin_status_payloads[status] = payload
            self.mannequin.effects[status] = True
            self.status_started_at.setdefault(status, current_time)
            self.mannequin_status_expirations = [
                entry for entry in self.mannequin_status_expirations
                if entry.get('status') != status
            ]
            self.mannequin_status_expirations.extend(
                {'status': status, 'end_time': end_time}
                for _ in range(stacks)
            )
            self.mannequin.apply_status(status, 86400.0, **payload)

    def get_event_refresh_duration(self):
        fire_rate = max(self.player.stats.get('fire_rate', 0.0), 1.0)
        shot_interval = 60.0 / fire_rate
        return max(0.35, shot_interval * 1.5)

    def is_out_of_combat(self):
        if self.mouse_pressed or self.reloading:
            return False
        if self.last_shot_time is None:
            return True
        return (time.time() - self.last_shot_time) >= 3.0

    def get_out_of_combat_time(self):
        if self.last_shot_time is None:
            return 999999.0
        return max(0.0, time.time() - self.last_shot_time)

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
        self.cleanup_temporary_flags()
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
            'ice_crystal_shattered': bool(self.get_temporary_flag('ice_crystal_shattered', getattr(self, 'ice_crystal_shattered', False))),
            'player_hp_ratio': self.get_player_hp_ratio(),
            'target_hp_ratio': (self.mannequin.current_hp / self.mannequin.max_hp) if self.mannequin.max_hp else 1.0,
            'enemy_type': self.mannequin.enemy_type,
            'current_mode': self.current_mode,
            'current_shield': self.current_shield,
            'status_stack_counts': self.status_stack_counts,
            'stacks': self.stacks,
            'temporary_flags': {flag: entry['value'] for flag, entry in self.temporary_flags.items()},
            'enemies_within_distance': self.enemies_within_distance,
            'target_distance': self.target_distance,
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

    def cleanup_temporary_flags(self):
        current_time = time.time()
        expired = [
            flag
            for flag, entry in self.temporary_flags.items()
            if entry.get('end_time') is not None and current_time >= entry['end_time']
        ]
        for flag in expired:
            self.temporary_flags.pop(flag, None)

    def set_temporary_flag(self, flag, value=True, duration_seconds=None, source=None):
        if not flag:
            return
        end_time = None
        if duration_seconds is not None and float(duration_seconds) > 0:
            end_time = time.time() + float(duration_seconds)
        self.temporary_flags[flag] = {
            'value': value,
            'end_time': end_time,
            'source': source,
        }

    def get_temporary_flag(self, flag, default=False):
        self.cleanup_temporary_flags()
        entry = self.temporary_flags.get(flag)
        if not entry:
            return default
        return entry.get('value', default)

    def consume_temporary_flag(self, flag, default=False):
        self.cleanup_temporary_flags()
        entry = self.temporary_flags.pop(flag, None)
        if not entry:
            return default
        return entry.get('value', default)

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
        self.status_started_at.setdefault(mode_name, time.time())
        self.mode_expirations[mode_name] = time.time() + max(duration_seconds, 0)
        self.refresh_player_stats()

    def clear_mode(self, mode_name=None):
        if mode_name and self.current_mode != mode_name:
            return
        ended_mode = self.current_mode
        if ended_mode:
            self.mode_expirations.pop(ended_mode, None)
            self.status_started_at.pop(ended_mode, None)
        self.current_mode = None
        self.refresh_player_stats()
        if ended_mode:
            self.process_combat_event(f'{ended_mode}_end')
            if ended_mode == 'fortress_warfare':
                self.process_combat_event('leave_fortress')

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
        extra_stats_to_display = [
            'accuracy', 'stability', 'range', 'sprint_speed_percent',
            'damage_reduction_percent', 'weapon_damage_reduction_percent', 'status_damage_reduction_percent',
            'head_damage_reduction_percent', 'torso_damage_reduction_percent', 'limb_damage_reduction_percent',
            'weakspot_damage_reduction_percent', 'crit_damage_reduction_percent',
            'burn_elemental_damage_reduction_percent', 'frost_elemental_damage_reduction_percent',
            'shock_elemental_damage_reduction_percent', 'fire_explosion_damage_reduction_percent',
            'frost_shock_damage_reduction_percent', 'healing_received_percent', 'medicine_healing_percent',
            'max_stamina', 'stamina_recovery_percent', 'stamina_cost_reduction_percent',
            'tactical_item_damage_percent', 'ads_stability_percent', 'raise_weapon_speed_percent',
            'draw_speed_percent', 'holster_speed_percent', 'melee_damage_percent'
        ]
        for stat in extra_stats_to_display:
            if stat in stats_to_display:
                continue
            value = player.stats.get(stat)
            if isinstance(value, bool):
                if value:
                    stats_to_display.append(stat)
            elif isinstance(value, (int, float)) and abs(value) > 1e-9:
                stats_to_display.append(stat)
        for stat in stats_to_display:
            value = player.stats.get(stat, getattr(self, stat, 0))
            stats_text += f"{self.format_stat_name(stat)}: {self.format_value(value)}\n"
        if self.mannequin_status_effects:
            stats_text += f"\n{self.get_text('status_effects', 'Status effects')}:\n"
            for key, val in self.mannequin_status_effects.items():
                stats_text += f"{key}: {self.format_value(val)}\n"
        return stats_text

    def initialize(self):
        self.player.effect_sources_dirty = True
        self.total_damage = 0
        self.dps = 0
        self.max_dps = 0
        self.max_total_damage = 0
        self.damage_history.clear()
        self.last_damage_time = 0.0
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
        self.hits_taken_count = 0
        self.kills_count = 0
        self.status_started_at.clear()
        self.reset_sources_by_event.clear()
        self.effect_cooldowns.clear()
        self.infinite_ammo_until = 0.0
        self.free_ammo_shots_remaining = 0
        self.current_stamina = self.max_stamina
        self.first_hit_after_reload_pending = False
        self.pending_projectiles_per_shot_bonus = 0
        self.continuous_fire_start_time = None
        self.next_continuous_fire_second = 1
        self.ice_crystals = []
        self.next_ice_crystal_available_at = 0.0
        self.ice_crystal_shattered = False
        self.last_ice_crystal_hit_pos = None
        self.weapon_switch_pending = False
        self.same_target_hit_streak = 0
        self.aim_started_at = None
        self.next_aiming_tick_at = 0.0
        self.aim_complete_emitted = False
        self.refresh_player_stats()
        self.update_max_hp()
        self.current_hp = self.max_hp
        self.current_ammo = self.player.stats.get('magazine_capacity', 0)
        for source in (
            'deviation:mark_weakspot',
            'deviation:weapon_vulnerability',
            'deviation:frost_bonus',
            'deviation:burn_bonus',
            'deviation:status_bonus',
            'deviation:explosion_bonus',
            'deviation:shock_bonus',
            'deviation:damage_share',
            'deviation:melee_companion',
            'deviation:healing_support',
        ):
            self.player.remove_stat_bonus_source(source)
        self.sync_persistent_mannequin_effects(time.time())
        self.next_time_tick_at = time.time() + 1.0
        if self.selected_deviation:
            self.reset_selected_deviation_runtime()

    def reset_combat_metrics(self):
        for item in list(self.scheduled_deletions):
            item_id = item.get('id')
            if item_id and dpg.does_item_exist(item_id):
                try:
                    dpg.delete_item(item_id)
                except Exception:
                    pass
        self.scheduled_deletions.clear()
        self.initialize()
        self.last_update_time = time.time()

    def deal_deviation_damage(self, multiplier, *, damage_kind='status', ability_name='deviation', hit_pos=None):
        multiplier = float(multiplier or 0)
        if multiplier <= 0:
            return
        base_damage = self.resolve_damage_formula({'type': 'psi_intensity', 'multiplier': multiplier})
        damage = base_damage
        if damage_kind == 'status':
            damage *= 1 + self.player.stats.get('status_damage_percent', 0) / 100.0
        elif damage_kind == 'weapon':
            damage *= 1 + self.player.stats.get('weapon_damage_percent', 0) / 100.0
        self.apply_direct_damage(damage, is_crit=False, weakspot_hit=False, ability_name=ability_name, hit_pos=hit_pos)

    def execute_selected_deviation_action(self, current_time):
        profile = self.get_selected_deviation_profile()
        if not profile or not profile.get('supported_runtime'):
            return

        parameter_formulas = profile.get('parameter_formulas', {})
        interval = max(0.5, self.evaluate_deviation_formula(parameter_formulas.get('interval_seconds_formula'), 3.0))
        self.deviation_state['next_action_at'] = current_time + interval
        behavior = profile.get('behavior')

        if behavior == 'ice_crystal_orbit':
            frost_bonus = self.evaluate_deviation_formula(parameter_formulas.get('frost_bonus_percent_formula'), 18.0)
            frost_damage = self.evaluate_deviation_formula(parameter_formulas.get('frost_damage_percent_formula'), 37.5) / 100.0
            self.deviation_state['ice_crystal_damage_formula'] = {'type': 'psi_intensity', 'multiplier': frost_damage}
            self.generate_ice_crystal(0.0, source='deviation')
            self.set_deviation_bonus('frost_elemental_damage_percent', frost_bonus, interval + 0.25, 'deviation:frost_bonus')
            return

        if behavior == 'mark_weakspot':
            duration = max(1.0, self.evaluate_deviation_formula(parameter_formulas.get('duration_seconds_formula'), 5.0))
            weakspot_bonus = self.evaluate_deviation_formula(parameter_formulas.get('weakspot_bonus_percent_formula'), 15.0)
            self.apply_status('the_bulls_eye', duration)
            self.set_deviation_bonus('marked_target_weakspot_damage_percent', weakspot_bonus, duration, 'deviation:mark_weakspot')
            self.deal_deviation_damage(
                self.get_deviation_damage_multiplier(['标记', '刀', '飞刀', 'knife', 'weakspot'], default=1.0),
                damage_kind='weapon',
                ability_name='deviation_mark',
            )
            self.process_combat_event('enemy_marked', is_crit=False, is_weakspot=False)
            return

        if behavior == 'weapon_vulnerability':
            weapon_bonus = self.evaluate_deviation_formula(parameter_formulas.get('weapon_bonus_percent_formula'), 15.0)
            self.set_deviation_bonus('weapon_damage_percent', weapon_bonus, interval + 0.25, 'deviation:weapon_vulnerability')
            self.deal_deviation_damage(
                self.get_deviation_damage_multiplier(['攻击', 'attack', '箭', 'ball', 'shot'], default=0.95),
                damage_kind='status',
                ability_name='deviation_weapon_vulnerability',
            )
            return

        if behavior == 'burn_bombard':
            burn_bonus = self.evaluate_deviation_formula(parameter_formulas.get('burn_bonus_percent_formula'), 15.0)
            burn_damage = self.evaluate_deviation_formula(
                parameter_formulas.get('burn_damage_percent_formula'),
                self.get_deviation_damage_multiplier(['陨', 'meteor', 'burn', '火'], default=1.2) * 100.0,
            ) / 100.0
            stack_bonus = self.evaluate_deviation_formula(parameter_formulas.get('stack_damage_bonus_formula'), 3.0)
            burn_chance = self.evaluate_deviation_formula(parameter_formulas.get('burn_trigger_chance_formula'), 35.0)
            burn_stacks = int(self.deviation_state.get('burn_stacks', 0))
            burn_damage *= 1 + (burn_stacks * stack_bonus / 100.0)
            self.trigger_ability('explosion', damage_formula={'type': 'psi_intensity', 'multiplier': burn_damage}, damage_type='burn')
            if random.uniform(0, 100) <= burn_chance:
                self.apply_status('burn', 6.0, damage_formula={'type': 'psi_intensity', 'multiplier': 0.4}, damage_type='burn', tick_interval=1.0)
            if self.is_status_active('burn'):
                self.deviation_state['burn_stacks'] = min(10, burn_stacks + 1)
            self.set_deviation_bonus('burn_elemental_damage_percent', burn_bonus, interval + 0.25, 'deviation:burn_bonus')
            return

        if behavior == 'burn_vulnerability':
            self.set_deviation_bonus('burn_elemental_damage_percent', 18.0, interval + 0.25, 'deviation:burn_bonus')
            self.deal_deviation_damage(
                self.get_deviation_damage_multiplier(['火', 'burn', 'fireball', 'flame'], default=0.9),
                damage_kind='status',
                ability_name='deviation_burn',
            )
            if self.is_status_active('burn'):
                self.trigger_ability('explosion', damage_formula={'type': 'psi_intensity', 'multiplier': 0.5}, damage_type='burn')
            return

        if behavior == 'tentacle_status':
            tentacles = max(1.0, self.evaluate_deviation_formula(parameter_formulas.get('tentacles_per_attack_formula'), 1.0))
            stacks_per_attack = max(1.0, self.evaluate_deviation_formula(parameter_formulas.get('stacks_per_attack_formula'), 1.0))
            status_bonus = self.evaluate_deviation_formula(parameter_formulas.get('status_damage_bonus_formula'), 7.5)
            status_cap = self.evaluate_deviation_formula(parameter_formulas.get('status_damage_bonus_cap_formula'), 30.0)
            new_total = min(status_cap, float(self.deviation_state.get('status_bonus_total', 0.0)) + stacks_per_attack * status_bonus)
            self.deviation_state['status_bonus_total'] = new_total
            self.set_deviation_bonus('status_damage_percent', new_total, interval + 0.75, 'deviation:status_bonus')
            self.deal_deviation_damage(0.35 * tentacles, damage_kind='status', ability_name='deviation_tentacle')
            return

        if behavior == 'explosion_vulnerability':
            bonus = self.evaluate_deviation_formula(parameter_formulas.get('explosion_bonus_percent_formula'), 20.0)
            self.set_deviation_bonus('explosion_elemental_damage_percent', bonus, interval + 0.25, 'deviation:explosion_bonus')
            self.deal_deviation_damage(
                self.get_deviation_damage_multiplier(['爆', 'explosion', 'fireball'], default=0.85),
                damage_kind='status',
                ability_name='deviation_explosion',
            )
            return

        if behavior == 'shock_vulnerability':
            bonus = self.evaluate_deviation_formula(parameter_formulas.get('shock_bonus_percent_formula'), 15.0)
            self.set_deviation_bonus('power_surge_damage_percent', bonus, interval + 0.25, 'deviation:shock_bonus')
            self.apply_status('power_surge', 4.0)
            self.deal_deviation_damage(
                self.get_deviation_damage_multiplier(['电', 'shock', 'lightning', 'thunder'], default=0.75),
                damage_kind='status',
                ability_name='deviation_shock',
            )
            return

        if behavior == 'ammo_refill':
            self.current_ammo = self.player.stats.get('magazine_capacity', 0)
            return

        if behavior == 'melee_blink':
            self.deal_deviation_damage(
                self.get_deviation_damage_multiplier(['斩', 'slash', 'melee', '刀'], default=1.75),
                damage_kind='weapon',
                ability_name='deviation_melee_blink',
            )
            return

        if behavior == 'damage_share':
            self.set_deviation_bonus('damage_reduction_percent', 50.0, interval + 0.25, 'deviation:damage_share')
            return

        if behavior == 'melee_companion':
            is_melee_weapon = getattr(self.player.weapon, 'type', None) == 'melee'
            movement_bonus = 20.0 if is_melee_weapon else 10.0
            self.set_deviation_bonus('movement_speed_percent', movement_bonus, interval + 0.25, 'deviation:melee_companion')
            return

        if behavior == 'healing_support':
            restore_percent = self.evaluate_deviation_formula(parameter_formulas.get('heal_percent_formula'), 7.0)
            restore_amount = self.max_hp * max(0.0, restore_percent) / 100.0
            if restore_amount > 0:
                self.current_hp = min(self.max_hp, self.current_hp + restore_amount)
                self.set_deviation_bonus('healing_received_percent', 0.0, interval + 0.25, 'deviation:healing_support')
            return

        if behavior == 'generic_runtime':
            runtime_payload = profile.get('runtime_payload') or {}
            duration_seconds = max(0.5, float(runtime_payload.get('duration_seconds', interval + 0.25) or interval + 0.25))
            if runtime_payload.get('generate_ice_crystal'):
                ice_crystal_damage_multiplier = float(
                    runtime_payload.get('ice_crystal_damage_multiplier', 0.0) or runtime_payload.get('damage_multiplier', 0.35) or 0.35
                )
                self.deviation_state['ice_crystal_damage_formula'] = {
                    'type': 'psi_intensity',
                    'multiplier': max(0.2, ice_crystal_damage_multiplier),
                }
                self.generate_ice_crystal(0.0, source='deviation')

            damage_multiplier = float(runtime_payload.get('damage_multiplier', 0.0) or 0.0)
            if damage_multiplier > 0:
                self.deal_deviation_damage(
                    damage_multiplier,
                    damage_kind=str(runtime_payload.get('damage_kind', 'status') or 'status'),
                    ability_name=str(runtime_payload.get('ability_name', 'deviation_generic') or 'deviation_generic'),
                )

            weapon_bonus = float(runtime_payload.get('weapon_bonus_percent', 0.0) or 0.0)
            if weapon_bonus:
                self.set_deviation_bonus('weapon_damage_percent', weapon_bonus, duration_seconds, 'deviation:weapon_vulnerability')

            status_bonus = float(runtime_payload.get('status_bonus_percent', 0.0) or 0.0)
            if status_bonus:
                self.set_deviation_bonus('status_damage_percent', status_bonus, duration_seconds, 'deviation:status_bonus')

            heal_percent = float(runtime_payload.get('heal_percent', 0.0) or 0.0)
            if heal_percent > 0:
                self.current_hp = min(self.max_hp, self.current_hp + self.max_hp * heal_percent / 100.0)

            shield_percent = float(runtime_payload.get('shield_percent', 0.0) or 0.0)
            if shield_percent > 0:
                self.apply_shield(percent_of_max_hp=shield_percent, duration_seconds=max(4.0, duration_seconds))

            mark_duration = float(runtime_payload.get('mark_duration_seconds', 0.0) or 0.0)
            if mark_duration > 0:
                self.apply_status('the_bulls_eye', mark_duration)
                self.set_deviation_bonus(
                    'marked_target_weakspot_damage_percent',
                    float(runtime_payload.get('mark_weakspot_bonus_percent', 15.0) or 15.0),
                    mark_duration,
                    'deviation:mark_weakspot',
                )

            status_stack_gain = max(1, int(runtime_payload.get('status_stack_gain', 1) or 1))
            status_max_stacks = int(runtime_payload.get('status_max_stacks', 0) or 0)

            if runtime_payload.get('apply_burn'):
                burn_tick_multiplier = float(runtime_payload.get('burn_tick_multiplier', 0.0) or 0.0)
                if burn_tick_multiplier <= 0.0:
                    burn_tick_multiplier = max(0.15, damage_multiplier * 0.35)
                burn_kwargs = {
                    'damage_formula': {
                        'type': 'psi_intensity',
                        'multiplier': burn_tick_multiplier,
                    },
                    'damage_type': 'burn',
                    'tick_interval': 1.0,
                }
                if status_max_stacks > 0:
                    burn_kwargs['max_stacks'] = status_max_stacks
                for _ in range(status_stack_gain):
                    self.apply_status(
                        'burn',
                        max(1.0, float(runtime_payload.get('burn_duration_seconds', 6.0) or 6.0)),
                        **burn_kwargs,
                    )

            if runtime_payload.get('apply_power_surge'):
                power_surge_kwargs = {}
                if status_max_stacks > 0:
                    power_surge_kwargs['max_stacks'] = status_max_stacks
                for _ in range(status_stack_gain):
                    self.apply_status(
                        'power_surge',
                        max(1.0, float(runtime_payload.get('power_surge_duration_seconds', 6.0) or 6.0)),
                        **power_surge_kwargs,
                    )

            if runtime_payload.get('apply_frost_vortex'):
                self.apply_status(
                    'frost_vortex',
                    max(1.0, float(runtime_payload.get('frost_vortex_duration_seconds', 6.0) or 6.0)),
                )
            return

    def handle_selected_deviation_event(self, event_name):
        profile = self.get_selected_deviation_profile()
        if not profile:
            return
        behavior = profile.get('behavior')
        if behavior == 'melee_companion' and event_name in {'hit', 'melee_kill'}:
            if getattr(self.player.weapon, 'type', None) == 'melee':
                self.current_hp = min(self.max_hp, self.current_hp + self.max_hp * 0.05)
            return
        runtime_payload = profile.get('runtime_payload') or {}
        if behavior not in {'ice_crystal_orbit', 'generic_runtime'}:
            return
        if behavior == 'generic_runtime' and not runtime_payload.get('generate_ice_crystal'):
            return
        damage_formula = self.deviation_state.get('ice_crystal_damage_formula') or {'type': 'psi_intensity', 'multiplier': 0.375}
        if event_name == 'shoot_ice_crystal':
            crystal = self.get_ice_crystal_hit(self.last_ice_crystal_hit_pos) if self.last_ice_crystal_hit_pos else None
            if crystal and crystal.get('source') == 'deviation':
                self.shatter_ice_crystal(damage_formula, 'frost')
        elif event_name == 'ice_crystal_shatter' and self.deviation_state.get('pending_ice_crystal_auto_shatter'):
            self.deviation_state['pending_ice_crystal_auto_shatter'] = False
            self.deal_status_damage(damage_formula, 'frost', 0, hit_pos=self.get_target_center_screen())

    def update(self):
        current_time = time.time()
        self.mannequin.update_effects(delta_time=current_time - self.last_update_time)
        self.last_update_time = current_time
        self.update_aim_state(current_time)
        self.update_ice_crystals(current_time)
        self.sync_persistent_mannequin_effects(current_time)
        self.update_selected_deviation(current_time)
        while self.next_time_tick_at and current_time >= self.next_time_tick_at:
            self.process_combat_event('time_tick', is_crit=False, is_weakspot=False)
            self.next_time_tick_at += 1.0
        self.update_status_effects()
        if self.reloading and current_time >= self.reload_end_time:
            self.reloading = False
            self.current_ammo = self.player.stats.get('magazine_capacity', 0)
            logging.info(f"Reload complete. Ammo replenished to {self.current_ammo}")
        self.dps = self.calculate_dps()
        self.max_dps = max(self.max_dps, self.dps)
        self.max_total_damage = max(self.max_total_damage, self.total_damage)
        self.player.update_active_stat_bonuses()
        self.update_max_hp()

    def update_selected_deviation(self, current_time):
        profile = self.get_selected_deviation_profile()
        if not profile or not profile.get('supported_runtime'):
            return
        if current_time < float(self.deviation_state.get('next_action_at', 0.0) or 0.0):
            return
        self.execute_selected_deviation_action(current_time)

    def update_aim_state(self, current_time):
        weapon_type = getattr(self.player.weapon, 'type', None)
        is_precision_bow = weapon_type in {'crossbows', 'bows'}
        if not is_precision_bow or not self.mouse_pressed:
            if self.aim_started_at is not None:
                self.process_combat_event('standing_up', is_crit=False, is_weakspot=False)
            self.aim_started_at = None
            self.next_aiming_tick_at = 0.0
            self.aim_complete_emitted = False
            return

        if self.aim_started_at is None:
            self.aim_started_at = current_time
            self.next_aiming_tick_at = current_time
            self.aim_complete_emitted = False

        while self.next_aiming_tick_at and current_time >= self.next_aiming_tick_at:
            self.process_combat_event('aiming', is_crit=False, is_weakspot=False)
            self.next_aiming_tick_at += 0.5

        if not self.aim_complete_emitted and current_time - self.aim_started_at >= 3.0:
            self.process_combat_event('aim_complete', is_crit=False, is_weakspot=False)
            self.aim_complete_emitted = True

    def update_ice_crystals(self, current_time):
        if not self.ice_crystals:
            return
        remaining_crystals = []
        auto_shattered = False
        deviation_auto_shattered = False
        for crystal in self.ice_crystals:
            if current_time >= crystal.get('shatter_at', 0.0):
                auto_shattered = True
                if crystal.get('source') == 'deviation':
                    deviation_auto_shattered = True
            else:
                remaining_crystals.append(crystal)
        self.ice_crystals = remaining_crystals
        if auto_shattered:
            self.ice_crystal_shattered = True
            if deviation_auto_shattered:
                self.deviation_state.setdefault('pending_ice_crystal_auto_shatter', True)
            self.set_temporary_flag('ice_crystal_shattered', True, duration_seconds=self.get_event_refresh_duration(), source='ice_crystal')
            self.process_combat_event('ice_crystal_shatter', is_crit=False, is_weakspot=False)

    def update_dps_display(self):
        dps_text = (
            f"DPS: {int(self.dps)}    "
            f"Max DPS: {int(self.max_dps)}    "
            f"Total DMG: {int(self.total_damage)}    "
            f"Max Total DMG: {int(self.max_total_damage)}"
        )
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

    def update_continuous_fire_state(self, current_time, time_between_shots):
        shot_gap_limit = max(0.35, time_between_shots * 1.5)
        if self.last_shot_time is None or current_time - self.last_shot_time > shot_gap_limit:
            self.continuous_fire_start_time = current_time
            self.next_continuous_fire_second = 1
        elif self.continuous_fire_start_time is None:
            self.continuous_fire_start_time = self.last_shot_time
        if self.continuous_fire_start_time is not None:
            while current_time - self.continuous_fire_start_time >= self.next_continuous_fire_second:
                self.process_combat_event('continuous_fire', is_crit=False, is_weakspot=False)
                self.next_continuous_fire_second += 1
        self.last_shot_time = current_time

    def consume_bullet_buffs(self):
        expired = []
        for buff_name, buff_data in list(self.buffs.items()):
            duration_bullets = buff_data.get('duration_bullets')
            if duration_bullets is None:
                continue
            buff_data['duration_bullets'] = max(0, duration_bullets - 1)
            if buff_data['duration_bullets'] <= 0:
                expired.append(buff_name)
        for buff_name in expired:
            self.remove_buff(buff_name)

    def try_fire_weapon(self):
        if not self.player.weapon:
            return
        if self.mouse_pressed:
            current_time = time.time()
            fire_rate = self.player.stats.get('fire_rate', 600.0)
            time_between_shots = 60.0 / fire_rate
            if current_time - self.last_fire_time >= time_between_shots:
                has_free_ammo = self.free_ammo_shots_remaining > 0
                has_infinite_ammo = current_time < self.infinite_ammo_until or has_free_ammo
                if self.current_ammo <= 0 and not has_infinite_ammo:
                    self.reload_weapon()
                    return
                if not has_infinite_ammo:
                    self.current_ammo -= 1
                elif has_free_ammo:
                    self.free_ammo_shots_remaining = max(0, self.free_ammo_shots_remaining - 1)
                self.magazine_bullets_fired += 1
                self.last_fire_time = current_time
                self.update_continuous_fire_state(current_time, time_between_shots)
                self.process_combat_event('shot_fired')
                magazine_capacity = max(1, self.player.stats.get('magazine_capacity', 1))
                effective_current_ammo = self.current_ammo if not has_infinite_ammo else max(self.current_ammo, 1)
                if effective_current_ammo == 0:
                    self.process_combat_event('mag_empty')
                    self.process_combat_event('last_shot')
                elif effective_current_ammo / magazine_capacity > 0.5:
                    self.process_combat_event('remaining_bullets_above_50_percent')
                else:
                    self.process_combat_event('magazine_below_half')
                self.consume_bullet_buffs()
                base_projectiles_per_shot = int(self.player.stats.get('projectiles_per_shot', 1) or 1)
                projectiles_per_shot = max(1, base_projectiles_per_shot + self.pending_projectiles_per_shot_bonus)
                self.pending_projectiles_per_shot_bonus = 0
                total_shot_damage = 0
                damage_list = []
                shot_hit_ice_crystal = False
                for _ in range(projectiles_per_shot):
                    current_mouse_pos = dpg.get_mouse_pos(local=False)
                    self.last_shot_mouse_pos = current_mouse_pos
                    hit_pos = self.simulate_projectile_hit(current_mouse_pos)
                    crystal_hit = self.get_ice_crystal_hit(hit_pos)
                    if crystal_hit:
                        self.last_ice_crystal_hit_pos = hit_pos
                        self.process_combat_event('shoot_ice_crystal', is_crit=False, is_weakspot=False)
                        shot_hit_ice_crystal = True
                        continue
                    weakspot_hit = self.is_weakspot_hit(hit_pos)
                    damage, is_crit = self.damage_calculator.calculate_damage_per_projectile(weakspot_hit)
                    total_shot_damage += damage
                    damage_list.append((damage, hit_pos, is_crit, weakspot_hit))
                if self.alternate_ammo == 'dragon_breath':
                    special_hit_pos = damage_list[-1][1] if damage_list else self.get_center_of_hit_area()
                    dragon_breath_damage = self.resolve_damage_formula({'type': 'attack', 'multiplier': 0.85})
                    dragon_breath_damage *= 1 + self.player.stats.get('weapon_damage_percent', 0) / 100.0
                    dragon_breath_damage = self.apply_dynamic_damage_bonuses(
                        dragon_breath_damage,
                        is_crit=False,
                        weakspot_hit=False,
                        damage_kind='burn',
                    )
                    total_shot_damage += dragon_breath_damage
                    damage_list.append((dragon_breath_damage, special_hit_pos, False, False))
                self.all_projectiles_hit = bool(damage_list) and all(self.is_within_target_area(entry[1]) for entry in damage_list)
                if self.all_projectiles_hit:
                    self.process_combat_event('all_projectiles_hit')
                if not damage_list and shot_hit_ice_crystal:
                    return
                if any(entry[3] for entry in damage_list):
                    self.magazine_weakspot_hits += 1
                self.total_damage += total_shot_damage
                self.damage_history.append((current_time, total_shot_damage))
                self.last_damage_time = current_time
                self.max_total_damage = max(self.max_total_damage, self.total_damage)
                if self.mannequin.show_unified_shotgun_damage:
                    center_pos = self.get_center_of_hit_area()
                    self.display_damage_number(total_shot_damage, center_pos,
                                               any(d[2] for d in damage_list),
                                               any(d[3] for d in damage_list))
                else:
                    display_damage_list = damage_list
                    if getattr(self.player.weapon, 'type', None) == 'shotgun' and projectiles_per_shot == 1:
                        display_damage_list = self.expand_shotgun_damage_for_display(damage_list)
                    for dmg_val, hit_pos, is_crit, weakspot_hit in display_damage_list:
                        self.display_damage_number(dmg_val, hit_pos, is_crit, weakspot_hit)
                self.mannequin.receive_damage(total_shot_damage)
                self.process_hit(any(d[2] for d in damage_list), any(d[3] for d in damage_list))
                self.handle_target_defeat(any(d[2] for d in damage_list), any(d[3] for d in damage_list))

    def get_center_of_hit_area(self):
        x_center, y_center = self.get_target_center_local()
        if not dpg.does_item_exist("damage_layer"):
            return (x_center, y_center)
        window_pos = dpg.get_item_rect_min("damage_layer")
        return (window_pos[0] + x_center, window_pos[1] + y_center)

    def process_hit(self, is_crit, is_weakspot):
        if self.weapon_switch_pending:
            self.process_combat_event('weapon_switch', is_crit=is_crit, is_weakspot=is_weakspot)
            self.weapon_switch_pending = False
        self.process_combat_event('hit_target', is_crit=is_crit, is_weakspot=is_weakspot)
        self.process_combat_event('hit_target_within_distance', is_crit=is_crit, is_weakspot=is_weakspot)
        if self.same_target_hit_streak > 0:
            self.process_combat_event('consecutive_hits_same_target', is_crit=is_crit, is_weakspot=is_weakspot)
        self.same_target_hit_streak += 1
        if self.mannequin_status_effects or self.mannequin.effects:
            self.process_combat_event('hit_target_with_status', is_crit=is_crit, is_weakspot=is_weakspot)
            self.process_combat_event('hit_enemy_with_status', is_crit=is_crit, is_weakspot=is_weakspot)
        if self.is_status_active('shielded'):
            self.process_combat_event('hit_shielded_enemy', is_crit=is_crit, is_weakspot=is_weakspot)
        if self.is_status_active('the_bulls_eye') or self.is_status_active('bulls_eye'):
            self.process_combat_event('hit_marked_enemy', is_crit=is_crit, is_weakspot=is_weakspot)
            if self.enemies_within_distance > 0:
                self.process_combat_event('spread_bulls_eye', is_crit=is_crit, is_weakspot=is_weakspot)
        if self.is_status_active('burn'):
            self.process_combat_event('hit_burned_target', is_crit=is_crit, is_weakspot=is_weakspot)
        if self.first_hit_after_reload_pending:
            self.process_combat_event('first_hit_after_reload', is_crit=is_crit, is_weakspot=is_weakspot)
            self.first_hit_after_reload_pending = False
        if is_crit:
            self.process_combat_event('crit_hit', is_crit=True, is_weakspot=is_weakspot)
            if not self.player.weapon or self.player.weapon.type != 'melee':
                self.process_combat_event('non_melee_crit_hit', is_crit=True, is_weakspot=is_weakspot)
        if is_weakspot:
            self.process_combat_event('weakspot_hit', is_crit=is_crit, is_weakspot=True)
            if self.is_status_active('burn'):
                self.process_combat_event('weakspot_hit_burned_target', is_crit=is_crit, is_weakspot=True)

    def receive_player_hit(self, damage=0.0, is_melee=False):
        self.hits_taken_count += 1
        self.process_combat_event('shot_received', is_crit=False, is_weakspot=False)
        self.process_combat_event('hit', is_crit=False, is_weakspot=False)
        if is_melee:
            self.process_combat_event('melee_damage_taken', is_crit=False, is_weakspot=False)
        if damage:
            self.current_hp = max(0.0, self.current_hp - max(0.0, damage))

    def use_healing_shot(self, heal_percent=0.0):
        if heal_percent > 0:
            self.restore_hp_percent(heal_percent)
        self.process_combat_event('use_healing_shot', is_crit=False, is_weakspot=False)

    def process_combat_event(self, event_name, **kwargs):
        if event_name in {'moving', 'standing_up', 'weapon_switch'}:
            self.same_target_hit_streak = 0
        self.reset_sources_for_event(event_name)
        self.handle_selected_deviation_event(event_name)
        self.mechanics_processor.process_event(event_name, **kwargs)
        self.refresh_player_stats()

    def is_within_target_area(self, mouse_pos):
        x, y = mouse_pos
        if not dpg.does_item_exist("damage_layer"):
            local_x, local_y = x, y
        else:
            window_pos = dpg.get_item_rect_min("damage_layer")
            local_x = x - window_pos[0]
            local_y = y - window_pos[1]
        if ((TARGET_BODY_RECT['left'] <= local_x <= TARGET_BODY_RECT['right']
             and TARGET_BODY_RECT['top'] <= local_y <= TARGET_BODY_RECT['bottom']) or
            (TARGET_WEAKSPOT_RECT['left'] <= local_x <= TARGET_WEAKSPOT_RECT['right']
             and TARGET_WEAKSPOT_RECT['top'] <= local_y <= TARGET_WEAKSPOT_RECT['bottom'])):
            return True
        else:
            return False

    def is_weakspot_hit(self, mouse_pos):
        x, y = mouse_pos
        if not dpg.does_item_exist("damage_layer"):
            local_x, local_y = x, y
        else:
            window_pos = dpg.get_item_rect_min("damage_layer")
            local_x = x - window_pos[0]
            local_y = y - window_pos[1]
        return (TARGET_WEAKSPOT_RECT['left'] <= local_x <= TARGET_WEAKSPOT_RECT['right']
                and TARGET_WEAKSPOT_RECT['top'] <= local_y <= TARGET_WEAKSPOT_RECT['bottom'])

    def reload_weapon(self):
        if not self.reloading:
            reload_time = self.player.stats.get('reload_time_seconds', 1.0)
            if self.magazine_bullets_fired > 0:
                self.last_magazine_weakspot_rate = (self.magazine_weakspot_hits / self.magazine_bullets_fired) * 100.0
            else:
                self.last_magazine_weakspot_rate = 0.0
            was_empty = self.current_ammo <= 0
            if self.alternate_ammo_until_reload:
                self.alternate_ammo = None
                self.alternate_ammo_until_reload = False
            self.reloading = True
            self.reload_end_time = time.time() + reload_time
            self.current_ammo = 0
            self.first_hit_after_reload_pending = True
            self.process_combat_event('reload_weapon')
            self.process_combat_event('reload')
            if was_empty:
                self.process_combat_event('reload_empty_magazine')
                self.process_combat_event('reload_empty_mag')
            self.magazine_bullets_fired = 0
            self.magazine_weakspot_hits = 0
            logging.info(f"Reloading weapon. It will take {reload_time} seconds.")

    def calculate_dps(self):
        current_time = time.time()
        recent_damage = [d for t, d in self.damage_history if current_time - t <= 1.0]
        self.damage_history[:] = [(t, d) for t, d in self.damage_history if current_time - t <= 30.0]
        return sum(recent_damage)

    def get_recent_dps_series(self, window_seconds=30, bucket_seconds=1.0):
        current_time = time.time()
        bucket_seconds = max(0.1, float(bucket_seconds))
        window_seconds = max(bucket_seconds, float(window_seconds))
        bucket_count = max(1, int(math.ceil(window_seconds / bucket_seconds)))
        bucket_anchor = math.floor(current_time / bucket_seconds) * bucket_seconds
        window_start = bucket_anchor - (bucket_count - 1) * bucket_seconds
        bucket_phase = current_time - bucket_anchor
        filtered_history = [(t, d) for t, d in self.damage_history if t >= window_start]
        bucket_totals = [0.0] * bucket_count

        # Keep bucket boundaries stable between frames so old peaks do not jump
        # across neighboring points while the chart scrolls left.
        for timestamp, damage in filtered_history:
            bucket_index = int((timestamp - window_start) / bucket_seconds)
            if 0 <= bucket_index < bucket_count:
                bucket_totals[bucket_index] += damage

        xs = []
        ys = []
        for bucket_index, bucket_damage in enumerate(bucket_totals):
            x_value = (bucket_index + 1) * bucket_seconds - bucket_count * bucket_seconds - bucket_phase
            xs.append(round(x_value, 3))
            ys.append(bucket_damage / bucket_seconds)
        return xs, ys

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
                self.status_started_at.pop(status, None)
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
                self.status_started_at.pop(status, None)
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

    def to_local_damage_layer_pos(self, mouse_pos):
        if not mouse_pos:
            center_x = (TARGET_BODY_RECT['left'] + TARGET_BODY_RECT['right']) / 2
            center_y = (TARGET_BODY_RECT['top'] + TARGET_BODY_RECT['bottom']) / 2
            return center_x, center_y
        if not dpg.does_item_exist("damage_layer"):
            return mouse_pos[0], mouse_pos[1]
        window_pos = dpg.get_item_rect_min("damage_layer")
        return mouse_pos[0] - window_pos[0], mouse_pos[1] - window_pos[1]

    def to_screen_damage_layer_pos(self, local_pos):
        if not local_pos:
            return self.get_center_of_hit_area()
        if not dpg.does_item_exist("damage_layer"):
            return local_pos[0], local_pos[1]
        window_pos = dpg.get_item_rect_min("damage_layer")
        return window_pos[0] + local_pos[0], window_pos[1] + local_pos[1]

    def get_target_center_local(self):
        return (
            (TARGET_BODY_RECT['left'] + TARGET_BODY_RECT['right']) / 2,
            (TARGET_BODY_RECT['top'] + TARGET_BODY_RECT['bottom']) / 2,
        )

    def get_target_center_screen(self):
        return self.to_screen_damage_layer_pos(self.get_target_center_local())

    def clamp_local_point_to_target(self, local_x, local_y, margin=14):
        return (
            max(TARGET_BODY_RECT['left'] + margin, min(TARGET_BODY_RECT['right'] - margin, local_x)),
            max(TARGET_BODY_RECT['top'] + margin, min(TARGET_BODY_RECT['bottom'] - margin, local_y)),
        )

    def get_ice_crystal_hit(self, mouse_pos):
        if not self.ice_crystals:
            return None
        local_x, local_y = self.to_local_damage_layer_pos(mouse_pos)
        for crystal in self.ice_crystals:
            crystal_x, crystal_y = crystal.get('local_pos', self.get_target_center_local())
            radius = float(crystal.get('radius', 14.0) or 14.0)
            if math.hypot(local_x - crystal_x, local_y - crystal_y) <= radius + 5.0:
                return crystal
        return None

    def pop_ice_crystal(self, crystal=None):
        if not self.ice_crystals:
            return None
        if crystal and crystal in self.ice_crystals:
            self.ice_crystals.remove(crystal)
            return crystal
        return self.ice_crystals.pop(0)

    def simulate_projectile_hit(self, mouse_pos):
        spread_radius = 15
        angle = random.uniform(0, 2 * math.pi)
        radius = random.uniform(0, spread_radius)
        offset_x = radius * math.cos(angle)
        offset_y = radius * math.sin(angle)
        hit_pos = (mouse_pos[0] + offset_x, mouse_pos[1] + offset_y)
        logging.info(f"Simulated projectile hit at {hit_pos}")
        return hit_pos

    def expand_shotgun_damage_for_display(self, damage_list, fragment_count=6):
        if not damage_list or fragment_count <= 1:
            return damage_list

        primary_damage, primary_hit_pos, primary_is_crit, primary_weakspot_hit = damage_list[0]
        primary_damage_int = max(1, int(round(primary_damage)))
        base_fragment_damage, remainder = divmod(primary_damage_int, fragment_count)
        display_entries = []

        # Imported shotgun entries sometimes store one aggregated hit; when the
        # unified mode is off, split that number into pellet-sized visuals.
        for fragment_index in range(fragment_count):
            fragment_damage = base_fragment_damage + (1 if fragment_index < remainder else 0)
            if fragment_damage <= 0:
                continue
            fragment_hit_pos = self.simulate_projectile_hit(primary_hit_pos)
            display_entries.append((
                fragment_damage,
                fragment_hit_pos,
                primary_is_crit,
                primary_weakspot_hit,
            ))

        return display_entries + list(damage_list[1:])

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
        if status in {'the_bulls_eye', 'bulls_eye'}:
            duration *= 1 + self.player.stats.get('marked_duration_percent', 0) / 100.0
        nested_effects = kwargs.get('effects', [])
        normalized_effects = normalize_effects(nested_effects) if nested_effects else []
        derived_stat_bonuses = dict(kwargs.get('stat_bonuses', {}) or {})
        derived_bonus_aliases = {
            'attack_bonus_percent': 'weapon_damage_percent',
            'weapon_damage_bonus_percent': 'weapon_damage_percent',
            'vulnerability_bonus_percent': 'vulnerability_percent',
            'weakspot_damage_bonus_percent': 'weakspot_damage_percent',
            'crit_rate_bonus_percent': 'crit_rate_percent',
            'crit_dmg_bonus_percent': 'crit_damage_percent',
            'blaze_elemental_damage_percent': 'burn_elemental_damage_percent',
        }
        for bonus_key, stat_name in derived_bonus_aliases.items():
            if bonus_key in kwargs:
                bonus_value = kwargs.get(bonus_key)
                if isinstance(bonus_value, (int, float, bool)):
                    if isinstance(bonus_value, bool):
                        derived_stat_bonuses[stat_name] = bonus_value
                    else:
                        derived_stat_bonuses[stat_name] = derived_stat_bonuses.get(stat_name, 0) + bonus_value
        preserve_target_status = bool(
            status in {'the_bulls_eye', 'bulls_eye'}
            or kwargs.get('damage_formula') is not None
            or kwargs.get('damage_type') is not None
        )
        if preserve_target_status and derived_stat_bonuses:
            source_name = kwargs.get('source', status)
            for stat_name, stat_value in derived_stat_bonuses.items():
                if isinstance(stat_value, bool):
                    self.player.apply_stat_bonus(
                        stat_name,
                        1 if stat_value else 0,
                        duration,
                        max_stacks=kwargs.get('max_stacks'),
                        source=source_name,
                    )
                else:
                    self.player.apply_stat_bonus(
                        stat_name,
                        stat_value,
                        duration,
                        max_stacks=kwargs.get('max_stacks'),
                        source=source_name,
                    )
        elif not normalized_effects and derived_stat_bonuses:
            normalized_effects = []
            for stat_name, stat_value in derived_stat_bonuses.items():
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
            self.status_started_at.setdefault(status, time.time())
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
        self.status_started_at.setdefault(status, time.time())
        logging.debug(f"Status {status} applied for {duration} seconds.")
        if status in {'the_bulls_eye', 'bulls_eye'}:
            self.process_combat_event('trigger_bulls_eye')
            self.process_combat_event('enemy_marked')

    def remove_buff(self, buff_name):
        buff_data = self.buffs.pop(buff_name, None)
        if not buff_data:
            return
        source = buff_data.get('source') or f"buff:{buff_name}"
        self.player.remove_stat_bonus_source(source)
        self.refresh_player_stats()
        logging.info(f"Buff {buff_name} removed.")

    def calculate_status_damage(self, base_damage, damage_type, bonus_stats=None):
        damage = float(base_damage)
        bonus_stats = bonus_stats or []
        damage *= 1 + self.player.stats.get('status_damage_percent', 0) / 100.0
        damage *= 1 + self.player.stats.get('elemental_damage_percent', 0) / 100.0
        for stat_name in bonus_stats:
            damage *= 1 + self.player.stats.get(stat_name, 0) / 100.0
        damage = self.apply_dynamic_damage_bonuses(
            damage,
            is_crit=False,
            weakspot_hit=False,
            damage_kind=damage_type,
        )
        return damage

    def apply_dynamic_damage_bonuses(self, damage, *, is_crit=False, weakspot_hit=False, damage_kind='weapon'):
        damage *= 1 + self.player.stats.get('vulnerability_percent', 0) / 100.0

        if self.is_status_active('the_bulls_eye') or self.is_status_active('bulls_eye'):
            damage *= 1 + self.player.stats.get('marked_target_damage_percent', 0) / 100.0
            if weakspot_hit:
                damage *= 1 + self.player.stats.get('marked_target_weakspot_damage_percent', 0) / 100.0
            if is_crit:
                damage *= 1 + self.player.stats.get('marked_target_crit_damage_percent', 0) / 100.0

        if self.is_status_active('power_surge'):
            damage *= 1 + self.player.stats.get('damage_to_shocked_target_percent', 0) / 100.0

        if damage_kind in {'weapon', 'bounce', 'shrapnel'} and self.is_status_active('fast_gunner'):
            damage *= 1 + self.player.stats.get('fast_gunner_weapon_damage_percent', 0) / 100.0

        if damage_kind == 'burn':
            damage *= 1 + self.player.stats.get('burn_elemental_damage_percent', 0) / 100.0
        elif damage_kind == 'frost':
            damage *= 1 + self.player.stats.get('frost_elemental_damage_percent', 0) / 100.0
        elif damage_kind in {'shock', 'power_surge'}:
            damage *= 1 + self.player.stats.get('shock_elemental_damage_percent', 0) / 100.0
            if is_crit:
                damage *= 1 + self.player.stats.get('shock_crit_damage_percent', 0) / 100.0
        elif damage_kind == 'bounce':
            damage *= 1 + self.player.stats.get('bounce_damage_percent', 0) / 100.0
            if weakspot_hit:
                damage *= 1 + self.player.stats.get('bounce_weakspot_damage_percent', 0) / 100.0
            if is_crit:
                damage *= 1 + self.player.stats.get('bounce_crit_dmg_percent', 0) / 100.0

        return damage

    def trigger_ability(self, ability_name, **kwargs):
        ability_lower = ability_name.lower()
        logging.info(f"Triggered ability: {ability_name} with {kwargs}")
        if ability_lower in {'the_bullseye', 'the_bulls_eye', 'bulls_eye'}:
            duration = kwargs.get('duration_seconds', 12.0) * (1 + self.player.stats.get('marked_duration_percent', 0) / 100.0)
            vulnerability_bonus = float(kwargs.get('vulnerability_bonus_percent', 8) or 0)
            if vulnerability_bonus:
                self.apply_temporary_stat_bonus(
                    'vulnerability_percent',
                    vulnerability_bonus,
                    max(duration, self.get_event_refresh_duration()),
                    max_stacks=1,
                    source='the_bulls_eye:vulnerability',
                )
            self.apply_status('the_bulls_eye', max(duration, 0.5))
            return

        if ability_lower in {'bounce', 'bounce_ricochet'}:
            previous_depth = self.active_bounce_chain_depth
            current_depth = previous_depth + (1 if ability_lower == 'bounce_ricochet' else 0)
            max_depth = int(kwargs.get('max_ricochet_depth', 3) or 3)
            if current_depth > max_depth:
                return
            self.active_bounce_chain_depth = current_depth
            try:
                damage_formula = kwargs.get('damage_formula', {'type': 'attack', 'multiplier': 0.6})
                base_hits = 1 if ability_lower == 'bounce_ricochet' else 1 + max(0, int(round(self.player.stats.get('bounce_trigger_count', 0))))
                total_hits = base_hits + max(0, int(round(self.player.stats.get('bounce_targets', 0))))
                total_hits = max(1, total_hits)

                for _ in range(total_hits):
                    dmg = self.resolve_damage_formula(damage_formula)
                    dmg *= 1 + self.player.stats.get('weapon_damage_percent', 0) / 100.0

                    trigger_bonus = self.trigger_factors.get('bounce') or self.trigger_factors.get(ability_lower) or self.trigger_factors.get(ability_name)
                    if trigger_bonus:
                        end_time = trigger_bonus.get('end_time')
                        if end_time is None or end_time >= time.time():
                            dmg *= 1 + trigger_bonus.get('bonus', 0) / 100.0

                    weakspot_hit = bool(kwargs.get('weakspot_hit', False) or kwargs.get('can_hit_weakspots', False))
                    guaranteed_crit = bool(self.consume_temporary_flag('guaranteed_crit', False))
                    precision_bounce = bool(self.consume_temporary_flag('is_precision_bounce', False))
                    crit_rate = self.player.stats.get('crit_rate_percent', 0) + self.player.stats.get('bounce_crit_rate_percent', 0)
                    is_crit = guaranteed_crit or precision_bounce or (
                        kwargs.get('can_crit', True) and random.uniform(0, 100) <= max(0.0, crit_rate)
                    )
                    if weakspot_hit:
                        dmg *= 1 + self.player.stats.get('weakspot_damage_percent', 0) / 100.0
                    if is_crit:
                        dmg *= 1 + self.player.stats.get('crit_damage_percent', 0) / 100.0
                    dmg = self.apply_dynamic_damage_bonuses(
                        dmg,
                        is_crit=is_crit,
                        weakspot_hit=weakspot_hit,
                        damage_kind='bounce',
                    )
                    self.apply_direct_damage(dmg, is_crit=is_crit, weakspot_hit=weakspot_hit, ability_name='bounce')
                    target_defeated = self.mannequin.current_hp <= 0
                    self.process_combat_event('bounce_hit', is_crit=is_crit, is_weakspot=weakspot_hit)
                    if weakspot_hit:
                        self.process_combat_event('bounce_hit_weakspot', is_crit=is_crit, is_weakspot=True)
                    if not target_defeated:
                        self.process_combat_event('bounce_did_not_defeat_or_no_target', is_crit=is_crit, is_weakspot=weakspot_hit)
                if self.player.stats.get('bounce_can_hit_allies'):
                    available_targets = 1 + max(0, int(self.enemies_within_distance))
                    ally_hits = max(0, total_hits - available_targets)
                    for _ in range(ally_hits):
                        self.process_combat_event('bounce_hit_ally', is_crit=False, is_weakspot=False)
                return
            finally:
                self.active_bounce_chain_depth = previous_depth

        if ability_lower == 'unstable_bomber':
            damage_formula = kwargs.get('damage_formula', {'type': 'psi_intensity', 'multiplier': 1.0})
            self.process_combat_event('unstable_bomber_hits_one_enemy', is_crit=False, is_weakspot=False)
            self.process_combat_event('before_bomb_explodes', is_crit=False, is_weakspot=False)
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

            delay_seconds = float(kwargs.get('delay_seconds', 0) or 0) + float(self.player.stats.get('unstable_bomber_delay_bonus_seconds', 0) or 0)
            delay_scaling = float(self.player.stats.get('unstable_bomber_damage_per_delay_step_percent', 0) or 0)
            if delay_seconds > 0 and delay_scaling > 0:
                dmg *= 1 + ((delay_seconds / 0.1) * delay_scaling) / 100.0

            additional_info = kwargs.get('additional_info', {})
            can_crit = kwargs.get('can_crit', additional_info.get('can_crit', False)) or self.player.stats.get('can_crit', False)
            is_crit = bool(self.player.stats.get('unstable_bomber_guaranteed_crit', False))
            if not is_crit and can_crit and random.uniform(0, 100) <= self.player.stats.get('crit_rate_percent', 0):
                is_crit = True
                crit_bonus = self.player.stats.get('crit_damage_percent', 0) + self.player.stats.get('unstable_bomber_crit_damage_percent', 0)
                dmg *= 1 + crit_bonus / 100.0
            elif is_crit:
                crit_bonus = self.player.stats.get('crit_damage_percent', 0) + self.player.stats.get('unstable_bomber_crit_damage_percent', 0)
                dmg *= 1 + crit_bonus / 100.0
            dmg = self.apply_dynamic_damage_bonuses(
                dmg,
                is_crit=is_crit,
                weakspot_hit=False,
                damage_kind='unstable_bomber',
            )

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
            weakspot_chance = max(0.0, min(100.0, self.player.stats.get('shrapnel_weakspot_hit_chance_percent', 0)))
            weakspot_hit = random.uniform(0, 100) <= weakspot_chance
            if weakspot_hit:
                weakspot_bonus = self.player.stats.get('weakspot_damage_percent', 0) + self.player.stats.get('shrapnel_weakspot_damage_percent', 0)
                dmg *= 1 + weakspot_bonus / 100.0
            guaranteed_crit = bool(self.consume_temporary_flag('guaranteed_crit', False))
            is_crit = guaranteed_crit or (kwargs.get('can_crit', False) and random.uniform(0, 100) <= self.player.stats.get('crit_rate_percent', 0))
            if is_crit:
                crit_bonus = self.player.stats.get('crit_damage_percent', 0) + self.player.stats.get('shrapnel_crit_damage_percent', 0)
                dmg *= 1 + crit_bonus / 100.0
            dmg = self.apply_dynamic_damage_bonuses(
                dmg,
                is_crit=is_crit,
                weakspot_hit=weakspot_hit,
                damage_kind='shrapnel',
            )
            self.apply_direct_damage(dmg, is_crit=is_crit, weakspot_hit=weakspot_hit, ability_name='shrapnel')
            self.process_combat_event('trigger_shrapnel', is_crit=is_crit, is_weakspot=weakspot_hit)
            if weakspot_hit:
                self.process_combat_event('shrapnel_hit_weakspot', is_crit=is_crit, is_weakspot=True)
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
            self.apply_direct_damage(dmg, is_crit=False, weakspot_hit=False, ability_name='celestial_thunder')
            self.process_combat_event('deal_power_surge_damage', is_crit=False, is_weakspot=False)
            return

        if ability_lower == 'explosion':
            damage_formula = kwargs.get('damage_formula', {'type': 'psi_intensity', 'multiplier': 1.0})
            damage_type = str(kwargs.get('damage_type', 'burn') or 'burn').lower()
            normalized_damage_type = 'burn' if damage_type in {'blaze', 'burn'} else damage_type
            bonus_stats = ['explosion_elemental_damage_percent']
            if normalized_damage_type == 'burn':
                bonus_stats.extend(['burn_damage_percent', 'burn_elemental_damage_percent'])
            dmg = self.calculate_status_damage(
                self.resolve_damage_formula(damage_formula),
                normalized_damage_type,
                bonus_stats,
            )
            self.apply_direct_damage(dmg, is_crit=False, weakspot_hit=False, ability_name='explosion')
            burn_payload = {
                'damage_formula': {'type': 'psi_intensity', 'multiplier': 0.4},
                'damage_type': 'burn',
                'tick_interval': 1.0,
            }
            self.apply_status('burn', 6.0, max_stacks=self.player.stats.get('max_burn_stacks'), **burn_payload)
            self.process_combat_event('deal_explosion_damage', is_crit=False, is_weakspot=False)
            return

        if ability_lower == 'burn':
            damage_formula = kwargs.get('damage_formula', {'type': 'psi_intensity', 'multiplier': 0.4})
            duration = kwargs.get('duration_seconds', 6.0) * (1 + self.player.stats.get('burn_duration_percent', 0) / 100.0)
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
            frost_duration = kwargs.get('duration_seconds', 6.0) * (1 + self.player.stats.get('frost_vortex_duration_percent', 0) / 100.0)
            self.apply_status('frost_vortex', frost_duration)
            for effect in self.player.static_effects:
                if effect.get('type') != 'frost_vortex_applies':
                    continue
                for nested_effect in normalize_effects(effect.get('effects', [])):
                    if nested_effect.get('type') != 'apply_status' or not nested_effect.get('status'):
                        continue
                    nested_duration = nested_effect.get('duration_seconds', frost_duration) or frost_duration
                    kwargs_payload = {k: v for k, v in nested_effect.items() if k not in {'type', 'status', 'duration_seconds'}}
                    self.apply_status(nested_effect['status'], nested_duration, **kwargs_payload)
            self.refresh_player_stats()
            self.process_combat_event('trigger_frost_vortex', is_crit=False, is_weakspot=False)
            self.process_combat_event('frost_vortex_triggered', is_crit=False, is_weakspot=False)
            return

        if ability_lower == 'fortress_warfare':
            fortress_duration = kwargs.get('duration_seconds', 8.0) * (1 + self.player.stats.get('fortress_warfare_duration_percent', 0) / 100.0)
            self.set_mode('fortress_warfare', fortress_duration)
            self.apply_status('fortress_warfare', fortress_duration)
            self.process_combat_event('fortress_warfare_triggered', is_crit=False, is_weakspot=False)
            self.process_combat_event('grant_ally_buff', is_crit=False, is_weakspot=False)
            return

        if ability_lower == 'fast_gunner':
            duration = kwargs.get('duration_seconds', 2.0) * (1 + self.player.stats.get('fast_gunner_duration_percent', 0) / 100.0)
            max_stacks = int(kwargs.get('max_stacks') or self.player.stats.get('fast_gunner_max_stacks', 5) or 5)
            stat_bonuses = kwargs.get('stat_bonuses') or {
                'fire_rate_percent': 1,
                'attack_percent': 1,
            }
            previous_stacks = self.status_stack_counts.get('fast_gunner', 0)
            self.apply_status('fast_gunner', duration, max_stacks=max_stacks, stat_bonuses=stat_bonuses)
            current_stacks = self.status_stack_counts.get('fast_gunner', previous_stacks)
            if current_stacks > previous_stacks:
                self.process_combat_event('trigger_fast_gunner', is_crit=False, is_weakspot=False)
                if current_stacks % 5 == 0:
                    self.process_combat_event('fast_gunner_stack_reached_multiple_of_5', is_crit=False, is_weakspot=False)
                if previous_stacks < max_stacks <= current_stacks:
                    self.process_combat_event('fast_gunner_max_stacks', is_crit=False, is_weakspot=False)
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
        effective_duration = duration if duration and duration > 0 else 999999
        self.player.apply_stat_bonus(stat, value, effective_duration, max_stacks, source=source)

    def register_reset_source(self, event_name, source_prefix):
        if not event_name or not source_prefix:
            return
        self.reset_sources_by_event.setdefault(event_name, set()).add(source_prefix)

    def reset_sources_for_event(self, event_name):
        for source_prefix in list(self.reset_sources_by_event.get(event_name, set())):
            self.player.remove_stat_bonus_source(source_prefix)
            for buff_name, buff_data in list(self.buffs.items()):
                buff_source = buff_data.get('source') or f"buff:{buff_name}"
                if buff_source == source_prefix or str(buff_source).startswith(f"{source_prefix}:"):
                    self.remove_buff(buff_name)

    def set_effect_cooldown(self, source, cooldown_seconds):
        if source and cooldown_seconds:
            self.effect_cooldowns[source] = time.time() + cooldown_seconds

    def restore_stamina_percent(self, percent):
        if percent <= 0:
            return
        self.current_stamina = min(self.max_stamina, self.current_stamina + self.max_stamina * (percent / 100.0))

    def apply_special_effect(self, effect):
        effect_name = effect.get('effect_name')
        source = effect.get('source') or effect_name or 'special_effect'
        value = float(effect.get('value', 0) or 0)
        if effect_name == 'shrapnel_weakspot_hit_chance_increase':
            self.apply_temporary_stat_bonus('shrapnel_weakspot_hit_chance_percent', value, self.get_event_refresh_duration(), 1, source=source)
        elif effect_name in {'frost_vortex_damage_increase', 'frost_vortex_ultimate_damage_increase'}:
            self.apply_temporary_stat_bonus('frost_vortex_damage_percent', value, self.get_event_refresh_duration(), 1, source=source)

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

    def generate_ice_crystal(self, cooldown_seconds, source='weapon'):
        current_time = time.time()
        if cooldown_seconds and current_time < self.next_ice_crystal_available_at:
            return
        base_x, base_y = self.to_local_damage_layer_pos(self.last_shot_mouse_pos)
        if not self.is_within_target_area(self.to_screen_damage_layer_pos((base_x, base_y))):
            base_x, base_y = self.get_target_center_local()
        angle = random.uniform(0, 2 * math.pi)
        distance = random.uniform(22.0, 42.0)
        crystal_x = base_x + math.cos(angle) * distance
        crystal_y = base_y + math.sin(angle) * distance
        crystal_x, crystal_y = self.clamp_local_point_to_target(crystal_x, crystal_y)
        self.ice_crystals.append({
            'created_at': current_time,
            'shatter_at': current_time + 15.0,
            'local_pos': (crystal_x, crystal_y),
            'radius': 14.0,
            'source': source,
        })
        self.next_ice_crystal_available_at = current_time + max(0.0, cooldown_seconds or 0.0)
        logging.info(f"Generated Ice Crystal, cooldown: {cooldown_seconds}s")

    def deal_status_damage(self, damage_formula, damage_type, radius_meters, hit_pos=None):
        base_damage = self.resolve_damage_formula(damage_formula)
        damage = self.calculate_status_damage(base_damage, damage_type, [])
        target_count = 1
        if radius_meters and self.enemies_within_distance > 0:
            target_count += int(self.enemies_within_distance)
        self.apply_direct_damage(
            damage * target_count,
            is_crit=False,
            weakspot_hit=False,
            ability_name=damage_type,
            hit_pos=hit_pos,
        )

    def shatter_ice_crystal(self, damage_formula, damage_type):
        crystal = self.pop_ice_crystal(self.get_ice_crystal_hit(self.last_ice_crystal_hit_pos) if self.last_ice_crystal_hit_pos else None)
        self.ice_crystal_shattered = True
        self.set_temporary_flag('ice_crystal_shattered', True, duration_seconds=self.get_event_refresh_duration(), source='ice_crystal')
        crystal_hit_pos = self.last_ice_crystal_hit_pos
        if crystal_hit_pos is None and crystal:
            crystal_hit_pos = self.to_screen_damage_layer_pos(crystal.get('local_pos'))
        self.deal_status_damage(damage_formula, damage_type, 0, hit_pos=crystal_hit_pos)
        self.last_ice_crystal_hit_pos = None

    def grant_infinite_ammo(self, duration_seconds=0, shots=None):
        if duration_seconds:
            self.infinite_ammo_until = max(self.infinite_ammo_until, time.time() + duration_seconds)
        if shots:
            self.free_ammo_shots_remaining = max(self.free_ammo_shots_remaining, int(shots))
            self.current_ammo = max(self.current_ammo, 1)
        logging.debug(
            "Infinite ammo granted: duration=%s, free_shots=%s",
            duration_seconds,
            shots,
        )

    def increase_projectiles_per_shot(self, additional_projectiles):
        additional_projectiles = int(additional_projectiles or 0)
        if additional_projectiles <= 0:
            return
        self.pending_projectiles_per_shot_bonus += additional_projectiles
        logging.debug(
            "Queued +%s projectile(s) for the next shot. Pending bonus: %s",
            additional_projectiles,
            self.pending_projectiles_per_shot_bonus,
        )

    def apply_buff(self, buff_name, duration_bullets=None, stat_bonuses=None, duration_seconds=None, max_stacks=None, source=None):
        source = source or f"buff:{buff_name}"
        if stat_bonuses:
            effective_duration = duration_seconds if duration_seconds and duration_seconds > 0 else 999999
            for stat, val in stat_bonuses.items():
                self.apply_temporary_stat_bonus(stat, val, effective_duration, max_stacks=max_stacks, source=f"{source}:{stat}")
        self.buffs[buff_name] = {
            'duration_bullets': duration_bullets,
            'stat_bonuses': stat_bonuses,
            'source': source,
            'max_stacks': max_stacks,
            'duration_seconds': duration_seconds,
        }
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
        if pickup_type == 'deviant_particle':
            self.charge_stacks += 1
            self.process_combat_event('enter_charge_state', is_crit=False, is_weakspot=False)

    def modify_ammo_type(self, ammo_type, duration_until_reload):
        self.alternate_ammo = ammo_type
        self.alternate_ammo_until_reload = duration_until_reload
        logging.info(f"Ammo type changed to {ammo_type}, revert on reload: {duration_until_reload}")

    def consume_charge(self, effect_data):
        if self.charge_stacks <= 0:
            logging.info("No charges to consume.")
            return
        consumed = min(self.charge_stacks, 4)
        self.charge_stacks -= consumed
        if isinstance(effect_data, dict):
            scaled_effect = copy.deepcopy(effect_data)
            if isinstance(scaled_effect.get('value'), (int, float)):
                scaled_effect['value'] = scaled_effect['value'] * consumed
            effect_context = self.build_effect_context(event_name='consume_charge')
            effect_context['effect_group_source'] = 'charge_state'
            effect_context['effect_source_key'] = f'charge_state:{consumed}'
            effect_context['effect_group_effects'] = [scaled_effect]
            from .mechanics import apply_effect
            apply_effect(scaled_effect, effect_context)
        logging.info(f"Consumed {consumed} charge stack(s). {effect_data}")

    def simulate_special_event(self, event_name):
        event_name = str(event_name or '').strip()
        if not event_name:
            return
        if event_name == 'enter_charge_state':
            self.charge_stacks += 1
        elif event_name == 'shoot_ice_crystal':
            if self.ice_crystals:
                self.ice_crystals.pop(0)
            self.ice_crystal_shattered = True
            self.set_temporary_flag('ice_crystal_shattered', True, duration_seconds=self.get_event_refresh_duration(), source='ice_crystal')
        elif event_name == 'ice_crystal_shatter':
            self.ice_crystal_shattered = True
            self.set_temporary_flag('ice_crystal_shattered', True, duration_seconds=self.get_event_refresh_duration(), source='ice_crystal')
        elif event_name == 'weapon_switch':
            self.weapon_switch_pending = True
            return
        self.process_combat_event(event_name, is_crit=False, is_weakspot=False)

    def area_damage(self, damage_percent, damage_type):
        if damage_percent <= 0:
            return
        self.deal_status_damage({'type': 'attack', 'multiplier': damage_percent / 100.0}, damage_type, self.enemies_within_distance)

    def modify_trigger_factor(self, ability, bonus_percent, duration_seconds=None):
        self.trigger_factors[ability] = {'bonus': bonus_percent,
                                         'end_time': (time.time() + duration_seconds
                                                      if duration_seconds else None)}
        logging.info(f"Trigger factor for {ability} modified by {bonus_percent}% for {duration_seconds} s")

    def check_custom_condition(self, condition):
        return True

    def apply_direct_damage(self, damage, is_crit=False, weakspot_hit=False, ability_name=None, hit_pos=None):
        center_pos = hit_pos or self.get_center_of_hit_area()
        self.mannequin.receive_damage(damage)
        self.total_damage += damage
        damage_time = time.time()
        self.last_damage_time = damage_time
        self.max_total_damage = max(self.max_total_damage, self.total_damage)
        self.damage_history.append((damage_time, damage))
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
            'dmg': 'damage_per_projectile',
        }
        formula_type = alias_map.get(formula_type, formula_type)
        if formula_type == 'psi_intensity':
            return float(self.player.stats.get('psi_intensity', 100)) * multiplier
        stat_value = self.player.stats.get(formula_type, self.player.stats.get('psi_intensity', 100))
        return float(stat_value) * multiplier

    def handle_target_defeat(self, is_crit=False, weakspot_hit=False):
        if self.mannequin.current_hp > 0 or self.enemy_defeated_pending_reset:
            return
        was_marked = self.is_status_active('the_bulls_eye') or self.is_status_active('bulls_eye')
        had_burn = self.is_status_active('burn')
        had_frost_vortex = self.is_status_active('frost_vortex')
        is_melee = bool(self.player.weapon and self.player.weapon.type == 'melee')
        self.enemy_defeated_pending_reset = True
        self.same_target_hit_streak = 0
        self.kills_count += 1
        self.process_combat_event('kill', is_crit=is_crit, is_weakspot=weakspot_hit)
        self.process_combat_event('defeat_enemy', is_crit=is_crit, is_weakspot=weakspot_hit)
        self.process_combat_event('kill_enemy_within_distance', is_crit=is_crit, is_weakspot=weakspot_hit)
        if self.kills_count % 2 == 0:
            self.process_combat_event('accumulated_kills', is_crit=is_crit, is_weakspot=weakspot_hit)
            self.process_combat_event('kill_two_enemies', is_crit=is_crit, is_weakspot=weakspot_hit)
        if self.current_mode == 'fortress_warfare':
            self.process_combat_event('enemy_defeated_in_fortress', is_crit=is_crit, is_weakspot=weakspot_hit)
        if had_frost_vortex:
            self.process_combat_event('enemy_defeated_at_center', is_crit=is_crit, is_weakspot=weakspot_hit)
        if weakspot_hit:
            self.process_combat_event('defeat_enemy_with_weakspot_hit', is_crit=is_crit, is_weakspot=True)
        if was_marked:
            self.process_combat_event('defeat_marked_enemy', is_crit=is_crit, is_weakspot=weakspot_hit)
            self.process_combat_event('marked_enemy_defeated', is_crit=is_crit, is_weakspot=weakspot_hit)
        if had_burn:
            self.process_combat_event('kill_enemy_with_burn', is_crit=is_crit, is_weakspot=weakspot_hit)
            self.process_combat_event('defeat_enemy_with_burn', is_crit=is_crit, is_weakspot=weakspot_hit)
        if is_melee:
            self.process_combat_event('melee_kill', is_crit=is_crit, is_weakspot=weakspot_hit)

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
