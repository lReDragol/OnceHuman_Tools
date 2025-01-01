#functions.py

import cv2
import pyautogui
import json
import time
import pytesseract
import os
import ctypes
from ctypes import wintypes
from vk_codes import VK_CODE
import sys

from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QFileDialog, QPushButton
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QRect, QPoint

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

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


class MainMenu(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Создание зон')
        self.setGeometry(100, 100, 400, 200)

        load_button = QPushButton('Загрузить скриншот', self)
        load_button.setGeometry(50, 80, 150, 40)
        load_button.clicked.connect(self.load_screenshot)

        screenshot_button = QPushButton('Сделать скриншот', self)
        screenshot_button.setGeometry(210, 80, 150, 40)
        screenshot_button.clicked.connect(self.take_screenshot)

        self.show()

    def load_screenshot(self):
        image_path, _ = QFileDialog.getOpenFileName(self, 'Выберите изображение', '', 'PNG files (*.png);;JPEG files (*.jpg *.jpeg)')
        if image_path:
            self.open_screenshot_selector(image_path)
            self.close()

    def take_screenshot(self):
        self.hide()
        time.sleep(0.5)
        screenshot = pyautogui.screenshot()
        screenshot_path = "screenshot.png"
        screenshot.save(screenshot_path)
        self.open_screenshot_selector(screenshot_path)
        self.close()

    def open_screenshot_selector(self, image_path):
        self.selector_window = ScreenshotSelector(image_path)
        self.selector_window.show()


class ScreenshotSelector(QMainWindow):
    def __init__(self, image_path):
        super().__init__()
        self.setWindowTitle('Выбор областей')
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

        self.save_button = QPushButton('Сохранить', self)
        self.save_button.setGeometry(10, 10, 100, 30)
        self.save_button.clicked.connect(self.save_config)

        self.clear_button = QPushButton('Очистить', self)
        self.clear_button.setGeometry(120, 10, 100, 30)
        self.clear_button.clicked.connect(self.clear_rectangles)

    def load_image(self, image_path):
        self.image = QPixmap(image_path)
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
        config_data = load_config("config.json")
        existing_zones = config_data.get("zones", [])
        for rect in self.rectangles:
            x1, y1 = rect.topLeft().x(), rect.topLeft().y()
            x2, y2 = rect.bottomRight().x(), rect.bottomRight().y()
            existing_zones.append({
                "c": [x1, y1, x2, y2],
                "p": []
            })
        config_data["zones"] = existing_zones

        save_config(config_data, "config.json")
        print("Конфигурация сохранена в config.json")
        self.close()

    def clear_rectangles(self):
        self.rectangles = []
        self.image_label.setPixmap(self.backup_image)
        self.update()


def start_zone_creation(callback=None):
    app = QApplication(sys.argv)
    main_menu = MainMenu()
    app.exec_()
    if callback:
        callback()
