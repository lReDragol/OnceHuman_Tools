from pathlib import Path
import copy
import sys
import threading
import time
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

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from functions import (
    apply_filter,
    draw_areas_on_frame,
    load_config,
    press_key,
    release_key,
    save_config,
    start_zone_creation,
)


IS_FROZEN = getattr(sys, "frozen", False)
BASE_DIR = Path(sys.executable).resolve().parent if IS_FROZEN else Path(__file__).resolve().parent
RESOURCE_ROOT = Path(getattr(sys, "_MEIPASS", BASE_DIR.parent if not IS_FROZEN else BASE_DIR))
CONFIG_PATH = BASE_DIR / "config.json"

FILTER_OPTIONS = ["Нет фильтра", "Градации серого", "Бинарный порог", "Края Кэнни"]
KEY_OPTIONS = ["a", "d", "f", "left mouse button", "TGBot"]
OCR_LANGUAGE_OPTIONS = ["rus", "eng"]
APP_STYLESHEET = """
QMainWindow, QWidget { background: #f4f6fb; color: #182131; }
QGroupBox { border: 1px solid #d6deeb; border-radius: 12px; margin-top: 12px; padding: 14px; font-weight: 600; background: #ffffff; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 4px; }
QPushButton { background: #e8eefb; border: 1px solid #c8d5ef; border-radius: 10px; padding: 8px 12px; }
QPushButton:hover { background: #dce7fb; }
QPushButton#primaryButton { background: #2563eb; color: #ffffff; border-color: #1d4ed8; }
QPushButton#dangerButton { background: #dc2626; color: #ffffff; border-color: #b91c1c; }
QComboBox, QSpinBox, QLineEdit, QPlainTextEdit, QTreeWidget, QListWidget { background: #ffffff; border: 1px solid #cfd7e6; border-radius: 10px; padding: 6px 8px; }
QTabWidget::pane { border: 1px solid #d6deeb; border-radius: 12px; background: #ffffff; }
QTabBar::tab { background: #e9eef7; border: 1px solid #d6deeb; border-bottom: none; padding: 8px 14px; border-top-left-radius: 10px; border-top-right-radius: 10px; margin-right: 4px; }
QTabBar::tab:selected { background: #ffffff; }
QPlainTextEdit#ocrMonitor { background: #121826; color: #edf2ff; border-color: #0f172a; }
QLabel#titleLabel { font-size: 22px; font-weight: 700; }
QLabel#mutedLabel { color: #5b677b; }
QLabel#statusLabel { color: #516078; }
"""


class UiBridge(QObject):
    status_message = Signal(str)
    ocr_output = Signal(list)
    tracking_finished = Signal()
    stop_requested = Signal()


