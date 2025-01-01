# data/menu/settings_button.py

import dearpygui.dearpygui as dpg
import os
import subprocess
from config import Config
from core import get_icon_path, toggle_console

class SettingsButton:
    def __init__(self, main_app, parent):
        self.main_app = main_app
        self.trans = self.main_app.translations.get(self.main_app.current_language, {}).get("settings", {})
        self.config = Config.from_json()

        self.button_tag = f"settings_button_{id(self)}"
        dpg.add_button(label=self.trans.get("title", "Settings"),
                       callback=self.toggle_settings,
                       parent=parent,
                       tag=self.button_tag)

        if not dpg.does_item_exist("SettingsWindow"):
            with dpg.window(label=self.trans.get("title", "Settings"),
                            width=300,
                            height=350,
                            show=False,
                            tag="SettingsWindow"):
                self.create_settings_elements()

        print(f"Creating Settings button with parent: {parent}")
        print(f"Settings button tag: {self.button_tag}")

    def create_settings_elements(self):
        self.always_on_top_var = dpg.add_checkbox(
            label=self.trans.get("always_on_top", "Always on top"),
            default_value=self.config.always_on_top,
            callback=self.toggle_always_on_top,
            parent="SettingsWindow",
            tag="always_on_top_checkbox"
        )

        self.monitoring_var = dpg.add_checkbox(
            label=self.trans.get("enable_console_log", "Enable Console Log"),
            default_value=self.config.monitoring,
            callback=self.toggle_monitoring,
            parent="SettingsWindow",
            tag="monitoring_checkbox"
        )

        self.open_config_button = dpg.add_button(
            label=self.trans.get("open_config_folder", "Open Config Folder"),
            callback=self.open_config_folder,
            parent="SettingsWindow",
            tag="open_config_button"
        )

        with dpg.group(horizontal=True, parent="SettingsWindow"):
            ru_flag_texture = self.load_flag_texture("russia_flag.png")
            if ru_flag_texture:
                dpg.add_image_button(
                    texture_tag=ru_flag_texture,
                    width=20,
                    height=15,
                    callback=lambda: self.set_language('ru'),
                    tag="ru_flag_button"
                )
            else:
                dpg.add_button(
                    label="RU",
                    callback=lambda: self.set_language('ru'),
                    tag="ru_flag_button"
                )

            en_flag_texture = self.load_flag_texture("usa_flag.png")
            if en_flag_texture:
                dpg.add_image_button(
                    texture_tag=en_flag_texture,
                    width=20,
                    height=15,
                    callback=lambda: self.set_language('en'),
                    tag="en_flag_button"
                )
            else:
                dpg.add_button(
                    label="EN",
                    callback=lambda: self.set_language('en'),
                    tag="en_flag_button"
                )

    def update_ui(self):
        self.trans = self.main_app.translations.get(self.main_app.current_language, {}).get("settings", {})
        dpg.set_item_label(self.button_tag, self.trans.get("title", "Settings"))

        if dpg.does_item_exist("SettingsWindow"):
            dpg.configure_item("always_on_top_checkbox", label=self.trans.get("always_on_top", "Always on top"))
            dpg.configure_item("monitoring_checkbox", label=self.trans.get("enable_console_log", "Enable Console Log"))
            dpg.configure_item("SettingsWindow", label=self.trans.get("title", "Settings"))
            dpg.configure_item("open_config_button", label=self.trans.get("open_config_folder", "Open Config Folder"))

    def set_language(self, lang):
        self.main_app.save_states()
        self.config.language = lang
        self.config.save_to_json()
        self.main_app.change_language(lang)
        self.update_ui()

    def load_flag_texture(self, flag_name):
        flag_path = get_icon_path(flag_name)
        if os.path.exists(flag_path):
            width, height, channels, data = dpg.load_image(flag_path)
            with dpg.texture_registry():
                texture_id = dpg.add_static_texture(width, height, data, tag=flag_name)
            return texture_id
        else:
            print(f"Flag image not found: {flag_path}")
            return None

    def toggle_settings(self):
        if dpg.does_item_exist("SettingsWindow"):
            current_show = dpg.get_item_configuration("SettingsWindow")["show"]
            dpg.configure_item("SettingsWindow", show=not current_show)

    def toggle_always_on_top(self, sender, app_data):
        self.config.always_on_top = app_data
        dpg.set_viewport_always_top(app_data)
        self.config.save_to_json()

    def toggle_monitoring(self, sender, app_data):
        self.config.monitoring = app_data
        if app_data:
            toggle_console()
        self.config.save_to_json()

    def open_config_folder(self):
        config_path = self.config.temp_folder
        if os.path.exists(config_path):
            subprocess.Popen(f'explorer "{config_path}"')
        else:
            print(f"Config folder does not exist: {config_path}")

    def stop(self):
        print("Settings stopped.")

