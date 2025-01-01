# main.py

import dearpygui.dearpygui as dpg
import os
import time
import random
import math
import json
from mechanics import *

dpg.create_context()
default_font = None
with dpg.font_registry():
    font_path = "C:\\Windows\\Fonts\\arial.ttf"
    if os.path.exists(font_path):
        with dpg.font(font_path, 15) as default_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Cyrillic)
    else:
        print("Шрифт Arial не найден. Используется шрифт по умолчанию.")

# Инициализация данных
current_mod = {}
stats_stack = []
current_mod['effects'] = []
stats_stack.append(current_mod['effects'])

# Глобальные переменные для калькулятора
context = {
    'total_damage': 0,
    'dps': 0,
    'max_dps': 0,
    'max_total_damage': 0,
    'damage_history': [],
    'mouse_pressed': False,
    'scheduled_deletions': [],
    'current_ammo': 0,
    'reloading': False,
    'reload_end_time': 0,
    'last_fire_time': time.time(),
    'last_damage_time': time.time(),
    'selected_mods': [],
    'mannequin_status_effects': {},
    'status_stack_counts': {"Fire": 0},
    'max_fire_stacks': 16,
    'stats_display_timer': 0.0,
    'selected_status': None,
}

# Списки для выпадающих меню
stats_options = ['damage', 'crit_rate_percent', 'crit_damage_percent', 'weapon_damage_percent', 'status_damage_percent',
                 'max_hp', 'movement_speed_percent', 'elemental_damage_percent', 'weakspot_damage_percent',
                 'reload_speed_percent', 'magazine_capacity_percent', 'damage_bonus_normal', 'damage_bonus_elite',
                 'damage_bonus_boss']
flags_options = ['can_deal_weakspot_damage', 'is_invincible', 'has_super_armor']
conditions_options = ['hp / max_hp > 0.5', 'enemies_within_distance == 0', 'is_crit', 'is_weak_spot',
                      'target_is_marked', 'hp / max_hp < 0.3']


# Функции для обновления превью
def update_effects_preview():
    dpg.set_value("effects_preview", json.dumps(current_mod['effects'], ensure_ascii=False, indent=2))


# Функции для создания и редактирования модов
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


def add_new_stat(sender, app_data, user_data):
    new_stat = dpg.get_value("new_stat_input").strip()
    if new_stat and new_stat not in stats_options:
        stats_options.append(new_stat)
        dpg.configure_item("effect_stat", items=stats_options)
        dpg.set_value("new_stat_input", "")
        dpg.configure_item("add_stat_window", show=False)
    else:
        dpg.configure_item("error_modal_stat", show=True)


def add_new_flag(sender, app_data, user_data):
    new_flag = dpg.get_value("new_flag_input").strip()
    if new_flag and new_flag not in flags_options:
        flags_options.append(new_flag)
        dpg.configure_item("effect_flag", items=flags_options)
        dpg.set_value("new_flag_input", "")
        dpg.configure_item("add_flag_window", show=False)
    else:
        dpg.configure_item("error_modal_flag", show=True)


def add_new_condition(sender, app_data, user_data):
    new_condition = dpg.get_value("new_condition_input").strip()
    if new_condition and new_condition not in conditions_options:
        conditions_options.append(new_condition)
        dpg.configure_item("effect_condition", items=conditions_options)
        dpg.set_value("new_condition_input", "")
        dpg.configure_item("add_condition_window", show=False)
    else:
        dpg.configure_item("error_modal_condition", show=True)


def add_effect(sender, app_data, user_data):
    effect_type = dpg.get_value("effect_type").strip()
    if effect_type:
        effect = {'type': effect_type}
        if effect_type in ['increase_stat', 'decrease_stat']:
            stat = dpg.get_value("effect_stat").strip()
            value = dpg.get_value("effect_value")
            if stat and value != '':
                effect['stat'] = stat if ',' not in stat else [s.strip() for s in stat.split(',')]
                effect['value'] = float(value)
            else:
                dpg.configure_item("error_modal_effect", show=True)
                return
        elif effect_type == 'set_flag':
            flag = dpg.get_value("effect_flag").strip()
            value = dpg.get_value("effect_flag_value")
            if flag:
                effect['flag'] = flag
                effect['value'] = value
            else:
                dpg.configure_item("error_modal_effect", show=True)
                return
        elif effect_type == 'conditional_effect':
            condition = dpg.get_value("effect_condition").strip()
            if condition:
                effect['condition'] = condition
                effect['effects'] = []
                stats_stack.append(effect['effects'])
            else:
                dpg.configure_item("error_modal_effect", show=True)
                return
        current_effects = stats_stack[-1]
        current_effects.append(effect)
        update_effects_preview()
        dpg.set_value("effect_type", "")
        dpg.set_value("effect_stat", "")
        dpg.set_value("effect_value", "")
        dpg.set_value("effect_flag", "")
        dpg.set_value("effect_flag_value", False)
        dpg.set_value("effect_condition", "")
    else:
        dpg.configure_item("error_modal_effect", show=True)


