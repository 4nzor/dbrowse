import json
import os
from pathlib import Path
from typing import Dict, Any

# Default language
DEFAULT_LANG = "en"
SUPPORTED_LANGS = ["en", "ru", "zh"]


class Translations:
    _instance = None
    _current_lang = DEFAULT_LANG
    _translations: Dict[str, Dict[str, str]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Translations, cls).__new__(cls)
        return cls._instance

    def load_translations(self):
        locales_dir = Path(__file__).parent / "locales"
        for lang in SUPPORTED_LANGS:
            lang_file = locales_dir / f"{lang}.json"
            if lang_file.exists():
                try:
                    with open(lang_file, "r", encoding="utf-8") as f:
                        self._translations[lang] = json.load(f)
                except Exception as e:
                    print(f"Error loading translation for {lang}: {e}")
                    self._translations[lang] = {}
            else:
                self._translations[lang] = {}

    def set_language(self, lang: str):
        if lang in SUPPORTED_LANGS:
            self._current_lang = lang
        else:
            self._current_lang = DEFAULT_LANG

    def get_language(self):
        return self._current_lang

    def translate(self, key: str, default: str = None) -> str:
        lang_dict = self._translations.get(self._current_lang, {})
        # Fallback to English if not found in current language
        val = lang_dict.get(key)
        if val is None and self._current_lang != "en":
            val = self._translations.get("en", {}).get(key)

        return val if val is not None else (default if default is not None else key)


# Global translator instance
translator = Translations()
translator.load_translations()


def _(key: str, default: str = None) -> str:
    return translator.translate(key, default)
