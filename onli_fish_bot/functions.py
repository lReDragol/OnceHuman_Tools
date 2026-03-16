#functions.py

import cv2
import pyautogui
import json
import time
import os
import ctypes
import subprocess
import tempfile
from ctypes import wintypes
from vk_codes import VK_CODE
import sys

from PIL import ImageGrab
from PySide6.QtCore import QEventLoop, QPoint, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow, QPushButton

PUL = ctypes.POINTER(ctypes.c_ulong)


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD),
                ("wScan", wintypes.WORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", PUL)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG),
                ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD),
                ("dwExtraInfo", PUL)]


class INPUT_I(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT),
                ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD),
                ("ii", INPUT_I)]


INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_EXTENDEDKEY = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
SW_MINIMIZE = 6


ZONE_CREATION_TEXT = {
    "window_title": "Выбор областей",
    "save_button": "Сохранить",
    "clear_button": "Очистить",
}


def SendInput(*inputs):
    nInputs = len(inputs)
    LPINPUT = INPUT * nInputs
    pInputs = LPINPUT(*inputs)
    cbSize = ctypes.sizeof(INPUT)
    return ctypes.windll.user32.SendInput(nInputs, pInputs, cbSize)


def get_virtual_key(key):
    return VK_CODE.get(key.lower(), 0)


def press_key(key):
    if key == 'left mouse button':
        input_struct = INPUT(type=INPUT_MOUSE,
                             ii=INPUT_I(mi=MOUSEINPUT(dx=0,
                                                      dy=0,
                                                      mouseData=0,
                                                      dwFlags=MOUSEEVENTF_LEFTDOWN,
                                                      time=0,
                                                      dwExtraInfo=None)))
        SendInput(input_struct)
        print(f"Нажата кнопка мыши")
    else:
        vk = get_virtual_key(key)
        if vk == 0:
            print(f"Неизвестная клавиша: {key}")
            return
        input_struct = INPUT(type=INPUT_KEYBOARD,
                             ii=INPUT_I(ki=KEYBDINPUT(wVk=vk,
                                                      wScan=0,
                                                      dwFlags=0,
                                                      time=0,
                                                      dwExtraInfo=None)))
        SendInput(input_struct)
        print(f"Нажата клавиша: {key}")


def release_key(key):
    if key == 'left mouse button':
        input_struct = INPUT(type=INPUT_MOUSE,
                             ii=INPUT_I(mi=MOUSEINPUT(dx=0,
                                                      dy=0,
                                                      mouseData=0,
                                                      dwFlags=MOUSEEVENTF_LEFTUP,
                                                      time=0,
                                                      dwExtraInfo=None)))
        SendInput(input_struct)
        print(f"Отпущена кнопка мыши")
    else:
        vk = get_virtual_key(key)
        if vk == 0:
            print(f"Неизвестная клавиша: {key}")
            return
        input_struct = INPUT(type=INPUT_KEYBOARD,
                             ii=INPUT_I(ki=KEYBDINPUT(wVk=vk,
                                                      wScan=0,
                                                      dwFlags=KEYEVENTF_KEYUP,
                                                      time=0,
                                                      dwExtraInfo=None)))
        SendInput(input_struct)
        print(f"Отпущена клавиша: {key}")


def load_config(filename):
    if not os.path.exists(filename):
        default_config = {
            "zones": [],
            "telegram_bot_token": "",
            "telegram_chat_id": ""
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False)
            print(f"Создан новый файл конфигурации: {filename}")
        return default_config
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except json.JSONDecodeError as e:
        print(f"Ошибка загрузки конфигурации: {e}")
        default_config = {
            "zones": [],
            "telegram_bot_token": "",
            "telegram_chat_id": ""
        }
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, ensure_ascii=False)
            print(f"Создан новый файл конфигурации по умолчанию: {filename}")
        return default_config
    except Exception as e:
        print(f"Ошибка загрузки конфигурации: {e}")
        return {}


def save_config(config, filename):
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print(f"Конфигурация сохранена в {filename}")
    except Exception as e:
        print(f"Ошибка сохранения конфигурации: {e}")


def apply_filter(image, filter_name):
    if filter_name == "Нет фильтра":
        return image
    elif filter_name == "Градации серого":
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif filter_name == "Бинарный порог":
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY)
        return thresh
    elif filter_name == "Края Кэнни":
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        return edges
    else:
        return image


