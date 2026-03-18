#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import marshal
import re
import struct
from pathlib import Path

TIER_RE = re.compile(r'^(?P<name>.+?)#7#(?:\+)?\{1\}%?#7#_\$S@TIDS\$_cih\|(?P<tier>[0-9a-z]+)$')
LEVEL_RE = re.compile(r'^(?P<name>.+?)_\$S@TIDS\$_cin\|(?P<tier>[0-9a-z]+)$')
NUMERIC_RE = re.compile(r'^[0-9]+(?:\.[0-9]+)?$')
CIH_NAME_RE = re.compile(r'^(?P<name>.+?)_\$S@TIDS\$_cih\|(?P<tier>[0-9a-z]+)$')

SUPPORTED_ATTRIBUTE_CONFIG = {
    '暴击率': {
        'id': 'crit_rate',
        'profile': 'crit_rate',
        'effect': {'type': 'increase_stat', 'stat': 'crit_rate_percent'},
        'display_name': {'ru': 'Шанс крита', 'en': 'Critical rate'},
    },
    '暴击伤害': {
        'id': 'crit_damage',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'crit_damage_percent'},
        'display_name': {'ru': 'Крит. урон', 'en': 'Critical damage'},
    },
    '弱点伤害': {
        'id': 'weakspot_damage',
        'profile': 'ultra_damage',
        'effect': {'type': 'increase_stat', 'stat': 'weakspot_damage_percent'},
        'display_name': {'ru': 'Урон по слабым местам', 'en': 'Weakspot damage'},
    },
    '枪械伤害': {
        'id': 'weapon_damage',
        'profile': 'ultra_damage',
        'effect': {'type': 'increase_stat', 'stat': 'weapon_damage_percent'},
        'display_name': {'ru': 'Урон оружия', 'en': 'Weapon damage'},
    },
    '异常伤害': {
        'id': 'status_damage',
        'profile': 'status_damage',
        'effect': {'type': 'increase_stat', 'stat': 'status_damage_percent'},
        'display_name': {'ru': 'Урон статуса', 'en': 'Status damage'},
    },
    '元素（炽能、霜寒、电离、爆炸）伤害': {
        'id': 'elemental_damage',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'elemental_damage_percent'},
        'display_name': {'ru': 'Элементальный урон', 'en': 'Elemental damage'},
    },
    '弹匣容量': {
        'id': 'magazine_capacity',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'magazine_capacity_percent'},
        'display_name': {'ru': 'Ёмкость магазина', 'en': 'Magazine capacity'},
    },
    '换弹速度': {
        'id': 'reload_speed',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'reload_speed_percent'},
        'display_name': {'ru': 'Скорость перезарядки', 'en': 'Reload speed'},
    },
    '换弹效率': {
        'id': 'reload_efficiency',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'reload_speed_percent'},
        'display_name': {'ru': 'Эффективность перезарядки', 'en': 'Reload efficiency'},
    },
    '最大生命值': {
        'id': 'max_hp_percent',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'hp_percent_bonus'},
        'display_name': {'ru': 'Макс. HP', 'en': 'Max HP'},
    },
    '生命百分比': {
        'id': 'hp_percent',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'hp_percent_bonus'},
        'display_name': {'ru': 'HP%', 'en': 'HP%'},
    },
    '超感强度': {
        'id': 'psi_intensity_percent',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'psi_intensity_percent_bonus'},
        'display_name': {'ru': 'PSI-интенсивность', 'en': 'PSI intensity'},
    },
    '灼烧伤害': {
        'id': 'burn_damage',
        'profile': 'status_damage',
        'effect': {'type': 'increase_stat', 'stat': 'burn_damage_percent'},
        'display_name': {'ru': 'Урон горения', 'en': 'Burn damage'},
    },
    '灼烧触发时间': {
        'id': 'burn_duration',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'burn_duration_percent'},
        'display_name': {'ru': 'Длительность горения', 'en': 'Burn duration'},
    },
    '电涌伤害': {
        'id': 'shock_damage',
        'profile': 'status_damage',
        'effect': {'type': 'increase_stat', 'stat': 'shock_damage_percent'},
        'display_name': {'ru': 'Урон шока', 'en': 'Shock damage'},
    },
    '冰霜漩涡伤害': {
        'id': 'frost_vortex_damage',
        'profile': 'status_damage',
        'effect': {'type': 'increase_stat', 'stat': 'frost_vortex_damage_percent'},
        'display_name': {'ru': 'Урон Frost Vortex', 'en': 'Frost Vortex damage'},
    },
    '冰霜漩涡持续时间': {
        'id': 'frost_vortex_duration',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'frost_vortex_duration_percent'},
        'display_name': {'ru': 'Длительность Frost Vortex', 'en': 'Frost Vortex duration'},
    },
    '不稳定爆弹伤害': {
        'id': 'unstable_bomber_damage',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'unstable_bomber_damage_percent'},
        'display_name': {'ru': 'Урон Unstable Bomber', 'en': 'Unstable Bomber damage'},
    },
    '不稳定爆弹暴击伤害': {
        'id': 'unstable_bomber_crit_damage',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'unstable_bomber_crit_damage_percent'},
        'display_name': {'ru': 'Крит. урон Unstable Bomber', 'en': 'Unstable Bomber crit damage'},
    },
    '不稳定爆弹触发概率': {
        'id': 'unstable_bomber_trigger_chance',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'unstable_bomber_trigger_chance_percent'},
        'display_name': {'ru': 'Шанс Unstable Bomber', 'en': 'Unstable Bomber chance'},
    },
    '不稳定爆弹触发范围': {
        'id': 'unstable_bomber_range',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'unstable_bomber_range_percent'},
        'display_name': {'ru': 'Радиус Unstable Bomber', 'en': 'Unstable Bomber range'},
    },
    '碎弹伤害': {
        'id': 'shrapnel_damage',
        'profile': 'status_damage',
        'effect': {'type': 'increase_stat', 'stat': 'shrapnel_damage_percent'},
        'display_name': {'ru': 'Урон Shrapnel', 'en': 'Shrapnel damage'},
    },
    '碎弹触发概率': {
        'id': 'shrapnel_trigger_chance',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'shrapnel_trigger_chance_percent'},
        'display_name': {'ru': 'Шанс Shrapnel', 'en': 'Shrapnel chance'},
    },
    '碎弹暴击伤害': {
        'id': 'shrapnel_crit_damage',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'shrapnel_crit_damage_percent'},
        'display_name': {'ru': 'Крит. урон Shrapnel', 'en': 'Shrapnel crit damage'},
    },
    '碎弹弱点伤害': {
        'id': 'shrapnel_weakspot_damage',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'shrapnel_weakspot_damage_percent'},
        'display_name': {'ru': 'Урон Shrapnel по weakspot', 'en': 'Shrapnel weakspot damage'},
    },
    '快枪手持续时间': {
        'id': 'fast_gunner_duration',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'fast_gunner_duration_percent'},
        'display_name': {'ru': 'Длительность Fast Gunner', 'en': 'Fast Gunner duration'},
    },
    '重装阵地时间': {
        'id': 'fortress_duration',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'fortress_warfare_duration_percent'},
        'display_name': {'ru': 'Длительность Fortress Warfare', 'en': 'Fortress Warfare duration'},
    },
    '重装阵地内伤害': {
        'id': 'fortress_damage',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'weapon_damage_percent'},
        'display_name': {'ru': 'Урон в Fortress Warfare', 'en': 'Fortress Warfare damage'},
    },
    '重装阵地触发概率': {
        'id': 'fortress_trigger_chance',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'fortress_warfare_trigger_chance_percent'},
        'display_name': {'ru': 'Шанс Fortress Warfare', 'en': 'Fortress Warfare chance'},
    },
    '范围效果（冰霜漩涡、不稳定爆弹、重装阵地）范围': {
        'id': 'aoe_range',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'fortress_warfare_range_percent'},
        'display_name': {'ru': 'Радиус зональных эффектов', 'en': 'Area effect range'},
    },
    '对普通敌人伤害': {
        'id': 'damage_vs_normal',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'damage_bonus_normal'},
        'display_name': {'ru': 'Урон по обычным врагам', 'en': 'Damage vs normal enemies'},
    },
    '对精英敌人伤害': {
        'id': 'damage_vs_elite',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'damage_bonus_elite'},
        'display_name': {'ru': 'Урон по элитным врагам', 'en': 'Damage vs elite enemies'},
    },
    '对上位者伤害': {
        'id': 'damage_vs_boss',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'damage_bonus_boss'},
        'display_name': {'ru': 'Урон по боссам', 'en': 'Damage vs bosses'},
    },
    '射程': {
        'id': 'range_bonus',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'range'},
        'display_name': {'ru': 'Дальность', 'en': 'Range'},
    },
    '射速加成': {
        'id': 'fire_rate_bonus',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'fire_rate_percent'},
        'display_name': {'ru': 'Скорострельность', 'en': 'Fire rate'},
    },
    '移动速度': {
        'id': 'movement_speed',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'movement_speed_percent'},
        'display_name': {'ru': 'Скорость передвижения', 'en': 'Movement speed'},
    },
    '爆炸伤害': {
        'id': 'explosion_damage',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'explosion_elemental_damage_percent'},
        'display_name': {'ru': 'Урон взрыва', 'en': 'Explosion damage'},
    },
    '持续伤害（灼烧、冰霜漩涡）伤害': {
        'id': 'damage_over_time',
        'profile': 'status_damage',
        'effect': {'type': 'increase_stat', 'stat': ['burn_damage_percent', 'frost_vortex_damage_percent']},
        'display_name': {'ru': 'Урон периодических статусов', 'en': 'Damage over time'},
    },
    '持续增益（快枪手、重装阵地）时间': {
        'id': 'persistent_buff_duration',
        'profile': 'extended_damage',
        'effect': {
            'type': 'increase_stat',
            'stat': ['fast_gunner_duration_percent', 'fortress_warfare_duration_percent'],
        },
        'display_name': {'ru': 'Длительность постоянных баффов', 'en': 'Persistent buff duration'},
    },
    '持续负面效果（灼烧、猎人标记、冰霜漩涡）时间': {
        'id': 'persistent_debuff_duration',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': ['burn_duration_percent', 'frost_vortex_duration_percent']},
        'display_name': {'ru': 'Длительность периодических дебаффов', 'en': 'Persistent debuff duration'},
    },
    '瞬时性伤害（不稳定爆弹、电涌）伤害': {
        'id': 'instant_keyword_damage',
        'profile': 'status_damage',
        'effect': {'type': 'increase_stat', 'stat': ['unstable_bomber_damage_percent', 'shock_damage_percent']},
        'display_name': {'ru': 'Урон мгновенных keyword-эффектов', 'en': 'Instant keyword damage'},
    },
    '冰霜漩涡触发概率': {
        'id': 'frost_vortex_trigger_chance',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'frost_vortex_trigger_chance_percent'},
        'display_name': {'ru': 'Шанс Frost Vortex', 'en': 'Frost Vortex chance'},
    },
    '子弹效果（弹射、碎弹）伤害': {
        'id': 'bullet_effect_damage',
        'profile': 'status_damage',
        'effect': {'type': 'increase_stat', 'stat': ['bounce_damage_percent', 'shrapnel_damage_percent']},
        'display_name': {'ru': 'Урон bullet-эффектов', 'en': 'Bullet effect damage'},
    },
    '子弹效果（弹射、碎弹）触发概率': {
        'id': 'bullet_effect_trigger_chance',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': ['bounce_trigger_chance_percent', 'shrapnel_trigger_chance_percent']},
        'display_name': {'ru': 'Шанс bullet-эффектов', 'en': 'Bullet effect trigger chance'},
    },
    '寒霜属性伤害': {
        'id': 'frost_elemental_damage',
        'profile': 'status_damage',
        'effect': {'type': 'increase_stat', 'stat': 'frost_elemental_damage_percent'},
        'display_name': {'ru': 'Урон frost-элемента', 'en': 'Frost elemental damage'},
    },
    '对猎人印记目标伤害': {
        'id': 'marked_target_damage',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'marked_target_damage_percent'},
        'display_name': {'ru': 'Урон по marked target', 'en': 'Damage vs marked target'},
    },
    '对猎人印记目标弱点伤害': {
        'id': 'marked_target_weakspot_damage',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'marked_target_weakspot_damage_percent'},
        'display_name': {'ru': 'Урон по weakspot marked target', 'en': 'Weakspot damage vs marked target'},
    },
    '对猎人印记目标暴击伤害': {
        'id': 'marked_target_crit_damage',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'marked_target_crit_damage_percent'},
        'display_name': {'ru': 'Крит. урон по marked target', 'en': 'Critical damage vs marked target'},
    },
    '对电涌异常目标伤害': {
        'id': 'damage_to_shocked_target',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'damage_to_shocked_target_percent'},
        'display_name': {'ru': 'Урон по Power Surge target', 'en': 'Damage vs shocked target'},
    },
    '弹射伤害': {
        'id': 'bounce_damage',
        'profile': 'status_damage',
        'effect': {'type': 'increase_stat', 'stat': 'bounce_damage_percent'},
        'display_name': {'ru': 'Урон Bounce', 'en': 'Bounce damage'},
    },
    '弹射弱点伤害': {
        'id': 'bounce_weakspot_damage',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'bounce_weakspot_damage_percent'},
        'display_name': {'ru': 'Урон Bounce по weakspot', 'en': 'Bounce weakspot damage'},
    },
    '弹射暴击伤害': {
        'id': 'bounce_crit_damage',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'bounce_crit_dmg_percent'},
        'display_name': {'ru': 'Крит. урон Bounce', 'en': 'Bounce crit damage'},
    },
    '弹射触发概率': {
        'id': 'bounce_trigger_chance',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'bounce_trigger_chance_percent'},
        'display_name': {'ru': 'Шанс Bounce', 'en': 'Bounce trigger chance'},
    },
    '快枪手状态下攻击力': {
        'id': 'fast_gunner_weapon_damage',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'fast_gunner_weapon_damage_percent'},
        'display_name': {'ru': 'Урон в Fast Gunner', 'en': 'Damage in Fast Gunner'},
    },
    '快枪手触发概率': {
        'id': 'fast_gunner_trigger_chance',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'fast_gunner_trigger_chance_percent'},
        'display_name': {'ru': 'Шанс Fast Gunner', 'en': 'Fast Gunner chance'},
    },
    '持续伤害（灼烧、冰霜漩涡）触发概率': {
        'id': 'persistent_dot_trigger_chance',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': ['burn_trigger_chance_percent', 'frost_vortex_trigger_chance_percent']},
        'display_name': {'ru': 'Шанс DoT-статусов', 'en': 'Damage-over-time trigger chance'},
    },
    '持续增益（快枪手、重装阵地）触发概率': {
        'id': 'persistent_buff_trigger_chance',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': ['fast_gunner_trigger_chance_percent', 'fortress_warfare_trigger_chance_percent']},
        'display_name': {'ru': 'Шанс persistent buffs', 'en': 'Persistent buff trigger chance'},
    },
    '持续负面效果（灼烧、猎人标记、冰霜漩涡）触发概率': {
        'id': 'persistent_debuff_trigger_chance',
        'profile': 'extended_damage',
        'effect': {
            'type': 'increase_stat',
            'stat': ['burn_trigger_chance_percent', 'the_bulls_eye_trigger_chance_percent', 'frost_vortex_trigger_chance_percent'],
        },
        'display_name': {'ru': 'Шанс persistent debuffs', 'en': 'Persistent debuff trigger chance'},
    },
    '灼烧触发概率': {
        'id': 'burn_trigger_chance',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'burn_trigger_chance_percent'},
        'display_name': {'ru': 'Шанс Burn', 'en': 'Burn trigger chance'},
    },
    '炽能属性伤害': {
        'id': 'burn_elemental_damage',
        'profile': 'status_damage',
        'effect': {'type': 'increase_stat', 'stat': 'burn_elemental_damage_percent'},
        'display_name': {'ru': 'Урон burn-элемента', 'en': 'Burn elemental damage'},
    },
    '猎人印记触发概率': {
        'id': 'the_bulls_eye_trigger_chance',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'the_bulls_eye_trigger_chance_percent'},
        'display_name': {'ru': 'Шанс The Bull\'s Eye', 'en': 'The Bull\'s Eye chance'},
    },
    '猎人标记持续时间': {
        'id': 'marked_duration',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'marked_duration_percent'},
        'display_name': {'ru': 'Длительность The Bull\'s Eye', 'en': 'The Bull\'s Eye duration'},
    },
    '电涌暴击伤害': {
        'id': 'shock_crit_damage',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'shock_crit_damage_percent'},
        'display_name': {'ru': 'Крит. урон Power Surge', 'en': 'Shock critical damage'},
    },
    '电涌触发概率': {
        'id': 'shock_trigger_chance',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'shock_trigger_chance_percent'},
        'display_name': {'ru': 'Шанс Power Surge', 'en': 'Shock trigger chance'},
    },
    '电离属性伤害': {
        'id': 'shock_elemental_damage',
        'profile': 'status_damage',
        'effect': {'type': 'increase_stat', 'stat': 'shock_elemental_damage_percent'},
        'display_name': {'ru': 'Урон shock-элемента', 'en': 'Shock elemental damage'},
    },
    '瞬时性伤害（不稳定爆弹、电涌）触发概率': {
        'id': 'instant_keyword_trigger_chance',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': ['unstable_bomber_trigger_chance_percent', 'shock_trigger_chance_percent']},
        'display_name': {'ru': 'Шанс мгновенных keyword-эффектов', 'en': 'Instant keyword trigger chance'},
    },
    '范围效果（冰霜漩涡、不稳定爆弹）触发概率': {
        'id': 'aoe_trigger_chance',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': ['frost_vortex_trigger_chance_percent', 'unstable_bomber_trigger_chance_percent']},
        'display_name': {'ru': 'Шанс зональных эффектов', 'en': 'Area effect trigger chance'},
    },
    '冲刺速度': {
        'id': 'sprint_speed',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'movement_speed_percent'},
        'display_name': {'ru': 'Скорость спринта', 'en': 'Sprint speed'},
    },
    '准确度': {
        'id': 'accuracy',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'accuracy'},
        'display_name': {'ru': 'Точность', 'en': 'Accuracy'},
    },
    '稳定度': {
        'id': 'stability',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'stability'},
        'display_name': {'ru': 'Стабильность', 'en': 'Stability'},
    },
    '冲锋枪准确度': {
        'id': 'smg_accuracy',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'smgs_accuracy'},
        'display_name': {'ru': 'Точность SMG', 'en': 'SMG accuracy'},
    },
    '冲锋枪稳定度': {
        'id': 'smg_stability',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'smgs_stability'},
        'display_name': {'ru': 'Стабильность SMG', 'en': 'SMG stability'},
    },
    '弓弩准确度': {
        'id': 'crossbow_accuracy',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'crossbows_accuracy'},
        'display_name': {'ru': 'Точность арбалета', 'en': 'Crossbow accuracy'},
    },
    '弓弩稳定度': {
        'id': 'crossbow_stability',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'crossbows_stability'},
        'display_name': {'ru': 'Стабильность арбалета', 'en': 'Crossbow stability'},
    },
    '手枪准确度': {
        'id': 'pistol_accuracy',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'pistol_accuracy'},
        'display_name': {'ru': 'Точность пистолета', 'en': 'Pistol accuracy'},
    },
    '手枪稳定度': {
        'id': 'pistol_stability',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'pistol_stability'},
        'display_name': {'ru': 'Стабильность пистолета', 'en': 'Pistol stability'},
    },
    '步枪准确度': {
        'id': 'rifle_accuracy',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'assault_rifl_accuracy'},
        'display_name': {'ru': 'Точность винтовки', 'en': 'Rifle accuracy'},
    },
    '步枪稳定度': {
        'id': 'rifle_stability',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'assault_rifl_stability'},
        'display_name': {'ru': 'Стабильность винтовки', 'en': 'Rifle stability'},
    },
    '狙击枪准确度': {
        'id': 'sniper_accuracy',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'sniper_rifles_accuracy'},
        'display_name': {'ru': 'Точность снайперки', 'en': 'Sniper accuracy'},
    },
    '狙击枪稳定度': {
        'id': 'sniper_stability',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'sniper_rifles_stability'},
        'display_name': {'ru': 'Стабильность снайперки', 'en': 'Sniper stability'},
    },
    '轻机枪准确度': {
        'id': 'lmg_accuracy',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'lmgs_accuracy'},
        'display_name': {'ru': 'Точность LMG', 'en': 'LMG accuracy'},
    },
    '轻机枪稳定度': {
        'id': 'lmg_stability',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'lmgs_stability'},
        'display_name': {'ru': 'Стабильность LMG', 'en': 'LMG stability'},
    },
    '重武器准确度': {
        'id': 'heavy_weapon_accuracy',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'heavy_weapon_accuracy'},
        'display_name': {'ru': 'Точность heavy weapon', 'en': 'Heavy weapon accuracy'},
    },
    '重武器稳定度': {
        'id': 'heavy_weapon_stability',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'heavy_weapon_stability'},
        'display_name': {'ru': 'Стабильность heavy weapon', 'en': 'Heavy weapon stability'},
    },
    '霰弹枪准确度': {
        'id': 'shotgun_accuracy',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'shotgun_accuracy'},
        'display_name': {'ru': 'Точность дробовика', 'en': 'Shotgun accuracy'},
    },
    '霰弹枪稳定度': {
        'id': 'shotgun_stability',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'shotgun_stability'},
        'display_name': {'ru': 'Стабильность дробовика', 'en': 'Shotgun stability'},
    },
    '近战伤害': {
        'id': 'melee_damage',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'melee_damage_percent'},
        'display_name': {'ru': 'Урон ближнего боя', 'en': 'Melee damage'},
    },
    '受治疗增益': {
        'id': 'healing_received',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'healing_received_percent'},
        'display_name': {'ru': 'Получаемое лечение', 'en': 'Healing received'},
    },
    '四肢伤害减免': {
        'id': 'limb_damage_reduction',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'limb_damage_reduction_percent'},
        'display_name': {'ru': 'Снижение урона по конечностям', 'en': 'Limb damage reduction'},
    },
    '头部受伤减免': {
        'id': 'head_damage_reduction',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'head_damage_reduction_percent'},
        'display_name': {'ru': 'Снижение урона по голове', 'en': 'Head damage reduction'},
    },
    '寒霜属性伤害减免': {
        'id': 'frost_damage_reduction',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'frost_elemental_damage_reduction_percent'},
        'display_name': {'ru': 'Снижение frost-урона', 'en': 'Frost damage reduction'},
    },
    '开镜瞄准稳定性': {
        'id': 'ads_stability',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'ads_stability_percent'},
        'display_name': {'ru': 'Стабильность при ADS', 'en': 'ADS stability'},
    },
    '异常伤害减免': {
        'id': 'status_damage_reduction',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'status_damage_reduction_percent'},
        'display_name': {'ru': 'Снижение статусного урона', 'en': 'Status damage reduction'},
    },
    '弱点伤害减免': {
        'id': 'weakspot_damage_reduction',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'weakspot_damage_reduction_percent'},
        'display_name': {'ru': 'Снижение урона по weakspot', 'en': 'Weakspot damage reduction'},
    },
    '战术道具伤害': {
        'id': 'tactical_item_damage',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'tactical_item_damage_percent'},
        'display_name': {'ru': 'Урон тактических предметов', 'en': 'Tactical item damage'},
    },
    '抬枪速度': {
        'id': 'raise_weapon_speed',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'raise_weapon_speed_percent'},
        'display_name': {'ru': 'Скорость вскидывания оружия', 'en': 'Raise weapon speed'},
    },
    '拔枪速度': {
        'id': 'draw_speed',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'draw_speed_percent'},
        'display_name': {'ru': 'Скорость доставания оружия', 'en': 'Draw speed'},
    },
    '收枪速度': {
        'id': 'holster_speed',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'holster_speed_percent'},
        'display_name': {'ru': 'Скорость убирания оружия', 'en': 'Holster speed'},
    },
    '暴击伤害减免': {
        'id': 'crit_damage_reduction',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'crit_damage_reduction_percent'},
        'display_name': {'ru': 'Снижение крит. урона', 'en': 'Critical damage reduction'},
    },
    '最大耐力': {
        'id': 'max_stamina',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'max_stamina_percent'},
        'display_name': {'ru': 'Макс. выносливость', 'en': 'Max stamina'},
    },
    '枪械伤害减免': {
        'id': 'weapon_damage_reduction',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'weapon_damage_reduction_percent'},
        'display_name': {'ru': 'Снижение урона от оружия', 'en': 'Weapon damage reduction'},
    },
    '炽能、爆炸伤害减免': {
        'id': 'fire_explosion_damage_reduction',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'fire_explosion_damage_reduction_percent'},
        'display_name': {'ru': 'Снижение burn/explosion-урона', 'en': 'Burn and explosion damage reduction'},
    },
    '炽能属性伤害减免': {
        'id': 'burn_damage_reduction',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'burn_elemental_damage_reduction_percent'},
        'display_name': {'ru': 'Снижение burn-урона', 'en': 'Burn damage reduction'},
    },
    '电离属性伤害减免': {
        'id': 'shock_damage_reduction',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'shock_elemental_damage_reduction_percent'},
        'display_name': {'ru': 'Снижение shock-урона', 'en': 'Shock damage reduction'},
    },
    '耐力恢复速度提升': {
        'id': 'stamina_recovery',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'stamina_recovery_percent'},
        'display_name': {'ru': 'Восстановление выносливости', 'en': 'Stamina recovery'},
    },
    '耐力消耗减免': {
        'id': 'stamina_cost_reduction',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'stamina_cost_reduction_percent'},
        'display_name': {'ru': 'Снижение расхода выносливости', 'en': 'Stamina cost reduction'},
    },
    '药物治疗增益': {
        'id': 'medicine_healing',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'medicine_healing_percent'},
        'display_name': {'ru': 'Эффективность медикаментов', 'en': 'Medicine healing bonus'},
    },
    '躯干伤害减免': {
        'id': 'torso_damage_reduction',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'torso_damage_reduction_percent'},
        'display_name': {'ru': 'Снижение урона по торсу', 'en': 'Torso damage reduction'},
    },
    '霜寒、电离伤害减免': {
        'id': 'frost_shock_damage_reduction',
        'profile': 'extended_damage',
        'effect': {'type': 'increase_stat', 'stat': 'frost_shock_damage_reduction_percent'},
        'display_name': {'ru': 'Снижение frost/shock-урона', 'en': 'Frost and shock damage reduction'},
    },
}

