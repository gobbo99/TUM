import logging
import concurrent.futures
import threading
from queue import Queue
import time
from typing import List, Any, Dict

import requests
from requests.exceptions import RequestException, HTTPError, Timeout
from urllib.parse import urlparse

from api.apiclient import ApiClient
from utility.ansi_colors import red, yellow, green

logger = logging.getLogger('')
SUCCESS = 25
KEYS = ('ping_sweep', 'new', 'delay')


class HeartbeatService:
    def __init__(self, api_client: ApiClient, shared_queue: Queue, ping_event):
        self.ping_sweep: threading.Event = ping_event
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.api_client = api_client
        self.shared_queue = shared_queue
        self.delay = 60
        self.alias_url_mapping = {}
        self.errors = {}  # Dictionary to store URL errors {target_url: errors: []}
        self.preview_errors = []  #  Dictionary to store URLs that are blocked by tineyrl preview feature
        self.stop = False

    def ping_check(self, url):
        try:
            response = requests.head(url, timeout=3, allow_redirects=True)
            response.raise_for_status()
            if 'tinyurl.com' == urlparse(response.url).netloc:
                self.preview_errors.append(url)
            if urlparse(response.url).netloc != urlparse(url).netloc:
                self.errors[url] = f"Redirect mismatch: Expected {url}, got {response.url}"
        except HTTPError as e:
            self.errors[url] = f"HTTP Error: {e}"
        except Timeout:
            self.errors[url] = "Request timed out"
        except RequestException as e:
            self.errors[url] = f"Request Exception: {e}"

    def start_heartbeat_service(self):
        logger.log(SUCCESS, f'Delay is {self.delay}!')
        while True:
            logger.info('111111111111')
            start_time = time.time()
            while time.time() - start_time < self.delay and not self.ping_sweep.is_set():
                if self.shared_queue.not_empty:
                    self.process_queue_data(self.shared_queue.get('data'))
                time.sleep(1)

            logger.info('22222222222222222222')
            if self.ping_sweep.is_set():
                self.ping_sweep.clear()

            while not self.stop:
                logger.info('33333333333333333333')
                self.errors = {}  # Reset errors before each check
                futures = [self.executor.submit(self.ping_check, url) for url in self.alias_url_mapping]
                logger.info('33333333333333333333')
                concurrent.futures.wait(futures)
                logger.error(f"{red}Errors:", self.errors)
                self.shared_queue.put(self.errors)
                logger.info('33333333333333333333')
                # Add logic to handle errors here, e.g., updating the API client
                # if the errors indicate that a URL is no longer valid.
                # Implement your custom logic as needed.

                # Sleep for 60 seconds (adjust this interval as needed)
                time.sleep(60)

    def fix_tinyurl_redirect(self, token_index):
        pass

    def process_queue_data(self, data: dict):
        for key in data.keys():
            if key == 'new':
                self.alias_url_mapping.update({data['new']['alias']: data['new']['url']})
                self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=(len(self.alias_url_mapping)))
            if key == 'delay':
                self.delay = data[key]
                logger.info('Ping changed to: ' + str(self.delay))
            elif key == 'ping_sweep':
                self.ping_sweep = True
