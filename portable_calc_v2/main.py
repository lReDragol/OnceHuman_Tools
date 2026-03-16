import json
import os
import sys
from pathlib import Path

import dearpygui.dearpygui as dpg


def get_runtime_root():
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parents[1]


RUNTIME_ROOT = get_runtime_root()
os.chdir(RUNTIME_ROOT)
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from config import Config
from data.menu.calc_and_mod_tab import CalcAndModTab


class PortableCalcApp:
    def __init__(self):
        self.translations = self.load_translations()
        self.current_language = self.load_language()
        self.default_font_tag = "PortableCalcDefaultFont"

        dpg.create_context()
        self.load_font()

        title = self.translations.get(self.current_language, {}).get("calc_and_mod_tab", {}).get("title", "Calculator")
        dpg.create_viewport(title=f"Once Human {title} V2", width=1200, height=820, resizable=True)
        dpg.setup_dearpygui()

        with dpg.window(label=title, tag="PortableCalcWindow", width=1180, height=790):
            self.calc_tab = CalcAndModTab(self)

        dpg.show_viewport()
        dpg.set_primary_window("PortableCalcWindow", True)

        while dpg.is_dearpygui_running():
            self.calc_tab.update()
            dpg.render_dearpygui_frame()

        dpg.destroy_context()

    def load_translations(self):
        translations_path = RUNTIME_ROOT / "translations.json"
        if translations_path.exists():
            with translations_path.open("r", encoding="utf-8") as file:
                return json.load(file)
        return {}

    def load_language(self):
        try:
            language = Config.from_json().language
        except Exception:
            language = "ru"
        return language if language in self.translations else "ru"

    def load_font(self):
        font_path = RUNTIME_ROOT / "data" / "file" / "ru.ttf"
        if not font_path.exists():
            return
        with dpg.font_registry():
            with dpg.font(str(font_path), 13, default_font=True, tag=self.default_font_tag):
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Cyrillic)
        dpg.bind_font(self.default_font_tag)


if __name__ == "__main__":
    PortableCalcApp()
