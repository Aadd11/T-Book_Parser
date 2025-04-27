from flask import Flask
from flask_cors import CORS
from translation.translator import TranslationManager
import logging


def create_app():
    app = Flask(__name__)
    CORS(app)

    # Initialize translation
    TranslationManager.initialize()

    # Register blueprints
    from api.google_books import google_books_bp
    from api.open_library import open_lib_bp
    from api.health import health_bp

    app.register_blueprint(google_books_bp, url_prefix='/api')
    app.register_blueprint(open_lib_bp, url_prefix='/api')
    app.register_blueprint(health_bp, url_prefix='/api')

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, threaded=True)