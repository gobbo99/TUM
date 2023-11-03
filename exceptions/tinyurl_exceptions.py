import logging


class TinyUrlPreviewException(Exception):
    def __init__(self, id, url):
        self.message = f'Preview page is blocking Tinyurl({id}) for {url}!'
        super().__init__(self.message)

    def __str__(self):
        return self.message


class TinyUrlCreationError(Exception):
    def __init__(self, message, status_code):
        self.message = message
        self.status_code = status_code

    def __str__(self):
        return f'{self.message}  [{self.status_code}]'


class TinyUrlUpdateError(Exception):
    def __init__(self, message, status_code):
        self.message = message
        self.status_code = status_code

    def __str__(self):
        return f'{self.message}  [{self.status_code}]'


class InputException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class NetworkException(Exception):
    def __init__(self, url):
        self.message = f'Redirect url {url} seems to be invalid!'
        super().__init__(self.message)

    def __str__(self):
        return self.message
