import cv2
import numpy as np
import tkinter as tk
from tkinter import ttk
import pyautogui
import json
import threading
import time
import pytesseract
from fuzzywuzzy import fuzz
import sys
import mss
import os
import webbrowser
from PyQt5.QtWidgets import QApplication, QLabel, QMainWindow, QFileDialog, QPushButton
from PyQt5.QtGui import QPixmap, QPainter, QPen, QColor
from PyQt5.QtCore import Qt, QRect, QPoint
import telebot
import ctypes
from ctypes import wintypes
from vk_codes import VK_CODE


PUL = ctypes.POINTER(ctypes.c_ulong)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

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
                ("time",wintypes.DWORD),
                ("dwExtraInfo", PUL)]

class INPUT_I(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT),
                ("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD),
                ("ii", INPUT_I)]

# Константы для ввода
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_SCANCODE = 0x0008
KEYEVENTF_EXTENDEDKEY = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

# Функция для отправки ввода
def SendInput(*inputs):
    nInputs = len(inputs)
    LPINPUT = INPUT * nInputs
    pInputs = LPINPUT(*inputs)
    cbSize = ctypes.sizeof(INPUT)
    return ctypes.windll.user32.SendInput(nInputs, pInputs, cbSize)

# Функция для получения виртуального кода клавиши
def get_virtual_key(key):
    return VK_CODE.get(key.lower(), 0)

# Функции для нажатия и отпускания клавиш с использованием SendInput
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

# Переменные и настройки
frame_visible = False
frame_open = False
text_windows_open = {}
text_vars = {}
last_frame = None

bot_enabled = False
stop_event = threading.Event()
text_visible = False
show_all_text = False

original_width, original_height = pyautogui.size()
frame_width = 480
frame_height = int(frame_width * original_height / original_width)

root = tk.Tk()
root.title("OCR Объектное отслеживание и управление")

selected_filter = tk.StringVar(value="Нет фильтра")
selected_filter_value = selected_filter.get()

scan_delay_var = tk.IntVar(value=500)
recognition_threshold_var = tk.IntVar(value=40)
selected_language = tk.StringVar(value='rus')

telegram_bot_enabled = False
telegram_bot_token = ''
telegram_chat_id = ''
bot = None

auto_lmb_enabled = False
last_action_time = time.time()

zones = []
last_press_time = []

# Функции для работы с конфигурацией
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
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
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

