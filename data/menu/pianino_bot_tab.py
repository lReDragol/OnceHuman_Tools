# data/menu/pianino_bot_tab.py

import dearpygui.dearpygui as dpg
import threading
import time
import json
import mido
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog
import keyboard
from .settings_button import SettingsButton

class PianinoBotTab:
    rus_to_eng = str.maketrans(
        "йцукенгшщзхъфывапролджэячсмитьбю",
        "qwertyuiop[]asdfghjkl;'zxcvbnm,."
    )

    def __init__(self, main_app):
        self.main_app = main_app
        self.trans = self.main_app.translations.get(self.main_app.current_language, {}).get("piano_bot_tab", {})

        self.selected_midi_path = ""
        self.is_playing = False
        self.tempo = getattr(self.main_app.config, 'tempo', 0)
        self.modifier_delay = getattr(self.main_app.config, 'modifier_delay', 0)
        self.repeat_song = getattr(self.main_app.config, 'repeat_song', False)
        self.skip_octave = getattr(self.main_app.config, 'skip_octave', False)
        self.merge_octave = getattr(self.main_app.config, 'merge_octave', False)

        self.midi_key_map = self.load_midi_key_map()
        self.piano_keys = {}

        self.current_modifiers = set()
        self.modifier_keys = {'ctrl', 'shift', 'alt'}

        self.currently_pressed_notes = set()

        self.lock = threading.Lock()

        with dpg.group(horizontal=False):
            with dpg.group(horizontal=True):
                self.create_midi_file_group()
            self.create_settings_group()
            self.create_information_group()
            self.create_piano()

            dpg.add_spacer(height=-1)

            with dpg.group(horizontal=True):
                dpg.add_spacer(width=-1)
                SettingsButton(self.main_app, parent=dpg.last_item())

        self.load_last_selected_midi()

        keyboard.add_hotkey('F5', self.hotkey_play_song)
        keyboard.add_hotkey('F6', self.hotkey_stop_song)

    def get_note_name(self, midi_key):
        note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        octave = (midi_key // 12) - 1
        note = note_names[midi_key % 12]
        return f"{note}{octave}"

    def load_midi_key_map(self):
        script_path = Path(__file__).resolve()
        json_path = script_path.parent.parent / 'file' / 'MidiKeyMap.json'

        midi_key_map = {}

        if json_path.exists():
            with open(json_path, 'r', encoding='utf-8') as file:
                try:
                    midi_key_map = json.load(file)
                except json.JSONDecodeError as e:
                    print(f"Error reading JSON file: {e}")
        else:
            print(f"File {json_path} not found.")

        return midi_key_map

    def create_midi_file_group(self):
        with dpg.group(horizontal=True):
            dpg.add_button(label=self.trans.get("load_midi", "Load MIDI"), callback=self.load_midi)
            dpg.add_spacer(width=10)
            dpg.add_button(label=self.trans.get("play_song", "Play"), callback=self.play_song)
            dpg.add_button(label=self.trans.get("stop_song", "Stop"), callback=self.stop_song)
            dpg.add_spacer(width=10)
            self.label_selected_midi = dpg.add_text(default_value="")

    def create_settings_group(self):
        with dpg.group():
            self.repeat_song_var = dpg.add_checkbox(label=self.trans.get("repeat_song", "Repeat Song"),
                                                    default_value=self.repeat_song,
                                                    callback=self.update_repeat_song)
            self.skip_octave_var = dpg.add_checkbox(label=self.trans.get("skip_octave", "Skip Octave 3 and 5"),
                                                    default_value=self.skip_octave,
                                                    callback=self.update_skip_octave)
            self.merge_octave_var = dpg.add_checkbox(label=self.trans.get("merge_octave", "Merge Octave 4"),
                                                     default_value=self.merge_octave,
                                                     callback=self.update_merge_octave)

            dpg.add_text(default_value=self.trans.get("speed", "Speed"))
            self.tempo_scale = dpg.add_slider_int(label="", min_value=-10, max_value=10, default_value=self.tempo,
                                                  callback=self.update_tempo)

            dpg.add_text(default_value=self.trans.get("modifier_delay", "Modifier Delay"))
            self.modifier_delay_scale = dpg.add_slider_int(label="", min_value=0, max_value=100,
                                                           default_value=self.modifier_delay,
                                                           callback=self.update_modifier_delay)

    def update_repeat_song(self, sender, app_data):
        self.repeat_song = app_data
        self.main_app.config.repeat_song = self.repeat_song
        self.main_app.config.save_to_json()

    def update_skip_octave(self, sender, app_data):
        with self.lock:
            self.skip_octave = app_data
        self.main_app.config.skip_octave = self.skip_octave
        self.main_app.config.save_to_json()

    def update_merge_octave(self, sender, app_data):
        with self.lock:
            self.merge_octave = app_data
        self.main_app.config.merge_octave = self.merge_octave
        self.main_app.config.save_to_json()

    def update_tempo(self, sender, app_data):
        self.tempo = app_data
        self.main_app.config.tempo = self.tempo
        self.main_app.config.save_to_json()

    def update_modifier_delay(self, sender, app_data):
        self.modifier_delay = app_data
        self.main_app.config.modifier_delay = self.modifier_delay
        self.main_app.config.save_to_json()

    def create_information_group(self):
        with dpg.group():
            dpg.add_text(default_value=self.trans.get("start_stop_midi", "Press F5 to Start and F6 to Stop the MIDI in game."))
            dpg.add_text(default_value=self.trans.get("stutter_warning", "A song with lots of Shift and Control presses will stutter. (Game Issue)"))
            dpg.add_text(default_value=self.trans.get("use_small_piano", "Use the small ingame piano."))

    def create_piano(self):
        white_key_width = 20
        white_key_height = 75
        black_key_width = 10
        black_key_height = 45

        num_white_keys = 21

        white_note_numbers = [0, 2, 4, 5, 7, 9, 11]
        black_note_numbers = [1, 3, 6, 8, 10]

        white_key_midi_notes = []
        black_key_positions = []
        black_key_midi_notes = []

        midi_note = 48  # Начинаем с ноты C4
        white_key_index = 0

        while len(white_key_midi_notes) < num_white_keys:
            note_in_octave = midi_note % 12
            if note_in_octave in white_note_numbers:
                white_key_midi_notes.append(midi_note)
                # Проверяем наличие черной клавиши (кроме после E и B)
                if note_in_octave != 4 and note_in_octave != 11:
                    black_midi_note = midi_note + 1
                    black_key_positions.append(white_key_index)
                    black_key_midi_notes.append(black_midi_note)
                white_key_index += 1
            midi_note += 1

        with dpg.group():
            with dpg.drawlist(width=num_white_keys * white_key_width + 20, height=white_key_height):
                # Рисуем белые клавиши
                for i, midi_key in enumerate(white_key_midi_notes):
                    x0 = i * white_key_width
                    x1 = x0 + white_key_width
                    key_tag = f"key_{midi_key}"
                    dpg.draw_rectangle((x0, 0), (x1, white_key_height), color=(0, 0, 0, 255),
                                       fill=(255, 255, 255, 255), thickness=1, tag=key_tag)
                    self.piano_keys[midi_key] = key_tag

                # Рисуем черные клавиши
                for i, (pos, midi_key) in enumerate(zip(black_key_positions, black_key_midi_notes)):
                    x0 = pos * white_key_width + white_key_width - black_key_width / 2
                    x1 = x0 + black_key_width
                    key_tag = f"key_{midi_key}"
                    dpg.draw_rectangle((x0, 0), (x1, black_key_height), color=(0, 0, 0, 255),
                                       fill=(0, 0, 0, 255), thickness=1, tag=key_tag)
                    self.piano_keys[midi_key] = key_tag

        self.black_keys_set = set(black_key_midi_notes)

    def load_midi(self):
        root = tk.Tk()
        root.withdraw()
        file_path = filedialog.askopenfilename(filetypes=[("MIDI files", "*.mid;*.midi")])
        if file_path and file_path.lower().endswith(('.mid', '.midi')):
            self.selected_midi_path = file_path
            file_name = os.path.basename(file_path)
            dpg.set_value(self.label_selected_midi, file_name)
            print(f"Selected MIDI File: {file_name}")

            self.main_app.config.last_midi_file = self.selected_midi_path
            self.main_app.config.save_to_json()
        else:
            print("Invalid file format. Please select a valid MIDI file.")

    def load_last_selected_midi(self):
        last_midi_file = getattr(self.main_app.config, 'last_midi_file', None)
        if last_midi_file and os.path.exists(last_midi_file):
            self.selected_midi_path = last_midi_file
            file_name = os.path.basename(last_midi_file)
            dpg.set_value(self.label_selected_midi, file_name)
            print(f"Loaded last selected MIDI File: {file_name}")
        else:
            if hasattr(self.main_app.config, 'last_midi_file'):
                del self.main_app.config.last_midi_file
                self.main_app.config.save_to_json()
            print("No valid MIDI file found or file does not exist.")

    def play_song(self):
        if not self.selected_midi_path:
            print("No MIDI file selected.")
            return

        if self.is_playing:
            print("A song is already playing. Please stop it first.")
            return

        self.is_playing = True
        self.midi_file = mido.MidiFile(self.selected_midi_path)

        # Применяем изменение темпа
        tempo_multiplier = 2 ** (self.tempo / 10)

        # Вычисляем реальные времена для сообщений
        for msg in self.midi_file:
            if not msg.is_meta:
                msg.time /= tempo_multiplier

        # Запускаем воспроизведение в отдельном потоке
        threading.Thread(target=self.play_song_thread).start()

    def stop_song(self):
        self.is_playing = False
        print("Song stopped.")
        # Сбрасываем подсветку всех нажатых клавиш
        for midi_key in self.currently_pressed_notes:
            self.highlight_key(midi_key, press=False)
        self.currently_pressed_notes.clear()
        # Отпускаем удерживаемые модификаторы
        for mod in self.current_modifiers.copy():
            self.release_key(mod)
            self.current_modifiers.remove(mod)

    def play_song_thread(self):
        self.currently_pressed_notes = set()
        for msg in self.midi_file:
            if not self.is_playing:
                break

            time.sleep(msg.time)

            if not msg.is_meta:
                if msg.type == 'note_on' and msg.velocity > 0:
                    self.process_note_on(msg)
                elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                    self.process_note_off(msg)

        if self.repeat_song and self.is_playing:
            self.play_song_thread()

    def process_note_on(self, msg):
        midi_key = msg.note

        with self.lock:
            merge_octave = self.merge_octave
            skip_octave = self.skip_octave

        if merge_octave:
            midi_key = self.merge_octave_function(midi_key)

        if skip_octave and self.is_skip_octave(midi_key):
            return

        if str(midi_key) in self.midi_key_map:
            key_combinations = self.midi_key_map[str(midi_key)]
            for key_combination in key_combinations:
                keys = key_combination.split('+')
                # Разделяем модификаторы и обычные клавиши
                modifiers = set(k.lower() for k in keys if k.lower() in self.modifier_keys)
                regular_keys = [k.lower() for k in keys if k.lower() not in self.modifier_keys]

                # Если функция Merge Octave 4 активна, игнорируем модификаторы
                with self.lock:
                    if self.merge_octave:
                        modifiers = set()

                # Обновляем состояние модификаторов
                self.update_modifiers(modifiers)

                # Нажимаем и отпускаем обычные клавиши
                for key in regular_keys:
                    self.press_key(key)
                    time.sleep(self.modifier_delay * 0.001)
                    self.release_key(key)

                self.highlight_key(midi_key, press=True)

            self.currently_pressed_notes.add(midi_key)

    def process_note_off(self, msg):
        midi_key = msg.note

        with self.lock:
            merge_octave = self.merge_octave
            skip_octave = self.skip_octave

        if merge_octave:
            midi_key = self.merge_octave_function(midi_key)

        if skip_octave and self.is_skip_octave(midi_key):
            return

        self.currently_pressed_notes.discard(midi_key)

        # Определяем, какие модификаторы требуются для оставшихся нот
        required_modifiers = self.get_required_modifiers_for_current_notes()

        # Обновляем состояние модификаторов
        self.update_modifiers(required_modifiers)

        self.highlight_key(midi_key, press=False)

    def update_modifiers(self, required_modifiers):
        # Нажимаем новые модификаторы
        new_modifiers = required_modifiers - self.current_modifiers
        for mod in new_modifiers:
            self.press_key(mod)
            self.current_modifiers.add(mod)
            print(f"Modifier pressed: {mod}")

        # Отпускаем модификаторы, которые больше не нужны
        old_modifiers = self.current_modifiers - required_modifiers
        for mod in old_modifiers:
            self.release_key(mod)
            self.current_modifiers.remove(mod)
            print(f"Modifier released: {mod}")

    def get_required_modifiers_for_current_notes(self):
        # Определяем модификаторы, требуемые для текущих нажатых нот
        required_modifiers = set()
        for midi_key in self.currently_pressed_notes:
            if str(midi_key) in self.midi_key_map:
                key_combinations = self.midi_key_map[str(midi_key)]
                for key_combination in key_combinations:
                    keys = key_combination.split('+')
                    modifiers = set(k.lower() for k in keys if k.lower() in self.modifier_keys)
                    # Если функция Merge Octave 4 активна, игнорируем модификаторы
                    with self.lock:
                        if self.merge_octave:
                            modifiers = set()
                    required_modifiers.update(modifiers)
        return required_modifiers

    def press_key(self, key):
        key = key.lower()
        keyboard.press(key)
        print(f"Key pressed: {key}")

    def release_key(self, key):
        key = key.lower()
        keyboard.release(key)
        print(f"Key released: {key}")

    def highlight_key(self, midi_key, press=True):
        if midi_key in self.piano_keys:
            key_tag = self.piano_keys[midi_key]
            if press:
                fill_color = (120,219,226, 255)
            else:
                if midi_key in self.black_keys_set:
                    fill_color = (0, 0, 0, 255)
                else:
                    fill_color = (255, 255, 255, 255)
            dpg.configure_item(key_tag, fill=fill_color)

    def merge_octave_function(self, midi_key):
        octave = (midi_key // 12) - 1
        if octave == 4:
            midi_key -= 12
        return midi_key

    def is_skip_octave(self, midi_key):
        octave = (midi_key // 12) - 1
        return octave in [3, 5]

    def hotkey_play_song(self):
        self.play_song()

    def hotkey_stop_song(self):
        self.stop_song()

    def restore_states(self):
        pass

    def save_states(self):
        pass

    def update_ui(self):
        print("UI updated with new translations.")

    def stop(self):
        print("Pianino stopped.")