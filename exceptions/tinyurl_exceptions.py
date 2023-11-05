import logging
from utility.ansi_colors import *


class TinyUrlPreviewException(Exception):
    def __init__(self, id, url):
        self.message = f'Preview page is blocking Tinyurl({id}) for {url}!'
        super().__init__(self.message)

    def __str__(self):
        return self.message


class TinyUrlCreationError(Exception):

    def __init__(self, errors: [], status_code):
        self.errors = errors
        self.status_code = status_code

    def __str__(self):
        message = '\n'.join(self.errors)
        return f'{red}Error HTTP code: [{self.status_code}]\n{message}'


class TinyUrlUpdateError(Exception):
    def __init__(self, errors: [], status_code):
        self.errors = errors
        self.status_code = status_code

    def __str__(self):
        message = '\n'.join(self.errors)
        return f'{red}Error HTTP code: [{self.status_code}]\n{message}'


class InputException(Exception):
    def __init__(self, message):
        self.message = message

    def __str__(self):
        return self.message


class RequestError(Exception):
    def __init__(self, url):
        self.message = f'{red}Redirect url {url} seems to be invalid!'
        super().__init__(self.message)

    def __str__(self):
        return self.message


class NetworkError(Exception):
    def __init__(self, message):
        self.message = f'{red}{message}'
        super().__init__(self.message)

    def __str__(self):
        return self.message

