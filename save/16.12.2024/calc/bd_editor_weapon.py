import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from tkinter.scrolledtext import ScrolledText
import json
import os
from pygments.lexers import JsonLexer
from pygments.token import Token

DB_FILE = "weapon_list.json"
MAX_RELOAD_SPEED = 69
MIN_RELOAD_TIME = 1.8
RELOAD_TIME_RANGE = 4.0 - MIN_RELOAD_TIME

def load_database():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            for weapon in data.get("weapons", []):
                base_stats = weapon.get("base_stats", {})
                if "reload_speed_points" not in base_stats:
                    pass
            return data
    return {"weapons": []}


def save_database(data):
    with open(DB_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)

class WeaponManager:
    def __init__(self, root):
        self.db = load_database()
        self.root = root
        self.root.title("BD editor weapon")
        self.root.geometry("1400x800")
        self.setup_dark_theme()
        self.main_frame = tk.Frame(root, bg="#2E2E2E")
        self.main_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        self.fields_frame = tk.LabelFrame(self.main_frame, text="Edit Weapon", fg="white", bg="#2E2E2E")
        self.fields_frame.grid(row=0, column=0, rowspan=2, padx=(0, 20), pady=5, sticky="nsew")
        self.fields = {}
        field_labels = [
            ("ID", "string"), ("Name", "string"), ("Type", "string"), ("Rarity", "string"),
            ("Damage per Projectile", "number"), ("Projectiles per Shot", "number"),
            ("Fire Rate", "number"), ("Magazine Capacity", "number"),
            ("Crit Chance (%)", "number"), ("Crit Damage (%)", "number"),
            ("Weakspot Damage (%)", "number"), ("Stability", "number"),
            ("Accuracy", "number"), ("Range", "number"),
            ("Reload Speed Points", "number"),
            ("Reload Time (sec)", "float")
        ]
        for i, (label, field_type) in enumerate(field_labels):
            tk.Label(self.fields_frame, text=label + ":", fg="white", bg="#2E2E2E").grid(row=i, column=0, sticky="w", pady=2, padx=5)
            if label == "Type":
                entry = ttk.Combobox(self.fields_frame, values=["Pistol", "Shotgun", "SMGs", "Assault Rifle", "Sniper Rifle", "LMGs", "Crossbow", "Heavy Artillery", "Melee"], state="readonly")
            elif label == "Rarity":
                entry = ttk.Combobox(self.fields_frame, values=["common", "fine", "rare", "epic", "legendary"], state="readonly")
            else:
                entry = tk.Entry(self.fields_frame, bg="#4F4F4F", fg="white", insertbackground="white")
                if field_type == "number":
                    entry.config(validate="key", validatecommand=(self.root.register(self.validate_number), "%P"))
                elif field_type == "float":
                    entry.config(validate="key", validatecommand=(self.root.register(self.validate_float), "%P"))
            entry.grid(row=i, column=1, pady=2, padx=5, sticky="ew")
            self.fields[label] = entry
        self.fields_frame.columnconfigure(1, weight=1)
        tk.Label(self.fields_frame, text="Mechanics Description:", fg="white", bg="#2E2E2E").grid(row=len(field_labels), column=0, sticky="w", pady=2, padx=5)
        self.mechanics_description = tk.Text(self.fields_frame, width=50, height=5, bg="#4F4F4F", fg="white", insertbackground="white")
        self.mechanics_description.grid(row=len(field_labels), column=1, pady=5, padx=5, sticky="ew")
        tk.Label(self.fields_frame, text="Mechanics Logic (JSON):", fg="white", bg="#2E2E2E").grid(row=len(field_labels)+1, column=0, sticky="w", pady=2, padx=5)
        self.mechanics_logic = ScrolledText(self.fields_frame, width=50, height=10, bg="#4F4F4F", fg="white", insertbackground="white")
        self.mechanics_logic.grid(row=len(field_labels)+1, column=1, pady=5, padx=5, sticky="ew")
        self.mechanics_logic.tag_configure("key", foreground="cyan")
        self.mechanics_logic.tag_configure("string", foreground="lightgreen")
        self.mechanics_logic.tag_configure("number", foreground="orange")
        self.mechanics_logic.tag_configure("boolean", foreground="violet")
        button_frame = tk.Frame(self.fields_frame, bg="#2E2E2E")
        button_frame.grid(row=len(field_labels)+2, column=0, columnspan=2, pady=10)
        self.add_button = tk.Button(button_frame, text="Add Weapon", command=self.add_weapon, bg="#3E3E3E", fg="white")
        self.add_button.pack(side=tk.LEFT, padx=5)
        self.update_button = tk.Button(button_frame, text="Update Weapon", command=self.update_weapon, bg="#3E3E3E", fg="white")
        self.update_button.pack(side=tk.LEFT, padx=5)
        self.json_button = tk.Button(button_frame, text="Add JSON", command=self.add_json_block, bg="#3E3E3E", fg="white")
        self.json_button.pack(side=tk.LEFT, padx=5)
        mass_button_frame = tk.Frame(self.fields_frame, bg="#2E2E2E")
        mass_button_frame.grid(row=len(field_labels)+3, column=0, columnspan=2, pady=10)
        self.mass_edit_button = tk.Button(mass_button_frame, text="Mass Edit", command=self.mass_edit, bg="#3E3E3E", fg="white")
        self.mass_edit_button.pack(side=tk.LEFT, padx=5)
        self.add_param_button = tk.Button(mass_button_frame, text="Add Parameter", command=self.add_parameter, bg="#3E3E3E", fg="white")
        self.add_param_button.pack(side=tk.LEFT, padx=5)
        self.delete_param_button = tk.Button(mass_button_frame, text="Delete Parameter", command=self.delete_parameter, bg="#3E3E3E", fg="white")
        self.delete_param_button.pack(side=tk.LEFT, padx=5)
        self.view_params_button = tk.Button(mass_button_frame, text="View Parameters", command=self.view_parameters, bg="#3E3E3E", fg="white")
        self.view_params_button.pack(side=tk.LEFT, padx=5)
        self.weapon_list_frame = tk.LabelFrame(self.main_frame, text="Weapon List", fg="white", bg="#2E2E2E")
        self.weapon_list_frame.grid(row=0, column=1, rowspan=2, pady=5, sticky="nsew")
        self.weapon_tree = ttk.Treeview(self.weapon_list_frame, columns=("ID", "Reload Time", "Reload Speed Points"), show="tree headings", selectmode="extended")
        self.weapon_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.weapon_tree.heading("#0", text="Weapon Name")
        self.weapon_tree.heading("ID", text="ID")
        self.weapon_tree.heading("Reload Time", text="Reload Time (sec)")
        self.weapon_tree.heading("Reload Speed Points", text="Reload Speed Points")
        self.weapon_tree.column("ID", width=100, anchor="center")
        self.weapon_tree.column("Reload Time", width=150, anchor="center")
        self.weapon_tree.column("Reload Speed Points", width=150, anchor="center")
        self.weapon_tree.bind("<<TreeviewSelect>>", self.load_weapon)
        self.weapon_tree.bind("<Button-3>", self.show_context_menu)
        tree_scroll_y = ttk.Scrollbar(self.weapon_list_frame, orient="vertical", command=self.weapon_tree.yview)
        tree_scroll_y.pack(side=tk.RIGHT, fill='y')
        self.weapon_tree.configure(yscrollcommand=tree_scroll_y.set)
        tree_scroll_x = ttk.Scrollbar(self.weapon_list_frame, orient="horizontal", command=self.weapon_tree.xview)
        tree_scroll_x.pack(side=tk.BOTTOM, fill='x')
        self.weapon_tree.configure(xscrollcommand=tree_scroll_x.set)
        self.weapon_tree.tag_configure("legendary", foreground="gold")
        self.weapon_tree.tag_configure("epic", foreground="#FF69B4")
        self.weapon_tree.tag_configure("rare", foreground="#00BFFF")
        self.weapon_tree.tag_configure("common", foreground="green")
        self.weapon_tree.tag_configure("fine", foreground="#00BFFF")
        # Добавляем кнопку для экспорта логики механик
        export_button = tk.Button(button_frame, text="Export Mechanics", command=self.export_mechanics_logic,
                                  bg="#3E3E3E",
                                  fg="white")
        export_button.pack(side=tk.LEFT, padx=5)
        self.update_weapon_tree()

    def setup_dark_theme(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview",
                        background="#3E3E3E",
                        foreground="white",
                        fieldbackground="#3E3E3E",
                        font=("Segoe UI", 10))
        style.map("Treeview",
                  background=[('selected', '#5A5A5A')],
                  foreground=[('selected', 'white')])
        style.configure("TButton",
                        background="#3E3E3E",
                        foreground="white",
                        font=("Segoe UI", 10))
        style.map("TButton",
                  background=[('active', '#5A5A5A')])
        style.configure("TLabel",
                        background="#2E2E2E",
                        foreground="white",
                        font=("Segoe UI", 10))
        style.configure("TLabelframe",
                        background="#2E2E2E",
                        foreground="white")
        style.configure("TLabelframe.Label",
                        background="#2E2E2E",
                        foreground="white")

    def validate_number(self, value):
        return value.isdigit() or value == ""

    def validate_float(self, value):
        if value == "":
            return True
        try:
            float(value)
            if value.count('.') > 1:
                return False
            return True
        except ValueError:
            return False

    def update_weapon_tree(self):
        for item in self.weapon_tree.get_children():
            self.weapon_tree.delete(item)
        types = {}
        for weapon in self.db["weapons"]:
            weapon_type = weapon.get("type", "Unknown").capitalize()
            if weapon_type not in types:
                types[weapon_type] = []
            types[weapon_type].append(weapon)
        rarity_order = {"legendary": 1, "epic": 2, "rare": 3, "fine": 3, "common": 4}
        for weapon_type in sorted(types.keys()):
            type_id = self.weapon_tree.insert("", "end", text=weapon_type, open=True, tags=("type",))
            sorted_weapons = sorted(types[weapon_type], key=lambda x: rarity_order.get(x.get("rarity", "common").lower(), 99))
            for weapon in sorted_weapons:
                rarity = weapon.get("rarity", "common").lower()
                weapon_name = weapon.get("name", "Unnamed Weapon")
                if rarity in ["rare", "fine"]:
                    tag = "rare"
                else:
                    tag = rarity
                base_stats = weapon.get("base_stats", {})
                reload_time = base_stats.get("reload_time_seconds", 0.0)
                reload_speed_points = base_stats.get("reload_speed_points", 0)
                self.weapon_tree.insert(
                    type_id,
                    "end",
                    text=weapon_name,
                    tags=(tag,),
                    values=(weapon["id"], reload_time, reload_speed_points)
                )

    def load_weapon(self, event):
        selected_items = self.weapon_tree.selection()
        if not selected_items:
            return
        if len(selected_items) > 1:
            self.clear_fields()
            return
        item = selected_items[0]
        parent = self.weapon_tree.parent(item)
        if parent:
            selected_name = self.weapon_tree.item(item, "text")
            for weapon in self.db["weapons"]:
                if weapon["name"] == selected_name:
                    self.fill_fields(weapon)
                    return

    def fill_fields(self, weapon):
        base_stats = weapon.get("base_stats", {})
        for field, entry in self.fields.items():
            entry.delete(0, tk.END)
        self.fields["ID"].insert(0, weapon.get("id", ""))
        self.fields["Name"].insert(0, weapon.get("name", ""))
        self.fields["Type"].set(weapon.get("type", ""))
        self.fields["Rarity"].set(weapon.get("rarity", ""))
        self.fields["Damage per Projectile"].insert(0, base_stats.get("damage_per_projectile", ""))
        self.fields["Projectiles per Shot"].insert(0, base_stats.get("projectiles_per_shot", ""))
        self.fields["Fire Rate"].insert(0, base_stats.get("fire_rate", ""))
        self.fields["Magazine Capacity"].insert(0, base_stats.get("magazine_capacity", ""))
        self.fields["Crit Chance (%)"].insert(0, base_stats.get("crit_rate_percent", ""))
        self.fields["Crit Damage (%)"].insert(0, base_stats.get("crit_damage_percent", ""))
        self.fields["Weakspot Damage (%)"].insert(0, base_stats.get("weakspot_damage_percent", ""))
        self.fields["Stability"].insert(0, base_stats.get("stability", ""))
        self.fields["Accuracy"].insert(0, base_stats.get("accuracy", ""))
        self.fields["Range"].insert(0, base_stats.get("range", ""))
        self.fields["Reload Speed Points"].insert(0, base_stats.get("reload_speed_points", ""))
        self.fields["Reload Time (sec)"].delete(0, tk.END)
        self.fields["Reload Time (sec)"].insert(0, base_stats.get("reload_time_seconds", ""))
        self.mechanics_description.delete("1.0", tk.END)
        self.mechanics_description.insert(tk.END, weapon.get("mechanics", {}).get("description", ""))
        self.highlight_json(weapon.get("mechanics", {}).get("effects", []))

    def clear_fields(self):
        for field, entry in self.fields.items():
            entry.delete(0, tk.END)
        self.mechanics_description.delete("1.0", tk.END)
        self.mechanics_logic.delete("1.0", tk.END)

    def highlight_json(self, json_data):
        self.mechanics_logic.delete("1.0", tk.END)
        if json_data:
            json_text = json.dumps(json_data, indent=4, ensure_ascii=False)
            lexer = JsonLexer()
            tokens = lexer.get_tokens(json_text)
            for token_type, token_value in tokens:
                tag = None
                if token_type in Token.Keyword:
                    tag = "key"
                elif token_type in Token.Literal.String:
                    tag = "string"
                elif token_type in Token.Literal.Number:
                    tag = "number"
                elif token_type in Token.Name.Builtin:
                    tag = "boolean"
                self.mechanics_logic.insert(tk.END, token_value, tag)

    def add_weapon(self):
        new_weapon = self.get_weapon_from_fields()
        if new_weapon:
            for weapon in self.db["weapons"]:
                if weapon["id"] == new_weapon["id"]:
                    messagebox.showerror("Error", "A weapon with this ID already exists.")
                    return
                if weapon["name"] == new_weapon["name"]:
                    messagebox.showerror("Error", "A weapon with this name already exists.")
                    return
            self.db["weapons"].append(new_weapon)
            save_database(self.db)
            self.update_weapon_tree()
            self.clear_fields()
            messagebox.showinfo("Success", "Weapon added!")
        else:
            messagebox.showerror("Error", "Invalid data.")

    def update_weapon(self):
        selected_items = self.weapon_tree.selection()
        if not selected_items:
            messagebox.showerror("Error", "Select a weapon to update.")
            return
        if len(selected_items) > 1:
            messagebox.showerror("Error", "Select only one weapon to update.")
            return
        item = selected_items[0]
        parent = self.weapon_tree.parent(item)
        if not parent:
            messagebox.showerror("Error", "Select a specific weapon, not a type.")
            return
        selected_name = self.weapon_tree.item(item, "text")
        for weapon in self.db["weapons"]:
            if weapon["name"] == selected_name:
                updated_weapon = self.get_weapon_from_fields()
                if updated_weapon:
                    for w in self.db["weapons"]:
                        if w["id"] == updated_weapon["id"] and w != weapon:
                            messagebox.showerror("Error", "Another weapon with this ID already exists.")
                            return
                        if w["name"] == updated_weapon["name"] and w != weapon:
                            messagebox.showerror("Error", "Another weapon with this name already exists.")
                            return
                    self.db["weapons"].remove(weapon)
                    self.db["weapons"].append(updated_weapon)
                    save_database(self.db)
                    self.update_weapon_tree()
                    self.clear_fields()
                    messagebox.showinfo("Success", "Weapon updated!")
                else:
                    messagebox.showerror("Error", "Invalid data.")
                return

    def get_weapon_from_fields(self):
        try:
            mechanics_logic_content = self.mechanics_logic.get("1.0", tk.END).strip()
            if mechanics_logic_content:
                mechanics_effects = json.loads(mechanics_logic_content)
            else:
                mechanics_effects = []
            selected_items = self.weapon_tree.selection()
            description = ""
            if selected_items:
                item = selected_items[0]
                parent = self.weapon_tree.parent(item)
                if parent:
                    selected_name = self.weapon_tree.item(item, "text")
                    for weapon in self.db["weapons"]:
                        if weapon["name"] == selected_name:
                            description = weapon.get("description", "")
                            break
            return {
                "id": self.fields["ID"].get(),
                "name": self.fields["Name"].get(),
                "type": self.fields["Type"].get(),
                "rarity": self.fields["Rarity"].get(),
                "base_stats": {
                    "damage_per_projectile": int(self.fields["Damage per Projectile"].get()),
                    "projectiles_per_shot": int(self.fields["Projectiles per Shot"].get()),
                    "fire_rate": int(self.fields["Fire Rate"].get()),
                    "magazine_capacity": int(self.fields["Magazine Capacity"].get()),
                    "crit_rate_percent": int(self.fields["Crit Chance (%)"].get()),
                    "crit_damage_percent": int(self.fields["Crit Damage (%)"].get()),
                    "weakspot_damage_percent": int(self.fields["Weakspot Damage (%)"].get()),
                    "stability": int(self.fields["Stability"].get()),
                    "accuracy": int(self.fields["Accuracy"].get()),
                    "range": int(self.fields["Range"].get()),
                    "reload_speed_points": int(self.fields["Reload Speed Points"].get()),
                    "reload_time_seconds": float(self.fields["Reload Time (sec)"].get())
                },
                "mechanics": {
                    "description": self.mechanics_description.get("1.0", tk.END).strip(),
                    "effects": mechanics_effects
                },
                "description": description
            }
        except Exception as e:
            messagebox.showerror("Error", f"Data error: {e}")
            return None

    def add_json_block(self):
        top = tk.Toplevel(self.root)
        top.title("Add JSON Block")
        top.geometry("800x600")
        top.configure(bg="#2E2E2E")
        json_text = ScrolledText(top, width=80, height=30, bg="#4F4F4F", fg="white", insertbackground="white")
        json_text.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        json_text.tag_configure("key", foreground="cyan")
        json_text.tag_configure("string", foreground="lightgreen")
        json_text.tag_configure("number", foreground="orange")
        json_text.tag_configure("boolean", foreground="violet")
        def highlight_json_block():
            json_content = json_text.get("1.0", tk.END)
            json_text.tag_remove("key", "1.0", tk.END)
            json_text.tag_remove("string", "1.0", tk.END)
            json_text.tag_remove("number", "1.0", tk.END)
            json_text.tag_remove("boolean", "1.0", tk.END)
            lexer = JsonLexer()
            tokens = lexer.get_tokens(json_content)
            pos = "1.0"
            for token_type, token_value in tokens:
                tag = None
                if token_type in Token.Keyword:
                    tag = "key"
                elif token_type in Token.Literal.String:
                    tag = "string"
                elif token_type in Token.Literal.Number:
                    tag = "number"
                elif token_type in Token.Name.Builtin:
                    tag = "boolean"
                if tag:
                    json_text.tag_add(tag, pos, f"{pos}+{len(token_value)}c")
                pos = json_text.index(f"{pos}+{len(token_value)}c")
        json_text.bind("<KeyRelease>", lambda event: highlight_json_block())
        def save_json():
            try:
                new_weapon = json.loads(json_text.get("1.0", tk.END))
                for weapon in self.db["weapons"]:
                    if weapon["id"] == new_weapon["id"]:
                        messagebox.showerror("Error", "A weapon with this ID already exists.")
                        return
                    if weapon["name"] == new_weapon["name"]:
                        messagebox.showerror("Error", "A weapon with this name already exists.")
                        return
                base_stats = new_weapon.get("base_stats", {})
                if "reload_speed_points" not in base_stats:
                    messagebox.showerror("Error", "JSON block must contain 'reload_speed_points' in 'base_stats'.")
                    return
                if "reload_time_seconds" not in base_stats:
                    messagebox.showerror("Error", "JSON block must contain 'reload_time_seconds' in 'base_stats'.")
                    return
                self.db["weapons"].append(new_weapon)
                save_database(self.db)
                self.update_weapon_tree()
                top.destroy()
                messagebox.showinfo("Success", "JSON block added!")
            except json.JSONDecodeError as e:
                messagebox.showerror("Error", f"Invalid JSON! {e}")
            except Exception as e:
                messagebox.showerror("Error", f"Error adding weapon: {e}")
        save_button = tk.Button(top, text="Save", command=save_json, bg="#3E3E3E", fg="white")
        save_button.pack(pady=5)

    def mass_edit(self):
        selected_items = self.weapon_tree.selection()
        if not selected_items:
            messagebox.showerror("Error", "Select weapons for mass editing.")
            return
        selected_weapons = []
        for item in selected_items:
            parent = self.weapon_tree.parent(item)
            if parent:
                selected_name = self.weapon_tree.item(item, "text")
                for weapon in self.db["weapons"]:
                    if weapon["name"] == selected_name:
                        selected_weapons.append(weapon)
                        break
        if not selected_weapons:
            messagebox.showerror("Error", "Select specific weapons for mass editing.")
            return
        mass_edit_window = tk.Toplevel(self.root)
        mass_edit_window.title("Mass Edit")
        mass_edit_window.geometry("500x400")
        mass_edit_window.configure(bg="#2E2E2E")
        tk.Label(mass_edit_window, text="Select Action:", fg="white", bg="#2E2E2E").pack(pady=10)
        action_var = tk.StringVar()
        action_dropdown = ttk.Combobox(mass_edit_window, textvariable=action_var, state="readonly")
        action_dropdown['values'] = ("replace", "add", "delete")
        action_dropdown.pack(pady=5)
        tk.Label(mass_edit_window, text="Select Parameter:", fg="white", bg="#2E2E2E").pack(pady=10)
        param_var = tk.StringVar()
        predefined_params = self.get_all_parameters()
        param_dropdown = ttk.Combobox(mass_edit_window, textvariable=param_var, state="readonly")
        param_dropdown['values'] = sorted(predefined_params)
        param_dropdown.pack(pady=5)
        value_frame = tk.Frame(mass_edit_window, bg="#2E2E2E")
        value_frame.pack(pady=10)
        value_label = tk.Label(value_frame, text="Enter New Value:", fg="white", bg="#2E2E2E")
        value_label.pack(side=tk.LEFT, padx=5)
        value_entry = tk.Entry(value_frame, bg="#4F4F4F", fg="white", insertbackground="white")
        value_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        def perform_mass_edit():
            action = action_var.get()
            param = param_var.get()
            value = value_entry.get()
            if not action or not param:
                messagebox.showerror("Error", "Please select an action and a parameter.")
                return
            if action in ["replace", "add"] and not value:
                messagebox.showerror("Error", "Please enter a value for 'replace' or 'add' action.")
                return
            for weapon in selected_weapons:
                try:
                    keys = param.split('.')
                    d = weapon
                    for key in keys[:-1]:
                        d = d.setdefault(key, {})
                    if action == "replace":
                        d[keys[-1]] = self.convert_value(value)
                    elif action == "add":
                        existing_value = d.get(keys[-1], 0)
                        if isinstance(existing_value, (int, float)) and isinstance(self.convert_value(value), (int, float)):
                            d[keys[-1]] = existing_value + self.convert_value(value)
                        else:
                            d[keys[-1]] = value
                    elif action == "delete":
                        d.pop(keys[-1], None)
                except Exception as e:
                    messagebox.showerror("Error", f"Error during mass editing: {e}")
                    return
            save_database(self.db)
            self.update_weapon_tree()
            mass_edit_window.destroy()
            messagebox.showinfo("Success", "Mass editing completed!")
        apply_button = tk.Button(mass_edit_window, text="Apply", command=perform_mass_edit, bg="#3E3E3E", fg="white")
        apply_button.pack(pady=20)

    def get_all_parameters(self):
        params = set()
        for weapon in self.db["weapons"]:
            self.collect_params(weapon, "", params)
        return params

    def collect_params(self, current, prefix, params_set):
        if isinstance(current, dict):
            for key, value in current.items():
                full_key = f"{prefix}.{key}" if prefix else key
                params_set.add(full_key)
                self.collect_params(value, full_key, params_set)
        elif isinstance(current, list):
            for index, item in enumerate(current):
                full_key = f"{prefix}[{index}]"
                self.collect_params(item, full_key, params_set)

    def delete_parameter(self):
        param = simpledialog.askstring("Delete Parameter", "Enter the parameter name to delete (supports nested with '.'): ", parent=self.root)
        if not param:
            messagebox.showerror("Error", "Parameter cannot be empty.")
            return
        confirm = messagebox.askyesno("Confirmation", f"Are you sure you want to delete the parameter '{param}' from all weapons?")
        if not confirm:
            return
        for weapon in self.db["weapons"]:
            keys = param.split('.')
            d = weapon
            for key in keys[:-1]:
                d = d.get(key, {})
            d.pop(keys[-1], None)
        save_database(self.db)
        self.update_weapon_tree()
        messagebox.showinfo("Success", f"Parameter '{param}' has been removed from all weapons.")

    def convert_value(self, value):
        if value.lower() in ["true", "false"]:
            return value.lower() == "true"
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            return value

    def show_context_menu(self, event):
        selected_item = self.weapon_tree.identify_row(event.y)
        if selected_item:
            self.weapon_tree.selection_set(selected_item)
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="Delete", command=self.delete_weapon)
            menu.post(event.x_root, event.y_root)

    def delete_weapon(self):
        selected_items = self.weapon_tree.selection()
        if not selected_items:
            return
        item = selected_items[0]
        parent = self.weapon_tree.parent(item)
        if not parent:
            return
        weapon_name = self.weapon_tree.item(item, "text")
        confirm = messagebox.askyesno("Confirmation", f"Are you sure you want to delete the weapon '{weapon_name}'?")
        if confirm:
            self.db["weapons"] = [w for w in self.db["weapons"] if w.get("name") != weapon_name]
            save_database(self.db)
            self.update_weapon_tree()
            self.clear_fields()
            messagebox.showinfo("Success", f"Weapon '{weapon_name}' has been deleted.")

    def view_parameters(self):
        params_count = {}
        for weapon in self.db["weapons"]:
            self.count_params(weapon, "", params_count)
        display_text = ""
        for param, count in sorted(params_count.items()):
            display_text += f"{param}: {count}\n"
        params_window = tk.Toplevel(self.root)
        params_window.title("Parameters List")
        params_window.geometry("600x600")
        params_window.configure(bg="#2E2E2E")
        scrolled_text = ScrolledText(params_window, wrap=tk.WORD, bg="#4F4F4F", fg="white", insertbackground="white")
        scrolled_text.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)
        scrolled_text.insert(tk.END, display_text)
        scrolled_text.config(state=tk.DISABLED)
        copy_button = tk.Button(params_window, text="Copy", command=lambda: self.copy_to_clipboard(display_text), bg="#3E3E3E", fg="white")
        copy_button.pack(pady=5)

    def count_params(self, current, prefix, params_count):
        if isinstance(current, dict):
            for key, value in current.items():
                full_key = f"{prefix}.{key}" if prefix else key
                params_count[full_key] = params_count.get(full_key, 0) + 1
                self.count_params(value, full_key, params_count)
        elif isinstance(current, list):
            for index, item in enumerate(current):
                full_key = f"{prefix}[{index}]"
                params_count[full_key] = params_count.get(full_key, 0) + 1
                self.count_params(item, full_key, params_count)

    def copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("Success", "Parameters list copied to clipboard.")

    def add_parameter(self):
        param = simpledialog.askstring("Add Parameter", "Enter the name of the new parameter (supports nested with '.'): ", parent=self.root)
        if not param:
            messagebox.showerror("Error", "Parameter cannot be empty.")
            return
        value = simpledialog.askstring("Add Parameter", "Enter the default value:", parent=self.root)
        if value is None:
            return
        for weapon in self.db["weapons"]:
            keys = param.split('.')
            d = weapon
            for key in keys[:-1]:
                d = d.setdefault(key, {})
            d[keys[-1]] = self.convert_value(value)
        save_database(self.db)
        self.update_weapon_tree()
        messagebox.showinfo("Success", f"Parameter '{param}' has been added to all weapons.")

    def export_mechanics_logic(self):
        """Экспорт логики механик в текстовый файл 111.txt"""
        try:
            with open("111.txt", "w", encoding="utf-8") as file:
                for weapon in self.db["weapons"]:
                    mechanics_logic = weapon.get("mechanics", {}).get("effects", [])
                    file.write(json.dumps(mechanics_logic, ensure_ascii=False, indent=4) + "\n")
            messagebox.showinfo("Success", "Mechanics logic exported to 111.txt successfully!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export mechanics logic: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = WeaponManager(root)
    root.mainloop()
