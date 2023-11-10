import os
import logging
import signal
from subprocess import Popen
import utility.package_installer


class LiveFeedHandler(logging.FileHandler):
    def __init__(self, formatter, path):
        super().__init__(mode='a', filename=path)
        self.setFormatter(formatter)

    def close(self):
        pass




