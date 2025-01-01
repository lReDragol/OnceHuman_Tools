#файл menu.py

import dearpygui.dearpygui as dpg
import os
import time
import random
import math
import json

from calc import *
from create import *
from calc import base_stats, armor_sets_data, mods_data, items_data, sets_data, multipliers

dpg.create_context()
default_font = None
is_editable = True

with dpg.font_registry():
    font_path = "C:\\Windows\\Fonts\\arial.ttf"
    if os.path.exists(font_path):
        with dpg.font(font_path, 15) as default_font:
            dpg.add_font_range_hint(dpg.mvFontRangeHint_Cyrillic)
    else:
        print("Шрифт Arial не найден. Используется шрифт по умолчанию.")

player = Player()
current_mod = {}
current_mod['effects'] = []
stats_stack = [current_mod['effects']]

items_and_sets_data = {
    'items': items_data,
    'sets': sets_data,
    'multipliers': multipliers
}

context = {
    'total_damage': 0,
    'dps': 0,
    'max_dps': 0,
    'max_total_damage': 0,
    'damage_history': [],
    'mouse_pressed': False,
    'scheduled_deletions': [],
    'hp': dpg.get_value("hp_input"),
    'max_hp': dpg.get_value("hp_input"),
    'enemies_within_distance': dpg.get_value("enemies_within_distance_input"),
    'target_distance': 0,
    'current_ammo': 0,
    'reloading': False,
    'reload_end_time': 0,
    'last_fire_time': time.time(),
    'last_damage_time': time.time(),
    'selected_mods': [],
    'selected_items': {},
    'mannequin_status_effects': {},
    'status_stack_counts': {"Fire": 0},
    'max_fire_stacks': 16,
    'stats_display_timer': 0.0,
    'selected_status': None,
}

def create_default_texture():
    width, height = 85, 85
    data = [255, 255, 255, 255] * width * height
    with dpg.texture_registry():
        texture_id = dpg.add_static_texture(width, height, data)
    return texture_id

def load_mod_images():
    mod_images = {}
    mod_images['default'] = create_default_texture()
    for category_key, mod_key in category_key_mapping.items():
        category_folder = os.path.join('data', 'icons', 'mods', mod_key)
        if os.path.exists(category_folder):
            mod_images[mod_key] = {}
            for filename in os.listdir(category_folder):
                if filename.endswith('.png'):
                    mod_name_key = os.path.splitext(filename)[0].lower()
                    mod_name_key = mod_name_key.replace(' ', '_')
                    image_path = os.path.join(category_folder, filename)
                    width, height, channels, data = dpg.load_image(image_path)
                    with dpg.texture_registry():
                        texture_id = dpg.add_static_texture(width, height, data)
                    mod_images[mod_key][mod_name_key] = texture_id
    return mod_images

def load_item_images():
    item_images = {}
    item_images['default'] = create_default_texture()
    item_icons_folder = os.path.join('data', 'icons', 'armor')
    if os.path.exists(item_icons_folder):
        for root, dirs, files in os.walk(item_icons_folder):
            for filename in files:
                if filename.endswith('.png'):
                    item_id = os.path.splitext(filename)[0]
                    image_path = os.path.join(root, filename)
                    try:
                        width, height, channels, data = dpg.load_image(image_path)
                        with dpg.texture_registry():
                            texture_id = dpg.add_static_texture(width, height, data)
                        item_images[item_id] = texture_id
                    except Exception as e:
                        print(f"Ошибка при загрузке изображения {image_path}: {e}")
    else:
        print(f"Папка {item_icons_folder} не существует.")
    return item_images

mod_images = load_mod_images()
item_images = load_item_images()

def update_effects_preview():
    dpg.set_value("effects_preview", json.dumps(current_mod['effects'], ensure_ascii=False, indent=2))

def add_category_callback(sender, app_data, user_data):
    dpg.configure_item("add_category_window", show=True)

