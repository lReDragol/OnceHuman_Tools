import json
import dearpygui.dearpygui as dpg
import os
import time
import random
import math

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

# Список категорий для создания модов
mod_categories = list({
    "Шлем",
    "Маска",
    "Нагрудник",
    "Перчатки",
    "Штаны"
})

# Обновим категории и создадим соответствие между категориями в интерфейсе и ключами в items_config.json
category_key_mapping = {
    "Шлем": "mod_helmet",
    "Маска": "mod_mask",
    "Нагрудник": "mod_top",
    "Перчатки": "mod_gloves",
    "Штаны": "mod_bottoms",
    "Ботинки": "mod_boots"
}

# Предопределенные имена параметров и их описания
parameter_names = {
    "damage": "Урон, наносимый модом",
    "range": "Дальность действия модификатора",
    "weight": "Вес модификатора",
    "bounce_can_hit_allies": "Рикошет может попасть по союзникам",
    "bounce_deals_no_dmg_to_allies": "Рикошет не наносит урон союзникам",
    "on_bounce_hit_ally": "При попадании рикошетом по союзнику",
    "refill_bullet": "Пополнить патрон",
    "on_trigger_unstable_bomber": "При срабатывании Unstable Bomber",
    "refill_magazine_percent": "Пополнить магазин на процент",
    "crit_rate_percent": "Шанс критического попадания %",
    "crit_dmg_percent": "Критический урон %",
    "fire_rate_percent": "Скорострельность %",
    "weapon_dmg_percent": "Урон оружия %",
    "status_dmg_percent": "Урон статуса %",
    "elemental_dmg_percent": "Элементальный урон %",
    "weakspot_dmg_percent": "Урон по слабым местам %",
    # Добавь другие параметры которых не хватает
}

