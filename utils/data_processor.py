from typing import Any, List, Dict, Union
import asyncio
from config import Config
import logging

logger = logging.getLogger(__name__)


class DataProcessor:
    @staticmethod
    async def process(data: Any, translator) -> Any:
        """Recursively process data structure with translation"""
        if isinstance(data, dict):
            return await DataProcessor._process_dict(data, translator)
        elif isinstance(data, list):
            return await DataProcessor._process_list(data, translator)
        elif isinstance(data, str):
            return await translator.translate_text(data)
        return data

    @staticmethod
    async def _process_dict(data: Dict, translator) -> Dict:
        """Process dictionary in parallel"""
        keys = list(data.keys())
        values = await asyncio.gather(*[
            DataProcessor.process(data[key], translator)
            for key in keys
        ])
        return dict(zip(keys, values))

    @staticmethod
    async def _process_list(data: List, translator) -> List:
        """Process list with chunking for large datasets"""
        if len(data) > 1000:  # Large lists get batched processing
            return await DataProcessor._process_large_list(data, translator)
        return await asyncio.gather(*[
            DataProcessor.process(item, translator)
            for item in data
        ])

    @staticmethod
    async def _process_large_list(data: List, translator) -> List:
        """Process large lists in chunks"""
        chunk_size = 500
        results = []
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            processed = await asyncio.gather(*[
                DataProcessor.process(item, translator)
                for item in chunk
            ])
            results.extend(processed)
            await asyncio.sleep(0.001)  # Brief yield
        return results