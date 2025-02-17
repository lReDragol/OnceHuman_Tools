# main.py

import dearpygui.dearpygui as dpg
from gui import GUI
from player import Player
from context_module import Context


def main():
    dpg.create_context()    
    dpg.create_viewport(title='Редактор и Калькулятор', width=1215, height=860)

    player = Player()  # Создаем игрока без передачи контекста
    context = Context(player)  # Создаем контекст, передавая игрока
    player.set_context(context)  # Устанавливаем контекст в игроке после создания
    gui = GUI(player, context)

    gui.setup()
    dpg.setup_dearpygui()
    dpg.show_viewport()
    gui.initialize()

    while dpg.is_dearpygui_running():
        gui.update()
        dpg.render_dearpygui_frame()

    dpg.destroy_context()


if __name__ == "__main__":
    main()
