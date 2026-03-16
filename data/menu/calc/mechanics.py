# mechanics.py

import os
import json
import random
import time
import logging
import copy
import re
from typing import Dict, Any, Callable, List

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Путь к текущей папке data/menu/calc
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

EffectHandler = Callable[[Dict[str, Any], Dict[str, Any]], None]
CONDITION_HANDLERS: Dict[str, Callable[[Any, Dict[str, Any]], bool or int]] = {}
EFFECT_HANDLERS: Dict[str, EffectHandler] = {}

EVENT_ALIAS_GROUPS = [
    {'shot_fired', 'fire_weapon'},
    {'hit_target', 'hit'},
    {'weakspot_hit', 'hit_weakspot'},
    {'reload', 'reload_weapon'},
    {'reload_empty_mag', 'reload_empty_magazine'},
    {'kill', 'defeat_enemy'},
]

COUNTER_EVENT_ALIASES = {
    'shots': ['shot_fired', 'fire_weapon'],
    'shot': ['shot_fired', 'fire_weapon'],
    'hits': ['hit_target', 'hit'],
    'weapon_hits': ['hit_target', 'hit'],
    'weapon_crit_hits': ['crit_hit', 'non_melee_crit_hit'],
    'crit_hits': ['crit_hit', 'non_melee_crit_hit'],
    'reload': ['reload', 'reload_weapon'],
    'reload_empty_mag': ['reload_empty_mag', 'reload_empty_magazine'],
    'reload_empty_magazine': ['reload_empty_mag', 'reload_empty_magazine'],
    'kill': ['kill', 'defeat_enemy'],
    'kills': ['kill', 'defeat_enemy'],
}


def get_equivalent_events(event_name: str) -> List[str]:
    equivalents = {event_name}
    for group in EVENT_ALIAS_GROUPS:
        if event_name in group:
            equivalents.update(group)
    return list(equivalents)


def resolve_counter_base_events(base_name: str) -> List[str]:
    return COUNTER_EVENT_ALIASES.get(base_name, get_equivalent_events(base_name))


def parse_counter_event(event_name: str, explicit_n: int | None = None) -> Dict[str, Any] | None:
    if explicit_n is not None:
        if event_name.startswith('every_n_'):
            base_name = event_name[len('every_n_'):]
            return {
                'counter_name': event_name,
                'required_count': explicit_n,
                'base_events': resolve_counter_base_events(base_name),
            }
        if event_name.endswith('_n_times'):
            base_name = event_name[:-len('_n_times')]
            return {
                'counter_name': event_name,
                'required_count': explicit_n,
                'base_events': resolve_counter_base_events(base_name),
            }

    match = re.match(r'^every_(\d+)_(.+)$', event_name)
    if match:
        required_count = int(match.group(1))
        base_name = match.group(2)
        return {
            'counter_name': event_name,
            'required_count': required_count,
            'base_events': resolve_counter_base_events(base_name),
        }
    return None


