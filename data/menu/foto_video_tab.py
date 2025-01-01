# data/menu/foto_video_tab.py

import dearpygui.dearpygui as dpg
from PIL import Image
import cv2
import os
import threading
import shutil
import numpy as np
from watchdog.observers import Observer
from core import process_image, MyHandler, cleanup_temp_files, hide_console_after_delay
from config import Config
import tkinter as tk
from tkinter import filedialog
import re
import time
import queue

def camel_to_snake(name):
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

class FotoVideoTab:
    def __init__(self, main_app):
        self.main_app = main_app
        self.translations = self.main_app.translations
        tab_key = camel_to_snake(self.__class__.__name__)
        self.trans = self.translations.get(self.main_app.current_language, {}).get(tab_key, {})

        self.config = Config.from_json()
        self.temp_folder = self.config.temp_folder
        self.template_path = None

        self.used = False
        self.observer = None

        self.path_finder = self.main_app.path_finder

        self.game_path = self.config.game_path if (self.config.game_path and os.path.exists(self.config.game_path)) else None

        hide_console_after_delay()

        self.frame_queue = queue.Queue()

        with dpg.group(horizontal=False):
            self.create_canvas()
            self.create_photo_local_path_line()  # Поле для пути к photo_local
            self.create_file_path_line()
            self.create_buttons()
            self.drag_drop_label = dpg.add_text(
                default_value=self.trans.get("drag_drop_label", "Please select a file to display"))

        self.selected_file_path = ""

        # Окно выбора пути вручную или продолжения поиска
        with dpg.window(label="Путь не найден", modal=True, width=400, height=120, show=False, tag="game_path_not_found_popup"):
            # Сохраняем теги для обновления при смене языка
            self.game_path_not_found_text = dpg.add_text("Путь к 'photo_local' не найден.\nУказать вручную или продолжить поиск?")
            self.game_path_manual_btn = dpg.add_button(label="Указать вручную", callback=self.set_path_manually_callback)
            self.game_path_continue_btn = dpg.add_button(label="Продолжить поиск", callback=self.continue_search_callback)
            self.game_path_cancel_btn = dpg.add_button(label="Отмена", callback=lambda: dpg.configure_item("game_path_not_found_popup", show=False))

    def create_canvas(self):
        with dpg.group():
            self.canvas_width = 480
            self.canvas_height = 270
            with dpg.drawlist(width=self.canvas_width, height=self.canvas_height, tag="canvas"):
                self.draw_canvas_background()

    def draw_canvas_background(self):
        dpg.draw_rectangle((0, 0), (self.canvas_width, self.canvas_height),
                           color=(128, 128, 128, 255), thickness=2,
                           fill=(128, 128, 128, 255), parent="canvas")

    def create_photo_local_path_line(self):
        with dpg.group(horizontal=True):
            default_value = self.game_path if self.game_path else ""
            # Сохраняем tag, чтобы обновлять label при смене языка
            self.photo_local_input = dpg.add_input_text(
                label=self.trans.get("photo_local_path_label", "Photo Local Path:"),
                default_value=default_value,
                width=400,
                readonly=True
            )
            self.create_select_folder_button()

    def create_select_folder_button(self):
        icon_path = os.path.join("data", "icons", "folder_icon.png")
        if os.path.exists(icon_path):
            width, height, channels, data = dpg.load_image(icon_path)
            with dpg.texture_registry():
                icon_id = dpg.add_static_texture(width, height, data)
            self.select_folder_button = dpg.add_image_button(texture_id=icon_id, callback=self.open_folder_dialog, width=30, height=30)
        else:
            self.select_folder_button = dpg.add_button(label=self.trans.get("select_folder", "Select Folder"), callback=self.open_folder_dialog)

    def create_file_path_line(self):
        with dpg.group(horizontal=True):
            self.file_path_input = dpg.add_input_text(
                label="",
                default_value="",
                width=400,
                readonly=True
            )
            self.create_select_file_button()

    def create_select_file_button(self):
        icon_path = os.path.join("data", "icons", "folder_icon.png")
        if os.path.exists(icon_path):
            width, height, channels, data = dpg.load_image(icon_path)
            with dpg.texture_registry():
                icon_id = dpg.add_static_texture(width, height, data)
            self.select_file_button = dpg.add_image_button(texture_id=icon_id, callback=self.open_file_dialog, width=30, height=30)
        else:
            self.select_file_button = dpg.add_button(label=self.trans.get("select_file", "Select File"), callback=self.open_file_dialog)

    def create_buttons(self):
        with dpg.group(horizontal=True):
            self.use_button = dpg.add_button(label=self.trans.get("use_button", "Use"),
                                             callback=self.on_use_clicked)

    def on_use_clicked(self):
        if self.verify_paths():
            self.set_template()
        else:
            # Путь неизвестен или поиск ещё не дал результата
            dpg.configure_item("game_path_not_found_popup", show=True)

    def set_path_manually_callback(self):
        dpg.configure_item("game_path_not_found_popup", show=False)
        self.path_finder.choose_game_path_manually()
        self.game_path = self.path_finder.found_path
        if self.game_path:
            dpg.set_value(self.photo_local_input, self.game_path)

    def continue_search_callback(self):
        dpg.configure_item("game_path_not_found_popup", show=False)
        if not self.path_finder.search_running:
            self.path_finder.search_running = True
            self.path_finder.search_completed = False
            self.path_finder.search_start_time = time.time()
            threading.Thread(target=self.path_finder.search_game_path_with_timeout, daemon=True).start()

    def open_folder_dialog(self, sender, app_data):
        # Убираем проверку уже известного пути, всегда даём возможность изменить путь
        root = tk.Tk()
        root.withdraw()
        folder_path = filedialog.askdirectory(title=self.trans.get("select_photo_local_dialog", "Select 'photo_local' folder"))
        root.destroy()

        if folder_path:
            self.path_finder.found_path = folder_path
            self.config.game_path = folder_path
            self.config.save_to_json()
            self.game_path = folder_path
            dpg.set_value(self.photo_local_input, self.game_path)
            print(f"Game path manually selected: {self.game_path}")
        else:
            print("User canceled folder selection.")

    def open_file_dialog(self, sender, app_data):
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(
            defaultextension="*",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg"),
                ("All files", "*.*")
            ],
            title=self.trans.get("select_image_file", "Select an image file")
        )
        root.destroy()

        if file_path:
            self.selected_file_path = file_path
            dpg.set_value(self.file_path_input, self.selected_file_path)
            self.process_selected_file(file_path)

    def verify_paths(self):
        if self.game_path and os.path.exists(self.game_path):
            print("Paths verified successfully.")
            return True
        else:
            print("Game path verification failed.")
            return False

    def set_template(self):
        if self.template_path:
            self.used = True
            print(f"Template set: {self.template_path}")
            if self.observer:
                self.observer.stop()
                self.observer.join()
            self.start_observer()

    def process_selected_file(self, file_path):
        if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            self.template_path = process_image(file_path, self.temp_folder)
            self.display_image(self.template_path)
            print(f"Image processed and displayed:  {self.template_path}")
        else:
            dpg.add_text(default_value=self.trans.get("file_error", "Unsupported file type"), parent="canvas")
            print(f"Unsupported file type: {file_path}")

    def display_image(self, image_path):
        width, height, channels, data = dpg.load_image(image_path)

        with dpg.texture_registry():
            texture_id = dpg.add_static_texture(width, height, data)

        dpg.delete_item("canvas", children_only=True)
        dpg.draw_image(texture_id, (0, 0), (self.canvas_width, self.canvas_height), parent="canvas")
        print(f"Image displayed on canvas: {image_path}")

    def start_observer(self):
        if not self.game_path:
            return
        event_handler = MyHandler(get_template_path=self.get_template_path)
        self.observer = Observer()
        self.observer.schedule(event_handler, self.game_path, recursive=False)
        self.observer.start()
        print(f"File observer started at: {self.game_path}")

    def get_template_path(self):
        return self.template_path

    def update_ui(self):
        tab_key = camel_to_snake(self.__class__.__name__)
        self.trans = self.main_app.translations.get(self.main_app.current_language, {}).get(tab_key, {})

        dpg.set_value(self.drag_drop_label, self.trans.get("drag_drop_label", "Please select a file to display"))
        dpg.configure_item(self.use_button, label=self.trans.get("use_button", "Use"))
        dpg.configure_item(self.file_path_input, label="")
        dpg.configure_item(self.photo_local_input, label=self.trans.get("photo_local_path_label", "Photo Local Path:"))

        # Обновляем кнопку выбора файла, если есть
        if hasattr(self, 'select_file_button') and self.select_file_button is not None:
            item_type = dpg.get_item_type(self.select_file_button)
            if item_type == 'mvAppItemType::mvButton':
                dpg.configure_item(self.select_file_button, label=self.trans.get("select_file", "Select File"))

        # Обновляем кнопку выбора папки
        if hasattr(self, 'select_folder_button') and self.select_folder_button is not None:
            item_type = dpg.get_item_type(self.select_folder_button)
            if item_type == 'mvAppItemType::mvButton':
                dpg.configure_item(self.select_folder_button, label=self.trans.get("select_folder", "Select Folder"))

        # Обновляем окно, которое появляется при отсутствии пути
        dpg.configure_item("game_path_not_found_popup", label=self.trans.get("game_path_not_found_title", "Path not found"))
        dpg.set_value(self.game_path_not_found_text, self.trans.get("game_path_not_found_text", "Path to 'photo_local' not found.\nSpecify manually or continue searching?"))
        dpg.configure_item(self.game_path_manual_btn, label=self.trans.get("game_path_manual_btn", "Specify manually"))
        dpg.configure_item(self.game_path_continue_btn, label=self.trans.get("game_path_continue_btn", "Continue searching"))
        dpg.configure_item(self.game_path_cancel_btn, label=self.trans.get("game_path_cancel_btn", "Cancel"))

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()
        cleanup_temp_files(self.temp_folder)
        print("Application stopped and temporary files cleaned up.")

    def restore_states(self):
        pass

    def save_states(self):
        pass
