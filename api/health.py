from flask import Blueprint, jsonify
from translation.translator import TranslationManager
import datetime

health_bp = Blueprint('health', __name__)

@health_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.datetime.utcnow().isoformat(),
        "translation": {
            "initialized": TranslationManager._translator is not None,
            "type": TranslationManager._translator.__class__.__name__
        }
    })