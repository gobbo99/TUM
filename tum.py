from typing import Dict, List, Any, Tuple, Optional
from threading import  Event
from queue import Queue
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, ALL_COMPLETED
from collections import OrderedDict

from tinyurl import TinyUrl
from api.apiclient import ApiClient
from utility import *
from exceptions.tinyurl_exceptions import TinyUrlCreationError, TinyUrlUpdateError, InputException, NetworkError, \
    RequestError
import settings


class TinyUrlManager:
    def __init__(self, shared_queue: Queue, update_event: Event, app_config: dict = None):
        self.selected_id: int = None
        self.auth_tokens: [] = None  # identical to authclients
        self.id_tinyurl_mapping = OrderedDict()
        self.shared_queue = shared_queue
        self.update_event = update_event
        self.ping_interval = settings.PING_INTERVAL
        if app_config:
            data = {
                'delay': app_config['delay'],
            }
            self.shared_queue.put_nowait(data)
            self.fallback_urls = get_valid_urls(app_config['fallback_urls'])
            self.auth_tokens = app_config['auth_tokens']
        else:
            data = {
                'delay': self.ping_interval,
            }
            self.shared_queue.put_nowait(data)
            self.fallback_urls = get_valid_urls(settings.TUNNELING_SERVICE_URLS)
            self.auth_tokens = settings.AUTH_TOKENS

        self.api_client = ApiClient(self.auth_tokens, fallback_urls=self.fallback_urls)
        self.token_id = 1

    @Spinner(text='Sending request to create...', spinner_type='bouncing_ball', color='bcyan', delay=0.05)
    def create_tinyurl(self, url: str, no_check: bool = False, new_id: int = None):
        if not new_id:
            new_id = self.get_next_available_id()
        try:
            new_tinyurl = TinyUrl(new_id)
            new_tinyurl.instantiate_tinyurl(url, self.api_client, no_check=no_check)
            self.id_tinyurl_mapping[new_tinyurl.id] = new_tinyurl
            queue_data = {'new': {'url': new_tinyurl.tinyurl, 'domain': new_tinyurl.domain}}
            self.shared_queue.put_nowait(queue_data)
            return new_tinyurl
        except (TinyUrlCreationError, RequestError, NetworkError, ValueError) as e:
            raise e

    @Spinner(text='Sending request to update...', spinner_type='bouncing_ball', color='bcyan', delay=0.05)
    def update_tinyurl(self, url: str):
        try:
            updated_tinyurl: TinyUrl = self.id_tinyurl_mapping[self.selected_id]
            updated_tinyurl.update_redirect(url, self.api_client)
            queue_data = {'update': {'url': updated_tinyurl.tinyurl, 'domain': updated_tinyurl.domain}}

            self.shared_queue.put_nowait(queue_data)
        except (TinyUrlUpdateError, RequestError, NetworkError) as e:
            raise e

    def delete_tinyurl(self, id):
        pass

    @Spinner(text='Creating urls from list...', spinner_type='pulse_horizontal', color='cyan', delay=0.04)
    def create_from_list(self, urls: List[str]):
        next_available_id = self.get_next_available_id()
        added_schema_urls = []

        for url in urls:
            if not urlparse(url).scheme:
                url_with_schema = 'https://' + url
            else:
                url_with_schema = url
            added_schema_urls.append(url_with_schema)

        with ThreadPoolExecutor(max_workers=4) as executor:  # Adjust max_workers as needed
            futures = [executor.submit(self.create_tinyurl, url, True, next_available_id + i) for i, url in enumerate(added_schema_urls)]
            wait(futures, return_when=ALL_COMPLETED)

        for future in as_completed(futures):
            try:
                tinyurl_obj = future.result()
                self.id_tinyurl_mapping[tinyurl_obj.id] = tinyurl_obj
            except Exception:
                pass

    def print_all(self):
        for tinyurl in self.id_tinyurl_mapping.values():
            print(f'{yellow}{tinyurl}')

    def print_short(self):
        for id, tinyurl in sorted(self.id_tinyurl_mapping.items()):
            if len(tinyurl.final_url) > 32:
                extra_space = (11 - len(tinyurl.alias)) * ' '
                print(f'{yellow}{id}. {tinyurl.tinyurl}{extra_space}-->  http://{tinyurl.domain}/...')
            else:
                extra_space = (11 - len(tinyurl.alias)) * ' '
                print(f'{yellow}{id}. {tinyurl.tinyurl}{extra_space}-->  {tinyurl.final_url} ')

    def print_tokens(self):
        for index, token in enumerate(self.auth_tokens):
            print(f'{white}{index + 1}. - {token}')
        print(f'\n{bwhite}Current token:\n{green}{self.token_id}. - {self.api_client.auth_tokens[self.token_id - 1]}')

    def process_updated_data(self, data: dict):
        for key, data in data.items():
            if key == 'patch':
                for obj in self.id_tinyurl_mapping.values():
                    if obj.alias == data['alias']:
                         obj.final_url = data['target_url']
                         obj.domain = data['domain']
            else:
                pass

    def get_next_available_id(self):
        if self.id_tinyurl_mapping.keys():
            last_id = max(self.id_tinyurl_mapping.keys())
            assigned_id = last_id + 1
        else:
            assigned_id = 1

        return assigned_id




