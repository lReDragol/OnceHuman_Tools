import json
import dearpygui.dearpygui as dpg
import os

# Функция для загрузки существующих модов из файла
def load_mods():
    try:
        with open('items_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Функция для сохранения модов в файл
def save_mods(mods):
    with open('items_config.json', 'w', encoding='utf-8') as f:
        json.dump(mods, f, ensure_ascii=False, indent=2)

# Инициализация данных
mods_data = load_mods()

# Переменные для хранения текущего состояния
current_mod = {}
stats_stack = []

# Список категорий (изначально пустой или загруженный из модов)
categories = set()
for mod in mods_data.get('mod_weapon', []):
    categories.add(mod.get('category', 'None'))
categories = list(categories)

# Предопределенные имена параметров и их описания
parameter_names = {
    "damage": "Урон, наносимый модом",
    "range": "Дальность действия модификатора",
    "weight": "Вес модификатора",
    # Добавьте другие параметры по мере необходимости
}

# Предопределенные значения параметров и их описания
parameter_values = {
    "low": "Низкое значение",
    "medium": "Среднее значение",
    "high": "Высокое значение",
    # Добавьте другие значения по мере необходимости
}

dpg.create_context()

default_font = None
with dpg.font_registry():
    font_path = "C:\\Windows\\Fonts\\arial.ttf"
    if os.path.exists(font_path):
        with dpg.font(font_path, 15) as default_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Cyrillic)
    else:
        print("Шрифт Arial не найден. Используется шрифт по умолчанию.")

def add_category(sender, app_data, user_data):
    dpg.configure_item("add_category_window", show=True)

def save_new_category(sender, app_data, user_data):
    new_category = dpg.get_value("new_category_input").strip()
    if new_category and new_category not in categories:
        categories.append(new_category)
        dpg.configure_item("mod_category", items=categories)
        dpg.set_value("new_category_input", "")
        dpg.configure_item("add_category_window", show=False)
    else:
        dpg.configure_item("error_modal_category", show=True)

def add_stat(sender, app_data, user_data):
    key = dpg.get_value("stat_key").strip()
    value = dpg.get_value("stat_value").strip()

    if key and value != '':
        # Получаем реальные значения из словарей
        key_actual = parameter_names.get(key, key)
        value_actual = parameter_values.get(value, value)

        try:
            # Попытка преобразовать значение в число, список, словарь или логическое значение
            value_actual = json.loads(value_actual)
        except json.JSONDecodeError:
            pass  # Оставляем как строку

        stats_stack[-1][key_actual] = value_actual
        update_stats_preview()
        dpg.set_value("stat_key", "")
        dpg.set_value("stat_value", "")
    else:
        dpg.configure_item("error_modal", show=True)

def update_stats_preview():
    dpg.set_value("stats_preview", json.dumps(current_mod['stats'], ensure_ascii=False, indent=2))

def begin_nested_stat(sender, app_data, user_data):
    key = dpg.get_value("stat_key").strip()
    if key:
        new_dict = {}
        stats_stack[-1][key] = new_dict
        stats_stack.append(new_dict)
        update_stats_preview()
        dpg.set_value("stat_key", "")
    else:
        dpg.configure_item("error_modal_key", show=True)

def end_nested_stat(sender, app_data, user_data):
    if len(stats_stack) > 1:
        stats_stack.pop()
        update_stats_preview()
    else:
        dpg.configure_item("error_modal_end", show=True)

def create_mod(sender, app_data, user_data):
    name = dpg.get_value("mod_name").strip()
    category = dpg.get_value("mod_category").strip()

    if name:
        current_mod['name'] = name
        if category:
            current_mod['category'] = category
        else:
            current_mod['category'] = "None"
        if 'mod_weapon' not in mods_data:
            mods_data['mod_weapon'] = []
        mods_data['mod_weapon'].append(current_mod.copy())
        save_mods(mods_data)
        dpg.configure_item("status_text", default_value="Модификатор успешно сохранен!", color=[0, 255, 0])
        # Сброс полей
        dpg.set_value("mod_name", "")
        dpg.set_value("mod_category", "")
        current_mod['stats'] = {}
        stats_stack.clear()
        stats_stack.append(current_mod['stats'])
        update_stats_preview()
    else:
        dpg.configure_item("error_modal_name", show=True)

def reset_form(sender, app_data, user_data):
    dpg.set_value("mod_name", "")
    dpg.set_value("mod_category", "")
    dpg.set_value("stat_key", "")
    dpg.set_value("stat_value", "")
    current_mod['stats'] = {}
    stats_stack.clear()
    stats_stack.append(current_mod['stats'])
    update_stats_preview()
    dpg.configure_item("status_text", default_value="", color=[0, 0, 0])

