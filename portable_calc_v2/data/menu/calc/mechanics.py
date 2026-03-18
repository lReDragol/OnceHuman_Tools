# mechanics.py

import os
import json
import random
import time
import logging
import copy
import re
from typing import Dict, Any, Callable, List

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    'bounce': ['bounce_hit'],
    'shrapnel': ['trigger_shrapnel'],
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
    match = re.match(r'^(\d+)(?:st|nd|rd|th)_(.+)$', event_name)
    if match:
        required_count = int(match.group(1))
        base_name = match.group(2)
        return {
            'counter_name': event_name,
            'required_count': required_count,
            'base_events': resolve_counter_base_events(base_name),
        }
    match = re.match(r'^after_(.+)_triggers_(\d+)_times$', event_name)
    if match:
        base_name = match.group(1)
        required_count = int(match.group(2))
        normalized_base = {
            'power_surge': 'deal_power_surge_damage',
        }.get(base_name, base_name)
        return {
            'counter_name': event_name,
            'required_count': required_count,
            'base_events': resolve_counter_base_events(normalized_base),
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


def iter_nested_effects(effects: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    nested: List[Dict[str, Any]] = []
    for effect in effects or []:
        if not isinstance(effect, dict):
            continue
        nested.append(effect)
        child_effects = effect.get('effects')
        if isinstance(child_effects, list):
            nested.extend(iter_nested_effects(child_effects))
        single_effect = effect.get('effect')
        if isinstance(single_effect, dict):
            nested.append(single_effect)
            if isinstance(single_effect.get('effects'), list):
                nested.extend(iter_nested_effects(single_effect['effects']))
    return nested


TRIGGER_CHANCE_BONUS_STATS = {
    ('ability', 'bounce'): ['bounce_trigger_chance_percent', 'bounce_trigger_factor_percent'],
    ('ability', 'bounce_ricochet'): ['bounce_trigger_chance_percent', 'bounce_trigger_factor_percent'],
    ('ability', 'shrapnel'): ['shrapnel_trigger_chance_percent'],
    ('ability', 'unstable_bomber'): ['unstable_bomber_trigger_chance_percent'],
    ('ability', 'power_surge'): ['shock_trigger_chance_percent'],
    ('ability', 'celestial_thunder'): ['shock_trigger_chance_percent'],
    ('ability', 'burn'): ['burn_trigger_chance_percent'],
    ('ability', 'frost_vortex'): ['frost_vortex_trigger_chance_percent'],
    ('ability', 'fast_gunner'): ['fast_gunner_trigger_chance_percent'],
    ('ability', 'fortress_warfare'): ['fortress_warfare_trigger_chance_percent'],
    ('status', 'the_bulls_eye'): ['the_bulls_eye_trigger_chance_percent'],
    ('status', 'bulls_eye'): ['the_bulls_eye_trigger_chance_percent'],
}


def get_trigger_chance_bonus_for_effects(effects: List[Dict[str, Any]], mec_ctx) -> float:
    if not mec_ctx or not getattr(mec_ctx, 'player', None):
        return 0.0
    stats = getattr(mec_ctx.player, 'stats', {}) or {}
    bonus = 0.0
    seen_stats: set[str] = set()
    for effect in iter_nested_effects(effects):
        targets: list[tuple[str, str]] = []
        effect_type = effect.get('type')
        if effect_type == 'trigger_ability' and effect.get('ability'):
            targets.append(('ability', str(effect['ability']).lower()))
        if effect_type == 'apply_status' and effect.get('status'):
            targets.append(('status', str(effect['status']).lower()))
        for target in targets:
            for stat_name in TRIGGER_CHANCE_BONUS_STATS.get(target, []):
                if stat_name in seen_stats:
                    continue
                bonus += float(stats.get(stat_name, 0) or 0)
                seen_stats.add(stat_name)
    return bonus


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

@register_condition_checker("has_flag")
def check_has_flag(flag_name: str, context: Dict[str, Any]) -> bool:
    temporary_flags = context.get('temporary_flags', {}) or {}
    return bool(temporary_flags.get(flag_name))

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

def scale_runtime_effect(effect: Dict[str, Any], stacks: int) -> Dict[str, Any]:
    scaled_effect = copy.deepcopy(effect)
    value = scaled_effect.get('value')
    max_value = scaled_effect.get('max_value')
    if isinstance(value, list):
        scaled_values = [entry * stacks if isinstance(entry, (int, float)) else entry for entry in value]
        if isinstance(max_value, (int, float)):
            scaled_values = [
                max(-max_value, min(max_value, entry)) if isinstance(entry, (int, float)) else entry
                for entry in scaled_values
            ]
        scaled_effect['value'] = scaled_values
    elif isinstance(value, (int, float)):
        scaled_value = value * stacks
        if isinstance(max_value, (int, float)):
            scaled_value = max(-max_value, min(max_value, scaled_value))
        scaled_effect['value'] = scaled_value
    return scaled_effect

def apply_nested_runtime_effects(
    effect: Dict[str, Any],
    context: Dict[str, Any],
    stacks: int = 1,
    active_status: str | None = None,
    skip_types: set[str] | None = None,
):
    for nested_effect in normalize_effects(effect.get('effects', [])):
        if skip_types and nested_effect.get('type') in skip_types:
            continue
        prepared_effect = scale_runtime_effect(nested_effect, stacks) if stacks != 1 else copy.deepcopy(nested_effect)
        if active_status and prepared_effect.get('_active_status') is None:
            prepared_effect['_active_status'] = active_status
        apply_effect(prepared_effect, context)

@register_effect_handler("trigger_ability")
def handle_trigger_ability(effect: Dict[str, Any], context: Dict[str, Any]):
    ability = effect.get('ability')
    ctx = context.get('mechanics_context')
    if ctx and ability:
        payload = dict(effect)
        payload.pop('ability', None)
        ctx.trigger_ability(ability, **payload)

@register_effect_handler("increment_counter")
def handle_increment_counter(effect: Dict[str, Any], context: Dict[str, Any]):
    counter_name = effect.get('counter')
    val = effect.get('value', 1)
    ctx = context.get('mechanics_context')
    if ctx and counter_name:
        ctx.increment_counter(counter_name, val)

@register_effect_handler("increase_stat")
def handle_increase_stat(effect: Dict[str, Any], context: Dict[str, Any]):
    duration = effect.get('duration_seconds')
    max_stacks = effect.get('max_stacks')
    max_value = effect.get('max_value')
    ctx = context.get('mechanics_context')
    source = effect.get('source') or context.get('effect_group_source')
    sibling_effects = context.get('effect_group_effects', [])
    has_reset_pair = any(entry.get('type') == 'reset_on_event' for entry in sibling_effects)
    if not ctx:
        return
    for stat, value in iter_stat_value_pairs(effect):
        if not stat:
            continue
        resolved_value = value
        resolved_source = source or stat
        if max_value is not None and hasattr(ctx.player, 'get_source_bonus_total'):
            current_total = ctx.player.get_source_bonus_total(stat, resolved_source)
            if resolved_value >= 0:
                resolved_value = min(resolved_value, max(0.0, float(max_value) - current_total))
            else:
                resolved_value = max(resolved_value, min(0.0, -float(max_value) - current_total))
            if abs(resolved_value) < 1e-9:
                continue

        effective_duration = duration if duration is not None else 0
        effective_max_stacks = max_stacks
        if effective_duration <= 0:
            if max_value is not None or effective_max_stacks is not None or has_reset_pair:
                effective_duration = 999999
            else:
                effective_duration = ctx.get_event_refresh_duration() if hasattr(ctx, 'get_event_refresh_duration') else 1.0
                effective_max_stacks = 1
        ctx.apply_temporary_stat_bonus(stat, resolved_value, effective_duration, effective_max_stacks, source=resolved_source)

@register_effect_handler("decrease_stat")
def handle_decrease_stat(effect: Dict[str, Any], context: Dict[str, Any]):
    prepared = copy.deepcopy(effect)
    value = prepared.get('value', 0)
    if isinstance(value, list):
        prepared['value'] = [(-entry if isinstance(entry, (int, float)) else entry) for entry in value]
    elif isinstance(value, (int, float)):
        prepared['value'] = -value
    handle_increase_stat(prepared, context)


@register_effect_handler("set_flag")
def handle_set_flag(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if not ctx or not hasattr(ctx, 'set_temporary_flag'):
        return
    flags = effect.get('flag')
    values = effect.get('value')
    duration = effect.get('duration_seconds')
    source = context.get('effect_source_key') or context.get('effect_group_source')
    if isinstance(flags, list):
        if not isinstance(values, list):
            values = [values] * len(flags)
        for flag, flag_value in zip(flags, values):
            ctx.set_temporary_flag(flag, flag_value, duration_seconds=duration, source=source)
    elif flags:
        ctx.set_temporary_flag(flags, values, duration_seconds=duration, source=source)

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

@register_effect_handler("reduce_stack_percent")
def handle_reduce_stack_percent(effect: Dict[str, Any], context: Dict[str, Any]):
    stack_type = effect.get('stack_type')
    value = effect.get('value', 0)
    ctx = context.get('mechanics_context')
    if ctx and stack_type:
        ctx.reduce_stacks_percent(stack_type, value)

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

@register_effect_handler("refill_magazine_percent")
def handle_refill_magazine_percent(effect: Dict[str, Any], context: Dict[str, Any]):
    value = effect.get('value', effect.get('percent', 0))
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.refill_magazine_percent(value)

@register_effect_handler("refill_bullets_from_inventory")
@register_effect_handler("refill_bullet_from_inventory")
def handle_refill_bullets_from_inventory(effect: Dict[str, Any], context: Dict[str, Any]):
    amount = effect.get('value', effect.get('amount', 1))
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.restore_bullet(amount)

@register_effect_handler("recover_hp_percent")
@register_effect_handler("restore_hp_percent")
def handle_restore_hp_percent(effect: Dict[str, Any], context: Dict[str, Any]):
    value = effect.get('value', 0)
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.restore_hp_percent(value)

@register_effect_handler("apply_shield")
def handle_apply_shield(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.apply_shield(
            percent_of_max_hp=effect.get('percent_of_max_hp'),
            flat_value=effect.get('value'),
            duration_seconds=effect.get('duration_seconds', 0),
            max_percent=effect.get('max_shield_percent'),
        )

@register_effect_handler("remove_stacks")
def handle_remove_stacks(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if not ctx:
        return
    stack_type = effect.get('stack_type') or effect.get('status')
    stacks = effect.get('stacks', effect.get('value', 0))
    if stack_type:
        ctx.reduce_stacks(stack_type, stacks)

@register_effect_handler("reduce_burn_stacks_percent")
def handle_reduce_burn_stacks_percent(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.reduce_status_stacks_percent('burn', effect.get('value', 0))

@register_effect_handler("trigger_status")
def handle_trigger_status(effect: Dict[str, Any], context: Dict[str, Any]):
    status = effect.get('status')
    duration = effect.get('duration_seconds', 0)
    chance = effect.get('chance_percent', 100)
    ctx = context.get('mechanics_context')
    if ctx and status and random.uniform(0, 100) <= chance:
        ctx.apply_status(status, duration)

@register_effect_handler("apply_status_to_nearby_enemies")
@register_effect_handler("spread_status_to_nearby_enemies")
def handle_apply_status_to_nearby_enemies(effect: Dict[str, Any], context: Dict[str, Any]):
    status = effect.get('status')
    duration = effect.get('duration_seconds', 0)
    ctx = context.get('mechanics_context')
    if ctx and status:
        kwargs = {k: v for k, v in effect.items() if k not in {'type', 'status', 'duration_seconds'}}
        ctx.apply_status(status, duration, **kwargs)

@register_effect_handler("increase_duration")
@register_effect_handler("extend_effect_duration")
@register_effect_handler("status_remains")
def handle_extend_status_duration(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if not ctx:
        return
    duration = effect.get('duration_seconds', 0)
    status = effect.get('status')
    if status:
        ctx.extend_status_duration(status, duration)
    elif ctx.current_mode:
        ctx.extend_mode_duration(ctx.current_mode, duration)


@register_effect_handler("more_targets_hit")
def handle_more_targets_hit(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if not ctx:
        return
    target_count = max(0, int(round(ctx.player.stats.get('bounce_targets', 0))))
    if target_count <= 0:
        return
    for nested_effect in normalize_effects(effect.get('effects', [])):
        scaled_effect = copy.deepcopy(nested_effect)
        value = scaled_effect.get('value')
        if isinstance(value, (int, float)):
            scaled_effect['value'] = min(float(value), target_count * 15.0)
        apply_effect(scaled_effect, context)

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


@register_effect_handler("aoe")
def handle_aoe(effect: Dict[str, Any], context: Dict[str, Any]):
    return


@register_effect_handler("deal_ice_damage")
def handle_deal_ice_damage(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if not ctx:
        return
    percent = float(effect.get('percent_of_psi_intensity', 0) or 0)
    if percent <= 0:
        return
    damage_formula = {'type': 'psi_intensity', 'multiplier': percent / 100.0}
    radius = effect.get('radius_meters', 0) or 0
    ctx.deal_status_damage(damage_formula, 'frost', radius)


@register_effect_handler("summon")
def handle_summon(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if not ctx:
        return
    entity = effect.get('entity')
    if not entity:
        return
    multiplier = float(effect.get('damage_percent_of_psi_intensity', 0) or 0) / 100.0
    damage_formula = {'type': 'psi_intensity', 'multiplier': multiplier} if multiplier else effect.get('damage_formula')
    ctx.trigger_ability(entity, damage_formula=damage_formula or {'type': 'psi_intensity', 'multiplier': 1.0})


@register_effect_handler("per_hits_taken")
def handle_per_hits_taken(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if not ctx:
        return
    hits_required = max(int(effect.get('hits_required', 1) or 1), 1)
    stacks = int(getattr(ctx, 'hits_taken_count', 0) // hits_required)
    if stacks <= 0:
        return
    for nested_effect in normalize_effects(effect.get('effects', [])):
        scaled_effect = copy.deepcopy(nested_effect)
        value = scaled_effect.get('value')
        max_value = scaled_effect.get('max_value')
        if isinstance(value, (int, float)):
            scaled_value = value * stacks
            if max_value is not None:
                scaled_value = max(-float(max_value), min(float(max_value), scaled_value))
            scaled_effect['value'] = scaled_value
        apply_effect(scaled_effect, context)

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

@register_effect_handler("conditional_effect")
def handle_conditional_effect(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    condition = effect.get('condition')
    if not ctx or not condition:
        return
    if hasattr(ctx.player, 'evaluate_condition') and ctx.player.evaluate_condition(condition, ctx):
        apply_nested_runtime_effects(effect, context)

@register_effect_handler("modify_skill")
def handle_modify_skill(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    skill_name = str(effect.get('skill') or '').lower()
    if not ctx or not skill_name:
        return
    is_active = ctx.is_status_active(skill_name) or ctx.current_mode == skill_name
    if skill_name == 'the_bulls_eye':
        is_active = is_active or ctx.is_status_active('bulls_eye')
    if is_active:
        apply_nested_runtime_effects(effect, context)

@register_effect_handler("frost_vortex_applies")
def handle_frost_vortex_applies(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if not ctx:
        return
    if ctx.is_status_active('frostbite') or ctx.is_status_active('frost_vortex'):
        apply_nested_runtime_effects(effect, context, skip_types={'apply_status'})

@register_effect_handler("out_of_combat")
def handle_out_of_combat(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if not ctx or not ctx.is_out_of_combat():
        return
    elapsed = ctx.get_out_of_combat_time()
    for nested_effect in normalize_effects(effect.get('effects', [])):
        if nested_effect.get('type') == 'gain_stack' and nested_effect.get('effects'):
            every_seconds = max(float(nested_effect.get('every_seconds', 1) or 1), 1.0)
            max_stacks = nested_effect.get('max_stacks')
            stacks = int(elapsed // every_seconds)
            if max_stacks is not None:
                stacks = min(stacks, int(max_stacks))
            if stacks > 0:
                apply_nested_runtime_effects(nested_effect, context, stacks=stacks)
        else:
            apply_effect(copy.deepcopy(nested_effect), context)

@register_effect_handler("while_active")
def handle_while_active(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    active_status = effect.get('status')
    if ctx and active_status and ctx.is_status_active(active_status):
        apply_nested_runtime_effects(effect, context, active_status=active_status)

@register_effect_handler("per_stack")
def handle_per_stack(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if not ctx:
        return
    stacks = ctx.get_stack_count(effect.get('stack_source'))
    if stacks > 0:
        apply_nested_runtime_effects(effect, context, stacks=stacks)

@register_effect_handler("per_hp_loss")
def handle_per_hp_loss(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if not ctx:
        return
    every_percent = max(float(effect.get('every_percent', 0) or 0), 1.0)
    hp_lost_percent = max(0.0, 100.0 - ctx.get_player_hp_ratio() * 100.0)
    stacks = int(hp_lost_percent // every_percent)
    if stacks > 0:
        apply_nested_runtime_effects(effect, context, stacks=stacks)

@register_effect_handler("per_meter")
def handle_per_meter(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if not ctx:
        return
    distance_over_threshold = max(0, int(math.floor(getattr(ctx, 'target_distance', 0) - 20)))
    if distance_over_threshold > 0:
        apply_nested_runtime_effects(effect, context, stacks=distance_over_threshold)

@register_effect_handler("per_bullets_consumed")
def handle_per_bullets_consumed(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if not ctx:
        return
    bullets = max(int(effect.get('bullets', 0) or 0), 1)
    stacks = int(getattr(ctx, 'magazine_bullets_fired', 0) // bullets)
    if stacks > 0:
        apply_nested_runtime_effects(effect, context, stacks=stacks)

@register_effect_handler("per_player_in_fortress")
def handle_per_player_in_fortress(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if not ctx:
        return
    players_in_fortress = max(1, int(getattr(ctx, 'players_in_fortress', 1)))
    apply_nested_runtime_effects(effect, context, stacks=players_in_fortress)

@register_effect_handler("per_weakspot_hit_rate")
def handle_per_weakspot_hit_rate(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if not ctx:
        return
    every_percent = max(float(effect.get('every_percent', 0) or 0), 1.0)
    stacks = int(getattr(ctx, 'last_magazine_weakspot_rate', 0.0) // every_percent)
    if stacks > 0:
        apply_nested_runtime_effects(effect, context, stacks=stacks)

@register_effect_handler("per_stat")
def handle_per_stat(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if not ctx:
        return
    stat_name = effect.get('stat')
    step = max(float(effect.get('value', 0) or 0), 1.0)
    stat_value = float(ctx.player.stats.get(stat_name, 0) or 0)
    stacks = int(stat_value // step)
    if stacks > 0:
        apply_nested_runtime_effects(effect, context, stacks=stacks)


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
    shots = effect.get('shots')
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.grant_infinite_ammo(duration, shots=shots)

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
    duration_seconds = effect.get('duration_seconds')
    max_stacks = effect.get('max_stacks')
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.apply_buff(
            buff_name,
            duration_bullets=duration_bullets,
            stat_bonuses=stat_bonuses,
            duration_seconds=duration_seconds,
            max_stacks=max_stacks,
        )

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

@register_effect_handler("increment_hit_count")
def handle_increment_hit_count(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.increment_hit_count(effect.get('value', 1))


@register_effect_handler("gain_buff")
def handle_gain_buff(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if not ctx:
        return
    buff_name = effect.get('buff_type') or effect.get('buff_name') or 'stacking_buff'
    stat_bonuses = {}
    alias_map = {
        'attack_increase_percent': 'weapon_damage_percent',
        'attack_percent': 'weapon_damage_percent',
        'weapon_dmg_increase_percent': 'weapon_damage_percent',
        'weakspot_dmg_increase_percent': 'weakspot_damage_percent',
        'weakspot_damage_increase_percent': 'weakspot_damage_percent',
        'crit_rate_increase_percent': 'crit_rate_percent',
        'crit_dmg_increase_percent': 'crit_damage_percent',
        'damage_reduction_increase_percent': 'damage_reduction_percent',
    }
    for key, stat_name in alias_map.items():
        if key in effect:
            stat_bonuses[stat_name] = effect[key]
    ctx.apply_buff(
        buff_name,
        duration_bullets=effect.get('duration_bullets'),
        stat_bonuses=stat_bonuses,
        duration_seconds=effect.get('duration_seconds'),
        max_stacks=effect.get('max_stacks'),
        source=context.get('effect_group_source'),
    )


@register_effect_handler("increase_stat_over_time")
def handle_increase_stat_over_time(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if not ctx:
        return
    stat_name = effect.get('stat')
    active_status = effect.get('_active_status') or effect.get('status') or ctx.current_mode
    active_seconds = ctx.get_status_uptime(active_status)
    if not stat_name or active_seconds <= 0:
        return
    value = active_seconds * float(effect.get('value_per_second', 0))
    max_value = effect.get('max_value')
    if max_value is not None:
        value = min(float(max_value), value)
    if value:
        ctx.apply_temporary_stat_bonus(stat_name, value, ctx.get_event_refresh_duration(), 1, source=context.get('effect_group_source'))


@register_effect_handler("restore_stamina_percent")
@register_effect_handler("recover_stamina_percent")
def handle_restore_stamina_percent(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if ctx:
        ctx.restore_stamina_percent(effect.get('value', 0))


@register_effect_handler("reset_on_event")
def handle_reset_on_event(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    event_name = effect.get('event')
    source = context.get('effect_group_source')
    if ctx and event_name and source:
        ctx.register_reset_source(event_name, source)


@register_effect_handler("set_cooldown")
def handle_set_cooldown(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    source = context.get('effect_group_source')
    if ctx and source and hasattr(ctx, 'set_effect_cooldown'):
        ctx.set_effect_cooldown(source, effect.get('cooldown_seconds', 0))


@register_effect_handler("special_effect")
def handle_special_effect(effect: Dict[str, Any], context: Dict[str, Any]):
    ctx = context.get('mechanics_context')
    if ctx and hasattr(ctx, 'apply_special_effect'):
        ctx.apply_special_effect(effect)


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
                counter_hint = effect_block.get('n')
                if counter_hint is None:
                    counter_hint = effect_block.get('kills_required')
                counter_event = parse_counter_event(effect_block['event'], counter_hint)
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

            distance_limit = event_block.get('distance_meters')
            if distance_limit is not None and mec_ctx and getattr(mec_ctx, 'target_distance', 0) > float(distance_limit):
                continue

            if not check_conditions(event_block['conditions'], context):
                continue

            cooldown_key = f"{index}:{event_block['event']}"
            cooldown = event_block.get('cooldown_seconds')
            interval = event_block.get('interval_seconds')
            last_trigger_time = self.last_trigger_times.get(cooldown_key)
            if cooldown and last_trigger_time and current_time - last_trigger_time < cooldown:
                continue
            if interval and last_trigger_time and current_time - last_trigger_time < interval:
                continue

            chance = event_block.get('chance_percent', 100)
            if mec_ctx:
                chance = mec_ctx.event_chance_modifiers.get(event_block['event'], chance)
                chance += get_trigger_chance_bonus_for_effects(event_block['effects'], mec_ctx)
            chance = max(0.0, min(100.0, float(chance)))
            if random.uniform(0, 100) > chance:
                continue

            if counter_event:
                if not mec_ctx:
                    continue
                mec_ctx.increment_counter(counter_event['counter_name'])
                if not mec_ctx.check_counter(counter_event['counter_name'], counter_event['required_count']):
                    continue

            effect_group_source = f"{self.description}:{index}:{event_block['event']}"
            for eff_index, eff in enumerate(event_block['effects']):
                eff_context = dict(context)
                eff_context['effect_group_source'] = effect_group_source
                eff_context['effect_source_key'] = f"{effect_group_source}:{eff_index}"
                eff_context['effect_group_effects'] = event_block['effects']
                apply_effect(eff, eff_context)

            if cooldown or interval:
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
    PROGRESSION_SCALING_STATS = {'damage_per_projectile'}

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
        self.equipped_attachments: Dict[str, Dict[str, Any]] = {}
        if isinstance(self.mechanics_data, dict) and 'description' in self.mechanics_data and 'effects' in self.mechanics_data:
            self.mechanics = Mechanic(self.mechanics_data['description'], self.mechanics_data['effects'])
        else:
            self.mechanics = None

    def equip_attachment(self, slot: str, attachment_data: Dict[str, Any]):
        if not slot or not attachment_data:
            return
        self.equipped_attachments[slot] = copy.deepcopy(attachment_data)

    def remove_attachment(self, slot: str):
        if slot in self.equipped_attachments:
            del self.equipped_attachments[slot]

    def clear_attachments(self):
        self.equipped_attachments.clear()

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
                if stat in self.PROGRESSION_SCALING_STATS:
                    new_value = base_value * star_multiplier * level_multiplier * (1 + calibration_bonus)
                else:
                    new_value = base_value
                if stat in ['projectiles_per_shot', 'magazine_capacity']:
                    stats[stat]=int(round(new_value))
                else:
                    stats[stat]=new_value
        for attachment in self.equipped_attachments.values():
            attachment_stats = attachment.get('stats', {})
            add_stats(stats, attachment_stats)
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
