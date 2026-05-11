from os import getenv

from core.logging import setup_logging

bind = getenv("GUNICORN_BIND", "127.0.0.1:8000")
workers = int(getenv("GUNICORN_WORKERS", "2"))
timeout = int(getenv("GUNICORN_TIMEOUT", "30"))
accesslog = "-"
errorlog = "-"
loglevel = getenv("GUNICORN_LOG_LEVEL", "info")
logconfig_dict = setup_logging(
    log_format=getenv("DJ_LOG_FORMAT", "json"),
    level=loglevel.upper(),
)
