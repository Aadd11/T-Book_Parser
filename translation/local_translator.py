from typing import List

from argostranslate import translate
from .translator import BaseTranslator
import asyncio


class LocalTranslator(BaseTranslator):
    def __init__(self):
        installed_languages = translate.get_installed_languages()
        self.translation = next(
            (lang for lang in installed_languages if lang.code == 'en')
        ).get_translation(next(
            (lang for lang in installed_languages if lang.code == 'ru'),
            None
        ))

    async def translate_text(self, text: str) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.translation.translate,
            text[:5000]
        )

    async def translate_batch(self, texts: List[str]) -> List[str]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: [self.translation.translate(t[:5000]) for t in texts]
        )

