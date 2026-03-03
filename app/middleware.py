import os
import time
import uuid
import logging
from flask import request, g, jsonify

logger = logging.getLogger(__name__)


def register_logging_middleware(app):
    @app.before_request
    def _before():
        g.request_id = str(uuid.uuid4())[:8]
        g.start_time = time.monotonic()

    @app.after_request
    def _after(response):
        duration_ms = round((time.monotonic() - g.start_time) * 1000, 2)
        logger.info(
            "%s %s %s %dms id=%s",
            request.method,
            request.path,
            response.status_code,
            duration_ms,
            g.request_id,
        )
        response.headers["X-Request-Id"] = g.request_id
        return response


def register_auth_middleware(app):
    @app.before_request
    def _check_api_key():
        if not request.path.startswith("/orders"):
            return
        api_key = os.environ.get("API_KEY", "")
        if not api_key:
            return
        if request.headers.get("X-API-Key") != api_key:
            return jsonify({"error": "unauthorized"}), 401
