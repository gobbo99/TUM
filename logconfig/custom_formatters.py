import logging
from datetime import datetime

from utility.ansi_colors import success, error, warning, info


class ColoredFormatter(logging.Formatter):

    # Define color codes
    GREEN = "\033[0;32m"
    RED = "\033[1;31m"
    YELLOW = "\033[0;33m"
    CYAN = "\033[0;36m"
    RESET = "\033[0m"

    def format(self, record):
        # Set the appropriate color based on the log level
        if record.levelno == logging.ERROR:
            color_code = error + ' ' + self.RED
        elif record.levelno == logging.getLevelName('SUCCESS'):
            color_code = success + ' ' + self.GREEN
        elif record.levelno == logging.INFO:
            color_code = info + ' ' + self.YELLOW
        elif record.levelno == logging.WARNING:
            color_code = warning + ' ' + self.CYAN
        else:
            color_code = info + ' ' + self.YELLOW

        record.custom_time = datetime.now().strftime('%H:%M')
        # Add color codes to the log message
        record.msg = f"{color_code}{record.msg}{self.RESET}"
        return super().format(record)


class DebugFormatter(logging.Formatter):

    def format(self, record):
        record.custom_time = datetime.now().strftime('%Y-%m-%d, %H:%M')
        return super().format(record)

