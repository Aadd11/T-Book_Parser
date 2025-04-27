
## API Endpoints

### Open Library API
- `GET /api/search/openlib`
  - Parameters:
    - `author` (optional): Author name
    - `title` (optional): Book title
    - `max_results` (optional, default=50): Max results to return
    - `lang` (optional, default=en): Language (en/ru)

### Google Books API
- `GET /api/search/google`
  - Parameters same as Open Library API
 
### Return JSON Example
{
  "metadata": {
    "source": "Google Books",
    "query": {
      "author": "Tolkien",
      "title": null,
      "max_results": 5
    },
    "result_stats": {
      "books": 5,
      "authors": 3,
      "genres": 4
    },
    "execution_time": "0.45s",
    "timestamp": "2025-04-28T14:30:00Z",
    "language": "ru"
  },
  "data": {
    "entities": {
      "authors": [
        {
          "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
          "name": "Дж. Р. Р. Толкин"
        }
      ],
      "genres": [
        {
          "id": "3fa85f64-5717-4562-b3fc-2c963f66afa7",
          "name": "Fantasy"  // Жанры не переводятся
        }
      ],
      "books": [
        {
          "id": "3fa85f64-5717-4562-b3fc-2c963f66afa8",
          "title": "Властелин колец",
          "year_published": 1954,
          "summary": "Эпическая фэнтезийная сага...", 
          "language": "en",
          "book_size_pages": 423,
          "book_size_description": "Long",
          "isbn_10": "0618640150",
          "isbn_13": "9780618640157",
          "average_rating": 4.5,
          "rating_details": {
            "google_books": {
              "rating": 4.5,
              "votes": 1200
            }
          },
          "source_url": "https://books.google.com/...",
          "thumbnail": "http://books.google.com/...jpg"
        }
      ]
    },
    "relationships": {
      "book_authors": [
        {
          "book_id": "3fa85f64-5717-4562-b3fc-2c963f66afa8",
          "author_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
        }
      ],
      "book_genres": [
        {
          "book_id": "3fa85f64-5717-4562-b3fc-2c963f66afa8",
          "genre_id": "3fa85f64-5717-4562-b3fc-2c963f66afa7"
        }
      ]
    }
  }
}

## Deployment

### 1. Build Image
```bash
docker build -t t-book_parser:prod --target production .
```

### 2. Run Production Container
```bash
docker run -d -p 8080:5000 \
  -e FLASK_ENV=production \
  -e GOOGLE_BOOKS_API_KEY=your_key \
  --name tbook_prod t-book_parser:prod
```