class FishBotApp(QMainWindow):
    def __init__(self):
        super().__init__()

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

        self.settings_state = {}
        self.bridge = UiBridge()
        self.bridge.status_message.connect(self._apply_status)
        self.bridge.ocr_output.connect(self._apply_ocr_output)
        self.bridge.tracking_finished.connect(self._on_tracking_finished)
        self.bridge.stop_requested.connect(self.stop_tracking)

        self.setWindowTitle("Bot Fish Portable V4")
        self.resize(1220, 760)
        self.setMinimumSize(1080, 700)
        self.setStyleSheet(APP_STYLESHEET)
        icon_path = RESOURCE_ROOT / "data" / "icons" / "fish.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        self.build_ui()
        self.sync_runtime_state()
        self.populate_zone_tree()
        self.apply_always_on_top()
        self.toggle_telegram_inputs()
        self._apply_ocr_output([])

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(18, 16, 18, 16)
        root_layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_left = QVBoxLayout()
        title_label = QLabel("Bot Fish Portable V4")
        title_label.setObjectName("titleLabel")
        subtitle_label = QLabel("Практичный интерфейс на PySide6 с редактором зон и понятным OCR-монитором.")
        subtitle_label.setObjectName("mutedLabel")
        header_left.addWidget(title_label)
        header_left.addWidget(subtitle_label)
        header_layout.addLayout(header_left, stretch=1)

        actions_layout = QHBoxLayout()
        self.start_button = QPushButton("Старт")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self.start_tracking)
        self.stop_button = QPushButton("Стоп")
        self.stop_button.setObjectName("dangerButton")
        self.stop_button.clicked.connect(self.stop_tracking)
        create_zone_button = QPushButton("Создать зону")
        create_zone_button.clicked.connect(self.add_zone)
        save_all_button = QPushButton("Сохранить всё")
        save_all_button.clicked.connect(self.save_all_settings)
        for button in (self.start_button, self.stop_button, create_zone_button, save_all_button):
            actions_layout.addWidget(button)
        header_layout.addLayout(actions_layout)
        root_layout.addLayout(header_layout)

        content_splitter = QSplitter(Qt.Horizontal)
        root_layout.addWidget(content_splitter, stretch=1)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        left_layout.addWidget(self.build_management_card())
        left_layout.addWidget(self.build_ocr_card())
        left_layout.addWidget(self.build_behavior_card())
        left_layout.addWidget(self.build_ocr_monitor_card(), stretch=1)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)
        right_layout.addWidget(self.build_right_tabs(), stretch=1)

        content_splitter.addWidget(left_panel)
        content_splitter.addWidget(right_panel)
        content_splitter.setStretchFactor(0, 1)
        content_splitter.setStretchFactor(1, 2)

        footer_layout = QHBoxLayout()
        self.status_label = QLabel("Готово к запуску.")
        self.status_label.setObjectName("statusLabel")
        footer_layout.addWidget(self.status_label, stretch=1)

        github_button = QPushButton("GitHub lReDragol")
        github_button.clicked.connect(lambda: webbrowser.open_new("https://github.com/lReDragol"))
        footer_layout.addWidget(github_button)
        root_layout.addLayout(footer_layout)

    def build_management_card(self):
        group = QGroupBox("Управление")
        layout = QGridLayout(group)

        self.frame_checkbox = QCheckBox("Показывать кадр")
        self.frame_checkbox.setChecked(self.config_data.get("frame_visible", False))
        self.text_checkbox = QCheckBox("Показывать OCR")
        self.text_checkbox.setChecked(self.config_data.get("text_visible", False))
        self.show_all_checkbox = QCheckBox("Показывать полный текст")
        self.show_all_checkbox.setChecked(self.config_data.get("show_all_text", False))
        self.bot_enabled_checkbox = QCheckBox("Бот активен")
        self.bot_enabled_checkbox.setChecked(self.config_data.get("bot_enabled", False))
        self.always_on_top_checkbox = QCheckBox("Всегда сверху")
        self.always_on_top_checkbox.setChecked(self.config_data.get("always_on_top", False))
        self.always_on_top_checkbox.stateChanged.connect(self.apply_always_on_top)

        layout.addWidget(self.frame_checkbox, 0, 0)
        layout.addWidget(self.bot_enabled_checkbox, 0, 1)
        layout.addWidget(self.text_checkbox, 1, 0)
        layout.addWidget(self.always_on_top_checkbox, 1, 1)
        layout.addWidget(self.show_all_checkbox, 2, 0, 1, 2)

        for widget in (
            self.frame_checkbox,
            self.text_checkbox,
            self.show_all_checkbox,
            self.bot_enabled_checkbox,
            self.always_on_top_checkbox,
        ):
            widget.stateChanged.connect(self.sync_runtime_state)

        return group

    def build_ocr_card(self):
        group = QGroupBox("OCR и действия")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(FILTER_OPTIONS)
        self.filter_combo.setCurrentText(self.config_data.get("selected_filter", FILTER_OPTIONS[0]))

        self.language_combo = QComboBox()
        self.language_combo.addItems(OCR_LANGUAGE_OPTIONS)
        self.language_combo.setCurrentText(self.config_data.get("selected_language", "rus"))

        self.scan_delay_spin = QSpinBox()
        self.scan_delay_spin.setRange(0, 10000)
        self.scan_delay_spin.setValue(self.config_data.get("scan_delay", 500))

        self.threshold_spin = QSpinBox()
        self.threshold_spin.setRange(0, 100)
        self.threshold_spin.setValue(self.config_data.get("recognition_threshold", 40))

        form.addRow("Фильтр", self.filter_combo)
        form.addRow("Язык OCR", self.language_combo)
        form.addRow("Задержка между нажатиями, мс", self.scan_delay_spin)
        form.addRow("Порог совпадения, %", self.threshold_spin)

        for widget in (self.filter_combo, self.language_combo):
            widget.currentTextChanged.connect(self.sync_runtime_state)
        for widget in (self.scan_delay_spin, self.threshold_spin):
            widget.valueChanged.connect(self.sync_runtime_state)

        return group

    def build_behavior_card(self):
        group = QGroupBox("Поведение")
        layout = QGridLayout(group)

        self.anti_afk_checkbox = QCheckBox("Anti afk")
        self.anti_afk_checkbox.setChecked(self.config_data.get("anti_afk_enabled", False))
        self.anti_afk_checkbox.stateChanged.connect(self.sync_runtime_state)

        self.anti_afk_spin = QSpinBox()
        self.anti_afk_spin.setRange(1, 3600)
        self.anti_afk_spin.setValue(self.config_data.get("anti_afk_delay", 10))
        self.anti_afk_spin.valueChanged.connect(self.sync_runtime_state)

        check_ocr_button = QPushButton("Проверить OCR")
        check_ocr_button.clicked.connect(self.validate_ocr_setup)

        layout.addWidget(self.anti_afk_checkbox, 0, 0)
        layout.addWidget(QLabel("Пауза, сек"), 0, 1)
        layout.addWidget(self.anti_afk_spin, 0, 2)
        layout.addWidget(check_ocr_button, 1, 0, 1, 3)
        return group

    def build_ocr_monitor_card(self):
        group = QGroupBox("OCR-монитор")
        layout = QVBoxLayout(group)
        self.ocr_output = QPlainTextEdit()
        self.ocr_output.setObjectName("ocrMonitor")
        self.ocr_output.setReadOnly(True)
        layout.addWidget(self.ocr_output)
        return group

    def build_right_tabs(self):
        tabs = QTabWidget()
        tabs.addTab(self.build_zones_tab(), "Зоны")
        tabs.addTab(self.build_telegram_tab(), "Telegram")
        return tabs

    def build_zones_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        self.zone_hint_label = QLabel("Выберите зону справа, чтобы редактировать её параметры.")
        self.zone_hint_label.setObjectName("mutedLabel")
        toolbar.addWidget(self.zone_hint_label, stretch=1)

        remove_zone_button = QPushButton("Удалить зону")
        remove_zone_button.clicked.connect(self.remove_selected_zone)
        save_zone_button = QPushButton("Сохранить зону")
        save_zone_button.clicked.connect(self.save_selected_zone)
        toolbar.addWidget(remove_zone_button)
        toolbar.addWidget(save_zone_button)
        layout.addLayout(toolbar)

        body_splitter = QSplitter(Qt.Vertical)
        layout.addWidget(body_splitter, stretch=1)

        body_splitter.addWidget(self.build_zone_tree_card())
        body_splitter.addWidget(self.build_zone_editor_card())
        body_splitter.setStretchFactor(0, 1)
        body_splitter.setStretchFactor(1, 2)
        return tab

    def build_zone_tree_card(self):
        group = QGroupBox("Список зон")
        layout = QVBoxLayout(group)

        self.zone_tree = QTreeWidget()
        self.zone_tree.setColumnCount(4)
        self.zone_tree.setHeaderLabels(["№", "Координаты", "Действие", "Фраз"])
        self.zone_tree.setRootIsDecorated(False)
        self.zone_tree.setAlternatingRowColors(True)
        self.zone_tree.currentItemChanged.connect(self.on_zone_selected)
        layout.addWidget(self.zone_tree)
        return group

    def build_zone_editor_card(self):
        group = QGroupBox("Редактор зоны")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        header_grid = QGridLayout()
        self.zone_coords_label = QLabel("Не выбрано")
        header_grid.addWidget(QLabel("Координаты"), 0, 0)
        header_grid.addWidget(self.zone_coords_label, 0, 1)

        self.keybind_combo = QComboBox()
        self.keybind_combo.addItems(KEY_OPTIONS)
        header_grid.addWidget(QLabel("Клавиша / действие"), 1, 0)
        header_grid.addWidget(self.keybind_combo, 1, 1)

        self.selected_phrase_combo = QComboBox()
        self.selected_phrase_combo.addItem("All")
        header_grid.addWidget(QLabel("Активная фраза"), 2, 0)
        header_grid.addWidget(self.selected_phrase_combo, 2, 1)
        layout.addLayout(header_grid)

        timings_group = QGroupBox("Тайминги и удержание")
        timings_grid = QGridLayout(timings_group)

        self.zone_hold_checkbox = QCheckBox("Удерживать кнопку")
        self.zone_hold_duration_spin = QSpinBox()
        self.zone_hold_duration_spin.setRange(0, 600000)
        self.zone_delay_before_spin = QSpinBox()
        self.zone_delay_before_spin.setRange(0, 600000)
        self.zone_delay_after_spin = QSpinBox()
        self.zone_delay_after_spin.setRange(0, 600000)
        self.zone_hold_lmb_checkbox = QCheckBox("Дожимать ЛКМ")
        self.zone_hold_lmb_duration_spin = QSpinBox()
        self.zone_hold_lmb_duration_spin.setRange(0, 600000)

        timings_grid.addWidget(self.zone_hold_checkbox, 0, 0)
        timings_grid.addWidget(QLabel("Длительность, мс"), 0, 1)
        timings_grid.addWidget(self.zone_hold_duration_spin, 0, 2)
        timings_grid.addWidget(QLabel("Задержка до, мс"), 1, 0)
        timings_grid.addWidget(self.zone_delay_before_spin, 1, 1)
        timings_grid.addWidget(QLabel("Задержка после, мс"), 1, 2)
        timings_grid.addWidget(self.zone_delay_after_spin, 1, 3)
        timings_grid.addWidget(self.zone_hold_lmb_checkbox, 2, 0)
        timings_grid.addWidget(QLabel("ЛКМ, мс"), 2, 1)
        timings_grid.addWidget(self.zone_hold_lmb_duration_spin, 2, 2)
        layout.addWidget(timings_group)

        phrases_group = QGroupBox("Фразы")
        phrases_layout = QVBoxLayout(phrases_group)
        self.phrases_list = QListWidget()
        phrases_layout.addWidget(self.phrases_list, stretch=1)

        phrase_buttons = QHBoxLayout()
        add_phrase_button = QPushButton("Добавить фразу")
        add_phrase_button.clicked.connect(self.add_phrase)
        remove_phrase_button = QPushButton("Удалить фразу")
        remove_phrase_button.clicked.connect(self.remove_selected_phrase)
        phrase_buttons.addWidget(add_phrase_button)
        phrase_buttons.addWidget(remove_phrase_button)
        phrase_buttons.addStretch(1)
        phrases_layout.addLayout(phrase_buttons)
        layout.addWidget(phrases_group, stretch=1)
        return group

    def build_telegram_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        group = QGroupBox("Уведомления")
        form = QFormLayout(group)

        self.telegram_checkbox = QCheckBox("Включить Telegram-бота")
        self.telegram_checkbox.setChecked(self.config_data.get("telegram_enabled", False))
        self.telegram_checkbox.stateChanged.connect(self.toggle_telegram_inputs)
        self.telegram_checkbox.stateChanged.connect(self.sync_runtime_state)

        self.telegram_bot_input = QLineEdit(self.config_data.get("telegram_bot_token", ""))
        self.telegram_bot_input.textChanged.connect(self.sync_runtime_state)
        self.telegram_chat_input = QLineEdit(self.config_data.get("telegram_chat_id", ""))
        self.telegram_chat_input.textChanged.connect(self.sync_runtime_state)

        self.telegram_connect_button = QPushButton("Подключить и проверить")
        self.telegram_connect_button.clicked.connect(self.apply_telegram_settings)

        hint = QLabel("Для уведомлений у зоны выберите действие TGBot. Проверка отправит сообщение 'connect'.")
        hint.setWordWrap(True)
        hint.setObjectName("mutedLabel")

        form.addRow(self.telegram_checkbox)
        form.addRow("Bot Token", self.telegram_bot_input)
        form.addRow("Chat ID", self.telegram_chat_input)
        form.addRow(self.telegram_connect_button)
        form.addRow(hint)

        layout.addWidget(group)
        layout.addStretch(1)
        return tab

    def sync_runtime_state(self, *_args):
        self.settings_state = {
            "selected_language": self.language_combo.currentText(),
            "recognition_threshold": self.threshold_spin.value(),
            "scan_delay": self.scan_delay_spin.value(),
            "selected_filter": self.filter_combo.currentText(),
            "anti_afk_delay": self.anti_afk_spin.value(),
            "telegram_bot_token": self.telegram_bot_input.text().strip(),
            "telegram_chat_id": self.telegram_chat_input.text().strip(),
            "telegram_enabled": self.telegram_checkbox.isChecked(),
            "always_on_top": self.always_on_top_checkbox.isChecked(),
            "anti_afk_enabled": self.anti_afk_checkbox.isChecked(),
            "bot_enabled": self.bot_enabled_checkbox.isChecked(),
            "frame_visible": self.frame_checkbox.isChecked(),
            "text_visible": self.text_checkbox.isChecked(),
            "show_all_text": self.show_all_checkbox.isChecked(),
        }

    def set_status(self, message):
        timestamped = f"{time.strftime('%H:%M:%S')} {message}"
        print(timestamped)
        self.bridge.status_message.emit(timestamped)

    def _apply_status(self, message):
        self.status_label.setText(message)

    def _apply_ocr_output(self, lines):
        if lines:
            self.ocr_output.setPlainText("\n".join(lines))
        else:
            self.ocr_output.setPlainText("OCR-монитор выключен.")

    def _on_tracking_finished(self):
        self.worker_thread = None
        self.frame_open = False

    def populate_zone_tree(self):
        current_selection = self.current_zone_index
        self.zone_tree.blockSignals(True)
        self.zone_tree.clear()

        for idx, zone in enumerate(self.zones):
            coords = ", ".join(map(str, zone.get("c", [])))
            keybind = zone.get("keybind", "a")
            phrase_count = str(len(zone.get("p", [])))
            item = QTreeWidgetItem([str(idx + 1), coords, str(keybind), phrase_count])
            item.setData(0, Qt.UserRole, idx)
            self.zone_tree.addTopLevelItem(item)

        self.zone_tree.blockSignals(False)

        if self.zones:
            target_index = current_selection if current_selection is not None and current_selection < len(self.zones) else 0
            item = self.zone_tree.topLevelItem(target_index)
            if item is not None:
                self.zone_tree.setCurrentItem(item)
                self.load_zone_into_editor(target_index)
        else:
            self.current_zone_index = None
            self.zone_coords_label.setText("Не выбрано")
            self.zone_hint_label.setText("Сначала создайте хотя бы одну зону.")
            self.clear_zone_editor()

    def clear_zone_editor(self):
        self.keybind_combo.setCurrentText(KEY_OPTIONS[0])
        self.zone_hold_checkbox.setChecked(False)
        self.zone_hold_duration_spin.setValue(0)
        self.zone_delay_before_spin.setValue(0)
        self.zone_delay_after_spin.setValue(self.scan_delay_spin.value())
        self.zone_hold_lmb_checkbox.setChecked(False)
        self.zone_hold_lmb_duration_spin.setValue(0)
        self.selected_phrase_combo.clear()
        self.selected_phrase_combo.addItem("All")
        self.phrases_list.clear()

    def on_zone_selected(self, current, _previous):
        if current is None:
            return
        zone_index = current.data(0, Qt.UserRole)
        if zone_index is not None:
            self.load_zone_into_editor(int(zone_index))

    def load_zone_into_editor(self, index):
        if index < 0 or index >= len(self.zones):
            self.clear_zone_editor()
            return

        zone = self.zones[index]
        self.current_zone_index = index
        self.zone_hint_label.setText(f"Редактируется зона #{index + 1}.")
        self.zone_coords_label.setText(", ".join(map(str, zone.get("c", []))) or "Не задано")
        self.keybind_combo.setCurrentText(zone.get("keybind", "a"))
        self.zone_hold_checkbox.setChecked(zone.get("hold", False))
        self.zone_hold_duration_spin.setValue(self.parse_int(zone.get("hold_duration", 0)))
        self.zone_delay_before_spin.setValue(self.parse_int(zone.get("delay_before", 0)))
        self.zone_delay_after_spin.setValue(self.parse_int(zone.get("delay_after", self.scan_delay_spin.value()), self.scan_delay_spin.value()))
        self.zone_hold_lmb_checkbox.setChecked(zone.get("hold_lmb", False))
        self.zone_hold_lmb_duration_spin.setValue(self.parse_int(zone.get("hold_lmb_duration", 0)))

        phrases = zone.get("p", [])
        phrase_values = ["All"] + phrases
        self.selected_phrase_combo.clear()
        self.selected_phrase_combo.addItems(phrase_values)
        selected_phrase = zone.get("selected_phrase", "All")
        self.selected_phrase_combo.setCurrentText(selected_phrase if selected_phrase in phrase_values else "All")

        self.phrases_list.clear()
        self.phrases_list.addItems(phrases)

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

        selected_phrase = self.selected_phrase_combo.currentText() or "All"
        zone["keybind"] = self.keybind_combo.currentText() or "a"
        zone["hold"] = self.zone_hold_checkbox.isChecked()
        zone["hold_duration"] = self.zone_hold_duration_spin.value()
        zone["delay_before"] = self.zone_delay_before_spin.value()
        zone["delay_after"] = self.zone_delay_after_spin.value()
        zone["hold_lmb"] = self.zone_hold_lmb_checkbox.isChecked()
        zone["hold_lmb_duration"] = self.zone_hold_lmb_duration_spin.value()
        zone["selected_phrase"] = selected_phrase
        return zone

    def save_selected_zone(self):
        zone = self.collect_zone_from_editor()
        if zone is None:
            QMessageBox.information(self, "Зоны", "Выберите зону для сохранения.")
            return

        self.zones[self.current_zone_index] = zone
        self.persist_current_state()
        self.populate_zone_tree()
        self.set_status(f"Зона #{self.current_zone_index + 1} сохранена.")

    def persist_current_state(self):
        self.sync_runtime_state()
        self.config_data["zones"] = copy.deepcopy(self.zones)
        self.config_data.update(self.settings_state)
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
        self.filter_combo.setCurrentText(self.config_data.get("selected_filter", FILTER_OPTIONS[0]))
        self.language_combo.setCurrentText(self.config_data.get("selected_language", "rus"))
        self.scan_delay_spin.setValue(self.config_data.get("scan_delay", 500))
        self.threshold_spin.setValue(self.config_data.get("recognition_threshold", 40))
        self.anti_afk_spin.setValue(self.config_data.get("anti_afk_delay", 10))
        self.telegram_bot_input.setText(self.config_data.get("telegram_bot_token", ""))
        self.telegram_chat_input.setText(self.config_data.get("telegram_chat_id", ""))
        self.telegram_checkbox.setChecked(self.config_data.get("telegram_enabled", False))
        self.always_on_top_checkbox.setChecked(self.config_data.get("always_on_top", False))
        self.anti_afk_checkbox.setChecked(self.config_data.get("anti_afk_enabled", False))
        self.bot_enabled_checkbox.setChecked(self.config_data.get("bot_enabled", False))
        self.frame_checkbox.setChecked(self.config_data.get("frame_visible", False))
        self.text_checkbox.setChecked(self.config_data.get("text_visible", False))
        self.show_all_checkbox.setChecked(self.config_data.get("show_all_text", False))
        self.sync_runtime_state()
        self.populate_zone_tree()
        self.toggle_telegram_inputs()

    def add_zone(self):
        self.save_all_settings()
        zones_saved = start_zone_creation(
            str(CONFIG_PATH),
            callback=self.reload_config_from_disk,
            ui_text={
                "window_title": "Выделение зон",
                "save_button": "Сохранить зоны",
                "clear_button": "Очистить",
            },
        )
        if zones_saved:
            self.set_status("Зоны обновлены.")
        else:
            self.set_status("Создание зон отменено.")

    def remove_selected_zone(self):
        if self.current_zone_index is None:
            QMessageBox.information(self, "Зоны", "Сначала выберите зону.")
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
            QMessageBox.information(self, "Фразы", "Сначала выберите зону.")
            return

        phrase, accepted = QInputDialog.getText(self, "Новая фраза", "Введите фразу для отслеживания:")
        if not accepted:
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
            QMessageBox.information(self, "Фразы", "Сначала выберите зону.")
            return

        item = self.phrases_list.currentItem()
        if item is None:
            QMessageBox.information(self, "Фразы", "Выберите фразу из списка.")
            return

        phrase = item.text()
        phrases = zone.get("p", [])
        if phrase in phrases:
            phrases.remove(phrase)
            if self.selected_phrase_combo.currentText() == phrase:
                self.selected_phrase_combo.setCurrentText("All")
            self.load_zone_into_editor(self.current_zone_index)
            self.set_status(f"Фраза удалена из зоны #{self.current_zone_index + 1}.")

    def apply_always_on_top(self, *_args):
        self.sync_runtime_state()
        was_visible = self.isVisible()
        self.setWindowFlag(Qt.WindowStaysOnTopHint, self.always_on_top_checkbox.isChecked())
        if was_visible:
            self.show()
        if self.frame_open:
            cv2.setWindowProperty("Frame", cv2.WND_PROP_TOPMOST, 1 if self.settings_state.get("always_on_top") else 0)

    def toggle_telegram_inputs(self, *_args):
        enabled = self.telegram_checkbox.isChecked()
        self.telegram_bot_input.setEnabled(enabled)
        self.telegram_chat_input.setEnabled(enabled)
        self.telegram_connect_button.setEnabled(enabled)
        if not enabled:
            self.bot = None
        self.sync_runtime_state()

    def apply_telegram_settings(self):
        if not self.telegram_checkbox.isChecked():
            self.bot = None
            self.set_status("Telegram-бот отключён.")
            return True

        if telebot is None:
            QMessageBox.critical(self, "Telegram", "Пакет pyTelegramBotAPI не установлен.")
            return False

        bot_token = self.telegram_bot_input.text().strip()
        chat_id = self.telegram_chat_input.text().strip()
        if not bot_token or not chat_id:
            QMessageBox.critical(self, "Telegram", "Заполните Bot Token и Chat ID.")
            return False

        try:
            self.bot = telebot.TeleBot(bot_token)
            self.bot.send_message(chat_id, "connect")
            self.set_status("Telegram-бот подключён и проверен.")
            self.persist_current_state()
            return True
        except Exception as exc:
            self.bot = None
            QMessageBox.critical(self, "Telegram", f"Не удалось подключить Telegram-бота:\n{exc}")
            self.set_status(f"Ошибка Telegram: {exc}")
            return False

    def validate_ocr_setup(self):
        try:
            self.ensure_ocr_ready(show_success=True)
            return True
        except RuntimeError as exc:
            QMessageBox.critical(self, "OCR", str(exc))
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

        required_language = self.settings_state.get("selected_language", self.language_combo.currentText())
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
            QMessageBox.warning(self, "Старт", "Сначала создайте хотя бы одну зону.")
            return

        if not self.validate_ocr_setup():
            return

        if self.telegram_checkbox.isChecked() and not self.apply_telegram_settings():
            return

        self.save_all_settings()
        self.stop_event.clear()
        self.last_action_time = time.time()
        self.worker_thread = threading.Thread(target=self.run_tracking_loop, daemon=True)
        self.worker_thread.start()
        self.set_status("Отслеживание запущено.")

    def find_match(self, phrases, recognized_text_psm6, recognized_text_psm7):
        threshold = self.settings_state.get("recognition_threshold", 40)

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
        if self.settings_state.get("show_all_text"):
            return f"Зона {zone_number}: {ocr_result_psm6.strip()} | {ocr_result_psm7.strip()}"
        return f"Зона {zone_number}: {matched_text}"

    def update_ocr_output(self, lines):
        self.bridge.ocr_output.emit(lines)

    def run_tracking_loop(self):
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                while not self.stop_event.is_set():
                    frame = np.array(sct.grab(monitor))
                    frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2RGB)

                    display_frame = apply_filter(frame.copy(), self.settings_state.get("selected_filter", FILTER_OPTIONS[0]))
                    if len(display_frame.shape) == 2:
                        preview_frame = cv2.cvtColor(display_frame, cv2.COLOR_GRAY2RGB)
                    else:
                        preview_frame = display_frame

                    small_frame = cv2.resize(preview_frame, (self.frame_width, self.frame_height))
                    scale_x = self.frame_width / self.original_width
                    scale_y = self.frame_height / self.original_height
                    draw_areas_on_frame(small_frame, self.runtime_zones, scale_x, scale_y)

                    if self.settings_state.get("frame_visible"):
                        cv2.imshow("Frame", small_frame)
                        self.frame_open = True
                        cv2.setWindowProperty("Frame", cv2.WND_PROP_TOPMOST, 1 if self.settings_state.get("always_on_top") else 0)
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

                        zone_frame_filtered = apply_filter(zone_frame, self.settings_state.get("selected_filter", FILTER_OPTIONS[0]))
                        ocr_lang = self.settings_state.get("selected_language", "rus")
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

                        if matched_text == "-" or not self.settings_state.get("bot_enabled"):
                            continue

                        press_delay = self.parse_int(
                            zone_data.get("press_delay", self.settings_state.get("scan_delay", 500)),
                            self.settings_state.get("scan_delay", 500),
                        ) / 1000.0
                        zone_last_press_time = self.last_press_time[idx]
                        last_press = zone_last_press_time.get(matched_text, 0)
                        if current_time - last_press < press_delay or self.action_in_progress.is_set():
                            continue

                        zone_last_press_time[matched_text] = current_time
                        self.last_action_time = current_time

                        if zone_data.get("keybind") == "TGBot":
                            if self.settings_state.get("telegram_enabled") and self.bot:
                                message = f"Найдена '{matched_text}' в зоне {idx + 1}"
                                try:
                                    self.bot.send_message(self.settings_state.get("telegram_chat_id", ""), message)
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

                    if self.settings_state.get("text_visible"):
                        self.update_ocr_output(ocr_lines)
                    else:
                        self.update_ocr_output([])

                    anti_afk_delay = max(1, self.settings_state.get("anti_afk_delay", 10))
                    if self.settings_state.get("anti_afk_enabled") and (current_time - self.last_action_time > anti_afk_delay):
                        pyautogui.click()
                        self.last_action_time = current_time
                        self.set_status(f"Anti afk: выполнен клик после {anti_afk_delay} секунд бездействия.")

                    if cv2.waitKey(1) == ord("q"):
                        self.bridge.stop_requested.emit()
                        break
        except Exception as exc:
            self.set_status(f"Ошибка отслеживания: {exc}")
        finally:
            self.frame_open = False
            cv2.destroyAllWindows()
            self.bridge.tracking_finished.emit()

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

    def closeEvent(self, event):
        self.stop_tracking()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1)
        cv2.destroyAllWindows()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    window = FishBotApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
