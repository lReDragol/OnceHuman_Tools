# config_manager.py

import json
import dearpygui.dearpygui as dpg
from tkinter import filedialog
import tkinter as tk

class ConfigManager:
    def __init__(self, context, player, update_item_stats_callback, open_mod_selection_callback, update_stats_display_callback):
        self.context = context
        self.player = player
        self.update_item_stats_callback = update_item_stats_callback
        self.open_mod_selection_callback = open_mod_selection_callback
        self.update_stats_display_callback = update_stats_display_callback

    def save_config(self):
        config_data = {
            'parameters': self.get_parameters(),
            'equipped_items': self.get_equipped_items(),
            'equipped_mods': self.get_equipped_mods(),
            'player_stats': self.player.base_stats,
            'context_stats': {
                'enemies_within_distance': self.context.enemies_within_distance,
                'target_distance': self.context.target_distance,
                'selected_status': self.context.selected_status,
                'enemy_type': self.context.enemy_type
            }
        }
        # Открываем диалог сохранения файла
        file_path = self.save_file_dialog()
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
            print(f"Конфигурация сохранена в {file_path}")

    def load_config(self):
        # Открываем диалог выбора файла
        file_path = self.open_file_dialog()
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            self.apply_config(config_data)
            print(f"Конфигурация загружена из {file_path}")

    def get_parameters(self):
        parameters = {}
        # Получаем значения всех параметров из GUI
        parameter_tags = [
            "base_damage_input", "crit_chance_input", "crit_dmg_input", "magazine_capacity_input",
            "fire_rate_input", "reload_speed_input", "status_damage_bonus_input",
            "weakspot_damage_bonus_input", "damage_bonus_normal_input", "damage_bonus_elite_input",
            "damage_bonus_boss_input", "hp_input", "psi_intensity_input", "contamination_resistance_input",
            "enemies_within_distance_input", "target_distance_input"
        ]
        for tag in parameter_tags:
            if dpg.does_item_exist(tag):
                parameters[tag] = dpg.get_value(tag)
        return parameters

    def get_equipped_items(self):
        equipped_items = {}
        for item_type, item in self.player.equipped_items.items():
            equipped_items[item_type] = {
                'id': item.id,
                'name': item.name,
                'star': item.star,
                'level': item.level,
                'calibration': item.calibration
            }
        return equipped_items

    def get_equipped_mods(self):
        equipped_mods = self.player.equipped_mods.copy()
        return equipped_mods

    def apply_config(self, config_data):
        # Устанавливаем параметры
        parameters = config_data.get('parameters', {})
        for tag, value in parameters.items():
            if dpg.does_item_exist(tag):
                dpg.set_value(tag, value)
                self.context.update_parameter(tag, value)

        # Устанавливаем контекстные параметры
        context_stats = config_data.get('context_stats', {})
        self.context.enemies_within_distance = context_stats.get('enemies_within_distance', 0)
        self.context.target_distance = context_stats.get('target_distance', 0)
        self.context.selected_status = context_stats.get('selected_status')
        self.context.enemy_type = context_stats.get('enemy_type', 'Обычный')
        if dpg.does_item_exist("status_combo"):
            dpg.set_value("status_combo", self.context.selected_status)
        if dpg.does_item_exist("enemy_type_combo"):
            dpg.set_value("enemy_type_combo", self.context.enemy_type)

        # Устанавливаем базовые статы игрока
        player_stats = config_data.get('player_stats', {})
        self.player.base_stats.update(player_stats)
        self.player.recalculate_stats()

        # Устанавливаем экипированные предметы
        equipped_items = config_data.get('equipped_items', {})
        for item_type, item_data in equipped_items.items():
            item_instance = self.context.create_item_instance_by_id(item_data['id'])
            if item_instance:
                item_instance.star = item_data.get('star', 1)
                item_instance.level = item_data.get('level', 1)
                item_instance.calibration = item_data.get('calibration', 0)
                self.player.equip_item(item_instance)
                # Обновляем GUI для этого предмета
                button_tag = f"{item_type}_item_selector"
                dpg.configure_item(button_tag, label=f"Изменить {item_type.capitalize()}")
                group_tag = f"{item_type}_upgrade_group"
                if dpg.does_item_exist(group_tag):
                    dpg.delete_item(group_tag)
                with dpg.group(horizontal=True, tag=group_tag, parent=f"{item_type}_item_mod_group"):
                    with dpg.group():
                        dpg.add_text(f"{item_instance.name} ({item_type.capitalize()})")
                        dpg.add_slider_int(label="Количество звёзд", min_value=1, max_value=item_instance.max_stars,
                                           default_value=item_instance.star, callback=self.update_item_stats_callback,
                                           user_data={'item': item_instance, 'item_type': item_type}, tag=f"{item_type}_star_slider")
                        dpg.add_slider_int(label="Уровень", min_value=1, max_value=5,
                                           default_value=item_instance.level, callback=self.update_item_stats_callback,
                                           user_data={'item': item_instance, 'item_type': item_type}, tag=f"{item_type}_level_slider")
                        dpg.add_slider_int(label="Уровень калибровки", min_value=0, max_value=item_instance.get_max_calibration(),
                                           default_value=item_instance.calibration, callback=self.update_item_stats_callback,
                                           user_data={'item': item_instance, 'item_type': item_type}, tag=f"{item_type}_calibration_slider")
                # Обновляем моды для предмета
                mod_button_tag = f"{item_type}_mod_selector"
                if dpg.does_item_exist(mod_button_tag):
                    dpg.delete_item(mod_button_tag)
                dpg.add_button(label=f"Выберите мод для {item_type.capitalize()}", callback=self.open_mod_selection_callback,
                               user_data=item_type, tag=mod_button_tag, parent=f"{item_type}_item_mod_group")

        # Устанавливаем экипированные моды
        equipped_mods = config_data.get('equipped_mods', {})
        self.player.equipped_mods = equipped_mods
        # Необходимо обновить GUI для модов (если есть соответствующие функции)

        # Пересчитываем статистику игрока
        self.player.recalculate_stats()
        # Обновляем отображение статистики
        self.update_stats_display_callback()


    def save_file_dialog(self):
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        root.destroy()
        return file_path

    def open_file_dialog(self):
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        root.destroy()
        return file_path

    def update_item_stats_from_gui(self, sender, app_data, user_data):
        item = user_data['item']
        item_type = user_data['item_type']
        star_slider_tag = f"{item_type}_star_slider"
        level_slider_tag = f"{item_type}_level_slider"
        calibration_slider_tag = f"{item_type}_calibration_slider"
        new_star = dpg.get_value(star_slider_tag)
        new_level = dpg.get_value(level_slider_tag)
        new_calibration = dpg.get_value(calibration_slider_tag)
        item.star = new_star
        item.level = new_level
        item.calibration = new_calibration
        self.player.equip_item(item)
        max_calibration = item.get_max_calibration()
        dpg.configure_item(calibration_slider_tag, max_value=max_calibration)
        if new_calibration > max_calibration:
            new_calibration = max_calibration
            dpg.set_value(calibration_slider_tag, new_calibration)
            item.calibration = new_calibration
        self.context.update_stats_display()

    def open_mod_selection(self, sender, app_data, user_data):
        item_type = user_data
        self.context.populate_mod_selection_list(item_type)
        dpg.configure_item("mod_selection_window", show=True)