# Функция для обновления окна
def update_window():
    global last_frame, frame_visible, frame_open, text_windows_open, text_vars, text_visible, selected_filter_value, show_all_text
    global last_action_time, zones, telegram_bot_enabled, bot, telegram_chat_id, last_press_time
    if not zones:
        return

    scale_x = frame_width / original_width
    scale_y = frame_height / original_height

    if not last_press_time:
        last_press_time = [{} for _ in zones]

    with mss.mss() as sct:
        while not stop_event.is_set():
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            frame = np.array(sct_img)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
            last_frame = frame

            display_frame = apply_filter(frame.copy(), selected_filter_value)
            small_frame = cv2.resize(display_frame, (frame_width, frame_height))

            draw_areas_on_frame(small_frame, zones, scale_x, scale_y)

            if frame_visible:
                cv2.imshow("Frame", small_frame)
                frame_open = True
                cv2.setWindowProperty("Frame", cv2.WND_PROP_TOPMOST, 1 if always_on_top_var.get() else 0)
            elif frame_open:
                cv2.destroyWindow("Frame")
                frame_open = False

            current_time = time.time()
            any_action_performed = False

            for idx, zone_data in enumerate(zones):
                x1, y1, x2, y2 = map(int, zone_data['c'])
                phrases = zone_data.get('p', [])
                zone_num = str(idx+1)
                keybind = zone_data.get('keybind', 'a')
                hold = zone_data.get('hold', False)
                hold_duration = zone_data.get('hold_duration', 0)
                delay_before = zone_data.get('delay_before', 0) / 1000.0
                delay_after = zone_data.get('delay_after', 0) / 1000.0
                press_delay = zone_data.get('press_delay', scan_delay_var.get()) / 1000.0
                hold_lmb = zone_data.get('hold_lmb', False)
                hold_lmb_duration = zone_data.get('hold_lmb_duration', 0)

                zone_last_press_time = last_press_time[idx]

                zone_frame = frame[y1:y2, x1:x2]
                zone_frame_filtered = apply_filter(zone_frame, selected_filter_value)
                ocr_lang = selected_language.get()
                ocr_result_psm6 = pytesseract.image_to_string(zone_frame_filtered, lang=ocr_lang, config='--psm 6')
                ocr_result_psm7 = pytesseract.image_to_string(zone_frame_filtered, lang=ocr_lang, config='--psm 7')

                matched_text = "-"
                action_performed = False
                threshold = recognition_threshold_var.get()

                selected_phrase = zone_data.get('selected_phrase', 'All')

                if selected_phrase == 'All':
                    phrases_to_check = phrases
                else:
                    phrases_to_check = [selected_phrase]

                recognized_text_psm6 = ocr_result_psm6.lower()
                recognized_text_psm7 = ocr_result_psm7.lower()

                for phrase in phrases_to_check:
                    target_phrase = phrase.lower()
                    if target_phrase in recognized_text_psm6 or target_phrase in recognized_text_psm7:
                        matched_text = phrase
                        break
                    else:
                        ratio_psm6 = fuzz.partial_ratio(target_phrase, recognized_text_psm6)
                        ratio_psm7 = fuzz.partial_ratio(target_phrase, recognized_text_psm7)
                        if ratio_psm6 > threshold or ratio_psm7 > threshold:
                            matched_text = phrase
                            break

                if matched_text != "-":
                    last_press = zone_last_press_time.get(matched_text, 0)
                    if current_time - last_press >= press_delay:
                        if bot_enabled:
                            if keybind == 'Тригер':
                                if telegram_bot_enabled and bot:
                                    message_text = f"Найдена '{matched_text}' в зоне {zone_num}"
                                    try:
                                        bot.send_message(telegram_chat_id, message_text)
                                        print(f"Отправлено сообщение в Telegram: {message_text}")
                                    except Exception as e:
                                        print(f"Ошибка отправки сообщения в Telegram: {e}")
                                else:
                                    print("Telegram бот не активирован или не настроен.")
                            else:
                                def perform_action(keybind=keybind, hold_duration=hold_duration, delay_before=delay_before, delay_after=delay_after, hold_lmb=hold_lmb, hold_lmb_duration=hold_lmb_duration):
                                    time.sleep(delay_before)
                                    press_key(keybind)
                                    if hold_duration > 0:
                                        time.sleep(hold_duration / 1000.0)
                                    release_key(keybind)
                                    if hold_lmb:
                                        pyautogui.mouseDown(button='left')
                                        threading.Timer(hold_lmb_duration / 1000.0, pyautogui.mouseUp, kwargs={'button':'left'}).start()
                                    time.sleep(delay_after)
                                threading.Thread(target=perform_action).start()
                                print(f"Удержание клавиши: {keybind}")
                        action_performed = True
                        zone_last_press_time[matched_text] = current_time
                        last_action_time = current_time
                        print(f"Распознано '{matched_text}' в зоне {zone_num}")
                else:
                    matched_text = "-"

                if action_performed:
                    any_action_performed = True

                if text_visible:
                    if zone_num not in text_windows_open:
                        text_window = tk.Toplevel(root)
                        text_window.title(f"Текст зоны {zone_num}")
                        text_window.geometry(f"200x100")
                        text_window.configure(bg='black')
                        text_window.attributes('-topmost', always_on_top_var.get())
                        text_windows_open[zone_num] = text_window

                        text_var = tk.StringVar()
                        text_vars[zone_num] = text_var

                        text_label = tk.Label(text_window, textvariable=text_var, justify='left', anchor='nw', bg='black', fg='white')
                        text_label.pack(fill='both', expand=True)

                        window_x, window_y = calculate_window_position(idx)
                        text_window.geometry(f"200x100+{window_x}+{window_y}")
                    else:
                        text_window = text_windows_open[zone_num]
                        text_window.attributes('-topmost', always_on_top_var.get())

                    if show_all_text:
                        text_content = f"{ocr_result_psm6.strip()} | {ocr_result_psm7.strip()}"
                    else:
                        text_content = matched_text if action_performed else "-"
                    text_vars[zone_num].set(text_content)
                elif zone_num in text_windows_open:
                    text_windows_open[zone_num].destroy()
                    del text_windows_open[zone_num]
                    del text_vars[zone_num]

            if auto_lmb_enabled and (current_time - last_action_time > 10):
                pyautogui.click()
                print("Выполнен Авто ЛКМ")
                last_action_time = current_time

            key = cv2.waitKey(1)
            if key == ord('q'):
                stop_event.set()
                break

    cv2.destroyAllWindows()
    for window in text_windows_open.values():
        window.destroy()
    text_windows_open.clear()
    text_vars.clear()

