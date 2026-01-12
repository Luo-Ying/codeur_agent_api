import logging
import os
from logging.handlers import TimedRotatingFileHandler
import datetime

def _get_level_from_env():
    env = os.getenv("ENV", "development").lower()
    if env in {"development", "test"}:
        return logging.DEBUG
    elif env == "staging":
        return logging.INFO  # can be adjusted to DEBUG if needed
    elif env == "production":
        return logging.INFO  # can be adjusted to WARNING if needed
    else:
        return logging.INFO

def get_log_dir():
    log_dir = os.getenv("LOG_DIR")
    print(f"log_dir: {log_dir}")
    if not log_dir:
        raise ValueError("LOG_DIR is not set")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

def setup_logging():
    log_dir = get_log_dir()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"{today}.log")
    root = logging.getLogger()
    if root.handlers:
        return # already setup
    level = _get_level_from_env()
    root.setLevel(level)
    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | %(message)s')
    # Console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    # File (rotated daily, keep 30 days)
    file_handler = TimedRotatingFileHandler(
        log_file,
        when="midnight",
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(console_handler)
    root.addHandler(file_handler)

# _LOG_DIR = get_log_dir()
# _LEVEL_FROM_ENV = _get_level_from_env()

# class Logging:
#     def __init__(self, name: str = __name__):
#         self.logger = logging.getLogger(name)
#         self.logger.setLevel(_LEVEL_FROM_ENV)
#         self.logger.addHandler(logging.StreamHandler())
#         self.logger.addHandler(logging.FileHandler(_LOG_FILE))

#     def get_logger(self) -> logging.Logger:
#         return self.logger

#     def info(self, message: str):
#         self.logger.info(message)

#     def warning(self, message: str):
#         self.logger.warning(message)

#     def error(self, message: str):
#         self.logger.error(message)