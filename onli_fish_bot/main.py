#main.py
import tkinter as tk
from tkinter import ttk
import threading
import cv2
import webbrowser
from functions import (
    load_config, save_config, apply_filter, draw_areas_on_frame,
    scale_coordinates, calculate_window_position, start_zone_creation,
    press_key, release_key
)
import pyautogui
import numpy as np
import mss
import pytesseract
from fuzzywuzzy import fuzz
import time
import telebot
import copy  # Импортируем модуль copy


# Переменные и настройки
frame_visible = False
frame_open = False
text_windows_open = {}
text_vars = {}
last_frame = None

bot_enabled = False
stop_event = threading.Event()
action_in_progress = threading.Event()
text_visible = False
show_all_text = False

original_width, original_height = pyautogui.size()
frame_width = 480
frame_height = int(frame_width * original_height / original_width)

root = tk.Tk()
root.title("Bot Fish")

selected_filter = tk.StringVar(value="Нет фильтра")
selected_filter_value = selected_filter.get()

scan_delay_var = tk.IntVar(value=500)
recognition_threshold_var = tk.IntVar(value=40)
selected_language = tk.StringVar(value='rus')

telegram_bot_token = ''
telegram_chat_id = ''
bot = None

anti_afk_enabled = False
last_action_time = time.time()
anti_afk_delay_var = tk.IntVar(value=10)

zones = []
zones_tk_vars = []  # Создаем список для хранения tk_vars отдельно
last_press_time = []

def update_window():
    global last_frame, frame_visible, frame_open, text_windows_open, text_vars, text_visible, selected_filter_value, show_all_text
    global last_action_time, zones, bot, telegram_chat_id, last_press_time
    if not zones:
        return

    scale_x = frame_width / original_width
    scale_y = frame_height / original_height

    if not last_press_time or len(last_press_time) != len(zones):
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
                        if action_in_progress.is_set():
                            continue
                        if bot_enabled:
                            if keybind == 'TGBot':
                                if telegram_bot_var.get() and bot:
                                    message_text = f"Найдена '{matched_text}' в зоне {zone_num}"
                                    try:
                                        bot.send_message(telegram_chat_id, message_text)
                                        print(f"{time.strftime('%H:%M:%S')} Отправлено сообщение в Telegram: {message_text}")
                                    except Exception as e:
                                        print(f"{time.strftime('%H:%M:%S')} Ошибка отправки сообщения в Telegram: {e}")
                                else:
                                    print(f"{time.strftime('%H:%M:%S')} Telegram бот не активирован или не настроен.")
                            else:
                                def perform_action(keybind=keybind, hold_duration=hold_duration, delay_before=delay_before, delay_after=delay_after, hold_lmb=hold_lmb, hold_lmb_duration=hold_lmb_duration):
                                    action_in_progress.set()
                                    try:
                                        print(f"{time.strftime('%H:%M:%S')} Жду {delay_before} секунд перед нажатием {keybind}")
                                        time.sleep(delay_before)
                                        print(f"{time.strftime('%H:%M:%S')} Нажимаю клавишу: {keybind}")
                                        press_key(keybind)
                                        if hold_duration > 0:
                                            print(f"{time.strftime('%H:%M:%S')} Удерживаю клавишу {keybind} в течение {hold_duration} мс")
                                            time.sleep(hold_duration / 1000.0)
                                        release_key(keybind)
                                        print(f"{time.strftime('%H:%M:%S')} Отпустил клавишу: {keybind}")
                                        if hold_lmb:
                                            print(f"{time.strftime('%H:%M:%S')} Нажимаю ЛКМ")
                                            pyautogui.mouseDown(button='left')
                                            threading.Timer(hold_lmb_duration / 1000.0, pyautogui.mouseUp, kwargs={'button':'left'}).start()
                                            print(f"{time.strftime('%H:%M:%S')} Удерживаю ЛКМ {hold_lmb_duration} мс")
                                        time.sleep(delay_after)
                                        print(f"{time.strftime('%H:%M:%S')} Задержка после нажатия: {delay_after} секунд")
                                    finally:
                                        action_in_progress.clear()
                                threading.Thread(target=perform_action).start()
                            action_performed = True
                            zone_last_press_time[matched_text] = current_time
                            last_action_time = current_time
                            print(f"{time.strftime('%H:%M:%S')} Распознано '{matched_text}' в зоне {zone_num}")
                        else:
                            print(f"{time.strftime('%H:%M:%S')} Действие уже выполняется, пропуск запуска нового действия.")
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

            anti_afk_delay = anti_afk_delay_var.get()
            if anti_afk_enabled and (current_time - last_action_time > anti_afk_delay):
                pyautogui.click()
                print(f"{time.strftime('%H:%M:%S')} Выполнен Anti afk ЛКМ после {anti_afk_delay} секунд бездействия")
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
    print(f"{time.strftime('%H:%M:%S')} Бот включен: {bot_enabled}")

