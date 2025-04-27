from flask import Blueprint, request, jsonify
from translation.translator import TranslationManager
from parsers.google_parser import GoogleBooksParser
from utils.async_utils import async_route
from config import Config
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
google_books_bp = Blueprint('google_books', __name__)
parser = GoogleBooksParser(api_key=Config.GOOGLE_BOOKS_API_KEY)  # Add your API key in config


@google_books_bp.route('/search/google', methods=['GET'])
@async_route
async def search_google():
    return await _search_google(language='en')


@google_books_bp.route('/search/google/ru', methods=['GET'])
@async_route
async def search_google_ru():
    return await _search_google(language='ru')


async def _search_google(language: str):
    start_time = datetime.now()

    try:
        # Initialize parser session
        await parser.initialize()

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
            "entities": {
                "authors": authors,
                "genres": genres,
                "books": books
            },
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
                "source": "Google Books",
                "query": {
                    "author": author,
                    "title": title,
                    "max_results": max_results
                },
                "result_stats": {
                    "books": len(books),
                    "authors": len(authors),
                    "genres": len(genres)
                },
                "execution_time": str(datetime.now() - start_time),
                "timestamp": datetime.utcnow().isoformat(),
                "language": language
            },
            "data": data
        })

    except asyncio.TimeoutError:
        logger.error("Google Books search timeout")
        return jsonify({"error": "Service timeout"}), 504
    except Exception as e:
        logger.exception("Google Books search failed")
        error_msg = str(e) if language == 'en' else "Ошибка сервера"
        return jsonify({"error": error_msg}), 500
    finally:
        await parser.close()