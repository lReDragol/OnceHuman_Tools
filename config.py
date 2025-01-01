import json
import os

temp_folder = os.getenv('TEMP') or os.path.expanduser("~\\AppData\\Local\\Temp")
temp_folder = os.path.join(temp_folder, 'Temp_Once_Human_Change')
user_data = os.path.join(temp_folder, 'user_data.json')


class Config:
    def __init__(self):
        self.language = "en"
        self.monitoring = False
        self.always_on_top = False
        self.console_log = False

        # Устанавливаем temp_folder с резервным значением
        self.temp_folder = temp_folder
        self.game_path = ""
        self.last_midi_file = ""

        # Остальные параметры
        self.foto_video_tab = {
            "drag_click_enabled": False,
            "no_prop_enabled": False
        }
        self.piano_bot_tab = {
            "repeat_song": False,
            "merge_octave": False,
            "skip_octave": False,
            "tempo": 0,
            "modifier_delay": 0
        }
        self.other_tab = {
            "drag_click": False,
            "no_prop": False,
            "disk_read_limit": 100
        }
        self.bindings = {
            "drag_click_key": None,
            "piano_hotkey_play": "F5",
            "piano_hotkey_stop": "F6"
        }
        self.fish_bot = {
            "fish_zones": [],
            "auto_fishing_enabled": False,
            "frame_visible": False,
            "mask_visible": False,
            "frame_open": False,
            "mask_open": [False, False, False],
            "bot_enabled": False,
            "mask_sensitivity": 40,
            "cooldown_zones": {"1": 0, "3": 0},
            "zone_2_holding": False
        }
        self.theme = {
            "theme_color": "orange",
            "theme_mode": "system"
        }
        self.monitoring_process = "ONCE_HUMAN.exe"
        self.bot_fish_tab = {
            'bot_enabled': False,
            'frame_visible': False,
            'text_visible': False,
            'show_all_text': False,
            'selected_filter_value': "Нет фильтра",
            'scan_delay_var': 500,
            'recognition_threshold_var': 40,
            'selected_language': 'rus',
            'telegram_bot_token': '',
            'telegram_chat_id': '',
            'anti_afk_enabled': False,
            'anti_afk_delay_var': 10,
            'always_on_top_var': False,
            'telegram_bot_var': False,
            'zones': []
        }

    @staticmethod
    def from_json():
        conf_obj = Config()
        # Проверка и создание temp_folder, если значение пустое
        if not conf_obj.temp_folder:
            conf_obj.temp_folder = os.path.join(os.getenv('TEMP') or os.path.expanduser("~\\AppData\\Local\\Temp"),
                                                'Temp_Once_Human_Change')

        os.makedirs(conf_obj.temp_folder, exist_ok=True)

        if os.path.isfile(user_data):
            try:
                with open(user_data, "r", encoding="utf-8") as file:
                    data = json.load(file)
                for name, value in data.items():
                    setattr(conf_obj, name, value)
                # Повторная проверка, если temp_folder все еще пуст
                if not conf_obj.temp_folder:
                    conf_obj.temp_folder = temp_folder
                print(f"Configuration loaded from {user_data}")
            except (json.JSONDecodeError, OSError):
                print("Error loading configuration, creating a new configuration.")
                conf_obj.set_default_json()
        else:
            print("Configuration file not found, creating a new configuration.")
            conf_obj.set_default_json()
        return conf_obj

    def set_default_json(self):
        os.makedirs(self.temp_folder, exist_ok=True)
        data = self.__dict__
        with open(user_data, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        print(f"Configuration saved to {user_data}")

    def save_to_json(self):
        # Проверка на случай, если temp_folder пуст перед сохранением
        if not self.temp_folder:
            self.temp_folder = os.path.join(os.getenv('TEMP') or os.path.expanduser("~\\AppData\\Local\\Temp"),
                                            'Temp_Once_Human_Change')
        os.makedirs(self.temp_folder, exist_ok=True)

        data = {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
        with open(user_data, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        print(f"Configuration saved to {user_data}")
