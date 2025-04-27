import aiohttp
import asyncio
import uuid
import json
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class OpenLibraryParser:
    def __init__(self):
        self.base_url = "https://openlibrary.org"
        self.request_delay = 0.5
        self.default_language = "en"
        self.default_publisher = "Unknown Publisher"
        self.default_summary = "No description available"
        self.session = None
        self.supported_languages = {
            'en': 'English',
            'ru': 'Russian',
            'rus': 'Russian'  # OpenLibrary sometimes uses 'rus'
        }

    async def __aenter__(self):
        """Initialize async context manager"""
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        """Clean up async context manager"""
        if self.session:
            await self.session.close()

    async def get_all_structured_data(
            self,
            author: Optional[str] = None,
            title: Optional[str] = None,
            max_results: int = 200,
            language: Optional[str] = None  # Added language parameter
    ) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict], List[Dict]]:
        """
        Returns structured data ready for database import:
        (authors, genres, books, book_authors, book_genres)
        """
        raw_books = await self.search_books(
            author=author,
            title=title,
            max_results=max_results,
            language=language  # Pass language to search
        )
        return self._structure_data(raw_books)

    async def search_books(
            self,
            author: Optional[str] = None,
            title: Optional[str] = None,
            max_results: int = 200,
            batch_size: int = 100,
            language: Optional[str] = None
    ) -> List[Dict]:
        """
        Async search for books with pagination support
        """
        all_books = []
        page = 1

        while len(all_books) < max_results:
            batch = await self._search_batch(
                author=author,
                title=title,
                page=page,
                limit=min(batch_size, max_results - len(all_books)),
                language=language
            )

            if not batch:
                break

            all_books.extend(batch)
            page += 1
            await asyncio.sleep(self.request_delay)

        return all_books[:max_results]

    async def _search_batch(
            self,
            author: Optional[str] = None,
            title: Optional[str] = None,
            page: int = 1,
            limit: int = 100,
            language: Optional[str] = None
    ) -> List[Dict]:
        """
        Async search for a single batch of books
        """
        params = {
            'q': self._build_query(author=author, title=title),
            'page': page,
            'limit': limit,
            'mode': 'everything',
            'fields': ','.join([
                'title', 'author_name', 'first_publish_year', 'description',
                'language', 'number_of_pages', 'number_of_pages_median',
                'isbn', 'isbn_10', 'isbn_13', 'subject', 'ratings_average',
                'ratings_count', 'cover_i', 'key', 'publisher', 'publish_date',
                'author_key', 'first_sentence', 'subject_people', 'subject_places'
            ])
        }

        if language and language in self.supported_languages:
            params['language'] = language

        try:
            async with self.session.get(
                f"{self.base_url}/search.json",
                params=params,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return [self._parse_book_item(doc) for doc in data.get('docs', [])]

        except Exception as e:
            logger.error(f"Open Library API request failed: {str(e)}")
            return []

    def _build_query(self, author: Optional[str], title: Optional[str]) -> str:
        """Build search query from parameters"""
        query_parts = []
        if author:
            query_parts.append(f'author:"{author}"')
        if title:
            query_parts.append(f'title:"{title}"')
        return " AND ".join(query_parts) if query_parts else "*:*"

    def _parse_book_item(self, doc: Dict) -> Dict:
        """Parse a single book item from API response"""
        try:
            description = self._get_description(doc)
            language = self._get_language(doc)
            publisher = self._get_publisher(doc)
            pages = doc.get('number_of_pages_median') or doc.get('number_of_pages')
            subjects = self._get_subjects(doc)

            # Detect if book is in Russian
            is_russian = any(
                lang.lower() in ('ru', 'rus', 'russian')
                for lang in doc.get('language', [])
            )

            return {
                'title': doc.get('title', 'Untitled'),
                'first_publish_year': doc.get('first_publish_year'),
                'description': description,
                'language': language,
                'is_russian': is_russian,  # Add Russian detection
                'number_of_pages': pages,
                'isbn_10': self._get_isbn(doc, 10),
                'isbn_13': self._get_isbn(doc, 13),
                'author_name': doc.get('author_name', []),
                'author_key': doc.get('author_key', []),
                'subject': subjects,
                'ratings_average': doc.get('ratings_average'),
                'ratings_count': doc.get('ratings_count'),
                'key': doc.get('key'),
                'cover_url': self._get_cover_url(doc),
                'publisher': publisher,
                'publish_date': self._get_publish_date(doc),
                'first_sentence': self._get_first_sentence(doc)
            }
        except Exception as e:
            logger.error(f"Error parsing book item: {str(e)}")
            return {}

    def _structure_data(self, raw_books: List[Dict]) -> Tuple:
        """Structure raw book data into database-ready format"""
        authors = []
        genres = []
        books = []
        book_authors = []
        book_genres = []

        seen_authors = set()
        seen_genres = set()

        for book in raw_books:
            if not book.get('title'):
                continue

            book_id = str(uuid.uuid4())

            books.append({
                'id': book_id,
                'title': book['title'],
                'year_published': book.get('first_publish_year'),
                'summary': book.get('description') or self._generate_summary(book),
                'language': book.get('language', self.default_language),
                'is_russian': book.get('is_russian', False),  # Include Russian flag
                'book_size_pages': book.get('number_of_pages'),
                'book_size_description': self._get_size_description(book.get('number_of_pages')),
                'isbn_10': book.get('isbn_10'),
                'isbn_13': book.get('isbn_13'),
                'source_url': f"{self.base_url}{book.get('key', '')}",
                'age_rating': self._get_age_rating(book.get('subject')),
                'average_rating': book.get('ratings_average'),
                'rating_details': self._get_rating_details(book),
                'cover_url': book.get('cover_url'),
                'publisher': book.get('publisher', self.default_publisher)
            })

            # Process authors
            for i, author_name in enumerate(book.get('author_name', [])):
                if not author_name:
                    continue

                author_key = book.get('author_key', [None] * len(book['author_name']))[i]

                if author_name not in seen_authors:
                    author_id = str(uuid.uuid4())
                    authors.append({
                        'id': author_id,
                        'name': author_name,
                        'key': author_key,
                        'source_url': f"{self.base_url}/authors/{author_key}" if author_key else None
                    })
                    seen_authors.add(author_name)
                else:
                    author_id = next(a['id'] for a in authors if a['name'] == author_name)

                book_authors.append({
                    'book_id': book_id,
                    'author_id': author_id
                })

            # Process genres
            for subject in book.get('subject', []):
                normalized_genre = self._normalize_genre(subject)
                if not normalized_genre:
                    continue

                if normalized_genre not in seen_genres:
                    genre_id = str(uuid.uuid4())
                    genres.append({
                        'id': genre_id,
                        'name': normalized_genre,
                        'original_name': subject
                    })
                    seen_genres.add(normalized_genre)
                else:
                    genre_id = next(g['id'] for g in genres if g['name'] == normalized_genre)

                book_genres.append({
                    'book_id': book_id,
                    'genre_id': genre_id
                })

        return authors, genres, books, book_authors, book_genres

    # ... (keep all existing helper methods unchanged) ...

    # Helper methods
    def _get_description(self, doc: Dict) -> str:
        description = doc.get('description')
        if isinstance(description, dict):
            description = description.get('value')
        if not description:
            first_sentence = doc.get('first_sentence')
            if isinstance(first_sentence, dict):
                first_sentence = first_sentence.get('value')
            if first_sentence:
                return f"{first_sentence}..."
        return description or self.default_summary

    def _get_language(self, doc: Dict) -> str:
        languages = doc.get('language', [])
        if languages:
            lang = languages[0]
            if isinstance(lang, dict):
                return lang.get('key', self.default_language)
            return lang
        return self.default_language

    def _get_publisher(self, doc: Dict) -> str:
        publisher = doc.get('publisher')
        if isinstance(publisher, list):
            return publisher[0] if publisher else self.default_publisher
        return publisher or self.default_publisher

    def _get_subjects(self, doc: Dict) -> List[str]:
        subjects = []
        for field in ['subject', 'subject_people', 'subject_places']:
            items = doc.get(field, [])
            if isinstance(items, str):
                subjects.append(items)
            else:
                subjects.extend(items)
        return subjects

    def _get_isbn(self, doc: Dict, length: int) -> Optional[str]:
        isbns = doc.get('isbn', [])
        if isbns:
            for isbn in isbns:
                if len(isbn) == length:
                    return isbn
        specific_field = doc.get(f'isbn_{length}', [])
        return specific_field[0] if specific_field else None

    def _get_cover_url(self, doc: Dict) -> Optional[str]:
        cover_id = doc.get('cover_i')
        if cover_id:
            return f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
        return None

    def _get_publish_date(self, doc: Dict) -> Optional[str]:
        publish_date = doc.get('publish_date')
        if isinstance(publish_date, list):
            return publish_date[0] if publish_date else None
        return publish_date

    def _get_first_sentence(self, doc: Dict) -> Optional[str]:
        first_sentence = doc.get('first_sentence')
        if isinstance(first_sentence, dict):
            return first_sentence.get('value')
        return first_sentence

    def _generate_summary(self, book: Dict) -> str:
        parts = []
        if book.get('first_publish_year'):
            parts.append(f"First published in {book['first_publish_year']}.")
        if book.get('publisher'):
            parts.append(f"Published by {book['publisher']}.")
        if book.get('subject'):
            parts.append(f"Topics include: {', '.join(book['subject'][:3])}.")
        return ' '.join(parts) or self.default_summary

    def _get_size_description(self, pages: Optional[int]) -> Optional[str]:
        if not pages:
            return None
        if pages < 50: return "Very Short"
        if pages < 150: return "Short"
        if pages < 300: return "Medium"
        if pages < 500: return "Long"
        return "Very Long"

    def _get_age_rating(self, subjects: List[str]) -> Optional[str]:
        if not subjects:
            return None

        age_keywords = {
            'juvenile': 'Children',
            'young adult': 'Teen',
            'children': 'Children',
            'teen': 'Teen',
            'adult': 'Adult'
        }

        for subject in subjects:
            lower_subject = subject.lower()
            for keyword, rating in age_keywords.items():
                if keyword in lower_subject:
                    return rating
        return None

    def _get_rating_details(self, book: Dict) -> Optional[str]:
        if not book.get('ratings_average'):
            return None

        return json.dumps({
            'open_library': {
                'rating': book['ratings_average'],
                'votes': book.get('ratings_count', 0),
                'want_to_read': book.get('want_to_read', 0)
            }
        })

    def _normalize_genre(self, genre: str) -> Optional[str]:
        if not genre:
            return None

        genre = genre.strip().title()

        # Remove common prefixes/suffixes
        removals = ['fiction', 'literature', 'books', 'stories', 'printed']
        for r in removals:
            genre = genre.replace(r, '').strip()

        # Specific normalizations
        genre_mappings = {
            'Sci-fi': 'Science Fiction',
            'Sci Fi': 'Science Fiction',
            'Sf': 'Science Fiction',
            'Fantasy Fiction': 'Fantasy',
            'Mystery And Suspense Fiction': 'Mystery'
        }

        return genre_mappings.get(genre, genre)