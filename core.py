# core.py

import os
import shutil
import json
import threading
import time
import uuid
from PIL import Image
import cv2
import ctypes
import dearpygui.dearpygui as dpg
from watchdog.events import FileSystemEventHandler
from config import Config
import tkinter as tk
from tkinter import filedialog
from concurrent.futures import ThreadPoolExecutor, as_completed

console = False
TEMPLATE_SOURCE_NAME = "template_source.png"
SUPPORTED_PHOTO_EXTENSIONS = {".png", ".jpg", ".jpeg"}


def is_valid_photo_local_path(path):
    if not path or not os.path.isdir(path):
        return False
    return os.path.basename(os.path.normpath(path)).lower() == "photo_local"

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
        if is_valid_photo_local_path(self.config.game_path):
            self.found_path = self.config.game_path
            print(f"Используется сохранённый путь к игре: {self.found_path}")
            return self.found_path
        if self.config.game_path:
            print(f"Сохранённый путь невалиден и будет проигнорирован: {self.config.game_path}")
        return None

    def search_game_path(self):
        """Осуществляет один проход по дискам в поисках пути."""
        print("Начинается поиск папки 'photo_local' в директории игры 'Once Human' на доступных дисках...")

        drives = [f'{d}:\\' for d in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ' if os.path.exists(f'{d}:')]
        if not drives:
            print("Диски для поиска не найдены.")
            return False

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
        with ThreadPoolExecutor(max_workers=len(drives)) as executor:
            future_to_drive = {executor.submit(search_drive, d): d for d in drives}
            for future in as_completed(future_to_drive):
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
            try:
                if self.search_game_path():
                    self.search_running = False
                    break
            except RuntimeError as exc:
                print(f"Поиск пути остановлен: {exc}")
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
            if not is_valid_photo_local_path(game_path):
                print(f"Выбран неверный путь, ожидалась папка photo_local: {game_path}")
                return False
            self.found_path = game_path
            self.config.game_path = game_path
            self.config.save_to_json()
            print(f"Путь к игре выбран вручную и сохранён: {game_path}")
            return True
        else:
            print("Путь к игре не выбран вручную.")
        return False

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
        os.makedirs(temp_folder, exist_ok=True)
        with Image.open(file_path) as source_image:
            image = source_image.convert("RGB")
        if image.size != (1920, 1080):
            image = resize_image(image, (1920, 1080))
        temp_image = os.path.join(temp_folder, TEMPLATE_SOURCE_NAME)
        image.save(temp_image, format="PNG")
        print(f"Template image prepared at: {temp_image}")
        return temp_image
    except Exception as e:
        print(f"Error processing image: {e}")
        raise

def cleanup_temp_files(temp_folder):
    if not os.path.isdir(temp_folder):
        return

    for filename in os.listdir(temp_folder):
        if filename == TEMPLATE_SOURCE_NAME or filename.startswith("replacement_"):
            file_path = os.path.join(temp_folder, filename)
            if os.path.isfile(file_path):
                os.remove(file_path)


def render_template_for_destination(template_path, destination_path, temp_folder):
    os.makedirs(temp_folder, exist_ok=True)
    extension = os.path.splitext(destination_path)[1].lower()
    if extension not in SUPPORTED_PHOTO_EXTENSIONS:
        extension = ".png"

    replacement_path = os.path.join(temp_folder, f"replacement_{uuid.uuid4().hex}{extension}")
    save_kwargs = {}

    with Image.open(template_path) as source_image:
        image = source_image
        if extension in {".jpg", ".jpeg"}:
            image = image.convert("RGB")
            save_format = "JPEG"
            save_kwargs["quality"] = 95
        else:
            if image.mode not in {"RGB", "RGBA"}:
                image = image.convert("RGBA")
            save_format = "PNG"

        image.save(replacement_path, format=save_format, **save_kwargs)
    return replacement_path


class MyHandler(FileSystemEventHandler):
    def __init__(self, get_template_path, temp_folder, cooldown_seconds=1.0, retry_delays=None):
        super().__init__()
        self.get_template_path = get_template_path
        self.temp_folder = temp_folder
        self.cooldown_seconds = cooldown_seconds
        self.retry_delays = retry_delays or (0.15, 0.3, 0.6, 1.0, 1.5)
        self.last_replaced_at = {}
        self.lock = threading.Lock()

    def _is_supported_event_path(self, path):
        lowered_path = path.lower()
        if "low" in lowered_path:
            print(f"Ignored file: {path}")
            return False
        extension = os.path.splitext(path)[1].lower()
        if extension not in SUPPORTED_PHOTO_EXTENSIONS:
            return False
        return True

    def _is_on_cooldown(self, path):
        normalized_path = os.path.normcase(os.path.normpath(path))
        current_time = time.monotonic()
        with self.lock:
            expired_paths = [
                saved_path
                for saved_path, replaced_at in self.last_replaced_at.items()
                if current_time - replaced_at >= self.cooldown_seconds
            ]
            for expired_path in expired_paths:
                self.last_replaced_at.pop(expired_path, None)

            last_replaced_at = self.last_replaced_at.get(normalized_path)
            if last_replaced_at and current_time - last_replaced_at < self.cooldown_seconds:
                return True

            self.last_replaced_at[normalized_path] = current_time
            return False

    def _queue_replacement(self, path):
        if not self._is_supported_event_path(path):
            return
        if self._is_on_cooldown(path):
            return
        threading.Thread(target=self._replace_file, args=(path,), daemon=True).start()

    def _replace_file(self, destination_path):
        template_file = self.get_template_path()
        if not template_file or not os.path.exists(template_file):
            print(f"Template file not found: {template_file}")
            return

        replacement_file = None
        temp_target = None
        for delay in self.retry_delays:
            time.sleep(delay)
            try:
                if not os.path.exists(destination_path):
                    continue

                replacement_file = render_template_for_destination(template_file, destination_path, self.temp_folder)
                temp_target = os.path.join(
                    os.path.dirname(destination_path),
                    f".once_human_{uuid.uuid4().hex}{os.path.splitext(destination_path)[1].lower()}",
                )
                shutil.copyfile(replacement_file, temp_target)
                os.replace(temp_target, destination_path)
                print(f"Replaced file with template: {destination_path}")
                return
            except PermissionError:
                continue
            except OSError as exc:
                print(f"Replacement retry failed for {destination_path}: {exc}")
            finally:
                if temp_target and os.path.exists(temp_target):
                    try:
                        os.remove(temp_target)
                    except OSError:
                        pass
                if replacement_file and os.path.exists(replacement_file):
                    try:
                        os.remove(replacement_file)
                    except OSError:
                        pass
                temp_target = None
                replacement_file = None

        print(f"Failed to replace file after retries: {destination_path}")

    def on_created(self, event):
        if not event.is_directory:
            self._queue_replacement(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._queue_replacement(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._queue_replacement(event.dest_path)