def end_conditional_effect(sender, app_data, user_data):
    if len(stats_stack) > 1:
        stats_stack.pop()
        update_effects_preview()
    else:
        dpg.configure_item("error_modal_end_conditional", show=True)


def create_mod(sender, app_data, user_data):
    name = dpg.get_value("mod_name").strip()
    category = dpg.get_value("mod_category").strip()
    if name:
        current_mod['name'] = name
        if category:
            current_mod['category'] = category
        else:
            current_mod['category'] = "None"
        mod_key = category_key_mapping.get(category, 'mod_weapon')
        if mod_key not in mods_data:
            mods_data[mod_key] = []
        mods_data[mod_key].append(current_mod.copy())
        save_mods(mods_data)
        dpg.configure_item("status_text", default_value="Модификатор успешно сохранен!", color=[0, 255, 0])
        dpg.set_value("mod_name", "")
        dpg.set_value("mod_category", "")
        current_mod['effects'] = []
        stats_stack.clear()
        stats_stack.append(current_mod['effects'])
        update_effects_preview()
    else:
        dpg.configure_item("error_modal_name", show=True)


def reset_form(sender, app_data, user_data):
    dpg.set_value("mod_name", "")
    dpg.set_value("mod_category", "")
    dpg.set_value("effect_type", "")
    dpg.set_value("effect_stat", "")
    dpg.set_value("effect_value", "")
    dpg.set_value("effect_flag", "")
    dpg.set_value("effect_flag_value", False)
    dpg.set_value("effect_condition", "")
    current_mod['effects'] = []
    stats_stack.clear()
    stats_stack.append(current_mod['effects'])
    update_effects_preview()
    dpg.configure_item("status_text", default_value="", color=[0, 0, 0])


def edit_mods(sender, app_data, user_data):
    dpg.delete_item("mods_list", children_only=True)
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
    dpg.configure_item("edit_mods_window", show=True)


def select_mod(sender, app_data, user_data):
    mod = user_data
    dpg.set_value("mod_name", mod.get('name', ''))
    dpg.set_value("mod_category", mod.get('category', ''))
    current_mod.clear()
    current_mod.update(mod)
    stats_stack.clear()
    stats_stack.append(current_mod['effects'])
    update_effects_preview()
    # Очистка полей перед заполнением
    dpg.set_value("effect_type", "")
    dpg.set_value("effect_stat", "")
    dpg.set_value("effect_value", "")
    dpg.set_value("effect_flag", "")
    dpg.set_value("effect_flag_value", False)
    dpg.set_value("effect_condition", "")
    dpg.configure_item("edit_mods_window", show=False)


def delete_mod(sender, app_data, user_data):
    mod = user_data['mod']
    mod_key = user_data['mod_key']
    if mod_key in mods_data:
        mods_data[mod_key].remove(mod)
        save_mods(mods_data)
        edit_mods(None, None, None)


# Функции для калькулятора
def mouse_down_callback(sender, app_data, user_data):
    context['mouse_pressed'] = True


def mouse_up_callback(sender, app_data, user_data):
    context['mouse_pressed'] = False


