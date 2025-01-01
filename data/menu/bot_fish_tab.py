# data/menu/bot_fish_tab.py

import threading
import time
import cv2
import numpy as np
import mss
import pytesseract
from fuzzywuzzy import fuzz
import pyautogui
import telebot
import copy
import dearpygui.dearpygui as dpg
from config import Config
import sys
import webbrowser

from .functions import apply_filter, draw_areas_on_frame, scale_coordinates, press_key, release_key

class BotFishTab:
    def __init__(self, main_app):
        self.main_app = main_app
        self.translations = self.main_app.translations
        self.update_translations()

        self.config = Config.from_json()
        self.bot_enabled = self.config.bot_fish_tab.get('bot_enabled', False)
        self.stop_event = threading.Event()
        self.action_in_progress = threading.Event()
        self.text_windows_open = {}
        self.text_vars = {}
        self.last_frame = None
        self.frame_visible = self.config.bot_fish_tab.get('frame_visible', False)
        self.frame_open = False
        self.text_visible = self.config.bot_fish_tab.get('text_visible', False)
        self.show_all_text = self.config.bot_fish_tab.get('show_all_text', False)
        self.original_width, self.original_height = pyautogui.size()
        self.frame_width = 480
        self.frame_height = int(self.frame_width * self.original_height / self.original_width)
        self.selected_filter_value = self.config.bot_fish_tab.get('selected_filter_value', "Нет фильтра")
        self.scan_delay_var = self.config.bot_fish_tab.get('scan_delay_var', 500)
        self.recognition_threshold_var = self.config.bot_fish_tab.get('recognition_threshold_var', 40)
        self.selected_language = self.config.bot_fish_tab.get('selected_language', 'rus')
        self.telegram_bot_token = self.config.bot_fish_tab.get('telegram_bot_token', '')
        self.telegram_chat_id = self.config.bot_fish_tab.get('telegram_chat_id', '')
        self.bot = None
        self.anti_afk_enabled = self.config.bot_fish_tab.get('anti_afk_enabled', False)
        self.last_action_time = time.time()
        self.anti_afk_delay_var = self.config.bot_fish_tab.get('anti_afk_delay_var', 10)
        self.zones = copy.deepcopy(self.config.bot_fish_tab.get('zones', []))
        self.zones_ui_elements = []
        self.last_press_time = []
        self.always_on_top_var = self.config.bot_fish_tab.get('always_on_top_var', False)
        self.telegram_bot_var = self.config.bot_fish_tab.get('telegram_bot_var', False)
        self.zone_settings_visible = False
        self.zone_settings_window = None  # Окно для настроек зон теперь будет создаваться отдельно

        # Создаем главную группу один раз
        self.main_group = dpg.add_group(horizontal=False)

        # Создаем окно предупреждения о Tesseract один раз
        with dpg.window(label="", modal=True, width=400, height=150, show=False, tag="tesseract_not_found_popup"):
            self.tesseract_not_found_text = dpg.add_text(default_value=self.trans.get("tesseract_not_installed", "Tesseract OCR is not installed.\nPlease install it or download from the official source."))
            dpg.add_button(label=self.trans.get("download_tesseract", "Download Tesseract"), callback=self.open_tesseract_link)
            dpg.add_button(label="OK", callback=lambda: dpg.configure_item("tesseract_not_found_popup", show=False))

        # Изначально создаем UI внутри main_group
        self.build_ui()

    def update_translations(self):
        self.trans = self.translations.get(self.main_app.current_language, {}).get("bot_fish_tab", {})

    def open_tesseract_link(self):
        webbrowser.open("https://github.com/UB-Mannheim/tesseract/wiki")

    def check_tesseract_installed(self):
        try:
            version = pytesseract.get_tesseract_version()
            if version:
                return True
        except Exception:
            return False
        return False

    def start_tracking(self, sender, app_data):
        if not self.check_tesseract_installed():
            dpg.configure_item("tesseract_not_found_popup", show=True)
            return
        self.stop_event.clear()
        threading.Thread(target=self.update_window, daemon=True).start()

    def stop_tracking(self, sender, app_data):
        self.stop_event.set()

    def toggle_frame_visibility(self, sender, app_data):
        self.frame_visible = not self.frame_visible
        self.config.bot_fish_tab['frame_visible'] = self.frame_visible
        self.config.save_to_json()

    def toggle_text_visibility(self, sender, app_data):
        self.text_visible = not self.text_visible
        self.config.bot_fish_tab['text_visible'] = self.text_visible
        self.config.save_to_json()

    def toggle_show_all_text(self, sender, app_data):
        self.show_all_text = not self.show_all_text
        self.config.bot_fish_tab['show_all_text'] = self.show_all_text
        self.config.save_to_json()

    def toggle_bot_enabled(self, sender, app_data):
        self.bot_enabled = not self.bot_enabled
        self.config.bot_fish_tab['bot_enabled'] = self.bot_enabled
        self.config.save_to_json()
        print(f"{time.strftime('%H:%M:%S')} Бот включен: {self.bot_enabled}")

    def toggle_always_on_top(self, sender, app_data):
        self.always_on_top_var = app_data
        self.config.bot_fish_tab['always_on_top_var'] = self.always_on_top_var
        self.config.save_to_json()

    def toggle_anti_afk(self, sender, app_data):
        self.anti_afk_enabled = not self.anti_afk_enabled
        self.config.bot_fish_tab['anti_afk_enabled'] = self.anti_afk_enabled
        self.config.save_to_json()
        if self.anti_afk_enabled:
            print(f"{time.strftime('%H:%M:%S')} Anti afk включен с задержкой {self.anti_afk_delay_var} секунд")
        else:
            print(f"{time.strftime('%H:%M:%S')} Anti afk выключен")

    def update_anti_afk_delay(self, sender, app_data):
        self.anti_afk_delay_var = app_data
        self.config.bot_fish_tab['anti_afk_delay_var'] = self.anti_afk_delay_var
        self.config.save_to_json()

    def on_filter_change(self, sender, app_data):
        self.selected_filter_value = app_data
        self.config.bot_fish_tab['selected_filter_value'] = self.selected_filter_value
        self.config.save_to_json()

    def update_scan_delay(self, sender, app_data):
        self.scan_delay_var = app_data
        self.config.bot_fish_tab['scan_delay_var'] = self.scan_delay_var
        self.config.save_to_json()

    def update_recognition_threshold(self, sender, app_data):
        self.recognition_threshold_var = app_data
        self.config.bot_fish_tab['recognition_threshold_var'] = self.recognition_threshold_var
        self.config.save_to_json()

    def update_selected_language(self, sender, app_data):
        self.selected_language = app_data
        self.config.bot_fish_tab['selected_language'] = self.selected_language
        self.config.save_to_json()

    def toggle_telegram_bot(self, sender, app_data):
        self.telegram_bot_var = not self.telegram_bot_var
        self.config.bot_fish_tab['telegram_bot_var'] = self.telegram_bot_var
        self.config.save_to_json()
        if self.telegram_bot_var:
            self.init_telegram_bot()
        else:
            self.bot = None
            print(f"{time.strftime('%H:%M:%S')} Telegram бот деактивирован.")

    def update_telegram_bot_token(self, sender, app_data):
        self.telegram_bot_token = app_data
        self.config.bot_fish_tab['telegram_bot_token'] = self.telegram_bot_token
        self.config.save_to_json()

    def update_telegram_chat_id(self, sender, app_data):
        self.telegram_chat_id = app_data
        self.config.bot_fish_tab['telegram_chat_id'] = self.telegram_chat_id
        self.config.save_to_json()

    def init_telegram_bot(self):
        if self.telegram_bot_token and self.telegram_chat_id:
            try:
                self.bot = telebot.TeleBot(self.telegram_bot_token)
                print(f"{time.strftime('%H:%M:%S')} Telegram бот активирован.")
                try:
                    self.bot.send_message(self.telegram_chat_id, "connect")
                    print(f"{time.strftime('%H:%M:%S')} Отправлено тестовое сообщение 'connect' в Telegram.")
                except Exception as e:
                    print(f"{time.strftime('%H:%M:%S')} Ошибка отправки сообщения в Telegram: {e}")
                self.config.bot_fish_tab['telegram_bot_token'] = self.telegram_bot_token
                self.config.bot_fish_tab['telegram_chat_id'] = self.telegram_chat_id
                self.config.save_to_json()
            except Exception as e:
                print(f"{time.strftime('%H:%M:%S')} Ошибка инициализации Telegram бота: {e}")
                self.telegram_bot_var = False
        else:
            print(f"{time.strftime('%H:%M:%S')} Пожалуйста, введите Bot Token и Chat ID.")
            self.telegram_bot_var = False

    def build_ui(self):
        dpg.add_checkbox(label=self.trans.get("show_frame", "Show Frame"), callback=self.toggle_frame_visibility, default_value=self.frame_visible, parent=self.main_group)
        dpg.add_checkbox(label=self.trans.get("show_ocr_text", "Show OCR Text"), callback=self.toggle_text_visibility, default_value=self.text_visible, parent=self.main_group)
        dpg.add_checkbox(label=self.trans.get("show_all_recognized_text", "Show All Recognized Text"), callback=self.toggle_show_all_text, default_value=self.show_all_text, parent=self.main_group)
        dpg.add_checkbox(label=self.trans.get("enable_bot", "Enable Bot"), callback=self.toggle_bot_enabled, default_value=self.bot_enabled, parent=self.main_group)
        dpg.add_checkbox(label=self.trans.get("always_on_top", "Always on top"), callback=self.toggle_always_on_top, default_value=self.always_on_top_var, parent=self.main_group)
        dpg.add_checkbox(label=self.trans.get("anti_afk", "Anti afk"), callback=self.toggle_anti_afk, default_value=self.anti_afk_enabled, parent=self.main_group)
        dpg.add_input_int(label=self.trans.get("anti_afk_delay", "Anti afk delay (sec):"), default_value=self.anti_afk_delay_var, callback=self.update_anti_afk_delay, parent=self.main_group)
        dpg.add_text(self.trans.get("select_filter", "Select filter:"), parent=self.main_group)
        self.filter_options = ["Нет фильтра", "Градации серого", "Бинарный порог", "Края Кэнни"]
        dpg.add_combo(self.filter_options, default_value=self.selected_filter_value, callback=self.on_filter_change, parent=self.main_group)
        dpg.add_button(label=self.trans.get("start_tracking", "Start tracking"), callback=self.start_tracking, parent=self.main_group)
        dpg.add_button(label=self.trans.get("stop_tracking", "Stop tracking"), callback=self.stop_tracking, parent=self.main_group)
        dpg.add_text(self.trans.get("delay_between_presses", "Delay between presses (ms):"), parent=self.main_group)
        dpg.add_input_int(default_value=self.scan_delay_var, callback=self.update_scan_delay, parent=self.main_group)
        dpg.add_text(self.trans.get("recognition_threshold", "Recognition threshold (%)") + ":", parent=self.main_group)
        dpg.add_slider_int(min_value=0, max_value=100, default_value=self.recognition_threshold_var, callback=self.update_recognition_threshold, parent=self.main_group)
        dpg.add_text(self.trans.get("ocr_language", "OCR language:"), parent=self.main_group)
        dpg.add_combo(['eng', 'rus'], default_value=self.selected_language, callback=self.update_selected_language, parent=self.main_group)
        dpg.add_checkbox(label=self.trans.get("enable_telegram_bot", "Enable Telegram bot"), callback=self.toggle_telegram_bot, default_value=self.telegram_bot_var, parent=self.main_group)
        dpg.add_input_text(label=self.trans.get("bot_token", "Bot Token:"), default_value=self.telegram_bot_token, callback=self.update_telegram_bot_token, parent=self.main_group)
        dpg.add_input_text(label=self.trans.get("chat_id", "Chat ID:"), default_value=self.telegram_chat_id, callback=self.update_telegram_chat_id, parent=self.main_group)
        self.zone_settings_checkbox = dpg.add_checkbox(label=self.trans.get("show_zone_settings", "Show zone settings"), callback=self.toggle_zone_settings, default_value=self.zone_settings_visible, parent=self.main_group)
        dpg.add_button(label=self.trans.get("create_zones", "Create zones"), callback=self.add_zone, parent=self.main_group)

    def update_window(self):
        if not self.zones:
            return

        scale_x = self.frame_width / self.original_width
        scale_y = self.frame_height / self.original_height

        if not self.last_press_time or len(self.last_press_time) != len(self.zones):
            self.last_press_time = [{} for _ in self.zones]

        with mss.mss() as sct:
            while not self.stop_event.is_set():
                monitor = sct.monitors[1]
                sct_img = sct.grab(monitor)
                frame = np.array(sct_img)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)
                self.last_frame = frame

                display_frame = apply_filter(frame.copy(), self.selected_filter_value)
                small_frame = cv2.resize(display_frame, (self.frame_width, self.frame_height))

                draw_areas_on_frame(small_frame, self.zones, scale_x, scale_y)

                if self.frame_visible:
                    cv2.imshow("Frame", small_frame)
                    self.frame_open = True
                    cv2.setWindowProperty("Frame", cv2.WND_PROP_TOPMOST, 1 if self.always_on_top_var else 0)
                elif self.frame_open:
                    cv2.destroyWindow("Frame")
                    self.frame_open = False

                current_time = time.time()

                for idx, zone_data in enumerate(self.zones):
                    x1, y1, x2, y2 = map(int, zone_data['c'])
                    phrases = zone_data.get('p', [])
                    zone_num = str(idx+1)
                    keybind = zone_data.get('keybind', 'a')
                    hold = zone_data.get('hold', False)
                    hold_duration = zone_data.get('hold_duration', 0)
                    delay_before = zone_data.get('delay_before', 0) / 1000.0
                    delay_after = zone_data.get('delay_after', 0) / 1000.0
                    press_delay = zone_data.get('press_delay', self.scan_delay_var) / 1000.0
                    hold_lmb = zone_data.get('hold_lmb', False)
                    hold_lmb_duration = zone_data.get('hold_lmb_duration', 0)

                    zone_last_press_time = self.last_press_time[idx]

                    zone_frame = frame[y1:y2, x1:x2]
                    zone_frame_filtered = apply_filter(zone_frame, self.selected_filter_value)
                    ocr_lang = self.selected_language
                    ocr_result_psm6 = pytesseract.image_to_string(zone_frame_filtered, lang=ocr_lang, config='--psm 6')
                    ocr_result_psm7 = pytesseract.image_to_string(zone_frame_filtered, lang=ocr_lang, config='--psm 7')

                    matched_text = "-"
                    threshold = self.recognition_threshold_var
                    selected_phrase = zone_data.get('selected_phrase', 'All')

                    phrases_to_check = [selected_phrase] if selected_phrase != 'All' else phrases
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
                            if self.action_in_progress.is_set():
                                continue
                            if self.bot_enabled:
                                if keybind == 'TGBot':
                                    if self.telegram_bot_var and self.bot:
                                        message_text = f"Найдена '{matched_text}' в зоне {zone_num}"
                                        try:
                                            self.bot.send_message(self.telegram_chat_id, message_text)
                                            print(f"{time.strftime('%H:%M:%S')} Отправлено сообщение в Telegram: {message_text}")
                                        except Exception as e:
                                            print(f"{time.strftime('%H:%M:%S')} Ошибка отправки сообщения в Telegram: {e}")
                                    else:
                                        print(f"{time.strftime('%H:%M:%S')} Telegram бот не активирован или не настроен.")
                                else:
                                    threading.Thread(target=self.perform_action, args=(
                                        keybind, hold_duration, delay_before, delay_after, hold_lmb, hold_lmb_duration), daemon=True).start()
                                    zone_last_press_time[matched_text] = current_time
                                    self.last_action_time = current_time
                                    print(f"{time.strftime('%H:%M:%S')} Распознано '{matched_text}' в зоне {zone_num}")

                    # Отображение OCR текста (если включено)
                    if self.text_visible:
                        window_name = f"Текст зоны {zone_num}"
                        if self.show_all_text:
                            ocr_text = ocr_result_psm6.strip() + " | " + ocr_result_psm7.strip()
                        else:
                            ocr_text = matched_text
                        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
                        cv2.resizeWindow(window_name, 300, 100)
                        img = np.zeros((100, 300, 3), dtype=np.uint8)
                        font = cv2.FONT_HERSHEY_SIMPLEX
                        font_scale = 0.5
                        cv2.putText(img, ocr_text, (10, 50), font, font_scale, (255, 255, 255), 1, cv2.LINE_AA)
                        cv2.imshow(window_name, img)
                        cv2.setWindowProperty(window_name, cv2.WND_PROP_TOPMOST, 1 if self.always_on_top_var else 0)
                    else:
                        window_name = f"Текст зоны {zone_num}"
                        try:
                            cv2.destroyWindow(window_name)
                        except cv2.error as e:
                            print(f"Ошибка при закрытии окна {window_name}: {e}")

                anti_afk_delay = self.anti_afk_delay_var
                if self.anti_afk_enabled and (current_time - self.last_action_time > anti_afk_delay):
                    pyautogui.click()
                    print(f"{time.strftime('%H:%M:%S')} Выполнен Anti afk ЛКМ после {anti_afk_delay} секунд бездействия")
                    self.last_action_time = current_time

                key = cv2.waitKey(1)
                if key == ord('q'):
                    self.stop_event.set()
                    break

        cv2.destroyAllWindows()

    def perform_action(self, keybind, hold_duration, delay_before, delay_after, hold_lmb, hold_lmb_duration):
        self.action_in_progress.set()
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
            self.action_in_progress.clear()

    def add_zone(self, sender, app_data):
        def update_zones_display():
            self.zones = copy.deepcopy(self.config.bot_fish_tab.get('zones', []))
            print("Зоны обновлены.")

        self.start_zone_creation(callback=update_zones_display)

    def toggle_zone_settings(self, sender, app_data):
        # Если пользователь включает настройки, создаем окно, если выключает — удаляем
        self.zone_settings_visible = not self.zone_settings_visible
        if self.zone_settings_visible:
            self.show_zone_settings()
        else:
            self.hide_zone_settings()

    def show_zone_settings(self):
        # Создаем отдельное окно настроек зон без родителя — независимое окно
        self.zone_settings_window = dpg.add_window(label="Настройки зон", width=800, height=600, pos=(100, 100), no_resize=False)
        self.populate_zone_settings()

    def hide_zone_settings(self, sender=None, app_data=None):
        if self.zone_settings_window is not None:
            dpg.delete_item(self.zone_settings_window)
            self.zone_settings_window = None
        # Снимаем галочку с чекбокса, если окно было закрыто не через чекбокс
        if dpg.get_value(self.zone_settings_checkbox) is True:
            dpg.set_value(self.zone_settings_checkbox, False)
        self.zone_settings_visible = False

    def populate_zone_settings(self):
        self.zones_ui_elements = []

        with dpg.table(header_row=True, resizable=True, policy=dpg.mvTable_SizingStretchProp, parent=self.zone_settings_window):
            dpg.add_table_column(label="№", width_fixed=True, width=30)
            dpg.add_table_column(label="Клавиша", width_fixed=True, width=100)
            dpg.add_table_column(label="Удержание", width_fixed=True, width=80)
            dpg.add_table_column(label="Продолжительность (мс)", width_fixed=True, width=150)
            dpg.add_table_column(label="Задержка (мс) до", width_fixed=True, width=120)
            dpg.add_table_column(label="Задержка (мс) после", width_fixed=True, width=130)
            dpg.add_table_column(label="Фразы", width_fixed=True, width=150)
            dpg.add_table_column(label="", width_fixed=True, width=20)
            dpg.add_table_column(label="", width_fixed=True, width=20)
            dpg.add_table_column(label="Дожать ЛКМ", width_fixed=True, width=100)
            dpg.add_table_column(label="Длительность ЛКМ (мс)", width_fixed=True, width=150)
            dpg.add_table_column(label="", width_fixed=True, width=50)

            for idx, zone in enumerate(self.zones):
                with dpg.table_row():
                    zone_number = idx + 1
                    dpg.add_text(f"{zone_number}")
                    keybind = zone.get('keybind', 'a')
                    keybind_var = dpg.add_combo(['a', 'd', 'f', 'left mouse button', 'TGBot'], default_value=str(keybind), width=100)
                    hold = zone.get('hold', False)
                    hold_var = dpg.add_checkbox(default_value=hold)
                    hold_duration = int(zone.get('hold_duration', 0))
                    hold_duration_var = dpg.add_input_int(default_value=hold_duration, step=0, width=150)
                    delay_before = int(zone.get('delay_before', 0))
                    delay_before_var = dpg.add_input_int(default_value=delay_before, step=0, width=120)
                    delay_after = int(zone.get('delay_after', 0))
                    delay_after_var = dpg.add_input_int(default_value=delay_after, step=0, width=130)
                    phrases = zone.get('p', [])
                    phrases_options = ['All'] + phrases
                    selected_phrase = zone.get('selected_phrase', 'All')
                    phrases_var = dpg.add_combo(phrases_options, default_value=selected_phrase, width=150)
                    add_phrase_button = dpg.add_button(label="+", callback=self.add_phrase, user_data=idx, width=20)
                    remove_phrase_button = dpg.add_button(label="-", callback=self.remove_phrase, user_data=idx, width=20)
                    hold_lmb = zone.get('hold_lmb', False)
                    hold_lmb_var = dpg.add_checkbox(default_value=hold_lmb)
                    hold_lmb_duration = int(zone.get('hold_lmb_duration', 0))
                    hold_lmb_duration_var = dpg.add_input_int(default_value=hold_lmb_duration, step=0, width=150)
                    remove_button = dpg.add_button(label="Удалить", callback=self.remove_zone, user_data=idx)

                    self.zones_ui_elements.append({
                        'keybind_var': keybind_var,
                        'hold_var': hold_var,
                        'hold_duration_var': hold_duration_var,
                        'delay_before_var': delay_before_var,
                        'delay_after_var': delay_after_var,
                        'phrases_var': phrases_var,
                        'hold_lmb_var': hold_lmb_var,
                        'hold_lmb_duration_var': hold_lmb_duration_var
                    })

        dpg.add_spacer(height=10, parent=self.zone_settings_window)
        dpg.add_button(label="Сохранить настройки зон", callback=self.save_zones_settings, parent=self.zone_settings_window)

    def add_zone_directly(self, sender, app_data):
        default_zone = {
            'c': [0, 0, 100, 100],
            'p': [],
            'keybind': 'a',
            'hold': False,
            'hold_duration': 0,
            'delay_before': 0,
            'delay_after': 0,
            'hold_lmb': False,
            'hold_lmb_duration': 0,
        }
        self.zones.append(default_zone)
        self.config.bot_fish_tab['zones'] = self.zones
        self.config.save_to_json()
        self.hide_zone_settings()
        self.show_zone_settings()
        print(f"{time.strftime('%H:%M:%S')} Добавлена новая зона.")

    def start_zone_creation(self, callback=None):
        self.callback = callback
        from PyQt5.QtWidgets import QApplication
        from .functions import MainMenu
        app = QApplication(sys.argv)
        main_menu = MainMenu(callback=self.on_zones_created, config=self.config)
        app.exec_()

    def on_zones_created(self):
        self.zones = copy.deepcopy(self.config.bot_fish_tab.get('zones', []))
        print("Зоны обновлены.")
        if self.zone_settings_visible:
            self.hide_zone_settings()
            self.show_zone_settings()
        if self.callback:
            self.callback()

    def add_phrase(self, sender, app_data, user_data):
        idx = user_data
        def save_phrase(sender, app_data, user_data):
            phrase = dpg.get_value(new_phrase_input)
            if phrase:
                self.zones[idx].setdefault('p', []).append(phrase)
                self.config.bot_fish_tab['zones'] = self.zones
                self.config.save_to_json()
                self.hide_zone_settings()
                self.show_zone_settings()
                print(f"{time.strftime('%H:%M:%S')} Фраза '{phrase}' добавлена в зону {idx + 1}.")
            dpg.delete_item(add_phrase_window)

        def cancel_phrase(sender, app_data, user_data):
            dpg.delete_item(add_phrase_window)

        add_phrase_window = dpg.add_window(label="Добавить фразу", modal=True, no_resize=True, no_move=True)
        new_phrase_input = dpg.add_input_text(label="Введите фразу", parent=add_phrase_window)
        dpg.add_button(label="Сохранить", callback=save_phrase, parent=add_phrase_window)
        dpg.add_button(label="Отмена", callback=cancel_phrase, parent=add_phrase_window)

    def remove_phrase(self, sender, app_data, user_data):
        idx = user_data
        selected_phrase = dpg.get_value(self.zones_ui_elements[idx]['phrases_var'])
        if selected_phrase == 'All':
            print(f"{time.strftime('%H:%M:%S')} Невозможно удалить 'All' из зоны {idx + 1}.")
            return
        if 'p' in self.zones[idx] and selected_phrase in self.zones[idx]['p']:
            self.zones[idx]['p'].remove(selected_phrase)
            self.config.bot_fish_tab['zones'] = self.zones
            self.config.save_to_json()
            self.hide_zone_settings()
            self.show_zone_settings()
            print(f"{time.strftime('%H:%M:%S')} Фраза '{selected_phrase}' удалена из зоны {idx + 1}.")

    def remove_zone(self, sender, app_data, user_data):
        idx = user_data
        if idx < len(self.zones):
            del self.zones[idx]
            self.config.bot_fish_tab['zones'] = self.zones
            self.config.save_to_json()
            self.hide_zone_settings()
            self.show_zone_settings()
            print(f"{time.strftime('%H:%M:%S')} Зона {idx + 1} удалена.")

    def save_zones_settings(self, sender, app_data):
        for idx, zone_ui in enumerate(self.zones_ui_elements):
            zone = self.zones[idx]
            keybind = dpg.get_value(zone_ui['keybind_var'])
            hold = dpg.get_value(zone_ui['hold_var'])
            hold_duration = dpg.get_value(zone_ui['hold_duration_var'])
            delay_before = dpg.get_value(zone_ui['delay_before_var'])
            delay_after = dpg.get_value(zone_ui['delay_after_var'])
            phrases = zone.get('p', [])
            hold_lmb = dpg.get_value(zone_ui['hold_lmb_var'])
            hold_lmb_duration = dpg.get_value(zone_ui['hold_lmb_duration_var'])
            zone['keybind'] = keybind
            zone['hold'] = hold
            zone['hold_duration'] = hold_duration
            zone['delay_before'] = delay_before
            zone['delay_after'] = delay_after
            zone['p'] = phrases
            zone['hold_lmb'] = hold_lmb
            zone['hold_lmb_duration'] = hold_lmb_duration
            selected_phrase = dpg.get_value(zone_ui['phrases_var'])
            zone['selected_phrase'] = selected_phrase
        self.config.bot_fish_tab['zones'] = self.zones
        self.config.save_to_json()
        print(f"{time.strftime('%H:%M:%S')} Настройки зон сохранены.")

    def restore_states(self):
        pass

    def save_states(self):
        pass

    def update_ui(self):
        self.update_translations()

        children = dpg.get_item_children(self.main_group, 1)
        for child in children:
            dpg.delete_item(child)

        self.build_ui()

        dpg.set_value(self.tesseract_not_found_text, self.trans.get("tesseract_not_installed", "Tesseract OCR is not installed.\nPlease install it or download from the official source."))
        dpg.configure_item("tesseract_not_found_popup", label=self.trans.get("tesseract_not_found_title", "Tesseract not found"))

        popup_children = dpg.get_item_children("tesseract_not_found_popup", 1)
        if len(popup_children) > 1:
            dpg.configure_item(popup_children[1], label=self.trans.get("download_tesseract", "Download Tesseract"))

        print("UI updated with new translations.")

    def stop(self):
        self.stop_event.set()
        cv2.destroyAllWindows()
        print("BotFishTab остановлен.")
