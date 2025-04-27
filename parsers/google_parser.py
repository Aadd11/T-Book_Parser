import asyncio
import requests
import aiohttp
from typing import Dict, List, Optional, Tuple
import uuid
import json
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class GoogleBooksParser:
    def __init__(self, api_key: Optional[str] = None):
        self.base_url = "https://www.googleapis.com/books/v1/volumes"
        self.api_key = api_key
        self.request_delay = 0.1
        self.session = None

    async def initialize(self):
        """Initialize async session"""
        self.session = aiohttp.ClientSession()

    async def close(self):
        """Close async session"""
        if self.session:
            await self.session.close()

    async def get_all_structured_data(
            self,
            author: Optional[str] = None,
            title: Optional[str] = None,
            max_results: int = 200
    ) -> Tuple[List[Dict], List[Dict], List[Dict], List[Dict], List[Dict]]:
        """
        Returns structured data ready for database import:
        (authors, genres, books, book_authors, book_genres)
        """
        raw_books = await self.search_books(author=author, title=title, max_results=max_results)

        authors = []
        genres = []
        books = []
        book_authors = []
        book_genres = []

        seen_authors = set()
        seen_genres = set()

        for book in raw_books:
            book_id = str(uuid.uuid4())
            books.append({
                'id': book_id,
                'title': book['title'],
                'year_published': book['publication_year'],
                'summary': book['summary'],
                'language': book['language'],
                'book_size_pages': book['page_count'],
                'average_rating': book.get('average_rating'),
                'rating_details': json.dumps(book.get('ratings_count', {})),
                'isbn_10': book.get('isbn_10'),
                'isbn_13': book.get('isbn_13'),
                'source_url': book.get('info_link'),
                'age_rating': None,
                'book_size_description': self._get_size_description(book.get('page_count')),
            })

            for author_name in book.get('authors', []):
                if author_name not in seen_authors:
                    authors.append({
                        'id': str(uuid.uuid4()),
                        'name': author_name
                    })
                    seen_authors.add(author_name)

                book_authors.append({
                    'book_id': book_id,
                    'author_id': next(a['id'] for a in authors if a['name'] == author_name)
                })

            for genre_name in book.get('categories', []):
                normalized_genre = self._normalize_genre(genre_name)
                if normalized_genre and normalized_genre not in seen_genres:
                    genres.append({
                        'id': str(uuid.uuid4()),
                        'name': normalized_genre
                    })
                    seen_genres.add(normalized_genre)

                if normalized_genre:
                    book_genres.append({
                        'book_id': book_id,
                        'genre_id': next(g['id'] for g in genres if g['name'] == normalized_genre)
                    })

        return authors, genres, books, book_authors, book_genres

    async def search_books(
            self,
            author: Optional[str] = None,
            title: Optional[str] = None,
            max_results: int = 200,
            batch_size: int = 40
    ) -> List[Dict]:
        """
        Async search for books with pagination support
        """
        batch_size = min(batch_size, 40)
        all_books = []
        start_index = 0

        while len(all_books) < max_results:
            batch = await self._search_batch(
                author=author,
                title=title,
                start_index=start_index,
                max_results=batch_size
            )

            if not batch:
                break

            all_books.extend(batch)
            start_index += len(batch)

            if len(batch) < batch_size:
                break

            await asyncio.sleep(self.request_delay)

        return all_books[:max_results]

    async def _search_batch(
            self,
            author: Optional[str] = None,
            title: Optional[str] = None,
            start_index: int = 0,
            max_results: int = 40
    ) -> List[Dict]:
        """
        Async search for a single batch of books
        """
        query_parts = []
        if author:
            query_parts.append(f"inauthor:{author}")
        if title:
            query_parts.append(f"intitle:{title}")

        if not query_parts:
            return []

        query = "+".join(query_parts)

        params = {
            'q': query,
            'startIndex': start_index,
            'maxResults': min(max_results, 40),
            'printType': 'books'
        }

        if self.api_key:
            params['key'] = self.api_key

        try:
            async with self.session.get(self.base_url, params=params) as response:
                response.raise_for_status()
                data = await response.json()

                books = []
                for item in data.get('items', []):
                    book_info = self._parse_book_item(item)
                    if book_info:
                        books.append(book_info)

                return books

        except Exception as e:
            logger.error(f"Error searching books: {str(e)}")
            return []

    def _parse_book_item(self, item: Dict) -> Optional[Dict]:
        """Parse a single book item from API response"""
        try:
            volume_info = item.get('volumeInfo', {})
            sale_info = item.get('saleInfo', {})

            isbn_10, isbn_13 = None, None
            for id_type in volume_info.get('industryIdentifiers', []):
                if id_type.get('type') == 'ISBN_10':
                    isbn_10 = id_type.get('identifier')
                elif id_type.get('type') == 'ISBN_13':
                    isbn_13 = id_type.get('identifier')

            ratings_info = {}
            if 'averageRating' in volume_info:
                ratings_info['google_books'] = {
                    'rating': volume_info['averageRating'],
                    'votes': volume_info.get('ratingsCount', 0)
                }

            return {
                'title': volume_info.get('title'),
                'publication_year': self._extract_year(volume_info.get('publishedDate', '')),
                'summary': volume_info.get('description'),
                'language': volume_info.get('language'),
                'page_count': volume_info.get('pageCount'),
                'average_rating': volume_info.get('averageRating'),
                'ratings_count': ratings_info,
                'isbn_10': isbn_10,
                'isbn_13': isbn_13,
                'info_link': volume_info.get('infoLink'),
                'authors': volume_info.get('authors', []),
                'categories': volume_info.get('categories', []),
                'publisher': volume_info.get('publisher'),
                'thumbnail': volume_info.get('imageLinks', {}).get('thumbnail')
            }
        except Exception as e:
            logger.error(f"Error parsing book item: {str(e)}")
            return None

    def _extract_year(self, date_str: str) -> Optional[int]:
        """Extract year from date string"""
        if not date_str:
            return None
        try:
            for fmt in ('%Y', '%Y-%m', '%Y-%m-%d'):
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.year
                except ValueError:
                    continue
            return None
        except Exception:
            return None

    def _get_size_description(self, page_count: Optional[int]) -> Optional[str]:
        """Convert page count to size description"""
        if not page_count:
            return None
        if page_count < 50: return "Very Short"
        if page_count < 150: return "Short"
        if page_count < 300: return "Medium"
        if page_count < 500: return "Long"
        return "Very Long"

    def _normalize_genre(self, genre: str) -> Optional[str]:
        """Normalize genre names"""
        if not genre:
            return None
        genre = genre.strip().title()
        if genre.lower() in ['fiction', 'nonfiction']:
            return genre.title()
        return genre.split('/')[0].split('&')[0].strip()