def edit_mods(sender, app_data, user_data):
    # Очищаем предыдущий список
    dpg.delete_item("mods_list", children_only=True)

    # Создаем структуру модов по категориям
    mods_by_category = {}
    for mod in mods_data.get('mod_weapon', []):
        category = mod.get('category', 'None')
        if category not in mods_by_category:
            mods_by_category[category] = []
        mods_by_category[category].append(mod)

    for category, mods in mods_by_category.items():
        dpg.add_text(f"Категория: {category}", parent="mods_list")
        for mod in mods:
            mod_name = mod['name']
            dpg.add_button(label=mod_name, parent="mods_list", callback=select_mod, user_data=mod)
        dpg.add_separator(parent="mods_list")

    dpg.configure_item("edit_mods_window", show=True)

def select_mod(sender, app_data, user_data):
    mod = user_data
    # Заполняем поля данными выбранного мода
    dpg.set_value("mod_name", mod.get('name', ''))
    dpg.set_value("mod_category", mod.get('category', ''))
    current_mod.clear()
    current_mod.update(mod)
    stats_stack.clear()
    stats_stack.append(current_mod['stats'])
    update_stats_preview()
    dpg.configure_item("edit_mods_window", show=False)

def add_parameter_name(sender, app_data, user_data):
    dpg.configure_item("add_parameter_name_window", show=True)

def save_new_parameter_name(sender, app_data, user_data):
    new_param = dpg.get_value("new_parameter_name_input").strip()
    description = dpg.get_value("new_parameter_name_description").strip()
    if new_param:
        parameter_names[new_param] = description
        dpg.configure_item("stat_key", items=list(parameter_names.keys()))
        dpg.set_value("new_parameter_name_input", "")
        dpg.set_value("new_parameter_name_description", "")
        dpg.configure_item("add_parameter_name_window", show=False)
    else:
        dpg.configure_item("error_modal_parameter_name", show=True)

def add_parameter_value(sender, app_data, user_data):
    dpg.configure_item("add_parameter_value_window", show=True)

def save_new_parameter_value(sender, app_data, user_data):
    new_value = dpg.get_value("new_parameter_value_input").strip()
    description = dpg.get_value("new_parameter_value_description").strip()
    if new_value:
        parameter_values[new_value] = description
        dpg.configure_item("stat_value", items=list(parameter_values.keys()))
        dpg.set_value("new_parameter_value_input", "")
        dpg.set_value("new_parameter_value_description", "")
        dpg.configure_item("add_parameter_value_window", show=False)
    else:
        dpg.configure_item("error_modal_parameter_value", show=True)

def show_tooltip(sender, app_data, user_data):
    item = dpg.get_item_label(sender)
    description = user_data.get(item, "Нет описания")
    with dpg.tooltip(sender):
        dpg.add_text(description)

# Настройка главного окна
dpg.create_viewport(title='Редактор Модификаторов', width=800, height=700)

