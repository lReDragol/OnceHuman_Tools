import dearpygui.dearpygui as dpg
import os
import json
import shutil
import logging
from tkinter import filedialog
import tkinter as tk

from data.menu.calc.player import Player
from data.menu.calc.context_module import Context
from data.menu.calc.config_manager import ConfigManager

logging.basicConfig(level=logging.DEBUG)


class CalcAndModTab:
    def __init__(self, main_app):
        self.main_app = main_app
        self.player = Player()
        self.context = Context(self.player)

        self.config_manager = ConfigManager(
            self.context,
            self.player,
            self.dummy_update_item_stats,
            self.open_mod_selection,
            self.dummy_update_stats_display
        )

        self.default_font = None
        self.is_editable = True
        self.mod_images = {}
        self.item_images = {}
        self.weapon_images = {}
        self.weapon_type_icons = {}

        self.mouse_pressed = False
        self.scheduled_deletions = []
        self.last_click_pos = (0, 0)
        self.last_damage_text_time = 0

        # Указываем контексту эффекты и т. д.
        self.context.available_effects = ['Горение', 'Заморозка']
        self.context.damage_text_settings.update({
            'speed': 100,
            'fade_delay': 1.0,
            'angle_min': 45,
            'angle_max': 135,
            'crit_color': [255, 165, 0, 255],
            'weakspot_color': [255, 0, 0, 255],
            'crit_weakspot_color': [0, 255, 0, 255],
            'normal_color': [255, 255, 255, 255]
        })

        self.setup_fonts()
        self.load_images()
        self.build_ui()

    def dummy_update_item_stats(self):
        pass

    def dummy_open_mod_selection(self):
        pass

    def dummy_update_stats_display(self):
        pass

    def get_target_image_path(self):
        return os.path.join("data", "icons", "target_image.png")

    def open_mod_selection(self, sender, app_data, user_data):
        if hasattr(self.context, "populate_mod_selection_list"):
            self.context.populate_mod_selection_list(user_data)
        else:
            dpg.delete_item("mod_selection_list", children_only=True)
            dpg.add_text("Пока не реализовано или список пуст...", parent="mod_selection_list")

        dpg.configure_item("mod_selection_window", show=True)

    def setup_fonts(self):
        with dpg.font_registry():
            font_path = "C:\\Windows\\Fonts\\arial.ttf"
            if os.path.exists(font_path):
                with dpg.font(font_path, 15) as self.default_font:
                    dpg.add_font_range_hint(dpg.mvFontRangeHint_Cyrillic)

    def create_default_texture(self):
        width, height = 85, 85
        data = [255, 255, 255, 255] * width * height
        with dpg.texture_registry():
            texture_id = dpg.add_static_texture(width, height, data)
        return texture_id

    def load_mod_images(self):
        mod_images = {}
        mod_images['default'] = self.create_default_texture()
        for category_key, mod_key in self.context.category_key_mapping.items():
            category_folder = os.path.join('data', 'icons', 'mods', mod_key)
            if os.path.exists(category_folder):
                mod_images[mod_key] = {}
                for filename in os.listdir(category_folder):
                    if filename.endswith('.png'):
                        mod_name_key = os.path.splitext(filename)[0].lower().replace(' ', '_')
                        image_path = os.path.join(category_folder, filename)
                        width, height, channels, data = dpg.load_image(image_path)
                        with dpg.texture_registry():
                            texture_id = dpg.add_static_texture(width, height, data)
                        mod_images[mod_key][mod_name_key] = texture_id
        return mod_images

    def load_item_images(self):
        item_images = {}
        item_images['default'] = self.create_default_texture()
        item_icons_folder = os.path.join('data', 'icons', 'armor')
        if os.path.exists(item_icons_folder):
            for root, dirs, files in os.walk(item_icons_folder):
                for filename in files:
                    if filename.endswith('.png'):
                        item_id = os.path.splitext(filename)[0]
                        image_path = os.path.join(root, filename)
                        try:
                            width, height, channels, data = dpg.load_image(image_path)
                            with dpg.texture_registry():
                                texture_id = dpg.add_static_texture(width, height, data)
                            item_images[item_id] = texture_id
                        except Exception as e:
                            print(f"Ошибка при загрузке изображения {image_path}: {e}")
        return item_images

    def load_weapon_images(self):
        weapon_images = {}
        weapon_images['default'] = self.create_default_texture()
        weapon_icons_folder = os.path.join('data', 'icons', 'weapons')
        if not os.path.exists(weapon_icons_folder):
            os.makedirs(weapon_icons_folder)
        for root, dirs, files in os.walk(weapon_icons_folder):
            for filename in files:
                if filename.endswith('.png'):
                    weapon_id = os.path.splitext(filename)[0]
                    image_path = os.path.join(root, filename)
                    try:
                        width, height, channels, data = dpg.load_image(image_path)
                        with dpg.texture_registry():
                            texture_id = dpg.add_static_texture(width, height, data)
                        weapon_images[weapon_id] = texture_id
                    except Exception as e:
                        print(f"Ошибка при загрузке изображения {image_path}: {e}")
        return weapon_images

    def load_weapon_type_icons(self):
        type_icons = {}
        icons_folder = os.path.join('data', 'icons', 'menu_weapon_icons')
        if os.path.exists(icons_folder):
            for filename in os.listdir(icons_folder):
                if filename.endswith('.png'):
                    base_name = os.path.splitext(filename)[0].lower().replace(' ', '_')
                    if base_name.endswith('_icon'):
                        type_name = base_name[:-5]
                    else:
                        type_name = base_name
                    image_path = os.path.join(icons_folder, filename)
                    try:
                        width, height, channels, data = dpg.load_image(image_path)
                        with dpg.texture_registry():
                            texture_id = dpg.add_static_texture(width, height, data)
                        type_icons[type_name] = texture_id
                    except:
                        pass
        return type_icons

    def load_images(self):
        self.mod_images = self.load_mod_images()
        self.item_images = self.load_item_images()
        self.weapon_images = self.load_weapon_images()
        self.weapon_type_icons = self.load_weapon_type_icons()

    def build_ui(self):
        with dpg.group():
            with dpg.tab_bar():
                self.create_calc_tab()
                self.create_create_tab()
            dpg.add_button(label="Сохранить конфигурацию", callback=self.save_config_callback)
            dpg.add_button(label="Загрузить конфигурацию", callback=self.load_config_callback)

        self.create_item_selection_window()
        self.create_mod_selection_window()
        self.create_weapon_selection_window()
        self.create_error_modals()
        self.create_item_edit_window()

        self.initialize()

    def initialize(self):
        self.context.initialize()
        if self.default_font is not None:
            dpg.bind_font(self.default_font)
        self.player.recalculate_stats()
        if not self.context.mannequin.show_hotbar:
            if dpg.does_item_exist("hotbar_group"):
                dpg.configure_item("hotbar_group", show=False)

    def update(self):
        self.context.update()
        if self.context.mouse_pressed:
            self.context.try_fire_weapon()

        self.update_dps_display()
        self.context.update_damage_layer()
        self.update_stats_display()

        active_effects = list(self.context.mannequin.effects.keys())
        effects_str = ", ".join(active_effects) if active_effects else "Нет активных статусов"
        if dpg.does_item_exist("active_statuses_text"):
            dpg.set_value("active_statuses_text", f"Активные статусы: {effects_str}")

        self.draw_mannequin_hp_bar()

    def create_calc_tab(self):
        with dpg.tab(label="Calc"):
            with dpg.group(horizontal=True):
                self.create_parameters_section()
                self.create_combat_section()

    def create_create_tab(self):
        with dpg.tab(label="Create"):
            dpg.add_text("Выберите, что вы хотите создать:", color=[255, 255, 0])
            dpg.add_radio_button(items=["Мод", "Предмет", "Сет"], default_value="Мод", horizontal=True,
                                 callback=lambda s,a,u: self.toggle_creation_menu(a))

            with dpg.group(tag="mod_creation_group", show=True):
                self.create_mod_creation_section()

            with dpg.group(show=False, tag="item_creation_group"):
                self.create_item_creation_section()

            with dpg.group(show=False, tag="set_creation_group"):
                self.create_set_creation_section()

    def create_parameters_section(self):
        with dpg.child_window(width=600, height=760, horizontal_scrollbar=True):
            dpg.add_text("Параметры:")
            dpg.add_spacer(height=5)
            dpg.add_separator()
            dpg.add_spacer(height=5)
            self.create_parameters_table("Базовые характеристики:", [
                ("Урон (УРН):", 0, "base_damage_input", True),
                ("Пси-интенсивность:", 125, "psi_intensity_input", True),
                ("ОЗ (xp):", 700, "hp_input", True),
                ("Сопротивление загрязнению:", 15, "contamination_resistance_input", True)
            ])
            self.create_parameters_table("Боевые характеристики:", [
                ("Шанс крит. попадания %:", 0, "crit_chance_input", True),
                ("Крит. УРН +%:", 0, "crit_dmg_input", True),
                ("УРН уязвимостям %:", 0, "weakspot_damage_bonus_input", True),
                ("Бонус к УРН оружия %:", 0, "weapon_damage_bonus_input", True),
                ("Бонус к УРН статуса %:", 4, "status_damage_bonus_input", True),
                ("Бонус к УРН обычным %:", 0, "damage_bonus_normal_input", True),
                ("Бонус к УРН элиткам %:", 0, "damage_bonus_elite_input", True),
                ("Бонус к УРН против боссов %:", 0, "damage_bonus_boss_input", True),
                ("Скорость стрельбы (выстр./мин):", 0, "fire_rate_input", True),
                ("Емкость магазина:", 0, "magazine_capacity_input", True),
                ("Скорость перезарядки (сек):", 0, "reload_speed_input", True)
            ])
            self.create_parameters_table("Показатели защиты:", [
                ("Снижение УРН %:", 0, "damage_reduction_input", True),
                ("Сопротивление загрязнению:", 15, "resistance_to_pollution", True)
            ])
            dpg.add_input_int(label="Врагов в радиусе (м):", default_value=0,
                              tag="enemies_within_distance_input", width=100,
                              callback=self.on_parameter_change)
            dpg.add_text("Выбор оружия:", color=[255, 255, 255], bullet=True)
            with dpg.group(horizontal=True, tag="weapon_selection_group"):
                weapon = self.player.weapon
                if weapon:
                    weapon_id = weapon.id
                    texture_id = self.weapon_images.get(weapon_id, self.weapon_images['default'])
                    image_tag = "weapon_image"
                    dpg.add_image_button(texture_id, width=85, height=85,
                                         callback=self.open_weapon_selection,
                                         tag=image_tag)
                    with dpg.item_handler_registry(tag="weapon_item_handler") as handler_id:
                        dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Right, callback=self.open_weapon_config_window)
                    dpg.bind_item_handler_registry(image_tag, handler_id)
                else:
                    button_tag = "weapon_selector"
                    dpg.add_button(label="Выберите оружие", callback=self.open_weapon_selection, tag=button_tag)
            dpg.add_text("Выбор брони:", color=[255, 255, 255], bullet=True)
            with dpg.group(horizontal=True, tag="armor_selection_group"):
                armor_types = ['helmet', 'mask', 'top', 'gloves', 'pants', 'boots']
                for armor_type in armor_types:
                    parent_tag = f"{armor_type}_item_mod_group"
                    with dpg.group(tag=parent_tag):
                        item = self.player.equipped_items.get(armor_type)
                        if item:
                            item_id = item.id
                            texture_id = self.item_images.get(item_id, self.item_images['default'])
                            image_tag = f"{armor_type}_item_image"
                            dpg.add_image_button(texture_id, width=85, height=85,
                                                 callback=self.open_item_selection,
                                                 user_data=armor_type, tag=image_tag,
                                                 parent=parent_tag)
                            with dpg.item_handler_registry(tag=f"{armor_type}_item_handler") as handler_id:
                                dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Right,
                                                             callback=self.open_item_config_window,
                                                             user_data=armor_type)
                            dpg.bind_item_handler_registry(image_tag, handler_id)
                        else:
                            button_tag = f"{armor_type}_item_selector"
                            item_type_name = armor_type.capitalize()
                            dpg.add_button(label=f"{item_type_name}",
                                           callback=self.open_item_selection,
                                           user_data=armor_type,
                                           tag=button_tag)

    def create_parameters_table(self, title, params):
        with dpg.collapsing_header(label=title, default_open=False):
            with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                dpg.add_table_column()
                dpg.add_table_column()
                for label, default, tag, editable in params:
                    with dpg.table_row():
                        dpg.add_text(label)
                        dpg.add_input_int(default_value=default, min_value=0, max_value=9999999, step=0,
                                          width=100, callback=self.on_parameter_change,
                                          tag=tag, enabled=editable)
        dpg.add_spacer(height=5)
        dpg.add_separator()
        dpg.add_spacer(height=5)

    def create_combat_section(self):
        with dpg.child_window(width=600, height=760):
            with dpg.group(horizontal=False):
                dpg.add_spacer(height=10)
                dpg.add_text("DPS: 0    Total DMG: 0", color=[120, 219, 226], tag="dps_text")
                dpg.add_text("Патроны: 0/0", tag="ammo_text")

                target_img = self.get_target_image_path()
                if os.path.exists(target_img):
                    width_img, height_img, channels, data = dpg.load_image(target_img)
                else:
                    width_img, height_img = 300, 300
                    data = [255] * width_img * height_img * 4

                with dpg.texture_registry():
                    texture_id = dpg.add_static_texture(width_img, height_img, data)

                with dpg.drawlist(width=300, height=330, tag="damage_layer"):
                    dpg.draw_image(texture_id, pmin=[0, 30], pmax=[300, 330])
                    dpg.draw_rectangle(pmin=[90, 80], pmax=[210, 320],
                                       color=[0, 0, 255, 100], fill=[0, 0, 255, 50])
                    dpg.draw_rectangle(pmin=[130, 40], pmax=[170, 80],
                                       color=[255, 0, 0, 100], fill=[255, 0, 0, 50])
                    with dpg.draw_layer(tag="hp_bar_layer", parent="damage_layer"):
                        pass

                with dpg.item_handler_registry(tag="damage_layer_handlers") as handler_id:
                    dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Left, callback=self.mouse_down_callback)
                    dpg.add_item_deactivated_handler(callback=self.mouse_up_callback)
                    dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Right,
                                                 callback=self.open_mannequin_settings_window)
                dpg.bind_item_handler_registry("damage_layer", "damage_layer_handlers")

                with dpg.group(tag="hotbar_group"):
                    dpg.add_text("Активные статусы:", tag="active_statuses_text")

                dpg.add_text("", tag="stats_display_text")

    def on_parameter_change(self, sender, app_data, user_data):
        self.context.update_parameter(sender, app_data)
        self.update_stats_display()

    def open_item_selection(self, sender, app_data, user_data):
        item_type = user_data
        self.populate_item_selection_list(item_type)
        dpg.configure_item("item_selection_window", show=True)

    def populate_item_selection_list(self, item_type):
        dpg.delete_item("item_selection_list", children_only=True)
        items = [itm for itm in self.context.items_data if itm['type'] == item_type]
        dpg.add_button(label="Ничего/Убрать", callback=self.remove_item_from_slot,
                       user_data=item_type, parent="item_selection_list")
        with dpg.table(header_row=False, parent="item_selection_list"):
            dpg.add_table_column(width=160)
            dpg.add_table_column()
            for itm in items:
                item_name = itm['name']
                item_id = itm['id']
                texture_id = self.item_images.get(item_id, self.item_images['default'])
                with dpg.table_row():
                    dpg.add_image_button(texture_id, width=150, height=70,
                                         callback=self.select_item_for_slot,
                                         user_data={'item': itm, 'type': item_type})
                    dpg.add_button(label=item_name, callback=self.select_item_for_slot,
                                   user_data={'item': itm, 'type': item_type})

    def remove_item_from_slot(self, sender, app_data, user_data):
        item_type = user_data
        self.player.remove_item(item_type)
        image_tag = f"{item_type}_item_image"
        if dpg.does_item_exist(image_tag):
            dpg.delete_item(image_tag)
        mod_button_tag = f"{item_type}_mod_selector"
        if dpg.does_item_exist(mod_button_tag):
            dpg.delete_item(mod_button_tag)
        button_tag = f"{item_type}_item_selector"
        if dpg.does_item_exist(button_tag):
            dpg.delete_item(button_tag)
        item_type_name = item_type.capitalize()
        parent_tag = f"{item_type}_item_mod_group"
        dpg.add_button(label=item_type_name, callback=self.open_item_selection,
                       user_data=item_type, tag=button_tag, parent=parent_tag)
        dpg.configure_item("item_selection_window", show=False)
        self.update_stats_display()

    def select_item_for_slot(self, sender, app_data, user_data):
        try:
            item_data = user_data['item']
            item_type = user_data['type']
            item = self.context.create_item_instance(item_data)
            self.player.equip_item(item)
            image_tag = f"{item_type}_item_image"
            parent_tag = f"{item_type}_item_mod_group"
            if dpg.does_item_exist(image_tag):
                dpg.delete_item(image_tag)
            button_tag = f"{item_type}_item_selector"
            if dpg.does_item_exist(button_tag):
                dpg.delete_item(button_tag)
            texture_id = self.item_images.get(item.id, self.item_images['default'])
            dpg.add_image_button(texture_id, width=150, height=70, callback=self.open_item_selection,
                                 user_data=item_type, tag=image_tag, parent=parent_tag)
            handler_tag = f"{item_type}_item_handler"
            if dpg.does_item_exist(handler_tag):
                dpg.delete_item(handler_tag)
            with dpg.item_handler_registry(tag=handler_tag) as h:
                dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Right,
                                             callback=self.open_item_config_window,
                                             user_data=item_type)
            dpg.bind_item_handler_registry(image_tag, handler_tag)
            mod_button_tag = f"{item_type}_mod_selector"
            if dpg.does_item_exist(mod_button_tag):
                dpg.delete_item(mod_button_tag)
            dpg.add_button(label=f"Выберите мод для {item_type.capitalize()}",
                           callback=self.open_mod_selection,
                           user_data=item_type, tag=mod_button_tag,
                           parent=parent_tag)
            dpg.configure_item("item_selection_window", show=False)
            self.update_stats_display()
        except Exception as e:
            print(f"Ошибка при выборе предмета для слота: {e}")

    def open_item_config_window(self, sender, app_data, user_data):
        item_type = user_data
        item = self.player.equipped_items.get(item_type)
        if item:
            self.show_item_config_window(item, item_type)

    def show_item_config_window(self, item, item_type):
        window_tag = f"{item_type}_config_window"
        if dpg.does_item_exist(window_tag):
            dpg.delete_item(window_tag)
        window_width = 400
        window_height = 300
        main_window_pos = dpg.get_viewport_pos()
        main_window_width = dpg.get_viewport_width()
        main_window_height = dpg.get_viewport_height()
        x_pos = main_window_pos[0] + (main_window_width - window_width) / 2
        y_pos = main_window_pos[1] + (main_window_height - window_height) / 2 - 100
        with dpg.window(label=f"Настройка {item.name}", modal=True, show=True, tag=window_tag,
                        width=window_width, height=window_height, pos=(x_pos, y_pos)):
            dpg.add_text(f"{item.name} ({item_type.capitalize()})")
            item_stats = item.get_stats()
            for stat_name, stat_value in item_stats.items():
                dpg.add_text(f"{stat_name}: {stat_value}", wrap=380)
            dpg.add_slider_int(label="Количество звёзд", min_value=1, max_value=item.max_stars,
                               default_value=item.star, callback=self.update_item_stats,
                               user_data={'item': item, 'item_type': item_type},
                               tag=f"{item_type}_star_slider")
            dpg.add_slider_int(label="Уровень", min_value=1, max_value=5,
                               default_value=item.level, callback=self.update_item_stats,
                               user_data={'item': item, 'item_type': item_type},
                               tag=f"{item_type}_level_slider")
            dpg.add_slider_int(label="Уровень калибровки", min_value=0, max_value=item.get_max_calibration(),
                               default_value=item.calibration, callback=self.update_item_stats,
                               user_data={'item': item, 'item_type': item_type},
                               tag=f"{item_type}_calibration_slider")
            set_id = item.set_id
            if set_id:
                game_set = self.context.get_set_by_id(set_id)
                if game_set:
                    set_description = game_set.get('description', 'Описание сета отсутствует.')
                    dpg.add_separator()
                    dpg.add_text(f"Сет: {game_set['name']}")
                    dpg.add_text(set_description, wrap=380)
            dpg.add_button(label="Закрыть", callback=lambda: dpg.delete_item(window_tag))

    def update_item_stats(self, sender, app_data, user_data):
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
        self.update_stats_display()

    def update_stats_display(self):
        stats_text = self.context.get_stats_display_text(self.player)
        if dpg.does_item_exist("stats_display_text"):
            dpg.set_value("stats_display_text", stats_text)

    def open_weapon_selection(self, sender, app_data, user_data):
        self.populate_weapon_selection_list()
        dpg.configure_item("weapon_selection_window", show=True)

    def populate_weapon_selection_list(self):
        dpg.delete_item("weapon_selection_list", children_only=True)
        weapons = self.context.weapons_data
        weapons_by_type = {}
        for wdata in weapons:
            wtype = wdata.get('type', 'Unknown')
            wkey = wtype.lower().replace(' ', '_')
            if wkey not in weapons_by_type:
                weapons_by_type[wkey] = []
            weapons_by_type[wkey].append(wdata)
        dpg.add_button(label="Ничего/Убрать", callback=self.remove_weapon, parent="weapon_selection_list")
        with dpg.child_window(parent="weapon_selection_list", autosize_x=True, autosize_y=True):
            for wtype_key, ws in weapons_by_type.items():
                icon_texture = self.weapon_type_icons.get(wtype_key, self.create_default_texture())
                with dpg.group(horizontal=True):
                    dpg.add_image(icon_texture, width=25, height=25)
                    dpg.add_text(f"{wtype_key.replace('_',' ').title()}")
                with dpg.table(header_row=False):
                    dpg.add_table_column(width=160)
                    dpg.add_table_column()
                    for weapon_data in ws:
                        weapon_name = weapon_data['name']
                        weapon_id = weapon_data['id']
                        texture_id = self.weapon_images.get(weapon_id, self.weapon_images['default'])
                        with dpg.table_row():
                            dpg.add_image_button(texture_id, width=150, height=70,
                                                 callback=self.select_weapon, user_data=weapon_data)
                            dpg.add_button(label=weapon_name, callback=self.select_weapon, user_data=weapon_data)

    def remove_weapon(self, sender, app_data, user_data):
        self.player.remove_weapon()
        image_tag = "weapon_image"
        if dpg.does_item_exist(image_tag):
            dpg.delete_item(image_tag)
        button_tag = "weapon_selector"
        if dpg.does_item_exist(button_tag):
            dpg.delete_item(button_tag)
        parent_tag = "weapon_selection_group"
        dpg.add_button(label="Выберите оружие", callback=self.open_weapon_selection,
                       tag=button_tag, parent=parent_tag)
        dpg.configure_item("weapon_selection_window", show=False)
        self.update_stats_display()

    def select_weapon(self, sender, app_data, user_data):
        weapon_data = user_data
        weapon = self.context.create_weapon_instance(weapon_data)
        self.player.equip_weapon(weapon)
        self.player.recalculate_stats()
        self.context.current_ammo = self.player.stats.get('magazine_capacity', 0)
        image_tag = "weapon_image"
        parent_tag = "weapon_selection_group"
        if dpg.does_item_exist(image_tag):
            dpg.delete_item(image_tag)
        button_tag = "weapon_selector"
        if dpg.does_item_exist(button_tag):
            dpg.delete_item(button_tag)
        texture_id = self.weapon_images.get(weapon.id, self.weapon_images['default'])
        dpg.add_image_button(texture_id, width=150, height=70, callback=self.open_weapon_selection,
                             tag=image_tag, parent=parent_tag)
        handler_tag = "weapon_item_handler"
        if dpg.does_item_exist(handler_tag):
            dpg.delete_item(handler_tag)
        with dpg.item_handler_registry(tag=handler_tag) as h:
            dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Right,
                                         callback=self.open_weapon_config_window)
        dpg.bind_item_handler_registry(image_tag, handler_tag)
        dpg.configure_item("weapon_selection_window", show=False)
        self.update_stats_display()

    def open_weapon_config_window(self, sender, app_data, user_data=None):
        weapon = self.player.weapon
        if weapon:
            self.show_weapon_config_window(weapon)

    def show_weapon_config_window(self, weapon):
        window_tag = f"{weapon.id}_config_window"
        if dpg.does_item_exist(window_tag):
            dpg.delete_item(window_tag)
        window_width = 400
        window_height = 300
        main_window_pos = dpg.get_viewport_pos()
        main_window_width = dpg.get_viewport_width()
        main_window_height = dpg.get_viewport_height()
        x_pos = main_window_pos[0] + (main_window_width - window_width) / 2
        y_pos = main_window_pos[1] + (main_window_height - window_height) / 2 - 100
        with dpg.window(label=f"Настройка оружия {weapon.name}", modal=True, show=True, tag=window_tag,
                        width=window_width, height=window_height, pos=(x_pos, y_pos)):
            dpg.add_text(f"Оружие: {weapon.name}")
            star_slider_tag = f"{weapon.id}_star_slider"
            level_slider_tag = f"{weapon.id}_level_slider"
            calibration_slider_tag = f"{weapon.id}_calibration_slider"
            dpg.add_slider_int(label="Звёзды", min_value=1, max_value=6, default_value=weapon.star,
                               tag=star_slider_tag, callback=self.update_weapon_stats,
                               user_data={'weapon': weapon})
            dpg.add_slider_int(label="Уровень", min_value=1, max_value=5, default_value=weapon.level,
                               tag=level_slider_tag, callback=self.update_weapon_stats,
                               user_data={'weapon': weapon})
            dpg.add_slider_int(label="Калибровка", min_value=0, max_value=6, default_value=weapon.calibration,
                               tag=calibration_slider_tag, callback=self.update_weapon_stats,
                               user_data={'weapon': weapon})
            dpg.add_separator()
            dpg.add_text("Описание:")
            dpg.add_text(weapon.description, wrap=380)
            dpg.add_button(label="Закрыть", callback=lambda: dpg.delete_item(window_tag))

    def update_weapon_stats(self, sender, app_data, user_data):
        weapon = user_data['weapon']
        star_slider_tag = f"{weapon.id}_star_slider"
        level_slider_tag = f"{weapon.id}_level_slider"
        calibration_slider_tag = f"{weapon.id}_calibration_slider"
        new_star = dpg.get_value(star_slider_tag)
        new_level = dpg.get_value(level_slider_tag)
        new_calibration = dpg.get_value(calibration_slider_tag)
        weapon.star = new_star
        weapon.level = new_level
        weapon.calibration = new_calibration
        weapon.get_stats()
        self.player.equip_weapon(weapon)
        self.player.recalculate_stats()
        self.update_stats_display()

    def create_item_selection_window(self):
        with dpg.window(label="Выбор предмета", modal=True, show=False,
                        tag="item_selection_window", width=600, height=500):
            dpg.add_text("Выберите предмет:")
            dpg.add_child_window(tag="item_selection_list", autosize_x=True, autosize_y=True)
            dpg.add_button(label="Закрыть",
                           callback=lambda: dpg.configure_item("item_selection_window", show=False))

    def create_mod_selection_window(self):
        with dpg.window(label="Выбор мода", modal=True, show=False,
                        tag="mod_selection_window", width=600, height=500):
            dpg.add_text("Выберите мод:")
            dpg.add_child_window(tag="mod_selection_list", autosize_x=True, autosize_y=True)
            dpg.add_button(label="Закрыть",
                           callback=lambda: dpg.configure_item("mod_selection_window", show=False))

    def create_weapon_selection_window(self):
        with dpg.window(label="Выбор оружия", modal=True, show=False,
                        tag="weapon_selection_window", width=600, height=500):
            dpg.add_text("Выберите оружие:")
            dpg.add_child_window(tag="weapon_selection_list", autosize_x=True, autosize_y=True)
            dpg.add_button(label="Закрыть",
                           callback=lambda: dpg.configure_item("weapon_selection_window", show=False))

    def create_error_modals(self):
        self.create_error_modal("error_modal_effect", "Пожалуйста, заполните все необходимые поля эффекта.")
        self.create_error_modal("error_modal_end_conditional", "Нет условных эффектов для завершения.")
        self.create_error_modal("error_modal_name", "Пожалуйста, введите название модификатора.")
        self.create_error_modal("error_modal_category", "Пожалуйста, введите уникальное название категории.")
        self.create_error_modal("error_modal_stat", "Пожалуйста, введите уникальное название стата.")
        self.create_error_modal("error_modal_flag", "Пожалуйста, введите уникальное название флага.")
        self.create_error_modal("error_modal_condition", "Пожалуйста, введите уникальное условие.")
        self.create_error_modal("error_modal_item", "Пожалуйста, заполните все поля для создания предмета.")

    def create_error_modal(self, tag, message):
        with dpg.window(label="Ошибка", modal=True, show=False, tag=tag):
            dpg.add_text(message)
            dpg.add_button(label="Закрыть", callback=lambda: dpg.configure_item(tag, show=False))

    def create_item_edit_window(self):
        with dpg.window(label="Редактировать Предметы", modal=True, show=False,
                        tag="edit_items_window", width=600, height=500):
            dpg.add_text("Список предметов:")
            dpg.add_child_window(tag="items_list", autosize_x=True, autosize_y=True)
            dpg.add_button(label="Закрыть",
                           callback=lambda: dpg.configure_item("edit_items_window", show=False))

    def create_set_creation_section(self):
        dpg.add_text("Введите информацию о сете:", color=[255, 255, 0])
        dpg.add_input_text(label="Название сета", tag="set_name_input")
        dpg.add_input_text(label="ID сета", tag="set_id_input")
        dpg.add_input_text(label="Описание сета", tag="set_description_input", multiline=True)
        dpg.add_button(label="Создать сет", callback=self.create_set_callback)
        dpg.add_text("", tag="status_text_set")

    def create_mod_creation_section(self):
        dpg.add_text("Введите информацию о модификаторе:", color=[255, 255, 0])
        with dpg.group(horizontal=True):
            dpg.add_combo(self.context.mod_categories, label="Категория модификатора", tag="mod_category")
            dpg.add_button(label="+", width=30, callback=self.add_category_callback)
        dpg.add_input_text(label="Название модификатора", tag="mod_name")
        dpg.add_separator()
        dpg.add_text("Добавьте эффекты модификатора:", color=[255, 255, 0])
        dpg.add_combo(['increase_stat', 'decrease_stat', 'set_flag', 'conditional_effect'],
                      label="Тип эффекта", tag="effect_type")
        with dpg.group(horizontal=True):
            dpg.add_combo(self.context.stats_options, label="Стат (если применимо)", tag="effect_stat")
            dpg.add_button(label="+", width=30, callback=self.add_new_stat_callback)
        with dpg.group(horizontal=True):
            dpg.add_input_text(label="Значение (если применимо)", tag="effect_value")
        with dpg.group(horizontal=True):
            dpg.add_combo(self.context.flags_options, label="Флаг (если применимо)", tag="effect_flag")
            dpg.add_button(label="+", width=30, callback=self.add_new_flag_callback)
        dpg.add_checkbox(label="Значение флага (если применимо)", tag="effect_flag_value")
        with dpg.group(horizontal=True):
            dpg.add_combo(self.context.conditions_options, label="Условие (если применимо)", tag="effect_condition")
            dpg.add_button(label="+", width=30, callback=self.add_new_condition_callback)
        with dpg.group(horizontal=True):
            dpg.add_button(label="Добавить эффект", callback=self.add_effect_callback)
            dpg.add_button(label="Завершить условный эффект", callback=self.end_conditional_effect_callback)
        dpg.add_separator()
        dpg.add_text("Предпросмотр эффектов:", color=[255, 255, 0])
        dpg.add_input_text(multiline=True, readonly=True, width=780, height=200, tag="effects_preview")
        with dpg.group(horizontal=True):
            dpg.add_button(label="Сохранить модификатор", callback=self.create_mod_callback)
            dpg.add_button(label="Сбросить форму", callback=self.reset_form_callback)
            dpg.add_button(label="Изменить моды", callback=self.edit_mods_callback)
        dpg.add_text("", tag="status_text")
        dpg.add_text("Выберите изображение мода:")
        dpg.add_button(label="Выбрать изображение", callback=self.select_mod_image)
        dpg.add_text("", tag="mod_image_path")
        self.create_mod_creation_windows()

    def create_item_creation_section(self):
        dpg.add_input_text(label="Название предмета", tag="item_name_input")
        dpg.add_combo(items=["helmet", "mask", "top", "gloves", "pants", "boots"], label="Тип предмета",
                      tag="item_type_combo")
        dpg.add_combo(items=["legendary", "epic", "rare", "common"], label="Редкость", tag="item_rarity_combo")
        dpg.add_input_text(label="ID сета (если применимо)", tag="item_set_input")
        dpg.add_button(label="Выбрать изображение", callback=self.select_item_image)
        dpg.add_text("", tag="item_image_path")
        with dpg.group(horizontal=True):
            dpg.add_button(label="Создать предмет", callback=self.create_item_callback)
            dpg.add_button(label="Сбросить форму", callback=self.reset_item_form_callback)
            dpg.add_button(label="Изменить предметы", callback=self.edit_items_callback)
        dpg.add_text("", tag="status_text_item")

    def edit_items_callback(self, sender, app_data, user_data):
        self.populate_items_list()
        dpg.configure_item("edit_items_window", show=True)

    def populate_items_list(self):
        dpg.delete_item("items_list", children_only=True)
        for itm in self.context.items_data:
            item_name = itm['name']
            with dpg.group(horizontal=True, parent="items_list"):
                dpg.add_button(label=item_name, callback=self.select_item_for_editing, user_data=itm)
                dpg.add_button(label="Удалить", callback=self.delete_item_callback, user_data=itm)

    def select_item_for_editing(self, sender, app_data, user_data):
        item = user_data
        dpg.set_value("item_name_input", item.get('name', ''))
        dpg.set_value("item_type_combo", item.get('type', ''))
        dpg.set_value("item_rarity_combo", item.get('rarity', ''))
        dpg.set_value("item_set_input", item.get('set_id', ''))
        item_image_path = f"{item['id']}.png"
        dpg.set_value("item_image_path", f"Изображение: {item_image_path}")
        self.context.current_item = item.copy()
        dpg.configure_item("edit_items_window", show=False)

    def delete_item_callback(self, sender, app_data, user_data):
        item = user_data
        success, message = self.context.delete_item(item)
        if success:
            self.populate_items_list()
        else:
            dpg.set_value("status_text_item", message)

    def reset_item_form_callback(self, sender, app_data, user_data):
        dpg.set_value("item_name_input", "")
        dpg.set_value("item_type_combo", "")
        dpg.set_value("item_rarity_combo", "")
        dpg.set_value("item_set_input", "")
        dpg.set_value("item_image_path", "")
        if hasattr(self.context, 'current_item_image_path'):
            delattr(self.context, 'current_item_image_path')
        dpg.configure_item("status_text_item", default_value="", color=[0, 0, 0])

    def select_item_image(self):
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg"), ("All files", "*.*")]
        )
        root.destroy()
        if file_path:
            self.context.current_item_image_path = file_path
            dpg.set_value("item_image_path", f"Изображение выбрано: {os.path.basename(file_path)}")

    def create_mod_creation_windows(self):
        with dpg.window(label="Добавить новую категорию", modal=True, show=False, tag="add_category_window"):
            dpg.add_input_text(label="Название новой категории", tag="new_category_input")
            dpg.add_button(label="Сохранить", callback=self.save_new_category_callback)
            dpg.add_button(label="Отмена", callback=lambda: dpg.configure_item("add_category_window", show=False))

        with dpg.window(label="Добавить новый стат", modal=True, show=False, tag="add_stat_window"):
            dpg.add_input_text(label="Название нового стата", tag="new_stat_input")
            dpg.add_button(label="Сохранить", callback=self.save_new_stat_callback)
            dpg.add_button(label="Отмена", callback=lambda: dpg.configure_item("add_stat_window", show=False))

        with dpg.window(label="Добавить новый флаг", modal=True, show=False, tag="add_flag_window"):
            dpg.add_input_text(label="Название нового флага", tag="new_flag_input")
            dpg.add_button(label="Сохранить", callback=self.save_new_flag_callback)
            dpg.add_button(label="Отмена", callback=lambda: dpg.configure_item("add_flag_window", show=False))

        with dpg.window(label="Добавить новое условие", modal=True, show=False, tag="add_condition_window"):
            dpg.add_input_text(label="Новое условие", tag="new_condition_input")
            dpg.add_button(label="Сохранить", callback=self.save_new_condition_callback)
            dpg.add_button(label="Отмена", callback=lambda: dpg.configure_item("add_condition_window", show=False))

        with dpg.window(label="Редактировать Моды", modal=True, show=False, tag="edit_mods_window", width=600, height=500):
            dpg.add_text("Список модов:")
            dpg.add_child_window(tag="mods_list", autosize_x=True, autosize_y=True)
            dpg.add_button(label="Закрыть", callback=lambda: dpg.configure_item("edit_mods_window", show=False))

    def select_mod_image(self):
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg"), ("All files", "*.*")]
        )
        root.destroy()
        if file_path:
            self.context.current_mod_image_path = file_path
            dpg.set_value("mod_image_path", f"Изображение выбрано: {os.path.basename(file_path)}")

    def mouse_down_callback(self, sender, app_data, user_data):
        self.mouse_pressed = True
        self.context.mouse_pressed = True
        logging.debug("Mouse down detected")

    def mouse_up_callback(self, sender, app_data, user_data):
        self.mouse_pressed = False
        self.context.mouse_pressed = False

    def open_mannequin_settings_window(self, sender, app_data, user_data):
        window_tag = "mannequin_settings_window"
        if dpg.does_item_exist(window_tag):
            dpg.delete_item(window_tag)
        window_width = 400
        window_height = 500
        main_window_pos = dpg.get_viewport_pos()
        main_window_width = dpg.get_viewport_width()
        main_window_height = dpg.get_viewport_height()
        x_pos = main_window_pos[0] + (main_window_width - window_width) / 2
        y_pos = main_window_pos[1] + (main_window_height - window_height) / 2 - 100
        with dpg.window(label="Настройки Манекена", modal=True, show=True, tag=window_tag,
                        width=window_width, height=window_height, pos=(x_pos, y_pos)):
            dpg.add_text(f"HP манекена: {self.context.mannequin.current_hp}/{self.context.mannequin.max_hp}")
            hp_slider_tag = "mannequin_hp_slider"
            dpg.add_slider_int(label="Установить HP", min_value=1000, max_value=1000000,
                               default_value=self.context.mannequin.max_hp, tag=hp_slider_tag,
                               callback=self.apply_mannequin_hp_callback)
            enemy_types = ['Обычный', 'Элитный', 'Босс']
            dpg.add_combo(label="Тип Врага", items=enemy_types, default_value=self.context.mannequin.enemy_type,
                          tag="mannequin_enemy_type_combo", callback=self.apply_mannequin_enemy_type_callback)
            dpg.add_checkbox(label="Отображать Хотбар", default_value=self.context.mannequin.show_hotbar,
                             callback=self.toggle_hotbar_callback)
            dpg.add_checkbox(label="Суммарный урон дробовика",
                             default_value=self.context.mannequin.show_unified_shotgun_damage,
                             callback=self.toggle_unified_shotgun_damage_callback)
            dpg.add_separator()
            dpg.add_text("Эффекты:")
            for eff_name in self.context.available_effects:
                is_active = eff_name in self.context.mannequin.effects
                dpg.add_checkbox(label=eff_name, default_value=is_active, user_data=eff_name,
                                 callback=self.toggle_mannequin_effect)
            dpg.add_button(label="Закрыть", callback=lambda: dpg.delete_item(window_tag))
            dpg.add_separator()
            dpg.add_text("Настройки анимации урона:")
            dpg.add_slider_float(label="Скорость", min_value=10, max_value=500,
                                 default_value=self.context.damage_text_settings['speed'],
                                 callback=lambda s,a,u: self.set_damage_text_setting('speed', a))
            dpg.add_slider_float(label="Задержка исчезновения", min_value=0.1, max_value=5.0,
                                 default_value=self.context.damage_text_settings['fade_delay'],
                                 callback=lambda s,a,u: self.set_damage_text_setting('fade_delay', a))
            dpg.add_slider_int(label="Мин. угол", min_value=0, max_value=180,
                               default_value=self.context.damage_text_settings['angle_min'],
                               callback=lambda s,a,u: self.set_damage_text_setting('angle_min', a))
            dpg.add_slider_int(label="Макс. угол", min_value=0, max_value=180,
                               default_value=self.context.damage_text_settings['angle_max'],
                               callback=lambda s,a,u: self.set_damage_text_setting('angle_max', a))
            dpg.add_text("Цвет для критического попадания:")
            dpg.add_color_picker(default_value=self.context.damage_text_settings['crit_color'], width=200,
                                 callback=lambda s,a,u: self.set_damage_text_setting('crit_color', a))
            dpg.add_text("Цвет для слабого места:")
            dpg.add_color_picker(default_value=self.context.damage_text_settings['weakspot_color'], width=200,
                                 callback=lambda s,a,u: self.set_damage_text_setting('weakspot_color', a))
            dpg.add_text("Цвет для критического попадания по слабому месту:")
            dpg.add_color_picker(default_value=self.context.damage_text_settings['crit_weakspot_color'], width=200,
                                 callback=lambda s,a,u: self.set_damage_text_setting('crit_weakspot_color', a))
            dpg.add_text("Цвет для обычного попадания:")
            dpg.add_color_picker(default_value=self.context.damage_text_settings['normal_color'], width=200,
                                 callback=lambda s,a,u: self.set_damage_text_setting('normal_color', a))

    def set_damage_text_setting(self, name, value):
        # Цвета приходят в формате float [0..1], поэтому преобразуем в int [0..255]
        if isinstance(value, list) and len(value) == 4:
            value = [int(v * 255) for v in value]
        self.context.damage_text_settings[name] = value

    def apply_mannequin_enemy_type_callback(self, sender, app_data, user_data):
        et = dpg.get_value("mannequin_enemy_type_combo")
        self.context.mannequin.enemy_type = et
        self.update_stats_display()

    def toggle_hotbar_callback(self, sender, app_data, user_data):
        self.context.mannequin.show_hotbar = not self.context.mannequin.show_hotbar
        if self.context.mannequin.show_hotbar:
            dpg.configure_item("hotbar_group", show=True)
            dpg.configure_item("hp_bar_layer", show=True)
        else:
            dpg.configure_item("hotbar_group", show=False)
            dpg.configure_item("hp_bar_layer", show=False)

    def toggle_unified_shotgun_damage_callback(self, sender, app_data, user_data):
        self.context.mannequin.toggle_unified_shotgun_damage()

    def toggle_mannequin_effect(self, sender, app_data, user_data):
        eff = user_data
        is_active = dpg.get_value(sender)
        if is_active:
            self.context.mannequin.apply_effect(eff)
        else:
            self.context.mannequin.remove_effect(eff)
        self.update_stats_display()

    def apply_mannequin_hp_callback(self, sender, app_data, user_data):
        hp = dpg.get_value("mannequin_hp_slider")
        self.context.mannequin.set_hp(hp)
        self.update_stats_display()

    def create_set_callback(self, sender, app_data, user_data=None):
        sn = dpg.get_value("set_name_input").strip()
        sid = dpg.get_value("set_id_input").strip()
        sd = dpg.get_value("set_description_input").strip()
        success, msg = self.context.create_set_data(sn, sid, sd)
        if success:
            dpg.configure_item("status_text_set", default_value=msg, color=[0, 255, 0])
        else:
            dpg.configure_item("status_text_set", default_value=msg, color=[255, 0, 0])

    def toggle_creation_menu(self, val):
        if val == "Мод":
            dpg.configure_item("mod_creation_group", show=True)
            dpg.configure_item("item_creation_group", show=False)
            dpg.configure_item("set_creation_group", show=False)
        elif val == "Предмет":
            dpg.configure_item("mod_creation_group", show=False)
            dpg.configure_item("item_creation_group", show=True)
            dpg.configure_item("set_creation_group", show=False)
        elif val == "Сет":
            dpg.configure_item("mod_creation_group", show=False)
            dpg.configure_item("item_creation_group", show=False)
            dpg.configure_item("set_creation_group", show=True)

    def add_category_callback(self, sender, app_data, user_data=None):
        dpg.configure_item("add_category_window", show=True)

    def save_new_category_callback(self, sender, app_data, user_data=None):
        nc = dpg.get_value("new_category_input").strip()
        if self.context.add_category(nc):
            dpg.configure_item("mod_category", items=self.context.mod_categories)
            dpg.set_value("new_category_input", "")
            dpg.configure_item("add_category_window", show=False)
        else:
            dpg.configure_item("error_modal_category", show=True)

    def add_new_stat_callback(self, sender, app_data, user_data=None):
        dpg.configure_item("add_stat_window", show=True)

    def save_new_stat_callback(self, sender, app_data, user_data=None):
        ns = dpg.get_value("new_stat_input").strip()
        if self.context.add_new_stat(ns):
            dpg.configure_item("effect_stat", items=self.context.stats_options)
            dpg.set_value("new_stat_input", "")
            dpg.configure_item("add_stat_window", show=False)
        else:
            dpg.configure_item("error_modal_stat", show=True)

    def add_new_flag_callback(self, sender, app_data, user_data=None):
        dpg.configure_item("add_flag_window", show=True)

    def save_new_flag_callback(self, sender, app_data, user_data=None):
        nf = dpg.get_value("new_flag_input").strip()
        if self.context.add_new_flag(nf):
            dpg.configure_item("effect_flag", items=self.context.flags_options)
            dpg.set_value("new_flag_input", "")
            dpg.configure_item("add_flag_window", show=False)
        else:
            dpg.configure_item("error_modal_flag", show=True)

    def add_new_condition_callback(self, sender, app_data, user_data=None):
        dpg.configure_item("add_condition_window", show=True)

    def save_new_condition_callback(self, sender, app_data, user_data=None):
        nc = dpg.get_value("new_condition_input").strip()
        if self.context.add_new_condition(nc):
            dpg.configure_item("effect_condition", items=self.context.conditions_options)
            dpg.set_value("new_condition_input", "")
            dpg.configure_item("add_condition_window", show=False)
        else:
            dpg.configure_item("error_modal_condition", show=True)

    def add_effect_callback(self, sender, app_data, user_data=None):
        et = dpg.get_value("effect_type")
        es = dpg.get_value("effect_stat")
        ev = dpg.get_value("effect_value")
        ef = dpg.get_value("effect_flag")
        efv = dpg.get_value("effect_flag_value")
        eco = dpg.get_value("effect_condition")
        success, message = self.context.add_effect(et, es, ev, ef, efv, eco)
        if success:
            self.update_effects_preview()
        else:
            dpg.configure_item("error_modal_effect", show=True)

    def update_effects_preview(self):
        dpg.set_value("effects_preview",
                      json.dumps(self.context.current_mod['effects'], ensure_ascii=False, indent=2))

    def end_conditional_effect_callback(self, sender, app_data, user_data=None):
        success, message = self.context.end_conditional_effect()
        if success:
            self.update_effects_preview()
        else:
            dpg.configure_item("error_modal_end_conditional", show=True)

    def create_mod_callback(self, sender, app_data, user_data=None):
        mn = dpg.get_value("mod_name").strip()
        mc = dpg.get_value("mod_category").strip()
        success, message = self.context.create_mod(mn, mc)
        if success:
            if hasattr(self.context, 'current_mod_image_path'):
                dest_folder = os.path.join('data', 'icons', 'mods', mc)
                os.makedirs(dest_folder, exist_ok=True)
                dest_path = os.path.join(dest_folder, f"{mn.lower().replace(' ', '_')}.png")
                shutil.copy(self.context.current_mod_image_path, dest_path)
                self.load_images()
                dpg.set_value("mod_image_path", "")
                delattr(self.context, 'current_mod_image_path')
            dpg.set_value("status_text", message)
            self.context.reset_mod_form()
            self.update_effects_preview()
        else:
            dpg.set_value("status_text", message)

    def reset_form_callback(self, sender, app_data, user_data=None):
        self.context.reset_mod_form()
        self.update_effects_preview()
        dpg.set_value("mod_name", "")
        dpg.set_value("effect_type", "")
        dpg.set_value("effect_stat", "")
        dpg.set_value("effect_value", "")
        dpg.set_value("effect_flag", "")
        dpg.set_value("effect_flag_value", False)
        dpg.set_value("effect_condition", "")
        dpg.configure_item("status_text", default_value="", color=[0, 0, 0])

    def create_item_callback(self, sender, app_data, user_data=None):
        name = dpg.get_value("item_name_input").strip()
        tp = dpg.get_value("item_type_combo").strip()
        rt = dpg.get_value("item_rarity_combo").strip()
        si = dpg.get_value("item_set_input").strip()
        success, message = self.context.create_item_data(name, tp, rt, si)
        if success:
            if hasattr(self.context, 'current_item_image_path'):
                dest_folder = os.path.join('data', 'icons', 'armor')
                os.makedirs(dest_folder, exist_ok=True)
                dest_path = os.path.join(dest_folder, f"{name.lower().replace(' ', '_')}.png")
                shutil.copy(self.context.current_item_image_path, dest_path)
                self.load_images()
                dpg.set_value("item_image_path", "")
                delattr(self.context, 'current_item_image_path')
            dpg.configure_item("status_text_item", default_value=message, color=[0, 255, 0])
        else:
            dpg.configure_item("status_text_item", default_value=message, color=[255, 0, 0])

    def edit_mods_callback(self, sender, app_data, user_data=None):
        self.populate_mods_list()
        dpg.configure_item("edit_mods_window", show=True)

    def populate_mods_list(self):
        dpg.delete_item("mods_list", children_only=True)
        for cat_display_name, mod_key in self.context.category_key_mapping.items():
            mods = self.context.mods_data.get(mod_key, [])
            if mods:
                dpg.add_text(f"Категория: {cat_display_name}", parent="mods_list")
                for mod in mods:
                    mod_name = mod['name']
                    with dpg.group(horizontal=True, parent="mods_list"):
                        dpg.add_button(label=mod_name, callback=self.select_mod_callback, user_data=mod)
                        dpg.add_button(label="Удалить", callback=self.delete_mod_callback,
                                       user_data={'mod': mod, 'mod_key': mod_key})
                dpg.add_separator(parent="mods_list")

    def select_mod_callback(self, sender, app_data, user_data):
        mod = user_data
        dpg.set_value("mod_name", mod.get('name', ''))
        dpg.set_value("mod_category", mod.get('category', ''))
        self.context.current_mod = mod.copy()
        self.context.stats_stack = [self.context.current_mod['effects']]
        self.update_effects_preview()
        dpg.set_value("effect_type", "")
        dpg.set_value("effect_stat", "")
        dpg.set_value("effect_value", "")
        dpg.set_value("effect_flag", "")
        dpg.set_value("effect_flag_value", False)
        dpg.set_value("effect_condition", "")
        dpg.configure_item("edit_mods_window", show=False)

    def delete_mod_callback(self, sender, app_data, user_data):
        mod = user_data['mod']
        mod_key = user_data['mod_key']
        success, message = self.context.delete_mod(mod, mod_key)
        if success:
            self.populate_mods_list()
        else:
            dpg.set_value("status_text", message)

    def update_dps_display(self):
        dps_text = f"DPS: {int(self.context.dps)}    Total DMG: {int(self.context.total_damage)}"
        if dpg.does_item_exist("dps_text"):
            dpg.set_value("dps_text", dps_text)
        ammo_text = f"Патроны: {self.context.current_ammo}/{self.player.stats.get('magazine_capacity', 0)}"
        if dpg.does_item_exist("ammo_text"):
            dpg.set_value("ammo_text", ammo_text)

    def draw_mannequin_hp_bar(self):
        max_hp = self.context.mannequin.max_hp
        current_hp = self.context.mannequin.current_hp
        if current_hp <= 0:
            self.context.mannequin.current_hp = max_hp
            current_hp = max_hp
        hp_percentage = current_hp / max_hp if max_hp > 0 else 0
        bar_width = 150
        bar_height = 15
        green_width = bar_width * hp_percentage
        red_width = bar_width - green_width
        bar_x = 75
        bar_y = 5
        if not dpg.does_item_exist("hp_bar_layer"):
            return
        dpg.delete_item("hp_bar_layer", children_only=True)
        dpg.draw_rectangle(pmin=[bar_x, bar_y],
                           pmax=[bar_x + green_width, bar_y + bar_height],
                           color=[0, 255, 0, 255], fill=[0, 255, 0, 255],
                           parent="hp_bar_layer")
        dpg.draw_rectangle(pmin=[bar_x + green_width, bar_y],
                           pmax=[bar_x + bar_width, bar_y + bar_height],
                           color=[255, 0, 0, 255], fill=[255, 0, 0, 255],
                           parent="hp_bar_layer")
        dpg.draw_rectangle(pmin=[bar_x, bar_y],
                           pmax=[bar_x + bar_width, bar_y + bar_height],
                           color=[255, 255, 255, 255], fill=[0, 0, 0, 0],
                           thickness=1, parent="hp_bar_layer")

    def save_config_callback(self):
        self.config_manager.save_config()

    def load_config_callback(self):
        self.config_manager.load_config()