def save_new_category_callback(sender, app_data, user_data):
    new_category = dpg.get_value("new_category_input").strip()
    if add_category(new_category):
        dpg.configure_item("mod_category", items=mod_categories)
        dpg.set_value("new_category_input", "")
        dpg.configure_item("add_category_window", show=False)
    else:
        dpg.configure_item("error_modal_category", show=True)

def add_new_stat_callback(sender, app_data, user_data):
    dpg.configure_item("add_stat_window", show=True)

def save_new_stat_callback(sender, app_data, user_data):
    new_stat = dpg.get_value("new_stat_input").strip()
    if add_new_stat(new_stat):
        dpg.configure_item("effect_stat", items=stats_options)
        dpg.set_value("new_stat_input", "")
        dpg.configure_item("add_stat_window", show=False)
    else:
        dpg.configure_item("error_modal_stat", show=True)

def add_new_flag_callback(sender, app_data, user_data):
    dpg.configure_item("add_flag_window", show=True)

def save_new_flag_callback(sender, app_data, user_data):
    new_flag = dpg.get_value("new_flag_input").strip()
    if add_new_flag(new_flag):
        dpg.configure_item("effect_flag", items=flags_options)
        dpg.set_value("new_flag_input", "")
        dpg.configure_item("add_flag_window", show=False)
    else:
        dpg.configure_item("error_modal_flag", show=True)

def add_new_condition_callback(sender, app_data, user_data):
    dpg.configure_item("add_condition_window", show=True)

def save_new_condition_callback(sender, app_data, user_data):
    new_condition = dpg.get_value("new_condition_input").strip()
    if add_new_condition(new_condition):
        dpg.configure_item("effect_condition", items=conditions_options)
        dpg.set_value("new_condition_input", "")
        dpg.configure_item("add_condition_window", show=False)
    else:
        dpg.configure_item("error_modal_condition", show=True)

def add_effect_callback(sender, app_data, user_data):
    effect_type = dpg.get_value("effect_type")
    effect_stat = dpg.get_value("effect_stat")
    effect_value = dpg.get_value("effect_value")
    effect_flag = dpg.get_value("effect_flag")
    effect_flag_value = dpg.get_value("effect_flag_value")
    effect_condition = dpg.get_value("effect_condition")
    success, message = add_effect(
        effect_type, effect_stat, effect_value, effect_flag, effect_flag_value,
        effect_condition, current_mod, stats_stack
    )
    if success:
        update_effects_preview()
    else:
        dpg.configure_item("error_modal_effect", show=True)

def end_conditional_effect_callback(sender, app_data, user_data):
    success, message = end_conditional_effect(stats_stack)
    if success:
        update_effects_preview()
    else:
        dpg.configure_item("error_modal_end_conditional", show=True)

def create_mod_callback(sender, app_data, user_data):
    mod_name = dpg.get_value("mod_name").strip()
    mod_category = dpg.get_value("mod_category").strip()
    success, message = create_mod(mod_name, mod_category, current_mod['effects'], mods_data)
    if success:
        dpg.set_value("status_text", message)
        reset_mod_form(current_mod, stats_stack)
        update_effects_preview()
    else:
        dpg.set_value("status_text", message)

def reset_form_callback(sender, app_data, user_data):
    reset_mod_form(current_mod, stats_stack)
    update_effects_preview()
    dpg.set_value("mod_name", "")
    dpg.set_value("effect_type", "")
    dpg.set_value("effect_stat", "")
    dpg.set_value("effect_value", "")
    dpg.set_value("effect_flag", "")
    dpg.set_value("effect_flag_value", False)
    dpg.set_value("effect_condition", "")
    dpg.configure_item("status_text", default_value="", color=[0, 0, 0])

