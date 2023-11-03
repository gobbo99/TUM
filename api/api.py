import logging
import json
from urllib.parse import urlparse

import requests
from requests.exceptions import *

from utility.url_tools import generate_string_5_30
from utility import green, red, bgreen, bred, byellow, yellow
from exceptions.tinyurl_exceptions import *
from utility.url_tools import get_final_domain
from tunneling.tunnelservicehandler import TunnelServiceHandler


BASE_URL = "https://api.tinyurl.com"
SUCCESS = 25
logger = logging.getLogger('')


class Api:
    def __init__(self, auth_tokens: [], fallback_urls=None):
        self.id_token_mapping = {}
        for i in range(1, len(auth_tokens)):
            self.id_token_mapping[i] = auth_tokens[i-1]
        self.token_id = 1
        self.tunneling_service = TunnelServiceHandler(fallback_urls)
        self.rebuild_headers()

    def create_tinyurl(self, target_url):
        self.rebuild_headers(self.auth_tokens[index])
        self.check_target_url(target_url)
        length = 5
        while True:
            try:
                payload = {'url': target_url,
                           'alias': generate_string_5_30(length=length),
                           'expires_at': None
                           }
                response = requests.post(url=f'{BASE_URL}/create', headers=self.headers, data=json.dumps(payload), timeout=5)
                response.raise_for_status()
                data = response.json()['data']
                final_url = f'https://{data["url"]}' if not urlparse(data['url']).scheme else data['url']
                domain = get_final_domain(final_url)
                tinyurl = f"https://tinyurl.com/{data['alias']}"
                return tinyurl, final_url, domain
            except RequestException:
                raise RequestError(target_url)
            except HTTPError as e:
                if response.json()['errors']:
                    if response.json()['errors'][0] == 'Alias is not available.':
                        length += 1
                        continue
                    raise TinyUrlCreationError(response.json(['errors']), response.status_code)
                else:
                    raise TinyUrlCreationError([e], response.status_code)
            except Timeout:
                raise NetworkError('Connection error. Request timed out!')
            except ValueError:
                raise NetworkError("Can't find ['data'] in response! Check Tinyurl docs")

    def update_tinyurl_redirect(self, url):
        pass

    def switch_auth_token(self, token_index):
        self.auth_token = self.auth_tokens[token_index]

    def rebuild_headers(self):
        self.headers = {'Authorization': f'Bearer {self.id_token_mapping[self.token_id]}', 'Content-Type': 'application/json',
                        'User-Agent': 'Google Chrome'}

    @staticmethod
    def check_target_url(url):
        try:
            response = requests.head(url)
            if urlparse(response.url).netloc == urlparse(url).netloc:
                return
            response.raise_for_status()
            return
        except RequestException:
            raise RequestError(f"Invalid or inaccessible resource {url}")
        except HTTPError as e:
            raise RequestError(f"Error for {url}: {e}")
        except Timeout:
            raise NetworkError('Connection error. Request timed out!')