def draw_areas_on_frame(frame, zones, scale_x, scale_y):
    for idx, zone_data in enumerate(zones):
        coordinates = zone_data['c']
        scaled_coords = scale_coordinates(coordinates, scale_x, scale_y)
        x1, y1, x2, y2 = scaled_coords
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.putText(frame, str(idx+1), (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)


def scale_coordinates(coordinates, scale_x, scale_y):
    x1, y1, x2, y2 = coordinates
    return int(x1 * scale_x), int(y1 * scale_y), int(x2 * scale_x), int(y2 * scale_y)


def calculate_window_position(index):
    screen_width, screen_height = pyautogui.size()
    window_width, window_height = 200, 100
    x = 0
    y = index * (window_height + 10)
    if y + window_height > screen_height:
        y = 0
        x += window_width + 10
    return x, y


def _clear_clipboard():
    user32 = ctypes.windll.user32
    if not user32.OpenClipboard(None):
        return
    try:
        user32.EmptyClipboard()
    finally:
        user32.CloseClipboard()


def _minimize_foreground_window():
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    if hwnd:
        ctypes.windll.user32.ShowWindow(hwnd, SW_MINIMIZE)


def _launch_windows_snipping():
    try:
        os.startfile("ms-screenclip:")
        return True
    except OSError:
        try:
            subprocess.Popen(["explorer.exe", "ms-screenclip:"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except Exception:
            return False


def capture_zone_screenshot():
    screenshot_path = os.path.join(tempfile.gettempdir(), "once_human_portable_zone_capture.png")
    _clear_clipboard()
    _minimize_foreground_window()
    time.sleep(0.2)

    if _launch_windows_snipping():
        deadline = time.time() + 45
        while time.time() < deadline:
            clipboard_content = ImageGrab.grabclipboard()
            if hasattr(clipboard_content, "save"):
                clipboard_content.save(screenshot_path)
                return screenshot_path
            time.sleep(0.25)
        return None

    screenshot = pyautogui.screenshot()
    screenshot.save(screenshot_path)
    return screenshot_path


class ScreenshotSelector(QMainWindow):
    def __init__(self, image_path, config_path, ui_text=None, result_holder=None):
        super().__init__()
        self.config_path = config_path
        self.ui_text = {**ZONE_CREATION_TEXT, **(ui_text or {})}
        self.result_holder = result_holder if result_holder is not None else {"saved": False}
        self.setAttribute(Qt.WA_DeleteOnClose, True)
        self.setWindowTitle(self.ui_text["window_title"])
        self.setGeometry(100, 100, 800, 600)

        self.image_label = QLabel(self)
        self.image_label.setGeometry(0, 0, 800, 600)
        self.image_label.setAlignment(Qt.AlignCenter)

        self.start_point = QPoint()
        self.end_point = QPoint()
        self.rectangles = []

        self.load_image(image_path)
        self.initUI()

    def initUI(self):
        self.image_label.mousePressEvent = self.on_mouse_press
        self.image_label.mouseMoveEvent = self.on_mouse_move
        self.image_label.mouseReleaseEvent = self.on_mouse_release

        self.save_button = QPushButton(self.ui_text["save_button"], self)
        self.save_button.setGeometry(10, 10, 100, 30)
        self.save_button.clicked.connect(self.save_config)

        self.clear_button = QPushButton(self.ui_text["clear_button"], self)
        self.clear_button.setGeometry(120, 10, 100, 30)
        self.clear_button.clicked.connect(self.clear_rectangles)

    def load_image(self, image_path):
        self.image = QPixmap(image_path)
        self.backup_image = self.image.copy()
        self.image_label.setPixmap(self.image)
        self.image_label.adjustSize()

    def on_mouse_press(self, event):
        if event.button() == Qt.LeftButton:
            self.start_point = event.pos()
            self.end_point = self.start_point
            self.backup_image = self.image.copy()

    def on_mouse_move(self, event):
        if event.buttons() & Qt.LeftButton:
            self.end_point = event.pos()
            self.image_label.setPixmap(self.backup_image)
            self.update()

    def on_mouse_release(self, event):
        if event.button() == Qt.LeftButton:
            rect = QRect(self.start_point, self.end_point).normalized()
            self.rectangles.append(rect)
            self.start_point = QPoint()
            self.end_point = QPoint()
            self.backup_image = self.image.copy()
            self.update()

    def paintEvent(self, event):
        if self.image_label.pixmap():
            painter = QPainter(self.image_label.pixmap())
            pen = QPen(QColor(255, 0, 0), 2)
            painter.setPen(pen)
            font = painter.font()
            font.setPointSize(20)
            painter.setFont(font)

            for i, rect in enumerate(self.rectangles):
                painter.drawRect(rect)
                text = str(i + 1)
                painter.drawText(rect.center(), text)

            if not self.start_point.isNull() and not self.end_point.isNull():
                painter.drawRect(QRect(self.start_point, self.end_point).normalized())

            painter.end()

    def save_config(self):
        config_data = load_config(self.config_path)
        existing_zones = config_data.get("zones", [])
        for rect in self.rectangles:
            x1, y1 = rect.topLeft().x(), rect.topLeft().y()
            x2, y2 = rect.bottomRight().x(), rect.bottomRight().y()
            existing_zones.append({
                "c": [x1, y1, x2, y2],
                "p": []
            })
        config_data["zones"] = existing_zones

        save_config(config_data, self.config_path)
        self.result_holder["saved"] = True
        print(f"Конфигурация сохранена в {self.config_path}")
        self.close()

    def clear_rectangles(self):
        self.rectangles = []
        self.image_label.setPixmap(self.backup_image)
        self.update()


def start_zone_creation(config_path="config.json", callback=None, ui_text=None):
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)

    screenshot_path = capture_zone_screenshot()
    if not screenshot_path or not os.path.exists(screenshot_path):
        return False

    result_holder = {"saved": False}
    selector = ScreenshotSelector(
        screenshot_path,
        config_path,
        ui_text=ui_text,
        result_holder=result_holder,
    )
    selector.show()
    loop = QEventLoop()
    selector.destroyed.connect(loop.quit)
    loop.exec()
    if result_holder["saved"] and callback:
        callback()
    return result_holder["saved"]