VALUE_PROFILES = {
    'crit_rate': [0.6, 1.2, 1.8, 2.4, 3.0, 3.6, 4.2, 4.8, 5.4, 6.0, 7.2],
    'extended_damage': [1.2, 2.4, 3.6, 4.8, 6.0, 7.2, 8.0, 9.6, 10.8, 12.0, 14.4, 16.0, 18.0, 20.0, 21.6, 24.0, 25.0],
    'status_damage': [1.2, 2.4, 3.6, 4.8, 6.0, 7.2, 8.0, 9.6, 10.8, 12.0, 14.4],
    'ultra_damage': [1.2, 2.4, 3.6, 4.8, 6.0, 7.2, 8.0, 9.6, 10.8, 12.0, 14.4, 16.0, 18.0, 20.0, 21.6, 24.0, 25.0],
}

EXACT_VALUE_ALIAS = {
    '超感强度': ['超感'],
    '冰霜漩涡持续时间': ['冰霜漩涡时间'],
    '持续增益（快枪手、重装阵地）时间': ['增益效果'],
    '持续负面效果（灼烧、猎人标记、冰霜漩涡）时间': ['负面效果'],
    '范围效果（冰霜漩涡、不稳定爆弹、重装阵地）范围': ['范围效果'],
    '射速加成': ['射速'],
    '碎弹暴击伤害': ['碎弹暴击'],
}


