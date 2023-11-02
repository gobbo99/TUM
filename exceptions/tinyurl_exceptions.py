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


class NetworkException(Exception):
    pass


def handle_tinyurl_response(tiny_url, response):
    if response.status_code in range(200, 300):
        return 0
    if response.status_code == 401:
        logging.error(f'You are not authorized to access this resource or token: {tiny_url.auth_token} is blocked!'
                      f'Error code: ' + str(response.status_code))
        return -1
    if response.status_code == 405:
        logging.error(f'You do not have the permission to see this resource! Error code: {response.status_code}')
        return -2
    if response.status_code == 422:
        logging.error(f'Error with the request! Error code: {response.status_code}')
        return -2
    if response.status_code > 500:
        logging.error(f'Error status code: {response.status_code}, Response: {response.text}')
        return -2

