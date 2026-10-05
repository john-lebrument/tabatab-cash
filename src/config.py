import json
import os
import sys
from pathlib import Path


def get_app_dir() -> Path:
    """Returns the portable application root directory."""
    if getattr(sys, "frozen", False):
        # Running in a PyInstaller bundle
        return Path(sys.executable).resolve().parent
    else:
        # Running in normal Python environment
        return Path(__file__).resolve().parent.parent


def get_settings_path() -> Path:
    """Returns the path to the portable settings.json file."""
    app_dir = get_app_dir()
    data_dir = app_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "settings.json"


def get_default_folders() -> list[str]:
    """Returns sensible default folders (e.g., Pictures or Home)."""
    pictures = Path.home() / "Pictures"
    if pictures.exists():
        return [str(pictures)]
    return [str(Path.home())]


DEFAULT_SETTINGS = {
    "tabs": get_default_folders(),
    "active_tab": 0,
    "thumbnail_size": 150,
    "show_hidden": False,
    "sort_by": "name",  # "name", "date", "size"
    "sort_order": "asc",  # "asc", "desc"
    "theme": "dark",
    "crop_save_mode": "prompt",  # "prompt", "copy", "overwrite"
    "custom_favorites": [],
    "window_width": 1280,
    "window_height": 820,
    "window_maximized": False,
}


class ConfigManager:
    """Manages application settings stored in portable JSON format."""

    def __init__(self):
        self.settings_file = get_settings_path()
        self.settings = self.load()

    def load(self) -> dict:
        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Merge with default settings for any missing keys
                    merged = DEFAULT_SETTINGS.copy()
                    merged.update(data)
                    return merged
            except Exception as e:
                print(f"Error loading settings: {e}")
        return DEFAULT_SETTINGS.copy()

    def save(self):
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key, default=None):
        return self.settings.get(key, default if default is not None else DEFAULT_SETTINGS.get(key))

    def set(self, key, value):
        self.settings[key] = value
        self.save()