# Остальные функции и настройки
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

def toggle_frame_visibility():
    global frame_visible
    frame_visible = not frame_visible

def toggle_text_visibility():
    global text_visible
    text_visible = not text_visible

def toggle_show_all_text():
    global show_all_text
    show_all_text = not show_all_text

def toggle_bot_enabled():
    global bot_enabled
    bot_enabled = not bot_enabled
    print(f"Бот включен: {bot_enabled}")

def toggle_always_on_top():
    is_always_on_top = always_on_top_var.get()
    root.attributes('-topmost', is_always_on_top)

    if frame_open:
        cv2.setWindowProperty("Frame", cv2.WND_PROP_TOPMOST, 1 if is_always_on_top else 0)

    for zone_num in text_windows_open.keys():
        text_windows_open[zone_num].attributes('-topmost', is_always_on_top)

def toggle_auto_lmb():
    global auto_lmb_enabled
    auto_lmb_enabled = auto_lmb_var.get()
    if auto_lmb_enabled:
        print("Авто ЛКМ включен")
    else:
        print("Авто ЛКМ выключен")

def on_closing():
    stop_event.set()
    root.destroy()

def start_tracking():
    global stop_event, zones, last_press_time
    config = load_config("config.json")
    zones = config.get('zones', [])
    update_zones_display()
    stop_event.clear()
    last_press_time = [{} for _ in zones]
    threading.Thread(target=update_window).start()

def stop_tracking():
    stop_event.set()

def on_filter_change(event):
    global selected_filter_value
    selected_filter_value = selected_filter.get()

def toggle_telegram_bot():
    global telegram_bot_enabled, bot, telegram_bot_token, telegram_chat_id
    telegram_bot_enabled = telegram_bot_var.get()
    if telegram_bot_enabled:
        telegram_bot_token = bot_token_entry.get()
        telegram_chat_id = chat_id_entry.get()
        if telegram_bot_token and telegram_chat_id:
            try:
                bot = telebot.TeleBot(telegram_bot_token)
                print("Telegram бот активирован.")

                config = load_config("config.json")
                config["telegram_bot_token"] = telegram_bot_token
                config["telegram_chat_id"] = telegram_chat_id
                save_config(config, "config.json")

            except Exception as e:
                print(f"Ошибка инициализации Telegram бота: {e}")
                telegram_bot_enabled = False
                telegram_bot_var.set(False)
        else:
            print("Пожалуйста, введите Bot Token и Chat ID.")
            telegram_bot_enabled = False
            telegram_bot_var.set(False)
    else:
        bot = None
        print("Telegram бот деактивирован.")

always_on_top_var = tk.BooleanVar()
auto_lmb_var = tk.BooleanVar()

frame_checkbox = tk.Checkbutton(root, text="Показать кадр", command=toggle_frame_visibility)
frame_checkbox.grid(row=0, column=0, padx=10, pady=5, sticky='w')

text_checkbox = tk.Checkbutton(root, text="Показать текст OCR", command=toggle_text_visibility)
text_checkbox.grid(row=1, column=0, padx=10, pady=5, sticky='w')

show_all_text_checkbox = tk.Checkbutton(root, text="Показывать весь распознанный текст", command=toggle_show_all_text)
show_all_text_checkbox.grid(row=2, column=0, padx=10, pady=5, sticky='w')

bot_checkbox = tk.Checkbutton(root, text="Включить бота", command=toggle_bot_enabled)
bot_checkbox.grid(row=3, column=0, padx=10, pady=5, sticky='w')

always_on_top_checkbox = tk.Checkbutton(root, text="Всегда сверху", variable=always_on_top_var,
                                        command=toggle_always_on_top)
always_on_top_checkbox.grid(row=4, column=0, padx=10, pady=5, sticky='w')

auto_lmb_checkbox = tk.Checkbutton(root, text="Авто ЛКМ", variable=auto_lmb_var, command=toggle_auto_lmb)
auto_lmb_checkbox.grid(row=5, column=0, padx=10, pady=5, sticky='w')

