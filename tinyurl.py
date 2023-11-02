import time

import requests

import logging
import json

import settings
from utility import *
from consts import BASE_URL
from exceptions.tinyurl_exceptions import handle_tinyurl_response, TinyUrlCreationError, TinyUrlUpdateError
from tunneling.tunnelservicehandler import TunnelServiceHandler

tunneling_service = TunnelServiceHandler(settings.TUNNELING_SERVICE_URLS)
logger = logging.getLogger('')
SUCCESS = 25


class TinyUrl:

    def __init__(self, token, new_id):
        self.id = new_id
        self.tinyurl = None
        self.redirect_url_short = None
        self.redirect_url_long = None
        self.auth_token = token
        self.existing_strings = set()
        self.alternate_tunnel = tunneling_service.set_tunneling_service()
        self.rebuild_headers()

    def create_redirect_url(self, redirect_url: str):
        request_url = f"{BASE_URL}/create"
        attempts = 3
        alias = generate_unique_string(self.existing_strings)
        self.existing_strings.add(alias)

        data = {'url': redirect_url,
                'alias': alias
                }

        status_code = None

        while attempts != 0:
            response = requests.post(url=request_url, headers=self.headers, data=json.dumps(data))
            if handle_tinyurl_response(self, response) == 0:
                data = response.json()['data']
                tiny_domain = data['domain']
                self.redirect_url_long = data['url']
                self.redirect_url_short = get_short_domain(self.redirect_url_long)
                self.tinyurl = f"https://{tiny_domain}/{data['alias']}"
                logger.log(SUCCESS, f'{bgreen}Tinyurl ({self.id}) successfully created!')
                return 0
            else:
                attempts -= 1
                status_code = str(response.status_code)

        raise TinyUrlCreationError(f'Tinyurl not created!', status_code=status_code)

    def update_redirect_service(self):
        request_url = f"{BASE_URL}/change"
        attempts = len(settings.AUTH_TOKENS) + 3
        initial_attempts = 3
        while initial_attempts != 0:
            data = {
                'domain': 'tinyurl.com',
                'alias': self.tinyurl.strip('/').split('/')[-1],
                'url': self.redirect_url_long
            }
            response = requests.patch(url=request_url, headers=self.headers, data=json.dumps(data))
            if handle_tinyurl_response(self, response) == 0:
                if 'tiny' in requests.head(self.tinyurl, allow_redirects=True).url:
                    time.sleep(1)
                    initial_attempts -= 1
                else:
                    data = response.json()['data']
                    logger.log(SUCCESS, f"{bgreen}Tinyurl ({self.id}) redirect updated! {self.redirect_url_short} -> {data['url']}")
                    self.redirect_url_long = data['url']
                    self.redirect_url_short = get_short_domain(self.redirect_url_long)
                    return True

        while attempts > 3:
            data = {
                'domain': 'tinyurl.com',
                'alias': self.tinyurl.strip('/').split('/')[-1],
                'url': self.alternate_tunnel
            }
            response = requests.patch(url=request_url, headers=self.headers, data=json.dumps(data))
            status_code = handle_tinyurl_response(self, response)
            if status_code == 0:
                if 'tiny' in requests.head(self.tinyurl, allow_redirects=True).url:
                    self.alternate_tunnel = tunneling_service.cycle_next()
                    attempts -= 1
                else:
                    data = response.json()['data']
                    logger.log(SUCCESS, f"{bgreen}Tinyurl ({self.id}) redirect updated! {self.redirect_url_short} -> {data['url']}")
                    self.redirect_url_long = data['url']
                    self.redirect_url_short = get_short_domain(self.redirect_url_long)
                    return True
            else:
                self.alternate_tunnel = tunneling_service.cycle_next()
                attempts -= 1

        return False

    def update_redirect(self, url):
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
            logger.log(SUCCESS, f"{bgreen}Tinyurl ({self.id}) redirect updated! {self.redirect_url_short} -> {data['url']}")
            self.redirect_url_short = get_short_domain(data['url'])
            self.redirect_url_long = data['url']
            print(self.redirect_url_long)
            return 0
        else:
            raise TinyUrlUpdateError(response.text, response.status_code)

    def rebuild_headers(self):
        self.headers = {'Authorization': f'Bearer {self.auth_token}', 'Content-Type': 'application/json',
                        'User-Agent': 'Google Chrome'}

    def __str__(self):
        return f'\n{yellow}ID: {self.id}\n________\n\nToken: {self.auth_token}\nURL: {self.tinyurl}\nRedirect URL: '\
               f'{self.redirect_url_long}{reset}'
