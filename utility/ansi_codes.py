from sys import stdout
from time import sleep


class AnsiCodes:
    RESET = '\033[0m'
    BOLD = '\033[1m'
    ITALIC = '\033[3m'
    UNDERLINE = '\033[4m'
    REVERSE = '\033[7m'

    # Foreground colors
    BLACK = '\033[0;30m'
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[0;33m'
    BLUE = '\033[0;34m'
    MAGENTA = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[0;37m'

    # Bold foreground colors
    BBLACK = '\033[1;30m'
    BRED = '\033[1;31m'
    BGREEN = '\033[1;32m'
    BYELLOW = '\033[1;33m'
    BBLUE = '\033[1;34m'
    BMAGENTA = '\033[1;35m'
    BCYAN = '\033[1;36m'
    BWHITE = '\033[1;37m'

    # Background colors
    BG_BLACK = '\033[40m'
    BG_RED = '\033[41m'
    BG_GREEN = '\033[42m'
    BG_YELLOW = '\033[43m'
    BG_BLUE = '\033[44m'
    BG_MAGENTA = '\033[45m'
    BG_CYAN = '\033[46m'
    BG_WHITE = '\033[47m'

    # Bold background colors
    BBG_BLACK = '\033[1;40m'
    BBG_RED = '\033[1;41m'
    BBG_GREEN = '\033[1;42m'
    BBG_YELLOW = '\033[1;43m'
    BBG_BLUE = '\033[1;44m'
    BBG_MAGENTA = '\033[1;45m'
    BBG_CYAN = '\033[1;46m'
    BBG_WHITE = '\033[1;47m'

    @staticmethod
    def move_cursor_up(n):
        return f'\033[{n}A'

    @staticmethod
    def move_cursor_down(n):
        return f'\033[{n}B'

    @staticmethod
    def move_cursor_forward(n):
        return f'\033[{n}C'

    @staticmethod
    def move_cursor_back(n):
        return f'\033[{n}D'

    @staticmethod
    def erase_line(n):          # 0 - cursor to right, 1 - cursor to left, 2 - entire line
        return f'\033[{n}K'

    @staticmethod
    def add_cursor():
        return '\033[?25h'

    @staticmethod
    def remove_cursor():
        return '\033[?25l'


SUCCESS = f"{AnsiCodes.YELLOW}[{AnsiCodes.BGREEN}√{AnsiCodes.YELLOW}]"
ERROR = f"{AnsiCodes.YELLOW}[{AnsiCodes.BRED}X{AnsiCodes.YELLOW}]"
INFO = f"{AnsiCodes.YELLOW}[{AnsiCodes.BRED}\u2022{AnsiCodes.YELLOW}]"
WARNING = f"{AnsiCodes.YELLOW}[{AnsiCodes.BWHITE}!{AnsiCodes.YELLOW}]"
MARKED = "\033[4;40;93m"


def slow_print(text, letter_time):
    for letter in text + '\n':
        stdout.write(letter)
        stdout.flush()
        sleep(letter_time)
