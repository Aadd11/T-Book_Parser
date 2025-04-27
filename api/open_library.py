from flask import Blueprint, request, jsonify
from translation.translator import TranslationManager
from parsers.openlib_parser import OpenLibraryParser
from utils.async_utils import async_route
from config import Config
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
open_lib_bp = Blueprint('open_library', __name__)

@open_lib_bp.route('/search/openlib', methods=['GET'])
@async_route
async def search_openlib():
    language = request.args.get('lang', 'en')
    return await _search_openlib(language=language)


async def _search_openlib(language: str):
    start_time = datetime.now()

    try:
        async with OpenLibraryParser() as parser:
            author = request.args.get('author', '').strip()
            title = request.args.get('title', '').strip()
            max_results = min(int(request.args.get('max_results', 50)), 200)

            if not author and not title:
                error_msg = {
                    'en': "Author or title required",
                    'ru': "Укажите автора или название"
                }.get(language, "Author or title required")
                return jsonify({"error": error_msg}), 400

            # Search with language preference
            authors, genres, books, book_authors, book_genres = await asyncio.wait_for(
                parser.get_all_structured_data(
                    author=author,
                    title=title,
                    max_results=max_results,
                    language='ru' if language == 'ru' else None
                ),
                timeout=Config.REQUEST_TIMEOUT
            )

            data = {
                "authors": authors,
                "genres": genres,
                "books": books,
                "relationships": {
                    "book_authors": book_authors,
                    "book_genres": book_genres
                }
            }

            # Translate only if needed
            if language == 'ru':
                data = await TranslationManager.translate(data, target_lang='ru')

            return jsonify({
                "metadata": {
                    "source": "Open Library",
                    "query": {
                        "author": author,
                        "title": title,
                        "max_results": max_results,
                        "language": language
                    },
                    "execution_time": str(datetime.now() - start_time),
                    "timestamp": datetime.utcnow().isoformat()
                },
                "data": data
            })

    except asyncio.TimeoutError:
        logger.error("Open Library search timeout")
        error_msg = {
            'en': "Service timeout",
            'ru': "Таймаут сервиса"
        }.get(language, "Service timeout")
        return jsonify({"error": error_msg}), 504
    except Exception as e:
        logger.exception("Open Library search failed")
        error_msg = str(e) if language == 'en' else "Ошибка сервера"
        return jsonify({"error": error_msg}), 500