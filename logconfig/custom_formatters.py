import logging
import re
from datetime import datetime

from utility.ansi_codes import AnsiCodes, SUCCESS, ERROR, WARNING, INFO, MARKED


def colorize_urls(text, color):
    url_pattern = r'(https?://[^\s\'"]+)'
    return re.sub(url_pattern, f"{MARKED}\\1{color}", text)


class ColoredFormatter(logging.Formatter):
    def __init__(self):
        super().__init__("\033[0m%(custom_time)s %(message)s")

    def format(self, record):
        if record.levelno == logging.ERROR:
            color_code = ERROR + ' ' + AnsiCodes.BRED
            color = AnsiCodes.BRED
        elif record.levelno == logging.getLevelName('SUCCESS'):
            color_code = SUCCESS + ' ' + AnsiCodes.GREEN
            color = AnsiCodes.GREEN
        elif record.levelno == logging.INFO:
            color_code = INFO + ' ' + AnsiCodes.YELLOW
            color = AnsiCodes.YELLOW
        elif record.levelno == logging.WARNING:
            color_code = WARNING + ' ' + AnsiCodes.CYAN
            color = AnsiCodes.CYAN
        else:
            color_code = INFO + ' ' + AnsiCodes.YELLOW
            color = AnsiCodes.YELLOW

        record.custom_time = datetime.now().strftime('%H:%M')

        record.msg = colorize_urls(f"{color_code}{record.msg}{AnsiCodes.RESET}", color)
        return super().format(record)


class DebugFormatter(logging.Formatter):

    def format(self, record):
        record.custom_time = datetime.now().strftime('%Y-%m-%d, %H:%M')
        return super().format(record)


