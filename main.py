# main.py

import os
import sys


def bootstrap_runtime():
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    os.chdir(base_dir)
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)


bootstrap_runtime()

from main_menu import MainApp

if __name__ == "__main__":
    print("Starting application...")
    app = MainApp()
    print("Main application loop exited.")
