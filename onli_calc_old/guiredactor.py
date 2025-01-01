import json
import tkinter as tk
from tkinter import ttk, messagebox

with open("all_armor_stats.json", "r", encoding="utf-8") as file:
    data = json.load(file)

entries = {}

RARITY_STAR_LIMITS = {
    'legendary': 6,
    'epic': 5,
    'rare': 4,
    'common': 3
}

def update_star_menu():
    rarity = rarity_var.get()
    max_stars = RARITY_STAR_LIMITS.get(rarity, 3)
    new_star_options = [str(i) for i in range(1, max_stars + 1)]
    menu = star_menu['menu']
    menu.delete(0, 'end')
    for star in new_star_options:
        menu.add_command(label=star, command=lambda value=star: star_var.set(value))
    if star_var.get() not in new_star_options:
        star_var.set(new_star_options[0])

def add_missing_levels():
    element = element_var.get()
    rarity = rarity_var.get()

    max_stars = RARITY_STAR_LIMITS.get(rarity, 3)

    for star in map(str, range(1, max_stars + 1)):
        if star not in data['items'][element][rarity]['stars']:
            data['items'][element][rarity]['stars'][star] = {'levels': {}}
        for level in range(1, 6):
            level_str = str(level)
            if level_str not in data['items'][element][rarity]['stars'][star]['levels']:
                data['items'][element][rarity]['stars'][star]['levels'][level_str] = {
                    'hp': 0,
                    'pollution_resist': 0,
                    'psi_intensity': 0
                }

def update_fields(*args):
    element = element_var.get()
    rarity = rarity_var.get()
    star = star_var.get()

    add_missing_levels()

    for widget in entry_frame.winfo_children():
        widget.destroy()

    headers = ["level", "hp", "pollution_resist", "psi_intensity"]
    header_labels = {
        "level": "Level",
        "hp": "HP",
        "pollution_resist": "Pollution Resist",
        "psi_intensity": "Psi Intensity"
    }

    for idx, key in enumerate(headers):
        ttk.Label(entry_frame, text=header_labels[key], font=('Arial', 10, 'bold')).grid(row=0, column=idx, padx=5, pady=5)

    row = 1
    stars = data['items'][element][rarity].get('stars', {})
    levels = stars.get(star, {}).get('levels', {})

    for level, stats in sorted(levels.items(), key=lambda x: int(x[0])):
        ttk.Label(entry_frame, text=f"Level {level}").grid(row=row, column=0, padx=5, pady=5)
        hp_entry = tk.Entry(entry_frame, width=10)
        hp_entry.insert(0, stats['hp'])
        hp_entry.grid(row=row, column=1, padx=5, pady=5)
        pollution_entry = tk.Entry(entry_frame, width=10)
        pollution_entry.insert(0, stats['pollution_resist'])
        pollution_entry.grid(row=row, column=2, padx=5, pady=5)
        psi_entry = tk.Entry(entry_frame, width=10)
        psi_entry.insert(0, stats['psi_intensity'])
        psi_entry.grid(row=row, column=3, padx=5, pady=5)
        entries[level] = (hp_entry, pollution_entry, psi_entry)
        row += 1

def apply_changes():
    element = element_var.get()
    rarity = rarity_var.get()
    star = star_var.get()

    for level, (hp_entry, pollution_entry, psi_entry) in entries.items():
        try:
            hp = int(hp_entry.get())
            pollution = int(pollution_entry.get())
            psi = int(psi_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Please enter valid integers.")
            return
        if star not in data['items'][element][rarity]['stars']:
            data['items'][element][rarity]['stars'][star] = {'levels': {}}
        data['items'][element][rarity]['stars'][star]['levels'][level] = {
            'hp': hp,
            'pollution_resist': pollution,
            'psi_intensity': psi
        }
    messagebox.showinfo("Applied", "Changes applied.")

def save_changes():
    try:
        with open("all_armor_stats.json", "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)
        messagebox.showinfo("Saved", "Changes saved successfully.")
    except Exception as e:
        messagebox.showerror("Error", f"Error saving: {e}")

def check_empty_fields():
    empty_items = []
    for element, rarities in data['items'].items():
        for rarity, stars_data in rarities.items():
            for star, levels in stars_data.get('stars', {}).items():
                # Проверяем, есть ли хотя бы один уровень с 0 0 0 для текущего количества звёзд
                if any(stats['hp'] == 0 and stats['pollution_resist'] == 0 and stats['psi_intensity'] == 0
                       for stats in levels['levels'].values()):
                    empty_items.append(f"{element} - {rarity} - Star {star}")

    if empty_items:
        messagebox.showinfo("Empty Fields", "Items with empty stats:\n" + "\n".join(empty_items))
    else:
        messagebox.showinfo("Empty Fields", "All items have filled stats.")
def on_rarity_change(*args):
    update_star_menu()
    update_fields()

root = tk.Tk()
root.title("BD Edit")
element_var = tk.StringVar(value='helmet')
rarity_var = tk.StringVar(value='legendary')
star_var = tk.StringVar(value='1')
label_element = ttk.Label(root, text="Element:")
label_element.grid(row=0, column=0, padx=5, pady=5, sticky='w')
element_menu = ttk.OptionMenu(root, element_var, element_var.get(), *data['items'].keys(), command=lambda _: update_fields())
element_menu.grid(row=0, column=1, padx=5, pady=5, sticky='w')
label_rarity = ttk.Label(root, text="Rarity:")
label_rarity.grid(row=1, column=0, padx=5, pady=5, sticky='w')
rarity_menu = ttk.OptionMenu(root, rarity_var, rarity_var.get(), *RARITY_STAR_LIMITS.keys())
rarity_menu.grid(row=1, column=1, padx=5, pady=5, sticky='w')
label_star_count = ttk.Label(root, text="Star Count:")
label_star_count.grid(row=2, column=0, padx=5, pady=5, sticky='w')
star_menu = ttk.OptionMenu(root, star_var, star_var.get(), '1', '2', '3', '4', '5', '6')
star_menu.grid(row=2, column=1, padx=5, pady=5, sticky='w')
entry_frame = ttk.Frame(root)
entry_frame.grid(row=3, column=0, columnspan=4, padx=10, pady=10)
button_apply_changes = ttk.Button(root, text="Apply Changes", command=apply_changes)
button_apply_changes.grid(row=4, column=0, padx=5, pady=5, sticky='w')
button_check_empty_fields = ttk.Button(root, text="Check Empty Fields", command=check_empty_fields)
button_check_empty_fields.grid(row=4, column=1, padx=5, pady=5, sticky='w')
rarity_var.trace_add("write", on_rarity_change)
star_var.trace_add("write", update_fields)
update_star_menu()
update_fields()
root.mainloop()
