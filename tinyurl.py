import random
import time
import json
import logging
from urllib.parse import urlparse

import requests

from utility import *
from consts import BASE_URL
from exceptions.tinyurl_exceptions import TinyUrlCreationError, TinyUrlUpdateError
from tunneling.tunnelservicehandler import TunnelServiceHandler

logger = logging.getLogger('')
SUCCESS = 25


class TinyUrl:

    def __init__(self, auth_token, fallback_urls, new_id):
        self.tunneling_service = TunnelServiceHandler(fallback_urls)
        self.id = new_id
        self.auth_token = auth_token
        self.tinyurl = None
        self.domain = None
        self.final_url = None
        self.existing_strings = set()
        self.rebuild_headers()

    def create_redirect_url(self, redirect_url: str):
        request_url = f"{BASE_URL}/create"
        alias = generate_unique_string(self.existing_strings)
        self.existing_strings.add(alias)

        payload = {'url': redirect_url,
                   'alias': alias
                  }
        try:
            response = requests.post(url=request_url, headers=self.headers, data=json.dumps(payload))
            data = response.json()['data']
        except:
            return False

        if response.status_code / 100 == 2:
            self.final_url = f'https://{data["url"]}' if not urlparse(data['url']).scheme else data['url']
            self.domain = get_final_domain(self.final_url)
            self.tinyurl = f"https://tinyurl.com/{alias}"
            logger.log(SUCCESS, f'{green}Tinyurl ({self.id}) added!')
            return True
        else:
            raise TinyUrlCreationError(response.json()['errors'], response.status_code)

    def update_redirect_service(self):
        request_url = f"{BASE_URL}/change"
        payload = {
            'domain': 'tinyurl.com',
            'alias': self.tinyurl.strip('/').split('/')[-1],
            'url': self.final_url
        }
        attempts = 0
        while attempts < 3:
            try:
                response = requests.patch(url=request_url, headers=self.headers, data=json.dumps(payload))
            except Exception as e:
                continue

            if response.status_code / 100 == 2:
                try:
                    check = requests.head(url=self.tinyurl, allow_redirects=True)
                except Exception as e:
                    break
                if get_final_domain(check.url) == self.domain:
                    logger.log(SUCCESS, f"{bgreen}Tinyurl({self.id}) preview page successfully removed!")
                    return True
                else:
                    time.sleep(random.uniform(1,5))
                    attempts += 1

        payload['url'] = self.tunneling_service.tunneler
        attempts = 0

        while attempts < self.tunneling_service.length:
            try:
                response = requests.patch(url=request_url, headers=self.headers, data=json.dumps(payload))
            except Exception:
                break

            if response.status_code / 100 == 2:
                data = response.json()['data']
                check = requests.head(url=self.tinyurl, allow_redirects=True)
                if get_final_domain(check.url) == get_final_domain(self.tunneling_service.tunneler):
                    self.final_url = f'https://{data["url"]}' if not urlparse(data['url']).scheme else data['url']
                    logger.log(SUCCESS,f"{bgreen}Tinyurl ({self.id}) redirect updated! {self.domain}/.. -> {self.final_url}")
                    self.domain = get_final_domain(self.final_url)
                    return True
                else:
                    time.sleep(random.uniform(1,5))
                    attempts += 1
                    continue

            logger.warning(f'({self.id}) Failed to update to {self.tunneling_service.tunneler}...')
            self.tunneling_service.cycle_next()
            logger.warning(f'({self.id}) Cycling to {self.tunneling_service.tunneler}!')

        return False

    def update_redirect(self, url):
        request_url = f"{BASE_URL}/change"
        payload = {
            'domain': 'tinyurl.com',
            'alias': self.tinyurl.strip('/').split('/')[-1],
            'url': url
        }
        try:
            response = requests.patch(url=request_url, headers=self.headers, data=json.dumps(payload))
        except Exception:
            pass
        if response.status_code / 100 == 2:
            data = response.json()['data']
            logger.log(SUCCESS, f"{bgreen}Tinyurl ({self.id}) redirect updated! {self.domain} -> {data['url']}!")
            self.final_url = f'https://{data["url"]}' if not urlparse(data['url']).scheme else data['url']
            self.final_url = data['url']
            self.domain = get_final_domain(url)
        else:
            raise TinyUrlUpdateError(response.json()['errors'], response.status_code)

    def rebuild_headers(self):
        self.headers = {'Authorization': f'Bearer {self.auth_token}', 'Content-Type': 'application/json',
                        'User-Agent': 'Google Chrome'}

    def __str__(self):
        return f'\n{yellow}ID: {self.id}\n________\n\nToken: {self.auth_token}\nURL: {self.tinyurl}\nRedirect URL: '\
               f'{self.final_url}{reset}'
