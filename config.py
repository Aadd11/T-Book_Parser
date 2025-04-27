import os


class Config:
    # Google Books API
    GOOGLE_BOOKS_API_KEY = "AIzaSyC5VzDhemjM9n1CV6HWG8DyOWdYtPYDAdM" #os.getenv('GOOGLE_BOOKS_API_KEY', '')

    # Translation
    TRANSLATION_TIMEOUT = 15
    MAX_TEXT_LENGTH = 1000
    CACHE_SIZE = 10000

    # System
    MAX_THREADS = min(8, os.cpu_count() or 4)
    REQUEST_TIMEOUT = 200

    # Local Translation
    ARGOS_PACKAGES = ["translate-en_ru"]

    GOOGLE_TRANSLATE_ENABLED = True