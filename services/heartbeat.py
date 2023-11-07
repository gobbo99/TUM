import concurrent.futures
from concurrent.futures import wait, ALL_COMPLETED
import random
import logging
from threading import Event, Thread
from queue import Queue, Empty
import time
from urllib.parse import urlparse

import requests
from requests.exceptions import RequestException, HTTPError, Timeout

from api.apiclient import ApiClient
from utility.url_tools import get_final_domain
from exceptions.tinyurl_exceptions import *
from settings import MAX_THREADS

SUCCESS = 25
logger = logging.getLogger('')


class HeartbeatService:
    def __init__(self, shared_queue: Queue, update_event: Event, api_client: ApiClient = None):
        self.update_event = update_event
        self.shared_queue = shared_queue
        self.shared_queue = shared_queue
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS)
        self.api_client = api_client
        self.delay = 60
        self.tinyurl_target_mapping = {}
        self.errors = {}  # Dictionary to store URL errors {target_url: errors: []}
        self.preview_errors = {}  # Tinyurl: target_url
        self.online = True

    def run_heartbeat_service(self):
        logger.info(f'Ping interval is set to {self.delay} seconds!')
        logger.info(f'Using {MAX_THREADS} threads for this service!')
        while self.online:
            start_time = time.time()
            while not self.update_event.is_set():
                elapsed_time = time.time() - start_time
                remaining_time = self.delay - elapsed_time
                if remaining_time <= 0:
                    break
                sleep_time = min(1, remaining_time)
                time.sleep(sleep_time)

            self._get_all_items_from_queue()

            self.update_event.clear() if self.update_event.is_set() else None
            self.perform_ping_sweep()
            logger.warning('\n'.join("{}: {}".format(k, v) for k, v in self.errors.items()))
            # Add logic to handle errors here, e.g., updating the API client
            # if the errors indicate that a URL is no longer valid.
            # Implement your custom logic as needed.
            if self.preview_errors:
                logger.info(f'Fixing previews... {self.preview_errors.keys()}')
                futures = [self.executor.submit(self.fix_tinyurl_redirect, url) for url in
                           self.preview_errors.keys()]
                concurrent.futures.wait(futures)
                wait(futures, return_when=ALL_COMPLETED)

        logger.info('Live logger turned off!')

    def start_heartbeat_service(self):
        while True:
            if self.online:
                self.run_heartbeat_service()
            else:
                while not self.update_event.is_set():
                    time.sleep(5)
                self._process_queue_data(self.shared_queue.get_nowait())

    def ping_check(self, tinyurl, message=False):
        try:
            if message:
                logger.info(f'Ping checking {tinyurl} if it redirects to {self.tinyurl_target_mapping[tinyurl]}')
            response = requests.head(tinyurl, timeout=3, allow_redirects=True)

            response_domain = get_final_domain(response.url)
            intended_domain = self.tinyurl_target_mapping[tinyurl]

            if 'tinyurl.com' in response_domain:
                self.preview_errors[tinyurl] = intended_domain
            if response_domain != intended_domain:
                self.errors[tinyurl] = f"Redirect mismatch: Expected domain: {intended_domain}, got {response_domain}"

        except HTTPError as e:
            self.errors[tinyurl] = f"HTTP Error: {e}"
        except Timeout:
            self.errors[tinyurl] = f"Request timed out!"
        except RequestException as e:
            self.errors[tinyurl] = f"Request Exception: {e}"
        except ValueError as e:
            raise e

    def perform_ping_sweep(self):
        futures = [self.executor.submit(self.ping_check, url, True) for url in self.tinyurl_target_mapping.keys()]
        wait(futures, return_when=ALL_COMPLETED)
        if self.errors.values() or self.preview_errors:
            for error in self.errors.values():
                logger.error(f"{red}Error: {error}")
        else:
            logger.log(SUCCESS, f"{green}All redirects point to the right domain!")

    def fix_tinyurl_redirect(self, tinyurl):
        """
        First attempting to self-update with same redirect by sending request 3 times and checking destination.
        After these attempts use alternate urls from fallback list and update redirect to them.

        :param tinyurl:
        :return:
        """
        alias = tinyurl.split('/')[-1]
        target_url = self.tinyurl_target_mapping[tinyurl]
        try:
            data = self.api_client.update_tinyurl_redirect_service(alias, target_url, retry=3)
            self.tinyurl_target_mapping[tinyurl] = get_final_domain(data['url'])
            self.ping_check(tinyurl, message=True)
            self.preview_errors.remove(target_url)
        except (TinyUrlUpdateError, NetworkError, HTTPError,  RequestError, ValueError) as e:
            logger.debug(f'Unable to self-update! {tinyurl}!\nError: {e}')
        attempts = 0
        if self.api_client.tunneling_service.tunneler:
            while attempts < self.api_client.tunneling_service.length:
                try:
                    logger.log(SUCCESS, f'Attempting to update {tinyurl} redirect to {self.api_client.tunneling_service.tunneler}...')
                    data = self.api_client.update_tinyurl_redirect_service(alias, self.api_client.tunneling_service.tunneler, retry=1, timeout=1)
                    full_url = 'https://' + data['url'] if not urlparse(data['url']).scheme else data['url']
                    target_domain = get_final_domain(data['url'])
                    self.tinyurl_target_mapping[tinyurl] = target_domain
                    self.preview_errors.pop(tinyurl)
                    data: dict = {'patch': {'alias': alias, 'target_url': full_url, 'domain': target_domain}}
                    self._add_queue_data(data)
                    logger.log(SUCCESS, f'{tinyurl} redirect successfully updated from {target_url} to {full_url}')
                    break
                except (TinyUrlUpdateError, NetworkError,  RequestError, ValueError):
                    attempts += 1
                    self.api_client.tunneling_service.cycle_next()
                finally:
                    time.sleep(random.uniform(2, 6))

    def _add_queue_data(self, data):
        self.shared_queue.put(data)
        self.update_event.set()

    def _get_all_items_from_queue(self):
        while True:
            try:
                data = self.shared_queue.get_nowait()
                self._process_queue_data(data)
            except Empty:
                break

    def _process_queue_data(self, data: dict):
        for key, data in data.items():
            if key == 'new' or key == 'update':
                self.tinyurl_target_mapping[data['url']] = data['domain']
            elif key == 'delay':
                self.delay = data
                self.update_event.clear()
                logger.info(f'Pinging interval changed to: {self.delay}')
            elif key == 'threads':
                    self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=data)
            elif key == 'online':
                self.online = data
                self.update_event.clear()
            else:
                pass
