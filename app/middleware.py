import time
import uuid
import logging
from flask import request, g

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
