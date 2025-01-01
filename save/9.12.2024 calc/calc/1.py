import webbrowser
import dearpygui.dearpygui as dpg

# Глобальные переменные для хранения логина/пароля (можно и без них, через get_value)
login_input_tag = "login_input"
password_input_tag = "password_input"
login_popup_tag = "LoginPopup"
login_text_tag = "login_text"
pass_text_tag = "pass_text"

def login_callback(sender, app_data, user_data):
    # Получаем введённые данные из полей
    login_value = dpg.get_value(login_input_tag)
    password_value = dpg.get_value(password_input_tag)
    # Устанавливаем значения на текстовые поля в попапе
    dpg.set_value(login_text_tag, login_value)
    dpg.set_value(pass_text_tag, password_value)
    # Показываем попап окно
    dpg.show_item(login_popup_tag)

def renew_callback(sender, app_data, user_data):
    # Переход по ссылке на YouTube
    webbrowser.open("https://youtube.com")

dpg.create_context()

# Создаём вьюпорт (окно)
dpg.create_viewport(title="AMAZINGBOTS", width=500, height=400)
dpg.setup_dearpygui()

with dpg.window(label="", tag="Main Window", no_title_bar=True, no_move=True, no_resize=True, no_scrollbar=True):
    # Основное окно без заголовка
    # Позиционирование и текст
    main_w = 500
    main_h = 400
    login_box_width = 300
    login_box_height = 200
    x_pos = int((main_w - login_box_width) / 2)
    y_pos = int((main_h - login_box_height) / 2)

    # Текст о подписке
    dpg.add_text("Подписка+: до 29.11.2024", tag="sub_text")
    dpg.configure_item("sub_text", pos=(main_w - 200, 20))

    # Кнопка "Продлить"
    dpg.add_button(label="Продлить", tag="renew_button", callback=renew_callback)
    dpg.configure_item("renew_button", pos=(main_w - 100, 18))
    dpg.configure_item("renew_button", width=80)

    # Заголовок
    dpg.add_text("AMAZINGBOTS", tag="main_title")
    dpg.configure_item("main_title", pos=(x_pos, y_pos - 50))

    dpg.add_text("Введите ваши данные", tag="sub_title")
    dpg.configure_item("sub_title", pos=(x_pos, y_pos - 30))

    with dpg.child_window(label="LoginBox", tag="LoginBox", width=login_box_width, height=login_box_height):
        dpg.add_text("EMail / Username")
        dpg.add_input_text(tag=login_input_tag, default_value="Lyapos", width=250)
        dpg.add_spacer(height=10)

        dpg.add_text("Password")
        dpg.add_input_text(tag=password_input_tag, password=True, default_value="", width=250)
        dpg.add_spacer(height=10)

        dpg.add_text("Forgot Username/Password", color=[100, 150, 200])
        dpg.add_spacer(height=10)

        dpg.add_button(label="Log in", callback=login_callback)

    dpg.configure_item("LoginBox", pos=(x_pos, y_pos))

# Окно-попап для отображения данных после логина
with dpg.window(label="", tag=login_popup_tag, modal=True, no_title_bar=True, no_resize=True, no_move=True, show=False):
    dpg.add_text("Вы ввели следующие данные:")
    dpg.add_spacer(height=5)
    dpg.add_text("Логин: ")
    dpg.add_same_line()
    dpg.add_text("", tag=login_text_tag)

    dpg.add_text("Пароль: ")
    dpg.add_same_line()
    dpg.add_text("", tag=pass_text_tag)

    dpg.add_button(label="Закрыть", callback=lambda s,a,u: dpg.hide_item(login_popup_tag))

dpg.set_primary_window("Main Window", True)

dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
