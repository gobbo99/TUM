import requests
from tenacity import retry, stop_after_attempt

import logging
import json

import settings
from utility import *
from consts import BASE_URL
from exceptions.tinyurl_exceptions import handle_tinyurl_response, TinyUrlCreationError, TinyUrlUpdateError
from services.heartbeat import tunneling_service

retry_times = len(settings.TUNNELING_SERVICES_URLS)
token_index = 0


class TinyUrl:

    def __init__(self, token):
        self.id = None
        self.tinyurl = None
        self.redirect_url_short = None
        self.redirect_url_long = None
        self.existing_strings = set()
        self.alternate_tunnel = tunneling_service.set_tunneling_service()
        self.auth_token = token
        self.headers = None
        self.rebuild_headers()

    def create_redirect_url(self, redirect_url:str):
        alias = generate_unique_string(self.existing_strings)
        self.existing_strings.add(alias)

        request_url = f"{BASE_URL}/create"
        data = {'url': redirect_url,
                'alias': alias
                }
        redirect_url = redirect_url.split('//')[-1]

        logging.info(f'Creating tinyurl for redirect to {redirect_url}...')
        response = requests.post(url=request_url, headers=self.headers, data=json.dumps(data))
        if handle_tinyurl_response(self, response) == 0:
            data = response.json()['data']
            tiny_domain = data['domain']
            self.redirect_url_short = redirect_url
            self.redirect_url_long = data['url']
            self.tinyurl = f"https://{tiny_domain}/{data['alias']}"
        else:
            raise TinyUrlCreationError(f'{red}Tinyurl not created!', response.status_code)

    def update_redirect(self, url): # when called by main if fail don't retry
        request_url = f"{BASE_URL}/change"

        data = {
            'domain': 'tinyurl.com',
            'alias': self.tinyurl.strip('/').split('/')[-1],
            'url': url
        }

        response = requests.patch(url=request_url, headers=self.headers, data=json.dumps(data))
        status_code = handle_tinyurl_response(self, response)
        if status_code == 0:
            data = response.json()['data']
            logging.info(f"Tinyurl ({self.id}) redirect updated. {self.redirect_url_short} -> {data['url']}")
            self.redirect_url_short = data['url']
            return 0
        else:
            raise TinyUrlUpdateError(f'{red}Tinyurl not updated!', response.status_code)

    def rebuild_headers(self):
        self.headers = {'Authorization': f'Bearer {self.auth_token}', 'Content-Type': 'application/json',
                        'User-Agent': 'Google Chrome'}

    def __str__(self):
        return f'\n{yellow}ID: {self.id}\n________\n\nToken: {self.auth_token}\nURL: {self.tinyurl}\nRedirect URL: {self.redirect_url_long}{reset}'