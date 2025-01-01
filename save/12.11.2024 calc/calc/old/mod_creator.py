import tkinter as tk
from tkinter import ttk

class ModCreator:
    def __init__(self, parent):
        self.parent = parent
        self.mods = {"mod_helmet": [], "mod_mask": [], "mod_top": [], "mod_gloves": [], "mod_bottoms": [], "mod_shoes": [],
                     "mod_weapon_burn": [], "mod_weapon_frost_vortex": [], "mod_weapon_power_surge": [],
                     "mod_weapon_unstable_bomber": [], "mod_weapon_shrapnel": [], "mod_weapon_fast_gunner": [],
                     "mod_weapon_the_bulrs_eye": [], "mod_weapon_fortress_warfare": [], "mod_weapon_bounce": []}
        self.weapons = {}
        self.armors = {}

        self.create_widgets()

    def create_widgets(self):
        # Выпадающий список для выбора типа предмета
        self.type_var = tk.StringVar()
        type_label = ttk.Label(self.parent, text="Select Type:")
        type_label.grid(column=0, row=0)
        self.type_combobox = ttk.Combobox(self.parent, textvariable=self.type_var)
        self.type_combobox['values'] = ("Weapon", "Armor", "Mod")
        self.type_combobox.grid(column=1, row=0)
        self.type_combobox.bind("<<ComboboxSelected>>", self.update_add_fields)

        # Поле для добавления параметров
        self.fields_frame = ttk.Frame(self.parent)
        self.fields_frame.grid(column=0, row=1, columnspan=2)

        # Кнопка для сохранения
        self.save_button = ttk.Button(self.parent, text="Save", command=self.save_data)
        self.save_button.grid(column=0, row=2, columnspan=2)

    def update_add_fields(self, event):
        for widget in self.fields_frame.winfo_children():
            widget.destroy()

        item_type = self.type_var.get()

        if item_type == "Weapon":
            self.create_weapon_fields()
        elif item_type == "Armor":
            self.create_armor_fields()
        elif item_type == "Mod":
            self.create_mod_fields()

    def create_weapon_fields(self):
        # Поля для ввода характеристик оружия
        ttk.Label(self.fields_frame, text="Weapon Name:").grid(column=0, row=0)
        self.weapon_name_entry = ttk.Entry(self.fields_frame)
        self.weapon_name_entry.grid(column=1, row=0)

        ttk.Label(self.fields_frame, text="Base Damage:").grid(column=0, row=1)
        self.base_damage_entry = ttk.Entry(self.fields_frame)
        self.base_damage_entry.grid(column=1, row=1)

        ttk.Label(self.fields_frame, text="Crit Chance:").grid(column=0, row=2)
        self.crit_chance_entry = ttk.Entry(self.fields_frame)
        self.crit_chance_entry.grid(column=1, row=2)

        ttk.Label(self.fields_frame, text="Crit Damage:").grid(column=0, row=3)
        self.crit_damage_entry = ttk.Entry(self.fields_frame)
        self.crit_damage_entry.grid(column=1, row=3)

    def create_armor_fields(self):
        # Поля для ввода характеристик брони
        ttk.Label(self.fields_frame, text="Armor Name:").grid(column=0, row=0)
        self.armor_name_entry = ttk.Entry(self.fields_frame)
        self.armor_name_entry.grid(column=1, row=0)

        ttk.Label(self.fields_frame, text="Crit Bonus:").grid(column=0, row=1)
        self.crit_bonus_entry = ttk.Entry(self.fields_frame)
        self.crit_bonus_entry.grid(column=1, row=1)

    def create_mod_fields(self):
        # Поля для ввода характеристик модов
        ttk.Label(self.fields_frame, text="Mod Name:").grid(column=0, row=0)
        self.mod_name_entry = ttk.Entry(self.fields_frame)
        self.mod_name_entry.grid(column=1, row=0)

        ttk.Label(self.fields_frame, text="Effect Value:").grid(column=0, row=1)
        self.effect_value_entry = ttk.Entry(self.fields_frame)
        self.effect_value_entry.grid(column=1, row=1)

        ttk.Label(self.fields_frame, text="Condition:").grid(column=0, row=2)
        self.condition_entry = ttk.Entry(self.fields_frame)
        self.condition_entry.grid(column=1, row=2)

    def save_data(self):
        # Логика сохранения данных
        item_type = self.type_var.get()
        if item_type == "Weapon":
            weapon_name = self.weapon_name_entry.get()
            self.weapons[weapon_name] = {
                "Base Damage": float(self.base_damage_entry.get()),
                "Crit Chance": float(self.crit_chance_entry.get()),
                "Crit Damage": float(self.crit_damage_entry.get())
            }
        elif item_type == "Armor":
            armor_name = self.armor_name_entry.get()
            self.armors[armor_name] = {
                "Crit Bonus": float(self.crit_bonus_entry.get())
            }
        elif item_type == "Mod":
            mod_type = "mod_" + self.mod_name_entry.get().split()[0].lower()
            mod_name = self.mod_name_entry.get()
            self.mods[mod_type].append({
                "Mod Name": mod_name,
                "Effect Value": float(self.effect_value_entry.get()),
                "Condition": self.condition_entry.get()
            })
        print("Data saved!")  # Временно для отладки