def toggle_always_on_top():
    is_always_on_top = always_on_top_var.get()
    root.attributes('-topmost', is_always_on_top)

    if frame_open:
        cv2.setWindowProperty("Frame", cv2.WND_PROP_TOPMOST, 1 if is_always_on_top else 0)

    for zone_num in text_windows_open.keys():
        text_windows_open[zone_num].attributes('-topmost', is_always_on_top)

def toggle_anti_afk():
    global anti_afk_enabled
    anti_afk_enabled = anti_afk_var.get()
    if anti_afk_enabled:
        print(f"{time.strftime('%H:%M:%S')} Anti afk включен с задержкой {anti_afk_delay_var.get()} секунд")
    else:
        print(f"{time.strftime('%H:%M:%S')} Anti afk выключен")

def on_closing():
    stop_event.set()
    root.destroy()

def start_tracking():
    global stop_event, zones, last_press_time, zones_tk_vars
    config = load_config("config.json")
    zones = copy.deepcopy(config.get('zones', []))
    zones_tk_vars = [{} for _ in zones]  # Инициализируем список tk_vars
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
    global bot, telegram_bot_token, telegram_chat_id
    if telegram_bot_var.get():
        telegram_bot_token = bot_token_entry.get()
        telegram_chat_id = chat_id_entry.get()
        if telegram_bot_token and telegram_chat_id:
            try:
                bot = telebot.TeleBot(telegram_bot_token)
                print(f"{time.strftime('%H:%M:%S')} Telegram бот активирован.")
                try:
                    bot.send_message(telegram_chat_id, "connect")
                    print(f"{time.strftime('%H:%M:%S')} Отправлено тестовое сообщение 'connect' в Telegram.")
                except Exception as e:
                    print(f"{time.strftime('%H:%M:%S')} Ошибка отправки тестового сообщения в Telegram: {e}")
                config = load_config("config.json")
                config["telegram_bot_token"] = telegram_bot_token
                config["telegram_chat_id"] = telegram_chat_id
                save_config(config, "config.json")

            except Exception as e:
                print(f"{time.strftime('%H:%M:%S')} Ошибка инициализации Telegram бота: {e}")
                telegram_bot_var.set(False)
        else:
            print(f"{time.strftime('%H:%M:%S')} Пожалуйста, введите Bot Token и Chat ID.")
            telegram_bot_var.set(False)
    else:
        bot = None
        print(f"{time.strftime('%H:%M:%S')} Telegram бот деактивирован.")

always_on_top_var = tk.BooleanVar()
anti_afk_var = tk.BooleanVar()

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

anti_afk_checkbox = tk.Checkbutton(root, text="Anti afk", variable=anti_afk_var, command=toggle_anti_afk)
anti_afk_checkbox.grid(row=5, column=0, padx=10, pady=5, sticky='w')

anti_afk_delay_label = tk.Label(root, text="Задержка Anti afk (сек):")
anti_afk_delay_label.grid(row=5, column=1, padx=10, pady=5, sticky='w')

anti_afk_delay_entry = tk.Entry(root, textvariable=anti_afk_delay_var)
anti_afk_delay_entry.grid(row=5, column=2, padx=10, pady=5, sticky='w')

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
zones_frame.grid(row=0, column=3, rowspan=15, padx=10, pady=5, sticky='n')

