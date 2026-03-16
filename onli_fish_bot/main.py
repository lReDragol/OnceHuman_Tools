from pathlib import Path
import copy
import threading
import time
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk
import webbrowser

import cv2
from fuzzywuzzy import fuzz
import mss
import numpy as np
import pyautogui

try:
    import pytesseract
    from pytesseract import TesseractNotFoundError
except ImportError:
    pytesseract = None

    class TesseractNotFoundError(RuntimeError):
        pass

try:
    import telebot
except ImportError:
    telebot = None

from functions import (
    apply_filter,
    draw_areas_on_frame,
    load_config,
    press_key,
    release_key,
    save_config,
    start_zone_creation,
)


BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"

FILTER_OPTIONS = ["Нет фильтра", "Градации серого", "Бинарный порог", "Края Кэнни"]
KEY_OPTIONS = ["a", "d", "f", "left mouse button", "TGBot"]
OCR_LANGUAGE_OPTIONS = ["rus", "eng"]


class FishBotApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Bot Fish Portable")
        self.root.geometry("1220x760")
        self.root.minsize(1080, 700)

        self.configure_style()

        self.config_data = load_config(str(CONFIG_PATH))
        self.zones = copy.deepcopy(self.config_data.get("zones", []))
        self.runtime_zones = copy.deepcopy(self.zones)

        self.stop_event = threading.Event()
        self.action_in_progress = threading.Event()
        self.worker_thread = None
        self.frame_open = False
        self.bot = None
        self.last_action_time = time.time()
        self.last_press_time = [{} for _ in self.runtime_zones]
        self.current_zone_index = None

        self.original_width, self.original_height = pyautogui.size()
        self.frame_width = 540
        self.frame_height = int(self.frame_width * self.original_height / self.original_width)

        self.status_var = tk.StringVar(value="Готово к запуску.")
        self.zone_hint_var = tk.StringVar(value="Выберите зону справа, чтобы редактировать её параметры.")
        self.ocr_monitor_var = tk.StringVar(value="OCR-монитор выключен.")

        self.frame_visible_var = tk.BooleanVar(value=self.config_data.get("frame_visible", False))
        self.text_visible_var = tk.BooleanVar(value=self.config_data.get("text_visible", False))
        self.show_all_text_var = tk.BooleanVar(value=self.config_data.get("show_all_text", False))
        self.bot_enabled_var = tk.BooleanVar(value=self.config_data.get("bot_enabled", False))
        self.always_on_top_var = tk.BooleanVar(value=self.config_data.get("always_on_top", False))
        self.anti_afk_var = tk.BooleanVar(value=self.config_data.get("anti_afk_enabled", False))
        self.telegram_bot_var = tk.BooleanVar(value=self.config_data.get("telegram_enabled", False))

        self.selected_filter = tk.StringVar(value=self.config_data.get("selected_filter", FILTER_OPTIONS[0]))
        self.scan_delay_var = tk.IntVar(value=self.config_data.get("scan_delay", 500))
        self.recognition_threshold_var = tk.IntVar(value=self.config_data.get("recognition_threshold", 40))
        self.selected_language = tk.StringVar(value=self.config_data.get("selected_language", "rus"))
        self.anti_afk_delay_var = tk.IntVar(value=self.config_data.get("anti_afk_delay", 10))
        self.telegram_bot_token_var = tk.StringVar(value=self.config_data.get("telegram_bot_token", ""))
        self.telegram_chat_id_var = tk.StringVar(value=self.config_data.get("telegram_chat_id", ""))

        self.zone_keybind_var = tk.StringVar(value=KEY_OPTIONS[0])
        self.zone_hold_var = tk.BooleanVar(value=False)
        self.zone_hold_duration_var = tk.StringVar(value="0")
        self.zone_delay_before_var = tk.StringVar(value="0")
        self.zone_delay_after_var = tk.StringVar(value=str(self.scan_delay_var.get()))
        self.zone_hold_lmb_var = tk.BooleanVar(value=False)
        self.zone_hold_lmb_duration_var = tk.StringVar(value="0")
        self.zone_selected_phrase_var = tk.StringVar(value="All")
        self.zone_coords_var = tk.StringVar(value="Не выбрано")

        self.build_ui()
        self.populate_zone_tree()
        self.apply_always_on_top()
        self.toggle_telegram_inputs()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def configure_style(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("App.TFrame", background="#f4f6fb")
        style.configure("Card.TLabelframe", padding=12)
        style.configure("Card.TLabelframe.Label", font=("Segoe UI", 10, "bold"))
        style.configure("Header.TLabel", font=("Segoe UI Semibold", 17))
        style.configure("Subtle.TLabel", foreground="#516078")
        style.configure("Accent.TButton", padding=(12, 8))
        style.configure("Danger.TButton", padding=(12, 8))
        style.configure("Treeview", rowheight=26)

        self.root.configure(bg="#f4f6fb")

    def build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        header = ttk.Frame(self.root, padding=(18, 16, 18, 8), style="App.TFrame")
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Bot Fish Portable", style="Header.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            header,
            text="Компактная версия с редактором зон и понятным статусом OCR.",
            style="Subtle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        actions = ttk.Frame(header, style="App.TFrame")
        actions.grid(row=0, column=1, rowspan=2, sticky="e")
        ttk.Button(actions, text="Старт", style="Accent.TButton", command=self.start_tracking).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(actions, text="Стоп", style="Danger.TButton", command=self.stop_tracking).grid(
            row=0, column=1, padx=(0, 8)
        )
        ttk.Button(actions, text="Создать зону", command=self.add_zone).grid(row=0, column=2, padx=(0, 8))
        ttk.Button(actions, text="Сохранить всё", command=self.save_all_settings).grid(row=0, column=3)

        content = ttk.Panedwindow(self.root, orient="horizontal")
        content.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 12))

        left_panel = ttk.Frame(content, padding=0, style="App.TFrame")
        right_panel = ttk.Frame(content, padding=0, style="App.TFrame")
        content.add(left_panel, weight=1)
        content.add(right_panel, weight=2)

        left_panel.columnconfigure(0, weight=1)
        right_panel.columnconfigure(0, weight=1)
        right_panel.rowconfigure(0, weight=1)

        self.build_left_panel(left_panel)
        self.build_right_panel(right_panel)

        footer = ttk.Frame(self.root, padding=(18, 0, 18, 16), style="App.TFrame")
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var, style="Subtle.TLabel").grid(row=0, column=0, sticky="w")

        github = ttk.Label(footer, text="GitHub lReDragol", foreground="#2563eb", cursor="hand2")
        github.grid(row=0, column=1, sticky="e")
        github.bind("<Button-1>", lambda _event: webbrowser.open_new("https://github.com/lReDragol"))

    def build_left_panel(self, parent):
        monitor_card = ttk.LabelFrame(parent, text="Управление", style="Card.TLabelframe")
        monitor_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        monitor_card.columnconfigure(0, weight=1)
        monitor_card.columnconfigure(1, weight=1)

        ttk.Checkbutton(monitor_card, text="Показывать кадр", variable=self.frame_visible_var).grid(
            row=0, column=0, sticky="w"
        )
        ttk.Checkbutton(monitor_card, text="Показывать OCR", variable=self.text_visible_var).grid(
            row=1, column=0, sticky="w", pady=(6, 0)
        )
        ttk.Checkbutton(
            monitor_card,
            text="Показывать полный текст",
            variable=self.show_all_text_var,
        ).grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Checkbutton(monitor_card, text="Бот активен", variable=self.bot_enabled_var).grid(
            row=0, column=1, sticky="w"
        )
        ttk.Checkbutton(
            monitor_card,
            text="Всегда сверху",
            variable=self.always_on_top_var,
            command=self.apply_always_on_top,
        ).grid(row=1, column=1, sticky="w", pady=(6, 0))

        ocr_card = ttk.LabelFrame(parent, text="OCR и действия", style="Card.TLabelframe")
        ocr_card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        ocr_card.columnconfigure(1, weight=1)

        ttk.Label(ocr_card, text="Фильтр").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            ocr_card,
            textvariable=self.selected_filter,
            values=FILTER_OPTIONS,
            state="readonly",
        ).grid(row=0, column=1, sticky="ew", padx=(10, 0))

        ttk.Label(ocr_card, text="Язык OCR").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Combobox(
            ocr_card,
            textvariable=self.selected_language,
            values=OCR_LANGUAGE_OPTIONS,
            state="readonly",
        ).grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(10, 0))

        ttk.Label(ocr_card, text="Задержка между нажатиями, мс").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Spinbox(ocr_card, from_=0, to=10000, textvariable=self.scan_delay_var).grid(
            row=2, column=1, sticky="ew", padx=(10, 0), pady=(10, 0)
        )

        ttk.Label(ocr_card, text="Порог совпадения, %").grid(row=3, column=0, sticky="w", pady=(10, 0))
        threshold_row = ttk.Frame(ocr_card)
        threshold_row.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=(10, 0))
        threshold_row.columnconfigure(0, weight=1)
        ttk.Scale(
            threshold_row,
            from_=0,
            to=100,
            variable=self.recognition_threshold_var,
            orient="horizontal",
        ).grid(row=0, column=0, sticky="ew")
        ttk.Label(threshold_row, textvariable=self.recognition_threshold_var, width=4).grid(row=0, column=1, padx=(8, 0))

        behavior_card = ttk.LabelFrame(parent, text="Поведение", style="Card.TLabelframe")
        behavior_card.grid(row=2, column=0, sticky="ew", pady=(0, 12))
        behavior_card.columnconfigure(1, weight=1)

        ttk.Checkbutton(
            behavior_card,
            text="Anti afk",
            variable=self.anti_afk_var,
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(behavior_card, text="Пауза, сек").grid(row=0, column=1, sticky="w", padx=(12, 0))
        ttk.Spinbox(behavior_card, from_=1, to=3600, textvariable=self.anti_afk_delay_var, width=8).grid(
            row=0, column=2, sticky="e"
        )

        ttk.Button(behavior_card, text="Проверить OCR", command=self.validate_ocr_setup).grid(
            row=1, column=0, columnspan=3, sticky="ew", pady=(10, 0)
        )

        ocr_output_card = ttk.LabelFrame(parent, text="OCR-монитор", style="Card.TLabelframe")
        ocr_output_card.grid(row=3, column=0, sticky="nsew")
        parent.rowconfigure(3, weight=1)
        ocr_output_card.columnconfigure(0, weight=1)
        ocr_output_card.rowconfigure(0, weight=1)

        self.ocr_output = tk.Text(
            ocr_output_card,
            height=14,
            wrap="word",
            bg="#121826",
            fg="#edf2ff",
            insertbackground="#edf2ff",
            relief="flat",
            padx=10,
            pady=10,
        )
        self.ocr_output.grid(row=0, column=0, sticky="nsew")
        self.ocr_output.insert("1.0", self.ocr_monitor_var.get())
        self.ocr_output.configure(state="disabled")

    def build_right_panel(self, parent):
        notebook = ttk.Notebook(parent)
        notebook.grid(row=0, column=0, sticky="nsew")

        zones_tab = ttk.Frame(notebook, padding=14)
        telegram_tab = ttk.Frame(notebook, padding=14)
        notebook.add(zones_tab, text="Зоны")
        notebook.add(telegram_tab, text="Telegram")

        zones_tab.columnconfigure(0, weight=1)
        zones_tab.rowconfigure(1, weight=1)
        telegram_tab.columnconfigure(0, weight=1)

        toolbar = ttk.Frame(zones_tab)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        toolbar.columnconfigure(0, weight=1)
        ttk.Label(toolbar, textvariable=self.zone_hint_var, style="Subtle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(toolbar, text="Удалить зону", command=self.remove_selected_zone).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(toolbar, text="Сохранить зону", command=self.save_selected_zone).grid(row=0, column=2, padx=(8, 0))

        body = ttk.Panedwindow(zones_tab, orient="vertical")
        body.grid(row=1, column=0, sticky="nsew")

        tree_card = ttk.LabelFrame(body, text="Список зон", style="Card.TLabelframe")
        editor_card = ttk.LabelFrame(body, text="Редактор зоны", style="Card.TLabelframe")
        body.add(tree_card, weight=1)
        body.add(editor_card, weight=2)

        self.build_zone_tree(tree_card)
        self.build_zone_editor(editor_card)
        self.build_telegram_tab(telegram_tab)

    def build_zone_tree(self, parent):
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        columns = ("zone", "coords", "key", "phrases")
        self.zone_tree = ttk.Treeview(parent, columns=columns, show="headings", selectmode="browse", height=8)
        self.zone_tree.grid(row=0, column=0, sticky="nsew")

        headings = {
            "zone": "№",
            "coords": "Координаты",
            "key": "Действие",
            "phrases": "Фраз",
        }
        widths = {"zone": 60, "coords": 260, "key": 160, "phrases": 80}

        for column in columns:
            self.zone_tree.heading(column, text=headings[column])
            self.zone_tree.column(column, width=widths[column], anchor="w")

        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=self.zone_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.zone_tree.configure(yscrollcommand=scrollbar.set)
        self.zone_tree.bind("<<TreeviewSelect>>", self.on_zone_selected)

    def build_zone_editor(self, parent):
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(5, weight=1)

        ttk.Label(parent, text="Координаты").grid(row=0, column=0, sticky="w")
        ttk.Label(parent, textvariable=self.zone_coords_var).grid(row=0, column=1, sticky="w", padx=(10, 0))

        ttk.Label(parent, text="Клавиша / действие").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.keybind_box = ttk.Combobox(parent, textvariable=self.zone_keybind_var, values=KEY_OPTIONS, state="readonly")
        self.keybind_box.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(10, 0))

        phrase_row = ttk.Frame(parent)
        phrase_row.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        phrase_row.columnconfigure(1, weight=1)
        ttk.Label(phrase_row, text="Активная фраза").grid(row=0, column=0, sticky="w")
        self.selected_phrase_box = ttk.Combobox(
            phrase_row,
            textvariable=self.zone_selected_phrase_var,
            values=["All"],
            state="readonly",
        )
        self.selected_phrase_box.grid(row=0, column=1, sticky="ew", padx=(10, 0))

        timings = ttk.Frame(parent)
        timings.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        for index in range(4):
            timings.columnconfigure(index, weight=1)

        ttk.Checkbutton(timings, text="Удерживать кнопку", variable=self.zone_hold_var).grid(row=0, column=0, sticky="w")
        ttk.Label(timings, text="Длительность, мс").grid(row=0, column=1, sticky="w")
        ttk.Entry(timings, textvariable=self.zone_hold_duration_var, width=10).grid(row=0, column=2, sticky="ew", padx=(8, 0))

        ttk.Label(timings, text="Задержка до, мс").grid(row=1, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(timings, textvariable=self.zone_delay_before_var, width=10).grid(
            row=1, column=1, sticky="ew", padx=(8, 0), pady=(10, 0)
        )
        ttk.Label(timings, text="Задержка после, мс").grid(row=1, column=2, sticky="w", padx=(16, 0), pady=(10, 0))
        ttk.Entry(timings, textvariable=self.zone_delay_after_var, width=10).grid(
            row=1, column=3, sticky="ew", padx=(8, 0), pady=(10, 0)
        )

        ttk.Checkbutton(timings, text="Дожимать ЛКМ", variable=self.zone_hold_lmb_var).grid(
            row=2, column=0, sticky="w", pady=(10, 0)
        )
        ttk.Label(timings, text="ЛКМ, мс").grid(row=2, column=1, sticky="w", pady=(10, 0))
        ttk.Entry(timings, textvariable=self.zone_hold_lmb_duration_var, width=10).grid(
            row=2, column=2, sticky="ew", padx=(8, 0), pady=(10, 0)
        )

        phrases_card = ttk.LabelFrame(parent, text="Фразы", style="Card.TLabelframe")
        phrases_card.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(14, 0))
        phrases_card.columnconfigure(0, weight=1)
        phrases_card.rowconfigure(0, weight=1)

        self.phrases_listbox = tk.Listbox(phrases_card, height=8, activestyle="none")
        self.phrases_listbox.grid(row=0, column=0, sticky="nsew")
        phrase_scrollbar = ttk.Scrollbar(phrases_card, orient="vertical", command=self.phrases_listbox.yview)
        phrase_scrollbar.grid(row=0, column=1, sticky="ns")
        self.phrases_listbox.configure(yscrollcommand=phrase_scrollbar.set)

        phrase_buttons = ttk.Frame(phrases_card)
        phrase_buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(phrase_buttons, text="Добавить фразу", command=self.add_phrase).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(phrase_buttons, text="Удалить фразу", command=self.remove_selected_phrase).grid(row=0, column=1)

    def build_telegram_tab(self, parent):
        parent.columnconfigure(0, weight=1)

        card = ttk.LabelFrame(parent, text="Уведомления", style="Card.TLabelframe")
        card.grid(row=0, column=0, sticky="nsew")
        card.columnconfigure(1, weight=1)

        ttk.Checkbutton(
            card,
            text="Включить Telegram-бота",
            variable=self.telegram_bot_var,
            command=self.toggle_telegram_inputs,
        ).grid(row=0, column=0, columnspan=2, sticky="w")

        ttk.Label(card, text="Bot Token").grid(row=1, column=0, sticky="w", pady=(12, 0))
        self.bot_token_entry = ttk.Entry(card, textvariable=self.telegram_bot_token_var)
        self.bot_token_entry.grid(row=1, column=1, sticky="ew", pady=(12, 0), padx=(10, 0))

        ttk.Label(card, text="Chat ID").grid(row=2, column=0, sticky="w", pady=(10, 0))
        self.chat_id_entry = ttk.Entry(card, textvariable=self.telegram_chat_id_var)
        self.chat_id_entry.grid(row=2, column=1, sticky="ew", pady=(10, 0), padx=(10, 0))

        self.telegram_connect_button = ttk.Button(
            card,
            text="Подключить и проверить",
            command=self.apply_telegram_settings,
        )
        self.telegram_connect_button.grid(row=3, column=0, columnspan=2, sticky="ew", pady=(14, 0))

        ttk.Label(
            card,
            text="Для уведомлений у зоны выберите действие TGBot. Проверка отправит сообщение 'connect'.",
            style="Subtle.TLabel",
            wraplength=520,
            justify="left",
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def set_status(self, message):
        timestamped = f"{time.strftime('%H:%M:%S')} {message}"
        print(timestamped)
        self.run_on_ui_thread(lambda: self.status_var.set(timestamped))

    def run_on_ui_thread(self, callback):
        try:
            self.root.after(0, callback)
        except RuntimeError:
            pass

    def populate_zone_tree(self):
        current_selection = self.current_zone_index
        for item_id in self.zone_tree.get_children():
            self.zone_tree.delete(item_id)

        for idx, zone in enumerate(self.zones):
            coords = ", ".join(map(str, zone.get("c", [])))
            keybind = zone.get("keybind", "a")
            phrase_count = len(zone.get("p", []))
            self.zone_tree.insert("", "end", iid=str(idx), values=(idx + 1, coords, keybind, phrase_count))

        if self.zones:
            target_index = current_selection if current_selection is not None and current_selection < len(self.zones) else 0
            self.zone_tree.selection_set(str(target_index))
            self.zone_tree.focus(str(target_index))
            self.load_zone_into_editor(target_index)
        else:
            self.current_zone_index = None
            self.zone_coords_var.set("Не выбрано")
            self.zone_hint_var.set("Сначала создайте хотя бы одну зону.")
            self.clear_zone_editor()

    def clear_zone_editor(self):
        self.zone_keybind_var.set(KEY_OPTIONS[0])
        self.zone_hold_var.set(False)
        self.zone_hold_duration_var.set("0")
        self.zone_delay_before_var.set("0")
        self.zone_delay_after_var.set(str(self.scan_delay_var.get()))
        self.zone_hold_lmb_var.set(False)
        self.zone_hold_lmb_duration_var.set("0")
        self.zone_selected_phrase_var.set("All")
        self.selected_phrase_box.configure(values=["All"])
        self.phrases_listbox.delete(0, tk.END)

    def on_zone_selected(self, _event=None):
        selection = self.zone_tree.selection()
        if not selection:
            return
        self.load_zone_into_editor(int(selection[0]))

    def load_zone_into_editor(self, index):
        if index < 0 or index >= len(self.zones):
            self.clear_zone_editor()
            return

        zone = self.zones[index]
        self.current_zone_index = index
        self.zone_hint_var.set(f"Редактируется зона #{index + 1}.")
        self.zone_coords_var.set(", ".join(map(str, zone.get("c", []))) or "Не задано")
        self.zone_keybind_var.set(zone.get("keybind", "a"))
        self.zone_hold_var.set(zone.get("hold", False))
        self.zone_hold_duration_var.set(str(zone.get("hold_duration", 0)))
        self.zone_delay_before_var.set(str(zone.get("delay_before", 0)))
        self.zone_delay_after_var.set(str(zone.get("delay_after", self.scan_delay_var.get())))
        self.zone_hold_lmb_var.set(zone.get("hold_lmb", False))
        self.zone_hold_lmb_duration_var.set(str(zone.get("hold_lmb_duration", 0)))

        phrases = zone.get("p", [])
        phrase_values = ["All"] + phrases
        self.selected_phrase_box.configure(values=phrase_values)
        selected_phrase = zone.get("selected_phrase", "All")
        self.zone_selected_phrase_var.set(selected_phrase if selected_phrase in phrase_values else "All")

        self.phrases_listbox.delete(0, tk.END)
        for phrase in phrases:
            self.phrases_listbox.insert(tk.END, phrase)

    def get_selected_zone(self):
        if self.current_zone_index is None or self.current_zone_index >= len(self.zones):
            return None
        return self.zones[self.current_zone_index]

    def parse_int(self, raw_value, fallback=0):
        try:
            return max(0, int(raw_value))
        except (TypeError, ValueError):
            return fallback

    def collect_zone_from_editor(self):
        zone = self.get_selected_zone()
        if zone is None:
            return None

        selected_phrase = self.zone_selected_phrase_var.get() or "All"
        zone["keybind"] = self.zone_keybind_var.get() or "a"
        zone["hold"] = self.zone_hold_var.get()
        zone["hold_duration"] = self.parse_int(self.zone_hold_duration_var.get())
        zone["delay_before"] = self.parse_int(self.zone_delay_before_var.get())
        zone["delay_after"] = self.parse_int(self.zone_delay_after_var.get(), self.scan_delay_var.get())
        zone["hold_lmb"] = self.zone_hold_lmb_var.get()
        zone["hold_lmb_duration"] = self.parse_int(self.zone_hold_lmb_duration_var.get())
        zone["selected_phrase"] = selected_phrase
        return zone

    def save_selected_zone(self):
        zone = self.collect_zone_from_editor()
        if zone is None:
            messagebox.showinfo("Зоны", "Выберите зону для сохранения.")
            return

        self.zones[self.current_zone_index] = zone
        self.persist_current_state()
        self.populate_zone_tree()
        self.set_status(f"Зона #{self.current_zone_index + 1} сохранена.")

    def persist_current_state(self):
        self.config_data["zones"] = copy.deepcopy(self.zones)
        self.config_data["selected_language"] = self.selected_language.get()
        self.config_data["recognition_threshold"] = self.recognition_threshold_var.get()
        self.config_data["scan_delay"] = self.scan_delay_var.get()
        self.config_data["selected_filter"] = self.selected_filter.get()
        self.config_data["anti_afk_delay"] = self.anti_afk_delay_var.get()
        self.config_data["telegram_bot_token"] = self.telegram_bot_token_var.get().strip()
        self.config_data["telegram_chat_id"] = self.telegram_chat_id_var.get().strip()
        self.config_data["telegram_enabled"] = self.telegram_bot_var.get()
        self.config_data["always_on_top"] = self.always_on_top_var.get()
        self.config_data["anti_afk_enabled"] = self.anti_afk_var.get()
        self.config_data["bot_enabled"] = self.bot_enabled_var.get()
        self.config_data["frame_visible"] = self.frame_visible_var.get()
        self.config_data["text_visible"] = self.text_visible_var.get()
        self.config_data["show_all_text"] = self.show_all_text_var.get()
        save_config(self.config_data, str(CONFIG_PATH))
        self.runtime_zones = copy.deepcopy(self.zones)
        self.last_press_time = [{} for _ in self.runtime_zones]

    def save_all_settings(self):
        if self.current_zone_index is not None:
            self.collect_zone_from_editor()
        self.persist_current_state()
        self.populate_zone_tree()
        self.set_status("Настройки сохранены.")

    def reload_config_from_disk(self):
        self.config_data = load_config(str(CONFIG_PATH))
        self.zones = copy.deepcopy(self.config_data.get("zones", []))
        self.runtime_zones = copy.deepcopy(self.zones)
        self.last_press_time = [{} for _ in self.runtime_zones]
        self.populate_zone_tree()

    def add_zone(self):
        self.save_all_settings()
        start_zone_creation(str(CONFIG_PATH), callback=self.reload_config_from_disk)
        self.set_status("Выбор зон завершён.")

    def remove_selected_zone(self):
        if self.current_zone_index is None:
            messagebox.showinfo("Зоны", "Сначала выберите зону.")
            return

        removed_index = self.current_zone_index
        self.zones.pop(removed_index)
        self.current_zone_index = None
        self.persist_current_state()
        self.populate_zone_tree()
        self.set_status(f"Зона #{removed_index + 1} удалена.")

    def add_phrase(self):
        zone = self.get_selected_zone()
        if zone is None:
            messagebox.showinfo("Фразы", "Сначала выберите зону.")
            return

        phrase = simpledialog.askstring("Новая фраза", "Введите фразу для отслеживания:", parent=self.root)
        if not phrase:
            return

        phrase = phrase.strip()
        if not phrase:
            return

        zone.setdefault("p", []).append(phrase)
        self.load_zone_into_editor(self.current_zone_index)
        self.set_status(f"Фраза добавлена в зону #{self.current_zone_index + 1}.")

    def remove_selected_phrase(self):
        zone = self.get_selected_zone()
        if zone is None:
            messagebox.showinfo("Фразы", "Сначала выберите зону.")
            return

        selection = self.phrases_listbox.curselection()
        if not selection:
            messagebox.showinfo("Фразы", "Выберите фразу из списка.")
            return

        phrase = self.phrases_listbox.get(selection[0])
        phrases = zone.get("p", [])
        if phrase in phrases:
            phrases.remove(phrase)
            if self.zone_selected_phrase_var.get() == phrase:
                self.zone_selected_phrase_var.set("All")
            self.load_zone_into_editor(self.current_zone_index)
            self.set_status(f"Фраза удалена из зоны #{self.current_zone_index + 1}.")

    def apply_always_on_top(self):
        is_topmost = self.always_on_top_var.get()
        self.root.attributes("-topmost", is_topmost)
        if self.frame_open:
            cv2.setWindowProperty("Frame", cv2.WND_PROP_TOPMOST, 1 if is_topmost else 0)

    def toggle_telegram_inputs(self):
        state = "normal" if self.telegram_bot_var.get() else "disabled"
        self.bot_token_entry.configure(state=state)
        self.chat_id_entry.configure(state=state)
        self.telegram_connect_button.configure(state=state)
        if not self.telegram_bot_var.get():
            self.bot = None

    def apply_telegram_settings(self):
        if not self.telegram_bot_var.get():
            self.bot = None
            self.set_status("Telegram-бот отключён.")
            return True

        if telebot is None:
            messagebox.showerror("Telegram", "Пакет pyTelegramBotAPI не установлен.")
            return False

        bot_token = self.telegram_bot_token_var.get().strip()
        chat_id = self.telegram_chat_id_var.get().strip()
        if not bot_token or not chat_id:
            messagebox.showerror("Telegram", "Заполните Bot Token и Chat ID.")
            return False

        try:
            self.bot = telebot.TeleBot(bot_token)
            self.bot.send_message(chat_id, "connect")
            self.set_status("Telegram-бот подключён и проверен.")
            self.persist_current_state()
            return True
        except Exception as exc:
            self.bot = None
            messagebox.showerror("Telegram", f"Не удалось подключить Telegram-бота:\n{exc}")
            self.set_status(f"Ошибка Telegram: {exc}")
            return False

    def validate_ocr_setup(self):
        try:
            self.ensure_ocr_ready(show_success=True)
            return True
        except RuntimeError as exc:
            messagebox.showerror("OCR", str(exc))
            self.set_status(f"OCR не готов: {exc}")
            return False

    def ensure_ocr_ready(self, show_success=False):
        if pytesseract is None:
            raise RuntimeError("Модуль pytesseract не установлен.")

        try:
            pytesseract.get_tesseract_version()
        except TesseractNotFoundError as exc:
            raise RuntimeError(
                "Tesseract OCR не найден. Установите Tesseract и языковые пакеты rus/eng."
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Не удалось проверить Tesseract OCR: {exc}") from exc

        try:
            languages = set(pytesseract.get_languages(config=""))
        except Exception as exc:
            raise RuntimeError(f"Не удалось получить список языков OCR: {exc}") from exc

        required_language = self.selected_language.get()
        if required_language not in languages:
            available = ", ".join(sorted(languages)) or "список пуст"
            raise RuntimeError(
                f"Для OCR не установлен язык '{required_language}'. Доступны: {available}"
            )

        if show_success:
            self.set_status(f"OCR готов. Найден язык '{required_language}'.")

    def start_tracking(self):
        if self.worker_thread and self.worker_thread.is_alive():
            self.set_status("Отслеживание уже запущено.")
            return

        if not self.zones:
            messagebox.showwarning("Старт", "Сначала создайте хотя бы одну зону.")
            return

        if not self.validate_ocr_setup():
            return

        if self.telegram_bot_var.get() and not self.apply_telegram_settings():
            return

        self.save_all_settings()
        self.stop_event.clear()
        self.last_action_time = time.time()
        self.worker_thread = threading.Thread(target=self.run_tracking_loop, daemon=True)
        self.worker_thread.start()
        self.set_status("Отслеживание запущено.")

    def find_match(self, phrases, recognized_text_psm6, recognized_text_psm7):
        threshold = self.recognition_threshold_var.get()

        for phrase in phrases:
            target_phrase = phrase.lower()
            if target_phrase in recognized_text_psm6 or target_phrase in recognized_text_psm7:
                return phrase

            ratio_psm6 = fuzz.partial_ratio(target_phrase, recognized_text_psm6)
            ratio_psm7 = fuzz.partial_ratio(target_phrase, recognized_text_psm7)
            if ratio_psm6 > threshold or ratio_psm7 > threshold:
                return phrase

        return "-"

    def format_ocr_lines(self, zone_number, matched_text, ocr_result_psm6, ocr_result_psm7):
        if self.show_all_text_var.get():
            return f"Зона {zone_number}: {ocr_result_psm6.strip()} | {ocr_result_psm7.strip()}"
        return f"Зона {zone_number}: {matched_text}"

    def update_ocr_output(self, lines):
        def writer():
            self.ocr_output.configure(state="normal")
            self.ocr_output.delete("1.0", tk.END)
            if lines:
                self.ocr_output.insert("1.0", "\n".join(lines))
            else:
                self.ocr_output.insert("1.0", "OCR-монитор выключен.")
            self.ocr_output.configure(state="disabled")

        self.run_on_ui_thread(writer)

    def run_tracking_loop(self):
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                while not self.stop_event.is_set():
                    frame = np.array(sct.grab(monitor))
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)

                    display_frame = apply_filter(frame.copy(), self.selected_filter.get())
                    if len(display_frame.shape) == 2:
                        preview_frame = cv2.cvtColor(display_frame, cv2.COLOR_GRAY2RGB)
                    else:
                        preview_frame = display_frame

                    small_frame = cv2.resize(preview_frame, (self.frame_width, self.frame_height))
                    scale_x = self.frame_width / self.original_width
                    scale_y = self.frame_height / self.original_height
                    draw_areas_on_frame(small_frame, self.runtime_zones, scale_x, scale_y)

                    if self.frame_visible_var.get():
                        cv2.imshow("Frame", small_frame)
                        self.frame_open = True
                        cv2.setWindowProperty("Frame", cv2.WND_PROP_TOPMOST, 1 if self.always_on_top_var.get() else 0)
                    elif self.frame_open:
                        cv2.destroyWindow("Frame")
                        self.frame_open = False

                    current_time = time.time()
                    ocr_lines = []

                    if len(self.last_press_time) != len(self.runtime_zones):
                        self.last_press_time = [{} for _ in self.runtime_zones]

                    for idx, zone_data in enumerate(self.runtime_zones):
                        x1, y1, x2, y2 = map(int, zone_data.get("c", [0, 0, 0, 0]))
                        zone_frame = frame[y1:y2, x1:x2]
                        if zone_frame.size == 0:
                            ocr_lines.append(f"Зона {idx + 1}: некорректные координаты")
                            continue

                        zone_frame_filtered = apply_filter(zone_frame, self.selected_filter.get())
                        ocr_lang = self.selected_language.get()
                        ocr_result_psm6 = pytesseract.image_to_string(zone_frame_filtered, lang=ocr_lang, config="--psm 6")
                        ocr_result_psm7 = pytesseract.image_to_string(zone_frame_filtered, lang=ocr_lang, config="--psm 7")

                        phrases = zone_data.get("p", [])
                        selected_phrase = zone_data.get("selected_phrase", "All")
                        phrases_to_check = phrases if selected_phrase == "All" else [selected_phrase]
                        matched_text = self.find_match(
                            phrases_to_check,
                            ocr_result_psm6.lower(),
                            ocr_result_psm7.lower(),
                        ) if phrases_to_check else "-"

                        ocr_lines.append(self.format_ocr_lines(idx + 1, matched_text, ocr_result_psm6, ocr_result_psm7))

                        if matched_text == "-":
                            continue

                        if not self.bot_enabled_var.get():
                            continue

                        press_delay = self.parse_int(zone_data.get("press_delay", self.scan_delay_var.get()), self.scan_delay_var.get()) / 1000.0
                        zone_last_press_time = self.last_press_time[idx]
                        last_press = zone_last_press_time.get(matched_text, 0)
                        if current_time - last_press < press_delay or self.action_in_progress.is_set():
                            continue

                        zone_last_press_time[matched_text] = current_time
                        self.last_action_time = current_time

                        if zone_data.get("keybind") == "TGBot":
                            if self.telegram_bot_var.get() and self.bot:
                                message = f"Найдена '{matched_text}' в зоне {idx + 1}"
                                try:
                                    self.bot.send_message(self.telegram_chat_id_var.get().strip(), message)
                                    self.set_status(f"Отправлено сообщение в Telegram: {message}")
                                except Exception as exc:
                                    self.set_status(f"Ошибка Telegram: {exc}")
                            continue

                        threading.Thread(
                            target=self.execute_zone_action,
                            args=(zone_data,),
                            daemon=True,
                        ).start()
                        self.set_status(f"Распознано '{matched_text}' в зоне {idx + 1}.")

                    if self.text_visible_var.get():
                        self.update_ocr_output(ocr_lines)
                    else:
                        self.update_ocr_output([])

                    anti_afk_delay = max(1, self.anti_afk_delay_var.get())
                    if self.anti_afk_var.get() and (current_time - self.last_action_time > anti_afk_delay):
                        pyautogui.click()
                        self.last_action_time = current_time
                        self.set_status(f"Anti afk: выполнен клик после {anti_afk_delay} секунд бездействия.")

                    if cv2.waitKey(1) == ord("q"):
                        self.run_on_ui_thread(self.stop_tracking)
                        break
        except Exception as exc:
            self.set_status(f"Ошибка отслеживания: {exc}")
        finally:
            self.frame_open = False
            cv2.destroyAllWindows()
            self.run_on_ui_thread(lambda: setattr(self, "worker_thread", None))

    def execute_zone_action(self, zone_data):
        keybind = zone_data.get("keybind", "a")
        hold_enabled = zone_data.get("hold", False)
        hold_duration = self.parse_int(zone_data.get("hold_duration", 0)) / 1000.0
        delay_before = self.parse_int(zone_data.get("delay_before", 0)) / 1000.0
        delay_after = self.parse_int(zone_data.get("delay_after", 0)) / 1000.0
        hold_lmb = zone_data.get("hold_lmb", False)
        hold_lmb_duration = self.parse_int(zone_data.get("hold_lmb_duration", 0)) / 1000.0

        self.action_in_progress.set()
        try:
            time.sleep(delay_before)
            press_key(keybind)
            if hold_enabled and hold_duration > 0:
                time.sleep(hold_duration)
            release_key(keybind)

            if hold_lmb:
                pyautogui.mouseDown(button="left")
                time.sleep(hold_lmb_duration)
                pyautogui.mouseUp(button="left")

            time.sleep(delay_after)
        finally:
            self.action_in_progress.clear()

    def stop_tracking(self):
        self.stop_event.set()
        if self.frame_open:
            cv2.destroyAllWindows()
            self.frame_open = False
        self.update_ocr_output([])
        self.set_status("Отслеживание остановлено.")

    def on_closing(self):
        self.stop_tracking()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1)
        self.root.destroy()

    def run(self):
        self.root.mainloop()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    FishBotApp().run()
