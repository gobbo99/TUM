import os
import logging
import signal
from subprocess import Popen
import utility.package_installer


class LiveFeedHandler(logging.FileHandler):
    def __init__(self, formatter, path, terminal):
        super().__init__(mode='w', filename=path)
        self.setFormatter(formatter)
        if terminal == 'gnome':
            utility.package_installer.install_gnome_terminal()
            self.process = Popen(['gnome-terminal', '--disable-factory', '--', 'tail', '-f', f'{path}'], preexec_fn=os.setpgrp)
        else:
            utility.package_installer.install_xfce4_terminal()
            self.process = Popen(['xfce4-terminal', '--disable-server', '--execute', 'tail', '-f', f'{path}'], preexec_fn=os.setpgrp)

    def close(self):
        os.killpg(self.process.pid, signal.SIGINT)




