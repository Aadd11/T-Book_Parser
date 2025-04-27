from .translator import BaseTranslator


class NullTranslator(BaseTranslator):
    async def translate_text(self, text: str) -> str:
        return text

    async def translate_batch(self, texts: List[str]) -> List[str]:
        return texts