def update_zones_display():
    global zones, zones_tk_vars
    for widget in zones_frame.winfo_children():
        widget.destroy()
    config = load_config("config.json")
    zones = copy.deepcopy(config.get('zones', []))
    zones_tk_vars = []  # Очищаем список tk_vars
    if not zones:
        return
    tk.Label(zones_frame, text="Зона").grid(row=0, column=1, padx=5, pady=5)
    tk.Label(zones_frame, text="Клавиша").grid(row=0, column=2, padx=5, pady=5)
    tk.Label(zones_frame, text="Удержание").grid(row=0, column=3, padx=5, pady=5)
    tk.Label(zones_frame, text="Продолжительность (мс)").grid(row=0, column=4, padx=5, pady=5)
    tk.Label(zones_frame, text="Задержка (мс) до").grid(row=0, column=5, padx=5, pady=5)
    tk.Label(zones_frame, text="Задержка (мс) после").grid(row=0, column=6, padx=5, pady=5)
    tk.Label(zones_frame, text="Фразы").grid(row=0, column=7, columnspan=3, padx=5, pady=5)
    key_options = ['a', 'd', 'f', 'left mouse button', 'TGBot']
    hold_options = ['Да', 'Нет']
    for idx, zone in enumerate(zones):
        zone_num = idx + 1
        remove_zone_button = tk.Button(zones_frame, text="-", command=lambda i=idx: remove_zone(i))
        remove_zone_button.grid(row=zone_num, column=0, padx=5, pady=5)
        tk.Label(zones_frame, text=f"{zone_num}").grid(row=zone_num, column=1, padx=5, pady=5)
        keybind_var = tk.StringVar(value=zone.get('keybind', 'a'))
        keybind_menu = ttk.Combobox(zones_frame, textvariable=keybind_var, width=15)
        keybind_menu['values'] = key_options
        keybind_menu.set(zone.get('keybind', 'a'))
        keybind_menu.grid(row=zone_num, column=2, padx=5, pady=5)
        keybind_menu.config(state='normal')

        hold_var = tk.StringVar(value='Да' if zone.get('hold', False) else 'Нет')
        hold_menu = ttk.Combobox(zones_frame, values=hold_options, textvariable=hold_var, state="readonly", width=10)
        hold_menu.grid(row=zone_num, column=3, padx=5, pady=5)
        hold_duration_var = tk.StringVar(value=str(zone.get('hold_duration', 0)))
        hold_duration_entry = tk.Entry(zones_frame, textvariable=hold_duration_var, width=15)
        hold_duration_entry.grid(row=zone_num, column=4, padx=5, pady=5)

        delay_before_var = tk.StringVar(value=str(zone.get('delay_before', 0)))
        delay_before_entry = tk.Entry(zones_frame, textvariable=delay_before_var, width=15)
        delay_before_entry.grid(row=zone_num, column=5, padx=5, pady=5)

        delay_after_var = tk.StringVar(value=str(zone.get('delay_after', scan_delay_var.get())))
        delay_after_entry = tk.Entry(zones_frame, textvariable=delay_after_var, width=15)
        delay_after_entry.grid(row=zone_num, column=6, padx=5, pady=5)

        add_phrase_button = tk.Button(zones_frame, text="+", command=lambda i=idx: add_phrase(i))
        add_phrase_button.grid(row=zone_num, column=7, padx=5, pady=5)
        remove_phrase_button = tk.Button(zones_frame, text="-", command=lambda i=idx: remove_phrase(i))
        remove_phrase_button.grid(row=zone_num, column=8, padx=5, pady=5)
        phrases_var = tk.StringVar()
        phrases_combobox = ttk.Combobox(zones_frame, textvariable=phrases_var, state="readonly", width=15)
        phrases_combobox.grid(row=zone_num, column=9, padx=5, pady=5)

        # Создаем словарь tk_vars для текущей зоны и сохраняем переменные
        tk_vars = {}
        tk_vars['phrases_var'] = phrases_var
        tk_vars['phrases_combobox'] = phrases_combobox
        tk_vars['keybind_var'] = keybind_var
        tk_vars['hold_var'] = hold_var
        tk_vars['hold_duration_var'] = hold_duration_var
        tk_vars['delay_before_var'] = delay_before_var
        tk_vars['delay_after_var'] = delay_after_var

        hold_lmb_var = tk.BooleanVar(value=zone.get('hold_lmb', False))
        hold_lmb_checkbox = tk.Checkbutton(zones_frame, text="Дожать лкм", variable=hold_lmb_var)
        hold_lmb_checkbox.grid(row=zone_num, column=10, padx=5, pady=5)

        hold_lmb_duration_var = tk.StringVar(value=str(zone.get('hold_lmb_duration', 0)))
        hold_lmb_duration_entry = tk.Entry(zones_frame, textvariable=hold_lmb_duration_var, width=10)
        hold_lmb_duration_entry.grid(row=zone_num, column=11, padx=5, pady=5)

        tk_vars['hold_lmb_var'] = hold_lmb_var
        tk_vars['hold_lmb_duration_var'] = hold_lmb_duration_var

        # Добавляем tk_vars в список zones_tk_vars перед вызовом update_phrases_combobox
        zones_tk_vars.append(tk_vars)

        # Теперь вызываем update_phrases_combobox
        update_phrases_combobox(idx, phrases_combobox)

    save_zones_button = tk.Button(zones_frame, text="Сохранить настройки зон", command=save_zones_settings)
    save_zones_button.grid(row=len(zones)+1, column=1, columnspan=11, padx=5, pady=10)

    add_zone_button = tk.Button(zones_frame, text="+", command=add_zone)
    add_zone_button.grid(row=len(zones)+2, column=1, columnspan=11, padx=5, pady=10)

def update_phrases_combobox(idx, phrases_combobox):
    zone = zones[idx]
    phrases = zone.get('p', [])
    phrases_options = ['All'] + phrases
    phrases_combobox['values'] = phrases_options
    selected_phrase = zone.get('selected_phrase', 'All')
    if selected_phrase in phrases_options:
        zones_tk_vars[idx]['phrases_var'].set(selected_phrase)
    else:
        zones_tk_vars[idx]['phrases_var'].set('All')

