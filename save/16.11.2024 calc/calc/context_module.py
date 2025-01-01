# context_module.py

import json
import time
import math
import random
import dearpygui.dearpygui as dpg  # Импортируем для доступа к позициям мыши
from player import Item
import shutil
import os

class DamageCalculator:
    def __init__(self, player, context):
        self.player = player
        self.context = context

    def calculate_damage(self, weakspot_hit=False):
        damage = self.get_base_damage()

        try:
            damage = self.apply_weapon_and_status_bonus(damage)
        except Exception as e:
            print(f"Ошибка при применении бонусов оружия и статуса: {e}")

        try:
            damage = self.apply_enemy_type_bonus(damage)
        except Exception as e:
            print(f"Ошибка при применении бонусов к типу врага: {e}")

        try:
            damage = self.apply_crit_bonus(damage)
        except Exception as e:
            print(f"Ошибка при применении критического бонуса: {e}")

        try:
            if weakspot_hit:
                damage = self.apply_weakspot_bonus(damage)
        except Exception as e:
            print(f"Ошибка при применении бонуса за попадание в слабое место: {e}")

        # Убедимся, что урон больше нуля
        if damage <= 0:
            damage = 1

        return damage

    def get_base_damage(self):
        damage = self.player.stats.get('damage', 0)
        return damage

    def apply_weapon_and_status_bonus(self, damage):
        weapon_damage_bonus = self.player.stats.get('weapon_damage_percent', 0)
        status_damage_bonus = self.player.stats.get('status_damage_percent', 0)
        total_bonus = (weapon_damage_bonus + status_damage_bonus) / 100.0
        damage *= (1 + total_bonus)
        return damage

    def apply_enemy_type_bonus(self, damage):
        damage_bonus_vs_enemy = 0
        if self.context.enemy_type == 'Обычный':
            damage_bonus_vs_enemy = self.player.stats.get('damage_bonus_normal', 0)
        elif self.context.enemy_type == 'Элитный':
            damage_bonus_vs_enemy = self.player.stats.get('damage_bonus_elite', 0)
        elif self.context.enemy_type == 'Босс':
            damage_bonus_vs_enemy = self.player.stats.get('damage_bonus_boss', 0)
        damage *= (1 + damage_bonus_vs_enemy / 100.0)
        return damage

    def apply_crit_bonus(self, damage):
        crit_rate = self.player.stats.get('crit_rate_percent', 0)
        is_crit = random.uniform(0, 100) <= crit_rate
        self.context.last_hit_crit = is_crit  # Сохраняем информацию о критическом попадании
        if is_crit:
            crit_damage_bonus = self.player.stats.get('crit_damage_percent', 0)
            damage *= (1 + crit_damage_bonus / 100.0)
        return damage

    def apply_weakspot_bonus(self, damage):
        weakspot_bonus = self.player.stats.get('weakspot_damage_percent', 0)
        damage *= (1 + weakspot_bonus / 100.0)
        self.context.last_hit_weakspot = True
        return damage