def create_item_callback(sender, app_data, user_data):
    item_name = dpg.get_value("item_name_input").strip()
    item_type = dpg.get_value("item_type_combo").strip()
    item_rarity = dpg.get_value("item_rarity_combo").strip()
    item_set_id = dpg.get_value("item_set_input").strip()
    success, message = create_item(item_name, item_type, item_rarity, item_set_id, items_and_sets_data)
    if success:
        dpg.configure_item("status_text_item", default_value=message, color=[0, 255, 0])
    else:
        dpg.configure_item("status_text_item", default_value=message, color=[255, 0, 0])

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
        dpg.set_value("ammo_text", f"Патроны: {context['current_ammo']}/{magazine_capacity}")
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
    context['is_weak_spot'] = weak_zone[0] <= local_mouse_pos[0] <= weak_zone[2] and weak_zone[1] <= local_mouse_pos[1] <= weak_zone[3]
    if not context['is_weak_spot']:
        if not (normal_zone[0] <= local_mouse_pos[0] <= normal_zone[2] and normal_zone[1] <= local_mouse_pos[1] <= normal_zone[3]):
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
    context['hp'] = dpg.get_value("hp_input")
    context['max_hp'] = context['hp']
    context['enemies_within_distance'] = dpg.get_value("enemies_within_distance_input")

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
    dpg.set_value("ammo_text", f"Патроны: {context['current_ammo']}/{magazine_capacity}")
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
    if sender == "hp_input":
        context['hp'] = dpg.get_value("hp_input")
        context['max_hp'] = context['hp']
    elif sender == "enemies_within_distance_input":
        context['enemies_within_distance'] = dpg.get_value("enemies_within_distance_input")

def initialize():
    max_hp_initial = dpg.get_value("hp_input")
    context['max_hp'] = max_hp_initial
    context['hp'] = max_hp_initial
    magazine_capacity = dpg.get_value("magazine_capacity_input")
    context['current_ammo'] = magazine_capacity
    dpg.set_value("ammo_text", f"Патроны: {context['current_ammo']}/{magazine_capacity}")

def create_text_color_theme(color):
    with dpg.theme() as theme_id:
        with dpg.theme_component(dpg.mvAll):
            dpg.add_theme_color(dpg.mvThemeCol_Text, color)
    return theme_id

def update_stats_display():
    stats_text = "Текущие параметры персонажа:\n\n"
    player.recalculate_stats(context)
    stats_text += f"Максимальный DPS: {int(context['max_dps'])}\n"
    stats_text += f"Максимальный общий урон: {int(context['max_total_damage'])}\n\n"
    stats_text += f"HP: {context['hp']}/{context['max_hp']}\n"
    stats_to_display = [
        'hp', 'max_hp', 'damage', 'crit_rate_percent', 'crit_damage_percent',
        'weapon_damage_percent', 'status_damage_percent', 'movement_speed_percent',
        'elemental_damage_percent', 'weakspot_damage_percent', 'reload_speed_percent',
        'magazine_capacity_percent', 'damage_bonus_normal', 'damage_bonus_elite',
        'damage_bonus_boss', 'pollution_resist', 'psi_intensity'
    ]
    for stat in stats_to_display:
        value = player.stats.get(stat, context.get(stat, 0))
        stats_text += f"{stat}: {value}\n"
    stats_text += "\nЭкипированные предметы:\n"
    for item_type, item in player.equipped_items.items():
        stats_text += f"{item.name} ({item_type.capitalize()}): Звёзд: {item.star}, Уровень: {item.level}, Калибровка: {item.calibration}\n"
        item_stats = item.get_stats()
        for stat_name, stat_value in item_stats.items():
            stats_text += f"  {stat_name}: {stat_value}\n"
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
        dpg.add_button(label="Закрыть", callback=lambda: dpg.configure_item(tag, show=False))

def toggle_creation_menu(selected_value):
    if selected_value == "Мод":
        dpg.configure_item("mod_creation_group", show=True)
        dpg.configure_item("item_creation_group", show=False)
    else:
        dpg.configure_item("mod_creation_group", show=False)
        dpg.configure_item("item_creation_group", show=True)

