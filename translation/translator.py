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
    async def translate(cls, data: Union[str, List, Dict], target_lang: str = 'ru') -> Any:
        """Enhanced translation with language targeting"""
        if isinstance(data, dict):
            return await cls._translate_dict(data, target_lang)
        elif isinstance(data, list):
            return await cls._translate_list(data, target_lang)
        elif isinstance(data, str):
            return await cls._translator.translate_text(data, target_lang)
        return data

    @classmethod
    async def _translate_dict(cls, data: Dict, target_lang: str) -> Dict:
        """Process dictionary in parallel"""
        # Skip translation if book is already in target language
        if data.get('is_russian') and target_lang == 'ru':
            return data

        keys = list(data.keys())
        values = await asyncio.gather(*[
            cls.translate(data[key], target_lang)
            for key in keys
        ])
        return dict(zip(keys, values))

    @classmethod
    async def _translate_list(cls, data: List, target_lang: str) -> List:
        """Process list with chunking for large datasets"""
        if len(data) > 1000:
            return await cls._process_large_list(data, target_lang)
        return await asyncio.gather(*[
            cls.translate(item, target_lang)
            for item in data
        ])

    @classmethod
    async def _process_large_list(cls, data: List, target_lang: str) -> List:
        """Process large lists in chunks"""
        chunk_size = 500
        results = []
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            processed = await asyncio.gather(*[
                cls.translate(item, target_lang)
                for item in chunk
            ])
            results.extend(processed)
            await asyncio.sleep(0.001)
        return results