class Context:
    def __init__(self, player):
        self.player = player
        self.total_damage = 0
        self.dps = 0
        self.max_dps = 0
        self.max_total_damage = 0
        self.damage_history = []
        self.mouse_pressed = False
        self.scheduled_deletions = []
        # Здоровье
        self.base_hp = 700  # Базовый HP без бонусов
        self.bonus_hp = 0   # Дополнительный HP от брони и других бонусов
        self.max_hp = self.base_hp + self.bonus_hp
        self.current_hp = self.max_hp  # Текущий HP начинает с максимума
        self.enemies_within_distance = 0
        self.target_distance = 0
        self.current_ammo = 0
        self.reloading = False
        self.reload_end_time = 0
        self.last_fire_time = 0
        self.last_damage_time = 0
        self.last_shot_time = None
        self.selected_mods = []
        self.selected_items = {}
        self.mannequin_status_effects = {}
        self.status_stack_counts = {"Fire": 0}
        self.max_fire_stacks = 16
        self.stats_display_timer = 0.0
        self.selected_status = None
        self.event_effects = {}
        # Загрузка данных
        self.items_data = self.load_items_and_sets()['items']
        self.sets_data = self.load_items_and_sets()['sets']
        self.mods_data = self.load_mods()
        self.base_stats_data = self.load_all_armor_stats()
        self.base_stats = self.base_stats_data.get('items', {})
        self.calibration_bonuses = self.base_stats_data.get('calibration_bonuses', {})
        self.multipliers = self.load_items_and_sets().get('multipliers', {})
        # Для обработки модификаторов
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
            'damage', 'crit_rate_percent', 'crit_damage_percent', 'weapon_damage_percent',
            'status_damage_percent', 'max_hp', 'movement_speed_percent',
            'elemental_damage_percent', 'weakspot_damage_percent', 'reload_speed_percent',
            'magazine_capacity', 'damage_bonus_normal', 'damage_bonus_elite',
            'damage_bonus_boss', 'fire_rate', 'reload_speed', 'hp', 'psi_intensity', 'pollution_resist'
        ]
        self.flags_options = ['can_deal_weakspot_damage', 'is_invincible', 'has_super_armor']
        self.conditions_options = [
            'hp / max_hp > 0.5', 'enemies_within_distance == 0', 'is_crit', 'is_weak_spot',
            'target_is_marked', 'hp / max_hp < 0.3'
        ]
        # Переменные для отображения урона
        self.last_damage_dealt = 0  # Последний нанесённый урон
        self.last_hit_weakspot = False  # Попадание в слабую точку
        self.last_hit_crit = False  # Критическое попадание
        self.enemy_type = 'Обычный'  # Тип врага
        self.last_shot_mouse_pos = (0, 0)  # Позиция мыши при последнем выстреле
        # Создаём экземпляр DamageCalculator
        self.damage_calculator = DamageCalculator(self.player, self)

    def load_mods(self):
        try:
            with open('mods_config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def load_all_armor_stats(self):
        try:
            with open('all_armor_stats.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def load_items_and_sets(self):
        try:
            with open('armor_sets.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Убедитесь, что каждый сет имеет поле 'description'
                for game_set in data.get('sets', []):
                    game_set.setdefault('description', '')
                return data
        except FileNotFoundError:
            return {
                'items': [],
                'sets': [],
                'multipliers': {}
            }

    def update_selected_status(self, status):
        self.selected_status = status

    def update_parameter(self, parameter, value):
        if parameter == "enemies_within_distance_input":
            self.enemies_within_distance = value
        elif parameter == "target_distance_input":
            self.target_distance = value
        elif parameter == "base_damage_input":
            self.player.base_stats['damage'] = value
        elif parameter == "crit_chance_input":
            self.player.base_stats['crit_rate_percent'] = value
        elif parameter == "crit_dmg_input":
            self.player.base_stats['crit_damage_percent'] = value
        elif parameter == "magazine_capacity_input":
            self.player.base_stats['magazine_capacity'] = value
        elif parameter == "fire_rate_input":
            self.player.base_stats['fire_rate'] = value
        elif parameter == "reload_speed_input":
            self.player.base_stats['reload_speed'] = value
        elif parameter == "status_damage_bonus_input":
            self.player.base_stats['status_damage_percent'] = value
        elif parameter == "weakspot_damage_bonus_input":
            self.player.base_stats['weakspot_damage_percent'] = value
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
        # Обновляем статистику игрока
        self.player.recalculate_stats()
        # Обновляем текущий боезапас на основе новых параметров
        self.current_ammo = self.player.stats.get('magazine_capacity', 0)
        # Обновляем максимальное здоровье
        self.update_max_hp()

    def update_max_hp(self):
        self.bonus_hp = self.player.stats.get('hp', 0)
        self.max_hp = self.base_hp + self.bonus_hp

    def get_stats_display_text(self, player):
        stats_text = "Текущие параметры персонажа:\n\n"
        stats_text += f"HP: {self.current_hp}/{self.max_hp}\n"
        stats_text += f"Базовый HP: {self.base_hp}\n"
        stats_text += f"Бонусный HP от брони: {self.bonus_hp}\n"
        stats_to_display = [
            'damage', 'crit_rate_percent', 'crit_damage_percent',
            'weapon_damage_percent', 'status_damage_percent', 'movement_speed_percent',
            'elemental_damage_percent', 'weakspot_damage_percent', 'reload_speed',
            'magazine_capacity', 'damage_bonus_normal', 'damage_bonus_elite',
            'damage_bonus_boss', 'pollution_resist', 'psi_intensity', 'fire_rate'
        ]
        for stat in stats_to_display:
            value = player.stats.get(stat, getattr(self, stat, 0))
            stats_text += f"{stat}: {value}\n"
        stats_text += "\nЭкипированные предметы:\n"
        for item_type, item in player.equipped_items.items():
            stats_text += f"{item.name} ({item_type.capitalize()}): Звёзд: {item.star}, Уровень: {item.level}, Калибровка: {item.calibration}\n"
            item_stats = item.get_stats()
            for stat_name, stat_value in item_stats.items():
                stats_text += f"  {stat_name}: {stat_value}\n"
        if self.mannequin_status_effects:
            stats_text += "\nСтатусные эффекты:\n"
            for key, value in self.mannequin_status_effects.items():
                stats_text += f"{key}: {value}\n"
        return stats_text

    def initialize(self):
        self.update_max_hp()
        self.current_hp = self.max_hp  # Начинаем с полного здоровья
        self.current_ammo = self.player.stats.get('magazine_capacity', 0)

    def update(self):
        current_time = time.time()
        if self.reloading and current_time >= self.reload_end_time:
            self.reloading = False
            magazine_capacity = self.player.stats.get('magazine_capacity', 0)
            self.current_ammo = magazine_capacity
        if self.mouse_pressed and not self.reloading:
            fire_rate = self.player.stats.get('fire_rate', 0)
            if fire_rate > 0:
                time_between_shots = 60.0 / fire_rate
                if current_time - self.last_fire_time >= time_between_shots:
                    self.try_fire_weapon()
                    self.last_fire_time = current_time
            else:
                # Не стреляем, если скорострельность равна нулю
                pass
        self.dps = self.calculate_dps()
        if current_time - self.last_damage_time >= 3.0 and self.total_damage != 0:
            self.total_damage = 0
            self.dps = 0
        self.update_status_effects()

        # Обновляем max_hp из статистики игрока
        previous_max_hp = self.max_hp
        self.update_max_hp()
        if self.max_hp != previous_max_hp:
            # Оставляем current_hp без изменений
            pass

    def try_fire_weapon(self):
        current_time = time.time()
        if self.reloading:
            return
        if self.current_ammo <= 0:
            self.reload_weapon()
            return

        # Определяем, попал ли игрок по манекену
        mouse_pos = dpg.get_mouse_pos(local=False)
        if not self.is_within_target_area(mouse_pos):
            return

        # Определяем, попал ли игрок в слабую точку
        weakspot_hit = self.is_weakspot_hit(mouse_pos)
        self.last_hit_weakspot = weakspot_hit

        damage = self.damage_calculator.calculate_damage(weakspot_hit)
        self.total_damage += damage
        self.max_total_damage = max(self.max_total_damage, self.total_damage)
        self.damage_history.append((current_time, damage))
        self.current_ammo -= 1
        self.last_damage_time = current_time
        self.last_shot_time = current_time
        self.last_damage_dealt = damage
        self.last_shot_mouse_pos = mouse_pos  # Сохраняем позицию мыши при выстреле

    def is_within_target_area(self, mouse_pos):
        # Координаты нормальной зоны (синяя зона)
        normal_zone = {
            'left': 90,
            'right': 210,
            'top': 50,
            'bottom': 290
        }
        # Координаты слабой точки (красная зона)
        weakspot_rect = {
            'left': 130,
            'right': 170,
            'top': 10,
            'bottom': 50
        }
        x, y = mouse_pos
        # Преобразуем координаты мыши в локальные относительно `damage_layer`
        window_pos = dpg.get_item_rect_min("damage_layer")
        local_x = x - window_pos[0]
        local_y = y - window_pos[1]
        # Проверяем, находится ли точка в пределах нормальной зоны или слабой точки
        if ((normal_zone['left'] <= local_x <= normal_zone['right'] and normal_zone['top'] <= local_y <= normal_zone['bottom']) or
                (weakspot_rect['left'] <= local_x <= weakspot_rect['right'] and weakspot_rect['top'] <= local_y <= weakspot_rect['bottom'])):
            return True
        else:
            return False

    def is_weakspot_hit(self, mouse_pos):
        # Координаты слабой точки (красная зона)
        weakspot_rect = {
            'left': 130,
            'right': 170,
            'top': 10,
            'bottom': 50
        }
        x, y = mouse_pos
        # Преобразуем координаты мыши в локальные относительно `damage_layer`
        window_pos = dpg.get_item_rect_min("damage_layer")
        local_x = x - window_pos[0]
        local_y = y - window_pos[1]
        # Проверяем, находится ли точка в пределах слабой зоны
        if weakspot_rect['left'] <= local_x <= weakspot_rect['right'] and weakspot_rect['top'] <= local_y <= weakspot_rect['bottom']:
            return True
        else:
            return False

    def reload_weapon(self):
        if not self.reloading:
            reload_speed = self.player.stats.get('reload_speed', 1.0)
            self.reloading = True
            self.reload_end_time = time.time() + reload_speed
            # Обнуляем боезапас при перезарядке
            self.current_ammo = 0

    def calculate_dps(self):
        current_time = time.time()
        recent_damage = [d for t, d in self.damage_history if current_time - t <= 1.0]
        self.damage_history[:] = [(t, d) for t, d in self.damage_history if current_time - t <= 1.0]
        return sum(recent_damage)

    def update_status_effects(self):
        # Обновление статусных эффектов на манекене или игроке
        pass

    def process_effect(self, effect, context_stats):
        effect_type = effect['type']
        try:
            if effect_type == 'increase_stat':
                stats = effect['stat']
                value = effect['value']
                if isinstance(stats, list):
                    for stat in stats:
                        context_stats[stat] = context_stats.get(stat, 0) + value
                else:
                    context_stats[stats] = context_stats.get(stats, 0) + value
            elif effect_type == 'decrease_stat':
                stats = effect['stat']
                value = effect['value']
                if isinstance(stats, list):
                    for stat in stats:
                        context_stats[stat] = context_stats.get(stat, 0) - value
                else:
                    context_stats[stats] = context_stats.get(stats, 0) - value
            elif effect_type == 'set_flag':
                flag = effect['flag']
                context_stats[flag] = effect['value']
            elif effect_type == 'conditional_effect':
                condition = effect['condition']
                if self.check_condition(condition, context_stats):
                    for conditional_effect in effect['effects']:
                        self.process_effect(conditional_effect, context_stats)
            elif effect_type == 'on_event':
                event = effect['event']
                if event not in self.event_effects:
                    self.event_effects[event] = []
                self.event_effects[event].append(effect['effects'])
            # Добавьте обработку других типов эффектов при необходимости
        except Exception as e:
            print(f"Ошибка при обработке эффекта '{effect_type}': {e}")

    def check_condition(self, condition, context_stats):
        try:
            safe_context = context_stats.copy()
            safe_context.setdefault('hp', self.current_hp)
            safe_context.setdefault('max_hp', self.max_hp)
            safe_context.setdefault('enemies_within_distance', self.enemies_within_distance)
            safe_context.setdefault('target_distance', self.target_distance)
            return eval(condition, {}, safe_context)
        except Exception as e:
            print(f"Ошибка в условии '{condition}': {e}")
            return False

    def create_set_data(self, set_name, set_id, set_description):
        if not set_name or not set_id:
            return False, "Название сета и ID сета должны быть заполнены."
        # Проверяем, что ID сета уникален
        existing_set = self.get_set_by_id(set_id)
        if existing_set:
            return False, f"Сет с ID '{set_id}' уже существует."
        new_set = {
            'name': set_name,
            'set_id': set_id,
            'description': set_description,
            # Здесь можно добавить дополнительные поля, такие как эффекты сета
        }
        self.sets_data.append(new_set)
        # Сохраняем обновлённые данные сетов
        self.save_sets_data()
        return True, f"Сет '{set_name}' успешно создан."

    def save_sets_data(self):
        data = {
            'items': self.items_data,
            'sets': self.sets_data,
            'multipliers': self.multipliers
        }
        with open('armor_sets.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    def get_set_by_id(self, set_id):
        for game_set in self.sets_data:
            if game_set['set_id'] == set_id:
                return game_set
        return None

    def apply_effects(self, effects, context_stats):
        for effect in effects:
            self.process_effect(effect, context_stats)

    def try_trigger_event(self, event_name):
        if event_name in self.event_effects:
            for effects in self.event_effects[event_name]:
                self.apply_effects(effects, self.player.stats)
            # После применения эффектов необходимо обновить статистику игрока
            self.player.recalculate_stats()

    def create_item_instance(self, item_data):
        return Item(item_data, self.base_stats, self.calibration_bonuses)

    def create_item_instance_by_id(self, item_id):
        item_data = next((item for item in self.items_data if item['id'] == item_id), None)
        if item_data:
            return self.create_item_instance(item_data)
        else:
            print(f"Предмет с id '{item_id}' не найден.")
            return None

    def delete_item(self, item):
        try:
            self.items_data.remove(item)
            self.save_items_and_sets()
            return True, f"Предмет '{item['name']}' удалён."
        except ValueError:
            return False, "Ошибка при удалении предмета."