def open_item_selection(sender, app_data, user_data):
    item_type = user_data
    dpg.delete_item("item_selection_list", children_only=True)
    items = [item for item in items_data if item['type'] == item_type]
    dpg.add_button(label="Ничего/Убрать", callback=remove_item_from_slot, user_data=item_type, parent="item_selection_list")
    with dpg.table(header_row=False, parent="item_selection_list"):
        dpg.add_table_column(width=160)
        dpg.add_table_column()
        for item in items:
            item_name = item['name']
            item_id = item['id']
            texture_id = item_images.get(item_id, item_images['default'])
            with dpg.table_row():
                dpg.add_image_button(texture_id, width=150, height=70, callback=select_item_for_slot,
                                     user_data={'item': item, 'type': item_type})
                dpg.add_button(label=item_name, callback=select_item_for_slot,
                               user_data={'item': item, 'type': item_type})
    dpg.configure_item("item_selection_window", show=True)

def open_mod_selection(sender, app_data, user_data):
    item_type = user_data
    dpg.delete_item("mod_selection_list", children_only=True)
    mod_key = category_key_mapping.get(item_type, 'mod_weapon')
    mods = mods_data.get(mod_key, [])
    dpg.add_button(label="Ничего/Убрать", callback=remove_mod_from_slot, user_data=item_type, parent="mod_selection_list")
    with dpg.table(header_row=False, resizable=True, policy=dpg.mvTable_SizingStretchProp, parent="mod_selection_list"):
        dpg.add_table_column(width=60)
        dpg.add_table_column(width=150)
        dpg.add_table_column()
        for mod in mods:
            mod_name = mod['name']
            mod_name_key = mod_name.lower().replace(' ', '_')
            texture_id = mod_images.get(mod_key, {}).get(mod_name_key, mod_images['default'])
            with dpg.table_row():
                dpg.add_image_button(texture_id, width=50, height=50, callback=select_mod_for_slot,
                                     user_data={'mod': mod, 'type': item_type})
                dpg.add_button(label=mod_name, callback=select_mod_for_slot,
                               user_data={'mod': mod, 'type': item_type})
                if 'description' in mod:
                    dpg.add_text(mod['description'], wrap=300)
    dpg.configure_item("mod_selection_window", show=True)

def select_mod_for_slot(sender, app_data, user_data):
    mod = user_data['mod']
    item_type = user_data['type']
    player.equip_mod(mod, context)
    context['selected_mods'].append(mod)
    mod_button_tag = f"{item_type}_mod_selector"
    mod_key = category_key_mapping.get(item_type, 'mod_weapon')
    mod_name_key = mod['name'].lower().replace(' ', '_')
    texture_id = mod_images.get(mod_key, {}).get(mod_name_key, mod_images['default'])
    parent = dpg.get_item_parent(mod_button_tag)
    dpg.delete_item(mod_button_tag)
    dpg.add_image_button(texture_id, width=50, height=50, callback=open_mod_selection,
                         user_data=item_type, tag=mod_button_tag, parent=parent)
    dpg.configure_item("mod_selection_window", show=False)
    update_stats_display()

def select_mod_callback(sender, app_data, user_data):
    mod = user_data
    dpg.set_value("mod_name", mod.get('name', ''))
    dpg.set_value("mod_category", mod.get('category', ''))
    current_mod.clear()
    current_mod.update(mod)
    stats_stack.clear()
    stats_stack.append(current_mod['effects'])
    update_effects_preview()
    dpg.set_value("effect_type", "")
    dpg.set_value("effect_stat", "")
    dpg.set_value("effect_value", "")
    dpg.set_value("effect_flag", "")
    dpg.set_value("effect_flag_value", False)
    dpg.set_value("effect_condition", "")
    dpg.configure_item("edit_mods_window", show=False)

def remove_item_from_slot(sender, app_data, user_data):
    item_type = user_data
    if item_type in player.equipped_items:
        del player.equipped_items[item_type]
    if item_type in context['selected_items']:
        del context['selected_items'][item_type]
    button_tag = f"{item_type}_item_selector"
    dpg.configure_item(button_tag, label=f"Выберите {item_type.capitalize()}")
    group_tag = f"{item_type}_upgrade_group"
    if dpg.does_item_exist(group_tag):
        dpg.delete_item(group_tag)
    mod_button_tag = f"{item_type}_mod_selector"
    if dpg.does_item_exist(mod_button_tag):
        dpg.delete_item(mod_button_tag)
    dpg.configure_item("item_selection_window", show=False)
    update_stats_display()

