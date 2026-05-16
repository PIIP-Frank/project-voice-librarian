import json
from pathlib import Path
from typing import Dict, List, Optional

# Supported languages: shortcode -> full name
SUPPORTED_LANGUAGES = {
    "en": "English UK",
    "ig": "Igbo Nigeria",
    "yo": "Yoruba Nigeria",
    "ha": "Hausa Nigeria",
    "tw": "Twi Ghana",
    "pg": "Pidgin Nigeria"
}

class WordTranslations:
    """Store for word translations across languages."""
    
    _instance = None
    _words_data: Dict[str, Dict[str, str]] = {}
    _file_path: Path
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._file_path = Path(__file__).parent.parent / "data" / "word_translations.json"
            cls._load_data(cls._instance)
        return cls._instance
    
    @classmethod
    def _load_data(cls, instance):
        """Load translations from JSON file."""
        if cls._file_path.exists():
            try:
                with open(cls._file_path, "r", encoding="utf-8") as f:
                    instance._words_data = json.load(f)
            except:
                instance._words_data = {}
        else:
            instance._words_data = {}
            cls._file_path.parent.mkdir(parents=True, exist_ok=True)
            cls._save_data(instance)
    
    @classmethod
    def _save_data(cls, instance):
        """Save translations to JSON file."""
        with open(cls._file_path, "w", encoding="utf-8") as f:
            json.dump(instance._words_data, f, indent=2, ensure_ascii=False)
    
    def get_word(self, english_word: str) -> Optional[Dict[str, str]]:
        """Get translations for a word (returns None if not exists)."""
        return self._words_data.get(english_word)
    
    def set_translation(self, english_word: str, lang_code: str, translated_word: str):
        """Set translation for a given language."""
        if english_word not in self._words_data:
            self._words_data[english_word] = {}
        self._words_data[english_word][lang_code] = translated_word
        self._save_data(self)
    
    def get_translation(self, english_word: str, lang_code: str) -> Optional[str]:
        """Get translation for a specific language."""
        return self._words_data.get(english_word, {}).get(lang_code)
    
    def list_all_words(self) -> List[str]:
        """Return all English words that have translations."""
        return list(self._words_data.keys())
    
    def delete_word(self, english_word: str) -> bool:
        """Delete a word and its translations."""
        if english_word in self._words_data:
            del self._words_data[english_word]
            self._save_data(self)
            return True
        return False