def update():
    current_time = time.time()
    if context['reloading'] and current_time >= context['reload_end_time']:
        context['reloading'] = False
        magazine_capacity = dpg.get_value("magazine_capacity_input")
        context['current_ammo'] = magazine_capacity
        dpg.set_value("ammo_text", f"Bullets: {context['current_ammo']}/{magazine_capacity}")
        dpg.configure_item("ammo_text", color=[255, 255, 255, 255])
    if context['mouse_pressed'] and not context['reloading']:
        fire_rate = dpg.get_value("fire_rate_input")
        if fire_rate > 0:
            time_between_shots = 60.0 / fire_rate
        else:
            time_between_shots = 0.1
        if time.time() - context['last_fire_time'] >= time_between_shots:
            apply_damage_main()
            context['last_fire_time'] = time.time()
    context['dps'] = calculate_dps(context)
    dpg.set_value("dps_text", f"DPS: {int(context['dps'])}    Total DMG: {int(context['total_damage'])}")
    if current_time - context['last_damage_time'] >= 3.0 and context['total_damage'] != 0:
        context['total_damage'] = 0
        dpg.set_value("dps_text", f"DPS: 0    Total DMG: {int(context['total_damage'])}")
        dpg.configure_item("dps_text", color=[255, 0, 0])
    else:
        dpg.configure_item("dps_text", color=[46, 237, 190])
    for item in context['scheduled_deletions'][:]:
        elapsed = current_time - item['start_time']
        if elapsed > item['duration']:
            dpg.delete_item(item['id'])
            context['scheduled_deletions'].remove(item)
        else:
            progress = elapsed / item['duration']
            dx = item['velocity'][0] * elapsed
            dy = item['velocity'][1] * elapsed
            new_pos = [item['start_pos'][0] + dx, item['start_pos'][1] + dy]
            new_alpha = int((1 - progress) * 255)
            new_color = item['color'][:3] + [new_alpha]
            dpg.configure_item(item['id'], pos=new_pos, color=new_color)
    update_status_effects(context)
    update_stats_display()
    if context['stats_display_timer'] > 0 and time.time() - context['stats_display_timer'] >= 3:
        dpg.bind_item_theme("stats_display_text", 0)
        context['stats_display_timer'] = 0.0


def apply_damage_main():
    current_time = time.time()
    if context['reloading']:
        return
    if context['current_ammo'] <= 0:
        context['reloading'] = True
        reload_speed = dpg.get_value("reload_speed_input")
        context['reload_end_time'] = current_time + reload_speed
        dpg.set_value("ammo_text", "Перезарядка...")
        dpg.configure_item("ammo_text", color=[255, 0, 0, 255])
        return
    context['is_crit'] = random.uniform(0, 100) <= dpg.get_value("crit_chance_input")
    mouse_pos = dpg.get_mouse_pos(local=False)
    drawlist_pos = dpg.get_item_rect_min("damage_layer")
    local_mouse_pos = [mouse_pos[0] - drawlist_pos[0], mouse_pos[1] - drawlist_pos[1]]
    normal_zone = [90, 50, 210, 290]
    weak_zone = [130, 10, 170, 50]
    context['is_weak_spot'] = weak_zone[0] <= local_mouse_pos[0] <= weak_zone[2] and weak_zone[1] <= local_mouse_pos[
        1] <= weak_zone[3]
    if not context['is_weak_spot']:
        if not (normal_zone[0] <= local_mouse_pos[0] <= normal_zone[2] and normal_zone[1] <= local_mouse_pos[1] <=
                normal_zone[3]):
            return
    context['damage'] = dpg.get_value("base_damage_input")
    context['crit_rate_percent'] = dpg.get_value("crit_chance_input")
    context['crit_damage_percent'] = dpg.get_value("crit_dmg_input")
    context['weapon_damage_percent'] = dpg.get_value("weapon_damage_bonus_input")
    context['status_damage_percent'] = dpg.get_value("status_damage_bonus_input")
    context['melee_damage_percent'] = 0
    context['weakspot_multiplier'] = dpg.get_value("weakspot_damage_bonus_input") / 100
    context['hp'] = dpg.get_value("hp_input")
    context['max_hp'] = context['hp']
    context['is_crit'] = context['is_crit']
    context['is_weak_spot'] = context['is_weak_spot']
    context['enemies_within_distance'] = dpg.get_value("enemies_within_distance_input")
    context['reload_speed'] = dpg.get_value("reload_speed_input")
    context['selected_mods'] = context['selected_mods']

    # Добавление типа врага и бонуса к урону против него
    context['enemy_type'] = dpg.get_value("enemy_type_combo")
    context['damage_bonus_vs_enemy'] = 0

    if context['enemy_type'] == 'Обычный':
        context['damage_bonus_vs_enemy'] = dpg.get_value("damage_bonus_normal_input")
    elif context['enemy_type'] == 'Элитный':
        context['damage_bonus_vs_enemy'] = dpg.get_value("damage_bonus_elite_input")
    elif context['enemy_type'] == 'Босс':
        context['damage_bonus_vs_enemy'] = dpg.get_value("damage_bonus_boss_input")

    damage = apply_damage(context)
    if damage is None:
        return
    magazine_capacity = dpg.get_value("magazine_capacity_input")
    dpg.set_value("ammo_text", f"Ammo: {context['current_ammo']}/{magazine_capacity}")
    damage_text = f"{int(damage)}"
    if context['is_weak_spot']:
        color = [255, 0, 0, 255]
    elif context['is_crit']:
        color = [255, 165, 0, 255]
    else:
        color = [255, 255, 255, 255]
    initial_pos = local_mouse_pos.copy()
    angle = random.uniform(math.radians(45), math.radians(135))
    speed = 100
    vx = speed * math.cos(angle)
    vy = -speed * math.sin(angle)
    damage_text_id = dpg.draw_text(pos=initial_pos, text=damage_text, color=color, parent="damage_layer", size=20)
    creation_time = time.time()
    context['scheduled_deletions'].append({
        'id': damage_text_id,
        'start_pos': initial_pos,
        'start_time': creation_time,
        'duration': 1.0,
        'color': color,
        'velocity': (vx, vy)
    })


