# mechanics.py

import time
import random
import math
import dearpygui.dearpygui as dpg
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


class MechanicsProcessor:
    def __init__(self, context):
        self.context = context
        self.active_effects = []
        self.counters = {}
        self.weapon_mechanics = []
        if context.player.weapon and context.player.weapon.mechanics:
            self.weapon_mechanics = context.player.weapon.mechanics.get('effects', [])

    def process_weapon_event(self, event_name, **kwargs):
        if event_name == 'on_fire':
            current_time = time.time()
            fire_rate = self.context.player.stats.get('fire_rate', 1)
            fire_cooldown = 60 / fire_rate
            if current_time - self.context.last_fire_time < fire_cooldown:
                #logging.info("Cannot fire yet, still in cooldown.")
                return
            self.context.last_fire_time = current_time  # Обновляем время выстрела
        for effect in self.weapon_mechanics:
            if effect.get('type') == 'on_event':
                event = effect.get('event')
                if event == event_name:
                    if event_name == 'on_fire':
                        self.handle_every_n_shots(effect)
                    else:
                        self.apply_effects(effect.get('effects', []), **kwargs)

    def handle_every_n_shots(self, effect):
        n = effect.get('n', 1)
        counter_name = f"every_n_shots_{n}"
        self.counters[counter_name] = self.counters.get(counter_name, 0) + 1
        logging.debug(f"Counter '{counter_name}' incremented to {self.counters[counter_name]}.")
        if self.counters[counter_name] >= n:
            self.counters[counter_name] = 0
            logging.info(f"Triggering 'every_n_shots' effect after {n} shots.")
            self.apply_effects(effect.get('effects', []))

    def apply_effects(self, effects, **kwargs):
        for effect in effects:
            effect_type = effect.get('type')
            if effect_type == 'trigger_ability':
                self.trigger_ability(effect)
            elif effect_type == 'increment_counter':
                self.increment_counter(effect)
            elif effect_type == 'increase_stat':
                self.increase_stat(effect)
            elif effect_type == 'apply_status':
                self.apply_status(effect)
            elif effect_type == 'spread_effect':
                self.spread_effect(effect)
            elif effect_type == 'set_flag':
                self.set_flag(effect)
            elif effect_type == 'trigger_unstable_bomber':
                self.trigger_unstable_bomber(effect)
            # Добавьте обработку других типов эффектов по мере необходимости

    def trigger_ability(self, effect):
        ability = effect.get('ability')
        if ability == 'unstable_bomber':
            self.trigger_unstable_bomber(effect)
        # Добавьте обработку других способностей

    def trigger_unstable_bomber(self, effect):
        # Вычисляем урон на основе формулы
        damage_formula = effect.get('damage_formula', '0')
        damage = self.calculate_damage_from_formula(damage_formula)
        # Применяем радиус взрыва и другие параметры, если необходимо
        # Для упрощения, наносим урон и отображаем его
        self.context.display_unstable_bomber_damage(damage)
        # Логируем урон
        logging.info(f"Unstable Bomber triggered! Damage dealt: {damage}")

    def calculate_damage_from_formula(self, formula):
        # Пример обработки формулы '100% Psi Intensity'
        if formula.endswith('% Psi Intensity'):
            percentage = float(formula.split('%')[0])
            psi_intensity = self.context.player.stats.get('psi_intensity', 0)
            damage = psi_intensity * (percentage / 100.0)
            logging.debug(f"Calculated damage from formula '{formula}': {damage}")
            return damage
        # Добавьте обработку других формул по мере необходимости
        logging.warning(f"Unknown damage formula: '{formula}'. Damage set to 0.")
        return 0

    def increment_counter(self, effect):
        counter_name = effect.get('counter')
        self.counters[counter_name] = self.counters.get(counter_name, 0) + 1
        logging.debug(f"Counter '{counter_name}' incremented to {self.counters[counter_name]}.")

    def increase_stat(self, effect):
        stat = effect.get('stat')
        value = effect.get('value')
        duration = effect.get('duration_seconds', 0)
        max_stacks = effect.get('max_stacks', 1)
        # Применяем бонус с учётом максимального количества стаков
        if stat not in self.context.player.active_stat_bonuses:
            self.context.player.active_stat_bonuses[stat] = []
        if len(self.context.player.active_stat_bonuses[stat]) < max_stacks:
            self.context.player.apply_stat_bonus(stat, value, duration)
            logging.info(f"Stat '{stat}' increased by {value} for {duration} seconds.")
        else:
            logging.debug(f"Max stacks reached for stat '{stat}'. Effect not applied.")

    def apply_status(self, effect):
        status = effect.get('status')
        vulnerability_bonus_percent = effect.get('vulnerability_bonus_percent', 0)
        duration_seconds = effect.get('duration_seconds', 0)
        description = effect.get('description', '')
        # Применяем статусный эффект
        if status == 'the_bulls_eye':
            self.context.player.apply_stat_bonus('vulnerability_percent', vulnerability_bonus_percent, duration_seconds)
            logging.info(
                f"Status '{status}' applied with vulnerability bonus {vulnerability_bonus_percent}% for {duration_seconds} seconds.")
        # Добавьте обработку других статусов по мере необходимости

    def spread_effect(self, effect):
        # Реализация эффекта распространения (spread)
        radius_meters = effect.get('radius_meters', 0)
        inner_effect = effect.get('effect')
        # Для упрощения, просто применяем внутренний эффект
        self.apply_effects([inner_effect])
        logging.info(f"Spread effect applied with radius {radius_meters} meters.")

    def set_flag(self, effect):
        flag = effect.get('flag')
        value = effect.get('value')
        self.context.player.stats[flag] = value
        logging.info(f"Flag '{flag}' set to {value}.")

    def update_active_effects(self):
        # Метод для обновления активных эффектов, если необходимо
        pass
