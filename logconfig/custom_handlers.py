import os
import logging
import signal
import time
from subprocess import Popen
import multiprocessing


class LiveFeedHandler(logging.FileHandler):
    def __init__(self, formatter, path):
        super().__init__(mode='w', filename=path)
        self.setFormatter(formatter)
        self.process = Popen(['xfce4-terminal', '--disable-server', '--execute', 'tail', '-f', f'{path}'], preexec_fn=os.setpgrp)
        self.process = Popen(['gnome-terminal', '--disable-factory', '--', 'tail', '-f', f'{path}'], preexec_fn=os.setpgrp)

    def close(self):
        os.killpg(self.process.pid, signal.SIGINT)








