"""Gunicorn configuration for TradeX Platform Onboarding Portal."""

from __future__ import annotations

import multiprocessing
import os

# Bind to the port assigned by the hosting platform (defaults to 8000 locally).
port = os.getenv("PORT", "8000")
bind = f"0.0.0.0:{port}"

# Worker configuration
workers = max(2, multiprocessing.cpu_count() // 2 + 1)
worker_class = "gthread"
threads = int(os.getenv("GUNICORN_THREADS", "4"))
worker_tmp_dir = "/tmp"

# Timeouts
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))

# Access and error logs
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

# Preload the application for faster worker start-up.
preload_app = True