def remove_mod_from_slot(sender, app_data, user_data):
    item_type = user_data
    context['selected_mods'] = [mod for mod in context['selected_mods'] if mod.get('category') != item_type]
    player.remove_mod(item_type)
    mod_button_tag = f"{item_type}_mod_selector"
    dpg.configure_item(mod_button_tag, label=f"Выберите мод для {item_type.capitalize()}")
    dpg.configure_item("mod_selection_window", show=False)
    update_stats_display()

def select_item_for_slot(sender, app_data, user_data):
    try:
        item_data = user_data['item']
        item_type = user_data['type']
        item = Item(item_data, base_stats, items_and_sets_data['multipliers'])
        context['selected_items'][item_type] = item
        player.equip_item(item, context)
        button_tag = f"{item_type}_item_selector"
        dpg.configure_item(button_tag, label=item.name)
        dpg.configure_item("item_selection_window", show=False)
        group_tag = f"{item_type}_upgrade_group"
        if dpg.does_item_exist(group_tag):
            dpg.delete_item(group_tag)
        with dpg.group(horizontal=True, tag=group_tag, parent=f"{item_type}_item_mod_group"):
            with dpg.group():
                dpg.add_text(f"{item.name} ({item_type.capitalize()})")
                dpg.add_slider_int(label="Количество звёзд", min_value=1, max_value=item.max_stars,
                                   default_value=item.star, callback=update_item_stats,
                                   user_data={'item': item, 'item_type': item_type}, tag=f"{item_type}_star_slider")
                dpg.add_slider_int(label="Уровень", min_value=1, max_value=5,
                                   default_value=item.level, callback=update_item_stats,
                                   user_data={'item': item, 'item_type': item_type}, tag=f"{item_type}_level_slider")
                dpg.add_slider_int(label="Уровень калибровки", min_value=0, max_value=item.get_max_calibration(),
                                   default_value=item.calibration, callback=update_item_stats,
                                   user_data={'item': item, 'item_type': item_type}, tag=f"{item_type}_calibration_slider")
        mod_button_tag = f"{item_type}_mod_selector"
        if dpg.does_item_exist(mod_button_tag):
            dpg.delete_item(mod_button_tag)
        dpg.add_button(label=f"Выберите мод для {item_type.capitalize()}", callback=open_mod_selection,
                       user_data=item_type, tag=mod_button_tag, parent=f"{item_type}_item_mod_group")
        update_stats_display()
    except Exception as e:
        print(f"Ошибка при выборе предмета для слота: {e}")

def update_item_stats(sender, app_data, user_data):
    item = user_data['item']
    item_type = user_data['item_type']
    star_slider_tag = f"{item_type}_star_slider"
    level_slider_tag = f"{item_type}_level_slider"
    calibration_slider_tag = f"{item_type}_calibration_slider"
    new_star = dpg.get_value(star_slider_tag)
    new_level = dpg.get_value(level_slider_tag)
    new_calibration = dpg.get_value(calibration_slider_tag)
    item.star = new_star
    item.level = new_level
    item.calibration = new_calibration
    level_str = str(item.level)
    base_values = item.base_stats_data.get('levels', {}).get(level_str, {})
    if not base_values:
        dpg.configure_item(level_slider_tag, default_value=1)
        item.level = 1
        base_values = item.base_stats_data.get('levels', {}).get('1', {})
        if not base_values:
            raise ValueError(f"No base values for level {item.level}")
    player.equip_item(item, context)
    max_calibration = item.get_max_calibration()
    dpg.configure_item(calibration_slider_tag, max_value=max_calibration)
    if new_calibration > max_calibration:
        new_calibration = max_calibration
        dpg.set_value(calibration_slider_tag, new_calibration)
        item.calibration = new_calibration
    update_stats_display()

