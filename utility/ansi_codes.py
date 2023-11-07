from sys import stdout
from time import sleep


def slow_print(text, letter_time):
    for letter in text + '\n':
        stdout.write(letter)
        stdout.flush()
        sleep(letter_time)


# Color snippets
black = "\033[0;30m"
red = "\033[0;31m"
bred = "\033[1;31m"
green = "\033[0;32m"
bgreen = "\033[1;32m"
yellow = "\033[0;33m"
byellow = "\033[1;33m"
blue = "\033[0;34m"
bblue = "\033[1;34m"
purple = "\033[0;35m"
bpurple = "\033[1;35m"
cyan = "\033[0;36m"
bcyan = "\033[1;36m"
white = "\033[0;37m"
bwhite = "\033[1;37m"
bmagenta = "\u001b[45;1m"
nc = "\033[00m"
reset = "\u001b[0m"

ansi_fg_colors = {
    'black': '\033[30m',
    'red': '\033[31m',
    'green': '\033[32m',
    'yellow': '\033[33m',
    'blue': '\033[34m',
    'magenta': '\033[35m',
    'cyan': '\033[36m',
    'bcyan': '\033[1;36m',
    'white': '\033[37m',
    'reset': '\033[0m'  # Reset color to default
}

success = f"{yellow}[{bgreen}√{yellow}]"
error = f"{yellow}[{bred}X{yellow}]"
info = f"{yellow}[{bred}\u2022{yellow}]"
warning = f"{yellow}[{bwhite}!{yellow}]"

cursor_up = '\x1b[1A'
erase_line = '\x1b[2K'