def add_phrase(idx):
    zone = zones[idx]
    def save_phrase():
        phrase = new_phrase_var.get()
        if phrase:
            zone.setdefault('p', []).append(phrase)
            update_phrases_combobox(idx, zones_tk_vars[idx]['phrases_combobox'])
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
    selected_phrase = zones_tk_vars[idx]['phrases_var'].get()
    if selected_phrase == 'All':
        return
    if 'p' in zone and selected_phrase in zone['p']:
        zone['p'].remove(selected_phrase)
        update_phrases_combobox(idx, zones_tk_vars[idx]['phrases_combobox'])

def add_zone():
    start_zone_creation(callback=update_zones_display)

def remove_zone(idx):
    global zones
    zones.pop(idx)
    zones_tk_vars.pop(idx)  # Удаляем tk_vars для удаленной зоны
    config = load_config("config.json")
    config['zones'] = zones
    save_config(config, "config.json")
    update_zones_display()
    print(f"{time.strftime('%H:%M:%S')} Зона {idx+1} удалена.")

def save_zones_settings():
    global zones, zones_tk_vars
    cleaned_zones = []
    for idx, zone in enumerate(zones):
        tk_vars = zones_tk_vars[idx]
        keybind = tk_vars.get('keybind_var', tk.StringVar(value='a')).get()
        hold = True if tk_vars.get('hold_var', tk.StringVar(value='Нет')).get() == 'Да' else False
        try:
            hold_duration = int(tk_vars.get('hold_duration_var', tk.StringVar(value='0')).get())
        except ValueError:
            hold_duration = 0
        try:
            delay_before = int(tk_vars.get('delay_before_var', tk.StringVar(value='0')).get())
        except ValueError:
            delay_before = 0
        try:
            delay_after = int(tk_vars.get('delay_after_var', tk.StringVar(value=str(scan_delay_var.get()))).get())
        except ValueError:
            delay_after = scan_delay_var.get()
        hold_lmb = tk_vars.get('hold_lmb_var', tk.BooleanVar(value=False)).get()
        try:
            hold_lmb_duration = int(tk_vars.get('hold_lmb_duration_var', tk.StringVar(value='0')).get())
        except ValueError:
            hold_lmb_duration = 0

        selected_phrase = tk_vars.get('phrases_var', tk.StringVar(value='All')).get()

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
    # Сохраняем дополнительные настройки
    config['selected_language'] = selected_language.get()
    config['recognition_threshold'] = recognition_threshold_var.get()
    config['scan_delay'] = scan_delay_var.get()
    save_config(config, "config.json")
    print(f"{time.strftime('%H:%M:%S')} Настройки зон сохранены.")

    config = load_config("config.json")
    zones = copy.deepcopy(config.get('zones', []))
    zones_tk_vars = [{} for _ in zones]
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

# Перенос кликабельного текста GitHub в правый нижний угол
root.grid_rowconfigure(999, weight=1)
root.grid_columnconfigure(3, weight=1)

github_label = tk.Label(root, text="GitHub lReDragol", fg="blue", cursor="hand2", bg="lightblue",
                        font=("Arial", 10, "underline"))
github_label.grid(row=999, column=3, padx=10, pady=5, sticky='se')
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

def create_context_menu(entry_widget):
    menu = tk.Menu(entry_widget, tearoff=0)
    menu.add_command(label="Вырезать", command=lambda: entry_widget.event_generate('<<Cut>>'))
    menu.add_command(label="Копировать", command=lambda: entry_widget.event_generate('<<Copy>>'))
    menu.add_command(label="Вставить", command=lambda: entry_widget.event_generate('<<Paste>>'))

    def show_menu(event):
        menu.tk_popup(event.x_root, event.y_root)

    entry_widget.bind("<Button-3>", show_menu)

create_context_menu(bot_token_entry)
create_context_menu(chat_id_entry)

config = load_config("config.json")
zones = copy.deepcopy(config.get('zones', []))
zones_tk_vars = [{} for _ in zones]  # Инициализируем список tk_vars
bot_token_entry.insert(0, config.get('telegram_bot_token', ''))
chat_id_entry.insert(0, config.get('telegram_chat_id', ''))
# Загружаем дополнительные настройки
selected_language.set(config.get('selected_language', 'rus'))
recognition_threshold_var.set(config.get('recognition_threshold', 40))
scan_delay_var.set(config.get('scan_delay', 500))

root.protocol("WM_DELETE_WINDOW", on_closing)

update_zones_display()

zone_creation_button = tk.Button(root, text="Создать зоны", command=add_zone)
zone_creation_button.grid(row=12, column=0, padx=10, pady=10, sticky='w')

root.mainloop()
cv2.destroyAllWindows()
