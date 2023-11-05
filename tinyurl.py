import datetime
import random
import time
import json
import logging
from urllib.parse import urlparse

import requests
from requests.exceptions import *

from utility import *
from api.apiclient import ApiClient
from exceptions.tinyurl_exceptions import TinyUrlCreationError, TinyUrlUpdateError, NetworkError, RequestError

logger = logging.getLogger('')
SUCCESS = 25


class TinyUrl:

    def __init__(self, new_id):
        self.tinyurl = None
        self.alias = None
        self.domain = None
        self.final_url = None
        self.id = new_id

    def instantiate_tinyurl(self, url: str, api_client: ApiClient, expires_at: datetime.datetime = None):
        try:
            data = api_client.create_tinyurl(url, expires_at=expires_at)
            self.final_url = f'https://{data["url"]}' if not urlparse(data['url']).scheme else data['url']  #  Because tinyurl response sometimes omits scheme
            self.domain = get_final_domain(self.final_url)
            self.tinyurl = f"https://tinyurl.com/{data['alias']}"
            self.alias = data['alias']
            logger.log(SUCCESS, f'{green}Tinyurl({self.id}) created! {self.tinyurl} --> {self.final_url}!')
        except (TinyUrlCreationError, RequestError, NetworkError) as e:
            raise e

    def update_redirect(self, url: str, api_client: ApiClient):
        try:
            data = api_client.update_tinyurl_redirect(self.alias, url)
            self.final_url = f'https://{data["url"]}' if not urlparse(data['url']).scheme else data['url']  #  Because tinyurl response sometimes omits scheme
            self.domain = get_final_domain(self.final_url)
            logger.log(SUCCESS, f'{green}Tinyurl({self.id}) updated: {self.tinyurl} --> {self.final_url}!')
        except (TinyUrlUpdateError, RequestError, NetworkError) as e:
            raise e

    def __str__(self):
        return f'\n{yellow}Tinyurl[{self.id}]'\
               f'\n__________________________________'\
               f'\nurl: {self.tinyurl}' \
               f'\ntarget: {self.final_url}'\
               f'\ntoken id: {self.token_id}'

    def __del__(self):
        print(f'{bred}Tinyurl ({self.id}) deleted from the system!')


    """

    def update_redirect_service(self):
        request_url = f"{BASE_URL}/change"
        payload = {
            'domain': 'tinyurl.com',
            'alias': self.tinyurl.strip('/').split('/')[-1],
            'url': self.final_url
        }
        attempts = 0
        while attempts < 3:
            print(attempts)
            try:
                response = requests.patch(url=request_url, headers=self.headers, data=json.dumps(payload), timeout=3)
                response.raise_for_status()
            except RequestException:
                if attempts == 2:
                    logger.debug(f'[self.id]Terminating instance because 3 consecutive network errors!')
                    return False   # Terminate instance
                else:
                    time.sleep(random.uniform(1, 5))
                    attempts += 1
            except HTTPError:
                if 'errors' in response.json():
                    logger.debug(f'Self-updating {self.domain} error: {response.json()["errors"]}')
                    attempts += 1
                continue

            if 99 < response.status_code < 400:
                try:
                    check = requests.head(url=self.tinyurl, allow_redirects=True)
                except HTTPError:
                    break
                except RequestException:
                    break

                if get_final_domain(check.url) == self.domain:
                    logger.log(SUCCESS, f"{bgreen}Tinyurl({self.id}) preview page successfully removed!")
                    return True
                else:
                    break

        payload['url'] = self.tunneling_service.tunneler
        attempts = 0

        while attempts < self.tunneling_service.length:
            try:
                response = requests.patch(url=request_url, headers=self.headers, data=json.dumps(payload))
                response.raise_for_status()
            except RequestException:
                if attempts == 2:
                    logger.debug(f'[self.id]Terminating instance because 3 consecutive network errors!')
                    return False  # Terminate instance
                else:
                    time.sleep(random.uniform(1, 5))
                    attempts += 1
            except HTTPError:
                if 'errors' in response.json():
                    attempts += 1

            if response.status_code / 100 == 2:
                data = response.json()['data']
                check = requests.head(url=self.tinyurl, allow_redirects=True)
                if get_final_domain(check.url) == get_final_domain(self.tunneling_service.tunneler):
                    self.final_url = f'https://{data["url"]}' if not urlparse(data['url']).scheme else data['url']
                    logger.log(SUCCESS,f"{bgreen}Tinyurl ({self.id}) redirect updated! {self.domain}/.. -> {self.final_url}")
                    self.domain = get_final_domain(self.final_url)
                    return True
                else:
                    time.sleep(random.uniform(1, 5))
                    attempts += 1
                    continue

            logger.warning(f'({self.id}) Failed to update to {self.tunneling_service.tunneler}...')
            self.tunneling_service.cycle_next()
            logger.warning(f'({self.id}) Cycling to {self.tunneling_service.tunneler}!')

        return False
"""