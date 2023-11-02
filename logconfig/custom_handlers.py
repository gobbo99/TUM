import os
import logging
import time
from subprocess import Popen
import multiprocessing


class LiveFeedHandler(logging.FileHandler):
    def __init__(self, formatter, path):
        super().__init__(mode='w', filename=path)
        self.path = path
        self.setFormatter(formatter)
        self.new_process = multiprocessing.Process(target=self.do_this)
        self.new_process.daemon = True
        self.new_process.start()


    def do_this(self):
        Popen(['gnome-terminal', '--', 'tail', '-f', f'{self.path}'])

    def close(self):
        self.new_process.close()
        self.new_process.terminate()








