# main_menu.py

from data.menu.foto_video_tab import FotoVideoTab
from data.menu.pianino_bot_tab import PianinoBotTab
from data.menu.bot_fish_tab import BotFishTab
from data.menu.other_tab import OtherTab
from data.menu.calc_and_mod_tab import CalcAndModTab
from data.menu.settings_button import SettingsButton
from config import Config
from core import PathFinder
import os
import re
import time
import threading
import dearpygui.dearpygui as dpg
import json

def camel_to_snake(name):
    s1 = re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

class MainApp:
    def __init__(self):
        self.config = Config.from_json()
        self.current_language = self.config.language
        self.translations = self.load_translations()
        self.trans = self.translations.get(self.current_language, {}).get("main", {})
        self.tabs = []
        self.settings_buttons = []
        self.default_font_tag = "Default font"

        dpg.create_context()

        self.load_font()  # грузим шрифт

        # Можно сделать resizable=True, чтобы динамически менять размер окна
        dpg.create_viewport(
            title=self.trans.get("app_title", "Default Title"),
            width=700,
            height=500,
            resizable=True,
            decorated=True
        )

        self.apply_settings()
        dpg.setup_dearpygui()
        dpg.set_viewport_resize_callback(self.handle_viewport_resize)

        self.path_finder = PathFinder(self.config)
        self.game_path = self.path_finder.find_game_path_in_config()

        self.search_start_time = None
        self.path_finder_thread = None

        self.setup_ui()
        self.restore_states()

        if not self.game_path:
            self.search_start_time = time.time()
            self.path_finder_thread = threading.Thread(
                target=self.path_finder.search_game_path_with_timeout,
                daemon=True
            )
            self.path_finder_thread.start()

        dpg.show_viewport()
        dpg.set_primary_window("MainWindow", True)
        self.handle_viewport_resize()

        try:
            while dpg.is_dearpygui_running():
                for tab in self.tabs:
                    if hasattr(tab, "update"):
                        tab.update()

                dpg.render_dearpygui_frame()

                if not self.game_path:
                    if self.path_finder.found_path and os.path.exists(self.path_finder.found_path):
                        self.game_path = self.path_finder.found_path
                    else:
                        if self.path_finder.search_completed and not self.path_finder.found_path:
                            pass
        except KeyboardInterrupt:
            print("Application interrupted by user.")
        finally:
            self.stop()
            dpg.destroy_context()

    def setup_ui(self):
        with dpg.window(label="Main Window", tag="MainWindow", width=680, height=460, no_resize=True):
            # ▼▼▼ Вместо обычного tab_bar, ставим колбэк ▼▼▼
            with dpg.tab_bar(tag="MainTabBar", callback=self.handle_tab_change):
                self.create_tab('Foto and Video', FotoVideoTab)
                self.create_tab('Piano Bot', PianinoBotTab)
                self.create_tab('Bot Fish', BotFishTab)
                self.create_tab('Calc and Mod', CalcAndModTab)
                self.create_tab('Misc', OtherTab)
            # ▲▲▲

            with dpg.group(horizontal=True) as settings_group:
                dpg.add_spacer(width=-1)
                SettingsButton(self, parent=settings_group)

    def handle_tab_change(self, sender, app_data, user_data):
        """
        Колбэк срабатывает при переключении вкладок внутри MainTabBar.
        sender — это "MainTabBar"
        app_data — это id выбранной вкладки (int)
        """
        tab_label = dpg.get_item_label(app_data)
        print(f"handle_tab_change: Выбрана вкладка: {tab_label}")
        self.handle_viewport_resize()

    def handle_viewport_resize(self, sender=None, app_data=None, user_data=None):
        viewport_width = max(700, dpg.get_viewport_client_width())
        viewport_height = max(500, dpg.get_viewport_client_height())
        if dpg.does_item_exist("MainWindow"):
            dpg.configure_item("MainWindow", width=viewport_width, height=viewport_height)

        for tab in self.tabs:
            if hasattr(tab, "handle_viewport_resize"):
                tab.handle_viewport_resize(viewport_width, viewport_height)

    def create_tab(self, tab_name, tab_class):
        with dpg.tab(label=tab_name) as tab_id:
            tab_instance = tab_class(self)
            self.tabs.append(tab_instance)
            if hasattr(tab_instance, "trans"):
                dpg.set_item_label(tab_id, tab_instance.trans.get("title", tab_name))
            print(f"Tab created: {tab_name}")

    def load_translations(self):
        translations_path = "translations.json"
        if os.path.exists(translations_path):
            with open(translations_path, 'r', encoding='utf-8') as translations_file:
                print("Translations loaded from file.")
                return json.load(translations_file)
        print("Translations file not found.")
        return {}

    def save_states(self):
        for tab in self.tabs:
            if hasattr(tab, "save_states"):
                tab.save_states()
        self.config.save_to_json()
        print("Configuration saved to JSON.")

    def restore_states(self):
        for tab in self.tabs:
            if hasattr(tab, "restore_states"):
                tab.restore_states()

    def load_font(self):
        if dpg.does_item_exist(self.default_font_tag):
            dpg.delete_item(self.default_font_tag)
        if dpg.does_item_exist("Font_Registry"):
            dpg.delete_item("Font_Registry")

        with dpg.font_registry(tag="Font_Registry"):
            font_path = "data/file/ru.ttf"
            if os.path.exists(font_path):
                with dpg.font(font_path, 13, default_font=True, tag=self.default_font_tag):
                    dpg.add_font_range_hint(dpg.mvFontRangeHint_Cyrillic)
                dpg.bind_font(self.default_font_tag)
                print("Unified font (ru.ttf) loaded for all languages.")
            else:
                print("No ru.ttf found, using default Dear PyGui font.")

    def change_language(self, lang):
        self.current_language = lang
        self.save_states()
        self.config.language = lang
        self.config.save_to_json()
        print(f"Language changed to: {lang}")

        self.trans = self.translations.get(lang, {}).get("main", {})

        tab_bar_children = dpg.get_item_children("MainTabBar", 1)
        for i, tab in enumerate(self.tabs):
            tab_key = camel_to_snake(tab.__class__.__name__)
            tab.trans = self.translations.get(lang, {}).get(tab_key, {})
            if hasattr(tab, "update_ui"):
                tab.update_ui()
            if i < len(tab_bar_children):
                tab_id = tab_bar_children[i]
                dpg.set_item_label(tab_id, tab.trans.get("title", "Unnamed Tab"))
            else:
                print(f"No tab found for index {i}")

        self.load_font()
        for settings_button in self.settings_buttons:
            settings_button.update_ui()

        dpg.set_viewport_title(self.trans.get("app_title", "Default Title"))
        self.handle_viewport_resize()
        print("UI updated with new translations.")

    def apply_settings(self):
        dpg.set_viewport_always_top(self.config.always_on_top)

    def stop(self):
        self.path_finder.search_running = False
        if hasattr(self, 'path_finder_thread') and self.path_finder_thread.is_alive():
            self.path_finder_thread.join()
        for tab in self.tabs:
            if hasattr(tab, "stop"):
                tab.stop()
        print("Application stopped.")
