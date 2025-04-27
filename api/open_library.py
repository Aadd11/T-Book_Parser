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
    lang = request.args.get('lang', 'en').lower()  # default to English
    if lang not in ('en', 'ru'):
        lang = 'en'  # fallback to English if invalid language
    return await _search_openlib(language=lang)

async def _search_openlib(language: str):
    start_time = datetime.now()

    try:
        # Use async context manager for the parser
        async with OpenLibraryParser() as parser:
            # Validate parameters
            author = request.args.get('author', '').strip()
            title = request.args.get('title', '').strip()
            max_results = min(int(request.args.get('max_results', 50)), 200)

            if not author and not title:
                error_msg = "Укажите автора или название" if language == 'ru' else "Author or title required"
                return jsonify({"error": error_msg}), 400

            # Get structured data
            authors, genres, books, book_authors, book_genres = await asyncio.wait_for(
                parser.get_all_structured_data(author=author, title=title, max_results=max_results),
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

            # Translate if needed
            if language == 'ru':
                data = await TranslationManager.translate(data)

            return jsonify({
                "metadata": {
                    "source": "Open Library",
                    "query": {
                        "author": author,
                        "title": title,
                        "max_results": max_results
                    },
                    "execution_time": str(datetime.now() - start_time),
                    "timestamp": datetime.utcnow().isoformat(),
                    "language": language
                },
                "data": data
            })

    except asyncio.TimeoutError:
        logger.error("Open Library search timeout")
        return jsonify({"error": "Service timeout"}), 504
    except Exception as e:
        logger.exception("Open Library search failed")
        error_msg = str(e) if language == 'en' else "Ошибка сервера"
        return jsonify({"error": error_msg}), 500