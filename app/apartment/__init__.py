import logging
import os
from logging.handlers import RotatingFileHandler
from time import perf_counter

import psycopg2
from flask import Flask, Response, g, jsonify, render_template, request
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import generate_password_hash

from .auth import AdminUser, auth
from .database import connect, initialize_schema
from .views import main

REQUESTS = Counter(
    "apartment_http_requests_total",
    "HTTP requests handled by the apartment management app.",
    ["method", "endpoint", "status"],
)
LATENCY = Histogram(
    "apartment_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5),
)


class JsonFormatter(logging.Formatter):
    def format(self, record):
        import json
        from datetime import datetime, timezone

        payload = {
            "time": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ("event", "method", "path", "status", "duration_ms", "username"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(app):
    log_path = os.environ.get("LOG_FILE", "/app/logs/app.json")
    handler = RotatingFileHandler(log_path, maxBytes=5_000_000, backupCount=3)
    handler.setFormatter(JsonFormatter())
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False


def create_app():
    required = ("APP_ADMIN_USERNAME", "APP_ADMIN_PASSWORD", "SESSION_SECRET")
    missing = [key for key in required if not os.environ.get(key)]
    if missing:
        raise RuntimeError("Missing required secrets: " + ", ".join(missing))
    if len(os.environ["APP_ADMIN_PASSWORD"]) < 20:
        raise RuntimeError("APP_ADMIN_PASSWORD must contain at least 20 characters.")
    if len(os.environ["SESSION_SECRET"]) < 32:
        raise RuntimeError("SESSION_SECRET must contain at least 32 characters.")
    if len(os.environ.get("DB_PASSWORD", "")) < 20:
        raise RuntimeError("DB_PASSWORD must contain at least 20 characters.")

    app = Flask(__name__)
    app.config.update(
        SECRET_KEY=os.environ["SESSION_SECRET"],
        ADMIN_USERNAME=os.environ["APP_ADMIN_USERNAME"],
        ADMIN_PASSWORD_HASH=generate_password_hash(os.environ["APP_ADMIN_PASSWORD"]),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_HTTPONLY=True,
        WTF_CSRF_TIME_LIMIT=3600,
        MAX_CONTENT_LENGTH=1_048_576,
    )
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    CSRFProtect(app)
    configure_logging(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Vui lòng đăng nhập để tiếp tục."
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        if user_id == app.config["ADMIN_USERNAME"]:
            return AdminUser(user_id)
        return None

    app.register_blueprint(auth)
    app.register_blueprint(main)

    @app.before_request
    def start_timer():
        g.started_at = perf_counter()

    @app.after_request
    def record_request(response):
        if request.endpoint != "metrics":
            endpoint = request.endpoint or "unmatched"
            elapsed = perf_counter() - getattr(g, "started_at", perf_counter())
            REQUESTS.labels(request.method, endpoint, str(response.status_code)).inc()
            LATENCY.labels(request.method, endpoint).observe(elapsed)
            app.logger.info(
                "http_request",
                extra={
                    "event": "http_request",
                    "method": request.method,
                    "path": request.path,
                    "status": response.status_code,
                    "duration_ms": round(elapsed * 1000, 2),
                    "username": current_user.get_id() if current_user.is_authenticated else None,
                },
            )
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        return response

    @app.get("/healthz")
    def healthz():
        try:
            with connect() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            return jsonify(status="ok", database="ok"), 200
        except psycopg2.Error:
            app.logger.exception("database_health_check_failed")
            return jsonify(status="degraded", database="unavailable"), 503

    @app.get("/metrics")
    def metrics():
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", code=404, message="Không tìm thấy trang."), 404

    @app.errorhandler(500)
    def server_error(_error):
        app.logger.exception("unhandled_server_error")
        return render_template("error.html", code=500, message="Đã có lỗi. Vui lòng thử lại."), 500

    with app.app_context():
        initialize_schema()

    return app
