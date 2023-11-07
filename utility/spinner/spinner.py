import functools
import sys
import time
import inspect
import threading
from typing import Callable, Any

from utility.ansi_colors import ansi_fg_colors
from .frames import spinner_frames


class SpinnerManager:
    active_spinner = None


class Spinner:
    _active_spinner = None
    busy = False
    delay = 0.1

    def spinning_cursor(self):
        while True:
            for frame in self.spinner_frames: yield frame

    def __call__(self, func: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args, **kwargs) -> Any:
            with self:
                return func(*args, **kwargs)

        return wrapper

    def __init__(self, **kwargs):
        self.text = kwargs.get('text')
        self.spinner_frames = spinner_frames[kwargs.get('spinner_type')]
        delay = kwargs.get('delay')
        if delay and float(delay): self.delay = delay
        if kwargs.get('color'):
            self.spinner_frames = colorize_spinner(kwargs.get('color'), self.spinner_frames)
        self.spinner_generator = self.spinning_cursor()

    def spinner_task(self):
        while self.busy:
            sys.stdout.write('\r' + self.text + ' ' + next(self.spinner_generator))
            sys.stdout.write('\033[K')
            sys.stdout.flush()
            time.sleep(self.delay)

    def __enter__(self):
        if SpinnerManager.active_spinner is not None:
            return
        self.busy = True
        SpinnerManager.active_spinner = self
        sys.stdout.write('\033[?25l')  # Remove cursor
        threading.Thread(target=self.spinner_task).start()

    def __exit__(self, exception, value, tb):
        self.busy = False
        SpinnerManager.active_spinner = None
        sys.stdout.write('\033[1K')  # Clear the line
        sys.stdout.write('\033[?25h')  # Add back cursor
        sys.stdout.write('\r')
        sys.stdout.flush()
        if not Exception:
            SpinnerManager.active_spinner = None
            self.busy = False
            sys.stdout.write('\033[1K')  # Clear the line
            sys.stdout.write('\033[?25h')  # Add back cursor
            sys.stdout.write('\r')
            sys.stdout.flush()


def colorize_spinner(color, frames):
    if color in ansi_fg_colors.keys():
        return [f'{ansi_fg_colors[color]}{frame}\033[0m' for frame in frames]