def on_parameter_change(sender, app_data, user_data):
    if sender == "magazine_capacity_input":
        magazine_capacity = dpg.get_value("magazine_capacity_input")
        context['current_ammo'] = magazine_capacity
        dpg.set_value("ammo_text", f"Патроны: {context['current_ammo']}/{magazine_capacity}")


def initialize():
    magazine_capacity = dpg.get_value("magazine_capacity_input")
    context['current_ammo'] = magazine_capacity
    dpg.set_value("ammo_text", f"Патроны: {context['current_ammo']}/{magazine_capacity}")


def on_mod_selected(sender, app_data, user_data):
    category = user_data['category']
    mod = user_data['mod']
    context['selected_mods'][:] = [m for m in context['selected_mods'] if m.get('category') != category]
    context['selected_mods'].append(mod)
    # Обновляем кнопку
    unique_tag = f"{category}_mod_selector"
    parent_tag = f"{unique_tag}_parent"
    button_label = mod['name']
    texture_id = mod_images.get(category_key_mapping.get(category), {}).get(mod['name'], None)

    # Удаляем старую кнопку
    if dpg.does_item_exist(unique_tag):
        dpg.delete_item(unique_tag)

    # Создаем новую кнопку
    if texture_id:
        dpg.add_image_button(texture_tag=texture_id, width=50, height=50,
                             callback=open_mod_selection, user_data=category,
                             tag=unique_tag, parent=parent_tag)
    else:
        dpg.add_button(label=button_label, callback=open_mod_selection,
                       user_data=category, tag=unique_tag, parent=parent_tag)
    dpg.configure_item("mod_selection_window", show=False)


def open_mod_selection(sender, app_data, user_data):
    category = user_data
    dpg.delete_item("mod_selection_list", children_only=True)
    mod_key = category_key_mapping.get(category, 'mod_weapon')
    mods = mods_data.get(mod_key, [])

    # Создаем таблицу с тремя колонками
    with dpg.table(header_row=False, parent="mod_selection_list", resizable=True, policy=dpg.mvTable_SizingStretchProp):
        # Первая и вторая колонки фиксированной ширины
        dpg.add_table_column(width=60)  # Первая колонка для изображения
        dpg.add_table_column(width=100)  # Вторая колонка для кнопки

        # Третья колонка растягивается
        dpg.add_table_column()  # Третья колонка для текста, которая будет растягиваться

        for mod in mods:
            mod_name = mod['name']
            texture_id = mod_images.get(mod_key, {}).get(mod_name, None)
            if not texture_id:
                texture_id = mod_images['default']

            with dpg.table_row():
                # Первая колонка - картинка
                dpg.add_image_button(texture_id, width=50, height=50, callback=select_mod_for_category,
                                     user_data={'category': category, 'mod': mod})

                # Вторая колонка - кнопка
                button_tag = f"{category}_{mod_name}_button"
                dpg.add_button(label=mod_name, callback=select_mod_for_category,
                               user_data={'category': category, 'mod': mod}, tag=button_tag)

                # Третья колонка - текст
                if 'description' in mod:
                    dpg.add_text(mod['description'], wrap=300)

    dpg.add_separator(parent="mod_selection_list")
    dpg.configure_item("mod_selection_window", show=True)