def normalize_effects(effects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not effects:
        return []

    group_duration = None
    group_max_stacks = None
    normalized: List[Dict[str, Any]] = []

    for effect in effects:
        if effect.get('type') == 'set_duration':
            group_duration = effect.get('duration_seconds', group_duration)
        elif effect.get('type') == 'set_max_stacks':
            group_max_stacks = effect.get('value', group_max_stacks)

    for effect in effects:
        effect_type = effect.get('type')
        if effect_type in {'set_duration', 'set_max_stacks'}:
            continue

        prepared = copy.deepcopy(effect)
        if group_duration is not None and effect_type in {'increase_stat', 'apply_status', 'conditional_stat_bonus', 'apply_buff'}:
            prepared.setdefault('duration_seconds', group_duration)
        if group_max_stacks is not None and effect_type in {'increase_stat', 'apply_status', 'conditional_stat_bonus', 'gain_stack'}:
            prepared.setdefault('max_stacks', group_max_stacks)

        nested_effects = prepared.get('effects')
        if isinstance(nested_effects, list):
            prepared['effects'] = normalize_effects(nested_effects)

        nested_effect = prepared.get('effect')
        if isinstance(nested_effect, dict) and isinstance(nested_effect.get('effects'), list):
            prepared['effect'] = copy.deepcopy(nested_effect)
            prepared['effect']['effects'] = normalize_effects(nested_effect['effects'])

        normalized.append(prepared)

    return normalized


def iter_stat_value_pairs(effect: Dict[str, Any]) -> List[tuple[Any, Any]]:
    stats = effect.get('stat')
    values = effect.get('value', 0)
    if isinstance(stats, list):
        if isinstance(values, list):
            return list(zip(stats, values))
        return [(stat, values) for stat in stats]
    return [(stats, values)]

def register_effect_handler(effect_type: str):
    def decorator(func: EffectHandler):
        EFFECT_HANDLERS[effect_type] = func
        return func
    return decorator

def register_condition_checker(condition_key: str):
    def decorator(func: Callable[[Any, Dict[str, Any]], bool or int]):
        CONDITION_HANDLERS[condition_key] = func
        return func
    return decorator

@register_condition_checker("target_is_marked")
def check_target_is_marked(expected_value: bool, context: Dict[str, Any]) -> bool:
    statuses = context.get('target_statuses', [])
    marked = any(s.get('status') == 'the_bulls_eye' for s in statuses)
    return marked == expected_value

@register_condition_checker("status")
def check_status_on_target(status_to_check: str, context: Dict[str, Any]) -> bool:
    statuses = context.get('target_statuses', [])
    return any(s.get('status') == status_to_check for s in statuses)

@register_condition_checker("attacking_specific_target")
def check_attacking_specific_target(target_name: str, context: Dict[str, Any]) -> bool:
    return context.get('enemy_type') == target_name

@register_condition_checker("attacking_protocell")
def check_attacking_protocell(value: bool, context: Dict[str, Any]) -> bool:
    return context.get('enemy_type') == "protocell"

@register_condition_checker("attacking_rosetta")
def check_attacking_rosetta(value: bool, context: Dict[str, Any]) -> bool:
    return context.get('enemy_type') == "rosetta"

@register_condition_checker("hp_above_percent")
def check_hp_above_percent(required_hp: float, context: Dict[str, Any]) -> bool:
    ratio = context.get('player_hp_ratio', 1.0)*100
    return ratio > required_hp

@register_condition_checker("mode")
def check_mode(mode_value: str, context: Dict[str, Any]) -> bool:
    return context.get('current_mode') == mode_value

@register_condition_checker("count")
def check_count(value: int, context: Dict[str, Any]) -> bool:
    event_name = context.get('event_name')
    if event_name:
        mec_ctx = context.get('mechanics_context')
        if mec_ctx:
            current_val = mec_ctx.counters.get(event_name,0)
            return current_val >= value
    return False

@register_condition_checker("extra_ammo_consumed")
def check_extra_ammo_consumed(value: bool, context: Dict[str, Any]) -> bool:
    return context.get('last_extra_ammo_consumed', False) == value

@register_condition_checker("all_projectiles_hit")
def check_all_projectiles_hit(value: bool, context: Dict[str, Any]) -> bool:
    return context.get('all_projectiles_hit', False) == value

@register_condition_checker("ice_crystal_shattered")
def check_ice_crystal_shattered(value: bool, context: Dict[str, Any]) -> bool:
    return context.get('ice_crystal_shattered', False) == value

@register_condition_checker("magazine_capacity_multiple")
def check_magazine_capacity_multiple(value: int, context: Dict[str, Any]) -> int:
    mec_ctx = context.get('mechanics_context')
    if mec_ctx:
        mag_cap = mec_ctx.player.stats.get('magazine_capacity', 0)
        if value > 0:
            return mag_cap // value
    return 0

@register_condition_checker("magazine_capacity_excess")
def check_magazine_capacity_excess(value: int, context: Dict[str, Any]) -> int:
    mec_ctx = context.get('mechanics_context')
    if mec_ctx:
        mag_cap = mec_ctx.player.stats.get('magazine_capacity', 0)
        excess = max(0, mag_cap - 100)
        if value > 0:
            return excess // value
    return 0

def apply_effect(effect: Dict[str, Any], context: Dict[str, Any]):
    eff_type = effect.get('type')
    if not eff_type and 'effect_name' in effect:
        eff_type = effect['effect_name']
    if eff_type in EFFECT_HANDLERS:
        EFFECT_HANDLERS[eff_type](effect, context)
    else:
        logging.warning(f"No handler for effect type: {eff_type}")

def check_conditions(conditions: Dict[str, Any], context: Dict[str, Any]) -> bool:
    for cond_key, expected_value in conditions.items():
        if cond_key in CONDITION_HANDLERS:
            result = CONDITION_HANDLERS[cond_key](expected_value, context)
            if isinstance(result, bool):
                if not result:
                    return False
            elif isinstance(result, int):
                if result <= 0:
                    return False
        else:
            logging.debug(f"No condition handler for {cond_key}, assuming True")
    return True

@register_effect_handler("trigger_ability")
def handle_trigger_ability(effect: Dict[str, Any], context: Dict[str, Any]):
    ability = effect.get('ability')
    ctx = context.get('mechanics_context')
    if ctx and ability:
        ctx.trigger_ability(ability, **effect)

@register_effect_handler("increment_counter")
def handle_increment_counter(effect: Dict[str, Any], context: Dict[str, Any]):
    counter_name = effect.get('counter')
    val = effect.get('value', 1)
    ctx = context.get('mechanics_context')
    if ctx and counter_name:
        ctx.increment_counter(counter_name, val)

@register_effect_handler("increase_stat")
def handle_increase_stat(effect: Dict[str, Any], context: Dict[str, Any]):
    duration = effect.get('duration_seconds', 0)
    max_stacks = effect.get('max_stacks')
    ctx = context.get('mechanics_context')
    source = effect.get('source')
    if not ctx:
        return
    for stat, value in iter_stat_value_pairs(effect):
        if stat:
            ctx.apply_temporary_stat_bonus(stat, value, duration, max_stacks, source=source)

@register_effect_handler("apply_status")
def handle_apply_status(effect: Dict[str, Any], context: Dict[str, Any]):
    status = effect.get('status')
    duration = effect.get('duration_seconds', 0)
    ctx = context.get('mechanics_context')
    if ctx and status:
        nested_effects = effect.get('effects', [])
        if not duration and nested_effects:
            duration_candidates = [nested.get('duration_seconds', 0) for nested in nested_effects if nested.get('duration_seconds')]
            if duration_candidates:
                duration = max(duration_candidates)
        kwargs = {k: v for k, v in effect.items() if k not in ['type', 'status', 'duration_seconds']}
        if 'max_stacks' not in kwargs and nested_effects:
            max_stack_candidates = [nested.get('max_stacks') for nested in nested_effects if nested.get('max_stacks') is not None]
            if max_stack_candidates:
                kwargs['max_stacks'] = max(max_stack_candidates)
        ctx.apply_status(status, duration, **kwargs)

@register_effect_handler("spread_effect")
def handle_spread_effect(effect: Dict[str, Any], context: Dict[str, Any]):
    radius = effect.get('radius_meters', 0)
    nested_effect = effect.get('effect', {})
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.spread_effect(radius, nested_effect)
        eff_type = nested_effect.get('type')
        if eff_type in EFFECT_HANDLERS:
            EFFECT_HANDLERS[eff_type](nested_effect, context)

@register_effect_handler("passive_effect")
def handle_passive_effect(effect: Dict[str, Any], context: Dict[str, Any]):
    properties = effect.get('properties', {})
    conditions = effect.get('conditions', {})
    if not check_conditions(conditions, context):
        return
    ctx = context.get('mechanics_context')
    if ctx:
        for prop, val in properties.items():
            if isinstance(val, (int, float)):
                ctx.apply_temporary_stat_bonus(prop, val, 999999, source=effect.get('effect_name', prop))
            elif isinstance(val, bool):
                ctx.player.stats[prop] = val
            else:
                logging.info(f"Complex property {prop}={val} encountered. Handle later.")
    logging.debug(f"Applied passive_effect {effect.get('effect_name','')}")

@register_effect_handler("modify_chance")
def handle_modify_chance(effect: Dict[str, Any], context: Dict[str, Any]):
    base_event = effect.get('base_event')
    new_chance = effect.get('new_chance_percent', 100)
    ctx = context.get('mechanics_context')
    if ctx and base_event:
        ctx.modify_event_chance(base_event, new_chance)

@register_effect_handler("gain_stack")
def handle_gain_stack(effect: Dict[str, Any], context: Dict[str, Any]):
    stack_type = effect.get('stack_type')
    count = effect.get('count', 1)
    ctx = context.get('mechanics_context')
    if ctx and stack_type:
        ctx.gain_stacks(stack_type, count)

@register_effect_handler("reduce_stack")
def handle_reduce_stack(effect: Dict[str, Any], context: Dict[str, Any]):
    stack_type = effect.get('stack_type')
    value = effect.get('value', 1)
    ctx = context.get('mechanics_context')
    if ctx and stack_type:
        ctx.reduce_stacks(stack_type, value)

@register_effect_handler("reload_ammo")
def handle_reload_ammo(effect: Dict[str, Any], context: Dict[str, Any]):
    amount = effect.get('amount', 1)
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.reload_ammo(amount)

@register_effect_handler("refill_bullet")
def handle_refill_bullet(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.refill_bullet()

@register_effect_handler("restore_bullet")
def handle_restore_bullet(effect: Dict[str, Any], context: Dict[str, Any]):
    amount = effect.get('amount', 1)
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.restore_bullet(amount)

@register_effect_handler("consume_extra_ammo")
def handle_consume_extra_ammo(effect: Dict[str, Any], context: Dict[str, Any]):
    amount = effect.get('amount', 1)
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.consume_extra_ammo(amount)

@register_effect_handler("spawn_pickup")
def handle_spawn_pickup(effect: Dict[str, Any], context: Dict[str, Any]):
    pickup_type = effect.get('pickup_type')
    ctx = context.get('mechanics_context')
    if ctx and pickup_type:
        ctx.spawn_pickup(pickup_type)

@register_effect_handler("modify_ammo")
def handle_modify_ammo(effect: Dict[str, Any], context: Dict[str, Any]):
    ammo_type = effect.get('ammo_type')
    duration_until_reload = effect.get('duration_until_reload', False)
    ctx = context.get('mechanics_context')
    if ctx and ammo_type:
        ctx.modify_ammo_type(ammo_type, duration_until_reload)

@register_effect_handler("consume_charge")
def handle_consume_charge(effect: Dict[str, Any], context: Dict[str, Any]):
    eff_data = effect.get('effect', {})
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.consume_charge(eff_data)

@register_effect_handler("area_damage")
def handle_area_damage(effect: Dict[str, Any], context: Dict[str, Any]):
    damage_percent = effect.get('damage_percent', 0)
    damage_type = effect.get('damage_type', 'unknown')
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.area_damage(damage_percent, damage_type)

@register_effect_handler("modify_trigger_factor")
def handle_modify_trigger_factor(effect: Dict[str, Any], context: Dict[str, Any]):
    ability = effect.get('ability')
    bonus_percent = effect.get('bonus_percent', 0)
    duration_seconds = effect.get('duration_seconds')
    ctx = context.get('mechanics_context')
    if ctx and ability:
        ctx.modify_trigger_factor(ability, bonus_percent, duration_seconds)

@register_effect_handler("conditional_stat_bonus")
def handle_conditional_stat_bonus(effect: Dict[str, Any], context: Dict[str, Any]):
    condition = effect.get('condition')
    increment = effect.get('increment')
    max_stacks = effect.get('max_stacks')
    duration = effect.get('duration_seconds', 0)
    ctx = context.get('mechanics_context')
    if not ctx or not condition:
        return
    if condition in CONDITION_HANDLERS:
        result = CONDITION_HANDLERS[condition](effect.get('value', 0), context)
        if isinstance(result, bool):
            if result:
                for stat, value in iter_stat_value_pairs(effect):
                    val_to_apply = increment if increment is not None else value
                    ctx.apply_temporary_stat_bonus(stat, val_to_apply, duration, max_stacks, source=effect.get('source'))
        elif isinstance(result, int):
            if result > 0:
                for stat, value in iter_stat_value_pairs(effect):
                    val_to_apply = increment if increment is not None else value
                    ctx.apply_temporary_stat_bonus(stat, val_to_apply * result, duration, max_stacks, source=effect.get('source'))


@register_effect_handler("set_duration")
def handle_set_duration(effect: Dict[str, Any], context: Dict[str, Any]):
    return


@register_effect_handler("set_max_stacks")
def handle_set_max_stacks(effect: Dict[str, Any], context: Dict[str, Any]):
    return

@register_effect_handler("generate_ice_crystal")
def handle_generate_ice_crystal(effect: Dict[str, Any], context: Dict[str, Any]):
    cooldown = effect.get('cooldown_seconds', 0)
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.generate_ice_crystal(cooldown)

@register_effect_handler("deal_status_dmg")
def handle_deal_status_dmg(effect: Dict[str, Any], context: Dict[str, Any]):
    damage_formula = effect.get('damage_formula','')
    damage_type = effect.get('damage_type','unknown')
    radius = effect.get('radius_meters',0)
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.deal_status_damage(damage_formula, damage_type, radius)

@register_effect_handler("shatter_ice_crystal")
def handle_shatter_ice_crystal(effect: Dict[str, Any], context: Dict[str, Any]):
    damage_formula = effect.get('damage_formula','')
    damage_type = effect.get('damage_type','unknown')
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.shatter_ice_crystal(damage_formula, damage_type)

@register_effect_handler("grant_infinite_ammo")
def handle_grant_infinite_ammo(effect: Dict[str, Any], context: Dict[str, Any]):
    duration = effect.get('duration_seconds',0)
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.grant_infinite_ammo(duration)

@register_effect_handler("increase_projectiles_per_shot")
def handle_increase_projectiles_per_shot(effect: Dict[str, Any], context: Dict[str, Any]):
    add_proj = effect.get('additional_projectiles',0)
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.increase_projectiles_per_shot(add_proj)

@register_effect_handler("apply_buff")
def handle_apply_buff(effect: Dict[str, Any], context: Dict[str, Any]):
    buff_name = effect.get('buff_name','unnamed_buff')
    duration_bullets = effect.get('duration_bullets')
    stat_bonuses = effect.get('stat_bonuses',{})
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.apply_buff(buff_name, duration_bullets, stat_bonuses)

@register_effect_handler("modify_behavior")
def handle_modify_behavior(effect: Dict[str, Any], context: Dict[str, Any]):
    behavior = effect.get('behavior')
    enabled = effect.get('enabled',True)
    ctx = context.get('mechanics_context')
    if ctx and behavior is not None:
        ctx.modify_behavior(behavior, enabled)

@register_effect_handler("count_as_hits")
def handle_count_as_hits(effect: Dict[str, Any], context: Dict[str, Any]):
    value = effect.get('value',1)
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.increment_counter('hit_count', value)

@register_effect_handler("remove_buff")
def handle_remove_buff(effect: Dict[str, Any], context: Dict[str, Any]):
    buff_type = effect.get('buff_type')
    ctx = context.get('mechanics_context')
    if ctx and buff_type:
        ctx.remove_buff(buff_type)

class Mechanic:
    def __init__(self, description: str, effects: List[Dict[str, Any]]):
        self.description = description
        self.last_trigger_times: Dict[str, float] = {}
        self.events = self.parse_effects(effects)

    def parse_effects(self, effects_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_events = []
        for effect_block in effects_data:
            block_type = effect_block.get('type')
            if block_type == 'on_event':
                counter_event = parse_counter_event(effect_block['event'], effect_block.get('n'))
                parsed_events.append({
                    'type': 'on_event',
                    'event': effect_block['event'],
                    'counter_event': counter_event,
                    'conditions': effect_block.get('conditions', {}),
                    'chance_percent': effect_block.get('chance_percent', 100),
                    'n': effect_block.get('n'),
                    'cooldown_seconds': effect_block.get('cooldown_seconds'),
                    'interval_seconds': effect_block.get('interval_seconds'),
                    'distance_meters': effect_block.get('distance_meters'),
                    'effects': normalize_effects(effect_block.get('effects', []))
                })
            elif block_type == 'passive_effect':
                parsed_events.append({
                    'type': 'passive_effect',
                    'conditions': effect_block.get('conditions', {}),
                    'effects': normalize_effects([effect_block])
                })
            else:
                parsed_events.append({
                    'type': block_type,
                    'conditions': effect_block.get('conditions', {}),
                    'effects': normalize_effects([effect_block])
                })
        return parsed_events

    def apply_passives(self, target, context: Dict[str, Any]):
        for event_block in self.events:
            if event_block['type'] == 'passive_effect':
                if check_conditions(event_block.get('conditions',{}), context):
                    for eff in event_block['effects']:
                        apply_effect(eff, context)

    def trigger_event(self, event_name: str, context: Dict[str, Any]):
        current_time = time.time()
        mec_ctx = context.get('mechanics_context')
        for index, event_block in enumerate(self.events):
            if event_block['type'] != 'on_event':
                continue

            counter_event = event_block.get('counter_event')
            if counter_event:
                if event_name not in counter_event['base_events']:
                    continue
            else:
                if event_name not in get_equivalent_events(event_block['event']):
                    continue

            if not check_conditions(event_block['conditions'], context):
                continue

            cooldown = event_block.get('cooldown_seconds')
            cooldown_key = f"{index}:{event_block['event']}"
            if cooldown:
                last_trigger_time = self.last_trigger_times.get(cooldown_key)
                if last_trigger_time and current_time - last_trigger_time < cooldown:
                    continue

            chance = event_block.get('chance_percent', 100)
            if mec_ctx:
                chance = mec_ctx.event_chance_modifiers.get(event_block['event'], chance)
            if random.uniform(0, 100) > chance:
                continue

            if counter_event:
                if not mec_ctx:
                    continue
                mec_ctx.increment_counter(counter_event['counter_name'])
                if not mec_ctx.check_counter(counter_event['counter_name'], counter_event['required_count']):
                    continue

            for eff in event_block['effects']:
                apply_effect(eff, context)

            if cooldown:
                self.last_trigger_times[cooldown_key] = current_time

def add_stats(stats_dict, new_stats):
    for stat, value in new_stats.items():
        if isinstance(value, dict):
            if stat not in stats_dict:
                stats_dict[stat] = {}
            add_stats(stats_dict[stat], value)
        elif isinstance(value, (int, float)):
            current_value = stats_dict.get(stat, 0)
            stats_dict[stat] = current_value + value

def load_weapon_data() -> List[Dict[str, Any]]:
    # ФОРМИРУЕМ ПОЛНЫЙ ПУТЬ К weapon_list.json
    json_path = os.path.join(CURRENT_DIR, "bd_json", "weapon_list.json")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data['weapons']

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
        star_multipliers = {1:1.0,2:1.1,3:1.2,4:1.3,5:1.4,6:1.5}
        level_multipliers = {1:1.0,2:1.05,3:1.10,4:1.15,5:1.20}
        calibration_bonuses = {0:0.0,1:0.02,2:0.04,3:0.06,4:0.08,5:0.10,6:0.12}
        star_multiplier = star_multipliers.get(self.star,1.0)
        level_multiplier = level_multipliers.get(self.level,1.0)
        calibration_bonus = calibration_bonuses.get(self.calibration,0.0)
        for stat in stats:
            base_value = stats[stat]
            if isinstance(base_value,(int,float)):
                new_value = base_value * star_multiplier * level_multiplier * (1+calibration_bonus)
                if stat in ['projectiles_per_shot','magazine_capacity']:
                    stats[stat]=int(round(new_value))
                else:
                    stats[stat]=new_value
        self.stats=stats
        return stats

    def get_stats(self):
        return self.calculate_stats()

    def trigger_event(self, event_name: str, context=None, **kwargs):
        if self.mechanics:
            if context and hasattr(context, 'build_effect_context'):
                eff_context = context.build_effect_context(event_name=event_name, **kwargs)
            else:
                eff_context = {
                    'mechanics_context': context,
                    'is_crit': kwargs.get('is_crit', False),
                    'is_weakspot': kwargs.get('is_weakspot', False),
                    'target_statuses': context.mannequin_status_effects if context else [],
                    'counters': self.counters,
                    'all_projectiles_hit': getattr(context, 'all_projectiles_hit', False),
                    'last_extra_ammo_consumed': getattr(context, 'last_extra_ammo_consumed', False),
                    'ice_crystal_shattered': getattr(context, 'ice_crystal_shattered', False),
                    'player_hp_ratio': context.get_player_hp_ratio() if context else 1.0,
                    'enemy_type': context.enemy_type if context else 'Обычный',
                    'current_mode': context.current_mode if context else None,
                    'event_name': event_name
                }
            self.mechanics.trigger_event(event_name, eff_context)

class MechanicsProcessor:
    def __init__(self, context=None):
        self.weapons_data = load_weapon_data()
        self.weapons = {data['id']: Weapon(data) for data in self.weapons_data}
        self.context = context
        self.external_mechanics: List[Mechanic] = []

    def set_external_mechanics(self, effect_sources: List[Dict[str, Any]] | None):
        self.external_mechanics = []
        for index, source in enumerate(effect_sources or []):
            effects = source.get('effects', [])
            if any(effect.get('type') == 'on_event' for effect in effects):
                description = source.get('source', f'external_{index}')
                self.external_mechanics.append(Mechanic(description, effects))

    def get_weapon(self, weapon_id: str) -> Weapon:
        return self.weapons.get(weapon_id)

    def process_event(self, event_name: str, **kwargs):
        weapon = self.context.player.weapon if self.context else None
        if weapon:
            weapon.trigger_event(event_name, context=self.context, **kwargs)
        if self.context and hasattr(self.context, 'build_effect_context'):
            eff_context = self.context.build_effect_context(event_name=event_name, **kwargs)
            for mechanic in self.external_mechanics:
                mechanic.trigger_event(event_name, eff_context)

    def process_weapon_event(self, event_name: str, **kwargs):
        self.process_event(event_name, **kwargs)
