import dearpygui.dearpygui as dpg
import time
import random
import os
import math

dpg.create_context()
dpg.create_viewport(title='Симулятор стрельбы по мишени', width=800, height=700)

# Глобальные переменные
total_damage = 0
dps = 0
damage_history = []  # История нанесенного урона для расчета DPS
mouse_pressed = False
scheduled_deletions = []
current_ammo = 0  # Текущее количество патронов
reloading = False  # Флаг перезарядки
reload_end_time = 0  # Время окончания перезарядки
last_fire_time = time.time()

# Время последнего нанесения урона
last_damage_time = time.time()

# Загружаем системный шрифт, поддерживающий русский язык
with dpg.font_registry():
    font_path = "C:\\Windows\\Fonts\\arial.ttf"
    if os.path.exists(font_path):
        with dpg.font(font_path, 15, default_font=True) as default_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Cyrillic)
    else:
        print("Шрифт Arial не найден. Используется шрифт по умолчанию.")


def mouse_down_callback(sender, app_data, user_data):
    global mouse_pressed
    mouse_pressed = True


def mouse_up_callback(sender, app_data, user_data):
    global mouse_pressed
    mouse_pressed = False


def calculate_damage(is_weak_spot, is_crit):
    base_damage = dpg.get_value(base_damage_input)
    crit_dmg = dpg.get_value(crit_dmg_input)
    vulnerability_damage = dpg.get_value(vulnerability_damage_input)
    weapon_damage_bonus = dpg.get_value(weapon_damage_bonus_input)

    # Get the enemy damage bonuses
    default_enemy_damage_bonus = dpg.get_value(default_enemy_damage_bonus_input)
    elit_enemy_damage_bonus = dpg.get_value(elit_enemy_damage_bonus_input)
    boss_damage_bonus = dpg.get_value(boss_damage_bonus_input)

    damage = base_damage

    # Apply buffs according to enemy type
    # Apply buffs according to enemy type
    enemy_type = dpg.get_value(enemy_type_combo)
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
        reload_speed = dpg.get_value(reload_speed_input)
        reload_end_time = current_time + reload_speed
        dpg.set_value(ammo_text, "Перезарядка...")
        dpg.configure_item(ammo_text, color=[255, 0, 0, 255])
        return

    last_damage_time = current_time

    crit_chance = dpg.get_value(crit_chance_input)

    # Определяем критический удар
    is_crit = random.uniform(0, 100) <= crit_chance

    # Получаем позицию мыши в глобальных координатах
    mouse_pos = dpg.get_mouse_pos(local=False)
    drawlist_pos = dpg.get_item_rect_min(damage_layer)
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
    magazine_capacity = dpg.get_value(magazine_capacity_input)
    dpg.set_value(ammo_text, f"Патроны: {current_ammo}/{magazine_capacity}")

    # Добавляем запись в историю урона
    damage_history.append((time.time(), damage))

    # Обновляем DPS
    dps = calculate_dps()

    # Обновляем надписи
    dpg.set_value(dps_text, f"DPS: {int(dps)}    Total DMG: {int(total_damage)}")

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

    damage_text_id = dpg.draw_text(pos=initial_pos, text=damage_text, color=color, parent=damage_layer, size=20)

    # Добавляем информацию для анимации
    creation_time = time.time()
    scheduled_deletions.append({
        'id': damage_text_id,
        'start_pos': initial_pos,
        'start_time': creation_time,
        'duration': 1.0,  # Продолжительность анимации
        'color': color,
        'velocity': (vx, vy)
    })


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
        magazine_capacity = dpg.get_value(magazine_capacity_input)
        current_ammo = magazine_capacity
        dpg.set_value(ammo_text, f"Патроны: {current_ammo}/{magazine_capacity}")
        dpg.configure_item(ammo_text, color=[255, 255, 255, 255])

    # Обрабатываем стрельбу
    if mouse_pressed and not reloading:
        fire_rate = dpg.get_value(fire_rate_input)  # выстрелов в минуту
        if fire_rate > 0:
            time_between_shots = 60.0 / fire_rate
        else:
            time_between_shots = 0.1  # Минимальный интервал между выстрелами

        if current_time - last_fire_time >= time_between_shots:
            apply_damage()
            last_fire_time = current_time

    # Обновляем DPS
    dps = calculate_dps()
    dpg.set_value(dps_text, f"DPS: {int(dps)}    Total DMG: {int(total_damage)}")

    # Проверяем, прошло ли 3 секунды без нанесения урона
    if current_time - last_damage_time >= 3.0 and total_damage != 0:
        total_damage = 0
        dpg.set_value(dps_text, f"DPS: 0    Total DMG: {int(total_damage)}")
        # Изменяем цвет на более яркий
        dpg.configure_item(dps_text, color=[255, 0, 0])
    else:
        # Возвращаем цвет текста
        dpg.configure_item(dps_text, color=[46, 237, 190])

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


