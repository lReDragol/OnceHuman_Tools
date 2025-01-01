import json
import time
import math
import random
import os
import dearpygui.dearpygui as dpg
from .player import Item, Mannequin, Player
from .mechanics import Weapon, MechanicsProcessor
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

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
            value = int(value)
            stats_text += f"{stat}: {value}\n"
        stats_text += "\nЭкипированные предметы:\n"
        for item_type, item in player.equipped_items.items():
            stats_text += (f"{item.name} ({item_type.capitalize()}): "
                           f"Звёзд: {item.star}, Уровень: {item.level}, "
                           f"Калибровка: {item.calibration}\n")
            item_stats = item.get_stats()
            for stat_name, stat_value in item_stats.items():
                stats_text += f"  {stat_name}: {stat_value}\n"
        if player.weapon:
            stats_text += f"\nОружие: {player.weapon.name}\n"
            for stat_name, stat_value in player.weapon.get_stats().items():
                stats_text += f"  {stat_name}: {stat_value}\n"
        if self.mannequin_status_effects:
            stats_text += "\nСтатусные эффекты:\n"
            for key, val in self.mannequin_status_effects.items():
                stats_text += f"{key}: {val}\n"
        return stats_text

    def initialize(self):
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
        self.player.update_active_stat_bonuses()  # <<<

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
                self.last_fire_time = current_time
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

    def get_center_of_hit_area(self):
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
            if status in self.mannequin.effects:
                del self.mannequin.effects[status]
            logging.debug(f"Status effect '{status}' expired.")

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
            else:
                dpg.draw_rectangle(pmin=[icon_x, icon_y], pmax=[icon_x + 10, icon_y + 10],
                                   color=[255, 255, 255, 255],
                                   fill=[255, 255, 255, 255],
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

    def get_set_by_id(self, set_id):
        for game_set in self.sets_data:
            if 'id' not in game_set:
                continue
            if game_set['id'] == set_id:
                return game_set
        return None

    def apply_status(self, status, duration, **kwargs):
        self.mannequin.apply_status(status, duration, **kwargs)
        end_time = time.time() + duration
        self.mannequin_status_effects[status] = end_time
        logging.debug(f"Status {status} applied for {duration} seconds.")
        self.mannequin.effects[status] = True

    def remove_buff(self, buff_name):
        if buff_name in self.buffs:
            buff_data = self.buffs[buff_name]
            stat_bonuses = buff_data.get('stat_bonuses', {})
            for stat, val in stat_bonuses.items():
                # Безопасно уменьшаем стат (если нет ключа, пропускаем)
                if stat in self.player.stats:
                    self.player.stats[stat] -= val
            del self.buffs[buff_name]
            logging.info(f"Buff {buff_name} removed.")

    def trigger_ability(self, ability_name, **kwargs):
        ability_lower = ability_name.lower()
        logging.info(f"Triggered ability: {ability_name} with {kwargs}")
        if ability_lower == 'unstable_bomber':
            psi_intensity = self.player.stats.get('psi_intensity', 100)
            dmg = psi_intensity
            self.apply_direct_damage(dmg, is_crit=False, weakspot_hit=False, ability_name='unstable_bomber')
            self.counters['shots_towards_bomber_trigger'] = 0

    def check_status_on_target(self, status_to_check):
        return status_to_check in self.mannequin_status_effects

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

    def apply_temporary_stat_bonus(self, stat, value, duration, max_stacks=None):
        self.player.apply_stat_bonus(stat, value, duration, max_stacks)

    def gain_stacks(self, stack_type, count):
        self.stacks[stack_type] = self.stacks.get(stack_type, 0) + count
        logging.debug(f"Stacks {stack_type} gained {count}, total: {self.stacks[stack_type]}")

    def reduce_stacks(self, stack_type, value):
        current = self.stacks.get(stack_type, 0)
        new_val = max(0, current - value)
        self.stacks[stack_type] = new_val
        logging.debug(f"Stacks {stack_type} reduced by {value}, total: {new_val}")

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
        self.display_damage_number(damage, center_pos, is_crit, weakspot_hit, ability_name=ability_name)

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
        filename = mod_name_key + '.png'
        full_path = os.path.join(folder, filename)

        if os.path.isfile(full_path):
            # Загрузим и зарегистрируем текстуру
            width, height, channels, data = dpg.load_image(full_path)
            with dpg.texture_registry():
                texture_id = dpg.add_static_texture(width, height, data)
            return texture_id
        else:
            return None  # не нашли, будет fallback

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
