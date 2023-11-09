import logging
from datetime import datetime
import re
from utility.ansi_codes import marked

from utility.ansi_codes import success, error, warning, info


def colorize_urls(text, color):
    # Regular expression pattern to match URLs
    url_pattern = r'(https://\S+)'
    # Use re.sub to replace URLs with colorized versions
    return re.sub(url_pattern, f"{marked}\\1{color}", text)


class ColoredFormatter(logging.Formatter):
    def __init__(self):
        super().__init__("\033[0m%(custom_time)s %(message)s")

    # Define color codes
    WHITE = "\033[1;37m"
    BRIGHT_RED = "\033[1;31m"
    YELLOW = "\033[0;33m"
    GREEN = "\033[0;32m"
    BRIGHT_YELLOW = "\033[1;33m"
    CYAN = "\033[0;36m"
    RESET = "\033[0m"

    def format(self, record):
        # Set the appropriate color based on the log level
        if record.levelno == logging.ERROR:
            color_code = error + ' ' + self.BRIGHT_RED
            color = self.BRIGHT_RED
        elif record.levelno == logging.getLevelName('SUCCESS'):
            color_code = success + ' ' + self.GREEN
            color = self.BRIGHT_RED + self.GREEN
        elif record.levelno == logging.INFO:
            color_code = info + ' ' + self.YELLOW
            color = self.BRIGHT_RED + self.YELLOW
        elif record.levelno == logging.WARNING:
            color_code = warning + ' ' + self.BRIGHT_YELLOW
            color = self.BRIGHT_YELLOW
        else:
            color_code = info + ' ' + self.YELLOW
            color = self.YELLOW

        record.custom_time = datetime.now().strftime('%H:%M')
        # Add color codes to the log message
        record.msg = colorize_urls(f"{color_code}{record.msg}{self.RESET}", color)
        return super().format(record)


class DebugFormatter(logging.Formatter):

    def format(self, record):
        record.custom_time = datetime.now().strftime('%Y-%m-%d, %H:%M')
        return super().format(record)