with dpg.window(label="Создание Модификатора", width=800, height=700):
    dpg.add_text("Введите информацию о модификаторе:", color=[255, 255, 0])

    # Поле выбора категории с возможностью добавить новую
    with dpg.group(horizontal=True):
        dpg.add_combo(categories, label="Категория модификатора", tag="mod_category")
        dpg.add_button(label="+", width=30, callback=add_category)

    # Поле ввода названия модификатора
    dpg.add_input_text(label="Название модификатора", tag="mod_name")

    dpg.add_separator()
    dpg.add_text("Добавьте параметры модификатора:", color=[255, 255, 0])

    # Поле выбора имени параметра с возможностью добавить новое
    with dpg.group(horizontal=True):
        dpg.add_combo(list(parameter_names.keys()), label="Имя параметра", tag="stat_key")
        dpg.add_button(label="+", width=30, callback=add_parameter_name)

    # Поле выбора значения параметра с возможностью добавить новое
    with dpg.group(horizontal=True):
        dpg.add_combo(list(parameter_values.keys()), label="Значение параметра", tag="stat_value")
        dpg.add_button(label="+", width=30, callback=add_parameter_value)

    # Добавление пояснений при наведении на элементы списка
    for item in dpg.get_item_children("stat_key", 1)[1]:
        dpg.set_item_callback(item, show_tooltip, user_data=parameter_names)
    for item in dpg.get_item_children("stat_value", 1)[1]:
        dpg.set_item_callback(item, show_tooltip, user_data=parameter_values)

    with dpg.group(horizontal=True):
        dpg.add_button(label="Добавить параметр", callback=add_stat)
        dpg.add_button(label="Начать вложенный параметр", callback=begin_nested_stat)
        dpg.add_button(label="Завершить вложенный параметр", callback=end_nested_stat)
    dpg.add_separator()
    dpg.add_text("Предпросмотр stats:", color=[255, 255, 0])
    dpg.add_input_text(multiline=True, readonly=True, width=780, height=200, tag="stats_preview")
    with dpg.group(horizontal=True):
        dpg.add_button(label="Сохранить модификатор", callback=create_mod)
        dpg.add_button(label="Сбросить форму", callback=reset_form)
        dpg.add_button(label="Изменить моды", callback=edit_mods)
    dpg.add_text("", tag="status_text")

    # Окно добавления новой категории
    with dpg.window(label="Добавить новую категорию", modal=True, show=False, tag="add_category_window"):
        dpg.add_input_text(label="Название новой категории", tag="new_category_input")
        dpg.add_button(label="Сохранить", callback=save_new_category)
        dpg.add_button(label="Отмена", callback=lambda: dpg.configure_item("add_category_window", show=False))

    # Окно добавления нового имени параметра
    with dpg.window(label="Добавить новое имя параметра", modal=True, show=False, tag="add_parameter_name_window"):
        dpg.add_input_text(label="Имя параметра", tag="new_parameter_name_input")
        dpg.add_input_text(label="Описание параметра", tag="new_parameter_name_description")
        dpg.add_button(label="Сохранить", callback=save_new_parameter_name)
        dpg.add_button(label="Отмена", callback=lambda: dpg.configure_item("add_parameter_name_window", show=False))

    # Окно добавления нового значения параметра
    with dpg.window(label="Добавить новое значение параметра", modal=True, show=False, tag="add_parameter_value_window"):
        dpg.add_input_text(label="Значение параметра", tag="new_parameter_value_input")
        dpg.add_input_text(label="Описание значения", tag="new_parameter_value_description")
        dpg.add_button(label="Сохранить", callback=save_new_parameter_value)
        dpg.add_button(label="Отмена", callback=lambda: dpg.configure_item("add_parameter_value_window", show=False))

    # Окно редактирования модов
    with dpg.window(label="Редактировать Моды", modal=True, show=False, tag="edit_mods_window", width=400, height=500):
        dpg.add_child_window(tag="mods_list", autosize_x=True, autosize_y=True)
        dpg.add_button(label="Закрыть", callback=lambda: dpg.configure_item("edit_mods_window", show=False))

    # Модальные окна ошибок
    with dpg.window(label="Ошибка", modal=True, show=False, tag="error_modal"):
        dpg.add_text("Пожалуйста, выберите имя и значение параметра.")
        dpg.add_button(label="ОК", callback=lambda: dpg.configure_item("error_modal", show=False))

    with dpg.window(label="Ошибка", modal=True, show=False, tag="error_modal_key"):
        dpg.add_text("Пожалуйста, введите имя параметра для вложенного уровня.")
        dpg.add_button(label="ОК", callback=lambda: dpg.configure_item("error_modal_key", show=False))

    with dpg.window(label="Ошибка", modal=True, show=False, tag="error_modal_end"):
        dpg.add_text("Нет вложенных параметров для завершения.")
        dpg.add_button(label="ОК", callback=lambda: dpg.configure_item("error_modal_end", show=False))

    with dpg.window(label="Ошибка", modal=True, show=False, tag="error_modal_name"):
        dpg.add_text("Пожалуйста, введите название модификатора.")
        dpg.add_button(label="ОК", callback=lambda: dpg.configure_item("error_modal_name", show=False))

    with dpg.window(label="Ошибка", modal=True, show=False, tag="error_modal_category"):
        dpg.add_text("Пожалуйста, введите уникальное название категории.")
        dpg.add_button(label="ОК", callback=lambda: dpg.configure_item("error_modal_category", show=False))

    with dpg.window(label="Ошибка", modal=True, show=False, tag="error_modal_parameter_name"):
        dpg.add_text("Пожалуйста, введите имя параметра.")
        dpg.add_button(label="ОК", callback=lambda: dpg.configure_item("error_modal_parameter_name", show=False))

    with dpg.window(label="Ошибка", modal=True, show=False, tag="error_modal_parameter_value"):
        dpg.add_text("Пожалуйста, введите значение параметра.")
        dpg.add_button(label="ОК", callback=lambda: dpg.configure_item("error_modal_parameter_value", show=False))

# Инициализация текущего модификатора
current_mod['stats'] = {}
stats_stack.append(current_mod['stats'])
update_stats_preview()

dpg.setup_dearpygui()
if default_font is not None:
    dpg.bind_font(default_font)
dpg.show_viewport()
dpg.start_dearpygui()
dpg.destroy_context()
