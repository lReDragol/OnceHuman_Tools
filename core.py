# core.py

import os
import shutil
import json
import threading
import time
from PIL import Image
import cv2
import subprocess
import ctypes
import dearpygui.dearpygui as dpg
from watchdog.events import FileSystemEventHandler
from config import Config
import tkinter as tk
from tkinter import filedialog
import concurrent.futures

console = False

class PathFinder:
    def __init__(self, config):
        self.config = config
        self.found_path = None
        self.search_running = False
        self.search_completed = False
        self.search_start_time = None
        self.search_timeout = 120  # 2 минуты

    def find_game_path_in_config(self):
        """Возвращает путь из конфига, если он существует и валиден."""
        if self.config.game_path and os.path.exists(self.config.game_path):
            self.found_path = self.config.game_path
            print(f"Используется сохранённый путь к игре: {self.found_path}")
            return self.found_path
        return None

    def search_game_path(self):
        """Осуществляет один проход по дискам в поисках пути."""
        print("Начинается поиск папки 'photo_local' в директории игры 'Once Human' на доступных дисках...")

        drives = [f'{d}:\\' for d in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if os.path.exists(f'{d}:')]

        def search_drive(drive):
            ignore_dirs = {'Windows', 'Program Files', 'Program Files (x86)', 'AppData', 'ProgramData'}

            for root, dirs, files in os.walk(drive, topdown=True):
                dirs[:] = [d for d in dirs if d not in ignore_dirs]
                try:
                    if 'photo_local' in dirs and 'Once Human' in root:
                        path = os.path.join(root, 'photo_local')
                        if os.path.exists(path):
                            return path
                except PermissionError:
                    continue
                except Exception as e:
                    print(f"Ошибка при доступе к {root}: {e}")
                    continue
            return None

        found_path = None
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(drives)) as executor:
            future_to_drive = {executor.submit(search_drive, d): d for d in drives}
            for future in concurrent.futures.as_completed(future_to_drive):
                result = future.result()
                if result:
                    found_path = result
                    executor.shutdown(wait=False, cancel_futures=True)
                    break

        if found_path:
            self.found_path = found_path.replace('/', '\\')
            self.config.game_path = self.found_path
            self.config.save_to_json()
            print(f"Путь к игре найден и сохранён: {self.found_path}")
            return True
        else:
            print("Путь к игре не найден при этом проходе.")
            return False

    def search_game_path_with_timeout(self):
        """
        Запускается в отдельном потоке.
        Выполняет поиск до тех пор, пока не найдёт путь или не истечёт время.
        После 2 минут или по принудительному прерыванию можно остановить поиск.
        """
        self.search_start_time = time.time()
        self.search_running = True
        self.search_completed = False
        while self.search_running:
            if self.search_game_path():
                # Путь найден
                self.search_running = False
                break
            # Проверяем таймаут
            if (time.time() - self.search_start_time) > self.search_timeout:
                # Таймаут истёк, но пользователь может продлить или указать путь вручную
                break
            # Если не нашли, подождём немного, затем попробуем ещё раз, чтобы было "продолжить в автоматическом режиме"
            # Можно сделать паузу перед повторным поиском или просто завершить после одного прохода.
            # В требованиях говорится о продолжении в автоматическом режиме, значит повторный проход.
            time.sleep(5)

        self.search_completed = True
        self.search_running = False

    def choose_game_path_manually(self):
        root = tk.Tk()
        root.withdraw()
        game_path = filedialog.askdirectory(title="Выберите папку 'photo_local'")
        if game_path:
            self.found_path = game_path
            self.config.game_path = game_path
            self.config.save_to_json()
            print(f"Путь к игре выбран вручную и сохранён: {game_path}")
        else:
            print("Путь к игре не выбран вручную.")

def load_translations():
    file_path = os.path.join(os.path.dirname(__file__), 'translations.json')
    print("Loading translations.")
    with open(file_path, 'r', encoding='utf-8') as f:
        print("Translations loaded successfully.")
        return json.load(f)

def get_icon_path(icon_name):
    path = os.path.join(os.path.dirname(__file__), 'data', 'icons', icon_name)
    print(f"Icon path for {icon_name}: {path}")
    return path

def toggle_console():
    global console
    hwnd = ctypes.windll.kernel32.GetConsoleWindow()
    if hwnd == 0:
        ctypes.windll.kernel32.AllocConsole()
        console = True
        print("Console allocated.")
    else:
        console = not console
        if console:
            ctypes.windll.user32.ShowWindow(hwnd, 1)
            print("Console shown.")
        else:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
            print("Console hidden.")

def hide_console_after_delay(delay=5000):
    def hide_console():
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd != 0:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
            print("Console hidden after delay.")

    if not console:
        threading.Timer(delay / 1000, hide_console).start()

def create_temp_folder():
    config = Config.from_json()
    temp_folder = config.temp_folder
    os.makedirs(temp_folder, exist_ok=True)
    print(f"Temporary folder created: {temp_folder}")
    return temp_folder

def resize_image(image, size):
    ratio = min(size[0] / image.size[0], size[1] / image.size[1])
    new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
    image = image.resize(new_size)
    new_image = Image.new("RGB", size)
    new_image.paste(image, ((size[0] - new_size[0]) // 2, (size[1] - new_size[1]) // 2))
    print(f"Image resized to: {new_size}")
    return new_image

def process_image(file_path, temp_folder):
    try:
        print(f"Processing image: {file_path}")
        image = Image.open(file_path)
        if image.size != (1920, 1080):
            image = resize_image(image, (1920, 1080))
            temp_image = os.path.join(temp_folder, "resized_image.jpg")
            image.save(temp_image)
            print(f"Image resized and saved to: {temp_image}")
            return temp_image
        else:
            print(f"Image does not need resizing: {file_path}")
            return file_path
    except Exception as e:
        print(f"Error processing image: {e}")
        raise

def cleanup_temp_files(temp_folder):
    temp_image = os.path.join(temp_folder, "resized_image.jpg")
    if os.path.exists(temp_image):
        os.remove(temp_image)


class MyHandler(FileSystemEventHandler):
    def __init__(self, get_template_path):
        super().__init__()
        self.get_template_path = get_template_path
        self.already_replaced = set()

    def on_created(self, event):
        if not event.is_directory:
            if 'low' in event.src_path.lower():
                print(f'Ignored file: {event.src_path}')
                return

            if event.src_path in self.already_replaced:
                return

            print(f'File created: {event.src_path}')
            template_file = self.get_template_path()
            if template_file and os.path.exists(template_file):
                os.remove(event.src_path)
                shutil.copy(template_file, event.src_path)
                self.already_replaced.add(event.src_path)
                print(f'Заменен на шаблонный файл: {event.src_path}')
            else:
                print(f'Шаблонный файл не найден: {template_file}')