# Предопределенные значения параметров и их описания
parameter_values = {
    "true": "Истина",
    "false": "Ложь",
    "1": "Единица",
    "10": "Десять",
    "25": "Двадцать пять",
    "50": "Пятьдесят",
    #Todo: Добавьте другие значения по мере необходимости
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

# Глобальные переменные для калькулятора
total_damage = 0
dps = 0
damage_history = []  # История нанесенного урона для расчета DPS
mouse_pressed = False
scheduled_deletions = []
current_ammo = 0  # Текущее количество патронов
reloading = False  # Флаг перезарядки
reload_end_time = 0  # Время окончания перезарядки
last_fire_time = time.time()
last_damage_time = time.time()
selected_mods_stats = {}  # Статы выбранных модов по категориям
# Дополнительные переменные для эффектов и статусов
mannequin_status_effects = {}
status_stack_counts = {"Fire": 0}  # Стак для огня
max_fire_stacks = 16  # Максимальное количество стаков огня

# Система событий
event_handlers = {
    "on_critical_hit": [],
    "on_trigger_unstable_bomber": [],
    # Добавьте другие события по мере необходимости
}

def add_category(sender, app_data, user_data):
    dpg.configure_item("add_category_window", show=True)

def save_new_category(sender, app_data, user_data):
    new_category = dpg.get_value("new_category_input").strip()
    if new_category and new_category not in mod_categories:
        mod_categories.append(new_category)
        dpg.configure_item("mod_category", items=mod_categories)
        dpg.set_value("new_category_input", "")
        dpg.configure_item("add_category_window", show=False)
    else:
        dpg.configure_item("error_modal_category", show=True)

def add_stat(sender, app_data, user_data):
    key = dpg.get_value("stat_key").strip()
    value = dpg.get_value("stat_value").strip()

    if key and value != '':
        try:
            # Попытка преобразовать значение в число, список, словарь или логическое значение
            value_actual = json.loads(value)
        except json.JSONDecodeError:
            # Оставляем как строку
            value_actual = value

        stats_stack[-1][key] = value_actual
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
        # Сохраняем мод в соответствующую категорию
        mod_key = category_key_mapping.get(category, 'mod_weapon')
        if mod_key not in mods_data:
            mods_data[mod_key] = []
        mods_data[mod_key].append(current_mod.copy())
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
    for category_display_name, mod_key in category_key_mapping.items():
        mods = mods_data.get(mod_key, [])
        if mods:
            dpg.add_text(f"Категория: {category_display_name}", parent="mods_list")
            for mod in mods:
                mod_name = mod['name']
                with dpg.group(horizontal=True, parent="mods_list"):
                    dpg.add_button(label=mod_name, callback=select_mod, user_data=mod)
                    dpg.add_button(label="Удалить", callback=delete_mod, user_data={'mod': mod, 'mod_key': mod_key})
            dpg.add_separator(parent="mods_list")

    # Добавляем моды оружия, сгруппированные по внутренней категории
    if 'mod_weapon' in mods_data:
        mods = mods_data['mod_weapon']
        if mods:
            # Группируем моды по внутренней категории
            mods_by_category = {}
            for mod in mods:
                mod_category = mod.get('category', 'None')
                mods_by_category.setdefault(mod_category, []).append(mod)

            # Отображаем моды, сгруппированные по категориям
            for mod_category, mods_in_category in mods_by_category.items():
                dpg.add_text(f"Категория: {mod_category}", parent="mods_list")
                for mod in mods_in_category:
                    mod_name = mod['name']
                    with dpg.group(horizontal=True, parent="mods_list"):
                        dpg.add_button(label=mod_name, callback=select_mod, user_data=mod)
                        dpg.add_button(label="Удалить", callback=delete_mod, user_data={'mod': mod, 'mod_key': 'mod_weapon'})
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

def delete_mod(sender, app_data, user_data):
    mod = user_data['mod']
    mod_key = user_data['mod_key']
    if mod_key in mods_data:
        mods_data[mod_key].remove(mod)
        save_mods(mods_data)
        edit_mods(None, None, None)

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

def update_parameter_name_tooltip(sender, app_data, user_data):
    selected_item = dpg.get_value(sender)
    description = parameter_names.get(selected_item, "Нет описания")
    dpg.set_value("stat_key_tooltip_text", description)

def update_parameter_value_tooltip(sender, app_data, user_data):
    selected_item = dpg.get_value(sender)
    description = parameter_values.get(selected_item, "Нет описания")
    dpg.set_value("stat_value_tooltip_text", description)

# Коллбэки для калькулятора
def mouse_down_callback(sender, app_data, user_data):
    global mouse_pressed
    mouse_pressed = True

def mouse_up_callback(sender, app_data, user_data):
    global mouse_pressed
    mouse_pressed = False

def calculate_damage(is_weak_spot, is_crit):
    base_damage = dpg.get_value("base_damage_input")
    crit_dmg = dpg.get_value("crit_dmg_input")
    vulnerability_damage = dpg.get_value("vulnerability_damage_input")
    weapon_damage_bonus = dpg.get_value("weapon_damage_bonus_input")

    # Get the enemy damage bonuses
    default_enemy_damage_bonus = dpg.get_value("default_enemy_damage_bonus_input")
    elit_enemy_damage_bonus = dpg.get_value("elit_enemy_damage_bonus_input")
    boss_damage_bonus = dpg.get_value("boss_damage_bonus_input")

    damage = base_damage

    # Применяем статы выбранных модов
    for mod_stats in selected_mods_stats.values():
        for stat_name, stat_value in mod_stats.items():
            if stat_name == "damage":
                damage += stat_value
            elif stat_name == "weapon_dmg_percent":
                weapon_damage_bonus += stat_value
            elif stat_name == "crit_dmg_percent":
                crit_dmg += stat_value
            elif stat_name == "vulnerability_damage_percent":
                vulnerability_damage += stat_value
            elif stat_name == "status_dmg_percent":
                # Применяем бонус к урону статуса
                damage *= (1 + stat_value / 100)
            elif stat_name == "elemental_dmg_percent":
                # Применяем бонус к элементальному урону
                damage *= (1 + stat_value / 100)
            elif stat_name == "weakspot_dmg_percent":
                if is_weak_spot:
                    damage *= (1 + stat_value / 100)
            # Добавьте обработку других статов по мере необходимости

    # Применяем эффекты статусов
    if "Vulnerability" in mannequin_status_effects:
        vulnerability_damage += mannequin_status_effects["Vulnerability"]

    # Apply buffs according to enemy type
    enemy_type = dpg.get_value("enemy_type_combo")
    if enemy_type == 'Игрок':
        # Не добавляем бонусы
        pass
    elif enemy_type == 'Моб':
        damage *= (1 + default_enemy_damage_bonus / 100)
    elif enemy_type == 'Элитный':
        damage *= (1 + elit_enemy_damage_bonus / 100)
    elif enemy_type == 'Босс':
        damage *= (1 + boss_damage_bonus / 100)

    # Apply weapon damage bonus
    damage *= (1 + weapon_damage_bonus / 100)

    if is_crit:
        damage *= (1 + crit_dmg / 100)

    if is_weak_spot:
        damage *= (1 + vulnerability_damage / 100)

    return damage

def apply_damage():
    global total_damage, dps, last_damage_time, damage_history, current_ammo, reloading, reload_end_time

    current_time = time.time()

    if reloading:
        return

    if current_ammo <= 0:
        # Начинаем перезарядку
        reloading = True
        reload_speed = dpg.get_value("reload_speed_input")
        reload_end_time = current_time + reload_speed
        dpg.set_value("ammo_text", "Перезарядка...")
        dpg.configure_item("ammo_text", color=[255, 0, 0, 255])
        return

    last_damage_time = current_time

    crit_chance = get_total_crit_chance()

    # Определяем критический удар
    is_crit = random.uniform(0, 100) <= crit_chance

    # Получаем позицию мыши в глобальных координатах
    mouse_pos = dpg.get_mouse_pos(local=False)
    drawlist_pos = dpg.get_item_rect_min("damage_layer")
    local_mouse_pos = [mouse_pos[0] - drawlist_pos[0], mouse_pos[1] - drawlist_pos[1]]

    # Координаты зон урона
    normal_zone = [90, 50, 210, 290]  # Обычная зона
    weak_zone = [130, 10, 170, 50]  # Слабое место

    # Проверяем попадание в слабую зону
    is_weak_spot = weak_zone[0] <= local_mouse_pos[0] <= weak_zone[2] and weak_zone[1] <= local_mouse_pos[1] <= weak_zone[3]

    # Проверяем попадание в обычную зону, если не было попадания в слабое место
    if not is_weak_spot:
        if not (normal_zone[0] <= local_mouse_pos[0] <= normal_zone[2] and normal_zone[1] <= local_mouse_pos[1] <= normal_zone[3]):
            # Если клик вне обеих зон, урон не наносится
            return

    # Вычисляем урон с помощью отдельной функции
    damage = calculate_damage(is_weak_spot, is_crit)

    total_damage += damage

    # Уменьшаем количество патронов
    current_ammo -= 1
    magazine_capacity = get_total_magazine_capacity()
    dpg.set_value("ammo_text", f"Патроны: {current_ammo}/{magazine_capacity}")

    # Добавляем запись в историю урона
    damage_history.append((time.time(), damage))

    # Обновляем DPS
    dps = calculate_dps()

    # Обновляем надписи
    dpg.set_value("dps_text", f"DPS: {int(dps)}    Total DMG: {int(total_damage)}")

    # Отображаем цифры урона
    damage_text = f"{int(damage)}"
    if is_weak_spot:
        color = [255, 0, 0, 255]  # Ярко-красный
    elif is_crit:
        color = [255, 165, 0, 255]  # Оранжевый
    else:
        color = [255, 255, 255, 255]  # Белый

    # Создаем текст урона на позиции мыши
    initial_pos = local_mouse_pos.copy()
    angle = random.uniform(math.radians(45), math.radians(135))  # Угол между 45 и 135 градусами
    speed = 100  # Скорость полета текста (пикселей в секунду)
    vx = speed * math.cos(angle)
    vy = -speed * math.sin(angle)  # Отрицательный, потому что ось Y направлена вниз

    damage_text_id = dpg.draw_text(pos=initial_pos, text=damage_text, color=color, parent="damage_layer", size=20)

    # Добавляем информацию для анимации
    creation_time = time.time()
    scheduled_deletions.append({
        'id': damage_text_id,
        'start_pos': initial_pos,
        'start_time': creation_time,
        'duration': 1.0,  # Продолжительность анимации
        'color': color,
        'velocity': (vx, vy)
        #todo: добавь всю оставшуюся информацию
    })

    # Обновляем эффекты статусов
    update_status_effects()

    # Обработка событий
    handle_events(is_crit)

def handle_events(is_crit):
    # Если произошел критический удар, вызываем обработчики
    if is_crit:
        for handler in event_handlers.get("on_critical_hit", []):
            handler()

    # Если произошло срабатывание Unstable Bomber, вызываем соответствующие обработчики
    if is_crit:
        for handler in event_handlers.get("on_trigger_unstable_bomber", []):
            handler()

def calculate_dps():
    current_time = time.time()
    # Оставляем только записи за последнюю секунду
    recent_damage = [d for t, d in damage_history if current_time - t <= 1.0]
    # Удаляем устаревшие записи
    damage_history[:] = [(t, d) for t, d in damage_history if current_time - t <= 1.0]
    return sum(recent_damage)

def update():
    global total_damage, last_damage_time, damage_history, dps, last_fire_time, reloading, reload_end_time, current_ammo

    current_time = time.time()

    # Обрабатываем перезарядку
    if reloading and current_time >= reload_end_time:
        reloading = False
        magazine_capacity = get_total_magazine_capacity()
        current_ammo = magazine_capacity
        dpg.set_value("ammo_text", f"Патроны: {current_ammo}/{magazine_capacity}")
        dpg.configure_item("ammo_text", color=[255, 255, 255, 255])

    # Обрабатываем стрельбу
    if mouse_pressed and not reloading:
        # Обработка мода, влияющего на скорострельность
        fire_rate = get_total_fire_rate()

        if fire_rate > 0:
            time_between_shots = 60.0 / fire_rate
        else:
            time_between_shots = 0.1  # Минимальный интервал между выстрелами

        if time.time() - last_fire_time >= time_between_shots:
            apply_damage()
            last_fire_time = time.time()

    # Обновляем DPS
    dps = calculate_dps()
    dpg.set_value("dps_text", f"DPS: {int(dps)}    Total DMG: {int(total_damage)}")

    # Проверяем, прошло ли 3 секунды без нанесения урона
    if current_time - last_damage_time >= 3.0 and total_damage != 0:
        total_damage = 0
        dpg.set_value("dps_text", f"DPS: 0    Total DMG: {int(total_damage)}")
        # Изменяем цвет на более яркий
        dpg.configure_item("dps_text", color=[255, 0, 0])
    else:
        # Возвращаем цвет текста
        dpg.configure_item("dps_text", color=[46, 237, 190])

    # Обновляем анимацию урона
    for item in scheduled_deletions[:]:
        elapsed = current_time - item['start_time']
        if elapsed > item['duration']:
            dpg.delete_item(item['id'])
            scheduled_deletions.remove(item)
        else:
            # Обновляем позицию и прозрачность
            progress = elapsed / item['duration']
            dx = item['velocity'][0] * elapsed
            dy = item['velocity'][1] * elapsed
            new_pos = [item['start_pos'][0] + dx, item['start_pos'][1] + dy]
            new_alpha = int((1 - progress) * 255)
            new_color = item['color'][:3] + [new_alpha]
            dpg.configure_item(item['id'], pos=new_pos, color=new_color)

    # Обновляем статус эффектов
    update_status_effects()

    # Обновляем отображение статов
    update_stats_display()

def update_status_effects():
    # Обработка бесконечных статусов
    selected_status = dpg.get_value("status_combo")
    if selected_status:
        if selected_status == "Заморозка":
            mannequin_status_effects["Vulnerability"] = 4  # Уязвимость +4%
            mannequin_status_effects["Movement Speed"] = -10  # Скорость перемещения -10%
        elif selected_status == "Горение":
            # Обработка стаков огня
            if status_stack_counts["Fire"] < max_fire_stacks:
                status_stack_counts["Fire"] += 1
            mannequin_status_effects["Fire Damage"] = status_stack_counts["Fire"] * 2  # Пример урона от огня
        # Добавьте другие статусы по необходимости
    else:
        mannequin_status_effects.clear()
        status_stack_counts["Fire"] = 0

def on_parameter_change(sender, app_data, user_data):
    global current_ammo
    # Если изменилось значение емкости магазина, обновляем текущие патроны
    if sender == "magazine_capacity_input":
        magazine_capacity = get_total_magazine_capacity()
        current_ammo = magazine_capacity
        dpg.set_value("ammo_text", f"Патроны: {current_ammo}/{magazine_capacity}")

def initialize():
    global current_ammo
    magazine_capacity = get_total_magazine_capacity()
    current_ammo = magazine_capacity
    dpg.set_value("ammo_text", f"Патроны: {current_ammo}/{magazine_capacity}")

def on_mod_selected(sender, app_data, user_data):
    global selected_mods_stats
    category = user_data['category']
    mod = user_data['mod']

    selected_mods_stats[category] = mod.get('stats', {})
    # Обновляем описание
    description = mod.get('description', '')
    dpg.set_value(f"{category}_mod_description", description)

    # Обновляем параметры, если моды влияют на них
    update_parameters_from_mods()

    # Регистрируем обработчики событий из модов
    register_event_handlers(mod.get('stats', {}))

def open_mod_selection(sender, app_data, user_data):
    category = user_data
    # Очищаем предыдущий список
    dpg.delete_item("mod_selection_list", children_only=True)

    if category == "Оружие":
        mods = mods_data.get('mod_weapon', [])
        # Группируем моды по внутренней категории
        mods_by_category = {}
        for mod in mods:
            mod_category = mod.get('category', 'None')
            mods_by_category.setdefault(mod_category, []).append(mod)

        # Отображаем моды, сгруппированные по категориям
        for mod_category, mods_in_category in mods_by_category.items():
            dpg.add_text(f"Категория: {mod_category}", parent="mod_selection_list")
            for mod in mods_in_category:
                mod_name = mod['name']
                with dpg.group(horizontal=True, parent="mod_selection_list"):
                    dpg.add_button(label=mod_name, callback=select_mod_for_category, user_data={'category': category, 'mod': mod})
                    if 'description' in mod:
                        dpg.add_text(mod['description'], wrap=300)
            dpg.add_separator(parent="mod_selection_list")
    else:
        # Получаем ключ категории для загрузки модов
        mod_key = category_key_mapping.get(category, 'mod_weapon')
        # Загружаем моды для данной категории
        mods = mods_data.get(mod_key, [])
        for mod in mods:
            mod_name = mod['name']
            with dpg.group(horizontal=True, parent="mod_selection_list"):
                dpg.add_button(label=mod_name, callback=select_mod_for_category, user_data={'category': category, 'mod': mod})
                if 'description' in mod:
                    dpg.add_text(mod['description'], wrap=300)
        dpg.add_separator(parent="mod_selection_list")

    dpg.configure_item("mod_selection_window", show=True)

def select_mod_for_category(sender, app_data, user_data):
    category = user_data['category']
    mod = user_data['mod']
    dpg.set_value(f"{category}_mod_selector", mod['name'])
    on_mod_selected(f"{category}_mod_selector", None, {'category': category, 'mod': mod})
    dpg.configure_item("mod_selection_window", show=False)

def update_parameters_from_mods():
    # Обновляем параметры, которые зависят от модов
    initialize()  # Обновляем емкость магазина
    # Добавьте другие обновления параметров по мере необходимости

def update_stats_display():
    # Обновляем отображение всех статов справа от манекена
    stats_text = "Текущие параметры:\n"
    # Собираем все параметры
    parameters = {
        "current_ammo": current_ammo,
        "magazine_capacity": get_total_magazine_capacity(),
        "base_damage": dpg.get_value("base_damage_input"),
        "crit_chance": get_total_crit_chance(),
        "crit_dmg": dpg.get_value("crit_dmg_input"),
        "vulnerability_damage": dpg.get_value("vulnerability_damage_input"),
        "weapon_damage_bonus": dpg.get_value("weapon_damage_bonus_input"),
        # Добавим параметры из раздела "Боевые характеристики"
        "status_damage_bonus": dpg.get_value("status_damage_bonus_input"),
        "fire_rate": get_total_fire_rate(),
        #Todo: Добавь другие параметры которых не хватает
    }

    # Применяем модификаторы от модов
    for mod_stats in selected_mods_stats.values():
        for key, value in mod_stats.items():
            if isinstance(value, (int, float)):
                if key in parameters:
                    parameters[key] += value
                else:
                    parameters[key] = value

    # Формируем текст для отображения
    for key, value in parameters.items():
        stats_text += f"{key}: {value}\n"

    # Добавляем статусные эффекты
    if mannequin_status_effects:
        stats_text += "\nСтатусные эффекты:\n"
        for key, value in mannequin_status_effects.items():
            stats_text += f"{key}: {value}\n"

    # Обновляем текстовый виджет
    dpg.set_value("stats_display_text", stats_text)

def get_total_magazine_capacity():
    magazine_capacity = dpg.get_value("magazine_capacity_input")
    magazine_bonus = 0
    for mod_stats in selected_mods_stats.values():
        magazine_bonus += mod_stats.get("magazine_capacity_bonus", 0)
    total_magazine_capacity = magazine_capacity + magazine_bonus
    return total_magazine_capacity

def get_total_fire_rate():
    fire_rate = dpg.get_value("fire_rate_input")
    fire_rate_bonus = 0
    for mod_stats in selected_mods_stats.values():
        fire_rate_bonus += mod_stats.get("fire_rate_percent", 0)
    total_fire_rate = fire_rate * (1 + fire_rate_bonus / 100)
    return total_fire_rate

def get_total_crit_chance():
    crit_chance = dpg.get_value("crit_chance_input")
    crit_chance_bonus = 0
    for mod_stats in selected_mods_stats.values():
        crit_chance_bonus += mod_stats.get("crit_rate_percent", 0)
    total_crit_chance = crit_chance + crit_chance_bonus
    return total_crit_chance

def register_event_handlers(mod_stats):
    # Регистрируем обработчики событий из модов
    for key, value in mod_stats.items():
        if key.startswith("on_"):
            event_name = key
            handler = create_event_handler(event_name, value)
            event_handlers.setdefault(event_name, []).append(handler)

def create_event_handler(event_name, effect):
    def handler():
        global current_ammo
        # Обрабатываем эффект
        if "refill_magazine_percent" in effect:
            percent = effect["refill_magazine_percent"]
            refill_amount = int(get_total_magazine_capacity() * (percent / 100))
            current_ammo = min(current_ammo + refill_amount, get_total_magazine_capacity())
            dpg.set_value("ammo_text", f"Патроны: {current_ammo}/{get_total_magazine_capacity()}")
        elif "refill_bullet" in effect:
            bullets = effect["refill_bullet"]
            current_ammo = min(current_ammo + bullets, get_total_magazine_capacity())
            dpg.set_value("ammo_text", f"Патроны: {current_ammo}/{get_total_magazine_capacity()}")
        # Добавьте обработку других эффектов по мере необходимости
    return handler

dpg.create_viewport(title='Редактор и Калькулятор', width=1200, height=700)

with dpg.window(label="Main Window", width=1200, height=700):
    with dpg.tab_bar():
        with dpg.tab(label="Calc"):
            # Создаем интерфейс калькулятора
            with dpg.group(horizontal=True):
                # Левое поле
                with dpg.child_window(width=600, height=650, horizontal_scrollbar=True):
                    # Параметры
                    dpg.add_text("Параметры:")

                    # Базовые характеристики
                    dpg.add_spacer(height=5)
                    dpg.add_separator()
                    dpg.add_spacer(height=5)
                    dpg.add_text("Базовые характеристики:", color=[255, 255, 255], bullet=True)

                    with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                        dpg.add_table_column()
                        dpg.add_table_column()

                        with dpg.table_row():
                            dpg.add_text("Урон (УРН):")
                            dpg.add_input_int(default_value=100, min_value=0, max_value=100000, step=0,
                                              width=100, callback=on_parameter_change, tag="base_damage_input")

                        with dpg.table_row():
                            dpg.add_text("Пси-интенсивность:")
                            dpg.add_input_int(default_value=0, min_value=0, max_value=100, step=0,
                                              width=100, callback=on_parameter_change, tag="psi_intensity_input")

                        with dpg.table_row():
                            dpg.add_text("ОЗ (xp):")
                            dpg.add_input_int(default_value=10000, min_value=0, max_value=100000, step=0,
                                              width=100, callback=on_parameter_change, tag="hp_input")

                        with dpg.table_row():
                            dpg.add_text("Сопротивление загрязнению:")
                            dpg.add_input_int(default_value=0, min_value=0, max_value=100, step=0,
                                              width=100, callback=on_parameter_change, tag="contamination_resistance_input")

                    # Боевые характеристики
                    dpg.add_spacer(height=5)
                    dpg.add_separator()
                    dpg.add_spacer(height=5)
                    dpg.add_text("Боевые характеристики:", color=[255, 255, 255], bullet=True)

                    with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                        dpg.add_table_column()
                        dpg.add_table_column()

                        with dpg.table_row():
                            dpg.add_text("Шанс крит. попадания %:")
                            dpg.add_input_int(default_value=20, min_value=0, max_value=100, step=0,
                                              width=100, callback=on_parameter_change, tag="crit_chance_input")

                        with dpg.table_row():
                            dpg.add_text("Крит. УРН +%:")
                            dpg.add_input_int(default_value=50, min_value=0, max_value=1000, step=0,
                                              width=100, callback=on_parameter_change, tag="crit_dmg_input")

                        with dpg.table_row():
                            dpg.add_text("УРН уязвимостям %:")
                            dpg.add_input_int(default_value=30, min_value=0, max_value=1000,
                                              step=0, width=100, callback=on_parameter_change, tag="vulnerability_damage_input")

                        with dpg.table_row():
                            dpg.add_text("Бонус к УРН оружия %:")
                            dpg.add_input_int(default_value=0, min_value=0, max_value=1000,
                                              step=0, width=100, callback=on_parameter_change, tag="weapon_damage_bonus_input")

                        with dpg.table_row():
                            dpg.add_text("Бонус к УРН статуса %:")
                            dpg.add_input_int(default_value=0, min_value=0, max_value=1000,
                                              step=0, width=100, callback=on_parameter_change, tag="status_damage_bonus_input")

                        with dpg.table_row():
                            dpg.add_text(f"Бонус к УРН обычным %:")
                            dpg.add_input_int(default_value=0, min_value=0, max_value=1000,
                                              step=0, width=100, callback=on_parameter_change, tag="default_enemy_damage_bonus_input")

                        with dpg.table_row():
                            dpg.add_text(f"Бонус к УРН элиткам %:")
                            dpg.add_input_int(default_value=0, min_value=0, max_value=1000,
                                              step=0, width=100, callback=on_parameter_change, tag="elit_enemy_damage_bonus_input")

                        with dpg.table_row():
                            dpg.add_text(f"Бонус к УРН против боссов %:")
                            dpg.add_input_int(default_value=0, min_value=0, max_value=1000,
                                              step=0, width=100, callback=on_parameter_change, tag="boss_damage_bonus_input")

                        with dpg.table_row():
                            dpg.add_text("Скорость стрельбы (выстр./мин):")
                            dpg.add_input_int(default_value=600, min_value=0, max_value=6000, step=0,
                                              width=100, callback=on_parameter_change, tag="fire_rate_input")

                        with dpg.table_row():
                            dpg.add_text("Емкость магазина:")
                            dpg.add_input_int(default_value=30, min_value=1, max_value=1000, step=0,
                                              width=100, callback=on_parameter_change, tag="magazine_capacity_input")

                        with dpg.table_row():
                            dpg.add_text("Скорость перезарядки (сек):")
                            dpg.add_input_int(default_value=1, min_value=0, max_value=10, step=0,
                                              width=100, callback=on_parameter_change, tag="reload_speed_input")

                    # Показатели защиты
                    dpg.add_spacer(height=5)
                    dpg.add_separator()
                    dpg.add_spacer(height=5)
                    dpg.add_text("Показатели защиты:", color=[255, 255, 255], bullet=True)

                    with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                        dpg.add_table_column()
                        dpg.add_table_column()

                        with dpg.table_row():
                            dpg.add_text("Снижение УРН %:")
                            dpg.add_input_int(default_value=0, min_value=0, max_value=100,
                                              step=0, width=100, callback=on_parameter_change, tag="damage_reduction_input")

                        with dpg.table_row():
                            dpg.add_text("Сопротивление загрязнению:")
                            dpg.add_input_int(default_value=0, min_value=0, max_value=100,
                                              step=0, width=100, callback=on_parameter_change, tag="resistance_to_pollution")

                    # Выбор модов
                    dpg.add_spacer(height=5)
                    dpg.add_separator()
                    dpg.add_spacer(height=5)
                    dpg.add_text("Выбор модов:", color=[255, 255, 255], bullet=True)

                    # Добавляем кнопку для выбора мода оружия отдельно
                    with dpg.group(horizontal=False):
                        with dpg.group(horizontal=True):
                            dpg.add_input_text(label=f"Оружие", readonly=True, tag=f"Оружие_mod_selector", width=150)
                            dpg.add_button(label="Выбрать", callback=open_mod_selection, user_data="Оружие", width=80)
                        dpg.add_text("", tag=f"Оружие_mod_description")

                    for category in mod_categories:
                        with dpg.group(horizontal=False):
                            with dpg.group(horizontal=True):
                                dpg.add_input_text(label=f"{category}", readonly=True, tag=f"{category}_mod_selector", width=150)
                                dpg.add_button(label="Выбрать", callback=open_mod_selection, user_data=category, width=80)
                            dpg.add_text("", tag=f"{category}_mod_description")

                # Правое поле
                with dpg.child_window(width=600, height=650) as right_field:

                    # Группа для всего содержимого правого поля
                    with dpg.group(horizontal=False):

                        # Верхняя часть: чекбоксы статусов, привязанные к правой стороне
                        with dpg.group(horizontal=False):
                            dpg.add_spacer(width=50)
                            dpg.add_combo(items=['Горение', 'Заморозка', 'Яблочко', 'Fortress W.'], label='Выберите статус', tag="status_combo", callback=lambda s, a, u: update_status_effects(), width=150)

                        # DPS и Total DMG, центрированные
                        with dpg.group(horizontal=True):
                            dpg.add_spacer(width=0)
                            dpg.add_text("DPS: 0    Total DMG: 0", color=[0, 0, 255], tag="dps_text")
                            dpg.add_spacer()

                        # Текущие патроны, центрированные
                        with dpg.group(horizontal=True):
                            dpg.add_spacer(width=0)
                            dpg.add_text(f"Патроны: {current_ammo}/0", tag="ammo_text")
                            dpg.add_spacer()

                        # Центрируем изображение и текст статов
                        with dpg.group(horizontal=True):
                            dpg.add_spacer()

                            # Левая часть: Манекен
                            with dpg.group():
                                # Загружаем изображение
                                if os.path.exists("target_image.png"):
                                    width_img, height_img, channels, data = dpg.load_image("target_image.png")
                                else:
                                    # Если изображения нет, создаем пустую текстуру
                                    width_img, height_img = 300, 300
                                    data = [255] * width_img * height_img * 4  # Белый фон

                                with dpg.texture_registry():
                                    texture_id = dpg.add_static_texture(width_img, height_img, data)

                                # Создаем drawlist
                                with dpg.drawlist(width=300, height=300, tag="damage_layer"):
                                    dpg.draw_image(texture_id, pmin=[0, 0], pmax=[300, 300])

                                    # Рисуем полупрозрачные зоны
                                    # Обычная зона (синяя)
                                    dpg.draw_rectangle(pmin=[90, 50], pmax=[210, 290], color=[0, 0, 255, 100], fill=[0, 0, 255, 50])
                                    # Слабое место (красная)
                                    dpg.draw_rectangle(pmin=[130, 10], pmax=[170, 50], color=[255, 0, 0, 100], fill=[255, 0, 0, 50])

                                    # Привязываем обработчики к drawlist
                                    with dpg.item_handler_registry() as handler_id:
                                        dpg.add_item_clicked_handler(callback=mouse_down_callback)
                                        dpg.add_item_deactivated_handler(callback=mouse_up_callback)
                                    dpg.bind_item_handler_registry("damage_layer", handler_id)
                            dpg.add_spacer()

                            # Правая часть: Отображение статов
                            with dpg.group():
                                dpg.add_text("", tag="stats_display_text")

                        with dpg.group(horizontal=True):
                            dpg.add_spacer()
                            dpg.add_combo(items=['Игрок', 'Моб', 'Элитный', 'Босс'], label='Тип врага', tag="enemy_type_combo", width=150)

            # Инициализируем значения
            initialize()

            # Окно выбора мода
            with dpg.window(label="Выбор мода", modal=True, show=False, tag="mod_selection_window", width=400, height=500):
                dpg.add_text("Выберите мод:")
                dpg.add_child_window(tag="mod_selection_list", autosize_x=True, autosize_y=True)
                dpg.add_button(label="Закрыть", callback=lambda: dpg.configure_item("mod_selection_window", show=False))

        with dpg.tab(label="Create"):
            # Код для вкладки "Create" (создание модов)
            dpg.add_text("Введите информацию о модификаторе:", color=[255, 255, 0])

            # Поле выбора категории с возможностью добавить новую
            with dpg.group(horizontal=True):
                dpg.add_combo(mod_categories, label="Категория модификатора", tag="mod_category")
                dpg.add_button(label="+", width=30, callback=add_category)

            # Поле ввода названия модификатора
            dpg.add_input_text(label="Название модификатора", tag="mod_name")

            dpg.add_separator()
            dpg.add_text("Добавьте параметры модификатора:", color=[255, 255, 0])

            # Поле выбора имени параметра с возможностью добавить новое
            with dpg.group(horizontal=True):
                dpg.add_combo(list(parameter_names.keys()), label="Имя параметра", tag="stat_key", callback=update_parameter_name_tooltip)
                dpg.add_button(label="+", width=30, callback=add_parameter_name)
                with dpg.tooltip("stat_key"):
                    dpg.add_text("", tag="stat_key_tooltip_text")

            # Поле выбора значения параметра с возможностью добавить новое
            with dpg.group(horizontal=True):
                dpg.add_combo(list(parameter_values.keys()), label="Значение параметра", tag="stat_value", callback=update_parameter_value_tooltip)
                dpg.add_button(label="+", width=30, callback=add_parameter_value)
                with dpg.tooltip("stat_value"):
                    dpg.add_text("", tag="stat_value_tooltip_text")

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

# Основной цикл приложения
while dpg.is_dearpygui_running():
    update()
    dpg.render_dearpygui_frame()

dpg.destroy_context()
