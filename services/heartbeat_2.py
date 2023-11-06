import logging
import concurrent.futures
import random
import threading
from queue import Queue
import time
from typing import List, Any, Dict

import requests
from requests.exceptions import RequestException, HTTPError, Timeout
from urllib.parse import urlparse

from api.apiclient import ApiClient
from utility.ansi_colors import red, yellow, green
from utility.url_tools import get_final_domain
from exceptions.tinyurl_exceptions import *

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
        self.tinyurl_target_mapping = {}
        self.errors = {}  # Dictionary to store URL errors {target_url: errors: []}
        self.preview_errors = {}  # Tinyurl: target_url
        self.stop = False

    def ping_check(self, url):
        try:
            response = requests.head(url, timeout=3, allow_redirects=True)
            response.raise_for_status()
            response_domain = get_final_domain(response.url)
            intended_domain = self.tinyurl_target_mapping[url]

            if 'tinyurl.com' == response_domain.strip():
                self.preview_errors[url] = intended_domain
            elif response_domain != intended_domain:
                self.errors[url] = f"Redirect mismatch: Expected domain: {intended_domain}, got {response_domain}"
            else:
                pass
        except HTTPError as e:
            self.errors[url] = f"HTTP Error for {url}: {e}"
        except Timeout:
            self.errors[url] = f"Request timed out for {url}"
        except RequestException as e:
            self.errors[url] = f"Request Exception for {url}: {e}"

    def start_heartbeat_service(self):
        logger.log(SUCCESS, f'Ping interval is set to {self.delay} seconds!')
        while True:
            logger.info(f'Tinyurls with preview exception: \n {self.preview_errors.keys()}')
            if self.preview_errors:
                logger.info('Fixing previews..')
                logger.warning('Fixing previews..')
                futures = [self.executor.submit(self.fix_tinyurl_redirect, url) for url in self.preview_errors.keys()]
                concurrent.futures.wait(futures)
            start_time = time.time()
            while time.time() - start_time < self.delay and not self.ping_sweep.is_set():
                if not self.shared_queue.empty():
                    self.process_queue_data(self.shared_queue.get())
                    self.shared_queue.task_done()
                time.sleep(1)
            if self.ping_sweep.is_set():
                self.ping_sweep.clear()

            self.errors = {}  # Reset errors before each check
            futures = [self.executor.submit(self.ping_check, url) for url in self.tinyurl_target_mapping.keys()]
            concurrent.futures.wait(futures)
            if self.errors.values():
                for error in self.errors.values():
                    logger.error(f"{red}Error: {error}")
            else:
                logger.log(SUCCESS, f"{green}All redirects point to the right domain!")
            self.shared_queue.put(self.errors)
            # Add logic to handle errors here, e.g., updating the API client
            # if the errors indicate that a URL is no longer valid.
            # Implement your custom logic as needed.

    def fix_tinyurl_redirect(self, tinyurl):
        alias = tinyurl.split('/')[-1]
        target_url = self.tinyurl_target_mapping[tinyurl]
        try:
            data = self.api_client.update_tinyurl_redirect_service(alias, target_url, retry=3)
            self.tinyurl_target_mapping[tinyurl] = get_final_domain((data['url']))
            self.ping_check(tinyurl)
            self.preview_errors.remove(target_url)
        except (TinyUrlUpdateError, NetworkError,  RequestError, ValueError):
            logger.warning(f'Failed to self-update to remove preview page for {tinyurl}!')
        attempts = 0
        if self.api_client.tunneling_service.tunneler:
            while attempts < len(self.api_client.tunneling_service.length):
                try:
                    self.api_client.update_tinyurl_redirect_service(alias, self.api_client.tunneling_service.tunneler, retry=1, timeout=1)
                    self.preview_errors.remove(target_url)
                    logger.info(f'{tinyurl} redirect successfully updated from {target_url} to {tunneler}')
                    break
                except (TinyUrlUpdateError, NetworkError,  RequestError, ValueError):
                    attempts += 1
                    tunneler = self.api_client.tunneling_service.cycle_next()
                finally:
                    time.sleep(random.uniform(5, 10))

    def process_queue_data(self, data: dict):
        for key in data.keys():
            if key == 'new':
                self.tinyurl_target_mapping.update({data['new']['url']: data['new']['target']})
                self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=(len(self.tinyurl_target_mapping)))
            if key == 'delay':
                self.delay = data[key]
                logger.info('Pinging interval changed to: ' + str(self.delay))
            elif key == 'ping_sweep':
                self.ping_sweep = True