filter_label = tk.Label(root, text="Выбрать фильтр:")
filter_label.grid(row=6, column=0, padx=10, pady=5, sticky='w')

filter_options = ["Нет фильтра", "Градации серого", "Бинарный порог", "Края Кэнни"]
filter_menu = ttk.Combobox(root, values=filter_options, textvariable=selected_filter, state="readonly")
filter_menu.grid(row=7, column=0, padx=10, pady=5, sticky='w')
filter_menu.current(0)
filter_menu.bind("<<ComboboxSelected>>", on_filter_change)

start_button = tk.Button(root, text="Начать отслеживание", command=start_tracking)
start_button.grid(row=8, column=0, padx=10, pady=5, sticky='w')

stop_button = tk.Button(root, text="Остановить отслеживание", command=stop_tracking)
stop_button.grid(row=9, column=0, padx=10, pady=5, sticky='w')

zones_frame = tk.Frame(root)
zones_frame.grid(row=0, column=1, rowspan=15, padx=10, pady=5, sticky='n')

def update_zones_display():
    global zones
    for widget in zones_frame.winfo_children():
        widget.destroy()
    config = load_config("config.json")
    zones = config.get('zones', [])
    if not zones:
        return
    tk.Label(zones_frame, text="Зона").grid(row=0, column=0, padx=5, pady=5)
    tk.Label(zones_frame, text="Клавиша").grid(row=0, column=1, padx=5, pady=5)
    tk.Label(zones_frame, text="Удержание").grid(row=0, column=2, padx=5, pady=5)
    tk.Label(zones_frame, text="Продолжительность (мс)").grid(row=0, column=3, padx=5, pady=5)
    tk.Label(zones_frame, text="Задержка (мс) до").grid(row=0, column=4, padx=5, pady=5)
    tk.Label(zones_frame, text="Задержка (мс) после").grid(row=0, column=5, padx=5, pady=5)
    tk.Label(zones_frame, text="Фразы").grid(row=0, column=6, columnspan=3, padx=5, pady=5)
    key_options = ['a', 'd', 'f', 'left mouse button', 'Тригер']
    hold_options = ['Да', 'Нет']
    for idx, zone in enumerate(zones):
        zone_num = idx + 1
        tk.Label(zones_frame, text=f"{zone_num}").grid(row=zone_num, column=0, padx=5, pady=5)
        keybind_var = tk.StringVar(value=zone.get('keybind', 'a'))
        keybind_menu = ttk.Combobox(zones_frame, textvariable=keybind_var, width=15)
        keybind_menu['values'] = key_options
        keybind_menu.set(zone.get('keybind', 'a'))
        keybind_menu.grid(row=zone_num, column=1, padx=5, pady=5)
        keybind_menu.config(state='normal')

        hold_var = tk.StringVar(value='Да' if zone.get('hold', False) else 'Нет')
        hold_menu = ttk.Combobox(zones_frame, values=hold_options, textvariable=hold_var, state="readonly", width=10)
        hold_menu.grid(row=zone_num, column=2, padx=5, pady=5)
        hold_duration_var = tk.StringVar(value=str(zone.get('hold_duration', 0)))
        hold_duration_entry = tk.Entry(zones_frame, textvariable=hold_duration_var, width=15)
        hold_duration_entry.grid(row=zone_num, column=3, padx=5, pady=5)

        delay_before_var = tk.StringVar(value=str(zone.get('delay_before', 0)))
        delay_before_entry = tk.Entry(zones_frame, textvariable=delay_before_var, width=15)
        delay_before_entry.grid(row=zone_num, column=4, padx=5, pady=5)

        delay_after_var = tk.StringVar(value=str(zone.get('delay_after', scan_delay_var.get())))
        delay_after_entry = tk.Entry(zones_frame, textvariable=delay_after_var, width=15)
        delay_after_entry.grid(row=zone_num, column=5, padx=5, pady=5)

        add_phrase_button = tk.Button(zones_frame, text="+", command=lambda i=idx: add_phrase(i))
        add_phrase_button.grid(row=zone_num, column=6, padx=5, pady=5)
        remove_phrase_button = tk.Button(zones_frame, text="-", command=lambda i=idx: remove_phrase(i))
        remove_phrase_button.grid(row=zone_num, column=7, padx=5, pady=5)
        phrases_var = tk.StringVar()
        phrases_combobox = ttk.Combobox(zones_frame, textvariable=phrases_var, state="readonly", width=15)
        phrases_combobox.grid(row=zone_num, column=8, padx=5, pady=5)

        # Присваиваем phrases_var и phrases_combobox перед вызовом update_phrases_combobox
        zone['phrases_var'] = phrases_var
        zone['phrases_combobox'] = phrases_combobox

        update_phrases_combobox(idx, phrases_combobox)

        selected_phrase = zone.get('selected_phrase', 'All')
        if selected_phrase in phrases_combobox['values']:
            phrases_var.set(selected_phrase)
        else:
            phrases_var.set('All')

        hold_lmb_var = tk.BooleanVar(value=zone.get('hold_lmb', False))
        hold_lmb_checkbox = tk.Checkbutton(zones_frame, text="Дожать лкм", variable=hold_lmb_var)
        hold_lmb_checkbox.grid(row=zone_num, column=9, padx=5, pady=5)

        hold_lmb_duration_var = tk.StringVar(value=str(zone.get('hold_lmb_duration', 0)))
        hold_lmb_duration_entry = tk.Entry(zones_frame, textvariable=hold_lmb_duration_var, width=10)
        hold_lmb_duration_entry.grid(row=zone_num, column=10, padx=5, pady=5)

        zone['keybind_var'] = keybind_var
        zone['hold_var'] = hold_var
        zone['hold_duration_var'] = hold_duration_var
        zone['delay_before_var'] = delay_before_var
        zone['delay_after_var'] = delay_after_var
        zone['hold_lmb_var'] = hold_lmb_var
        zone['hold_lmb_duration_var'] = hold_lmb_duration_var

    save_zones_button = tk.Button(zones_frame, text="Сохранить настройки зон", command=save_zones_settings)
    save_zones_button.grid(row=len(zones)+1, column=0, columnspan=11, padx=5, pady=10)

