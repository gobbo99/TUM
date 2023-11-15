import logging
from pathlib import Path
import datetime

from .custom_formatters import ColoredFormatter, DebugFormatter
from .custom_handlers import LiveFeedHandler

logger = logging.getLogger('')


def initialize_live_logger(path):
    color_formatter = ColoredFormatter()
    temp_handler = LiveFeedHandler(path)
    temp_handler.setFormatter(color_formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(temp_handler)


def initialize_file_logger(path):
    created_at = datetime.datetime.now().strftime('%c') + '.txt'
    logs_path = Path(path)
    log_dir = logs_path / '.tum_logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    file_path = log_dir / created_at
    file_path.touch()
    file_handler = logging.FileHandler(file_path)
    debug_formatter = DebugFormatter("%(custom_time)s - %(levelname)s - %(message)s")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(debug_formatter)
    logger.addHandler(file_handler)


def initialize_loggers(config):
    logs_path = Path(config['logs_path'])
    log_dir = logs_path / '.tum_logs'
    log_dir.mkdir(parents=True, exist_ok=True)

    if config['use_logger']:
        initialize_file_logger(config['logs_path'])

    temp_path = log_dir / 'temp'
    temp_path.touch()
    initialize_live_logger(temp_path)
