import threading
from logging import LoggerAdapter

thread_local_logging = threading.local()


def set_threadlocal_log_adapter(adapter: LoggerAdapter):
    thread_local_logging.logger_adapter = adapter


def log() -> LoggerAdapter:
    return thread_local_logging.logger_adapter
