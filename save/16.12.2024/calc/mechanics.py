# mechanics.py

import json
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import random
import logging
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


def load_weapon_data() -> List[Dict[str, Any]]:
    with open('weapon_list.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['weapons']


def add_stats(stats_dict, new_stats):
    for stat, value in new_stats.items():
        if isinstance(value, dict):
            if stat not in stats_dict:
                stats_dict[stat] = {}
            add_stats(stats_dict[stat], value)
        elif isinstance(value, (int, float)):
            current_value = stats_dict.get(stat, 0)
            stats_dict[stat] = current_value + value


def check_conditions(conditions: Dict[str, Any], target, context, **kwargs):
    # Проверяем условия для событий
    for key, val in conditions.items():
        if key == "target_is_marked":
            if kwargs.get("target_is_marked", False) != val:
                return False
        elif key == "status":
            status_to_check = val
            if not context or not context.check_status_on_target(status_to_check):
                return False
        elif key == "attacking_specific_target":
            target_name = val
            if not context or context.enemy_type != target_name:
                return False
        elif key == "hp_above_percent":
            required_hp = val
            current_hp_ratio = context.get_player_hp_ratio() if context else 1.0
            if current_hp_ratio * 100 < required_hp:
                return False
        elif key == "mode":
            if not context or context.current_mode != val:
                return False
        elif key == "count":
            if context.get_count_for_event(kwargs.get('event_name', '')) < val:
                return False
        # По аналогии можно расширять проверку других условий
    return True


class Effect(ABC):
    @abstractmethod
    def apply(self, target, context=None, **kwargs):
        pass


class IncreaseStatEffect(Effect):
    def __init__(self, stat: str, value: float, duration: float = None, max_stacks: int = None):
        self.stat = stat
        self.value = value
        self.duration = duration
        self.max_stacks = max_stacks

    def apply(self, target, context=None, **kwargs):
        if self.duration and context:
            context.apply_temporary_stat_bonus(self.stat, self.value, self.duration, self.max_stacks)
        else:
            if hasattr(target, 'stats'):
                original_value = target.stats.get(self.stat, 0)
                target.stats[self.stat] = original_value + self.value
                logging.debug(f"{self.stat} increased by {self.value}. New value: {target.stats[self.stat]}")


class DecreaseStatEffect(Effect):
    def __init__(self, stat: str, value: float):
        self.stat = stat
        self.value = value

    def apply(self, target, context=None, **kwargs):
        if hasattr(target, 'stats'):
            original_value = target.stats.get(self.stat, 0)
            target.stats[self.stat] = original_value - self.value
            logging.debug(f"{self.stat} decreased by {self.value}. New value: {target.stats[self.stat]}")


class ApplyStatusEffect(Effect):
    def __init__(self, status: str, duration: float, **kwargs):
        self.status = status
        self.duration = duration
        self.kwargs = kwargs

    def apply(self, target, context=None, **kwargs):
        if context:
            context.apply_status(self.status, self.duration, **self.kwargs)
        logging.debug(f"Status {self.status} applied for {self.duration} seconds.")


class TriggerAbilityEffect(Effect):
    def __init__(self, ability: str, **kwargs):
        self.ability = ability
        self.kwargs = kwargs

    def apply(self, target, context=None, **kwargs):
        if context:
            context.trigger_ability(self.ability, **self.kwargs)
        logging.debug(f"Ability {self.ability} triggered with params {self.kwargs}")


class IncrementCounterEffect(Effect):
    def __init__(self, counter: str, value: int = 1):
        self.counter = counter
        self.value = value

    def apply(self, target, context=None, **kwargs):
        if context:
            context.increment_counter(self.counter, self.value)
        logging.debug(f"Counter {self.counter} incremented by {self.value}.")


class CountAsHitsEffect(Effect):
    def __init__(self, value: int):
        self.value = value

    def apply(self, target, context=None, **kwargs):
        if context:
            context.increment_hit_count(self.value)
        logging.debug(f"Hits count as {self.value}.")


class ModifyChanceEffect(Effect):
    def __init__(self, base_event: str, new_chance_percent: float):
        self.base_event = base_event
        self.new_chance_percent = new_chance_percent

    def apply(self, target, context=None, **kwargs):
        if context:
            context.modify_event_chance(self.base_event, self.new_chance_percent)
        logging.debug(f"Event {self.base_event} chance changed to {self.new_chance_percent}%.")


class GainStackEffect(Effect):
    def __init__(self, stack_type: str, count: int):
        self.stack_type = stack_type
        self.count = count

    def apply(self, target, context=None, **kwargs):
        if context:
            context.gain_stacks(self.stack_type, self.count)
        logging.debug(f"Gained {self.count} stacks of {self.stack_type}.")


class ReduceStackEffect(Effect):
    def __init__(self, stack_type: str, value: int):
        self.stack_type = stack_type
        self.value = value

    def apply(self, target, context=None, **kwargs):
        if context:
            context.reduce_stacks(self.stack_type, self.value)
        logging.debug(f"Reduced stacks of {self.stack_type} by {self.value}.")


class SpreadEffect(Effect):
    def __init__(self, radius_meters: float, effect: Dict[str, Any]):
        self.radius_meters = radius_meters
        self.effect_data = effect

    def apply(self, target, context=None, **kwargs):
        if context:
            context.spread_effect(self.radius_meters, self.effect_data)
        logging.debug(f"Spread effect in {self.radius_meters}m radius.")


class GenerateIceCrystalEffect(Effect):
    def __init__(self, cooldown_seconds: float):
        self.cooldown_seconds = cooldown_seconds

    def apply(self, target, context=None, **kwargs):
        if context:
            context.generate_ice_crystal(self.cooldown_seconds)
        logging.debug(f"Generated Ice Crystal with cooldown {self.cooldown_seconds}s.")


class DealStatusDmgEffect(Effect):
    def __init__(self, damage_formula: str, damage_type: str, radius_meters: float):
        self.damage_formula = damage_formula
        self.damage_type = damage_type
        self.radius_meters = radius_meters

    def apply(self, target, context=None, **kwargs):
        if context:
            context.deal_status_damage(self.damage_formula, self.damage_type, self.radius_meters)
        logging.debug(f"Dealt status dmg {self.damage_formula} ({self.damage_type}) in {self.radius_meters}m radius.")


class ShatterIceCrystalEffect(Effect):
    def __init__(self, damage_formula: str, damage_type: str):
        self.damage_formula = damage_formula
        self.damage_type = damage_type

    def apply(self, target, context=None, **kwargs):
        if context:
            context.shatter_ice_crystal(self.damage_formula, self.damage_type)
        logging.debug(f"Shattered ice crystal, dmg {self.damage_formula}, type {self.damage_type}.")


class GrantInfiniteAmmoEffect(Effect):
    def __init__(self, duration_seconds: float):
        self.duration_seconds = duration_seconds

    def apply(self, target, context=None, **kwargs):
        if context:
            context.grant_infinite_ammo(self.duration_seconds)
        logging.debug(f"Infinite ammo granted for {self.duration_seconds}s.")


class IncreaseProjectilesEffect(Effect):
    def __init__(self, additional_projectiles: int):
        self.additional_projectiles = additional_projectiles

    def apply(self, target, context=None, **kwargs):
        if context:
            context.increase_projectiles_per_shot(self.additional_projectiles)
        logging.debug(f"Increased projectiles per shot by {self.additional_projectiles}.")


class ApplyBuffEffect(Effect):
    def __init__(self, buff_name: str, duration_bullets: int = None, stat_bonuses: dict = None):
        self.buff_name = buff_name
        self.duration_bullets = duration_bullets
        self.stat_bonuses = stat_bonuses or {}

    def apply(self, target, context=None, **kwargs):
        if context:
            context.apply_buff(self.buff_name, self.duration_bullets, self.stat_bonuses)
        logging.debug(f"Buff {self.buff_name} applied.")


class ModifyBehaviorEffect(Effect):
    def __init__(self, behavior: str, enabled: bool):
        self.behavior = behavior
        self.enabled = enabled

    def apply(self, target, context=None, **kwargs):
        if context:
            context.modify_behavior(self.behavior, self.enabled)
        logging.debug(f"Behavior {self.behavior} set to {self.enabled}.")


class ReloadAmmoEffect(Effect):
    def __init__(self, amount: int = None):
        self.amount = amount

    def apply(self, target, context=None, **kwargs):
        if context:
            context.reload_ammo(self.amount)
        logging.debug(f"Ammo reloaded by {self.amount}.")


class RestoreBulletEffect(Effect):
    def __init__(self, amount: int = 1):
        self.amount = amount

    def apply(self, target, context=None, **kwargs):
        if context:
            context.restore_bullet(self.amount)
        logging.debug(f"Restored {self.amount} bullets.")


class RefillBulletEffect(Effect):
    def apply(self, target, context=None, **kwargs):
        if context:
            context.refill_bullet()
        logging.debug("Bullet refilled.")


class ConsumeExtraAmmoEffect(Effect):
    def __init__(self, amount: int):
        self.amount = amount

    def apply(self, target, context=None, **kwargs):
        if context:
            context.consume_extra_ammo(self.amount)
        logging.debug(f"Consumed {self.amount} extra ammo.")


class SpawnPickupEffect(Effect):
    def __init__(self, pickup_type: str):
        self.pickup_type = pickup_type

    def apply(self, target, context=None, **kwargs):
        if context:
            context.spawn_pickup(self.pickup_type)
        logging.debug(f"Spawned pickup {self.pickup_type}.")


class ModifyAmmoEffect(Effect):
    def __init__(self, ammo_type: str, duration_until_reload: bool):
        self.ammo_type = ammo_type
        self.duration_until_reload = duration_until_reload

    def apply(self, target, context=None, **kwargs):
        if context:
            context.modify_ammo_type(self.ammo_type, self.duration_until_reload)
        logging.debug(f"Ammo type modified to {self.ammo_type}, until reload: {self.duration_until_reload}.")


class ConsumeChargeEffect(Effect):
    def __init__(self, effect_data: Dict[str, Any]):
        self.effect_data = effect_data

    def apply(self, target, context=None, **kwargs):
        if context:
            context.consume_charge(self.effect_data)
        logging.debug(f"Charge consumed with effect {self.effect_data}.")


class AreaDamageEffect(Effect):
    def __init__(self, damage_percent: float, damage_type: str):
        self.damage_percent = damage_percent
        self.damage_type = damage_type

    def apply(self, target, context=None, **kwargs):
        if context:
            context.area_damage(self.damage_percent, self.damage_type)
        logging.debug(f"Area damage {self.damage_percent}% {self.damage_type} dealt.")


class ModifyTriggerFactorEffect(Effect):
    def __init__(self, ability: str, bonus_percent: float, duration_seconds: float = None):
        self.ability = ability
        self.bonus_percent = bonus_percent
        self.duration_seconds = duration_seconds

    def apply(self, target, context=None, **kwargs):
        if context:
            context.modify_trigger_factor(self.ability, self.bonus_percent, self.duration_seconds)
        logging.debug(f"Trigger factor for {self.ability} modified by {self.bonus_percent}% for {self.duration_seconds} s.")


class ConditionalStatBonusEffect(Effect):
    def __init__(self, condition: str, stat: str, value: float, increment: float = None, max_stacks: int = None, duration_seconds: float = None):
        self.condition = condition
        self.stat = stat
        self.value = value
        self.increment = increment
        self.max_stacks = max_stacks
        self.duration_seconds = duration_seconds

    def apply(self, target, context=None, **kwargs):
        if context and context.check_custom_condition(self.condition):
            if self.duration_seconds:
                context.apply_temporary_stat_bonus(self.stat, self.value, self.duration_seconds, self.max_stacks)
            else:
                if hasattr(target, 'stats'):
                    original_value = target.stats.get(self.stat, 0)
                    target.stats[self.stat] = original_value + self.value
                    logging.debug(f"Conditional bonus: {self.stat} +{self.value}.")

class PassiveEffect(Effect):
    def __init__(self, effect_name: str, properties: dict):
        self.effect_name = effect_name
        self.properties = properties

    def apply(self, target, context=None, **kwargs):
        # Применяем пассивные свойства к целевым статам
        # Допустим, что properties может содержать стат-бонусы, подобно increase_stat
        # Пример: {"damage_bonus_percent": 30} - увеличим stat damage_bonus_percent
        if hasattr(target, 'stats'):
            for prop, val in self.properties.items():
                # Если значение - число, увеличим стат
                if isinstance(val, (int, float)):
                    target.stats[prop] = target.stats.get(prop, 0) + val
                    logging.debug(f"PassiveEffect: {prop} increased by {val}. New val: {target.stats[prop]}")
                else:
                    # Если не число, просто логируем
                    logging.debug(f"PassiveEffect property {prop}={val} not applied as stat.")
        else:
            logging.debug(f"PassiveEffect {self.effect_name} applied but target has no stats.")
class GainBuffEffect(Effect):
    def __init__(self, buff_name: str, duration_seconds: float = None, stat_bonuses: dict = None):
        self.buff_name = buff_name
        self.duration_seconds = duration_seconds
        self.stat_bonuses = stat_bonuses or {}

    def apply(self, target, context=None, **kwargs):
        if context:
            context.apply_buff(self.buff_name, duration_bullets=None, stat_bonuses=self.stat_bonuses)
        logging.info(f"Buff {self.buff_name} gained.")

class RemoveBuffEffect(Effect):
    def __init__(self, buff_name: str):
        self.buff_name = buff_name

    def apply(self, target, context=None, **kwargs):
        if context:
            context.remove_buff(self.buff_name)
        logging.info(f"Buff {self.buff_name} removed.")



EFFECT_CONSTRUCTORS = {
    'increase_stat': lambda data: IncreaseStatEffect(data['stat'], data['value'], data.get('duration_seconds'), data.get('max_stacks')),
    'decrease_stat': lambda data: DecreaseStatEffect(data['stat'], data['value']),
    'apply_status': lambda data: ApplyStatusEffect(
        data['status'],
        data['duration_seconds'],
        **{k: v for k, v in data.items() if k not in ['type', 'status', 'duration_seconds']}
    ),
    'trigger_ability': lambda data: TriggerAbilityEffect(
        data['ability'],
        **{k: v for k, v in data.items() if k not in ['type', 'ability']}
    ),
    'increment_hit_count': lambda data: IncrementCounterEffect('hit_count', data.get('value', 1)),
    'count_as_hits': lambda data: CountAsHitsEffect(data['value']),
    'modify_chance': lambda data: ModifyChanceEffect(data['base_event'], data['new_chance_percent']),
    'gain_stack': lambda data: GainStackEffect(data['stack_type'], data['count']),
    'reduce_stack': lambda data: ReduceStackEffect(data['stack_type'], data['value']),
    'spread_effect': lambda data: SpreadEffect(data['radius_meters'], data['effect']),
    'generate_ice_crystal': lambda data: GenerateIceCrystalEffect(data.get('cooldown_seconds', 0)),
    'deal_status_dmg': lambda data: DealStatusDmgEffect(data['damage_formula'], data['damage_type'], data['radius_meters']),
    'shatter_ice_crystal': lambda data: ShatterIceCrystalEffect(data['damage_formula'], data['damage_type']),
    'grant_infinite_ammo': lambda data: GrantInfiniteAmmoEffect(data['duration_seconds']),
    'increase_projectiles_per_shot': lambda data: IncreaseProjectilesEffect(data['additional_projectiles']),
    'apply_buff': lambda data: ApplyBuffEffect(
        data.get('buff_name', 'unnamed_buff'),  # Значение по умолчанию, если buff_name нет
        data.get('duration_bullets'),
        data.get('stat_bonuses', {})
    ),
    'modify_behavior': lambda data: ModifyBehaviorEffect(data['behavior'], data['enabled']),
    'reload_ammo': lambda data: ReloadAmmoEffect(data.get('amount', 1)),
    'restore_bullet': lambda data: RestoreBulletEffect(data.get('amount', 1)),
    'refill_bullet': lambda data: RefillBulletEffect(),
    'consume_extra_ammo': lambda data: ConsumeExtraAmmoEffect(data['amount']),
    'spawn_pickup': lambda data: SpawnPickupEffect(data['pickup_type']),
    'modify_ammo': lambda data: ModifyAmmoEffect(data['ammo_type'], data['duration_until_reload']),
    'consume_charge': lambda data: ConsumeChargeEffect(data['effect']),
    'area_damage': lambda data: AreaDamageEffect(data['damage_percent'], data['damage_type']),
    'modify_trigger_factor': lambda data: ModifyTriggerFactorEffect(
        data['ability'], data['bonus_percent'], data.get('duration_seconds')
    ),
    'conditional_stat_bonus': lambda data: ConditionalStatBonusEffect(
        data['condition'], data['stat'], data['value'],
        data.get('increment'), data.get('max_stacks'), data.get('duration_seconds')
    ),
    'increment_counter': lambda data: IncrementCounterEffect(data['counter'], data.get('value',1)),
    'passive_effect': lambda data: PassiveEffect(data.get('effect_name',''), data.get('properties', {})),
    'gain_buff': lambda data: GainBuffEffect(
        data.get('buff_name', 'unnamed_buff'),
        data.get('duration_seconds'),
        data.get('stat_bonuses', {})
    ),
    'remove_buff': lambda data: RemoveBuffEffect(data.get('buff_name', 'unnamed_buff'))
}



class Event:
    def __init__(self, name: str, conditions: Dict[str, Any] = None, n: int = None, chance_percent=100, cooldown_seconds=None, interval_seconds=None, distance_meters=None):
        self.name = name
        self.conditions = conditions or {}
        self.n = n
        self.chance = chance_percent
        self.cooldown = cooldown_seconds
        self.interval = interval_seconds
        self.distance = distance_meters
        self.last_trigger_time = 0.0

    def can_trigger(self):
        if self.cooldown:
            current_time = time.time()
            if current_time - self.last_trigger_time < self.cooldown:
                return False
        return True

    def mark_triggered(self):
        if self.cooldown:
            self.last_trigger_time = time.time()

    def check_conditions(self, target, context, **kwargs):
        return check_conditions(self.conditions, target, context, **kwargs)


class Mechanic:
    def __init__(self, description: str, effects: List[Dict[str, Any]]):
        self.description = description
        self.events = self.parse_effects(effects)

    def parse_effects(self, effects_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_events = []
        for effect_data in effects_data:
            event_type = effect_data.get('type')
            if event_type == 'on_event':
                event_name = effect_data['event']
                conditions = effect_data.get('conditions', {})
                n = effect_data.get('n', None)
                chance = effect_data.get('chance_percent', 100)
                cooldown = effect_data.get('cooldown_seconds')
                interval = effect_data.get('interval_seconds')
                distance = effect_data.get('distance_meters')
                counter_name = effect_data.get('counter', None)
                event = Event(event_name, conditions=conditions, n=n, chance_percent=chance,
                              cooldown_seconds=cooldown, interval_seconds=interval, distance_meters=distance)
                event.counter_name = counter_name
                sub_effects = self.create_effects(effect_data.get('effects', []))
                parsed_events.append({'event': event, 'effects': sub_effects})
            elif event_type == 'passive_effect':
                # Пассивный эффект без события
                sub_effects = self.create_effects([effect_data])
                parsed_events.append({'event': None, 'effects': sub_effects})
            elif event_type == 'conditional_stat_bonus':
                # Условный бонус к статам без привязки к событию
                sub_effects = self.create_effects([effect_data])
                parsed_events.append({'event': None, 'effects': sub_effects})
        return parsed_events

    def trigger_event(self, event_name: str, target, context=None, **kwargs):
        for entry in self.events:
            event = entry['event']
            # Пассивные эффекты
            if event is None:
                if event_name == 'passive':
                    for effect in entry['effects']:
                        effect.apply(target, context=context, **kwargs)
                continue

            if event and event.name == event_name:
                if not event.can_trigger():
                    continue
                if event.chance >= 100 or random.randint(1, 100) <= event.chance:
                    if event.check_conditions(target, context, **kwargs):
                        # Если это every_n_shots
                        if event.name == 'every_n_shots' and event.n is not None:
                            counter_to_check = getattr(event, 'counter_name', None) or event.name
                            if context and context.check_counter(counter_to_check, event.n):
                                for effect in entry['effects']:
                                    effect.apply(target, context=context, **kwargs)
                                event.mark_triggered()
                        else:
                            # Обычное событие
                            for effect in entry['effects']:
                                effect.apply(target, context=context, **kwargs)
                            event.mark_triggered()

    def create_effects(self, effects_data: List[Dict[str, Any]]) -> List[Effect]:
        effects = []
        for data in effects_data:
            effect_type = data['type']
            constructor = EFFECT_CONSTRUCTORS.get(effect_type)
            if constructor:
                effect = constructor(data)
                effects.append(effect)
            else:
                logging.warning(f"Unknown effect type: {effect_type}")
        return effects



class Weapon:
    def __init__(self, data: Dict[str, Any]):
        self.id = data['id']
        self.name = data['name']
        self.type = data['type']
        self.rarity = data['rarity']
        self.base_stats = data['base_stats']
        self.mechanics_data = data.get('mechanics', {})
        self.description = data.get('description', '')
        self.star = 1
        self.level = 1
        self.calibration = 0
        self.stats = {}
        self.counters = {}

        if isinstance(self.mechanics_data, dict) and 'description' in self.mechanics_data and 'effects' in self.mechanics_data:
            self.mechanics = Mechanic(self.mechanics_data['description'], self.mechanics_data['effects'])
        else:
            self.mechanics = None

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
                if stat in ['projectiles_per_shot', 'magazine_capacity']:
                    stats[stat] = int(round(new_value))
                else:
                    stats[stat] = new_value
        self.stats = stats
        return stats

    def get_stats(self):
        return self.calculate_stats()

    def apply_status(self, status: str, duration: float, **kwargs):
        # Логика применения статуса к оружию или игроку
        # Передадим вызов в контекст
        pass

    def trigger_ability(self, ability_name, **kwargs):
        # Логика триггера способности оружия
        # Передадим вызов в контекст
        pass

    def trigger_event(self, event_name: str, context=None, **kwargs):
        if self.mechanics:
            self.mechanics.trigger_event(event_name, target=self, context=context, **kwargs)


class MechanicsProcessor:
    def __init__(self, context=None):
        self.weapons_data = load_weapon_data()
        self.weapons = {data['id']: Weapon(data) for data in self.weapons_data}
        self.all_effects = self.get_all_effects()
        self.context = context

    def get_weapon(self, weapon_id: str) -> Weapon:
        return self.weapons.get(weapon_id)

    def get_all_effects(self) -> List[Effect]:
        # Загрузка эффектов модов, если нужно
        try:
            with open('mods_config.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                effects = []
                for category, mods in data.items():
                    for mod in mods:
                        for effect_data in mod['effects']:
                            constructor = EFFECT_CONSTRUCTORS.get(effect_data['type'])
                            if constructor:
                                effect = constructor(effect_data)
                                effects.append(effect)
                return effects
        except FileNotFoundError:
            return []

    def process_weapon_event(self, event_name: str, **kwargs):
        weapon = self.context.player.weapon if self.context else None
        if weapon:
            weapon.trigger_event(event_name, context=self.context, **kwargs)
