# damage_calculation.py

def display_damage(damage, target):
    # Функция для отображения урона на манекене
    print(f"Нанесено {damage} урона по манекену.")
    target.receive_damage(damage)

def calculate_shotgun_damage(weapon, target):
    damage_per_projectile = weapon.damage_per_projectile
    projectiles = weapon.projectiles_per_shot
    total_damage = 0
    damage_list = []

    for _ in range(projectiles):
        # Здесь можно учесть все модификаторы урона, эффекты и т.д.
        damage = damage_per_projectile  # Модифицируйте согласно механикам игры
        total_damage += damage
        damage_list.append(damage)

    if target.show_unified_shotgun_damage:
        # Отображаем суммарный урон
        display_damage(total_damage, target)
    else:
        # Отображаем урон каждой дробинки
        for dmg in damage_list:
            display_damage(dmg, target)
