from __future__ import annotations

import json
from pathlib import Path


class ModSecondaryAttributeCatalog:
    def __init__(self, payload: dict):
        self.payload = payload or {}
        source_attributes = self.payload.get('all_attributes') or self.payload.get('supported_attributes') or []
        self.attributes = [self._normalize_attribute(entry) for entry in source_attributes]
        self.attributes.sort(
            key=lambda entry: (
                0 if entry.get('implemented') else 1,
                entry.get('display_name', {}).get('ru') or entry.get('game_name') or entry.get('id'),
            )
        )
        self.by_id = {entry['id']: entry for entry in self.attributes}
        self.by_game_name = {entry['game_name']: entry for entry in self.attributes}

    @classmethod
    def load(cls, bd_json_path: str | Path) -> 'ModSecondaryAttributeCatalog':
        path = Path(bd_json_path) / 'mod_secondary_attributes.json'
        if not path.exists():
            return cls({})
        with path.open('r', encoding='utf-8') as fh:
            payload = json.load(fh)
        return cls(payload)

    @staticmethod
    def _normalize_attribute(entry: dict) -> dict:
        normalized = dict(entry or {})
        game_name = normalized.get('game_name') or normalized.get('id') or ''
        normalized.setdefault('id', game_name)
        normalized.setdefault('game_name', game_name)
        normalized.setdefault('display_name', {'ru': game_name, 'en': game_name})
        normalized.setdefault('tier_codes', [])
        normalized.setdefault('values', {})
        normalized.setdefault('tier_metadata', {})
        normalized['implemented'] = bool(normalized.get('effect') and normalized.get('values'))
        normalized['supported'] = bool(normalized.get('supported', normalized['implemented']))
        return normalized

    def get_attribute(self, attribute_id: str):
        return self.by_id.get(attribute_id)

    def get_attribute_options(self):
        return self.attributes

    def build_effects(self, mod: dict) -> list[dict]:
        effects: list[dict] = []
        for index, roll in enumerate(mod.get('secondary_attributes', [])):
            attribute_id = roll.get('attribute_id')
            tier_code = str(roll.get('tier_code', ''))
            attribute = self.by_id.get(attribute_id)
            if not attribute or not attribute.get('implemented'):
                continue
            value = attribute.get('values', {}).get(tier_code)
            if value is None:
                continue
            effect = dict(attribute.get('effect', {}))
            effect['value'] = value
            effect.setdefault('source', f"mod_secondary:{mod.get('name', 'unknown')}:{attribute_id}:{tier_code}:{index}")
            effects.append(effect)
        return effects

    def build_roll(self, attribute_id: str, tier_code: str) -> dict | None:
        attribute = self.by_id.get(attribute_id)
        if not attribute:
            return None
        tier_code = str(tier_code)
        if tier_code not in attribute.get('tier_codes', []):
            return None
        value = attribute.get('values', {}).get(tier_code)
        return {
            'attribute_id': attribute_id,
            'tier_code': tier_code,
            'game_name': attribute.get('game_name'),
            'value': value,
            'implemented': attribute.get('implemented', False),
        }

    def get_display_name(self, attribute_id: str, language: str = 'ru') -> str:
        attribute = self.by_id.get(attribute_id)
        if not attribute:
            return attribute_id
        display_name = attribute.get('display_name', {})
        return display_name.get(language) or display_name.get('en') or attribute.get('game_name', attribute_id)

    def get_tier_codes(self, attribute_id: str) -> list[str]:
        attribute = self.by_id.get(attribute_id)
        if not attribute:
            return []
        return list(attribute.get('tier_codes', []))

    def get_tier_metadata(self, attribute_id: str, tier_code: str) -> list[str]:
        attribute = self.by_id.get(attribute_id)
        if not attribute:
            return []
        return list(attribute.get('tier_metadata', {}).get(str(tier_code), []))

    def format_roll(self, roll: dict, language: str = 'ru') -> str:
        attribute_id = roll.get('attribute_id')
        tier_code = str(roll.get('tier_code', ''))
        value = roll.get('value')
        attribute = self.by_id.get(attribute_id)
        if attribute and value is None:
            value = attribute.get('values', {}).get(tier_code)
        if value is None:
            value_text = None
        elif float(value).is_integer():
            value_text = str(int(value))
        else:
            value_text = f'{float(value):.2f}'.rstrip('0').rstrip('.')
        name = self.get_display_name(attribute_id, language)
        tier_label = f'T{tier_code.upper()}'
        if value_text is None:
            return f'{name} [{tier_label}]'
        return f'{name} +{value_text}% [{tier_label}]'

    def summarize_rolls(self, mod: dict, language: str = 'ru') -> str:
        lines = [self.format_roll(roll, language) for roll in mod.get('secondary_attributes', []) if roll.get('attribute_id')]
        return '\n'.join(lines)