# Коллбэки для обновления параметров
def on_parameter_change(sender, app_data, user_data):
    global current_ammo
    # Если изменилось значение емкости магазина, обновляем текущие патроны
    if sender == magazine_capacity_input:
        magazine_capacity = dpg.get_value(magazine_capacity_input)
        current_ammo = magazine_capacity
        dpg.set_value(ammo_text, f"Патроны: {current_ammo}/{magazine_capacity}")

    # Можно добавить другие условия для обновления соответствующих переменных


# Создаем интерфейс
with dpg.window(label='Главное окно', width=800, height=650):
    with dpg.group(horizontal=True):
        # Левое поле
        with dpg.child_window(width=350, height=650, horizontal_scrollbar=True):
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
                    base_damage_input = dpg.add_input_int(default_value=1000, min_value=0, max_value=1000, step=0,
                                                          width=100, callback=on_parameter_change)

                with dpg.table_row():
                    dpg.add_text("Пси-интенсивность:")
                    psi_intensity_input = dpg.add_input_int(default_value=0, min_value=0, max_value=100, step=0,
                                                            width=100, callback=on_parameter_change)

                with dpg.table_row():
                    dpg.add_text("ОЗ (xp):")
                    hp_input = dpg.add_input_int(default_value=10000, min_value=0, max_value=100000, step=0,
                                                 width=100, callback=on_parameter_change)

                with dpg.table_row():
                    dpg.add_text("Сопротивление загрязнению:")
                    contamination_resistance_input = dpg.add_input_int(default_value=0, min_value=0, max_value=100,
                                                                      step=0, width=100, callback=on_parameter_change)

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
                    crit_chance_input = dpg.add_input_int(default_value=20, min_value=0, max_value=100, step=0,
                                                          width=100, callback=on_parameter_change)

                with dpg.table_row():
                    dpg.add_text("Крит. УРН +%:")
                    crit_dmg_input = dpg.add_input_int(default_value=50, min_value=0, max_value=1000, step=0,
                                                       width=100, callback=on_parameter_change)

                with dpg.table_row():
                    dpg.add_text("УРН уязвимостям %:")
                    vulnerability_damage_input = dpg.add_input_int(default_value=30, min_value=0, max_value=1000,
                                                                   step=0, width=100, callback=on_parameter_change)

                with dpg.table_row():
                    dpg.add_text("Бонус к УРН оружия %:")
                    weapon_damage_bonus_input = dpg.add_input_int(default_value=0, min_value=0, max_value=1000,
                                                                  step=0, width=100, callback=on_parameter_change)

                with dpg.table_row():
                    dpg.add_text("Бонус к УРН статуса %:")
                    status_damage_bonus_input = dpg.add_input_int(default_value=0, min_value=0, max_value=1000,
                                                                  step=0, width=100, callback=on_parameter_change)

                with dpg.table_row():
                    dpg.add_text(f"Бонус к УРН обычным %:")
                    default_enemy_damage_bonus_input = dpg.add_input_int(default_value=0, min_value=0, max_value=1000,
                                                                         step=0, width=100, callback=on_parameter_change)

                with dpg.table_row():
                    dpg.add_text(f"Бонус к УРН элиткам %:")
                    elit_enemy_damage_bonus_input = dpg.add_input_int(default_value=0, min_value=0, max_value=1000,
                                                                      step=0, width=100, callback=on_parameter_change)

                with dpg.table_row():
                    dpg.add_text(f"Бонус к УРН против боссов %:")
                    boss_damage_bonus_input = dpg.add_input_int(default_value=0, min_value=0, max_value=1000,
                                                                step=0, width=100, callback=on_parameter_change)

                with dpg.table_row():
                    dpg.add_text("Скорость стрельбы (выстр./мин):")
                    fire_rate_input = dpg.add_input_int(default_value=600, min_value=0, max_value=6000, step=0,
                                                        width=100, callback=on_parameter_change)

                with dpg.table_row():
                    dpg.add_text("Емкость магазина:")
                    magazine_capacity_input = dpg.add_input_int(default_value=30, min_value=1, max_value=1000, step=0,
                                                                width=100, callback=on_parameter_change)

                with dpg.table_row():
                    dpg.add_text("Скорость перезарядки (сек):")
                    reload_speed_input = dpg.add_input_int(default_value=1, min_value=0, max_value=10, step=0,
                                                           width=100, callback=on_parameter_change)

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
                    damage_reduction_input = dpg.add_input_int(default_value=0, min_value=0, max_value=100,
                                                               step=0, width=100, callback=on_parameter_change)

                with dpg.table_row():
                    dpg.add_text("Сопротивление загрязнению:")
                    resistance_to_pollution = dpg.add_input_int(default_value=0, min_value=0, max_value=100,
                                                               step=0, width=100, callback=on_parameter_change)


        # Правое поле
        with dpg.child_window(width=-1) as right_field:

            # Группа для всего содержимого правого поля
            with dpg.group(horizontal=False):

                # Верхняя часть: чекбоксы статусов, привязанные к правой стороне
                with dpg.group(horizontal=False):
                    dpg.add_spacer(width=50)
                    status_combo = dpg.add_combo(items=['Горение', 'Заморозка', 'Яблочко', 'Fortress W.'], label= 'Выберитестатус')

                    # DPS и Total DMG, центрированные
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=0)
                    dps_text = dpg.add_text("DPS: 0    Total DMG: 0", color=[0, 0, 255])
                    dpg.add_spacer()

                # Текущие патроны, центрированные
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=0)
                    ammo_text = dpg.add_text(f"Патроны: {current_ammo}/0")
                    dpg.add_spacer()

                # Центрируем изображение
                with dpg.group(horizontal=True):
                    dpg.add_spacer()
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
                    with dpg.drawlist(width=300, height=300) as damage_layer:
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
                        dpg.bind_item_handler_registry(damage_layer, handler_id)
                    dpg.add_spacer()

                with dpg.group(horizontal=True):
                    dpg.add_spacer()
                    enemy_type_combo = dpg.add_combo(items=['Игрок', 'Моб', 'Элитный', 'Босс'], label='Тип врага')



    # Устанавливаем шрифт по умолчанию, если удалось загрузить
    if 'default_font' in locals():
        dpg.bind_font(default_font)

    # Инициализируем значения


def initialize():
    global current_ammo
    magazine_capacity = dpg.get_value(magazine_capacity_input)
    current_ammo = magazine_capacity
    dpg.set_value(ammo_text, f"Патроны: {current_ammo}/{magazine_capacity}")


initialize()

dpg.setup_dearpygui()
dpg.show_viewport()

# Основной цикл приложения
while dpg.is_dearpygui_running():
    update()
    dpg.render_dearpygui_frame()

dpg.destroy_context()
