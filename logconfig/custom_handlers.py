import os
import logging
import signal
from subprocess import Popen
import utility.package_installer


class LiveFeedHandler(logging.FileHandler):
    def __init__(self, path):
        super().__init__(mode='w', filename=path)

    def close(self):
        pass




