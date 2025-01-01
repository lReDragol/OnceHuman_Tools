# mechanics.py

import json
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import random
import logging

# Функция для загрузки данных оружия из базы данных
def load_weapon_data() -> List[Dict[str, Any]]:
    # Здесь должна быть реализация загрузки данных из базы данных
    # Временно загрузим данные из файла weapon_list.json для демонстрации
    with open('weapon_list.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['weapons']

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Базовый класс для всех эффектов
class Effect(ABC):
    @abstractmethod
    def apply(self, target, **kwargs):
        pass

# Классы эффектов
class IncreaseStatEffect(Effect):
    def __init__(self, stat: str, value: float):
        self.stat = stat
        self.value = value

    def apply(self, target, **kwargs):
        if hasattr(target, 'stats'):
            original_value = target.stats.get(self.stat, 0)
            target.stats[self.stat] = original_value + self.value
            logging.debug(f"{self.stat} увеличен на {self.value}. Новое значение: {target.stats[self.stat]}")

class DecreaseStatEffect(Effect):
    def __init__(self, stat: str, value: float):
        self.stat = stat
        self.value = value

    def apply(self, target, **kwargs):
        if hasattr(target, 'stats'):
            original_value = target.stats.get(self.stat, 0)
            target.stats[self.stat] = original_value - self.value
            logging.debug(f"{self.stat} уменьшен на {self.value}. Новое значение: {target.stats[self.stat]}")

class ApplyStatusEffect(Effect):
    def __init__(self, status: str, duration: float, **kwargs):
        self.status = status
        self.duration = duration
        self.kwargs = kwargs

    def apply(self, target, **kwargs):
        if hasattr(target, 'apply_status'):
            target.apply_status(self.status, self.duration, **self.kwargs)
            logging.debug(f"Применён статус {self.status} на {self.duration} секунд.")

# Класс для событий
class Event:
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.kwargs = kwargs

# Класс для механик оружия
class Mechanic:
    def __init__(self, description: str, effects: List[Dict[str, Any]]):
        self.description = description
        self.effects_data = effects
        self.effects = self.parse_effects(effects)

    def parse_effects(self, effects_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        parsed_effects = []
        for effect_data in effects_data:
            event_type = effect_data.get('type')
            if event_type == 'on_event':
                event = Event(effect_data['event'], **effect_data.get('conditions', {}))
                effects = self.create_effects(effect_data['effects'])
                parsed_effects.append({'event': event, 'effects': effects, 'chance': effect_data.get('chance_percent', 100)})
            elif event_type == 'passive_effect':
                effects = self.create_effects([effect_data])
                parsed_effects.append({'event': None, 'effects': effects})
        return parsed_effects

    def create_effects(self, effects_data: List[Dict[str, Any]]) -> List[Effect]:
        effects = []
        for effect_data in effects_data:
            effect_type = effect_data['type']
            if effect_type == 'increase_stat':
                effect = IncreaseStatEffect(effect_data['stat'], effect_data['value'])
            elif effect_type == 'decrease_stat':
                effect = DecreaseStatEffect(effect_data['stat'], effect_data['value'])
            elif effect_type == 'apply_status':
                effect = ApplyStatusEffect(effect_data['status'], effect_data['duration_seconds'], **effect_data.get('stat_bonuses', {}))
            # Добавьте другие типы эффектов по мере необходимости
            else:
                continue  # Пропускаем неизвестные типы эффектов
            effects.append(effect)
        return effects

    def trigger_event(self, event_name: str, target, **kwargs):
        for effect_entry in self.effects:
            event = effect_entry['event']
            if event and event.name == event_name:
                chance = effect_entry.get('chance', 100)
                if chance >= 100 or random.randint(1, 100) <= chance:
                    for effect in effect_entry['effects']:
                        effect.apply(target, **kwargs)
            elif event is None:
                for effect in effect_entry['effects']:
                    effect.apply(target, **kwargs)

# Функция для суммирования статистик
def add_stats(stats_dict, new_stats):
    for stat, value in new_stats.items():
        if isinstance(value, dict):
            if stat not in stats_dict:
                stats_dict[stat] = {}
            add_stats(stats_dict[stat], value)
        elif isinstance(value, (int, float)):
            current_value = stats_dict.get(stat, 0)
            stats_dict[stat] = current_value + value
        else:
            # Игнорируем значения, которые не являются числами или словарями
            pass

# Класс для оружия
class Weapon:
    def __init__(self, data: Dict[str, Any]):
        self.id = data['id']
        self.name = data['name']
        self.type = data['type']
        self.rarity = data['rarity']
        self.base_stats = data['base_stats']
        self.mechanics_data = data.get('mechanics', {})
        self.description = data.get('description', '')
        self.star = 1  # Звёзды по умолчанию
        self.level = 1  # Уровень по умолчанию
        self.calibration = 0  # Калибровка по умолчанию
        self.stats = {}

        # Если есть механики, создаём объект Mechanic
        if isinstance(self.mechanics_data, dict) and 'description' in self.mechanics_data and 'effects' in self.mechanics_data:
            self.mechanics = Mechanic(self.mechanics_data['description'], self.mechanics_data['effects'])
        else:
            self.mechanics = None

    def calculate_stats(self):
        stats = {}
        add_stats(stats, self.base_stats)
        # Применяем модификаторы на основе звёзд, уровня и калибровки
        star_multipliers = {
            1: 1.0,
            2: 1.1,
            3: 1.2,
            4: 1.3,
            5: 1.4,
            6: 1.5
        }
        level_multipliers = {
            1: 1.0,
            2: 1.05,
            3: 1.10,
            4: 1.15,
            5: 1.20
        }
        calibration_bonuses = {
            0: 0.0,
            1: 0.02,
            2: 0.04,
            3: 0.06,
            4: 0.08,
            5: 0.10,
            6: 0.12
        }
        star_multiplier = star_multipliers.get(self.star, 1.0)
        level_multiplier = level_multipliers.get(self.level, 1.0)
        calibration_bonus = calibration_bonuses.get(self.calibration, 0.0)
        for stat in stats:
            base_value = stats[stat]
            if isinstance(base_value, (int, float)):
                new_value = base_value * star_multiplier * level_multiplier * (1 + calibration_bonus)
                # Если статистика должна быть целым числом, приводим результат к int
                if stat in ['projectiles_per_shot', 'magazine_capacity']:
                    stats[stat] = int(round(new_value))
                else:
                    stats[stat] = new_value
        self.stats = stats
        return stats

    def get_stats(self):
        return self.calculate_stats()

    def apply_status(self, status: str, duration: float, **kwargs):
        # Реализация применения статуса к цели
        logging.debug(f"{self.name} применяет статус {status} на {duration} секунд с эффектами {kwargs}")

    def trigger_event(self, event_name: str, **kwargs):
        if self.mechanics:
            self.mechanics.trigger_event(event_name, target=self, **kwargs)

# Класс для обработки механик
class MechanicsProcessor:
    def __init__(self, context=None):
        # Загрузка данных оружия из базы данных
        self.weapons_data = load_weapon_data()
        # Создание словаря оружия по идентификатору
        self.weapons = {data['id']: Weapon(data) for data in self.weapons_data}
        # Загрузка модов и эффектов (если необходимо)
        self.all_effects = self.get_all_effects()
        self.context = context

    def get_weapon(self, weapon_id: str) -> Weapon:
        return self.weapons.get(weapon_id)

    def get_all_effects(self) -> List[Effect]:
        # Реализация загрузки всех эффектов
        # Предположим, что эффекты загружаются из файла mods_config.json
        effects = []
        with open('mods_config.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
            for category, mods in data.items():
                for mod in mods:
                    for effect_data in mod['effects']:
                        effect = self.create_effect_from_data(effect_data)
                        if effect:
                            effects.append(effect)
        return effects

    def create_effect_from_data(self, effect_data: Dict[str, Any]) -> Optional[Effect]:
        effect_type = effect_data['type']
        if effect_type == 'increase_stat':
            stat = effect_data['stat']
            value = effect_data['value']
            return IncreaseStatEffect(stat, value)
        # Добавьте обработку других типов эффектов
        return None

    # Метод для обработки событий оружия
    def process_weapon_event(self, event_name: str, **kwargs):
        weapon = self.context.player.weapon if self.context else None
        if weapon:
            weapon.trigger_event(event_name, **kwargs)

def display_damage(self, damage):
    print(f"Нанесено {damage} урона по манекену.")
    self.context.mannequin.receive_damage(damage)

def calculate_shotgun_damage(self):
    damage_per_projectile = self.player.stats.get('damage_per_projectile', 0)
    projectiles = self.player.stats.get('projectiles_per_shot', 1)
    total_damage = 0
    damage_list = []

    for _ in range(projectiles):
        damage = self.calculate_damage_per_projectile()
        total_damage += damage
        damage_list.append(damage)

    self.total_damage += total_damage  # Обновляем суммарный урон

    if self.context.mannequin.show_unified_shotgun_damage:
        self.display_damage(total_damage)
    else:
        for dmg in damage_list:
            self.display_damage(dmg)



def calculate_damage(self):
    base_damage = self.player.stats.get('damage_per_projectile', 0)
    # Применение бонусов к урону
    weakspot_bonus = self.player.stats.get('weakspot_damage_bonus_input', 0) if self.last_hit_weakspot else 0
    elite_bonus = self.player.stats.get('damage_bonus_elite_input', 0) if self.context.mannequin.enemy_type == 'Элитный' else 0
    boss_bonus = self.player.stats.get('damage_bonus_boss_input', 0) if self.context.mannequin.enemy_type == 'Босс' else 0
    total_bonus = weakspot_bonus + elite_bonus + boss_bonus
    damage = base_damage * (1 + total_bonus / 100)
    # Учёт критического урона
    if self.last_hit_crit:
        crit_damage_bonus = self.player.stats.get('crit_dmg_input', 0)
        damage *= (1 + crit_damage_bonus / 100)
    return damage


# Пример использования
if __name__ == "__main__":
    # Загрузим данные оружия из базы данных
    mechanics_processor = MechanicsProcessor()

    # нужно сделать автоматический выбор
    test_weapon = mechanics_processor.get_weapon('kv-sbr_frosted_falcon')  # Замените на нужный ID оружия

    # Тестируем событие попадания по цели
    print(f"Тестируем оружие: {test_weapon.name}")
    test_weapon.trigger_event('hit_target')

    # Тестируем событие критического удара
    test_weapon.trigger_event('crit_hit')

    # Тестируем пассивные эффекты
    test_weapon.trigger_event('passive')
