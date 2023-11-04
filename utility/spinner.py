import sys
import time
import threading
import codecs

bouncing_ball = [
            "\033[0;36m(●        )",
            "( ●       )",
            "(  ●      )",
            "(   ●     )",
            "(    ●    )",
            "(     ●   )",
            "(      ●  )",
            "(       ● )",
            "(        ●)",
            "(       ● )",
            "(      ●  )",
            "(     ●   )",
            "(    ●    )",
            "(   ●     )",
            "(  ●      )",
            "( ●       )",
            "(●        )"
        ]
cool = ['●      ●',' ●    ● ','   ● ●  ','   ●●   ','   ● ●  ',' ●    ● ','●      ●']


class Spinner:
    busy = False
    delay = 0.1

    @staticmethod
    def spinning_cursor():
        while True:
            for ball in bouncing_ball: yield ball

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            with self:
                return func(*args, **kwargs)

        return wrapper

    def __init__(self, delay=None):
        self.spinner_generator = self.spinning_cursor()
        if delay and float(delay): self.delay = delay

    def spinner_task(self):
        while self.busy:
            sys.stdout.write('\r' + next(self.spinner_generator))
            sys.stdout.write('\033[K')
            sys.stdout.write('\b')
            sys.stdout.flush()
            time.sleep(self.delay)

    def __enter__(self):
        self.busy = True
        threading.Thread(target=self.spinner_task).start()

    def __exit__(self, exception, value, tb):
        sys.stdout.write('\033[0m')
        sys.stdout.flush()
        self.busy = False
        time.sleep(self.delay)
        if exception is not None:
            return False