def read_varint(buf: bytes, pos: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        b = buf[pos]
        pos += 1
        value |= (b & 0x7F) << shift
        if not (b & 0x80):
            return value, pos
        shift += 7


def load_bindict_blob(path: Path) -> tuple[bytes, list[str], bytes]:
    raw = path.read_bytes()
    code = marshal.loads(raw[16:])
    blob = next(const for const in code.co_consts if isinstance(const, (bytes, bytearray)) and len(const) > 16)
    count = struct.unpack_from('<I', blob, 0)[0]
    offsets = [struct.unpack_from('<I', blob, 8 + i * 4)[0] for i in range(count)]
    data_start = 8 + count * 4
    prev = 0
    strings: list[str] = []
    for end in offsets:
        strings.append(blob[data_start + prev:data_start + end].decode('utf-8', 'ignore'))
        prev = end
    return raw, strings, blob


def read_bindict_strings(path: Path) -> list[str]:
    _, strings, _ = load_bindict_blob(path)
    return strings


def extract_attribute_families(strings: list[str]) -> dict[str, list[str]]:
    families: dict[str, list[str]] = {}
    for entry in strings:
        match = TIER_RE.match(entry)
        if not match:
            continue
        name = match.group('name')
        tier = match.group('tier')
        families.setdefault(name, []).append(tier)
    for name, tiers in families.items():
        families[name] = sorted(set(tiers), key=lambda value: int(value, 36))
    return families


def extract_categories(strings: list[str]) -> list[str]:
    categories: list[str] = []
    for entry in strings:
        if '_$S@TIDS$_ciq|' not in entry:
            continue
        name = entry.split('_$S@TIDS$_ciq|', 1)[0]
        if name and name != 'lan_translate' and name not in categories:
            categories.append(name)
    return categories


def extract_level_profiles(strings: list[str]) -> tuple[list[str], dict[str, list[str]]]:
    profiles: list[str] = []
    by_tier: dict[str, list[str]] = {}
    for entry in strings:
        match = LEVEL_RE.match(entry)
        if not match:
            continue
        name = match.group('name')
        tier = match.group('tier')
        if name and name != 'lan_translate' and name not in profiles:
            profiles.append(name)
        if name and name != 'lan_translate':
            by_tier.setdefault(tier, [])
            if name not in by_tier[tier]:
                by_tier[tier].append(name)
    return profiles, by_tier


def build_values(tiers: list[str], profile_name: str) -> dict[str, float]:
    profile = VALUE_PROFILES[profile_name]
    values: dict[str, float] = {}
    for index, tier in enumerate(tiers):
        if index < len(profile):
            values[tier] = profile[index]
        else:
            last_value = profile[-1]
            step = profile[-1] - profile[-2] if len(profile) > 1 else max(last_value * 0.15, 0.5)
            values[tier] = round(last_value + step * (index - len(profile) + 1), 2)
    return values


def read_bindict_top_level_records(path: Path) -> tuple[list[str], bytes, list[tuple[int, int]]]:
    _, strings, blob = load_bindict_blob(path)
    count = struct.unpack_from('<I', blob, 0)[0]
    offsets = [struct.unpack_from('<I', blob, 8 + i * 4)[0] for i in range(count)]
    data_start = 8 + count * 4
    tail = blob[data_start + offsets[-1]:]
    index_off = struct.unpack_from('<I', tail, 0)[0]
    data = tail[4:index_off]
    index = tail[index_off:]
    entry_count, pos = read_varint(index, 3)
    for _ in range(entry_count):
        pos += 8
    region = index[pos:]
    pairs: list[tuple[int, int]] = []
    cursor = 0
    while cursor < len(region):
        try:
            key, next_pos = read_varint(region, cursor)
            value, cursor = read_varint(region, next_pos)
        except Exception:
            break
        pairs.append((key, value))
    return strings, data, sorted(pairs, key=lambda item: item[1])


def scan_bindict_record(buf: bytes, strings: list[str]) -> tuple[list[tuple[int, list[int | float]]], list[str]]:
    arrays: list[tuple[int, list[int | float]]] = []
    refs: list[str] = []
    pos = 0
    while pos < len(buf):
        if buf[pos] == 0x27 and pos + 2 < len(buf):
            subtype = buf[pos + 1]
            try:
                count, payload_pos = read_varint(buf, pos + 2)
            except Exception:
                pos += 1
                continue
            if subtype == 0x22:
                required = payload_pos + 8 * count
                if required <= len(buf):
                    values = [round(struct.unpack_from('<d', buf, payload_pos + 8 * index)[0], 6) for index in range(count)]
                    arrays.append((subtype, values))
                    pos = required
                    continue
            else:
                values: list[int] = []
                cursor = payload_pos
                try:
                    for _ in range(count):
                        value, cursor = read_varint(buf, cursor)
                        values.append(value)
                except Exception:
                    pos += 1
                    continue
                arrays.append((subtype, values))
                pos = cursor
                continue
        if buf[pos] == 0x07 and pos + 3 < len(buf) and buf[pos + 1] == 0x01 and buf[pos + 2] == 0x05:
            try:
                ref_index, next_pos = read_varint(buf, pos + 3)
            except Exception:
                pos += 1
                continue
            if ref_index < len(strings):
                refs.append(strings[ref_index])
            pos = next_pos
            continue
        pos += 1
    return arrays, refs


def normalize_exact_family(text: str) -> tuple[str | None, str | None]:
    match = CIH_NAME_RE.match(text)
    if not match:
        return None, None
    name = match.group('name')
    for token in ['#7#+{1}%#7#', '#7#+{1}#7#', '#7#{1}%#7#', '#7#+{2}%#7#', '#7#{1}#7#', '#7#+{2}#7#']:
        name = name.replace(token, '')
    return name.strip(), match.group('tier')


def normalize_game_value(value: float) -> float:
    if value == 0:
        return 0.0
    if abs(value) <= 1.0:
        return round(value * 100, 6)
    return round(value, 6)


def extract_exact_values_from_mod_entry_data(path: Path) -> dict[str, dict[str, list[float]]]:
    strings, data, records = read_bindict_top_level_records(path)
    exact_values: dict[str, dict[str, set[float]]] = {}
    for index, (_, offset) in enumerate(records):
        rel = offset - 4
        next_rel = records[index + 1][1] - 4 if index + 1 < len(records) else len(data)
        arrays, refs = scan_bindict_record(data[rel:next_rel], strings)
        cih_texts = [entry for entry in refs if '_$S@TIDS$_cih|' in entry]
        if not cih_texts:
            continue
        numeric_values: list[float] = []
        for subtype, values in arrays:
            if subtype == 0x22:
                numeric_values.extend(normalize_game_value(value) for value in values if isinstance(value, float))
                continue
            for value in values:
                if isinstance(value, int) and value < len(strings) and NUMERIC_RE.fullmatch(strings[value]):
                    numeric_values.append(normalize_game_value(float(strings[value])))
        if not numeric_values:
            continue
        normalized: list[tuple[str, str, str]] = []
        for text in cih_texts:
            family, tier = normalize_exact_family(text)
            if family and tier:
                normalized.append((family, tier, text))
        if not normalized:
            continue
        normalized.sort(key=lambda item: ('#7#' in item[2], len(item[0])))
        family, tier, _ = normalized[0]
        exact_values.setdefault(family, {}).setdefault(tier, set()).update(numeric_values)
    return {
        family: {tier: sorted(values) for tier, values in sorted(tiers.items(), key=lambda item: int(item[0], 36))}
        for family, tiers in sorted(exact_values.items(), key=lambda item: item[0])
    }


def merge_exact_values(name: str, tiers: list[str], values: dict[str, float], exact_value_families: dict[str, dict[str, list[float]]]) -> dict[str, float]:
    merged = dict(values)
    family_names = [name, *EXACT_VALUE_ALIAS.get(name, [])]
    for family_name in family_names:
        exact_values = exact_value_families.get(family_name)
        if not exact_values:
            continue
        ratios: list[float] = []
        for tier in tiers:
            tier_values = exact_values.get(tier)
            base_value = values.get(tier)
            if not tier_values or len(tier_values) != 1 or not base_value:
                continue
            ratios.append(tier_values[0] / base_value)
        if ratios:
            average_ratio = sum(ratios) / len(ratios)
            if len(ratios) == 1 or max(abs(ratio - average_ratio) for ratio in ratios) <= max(abs(average_ratio) * 0.15, 0.25):
                merged = {tier: round(value * average_ratio, 6) for tier, value in values.items()}
        for tier in tiers:
            tier_values = exact_values.get(tier)
            if tier_values and len(tier_values) == 1:
                merged[tier] = tier_values[0]
        break
    return merged


def main() -> int:
    parser = argparse.ArgumentParser(description='Extract Once Human mod secondary attribute metadata from decompiled game files.')
    parser.add_argument('--decompile-dir', type=Path, required=True, help='Path to Once Human/decompile')
    parser.add_argument('--output', type=Path, required=True, help='Output JSON path')
    args = parser.parse_args()

    base = args.decompile_dir / 'root_script' / 'raw' / 'game_common' / 'data'
    mod_entry_strings = read_bindict_strings(base / 'mod_entry_data.pyc')
    mod_sub_entry_strings = read_bindict_strings(base / 'mod_sub_entry_lib.pyc')
    mod_level_strings = read_bindict_strings(base / 'mod_level_lib_data.pyc')
    exact_value_families = extract_exact_values_from_mod_entry_data(base / 'mod_entry_data.pyc')

    families = extract_attribute_families(mod_entry_strings)
    categories = extract_categories(mod_sub_entry_strings)
    level_profiles, tier_metadata = extract_level_profiles(mod_level_strings)

    all_attributes = []
    supported_attributes = []
    for name, tiers in sorted(families.items(), key=lambda item: item[0]):
        config = SUPPORTED_ATTRIBUTE_CONFIG.get(name)
        entry = {
            'id': config['id'] if config else name,
            'game_name': name,
            'display_name': (config or {}).get('display_name', {'ru': name, 'en': name}),
            'tier_codes': tiers,
            'tier_metadata': {tier: tier_metadata.get(tier, []) for tier in tiers if tier in tier_metadata},
            'effect': (config or {}).get('effect'),
            'values': merge_exact_values(name, tiers, build_values(tiers, config['profile']), exact_value_families) if config else {},
            'exact_values': exact_value_families.get(name) or next(
                (exact_value_families[alias] for alias in EXACT_VALUE_ALIAS.get(name, []) if alias in exact_value_families),
                {},
            ),
            'profile': (config or {}).get('profile'),
            'implemented': bool(config),
            'supported': bool(config),
            'source': 'mod_entry_data.pyc',
        }
        all_attributes.append(entry)
        if not config:
            continue
        supported_attributes.append({
            **entry,
            'source': {
                'family': 'mod_entry_data.pyc',
                'levels': 'mod_level_lib_data.pyc',
            },
        })

    payload = {
        'source': {
            'decompile_dir': str(args.decompile_dir),
            'files': [
                'root_script/raw/game_common/data/mod_entry_data.pyc',
                'root_script/raw/game_common/data/mod_sub_entry_lib.pyc',
                'root_script/raw/game_common/data/mod_level_lib_data.pyc',
            ],
        },
        'categories': categories,
        'level_profiles': level_profiles,
        'tier_metadata': tier_metadata,
        'exact_value_families': exact_value_families,
        'all_attributes': all_attributes,
        'supported_attributes': supported_attributes,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'Wrote {len(supported_attributes)} supported attributes to {args.output}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
