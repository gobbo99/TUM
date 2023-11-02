import logging


class TinyUrlPreviewException(Exception):
    def __init__(self, id, url):
        self.message = f'Preview page is blocking Tinyurl({id}) for {url}!'
        super().__init__(self.message)

    def __str__(self):
        return self.message


class TinyUrlCreationError(Exception):
    def __init__(self, message):
        self.message = message


class TinyUrlUpdateError(Exception):
    def __init__(self, message, status_code):
        self.message = message
        self.status_code = status_code

    def __str__(self):
        return f'{self.message}  [{self.status_code}]'


class InputException(Exception):
    def __init__(self, message):
        self.message = message


class NetworkException(Exception):
    def __init__(self, url):
        self.message = f'Redirect url {url} seems to be invalid!'
        super().__init__(self.message)

    def __str__(self):
        return self.message


def handle_tinyurl_response(tiny_url, response):
    if response.status_code in range(200, 300):
        return 0
    if response.status_code == 401:
        return f'You are not authorized to access this resource or token: {tiny_url.auth_token} might be blocked! [401]'
    if response.status_code == 405:
        return f'You do not have the permission to see this resource! [{response.status_code}]'
    if response.status_code == 422:
        return f'Invalid request data! [{response.status_code}]'
    if response.status_code > 500 or response.status_code == 0:
        return f'Server error! {response.status_code}'

