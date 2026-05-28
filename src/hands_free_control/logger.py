# ============================================================
# logger.py - Centralised logging via loguru
# ============================================================

import sys
import os

try:
    from .config import DATA_DIR
except ImportError:
    from config import DATA_DIR

try:
    from loguru import logger
except ImportError:
    import logging
    from logging.handlers import RotatingFileHandler

    logger = logging.getLogger("hands_free")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()

    if sys.stderr is not None:
        _console = logging.StreamHandler(sys.stderr)
        _console.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s - %(message)s", "%H:%M:%S"))
        _console.setLevel(logging.DEBUG)
        logger.addHandler(_console)

    _LOGURU_AVAILABLE = False
else:
    _LOGURU_AVAILABLE = True

LOG_DIR = os.path.join(DATA_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "hands_free.log")

if _LOGURU_AVAILABLE:
    # Remove default handler, add custom ones
    logger.remove()

    if sys.stderr is not None:
        # Windowed PyInstaller apps do not have a console stream.
        logger.add(
            sys.stderr,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - {message}",
            level="DEBUG",
            colorize=True,
        )

    # File: full detail, rotating
    logger.add(
        LOG_FILE,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="5 MB",
        retention="7 days",
        compression="zip",
    )
else:
    _file = RotatingFileHandler(LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3)
    _file.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"))
    _file.setLevel(logging.DEBUG)
    logger.addHandler(_file)

log = logger
