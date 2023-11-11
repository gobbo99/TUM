import logging


class LiveFeedHandler(logging.FileHandler):
    def __init__(self, path):
        super().__init__(mode='w', filename=path)

    def close(self):
        pass




