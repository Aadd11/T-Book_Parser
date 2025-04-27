from deep_translator import GoogleTranslator
from .translator import BaseTranslator
import asyncio
import logging

logger = logging.getLogger(__name__)


class GoogleTranslatorWrapper(BaseTranslator):
    def __init__(self):
        self.translator = GoogleTranslator(source='auto', target='ru')

    async def translate_text(self, text: str) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.translator.translate(text)
        )

    async def translate_batch(self, texts: List[str]) -> List[str]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: [self.translator.translate(t) for t in texts]
        )