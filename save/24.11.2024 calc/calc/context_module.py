# context_module.py

import json
import time
import math
import random
import dearpygui.dearpygui as dpg
from player import Item, Mannequin
from mechanics import Weapon, MechanicsProcessor
import logging

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

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
        damage *= (1 + total_bonus)
        logging.debug(f"Weapon and status bonus applied. Total bonus: {total_bonus * 100}%. Damage now: {damage}")
        return damage

    def apply_enemy_type_bonus(self, damage):
        damage_bonus_vs_enemy = 0
        enemy_type = self.context.mannequin.enemy_type
        if enemy_type == 'Обычный':
            damage_bonus_vs_enemy = self.player.stats.get('damage_bonus_normal', 0)
        elif enemy_type == 'Элитный':
            damage_bonus_vs_enemy = self.player.stats.get('damage_bonus_elite', 0)
        elif enemy_type == 'Босс':
            damage_bonus_vs_enemy = self.player.stats.get('damage_bonus_boss', 0)
        damage *= (1 + damage_bonus_vs_enemy / 100.0)
        logging.debug(f"Enemy type bonus applied. Bonus: {damage_bonus_vs_enemy}%. Damage now: {damage}")
        return damage

    def apply_crit_bonus(self, damage):
        crit_rate = self.player.stats.get('crit_rate_percent', 0)
        is_crit = random.uniform(0, 100) <= crit_rate
        self.context.last_hit_crit = is_crit
        logging.debug(f"Critical hit rolled: {'Yes' if is_crit else 'No'}.")
        if is_crit:
            crit_damage_bonus = self.player.stats.get('crit_damage_percent', 0)
            damage *= (1 + crit_damage_bonus / 100.0)
            logging.debug(f"Critical damage bonus applied: {crit_damage_bonus}%. Damage now: {damage}")
        return is_crit, damage

    def apply_weakspot_bonus(self, damage):
        weakspot_bonus = self.player.stats.get('weakspot_damage_percent', 0)
        damage *= (1 + weakspot_bonus / 100.0)
        self.context.last_hit_weakspot = True
        logging.debug(f"Weakspot damage bonus applied: {weakspot_bonus}%. Damage now: {damage}")
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
        self.last_fire_time = 0.0
        # Здоровье
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
        self.status_stack_counts = {}
        self.max_fire_stacks = 16
        self.stats_display_timer = 0.0
        self.selected_status = None
        self.event_effects = {}
        self.counters = {}
        # Загрузка данных
        items_and_sets = self.load_items_and_sets()
        self.items_data = items_and_sets['items']
        self.sets_data = items_and_sets['sets']
        self.multipliers = items_and_sets.get('multipliers', {})
        self.mods_data = self.load_mods()
        self.base_stats_data = self.load_all_armor_stats()
        self.base_stats = self.base_stats_data.get('items', {})
        self.calibration_bonuses = self.base_stats_data.get('calibration_bonuses', {})
        self.weapons_data = self.load_weapons()

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
            'damage_per_projectile', 'crit_rate_percent', 'crit_damage_percent', 'weapon_damage_percent',
            'status_damage_percent', 'movement_speed_percent',
            'elemental_damage_percent', 'weakspot_damage_percent', 'reload_time_seconds',
            'magazine_capacity', 'damage_bonus_normal', 'damage_bonus_elite',
            'damage_bonus_boss', 'pollution_resist', 'psi_intensity', 'fire_rate',
            'projectiles_per_shot'
        ]
        self.flags_options = ['can_deal_weakspot_damage', 'is_invincible', 'has_super_armor']
        self.conditions_options = [
            'hp / max_hp > 0.5', 'enemies_within_distance == 0', 'is_crit', 'is_weak_spot',
            'target_is_marked', 'hp / max_hp < 0.3'
        ]
        # Переменные для отображения урона
        self.last_damage_dealt = 0
        self.last_hit_weakspot = False
        self.last_hit_crit = False
        self.enemy_type = 'Обычный'
        self.last_shot_mouse_pos = (0, 0)
        # Создаём экземпляр DamageCalculator
        self.damage_calculator = DamageCalculator(self.player, self)
        # Создаём экземпляр MechanicsProcessor
        self.mechanics_processor = MechanicsProcessor(self)
        self.mannequin = Mannequin()
        self.last_update_time = time.time()

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
                for game_set in data.get('sets', []):
                    game_set.setdefault('description', '')
                return data
        except FileNotFoundError:
            return {
                'items': [],
                'sets': [],
                'multipliers': {}
            }

    def load_weapons(self):
        try:
            with open('weapon_list.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('weapons', [])
        except FileNotFoundError:
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
        elif parameter == "magazine_capacity_input":
            self.player.base_stats['magazine_capacity'] = value
        elif parameter == "fire_rate_input":
            self.player.base_stats['fire_rate'] = value
        elif parameter == "reload_speed_input":
            self.player.base_stats['reload_time_seconds'] = value
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
        self.player.recalculate_stats()
        self.current_ammo = self.player.stats.get('magazine_capacity', 0)
        self.update_max_hp()

    def update_max_hp(self):
        self.bonus_hp = self.player.stats.get('hp', 0)
        self.max_hp = self.base_hp + self.bonus_hp
        logging.debug(f"Updated max HP: {self.max_hp}")

    def get_stats_display_text(self, player):
        stats_text = "Текущие параметры персонажа:\n\n"
        stats_text += f"HP манекена: {self.mannequin.current_hp}/{self.mannequin.max_hp}\n"
        stats_text += f"Статус манекена: {self.mannequin.status}\n"
        stats_text += f"Тип врага манекена: {self.mannequin.enemy_type}\n"
        if self.mannequin.effects:
            stats_text += "Эффекты на манекене:\n"
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
            stats_text += f"{stat}: {value}\n"
        stats_text += "\nЭкипированные предметы:\n"
        for item_type, item in player.equipped_items.items():
            stats_text += f"{item.name} ({item_type.capitalize()}): Звёзд: {item.star}, Уровень: {item.level}, Калибровка: {item.calibration}\n"
            item_stats = item.get_stats()
            for stat_name, stat_value in item_stats.items():
                stats_text += f"  {stat_name}: {stat_value}\n"
        if player.weapon:
            stats_text += f"\nОружие: {player.weapon.name}\n"
            for stat_name, stat_value in player.weapon.get_stats().items():
                stats_text += f"  {stat_name}: {stat_value}\n"
        if self.mannequin_status_effects:
            stats_text += "\nСтатусные эффекты:\n"
            for key, value in self.mannequin_status_effects.items():
                stats_text += f"{key}: {value}\n"
        return stats_text

    def initialize(self):
        self.update_max_hp()
        self.current_hp = self.max_hp
        self.current_ammo = self.player.stats.get('magazine_capacity', 0)

    def update(self):
        # Обновляем статусные эффекты манекена
        self.mannequin.update_effects(delta_time=time.time() - self.last_update_time)
        self.last_update_time = time.time()
        # Обновляем статусные эффекты
        self.update_status_effects()
        # Обрабатываем перезарядку
        if self.reloading and time.time() >= self.reload_end_time:
            self.reloading = False
            self.current_ammo = self.player.stats.get('magazine_capacity', 0)
            logging.info(f"Reload complete. Ammo replenished to {self.current_ammo}")
        # Рассчитываем текущий DPS
        self.dps = self.calculate_dps()

    def update_dps_display(self):
        dps_text = f"DPS: {int(self.context.dps)}    Total DMG: {int(self.context.total_damage)}"
        dpg.set_value("dps_text", dps_text)
        ammo_text = f"Патроны: {self.current_ammo}/{self.player.stats.get('magazine_capacity', 0)}"
        dpg.set_value("ammo_text", ammo_text)

    def update_damage_layer(self):
        current_time = time.time()
        for item in self.scheduled_deletions[:]:
            elapsed = current_time - item['start_time']
            if elapsed > item['duration']:
                try:
                    dpg.delete_item(item['id'])
                    logging.debug(f"Damage text {item['id']} removed after {elapsed} seconds.")
                except Exception as e:
                    logging.error(f"Error deleting damage text {item['id']}: {e}")
                self.scheduled_deletions.remove(item)
            else:
                # Обновление позиции
                # Используем фиксированный шаг времени, например, 1/60 секунды
                dx = item['velocity'][0] * (1 / 60)
                dy = item['velocity'][1] * (1 / 60)
                new_pos = [
                    item['start_pos'][0] + dx,
                    item['start_pos'][1] + dy
                ]
                # Обновление цвета с затуханием
                alpha = max(0, int(255 * (1 - elapsed / item['duration'])))
                color = item['color'][:3] + [alpha]
                try:
                    dpg.configure_item(item['id'], pos=new_pos, color=color)
                    # Обновляем стартовую позицию для следующего кадра
                    item['start_pos'] = new_pos
                    # logging.debug(f"Damage text {item['id']} moved to {new_pos} with alpha {alpha}.")
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
                self.last_fire_time = current_time
                # Рассчитываем урон
                projectiles_per_shot = int(self.player.weapon.get_stats().get('projectiles_per_shot', 1))
                total_shot_damage = 0
                damage_list = []
                for _ in range(projectiles_per_shot):
                    # Для каждого снаряда
                    # Получаем текущую позицию мыши
                    current_mouse_pos = dpg.get_mouse_pos(local=False)
                    self.last_shot_mouse_pos = current_mouse_pos
                    # Симулируем попадание снаряда с учётом разброса
                    hit_pos = self.simulate_projectile_hit(current_mouse_pos)
                    # Определяем, было ли попадание в слабое место
                    weakspot_hit = self.is_weakspot_hit(hit_pos)
                    damage, is_crit = self.damage_calculator.calculate_damage_per_projectile(weakspot_hit)
                    total_shot_damage += damage
                    damage_list.append((damage, hit_pos, is_crit, weakspot_hit))
                self.total_damage += total_shot_damage
                self.damage_history.append((current_time, total_shot_damage))
                # Отображаем нанесённый урон
                if self.mannequin.show_unified_shotgun_damage:
                    # Отображаем суммарный урон в центре зоны
                    center_pos = self.get_center_of_hit_area()
                    self.display_damage_number(total_shot_damage, center_pos, any(d[2] for d in damage_list), any(d[3] for d in damage_list))
                else:
                    for damage, hit_pos, is_crit, weakspot_hit in damage_list:
                        self.display_damage_number(damage, hit_pos, is_crit, weakspot_hit)
                # Обновляем состояние манекена
                self.mannequin.receive_damage(total_shot_damage)
                # Обработка событий
                self.process_hit(any(d[2] for d in damage_list), any(d[3] for d in damage_list))
            else:
                logging.debug("Cannot fire yet, still in cooldown.")

    def get_center_of_hit_area(self):
        # Возвращает центр области попадания
        normal_zone = {
            'left': 90,
            'right': 210,
            'top': 80,
            'bottom': 320
        }
        x_center = (normal_zone['left'] + normal_zone['right']) / 2
        y_center = (normal_zone['top'] + normal_zone['bottom']) / 2
        window_pos = dpg.get_item_rect_min("damage_layer")
        return (window_pos[0] + x_center, window_pos[1] + y_center)

    def process_hit(self, is_crit, is_weakspot):
        self.mechanics_processor.process_weapon_event('hit_target', is_crit=is_crit, is_weakspot=is_weakspot)
        if is_crit:
            self.mechanics_processor.process_weapon_event('crit_hit')
        if is_weakspot:
            self.mechanics_processor.process_weapon_event('weakspot_hit')

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
        if ((normal_zone['left'] <= local_x <= normal_zone['right'] and normal_zone['top'] <= local_y <= normal_zone['bottom']) or
                (weakspot_rect['left'] <= local_x <= weakspot_rect['right'] and weakspot_rect['top'] <= local_y <= weakspot_rect['bottom'])):
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
        if weakspot_rect['left'] <= local_x <= weakspot_rect['right'] and weakspot_rect['top'] <= local_y <= weakspot_rect['bottom']:
            return True
        else:
            return False

    def reload_weapon(self):
        if not self.reloading:
            reload_time = self.player.stats.get('reload_time_seconds', 1.0)
            self.reloading = True
            self.reload_end_time = time.time() + reload_time
            self.current_ammo = 0
            logging.info(f"Reloading weapon. It will take {reload_time} seconds.")

    def calculate_dps(self):
        current_time = time.time()
        recent_damage = [d for t, d in self.damage_history if current_time - t <= 1.0]
        self.damage_history[:] = [(t, d) for t, d in self.damage_history if current_time - t <= 1.0]
        return sum(recent_damage)

    def update_status_effects(self):
        current_time = time.time()
        expired_effects = []
        for status, end_time in self.mannequin_status_effects.items():
            if current_time >= end_time:
                expired_effects.append(status)
        for status in expired_effects:
            del self.mannequin_status_effects[status]
            logging.debug(f"Status effect '{status}' expired.")

    def simulate_projectile_hit(self, mouse_pos):
        # Генерируем отклонение для дробинок
        spread_radius = 15  # Радиус разброса в пикселях
        angle = random.uniform(0, 2 * math.pi)
        radius = random.uniform(0, spread_radius)
        offset_x = radius * math.cos(angle)
        offset_y = radius * math.sin(angle)
        hit_pos = (mouse_pos[0] + offset_x, mouse_pos[1] + offset_y)
        logging.debug(f"Simulated projectile hit at {hit_pos}")
        return hit_pos

    def display_damage_number(self, damage, hit_pos, is_crit, weakspot_hit):
        window_pos = dpg.get_item_rect_min("damage_layer")
        local_x = hit_pos[0] - window_pos[0]
        local_y = hit_pos[1] - window_pos[1]
        damage_text_id = dpg.generate_uuid()
        # Определяем цвет в зависимости от типа попадания
        if weakspot_hit and is_crit:
            color = [0, 255, 0, 255]  # Зелёный для критического попадания по слабой точке
        elif is_crit:
            color = [255, 165, 0, 255]  # Оранжевый для критического попадания
        elif weakspot_hit:
            color = [255, 0, 0, 255]  # Красный для попадания по слабой точке
        else:
            color = [255, 255, 255, 255]  # Белый для обычных попаданий
        current_time = time.time()
        dpg.draw_text(
            pos=[local_x, local_y],
            text=str(int(damage)),
            color=color,
            size=20,
            parent="damage_layer",
            tag=damage_text_id
        )
        # Добавляем в список для удаления с параметрами анимации
        angle = random.uniform(math.radians(75), math.radians(105))
        speed = 100  # Скорость анимации
        vx = speed * math.cos(angle)
        vy = speed * math.sin(angle)  # Положительное значение, чтобы двигаться вверх
        self.scheduled_deletions.append({
            'id': damage_text_id,
            'start_time': current_time,
            'duration': 1.0,  # Длительность анимации в секундах
            'start_pos': [local_x, local_y],
            'velocity': (vx, -vy),  # Отрицательное значение y для движения вверх
            'color': color
        })
        # Логируем нанесённый урон
        logging.info(f"Damage dealt: {damage}, Crit: {is_crit}, Weakspot: {weakspot_hit}")

    def update_damage_layer(self):
        current_time = time.time()
        for item in self.scheduled_deletions[:]:
            elapsed = current_time - item['start_time']
            if elapsed > item['duration']:
                try:
                    dpg.delete_item(item['id'])
                    logging.debug(f"Damage text {item['id']} removed after {elapsed} seconds.")
                except Exception as e:
                    logging.error(f"Error deleting damage text {item['id']}: {e}")
                self.scheduled_deletions.remove(item)
            else:
                # Обновление позиции
                # Используем фиксированный шаг времени, например, 1/60 секунды
                dx = item['velocity'][0] * (1 / 60)
                dy = item['velocity'][1] * (1 / 60)
                new_pos = [
                    item['start_pos'][0] + dx,
                    item['start_pos'][1] + dy
                ]
                # Обновление цвета с затуханием
                alpha = max(0, int(255 * (1 - elapsed / item['duration'])))
                color = item['color'][:3] + [alpha]
                try:
                    dpg.configure_item(item['id'], pos=new_pos, color=color)
                    # Обновляем стартовую позицию для следующего кадра
                    item['start_pos'] = new_pos
                    # logging.debug(f"Damage text {item['id']} moved to {new_pos} with alpha {alpha}.")
                except Exception as e:
                    logging.error(f"Error updating damage text {item['id']}: {e}")

    def create_weapon_instance(self, weapon_data):
        weapon = Weapon(weapon_data)
        return weapon

    def create_item_instance(self, item_data):
        item = Item(item_data, self.base_stats, self.calibration_bonuses)
        return item

    def get_set_by_id(self, set_id):
        for game_set in self.sets_data:
            if 'id' not in game_set:
                continue
            if game_set['id'] == set_id:
                return game_set
        return None