def edit_mods_callback(sender, app_data, user_data):
    dpg.delete_item("mods_list", children_only=True)
    mods_data = load_mods()
    for category_display_name, mod_key in category_key_mapping.items():
        mods = mods_data.get(mod_key, [])
        if mods:
            dpg.add_text(f"Категория: {category_display_name}", parent="mods_list")
            for mod in mods:
                mod_name = mod['name']
                with dpg.group(horizontal=True, parent="mods_list"):
                    dpg.add_button(label=mod_name, callback=select_mod_callback,
                                   user_data=mod)
                    dpg.add_button(label="Удалить", callback=delete_mod_callback,
                                   user_data={'mod': mod, 'mod_key': mod_key})
            dpg.add_separator(parent="mods_list")
    dpg.configure_item("edit_mods_window", show=True)

def delete_mod_callback(sender, app_data, user_data):
    mod = user_data['mod']
    mod_key = user_data['mod_key']
    success, message = delete_mod(mod, mod_key, load_mods())
    if success:
        edit_mods_callback(None, None, None)
    else:
        dpg.set_value("status_text", message)

def run():
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
                            with dpg.collapsing_header(label=title, default_open=False):
                                with dpg.table(header_row=False, resizable=False, policy=dpg.mvTable_SizingFixedFit):
                                    dpg.add_table_column()
                                    dpg.add_table_column()
                                    for label, default, tag, editable in params:
                                        with dpg.table_row():
                                            dpg.add_text(label)
                                            dpg.add_input_int(
                                                default_value=default, min_value=0, max_value=9999999,
                                                step=0, width=100, callback=on_parameter_change, tag=tag,
                                                enabled=editable
                                            )
                            dpg.add_spacer(height=5)
                            dpg.add_separator()
                            dpg.add_spacer(height=5)
                        create_parameters_table("Базовые характеристики:", [
                            ("Урон (УРН):", 0, "base_damage_input", is_editable),
                            ("Пси-интенсивность:", 125, "psi_intensity_input", is_editable),
                            ("ОЗ (xp):", 700, "hp_input", is_editable),
                            ("Сопротивление загрязнению:", 15, "contamination_resistance_input", is_editable),
                        ])
                        create_parameters_table("Боевые характеристики:", [
                            ("Шанс крит. попадания %:", 0, "crit_chance_input", is_editable),
                            ("Крит. УРН +%:", 0, "crit_dmg_input", is_editable),
                            ("УРН уязвимостям %:", 0, "weakspot_damage_bonus_input", is_editable),
                            ("Бонус к УРН оружия %:", 0, "weapon_damage_bonus_input", is_editable),
                            ("Бонус к УРН статуса %:", 4, "status_damage_bonus_input", is_editable),
                            ("Бонус к УРН обычным %:", 0, "damage_bonus_normal_input", is_editable),
                            ("Бонус к УРН элиткам %:", 0, "damage_bonus_elite_input", is_editable),
                            ("Бонус к УРН против боссов %:", 0, "damage_bonus_boss_input", is_editable),
                            ("Скорость стрельбы (выстр./мин):", 0, "fire_rate_input", is_editable),
                            ("Емкость магазина:", 0, "magazine_capacity_input", is_editable),
                            ("Скорость перезарядки (сек):", 0, "reload_speed_input", is_editable),
                        ])
                        create_parameters_table("Показатели защиты:", [
                            ("Снижение УРН %:", 0, "damage_reduction_input", is_editable),
                            ("Сопротивление загрязнению:", 15, "resistance_to_pollution", is_editable),
                        ])
                        dpg.add_input_int(label="Врагов в радиусе (м):", default_value=0,
                                          tag="enemies_within_distance_input", width=100)
                        dpg.add_text("Выбор брони:", color=[255, 255, 255], bullet=True)
                        with dpg.group(horizontal=False, tag="armor_selection_group"):
                            armor_types = ['helmet', 'mask', 'top', 'gloves', 'pants', 'boots']
                            for armor_type in armor_types:
                                with dpg.group(horizontal=True, tag=f"{armor_type}_item_mod_group"):
                                    button_tag = f"{armor_type}_item_selector"
                                    item_type_name = armor_type.capitalize()
                                    dpg.add_button(label=f"Выберите {item_type_name}", callback=open_item_selection,
                                                   user_data=armor_type, tag=button_tag)
                        with dpg.group(horizontal=False, tag="armor_mods_group"):
                            pass
                    with dpg.child_window(width=600, height=760):
                        with dpg.group(horizontal=False):
                            dpg.add_spacer(height=10)
                            dpg.add_combo(items=['Горение', 'Заморозка'], label='Выберите статус', tag="status_combo",
                                          callback=lambda s, a, u: context.update(
                                              {'selected_status': dpg.get_value("status_combo")}), width=150)
                            dpg.add_combo(items=['Обычный', 'Элитный', 'Босс'], label='Тип врага', tag="enemy_type_combo",
                                          width=150, default_value='Обычный')
                            dpg.add_text("DPS: 0    Total DMG: 0", color=[0, 0, 255], tag="dps_text")
                            dpg.add_text(f"Патроны: {context['current_ammo']}/0", tag="ammo_text")
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
                            dpg.add_text("", tag="stats_display_text")
            with dpg.tab(label="Create"):
                dpg.add_text("Выберите, что вы хотите создать:", color=[255, 255, 0])
                dpg.add_radio_button(items=["Мод", "Предмет"], default_value="Мод", horizontal=True,
                                     callback=lambda s, a, u: toggle_creation_menu(a))
                with dpg.group(tag="mod_creation_group", show=True):
                    dpg.add_text("Введите информацию о модификаторе:", color=[255, 255, 0])
                    with dpg.group(horizontal=True):
                        dpg.add_combo(mod_categories, label="Категория модификатора", tag="mod_category")
                        dpg.add_button(label="+", width=30, callback=add_category_callback)
                    dpg.add_input_text(label="Название модификатора", tag="mod_name")
                    dpg.add_separator()
                    dpg.add_text("Добавьте эффекты модификатора:", color=[255, 255, 0])
                    dpg.add_combo(['increase_stat', 'decrease_stat', 'set_flag', 'conditional_effect'], label="Тип эффекта",
                                  tag="effect_type")
                    with dpg.group(horizontal=True):
                        dpg.add_combo(stats_options, label="Стат (если применимо)", tag="effect_stat")
                        dpg.add_button(label="+", width=30, callback=add_new_stat_callback)
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
                        dpg.add_button(label="+", width=30, callback=add_new_flag_callback)
                    dpg.add_tooltip("effect_flag")
                    with dpg.tooltip("effect_flag"):
                        dpg.add_text("Выберите флаг для установки или снятия, например, 'can_deal_weakspot_damage'.")
                    dpg.add_checkbox(label="Значение флага (если применимо)", tag="effect_flag_value")
                    with dpg.group(horizontal=True):
                        dpg.add_combo(conditions_options, label="Условие (если применимо)", tag="effect_condition")
                        dpg.add_button(label="+", width=30, callback=add_new_condition_callback)
                    dpg.add_tooltip("effect_condition")
                    with dpg.tooltip("effect_condition"):
                        dpg.add_text("Введите условие, например, 'hp / max_hp > 0.5'.")
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="Добавить эффект", callback=add_effect_callback)
                        dpg.add_button(label="Завершить условный эффект", callback=end_conditional_effect_callback)
                    dpg.add_separator()
                    dpg.add_text("Предпросмотр эффектов:", color=[255, 255, 0])
                    dpg.add_input_text(multiline=True, readonly=True, width=780, height=200, tag="effects_preview")
                    with dpg.group(horizontal=True):
                        dpg.add_button(label="Сохранить модификатор", callback=create_mod_callback)
                        dpg.add_button(label="Сбросить форму", callback=reset_form_callback)
                        dpg.add_button(label="Изменить моды", callback=edit_mods_callback)
                    dpg.add_text("", tag="status_text")
                    with dpg.window(label="Добавить новую категорию", modal=True, show=False, tag="add_category_window"):
                        dpg.add_input_text(label="Название новой категории", tag="new_category_input")
                        dpg.add_button(label="Сохранить", callback=save_new_category_callback)
                        dpg.add_button(label="Отмена",
                                       callback=lambda: dpg.configure_item("add_category_window", show=False))
                    with dpg.window(label="Добавить новый стат", modal=True, show=False, tag="add_stat_window"):
                        dpg.add_input_text(label="Название нового стата", tag="new_stat_input")
                        dpg.add_button(label="Сохранить", callback=save_new_stat_callback)
                        dpg.add_button(label="Отмена", callback=lambda: dpg.configure_item("add_stat_window", show=False))
                    with dpg.window(label="Добавить новый флаг", modal=True, show=False, tag="add_flag_window"):
                        dpg.add_input_text(label="Название нового флага", tag="new_flag_input")
                        dpg.add_button(label="Сохранить", callback=save_new_flag_callback)
                        dpg.add_button(label="Отмена", callback=lambda: dpg.configure_item("add_flag_window", show=False))
                    with dpg.window(label="Добавить новое условие", modal=True, show=False, tag="add_condition_window"):
                        dpg.add_input_text(label="Новое условие", tag="new_condition_input")
                        dpg.add_button(label="Сохранить", callback=save_new_condition_callback)
                        dpg.add_button(label="Отмена", callback=lambda: dpg.configure_item("add_condition_window", show=False))
                    with dpg.window(label="Редактировать Моды", modal=True, show=False, tag="edit_mods_window",
                                    width=600, height=500):
                        dpg.add_text("Список модов:")
                        dpg.add_child_window(tag="mods_list", autosize_x=True, autosize_y=True)
                        dpg.add_button(label="Закрыть",
                                       callback=lambda: dpg.configure_item("edit_mods_window", show=False))
                    create_error_modal("error_modal_effect", "Пожалуйста, заполните все необходимые поля эффекта.")
                    create_error_modal("error_modal_end_conditional", "Нет условных эффектов для завершения.")
                    create_error_modal("error_modal_name", "Пожалуйста, введите название модификатора.")
                    create_error_modal("error_modal_category", "Пожалуйста, введите уникальное название категории.")
                    create_error_modal("error_modal_stat", "Пожалуйста, введите уникальное название стата.")
                    create_error_modal("error_modal_flag", "Пожалуйста, введите уникальное название флага.")
                    create_error_modal("error_modal_condition", "Пожалуйста, введите уникальное условие.")
                with dpg.group(show=False, tag="item_creation_group"):
                    dpg.add_input_text(label="Название предмета", tag="item_name_input")
                    dpg.add_combo(items=["helmet", "mask", "top", "gloves", "pants", "boots"], label="Тип предмета",
                                  tag="item_type_combo")
                    dpg.add_combo(items=["legendary", "epic", "rare", "common"], label="Редкость", tag="item_rarity_combo")
                    dpg.add_input_text(label="ID сета (если применимо)", tag="item_set_input")
                    dpg.add_button(label="Создать предмет", callback=create_item_callback)
                    dpg.add_text("", tag="status_text_item")
                    create_error_modal("error_modal_item", "Пожалуйста, заполните все поля для создания предмета.")
    with dpg.window(label="Выбор предмета", modal=True, show=False, tag="item_selection_window", width=600, height=500):
        dpg.add_text("Выберите предмет:")
        dpg.add_child_window(tag="item_selection_list", autosize_x=True, autosize_y=True)
        dpg.add_button(label="Закрыть", callback=lambda: dpg.configure_item("item_selection_window", show=False))
    with dpg.window(label="Выбор мода", modal=True, show=False, tag="mod_selection_window", width=600, height=500):
        dpg.add_text("Выберите мод:")
        dpg.add_child_window(tag="mod_selection_list", autosize_x=True, autosize_y=True)
        dpg.add_button(label="Закрыть", callback=lambda: dpg.configure_item("mod_selection_window", show=False))
    dpg.setup_dearpygui()
    if default_font is not None:
        dpg.bind_font(default_font)
    dpg.show_viewport()
    initialize()
    while dpg.is_dearpygui_running():
        update()
        dpg.render_dearpygui_frame()
    dpg.destroy_context()

if __name__ == "__main__":
    run()
