from functools import wraps
import asyncio
import logging
from flask import jsonify
from config import Config

logger = logging.getLogger(__name__)


def async_route(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            task = loop.create_task(f(*args, **kwargs))
            try:
                return loop.run_until_complete(asyncio.wait_for(
                    task,
                    timeout=Config.REQUEST_TIMEOUT
                ))
            except asyncio.TimeoutError:
                task.cancel()
                logger.error("Request timeout")
                return jsonify({"error": "Request timeout"}), 504
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Route handler failed: {str(e)}")
            return jsonify({"error": "Internal server error"}), 500

    return wrapper