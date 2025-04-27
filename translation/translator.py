from abc import ABC, abstractmethod
from typing import List, Union, Dict, Any
import asyncio


class BaseTranslator(ABC):
    @abstractmethod
    async def translate_text(self, text: str) -> str:
        pass

    @abstractmethod
    async def translate_batch(self, texts: List[str]) -> List[str]:
        pass


class TranslationManager:
    _translator = None
    # Fields to skip during translation
    SKIP_FIELDS = {'language', 'genre', 'genres', 'language_code'}
    # Entity types to skip during translation
    SKIP_ENTITIES = {'Genre', 'Language'}

    @classmethod
    def initialize(cls):
        try:
            from .local_translator import LocalTranslator
            cls._translator = LocalTranslator()
            print("Using local translation engine")
        except ImportError:
            from .google_translator import GoogleTranslator
            cls._translator = GoogleTranslator()
            print("Using Google Translate as fallback")

    @classmethod
    async def translate(cls, data: Union[str, List, Dict]) -> Any:
        if isinstance(data, dict):
            return await cls._translate_dict(data)
        elif isinstance(data, list):
            return await cls._translate_list(data)
        elif isinstance(data, str):
            return await cls._translator.translate_text(data)
        return data

    @classmethod
    async def _translate_dict(cls, data: Dict) -> Dict:
        """Process dictionary while skipping specified fields"""
        translated = {}
        for key, value in data.items():
            # Skip translation for specified fields and entities
            if (key in cls.SKIP_FIELDS or
                any(entity in str(key) for entity in cls.SKIP_ENTITIES)):
                translated[key] = value
            else:
                translated[key] = await cls.translate(value)
        return translated

    @classmethod
    async def _translate_list(cls, data: List) -> List:
        """Process list items"""
        return await asyncio.gather(*[cls.translate(item) for item in data])