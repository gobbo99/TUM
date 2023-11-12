import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, ALL_COMPLETED
from queue import Queue, Empty, Full
from threading import Event
from typing import List
from urllib.parse import urlparse

import settings
from api.apiclient import ApiClient
from exceptions.tinyurl_exceptions import TinyUrlCreationError, TinyUrlUpdateError, NetworkError, \
    RequestError
from tinyurl import TinyUrl
from utility.ansi_codes import AnsiCodes
from utility.url_network_tools import get_valid_urls, check_redirect_url
from spinner_utilities.spinner import Spinner

AUTH_TOKENS = settings.AUTH_TOKENS
TUNNELING_SERVICE_URLS = settings.TUNNELING_SERVICE_URLS


class TinyUrlManager:
    def __init__(self, shared_queue: Queue, control_event: Event, feedback_event: Event, app_config: dict = None):
        self.selected_id: int = None
        self.id_tinyurl_mapping = OrderedDict()
        if app_config:
            self.auth_tokens: List[str] = app_config['tokens']
            self.ping_interval: int = app_config.get('delay') or 60
            self.fallback_urls: List[str] = app_config.get('fallback_urls')
        else:
            self.shared_queue: Queue = shared_queue
            self.control_event: Event = control_event
            self.feedback_event: Event = feedback_event
            self.fallback_urls: List[str] = get_valid_urls(TUNNELING_SERVICE_URLS)
            self.auth_tokens: List[str] = AUTH_TOKENS
            self.ping_interval: int = settings.PING_INTERVAL

        self.api_client = ApiClient(self.auth_tokens, self.fallback_urls)
        self.token_id = 1

    @Spinner(text='Sending request to create...', spinner_type='bouncing_ball', color='cyan', delay=0.03)
    def create_tinyurl(self, url: str, no_check: bool = False, new_id: int = None):
        new_id = new_id or self.get_next_available_id()
        try:
            new_tinyurl = TinyUrl(new_id)
            new_tinyurl.instantiate_tinyurl(url, self.api_client, no_check=no_check)
            queue_data = {'update': {'tinyurl': new_tinyurl.tinyurl,
                                     'domain': new_tinyurl.domain, 'id': new_tinyurl.id}}
            self._enqueue(queue_data)
            self.id_tinyurl_mapping[new_tinyurl.id] = new_tinyurl
            return new_tinyurl
        except (TinyUrlCreationError, RequestError, NetworkError, ValueError) as e:
            raise e

    @Spinner(text='Sending request to update...', spinner_type='bouncing_ball', color='cyan', delay=0.03)
    def update_tinyurl(self, url: str):
        try:
            updated_tinyurl: TinyUrl = self.id_tinyurl_mapping[self.selected_id]
            updated_tinyurl.update_redirect(url, self.api_client)
            queue_data = {'update': {'tinyurl': updated_tinyurl.tinyurl, 'domain': updated_tinyurl.domain,
                                     'id': updated_tinyurl.id}}
            self._enqueue(queue_data)
        except (TinyUrlUpdateError, RequestError, NetworkError) as e:
            raise e

    @interface
    def create_from_list(self, urls_list: List[str], wait_time: int = 60):
        assigned_id = self.get_next_available_id()
        urls = []
        tinyurls = []
        invalid_urls = []

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
                    valid = check_redirect_url(tinyurl, target_domain)
                    if valid:
                        tinyurls.append(future.result())
                    else:
                        invalid_urls.append(future.result().tinyurl)

                    _, not_completed = wait(futures, return_when=ALL_COMPLETED)
                    return tinyurls, None
            except TimeoutError as e:
                return tinyurls, e
            except Exception as e:
                return tinyurls, e

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

    def process_item(self):
        try:
            data = self.shared_queue.get()
            self.shared_queue.task_done()
        except Empty:
            raise Empty
        for key, data in data.items():
            for tinyurl in self.id_tinyurl_mapping.values():
                if key == tinyurl.alias:
                    tinyurl.final_url = data['full_url']
                    tinyurl.domain = data['domain']

    def _enqueue(self, data: dict):
        while self.feedback_event.is_set():
            time.sleep(0.2)
        try:
            self.control_event.set()
            self.shared_queue.put(data)
        except Exception as e:
            print(f'Exception in _enqueue: {e}')
        except Full:
            print('Exception queue full!')
