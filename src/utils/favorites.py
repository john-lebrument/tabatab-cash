"""Portable favorites exchange, with validation before changing preferences."""
import json
from pathlib import Path


def export_favorites(config, filename):
    payload = {'format': 'tabatab-favorites', 'version': 1}
    for key in ('custom_favorites', 'hidden_favorites', 'favorite_order'):
        payload[key] = config.get(key, [])
    Path(filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def import_favorites(config, filename):
    payload = json.loads(Path(filename).read_text(encoding='utf-8-sig'))
    if not isinstance(payload, dict) or payload.get('format') != 'tabatab-favorites' or payload.get('version') != 1:
        raise ValueError('Ce fichier ne contient pas un export de favoris TABaTAB compatible.')
    updates = {}
    for key in ('custom_favorites', 'hidden_favorites'):
        paths = payload.get(key, [])
        if not isinstance(paths, list) or any(not isinstance(p, str) or not p or '\x00' in p or not Path(p).is_absolute() for p in paths):
            raise ValueError('Les chemins des favoris sont invalides.')
        updates[key] = paths
    order = payload.get('favorite_order', [])
    if not isinstance(order, list) or any(not isinstance(entry, list) or len(entry) != 2 or
        not isinstance(entry[0], str) or not entry[0] or '\x00' in entry[0] or
        not Path(entry[0]).is_absolute() or not isinstance(entry[1], bool) for entry in order):
        raise ValueError("L'ordre des favoris est invalide.")
    updates['favorite_order'] = order
    # Merge without discarding existing entries or inaccessible network folders.
    for key, incoming in updates.items():
        merged = list(config.get(key, []))
        for value in incoming:
            if value not in merged:
                merged.append(value)
        updates[key] = merged
    updates['hidden_favorites'] = [p for p in updates['hidden_favorites'] if p not in updates['custom_favorites']]
    config.settings.update(updates)
    config.save()
