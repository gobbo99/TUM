import time

import requests
from requests import RequestException

import logging
import json

import settings
from utility import *
from consts import BASE_URL
from exceptions.tinyurl_exceptions import handle_tinyurl_response, TinyUrlCreationError, TinyUrlUpdateError
from tunneling.tunnelservicehandler import TunnelServiceHandler

logger = logging.getLogger('')
SUCCESS = 25


class TinyUrl:

    def __init__(self, auth_token, fallback_urls, new_id):
        self.tunneling_service = TunnelServiceHandler(fallback_urls)
        self.id = new_id
        self.tinyurl = None
        self.redirect_url_short = None
        self.redirect_url_long = None
        self.auth_token = auth_token
        self.existing_strings = set()
        self.rebuild_headers()

    def create_redirect_url(self, redirect_url: str):
        request_url = f"{BASE_URL}/create"
        attempts = 3
        alias = generate_unique_string(self.existing_strings)
        self.existing_strings.add(alias)

        data = {'url': redirect_url,
                'alias': alias
                }

        while attempts != 0:
            response = requests.post(url=request_url, headers=self.headers, data=json.dumps(data))
            result = handle_tinyurl_response(self, response)
            if result == 0:
                data = response.json()['data']
                tiny_domain = data['domain']
                self.redirect_url_long = data['url']
                self.redirect_url_short = get_short_domain(self.redirect_url_long)
                self.tinyurl = f"https://{tiny_domain}/{data['alias']}"
                logger.log(SUCCESS, f'{green}Tinyurl ({self.id}) added!')
                return 0
            else:
                attempts -= 1

        raise TinyUrlCreationError(result)

    def update_redirect_service(self):
        request_url = f"{BASE_URL}/change"
        initial_attempts = 3
        while initial_attempts != 0:
            data = {
                'domain': 'tinyurl.com',
                'alias': self.tinyurl.strip('/').split('/')[-1],
                'url': self.redirect_url_long
            }
            response = requests.patch(url=request_url, headers=self.headers, data=json.dumps(data))
            try:
                check = requests.head(self.tinyurl, allow_redirects=True)   #  do this for regular redirect too and create?
                check.raise_for_status()
            except RequestException:
                break

            if handle_tinyurl_response(self, check) == 0:
                if 'tiny' in check.url:
                    time.sleep(1)
                    initial_attempts -= 1
                else:
                    data = response.json()['data']
                    logger.log(SUCCESS, f"{bgreen}Tinyurl ({self.id}) redirect updated! {self.redirect_url_short} -> {data['url']}")
                    self.redirect_url_long = data['url']
                    self.redirect_url_short = get_short_domain(self.redirect_url_long)
                    return True
            else:
                time.sleep(1)
                initial_attempts -= 1

        attempts = 0
        while attempts < self.tunneling_service.length:
            print(f'attempts: {attempts}')
            data = {
                'domain': 'tinyurl.com',
                'alias': self.tinyurl.strip('/').split('/')[-1],
                'url': self.tunneling_service.tunneler
            }
            response = requests.patch(url=request_url, headers=self.headers, data=json.dumps(data))
            if handle_tinyurl_response(self, response) == 0:
                if 'tiny' in requests.head(self.tinyurl, allow_redirects=True).url:
                    self.tunneling_service.cycle_next()
                    attempts += 1
                else:
                    data = response.json()['data']
                    logger.log(SUCCESS, f"{bgreen}Tinyurl ({self.id}) redirect updated! {self.redirect_url_short} -> {data['url']}")
                    self.redirect_url_long = data['url']
                    self.redirect_url_short = get_short_domain(self.redirect_url_long)
                    return True
            else:
                self.tunneling_service.cycle_next()
                attempts += 1

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
            return 0
        else:
            raise TinyUrlUpdateError(response.text, response.status_code)

    def rebuild_headers(self):
        self.headers = {'Authorization': f'Bearer {self.auth_token}', 'Content-Type': 'application/json',
                        'User-Agent': 'Google Chrome'}

    def __str__(self):
        return f'\n{yellow}ID: {self.id}\n________\n\nToken: {self.auth_token}\nURL: {self.tinyurl}\nRedirect URL: '\
               f'{self.redirect_url_long}{reset}'