def update_phrases_combobox(idx, phrases_combobox):
    zone = zones[idx]
    phrases = zone.get('p', [])
    phrases_options = ['All'] + phrases
    phrases_combobox['values'] = phrases_options
    selected_phrase = zone.get('selected_phrase', 'All')
    if selected_phrase in phrases_options:
        zone['phrases_var'].set(selected_phrase)
    else:
        zone['phrases_var'].set('All')

def add_phrase(idx):
    zone = zones[idx]
    def save_phrase():
        phrase = new_phrase_var.get()
        if phrase:
            zone.setdefault('p', []).append(phrase)
            update_phrases_combobox(idx, zone['phrases_combobox'])
            phrase_window.destroy()

    phrase_window = tk.Toplevel(root)
    phrase_window.title(f"Добавить фразу в зону {idx+1}")
    tk.Label(phrase_window, text="Введите фразу:").grid(row=0, column=0, padx=5, pady=5)
    new_phrase_var = tk.StringVar()
    phrase_entry = tk.Entry(phrase_window, textvariable=new_phrase_var)
    phrase_entry.grid(row=0, column=1, padx=5, pady=5)
    phrase_entry.focus_set()

    tk.Button(phrase_window, text="Сохранить", command=save_phrase).grid(row=1, column=0, columnspan=2, padx=5, pady=5)

def remove_phrase(idx):
    zone = zones[idx]
    selected_phrase = zone['phrases_var'].get()
    if selected_phrase == 'All':
        return
    if 'p' in zone and selected_phrase in zone['p']:
        zone['p'].remove(selected_phrase)
        update_phrases_combobox(idx, zone['phrases_combobox'])

def save_zones_settings():
    global zones
    cleaned_zones = []
    for idx, zone in enumerate(zones):
        keybind = zone['keybind_var'].get()
        hold = True if zone['hold_var'].get() == 'Да' else False
        try:
            hold_duration = int(zone['hold_duration_var'].get())
        except ValueError:
            hold_duration = 0
        try:
            delay_before = int(zone['delay_before_var'].get())
        except ValueError:
            delay_before = 0
        try:
            delay_after = int(zone['delay_after_var'].get())
        except ValueError:
            delay_after = scan_delay_var.get()
        hold_lmb = zone['hold_lmb_var'].get()
        try:
            hold_lmb_duration = int(zone['hold_lmb_duration_var'].get())
        except ValueError:
            hold_lmb_duration = 0

        selected_phrase = zone['phrases_var'].get()

        cleaned_zone = {
            'c': zone['c'],
            'p': zone.get('p', []),
            'keybind': keybind,
            'hold': hold,
            'hold_duration': hold_duration,
            'delay_before': delay_before,
            'delay_after': delay_after,
            'hold_lmb': hold_lmb,
            'hold_lmb_duration': hold_lmb_duration,
            'selected_phrase': selected_phrase
        }
        cleaned_zones.append(cleaned_zone)
    config = load_config("config.json")
    config['zones'] = cleaned_zones
    save_config(config, "config.json")
    print("Настройки зон сохранены.")

    config = load_config("config.json")
    zones = config.get('zones', [])
    update_zones_display()

