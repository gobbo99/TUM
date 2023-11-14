import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, ALL_COMPLETED, TimeoutError
from queue import Queue, Empty, Full
from threading import Event
from typing import List, Dict, Optional
from urllib.parse import urlparse

import settings
from api.apiclient import ApiClient
from exceptions.tinyurl_exceptions import TinyUrlCreationError, TinyUrlUpdateError, NetworkError, \
    RequestError, UnwantedDomain, NetworkException
from tinyurl import TinyUrl
from utility.ansi_codes import AnsiCodes
from utility.url_network_tools import get_valid_urls, check_redirect_url
from spinner_utilities.spinner import Spinner

AUTH_TOKENS = settings.AUTH_TOKENS
TUNNELING_SERVICE_URLS = settings.TUNNELING_SERVICE_URLS


class TinyUrlManager:
    use_spinner = False

    def __init__(self, shared_queue: Queue = None, control_event: Event = None, feedback_event: Event = None,
                 app_config: Dict[str, List[str]] = None):

        if app_config:
            self.auth_tokens: List[str] = app_config.get('tokens')
            self.fallback_urls: List[str] = app_config.get('urls', [])
            self.use_spinner = False
        else:
            self.shared_queue: Optional[Queue] = shared_queue
            self.control_event: Optional[Event] = control_event
            self.feedback_event: Optional[Event] = feedback_event
            self.fallback_urls: List[str] = get_valid_urls(TUNNELING_SERVICE_URLS)
            self.auth_tokens: List[str] = AUTH_TOKENS
            self.ping_interval: int = settings.PING_INTERVAL
            self.selected_id = None
            self.use_spinner = True

        self.id_tinyurl_mapping = OrderedDict()
        self.api_client = ApiClient(self.auth_tokens, self.fallback_urls)
        self.token_id = 1

    @Spinner(text='Sending request to create...', spinner_type='bouncing_ball', color='cyan', delay=0.03, special=True)
    def create_tinyurl(self, url: str, no_check: bool = False, new_id: int = None):
        new_id = new_id or self.get_next_available_id()
        try:
            new_tinyurl = TinyUrl(new_id)
            new_tinyurl.instantiate_tinyurl(url, self.api_client, no_check=no_check)
            queue_data = {'update': {'tinyurl': new_tinyurl.tinyurl,
                                     'domain': new_tinyurl.domain, 'id': new_tinyurl.id}}
            if self.use_spinner:
                self._enqueue(queue_data)
            self.id_tinyurl_mapping[new_tinyurl.id] = new_tinyurl
            return new_tinyurl
        except (TinyUrlCreationError, RequestError, NetworkError, ValueError) as e:
            raise e

    @Spinner(text='Sending request to update...', spinner_type='bouncing_ball', color='cyan', delay=0.03, special=True)
    def update_tinyurl(self, url: str):
        try:
            updated_tinyurl: TinyUrl = self.id_tinyurl_mapping[self.selected_id]
            updated_tinyurl.update_redirect(url, self.api_client)
            queue_data = {'update': {'tinyurl': updated_tinyurl.tinyurl, 'domain': updated_tinyurl.domain,
                                     'id': updated_tinyurl.id}}
            if self.use_spinner:
                self._enqueue(queue_data)
        except (TinyUrlUpdateError, RequestError, NetworkError) as e:
            raise e

    def create_from_list(self, urls_list: List[str], wait_time: int = 60):
        assigned_id = self.get_next_available_id()
        urls = []
        result = {'errors': [], 'created': [], 'invalid_redirect': []}

        for url in urls_list:
            if not urlparse(url).scheme:
                url_with_schema = 'https://' + url
            else:
                url_with_schema = url
            urls.append(url_with_schema)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(self.create_tinyurl, url, True, assigned_id + i) for i, url in
                       enumerate(urls)]
            try:
                for future in as_completed(futures, timeout=wait_time):
                    tinyurl = future.result().tinyurl
                    target_domain = future.result().domain
                    final_redirect = future.result().final_url
                    valid = check_redirect_url(tinyurl, target_domain)
                    if valid:
                        result['created'].append({'url': tinyurl, 'redirect': final_redirect})
                    else:
                        result['invalid_redirect'].append(future.result().tinyurl)
                        self.id_tinyurl_mapping.pop(future.result().id)
                    wait(futures, return_when=ALL_COMPLETED)

            except TimeoutError as e:
                result['errors'].append(e)
            except Exception as e:
                result['errors'].append(e)
            return result

    def self_check(self, timeout=60):
        result = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(check_redirect_url, t.tinyurl, t.domain, True) for t in self.id_tinyurl_mapping.values()]
            for future, tinyurl, domain in as_completed(futures, timeout=timeout):
                try:
                    future.result()
                except UnwantedDomain as e:
                    result.update({tinyurl: e})
                except TimeoutError as e:
                    result.update({tinyurl: str(e)})
                except NetworkException as e:
                    result.update({tinyurl: e})

        return result

    def cycle_next_token(self):
        return self.api_client.cycle_next_token()

    def get_token(self):
        return self.api_client.token_selected

    def get_all(self):
        return self.id_tinyurl_mapping

    def print_all(self):
        for tinyurl in self.id_tinyurl_mapping.values():
            print(f'{AnsiCodes.YELLOW}{tinyurl}')

    def print_short(self):
        for id, tinyurl in sorted(self.id_tinyurl_mapping.items()):
            if len(tinyurl.final_url) > 32:
                extra_space = (11 - len(tinyurl.alias)) * ' '
                print(f'{AnsiCodes.YELLOW}{id}. {tinyurl.tinyurl}{extra_space}-->  http://{tinyurl.domain}/...')
            else:
                extra_space = (11 - len(tinyurl.alias)) * ' '
                print(f'{AnsiCodes.YELLOW}{id}. {tinyurl.tinyurl}{extra_space}-->  {tinyurl.final_url} ')

    def print_tokens(self):
        for index, token in enumerate(self.auth_tokens):
            print(f'{AnsiCodes.WHITE}{index + 1}. - {token}')
        print(
            f'\n{AnsiCodes.BWHITE}Current token:\n{AnsiCodes.GREEN}{self.token_id}. - {self.api_client.auth_tokens[self.token_id - 1]}')

    def get_next_available_id(self):
        if self.id_tinyurl_mapping.keys():
            last_id = max(self.id_tinyurl_mapping.keys())
            assigned_id = last_id + 1
        else:
            assigned_id = 1
        return assigned_id

    def process_item(self, data):
        for key, value in data.items():
            if key == 'delete':
                self.id_tinyurl_mapping.pop(value)
                return value
            for tinyurl in self.id_tinyurl_mapping.values():
                if key == tinyurl.alias:
                    tinyurl.final_url = value['full_url']
                    tinyurl.domain = value['domain']

    def _enqueue(self, data: dict):
        while self.feedback_event.is_set():
            time.sleep(0.2)
        try:
            self.control_event.set()
            self.shared_queue.put(data)
        except Full:
            print('Exception queue full!')
        except Exception as e:
            print(f'Exception in _enqueue: {str(e)}')
