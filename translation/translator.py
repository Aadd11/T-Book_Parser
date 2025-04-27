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
    async def translate(cls, data: Union[str, List, Dict]) -> Any:
        from utils.data_processor import DataProcessor  # Import the class
        return await DataProcessor.process(data, cls._translator)  # Use the class method