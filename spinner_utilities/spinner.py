import sys
import threading
import time
from typing import Callable, Any

from .frames import spinner_frames
from utility.ansi_codes import AnsiCodes

fg_colors = {
    'black': "\033[0;30m",
    'red': "\033[0;31m",
    'green': "\033[0;32m",
    'yellow': "\033[0;33m",
    'blue': "\033[0;34m",
    'purple': "\033[0;35m",
    'cyan': "\033[0;36m",
    'white': "\033[0;37m",
    'magenta': "\033[0;35m",
    'reset': "\u001b[0m",
    'nc': "\033[00m",
}


class SpinnerManager:
    active_spinner = None


class Spinner:
    busy = False
    delay = 0.1

    def spinner_generator(self):
        while True:
            for frame in self.spinner_frames:
                yield frame

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args, **kwargs) -> Any:
            with self:
                return func(*args, **kwargs)

        return wrapper

    def __enter__(self):
        if SpinnerManager.active_spinner is not None:
            return
        self.busy = True
        SpinnerManager.active_spinner = self
        sys.stdout.write(AnsiCodes.remove_cursor())
        threading.Thread(target=self.spinner_task).start()

    def __exit__(self, exception, value, tb):
        self.busy = False
        sys.stdout.write(AnsiCodes.erase_line(1))
        sys.stdout.write(AnsiCodes.add_cursor())
        sys.stdout.write('\r')
        sys.stdout.flush()
        SpinnerManager.active_spinner = None

    def __init__(self, **kwargs):
        self.text = kwargs.get('text')
        self.color = kwargs.get('color')
        self.spinner_frames = colorize_frames(kwargs.get('color'), spinner_frames[kwargs.get('spinner_type')])
        color = kwargs.get('color')
        frames = spinner_frames.get(kwargs.get('spinner_type'))
        self.spinner_frames = colorize_frames(color, frames)

        delay = kwargs.get('delay')
        if delay and float(delay):
            self.delay = delay

        self.spinner_generator = self.spinner_generator()

    def spinner_task(self):
        while self.busy:
            sys.stdout.write('\r')
            sys.stdout.write(f'{self.text} {next(self.spinner_generator)}')
            sys.stdout.write(AnsiCodes.erase_line(0))
            sys.stdout.flush()
            time.sleep(self.delay)


def colorize_frames(color, frames):
    if color in fg_colors.keys():
        return [f'{fg_colors[color]}{frame}\033[0m' for frame in frames]