def select_mod_for_category(sender, app_data, user_data):
    category = user_data['category']
    mod = user_data['mod']
    on_mod_selected(None, None, {'category': category, 'mod': mod})
    dpg.configure_item("mod_selection_window", show=False)

def create_text_color_theme(color):
    with dpg.theme() as theme_id:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Text, color)
    return theme_id


def update_stats_display():
    stats_text = "Maximum performance:\n"
    stats_text += f"max_dps: {int(context['max_dps'])}\n"
    stats_text += f"max_total_damage: {int(context['max_total_damage'])}\n"
    stats_text += "\nТекущие параметры:\n"
    parameters = {
        "current_ammo": context['current_ammo'],
        "magazine_capacity": dpg.get_value("magazine_capacity_input"),
        "base_damage": dpg.get_value("base_damage_input"),
        "crit_chance": dpg.get_value("crit_chance_input"),
        "crit_dmg": dpg.get_value("crit_dmg_input"),
        "weapon_damage_bonus": dpg.get_value("weapon_damage_bonus_input"),
        "status_damage_bonus": dpg.get_value("status_damage_bonus_input"),
        "fire_rate": dpg.get_value("fire_rate_input"),
    }
    for key, value in parameters.items():
        stats_text += f"{key}: {value}\n"
    if context['mannequin_status_effects']:
        stats_text += "\nСтатусные эффекты:\n"
        for key, value in context['mannequin_status_effects'].items():
            stats_text += f"{key}: {value}\n"
    dpg.set_value("stats_display_text", stats_text)


def show_parameter_changes():
    context['stats_display_timer'] = time.time()
    base_parameters = {
        "base_damage": dpg.get_value("base_damage_input"),
        "crit_chance": dpg.get_value("crit_chance_input"),
        "crit_dmg": dpg.get_value("crit_dmg_input"),
        "weapon_damage_bonus": dpg.get_value("weapon_damage_bonus_input"),
        "status_damage_bonus": dpg.get_value("status_damage_bonus_input"),
        "fire_rate": dpg.get_value("fire_rate_input"),
    }
    context_base = base_parameters.copy()
    context_base.update({
        'hp': dpg.get_value("hp_input"),
        'max_hp': dpg.get_value("hp_input"),
        'damage': base_parameters['base_damage'],
        'crit_rate_percent': base_parameters['crit_chance'],
        'crit_damage_percent': base_parameters['crit_dmg'],
        'selected_mods': context['selected_mods'],
    })
    context_modded = context_base.copy()
    apply_mods(context_modded['selected_mods'], context_modded)
    stats_text = "Изменения параметров:\n"
    color = [255, 255, 255]
    for key in base_parameters:
        base_value = base_parameters[key]
        modded_value = context_modded.get(key, base_value)
        difference = modded_value - base_value
        if difference != 0:
            color = [0, 255, 0] if difference > 0 else [255, 0, 0]
            stats_text += f"{key}: {base_value} "
            stats_text += f"{'+' if difference > 0 else ''}{difference} ({modded_value})\n"
        else:
            stats_text += f"{key}: {base_value}\n"
    dpg.set_value("stats_display_text", stats_text)
    color_theme = create_text_color_theme(color)
    dpg.bind_item_theme("stats_display_text", color_theme)


def create_error_modal(tag, message):
    with dpg.window(label="Ошибка", modal=True, show=False, tag=tag):
        dpg.add_text(message)
        dpg.add_button(label="ОК", callback=lambda: dpg.configure_item(tag, show=False))


def create_default_texture():
    width, height = 85, 85
    data = [255, 255, 255, 255] * width * height  # Белое изображение
    with dpg.texture_registry():
        texture_id = dpg.add_static_texture(width, height, data)
    return texture_id


def load_mod_images():
    mod_images = {}
    # Создаем текстуру по умолчанию
    mod_images['default'] = create_default_texture()
    for category_key, mod_key in category_key_mapping.items():
        category_folder = os.path.join('data', 'icons', 'mods', mod_key)
        if os.path.exists(category_folder):
            mod_images[mod_key] = {}
            for filename in os.listdir(category_folder):
                if filename.endswith('.png'):
                    mod_name = os.path.splitext(filename)[0]
                    image_path = os.path.join(category_folder, filename)
                    width, height, channels, data = dpg.load_image(image_path)
                    with dpg.texture_registry():
                        texture_id = dpg.add_static_texture(width, height, data)
                    mod_images[mod_key][mod_name] = texture_id
    return mod_images


