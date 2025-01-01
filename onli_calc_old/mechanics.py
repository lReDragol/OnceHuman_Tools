# mechanics.py

import json
import random
import time
import logging
from typing import Dict, Any, Callable, List

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

EffectHandler = Callable[[Dict[str, Any], Dict[str, Any]], None]
CONDITION_HANDLERS: Dict[str, Callable[[Any, Dict[str, Any]], bool or int]] = {}
EFFECT_HANDLERS: Dict[str, EffectHandler] = {}

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
            return mag_cap // value  # целочисленное деление, сколько раз помещается
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
                # Если условие возвращает число, >0 значит условие истинно
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
    stat = effect.get('stat')
    value = effect.get('value', 0)
    duration = effect.get('duration_seconds', 0)
    max_stacks = effect.get('max_stacks')
    ctx = context.get('mechanics_context')
    if ctx and stat:
        ctx.apply_temporary_stat_bonus(stat, value, duration, max_stacks)

@register_effect_handler("apply_status")
def handle_apply_status(effect: Dict[str, Any], context: Dict[str, Any]):
    status = effect.get('status')
    duration = effect.get('duration_seconds', 0)
    ctx = context.get('mechanics_context')
    if ctx and status:
        kwargs = {k:v for k,v in effect.items() if k not in ['type','status','duration_seconds']}
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
                ctx.apply_temporary_stat_bonus(prop, val, 999999)
            else:
                # сложные свойства просто логируем
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
    stat = effect.get('stat')
    value = effect.get('value', 0)
    increment = effect.get('increment')
    max_stacks = effect.get('max_stacks')
    duration = effect.get('duration_seconds', 0)
    ctx = context.get('mechanics_context')
    if not ctx or not stat or not condition:
        return
    if condition in CONDITION_HANDLERS:
        result = CONDITION_HANDLERS[condition](value, context)
        # result может быть bool или int
        if isinstance(result, bool):
            if result:
                # Просто один раз применяем
                val_to_apply = increment if increment else value
                ctx.apply_temporary_stat_bonus(stat, val_to_apply, duration, max_stacks)
        elif isinstance(result, int):
            # Применяем increment или value result раз
            if result > 0:
                val_to_apply = increment if increment else value
                # Применяем bonus result раз
                # Можно применить result * val_to_apply сразу
                ctx.apply_temporary_stat_bonus(stat, val_to_apply * result, duration, max_stacks)

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
        # increment_counter('hit_count', value-1) как раньше, но возможно лучше просто value раз
        # Предположим, count_as_hits добавляет дополнительные хиты
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
        self.events = self.parse_effects(effects)

    def parse_effects(self, effects_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_events = []
        for effect_block in effects_data:
            block_type = effect_block.get('type')
            if block_type == 'on_event':
                parsed_events.append({
                    'type': 'on_event',
                    'event': effect_block['event'],
                    'conditions': effect_block.get('conditions', {}),
                    'chance_percent': effect_block.get('chance_percent', 100),
                    'n': effect_block.get('n'),
                    'cooldown_seconds': effect_block.get('cooldown_seconds'),
                    'interval_seconds': effect_block.get('interval_seconds'),
                    'distance_meters': effect_block.get('distance_meters'),
                    'effects': effect_block.get('effects', [])
                })
            elif block_type == 'passive_effect':
                parsed_events.append({
                    'type': 'passive_effect',
                    'conditions': effect_block.get('conditions', {}),
                    'effects': [effect_block]
                })
            else:
                parsed_events.append({
                    'type': block_type,
                    'conditions': effect_block.get('conditions', {}),
                    'effects': [effect_block]
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
        for event_block in self.events:
            if event_block['type'] == 'on_event' and event_block['event'] == event_name:
                if not check_conditions(event_block['conditions'], context):
                    continue
                cooldown = event_block.get('cooldown_seconds')
                last_trigger_time_key = f"last_trigger_time_{event_name}"
                if cooldown and context.get(last_trigger_time_key):
                    if current_time - context[last_trigger_time_key] < cooldown:
                        continue
                chance = event_block.get('chance_percent', 100)
                if random.uniform(0,100)<=chance:
                    n = event_block.get('n')
                    if (event_name.startswith('every_n_') or event_name.endswith('_n_times')) and n is not None:
                        mec_ctx = context.get('mechanics_context')
                        if mec_ctx and mec_ctx.check_counter(event_name, n):
                            for eff in event_block['effects']:
                                apply_effect(eff, context)
                            if cooldown:
                                context[last_trigger_time_key] = current_time
                    else:
                        # Обычное событие
                        for eff in event_block['effects']:
                            apply_effect(eff, context)
                        if cooldown:
                            context[last_trigger_time_key] = current_time

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
    with open('weapon_list.json', 'r', encoding='utf-8') as f:
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
            eff_context = {
                'mechanics_context': context,
                'is_crit': kwargs.get('is_crit',False),
                'is_weakspot': kwargs.get('is_weakspot',False),
                'target_statuses': context.mannequin_status_effects if context else [],
                'counters': self.counters,
                'all_projectiles_hit': getattr(context,'all_projectiles_hit',False),
                'last_extra_ammo_consumed': getattr(context,'last_extra_ammo_consumed',False),
                'ice_crystal_shattered': getattr(context,'ice_crystal_shattered',False),
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

    def get_weapon(self, weapon_id: str) -> Weapon:
        return self.weapons.get(weapon_id)

    def process_weapon_event(self, event_name: str, **kwargs):
        weapon = self.context.player.weapon if self.context else None
        if weapon:
            weapon.trigger_event(event_name, context=self.context, **kwargs)