scan_delay_label = tk.Label(root, text="Задержка между нажатиями (мс):")
scan_delay_label.grid(row=13, column=0, padx=10, pady=5, sticky='w')

scan_delay_entry = tk.Entry(root, textvariable=scan_delay_var)
scan_delay_entry.grid(row=13, column=1, padx=10, pady=5, sticky='w')

threshold_label = tk.Label(root, text="Порог распознавания (%):")
threshold_label.grid(row=14, column=0, padx=10, pady=5, sticky='w')

threshold_scale = tk.Scale(root, from_=0, to=100, orient='horizontal', variable=recognition_threshold_var)
threshold_scale.grid(row=14, column=1, padx=10, pady=5, sticky='w')

language_label = tk.Label(root, text="Язык OCR:")
language_label.grid(row=15, column=0, padx=10, pady=5, sticky='w')

language_options = ['eng', 'rus']
language_menu = ttk.Combobox(root, values=language_options, textvariable=selected_language, state="readonly")
language_menu.grid(row=15, column=1, padx=10, pady=5, sticky='w')
language_menu.current(0)

github_label = tk.Label(root, text="GitHub Repository", fg="blue", cursor="hand2", bg="lightblue",
                        font=("Arial", 10, "underline"))
github_label.grid(row=16, column=0, columnspan=2, padx=10, pady=5, sticky='sw')
github_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://github.com/lReDragol"))

telegram_bot_var = tk.BooleanVar()
telegram_bot_checkbox = tk.Checkbutton(root, text="Включить Telegram бота", variable=telegram_bot_var, command=toggle_telegram_bot)
telegram_bot_checkbox.grid(row=17, column=0, padx=10, pady=5, sticky='w')

bot_token_label = tk.Label(root, text="Bot Token:")
bot_token_label.grid(row=18, column=0, padx=10, pady=5, sticky='w')
bot_token_entry = tk.Entry(root)
bot_token_entry.grid(row=18, column=1, padx=10, pady=5, sticky='w')

chat_id_label = tk.Label(root, text="Chat ID:")
chat_id_label.grid(row=19, column=0, padx=10, pady=5, sticky='w')
chat_id_entry = tk.Entry(root)
chat_id_entry.grid(row=19, column=1, padx=10, pady=5, sticky='w')

config = load_config("config.json")
bot_token_entry.insert(0, config.get('telegram_bot_token', ''))
chat_id_entry.insert(0, config.get('telegram_chat_id', ''))

root.protocol("WM_DELETE_WINDOW", on_closing)

update_zones_display()

# Класс для создания зон
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

    def take_screenshot(self):
        self.hide()
        time.sleep(0.5)
        screenshot = pyautogui.screenshot()
        screenshot_path = "screenshot.png"
        screenshot.save(screenshot_path)
        self.open_screenshot_selector(screenshot_path)
        self.show()

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
        config_data["zones"] = []
        for i, rect in enumerate(self.rectangles):
            x1, y1 = rect.topLeft().x(), rect.topLeft().y()
            x2, y2 = rect.bottomRight().x(), rect.bottomRight().y()
            config_data["zones"].append({
                "c": [x1, y1, x2, y2],
                "p": []
            })

        save_config(config_data, "config.json")
        print("Конфигурация сохранена в config.json")
        self.close()
        root.after(0, update_zones_display)

    def clear_rectangles(self):
        self.rectangles = []
        self.image_label.setPixmap(self.backup_image)
        self.update()

def start_zone_creation():
    app = QApplication(sys.argv)
    main_menu = MainMenu()
    app.exec_()

zone_creation_button = tk.Button(root, text="Создать зоны", command=lambda: threading.Thread(target=start_zone_creation).start())
zone_creation_button.grid(row=12, column=0, padx=10, pady=10, sticky='w')

root.mainloop()
cv2.destroyAllWindows()