mod_images = load_mod_images()

dpg.create_viewport(title='Редактор и Калькулятор', width=1215, height=860)
with dpg.window(label="Main Window", width=1200, height=825):
    with dpg.tab_bar():
        with dpg.tab(label="Calc"):
            with dpg.group(horizontal=True):
                with dpg.child_window(width=600, height=760, horizontal_scrollbar=True):
                    dpg.add_text("Параметры:")
                    dpg.add_spacer(height=5)
                    dpg.add_separator()
                    dpg.add_spacer(height=5)

                    def create_parameters_table(title, params):
                        dpg.add_text(title, color=[255, 255, 255], bullet=True)
                        with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                            dpg.add_table_column()
                            dpg.add_table_column()
                            for label, default, tag in params:
                                with dpg.table_row():
                                    dpg.add_text(label)
                                    dpg.add_input_int(default_value=default, min_value=0, max_value=100000, step=0,
                                                      width=100, callback=on_parameter_change, tag=tag)
                        dpg.add_spacer(height=5)
                        dpg.add_separator()
                        dpg.add_spacer(height=5)

                    create_parameters_table("Базовые характеристики:", [
                        ("Урон (УРН):", 1000, "base_damage_input"),
                        ("Пси-интенсивность:", 0, "psi_intensity_input"),
                        ("ОЗ (xp):", 10000, "hp_input"),
                        ("Сопротивление загрязнению:", 0, "contamination_resistance_input"),
                    ])

                    create_parameters_table("Боевые характеристики:", [
                        ("Шанс крит. попадания %:", 20, "crit_chance_input"),
                        ("Крит. УРН +%:", 50, "crit_dmg_input"),
                        ("УРН уязвимостям %:", 0, "weakspot_damage_bonus_input"),
                        ("Бонус к УРН оружия %:", 0, "weapon_damage_bonus_input"),
                        ("Бонус к УРН статуса %:", 0, "status_damage_bonus_input"),
                        ("Бонус к УРН обычным %:", 0, "damage_bonus_normal_input"),
                        ("Бонус к УРН элиткам %:", 0, "damage_bonus_elite_input"),
                        ("Бонус к УРН против боссов %:", 0, "damage_bonus_boss_input"),
                        ("Скорость стрельбы (выстр./мин):", 600, "fire_rate_input"),
                        ("Емкость магазина:", 30, "magazine_capacity_input"),
                        ("Скорость перезарядки (сек):", 1, "reload_speed_input"),
                    ])

                    create_parameters_table("Показатели защиты:", [
                        ("Снижение УРН %:", 0, "damage_reduction_input"),
                        ("Сопротивление загрязнению:", 0, "resistance_to_pollution"),
                    ])

                    dpg.add_input_int(label="Врагов в радиусе (м):", default_value=0,
                                      tag="enemies_within_distance_input", width=100)

                    dpg.add_text("Выбор модов:", color=[255, 255, 255], bullet=True)
                    with dpg.group(horizontal=False):
                        for category in mod_categories:
                            unique_tag = f"{category}_mod_selector"
                            parent_tag = f"{unique_tag}_parent"
                            with dpg.group(horizontal=True, tag=parent_tag):
                                selected_mod = next(
                                    (mod for mod in context['selected_mods'] if mod.get('category') == category),
                                    None)
                                if selected_mod:
                                    button_label = selected_mod['name']
                                    texture_id = mod_images.get(category_key_mapping.get(category), {}).get(
                                        selected_mod['name'], None)
                                    if texture_id:
                                        dpg.add_image_button(texture_tag=texture_id, width=85, height=85,
                                                             callback=open_mod_selection, user_data=category,
                                                             tag=unique_tag)
                                    else:
                                        dpg.add_button(label=button_label, callback=open_mod_selection,
                                                       user_data=category, tag=unique_tag)
                                else:
                                    button_label = f"Выберите мод для {category}"
                                    dpg.add_button(label=button_label, callback=open_mod_selection,
                                                   user_data=category, tag=unique_tag)

                    dpg.add_button(label="Показать изменения параметров", callback=show_parameter_changes)

                with dpg.child_window(width=600, height=650) as right_field:
                    with dpg.group(horizontal=False):
                        with dpg.group(horizontal=False):
                            dpg.add_spacer(width=50)
                            dpg.add_combo(items=['Горение', 'Заморозка'], label='Select the superimposed status ', tag="status_combo",
                                          callback=lambda s, a, u: context.update(
                                              {'selected_status': dpg.get_value("status_combo")}), width=150)
                        with dpg.group(horizontal=True):
                            dpg.add_spacer(width=0)
                            dpg.add_text("DPS: 0    Total DMG: 0", color=[0, 0, 255], tag="dps_text")
                            dpg.add_spacer()
                        with dpg.group(horizontal=True):
                            dpg.add_spacer(width=0)
                            dpg.add_text(f"Ammo: {context['current_ammo']}/0", tag="ammo_text")
                            dpg.add_spacer()
                        with dpg.group(horizontal=True):
                            dpg.add_spacer()
                            with dpg.group():
                                if os.path.exists("target_image.png"):
                                    width_img, height_img, channels, data = dpg.load_image("target_image.png")
                                else:
                                    width_img, height_img = 300, 300
                                    data = [255] * width_img * height_img * 4
                                with dpg.texture_registry():
                                    texture_id = dpg.add_static_texture(width_img, height_img, data)
                                with dpg.drawlist(width=300, height=300, tag="damage_layer"):
                                    dpg.draw_image(texture_id, pmin=[0, 0], pmax=[300, 300])
                                    dpg.draw_rectangle(pmin=[90, 50], pmax=[210, 290], color=[0, 0, 255, 100],
                                                       fill=[0, 0, 255, 50])
                                    dpg.draw_rectangle(pmin=[130, 10], pmax=[170, 50], color=[255, 0, 0, 100],
                                                       fill=[255, 0, 0, 50])
                                    with dpg.item_handler_registry() as handler_id:
                                        dpg.add_item_clicked_handler(callback=mouse_down_callback)
                                        dpg.add_item_deactivated_handler(callback=mouse_up_callback)
                                    dpg.bind_item_handler_registry("damage_layer", handler_id)
                            dpg.add_spacer()
                            with dpg.group():
                                dpg.add_text("", tag="stats_display_text")
                        with dpg.group(horizontal=True):
                            dpg.add_spacer()
                            dpg.add_combo(items=['Обычный', 'Элитный', 'Boss'], label='Enemy type',
                                          tag="enemy_type_combo", width=150)
            initialize()
            with dpg.window(label="Выбор мода", modal=True, show=False, tag="mod_selection_window", width=600,
                            height=500):
                dpg.add_text("Выберите мод:")
                dpg.add_child_window(tag="mod_selection_list", autosize_x=True, autosize_y=True)
                dpg.add_button(label="Закрыть", callback=lambda: dpg.configure_item("mod_selection_window", show=False))
        with dpg.tab(label="Create"):
            dpg.add_text("Введите информацию о модификаторе:", color=[255, 255, 0])
            with dpg.group(horizontal=True):
                dpg.add_combo(mod_categories, label="Категория модификатора", tag="mod_category")
                dpg.add_button(label="+", width=30, callback=add_category)
            dpg.add_input_text(label="Название модификатора", tag="mod_name")
            dpg.add_separator()
            dpg.add_text("Добавьте эффекты модификатора:", color=[255, 255, 0])

            dpg.add_combo(['increase_stat', 'decrease_stat', 'set_flag', 'conditional_effect'], label="Тип эффекта",
                          tag="effect_type")

            with dpg.group(horizontal=True):
                dpg.add_combo(stats_options, label="Стат (если применимо)", tag="effect_stat")
                dpg.add_button(label="+", width=30, callback=lambda: dpg.configure_item("add_stat_window", show=True))
            dpg.add_tooltip("effect_stat")
            with dpg.tooltip("effect_stat"):
                dpg.add_text("Выберите стат для модификации, например, 'damage', 'crit_rate_percent', и т.д.")

            with dpg.group(horizontal=True):
                dpg.add_input_text(label="Значение (если применимо)", tag="effect_value")
            dpg.add_tooltip("effect_value")
            with dpg.tooltip("effect_value"):
                dpg.add_text("Введите значение для выбранного стата.")

            with dpg.group(horizontal=True):
                dpg.add_combo(flags_options, label="Флаг (если применимо)", tag="effect_flag")
                dpg.add_button(label="+", width=30, callback=lambda: dpg.configure_item("add_flag_window", show=True))
            dpg.add_tooltip("effect_flag")
            with dpg.tooltip("effect_flag"):
                dpg.add_text("Выберите флаг для установки или снятия, например, 'can_deal_weakspot_damage'.")

            dpg.add_checkbox(label="Значение флага (если применимо)", tag="effect_flag_value")

            with dpg.group(horizontal=True):
                dpg.add_combo(conditions_options, label="Условие (если применимо)", tag="effect_condition")
                dpg.add_button(label="+", width=30,
                               callback=lambda: dpg.configure_item("add_condition_window", show=True))
            dpg.add_tooltip("effect_condition")
            with dpg.tooltip("effect_condition"):
                dpg.add_text("Введите условие, например, 'hp / max_hp > 0.5'.")

            with dpg.group(horizontal=True):
                dpg.add_button(label="Добавить эффект", callback=add_effect)
                dpg.add_button(label="Завершить условный эффект", callback=end_conditional_effect)
            dpg.add_separator()
            dpg.add_text("Предпросмотр эффектов:", color=[255, 255, 0])
            dpg.add_input_text(multiline=True, readonly=True, width=780, height=200, tag="effects_preview")
            with dpg.group(horizontal=True):
                dpg.add_button(label="Сохранить модификатор", callback=create_mod)
                dpg.add_button(label="Сбросить форму", callback=reset_form)
                dpg.add_button(label="Изменить моды", callback=edit_mods)
            dpg.add_text("", tag="status_text")
            with dpg.window(label="Добавить новую категорию", modal=True, show=False, tag="add_category_window"):
                dpg.add_input_text(label="Название новой категории", tag="new_category_input")
                dpg.add_button(label="Сохранить", callback=save_new_category)
                dpg.add_button(label="Отмена", callback=lambda: dpg.configure_item("add_category_window", show=False))
            with dpg.window(label="Добавить новый стат", modal=True, show=False, tag="add_stat_window"):
                dpg.add_input_text(label="Название нового стата", tag="new_stat_input")
                dpg.add_button(label="Сохранить", callback=add_new_stat)
                dpg.add_button(label="Отмена", callback=lambda: dpg.configure_item("add_stat_window", show=False))
            with dpg.window(label="Добавить новый флаг", modal=True, show=False, tag="add_flag_window"):
                dpg.add_input_text(label="Название нового флага", tag="new_flag_input")
                dpg.add_button(label="Сохранить", callback=add_new_flag)
                dpg.add_button(label="Отмена", callback=lambda: dpg.configure_item("add_flag_window", show=False))
            with dpg.window(label="Добавить новое условие", modal=True, show=False, tag="add_condition_window"):
                dpg.add_input_text(label="Новое условие", tag="new_condition_input")
                dpg.add_button(label="Сохранить", callback=add_new_condition)
                dpg.add_button(label="Отмена", callback=lambda: dpg.configure_item("add_condition_window", show=False))
            with dpg.window(label="Редактировать Моды", modal=True, show=False, tag="edit_mods_window", width=400,
                            height=500):
                dpg.add_child_window(tag="mods_list", autosize_x=True, autosize_y=True)
                dpg.add_button(label="Закрыть", callback=lambda: dpg.configure_item("edit_mods_window", show=False))
            create_error_modal("error_modal_effect", "Пожалуйста, заполните все необходимые поля эффекта.")
            create_error_modal("error_modal_end_conditional", "Нет условных эффектов для завершения.")
            create_error_modal("error_modal_name", "Пожалуйста, введите название модификатора.")
            create_error_modal("error_modal_category", "Пожалуйста, введите уникальное название категории.")
            create_error_modal("error_modal_stat", "Пожалуйста, введите уникальное название стата.")
            create_error_modal("error_modal_flag", "Пожалуйста, введите уникальное название флага.")
            create_error_modal("error_modal_condition", "Пожалуйста, введите уникальное условие.")

current_mod['effects'] = []
stats_stack.append(current_mod['effects'])
update_effects_preview()

dpg.setup_dearpygui()
if default_font is not None:
    dpg.bind_font(default_font)
dpg.show_viewport()
while dpg.is_dearpygui_running():
    update()
    dpg.render_dearpygui_frame()
dpg.destroy_context()
