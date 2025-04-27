
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


