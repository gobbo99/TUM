import concurrent.futures
from concurrent.futures import wait, ALL_COMPLETED, FIRST_COMPLETED
import random
import logging
from threading import Event, Thread
from queue import Queue, Empty
import time
from urllib.parse import urlparse
from typing import Optional

import requests
from requests.exceptions import RequestException, HTTPError, Timeout

from api.apiclient import ApiClient
from utility.url_tools import get_final_domain
from exceptions.tinyurl_exceptions import *
import settings

SUCCESS = 25
logger = logging.getLogger('')
MAX_THREADS = settings.MAX_THREADS
INTERVAL = settings.PING_INTERVAL


class HeartbeatService:
    def __init__(self, shared_queue: Queue, update_event: Event, sweeping_event: Event,
                 api_client: ApiClient = None):
        self.control_event = update_event
        self.feedback_event = sweeping_event
        self.control_event.clear()
        self.feedback_event.clear()
        self.shared_queue = shared_queue
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS)
        self.batch = {}
        self.last_sweep = None
        self.api_client = api_client
        self.delay = INTERVAL
        self.tinyurl_target_mapping = {}
        self.errors = {}
        self.preview_errors = {}
        self.active = False

    def run_heartbeat_service(self):
        while time.time() - self.last_sweep < self.delay:
            if self.control_event.is_set():
                self._consume_all_control()
                continue

            self.consume_all_update()
            time.sleep(2)

        self.consume_all_update()  # Process if there is anything left in queue
        self._ping_sweep()

        if self.preview_errors:
            if self.errors is not None:
                error_urls = list(self.preview_errors.keys()) + list(self.errors)
            else:
                error_urls = list(self.preview_errors.keys())
            futures = [self.executor.submit(self.fix_tinyurl_redirect, url) for url in error_urls]
            wait(futures, return_when=ALL_COMPLETED, timeout=60)

        self._add_batch_to_queue() if self.batch else None

    def ping_check(self, tinyurl, verbose=False):
        try:
            if verbose:
                logger.info(f'Ping checking {tinyurl} if it redirects to'
                            f' {self.tinyurl_target_mapping[tinyurl]}')
            response = requests.head(tinyurl, timeout=3, allow_redirects=True)

            response_domain = get_final_domain(response.url)
            intended_domain = self.tinyurl_target_mapping[tinyurl]

            if 'tinyurl.com' in response_domain:
                self.preview_errors[tinyurl] = intended_domain
            elif response_domain != intended_domain:
                self.errors[tinyurl] = (f"Redirect mismatch: Expected domain: {intended_domain}"
                                        f", got {response_domain}")
            else:
                return True

        except HTTPError as e:
            self.errors[tinyurl] = f"HTTP Error: {e}"
        except Timeout:
            self.errors[tinyurl] = f"Request timed out!"
        except RequestException as e:
            self.errors[tinyurl] = f"Request Exception: {e}"
        except ValueError as e:
            raise e

    def _fix_redirects(self):
        pass

    def _ping_sweep(self):
        self.last_sweep = time.time()
        futures = [self.executor.submit(self.ping_check, url, False) for url in self.tinyurl_target_mapping.keys()]
        wait(futures, return_when=FIRST_COMPLETED)
        if self.errors.values():
            for err in self.errors.values():
                logger.error(f"{red}Error: {err}")
        elif self.preview_errors:
            for err in self.preview_errors.keys():
                logger.error(f"{red}Preview Error for {err}...")
        else:
            logger.log(SUCCESS, f"{green}All redirects point to the right domain!")

    def fix_tinyurl_redirect(self, tinyurl):
        """
        First attempting to self-update with same redirect by sending request 3 times and checking destination.
        After these attempts use alternate urls from fallback list and update redirect to them.

        :param tinyurl:
        :return:
        """

        logger.info(f'Fixing tinyurl {tinyurl}...')
        alias = tinyurl.split('/')[-1]
        target_url = self.tinyurl_target_mapping[tinyurl]
        try:
            data = self.api_client.update_tinyurl_redirect_service(alias, target_url, retry=3)
            self.tinyurl_target_mapping[tinyurl] = get_final_domain(data['url'])
            if self.ping_check(tinyurl):
                self.preview_errors.pop(tinyurl)
        except (TinyUrlUpdateError, NetworkError, HTTPError,  RequestError, ValueError) as e:
            logger.debug(f'Unable to self-update! {tinyurl}!\nError: {e}')
        logger.info(f'Unable to self-update to {target_url} | {tinyurl}!')
        attempts = 0
        if self.api_client.tunneling_service.tunneler:
            while attempts < self.api_client.tunneling_service.length:
                try:
                    logger.log(SUCCESS, f'Attempting to update {tinyurl} redirect to'
                                        f' {self.api_client.tunneling_service.tunneler}...')
                    data = self.api_client.update_tinyurl_redirect_service(alias, self.api_client.tunneling_service.tunneler, retry=1, timeout=1)
                    full_url = 'https://' + data['url'] if not urlparse(data['url']).scheme else data['url']
                    target_domain = get_final_domain(data['url'])
                    self.tinyurl_target_mapping[tinyurl] = target_domain
                    self.preview_errors.pop(tinyurl)
                    logger.log(SUCCESS, f'{tinyurl} redirect successfully updated from {target_url} to {full_url}')
                    self.batch[alias] = {'domain': target_domain, 'full_url': full_url}
                    break
                except (TinyUrlUpdateError, NetworkError,  RequestError, ValueError) as e:
                    time.sleep(random.uniform(2, 6))
                    logger.warning(e)
                    attempts += 1
                    self.api_client.tunneling_service.cycle_next()

    def _consume_all_control(self):
        while True:
            try:
                data = self.shared_queue.get(timeout=15)
                self.process_control_event(data)
            except Empty:
                break

    def consume_all_update(self):
        while True:
            try:
                data = self.shared_queue.get_nowait()
                self._process_update_event(data)
            except Empty:
                break

    def _add_batch_to_queue(self):
        self.feedback_event.set()
        self.consume_all_update()
        self.shared_queue.put(self.batch)
        self.shared_queue.join()
        self.batch = {}
        self.feedback_event.clear()

    def process_control_event(self, data):
        for key, value in data.items():
            if key == 'delay':
                self.delay = value
                logger.info(f'Pinging interval changed to: {self.delay}')
                self.control_event.clear()
            elif key == 'threads':
                self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=value)
                self.control_event.clear()
            elif key == 'active':
                self.active = value
                self.control_event.clear()
            elif key == 'ping':
                self._ping_sweep()
                self.control_event.clear()
            else:
                logger.error(f'Unknown data received in queue!{data}')
            self.shared_queue.task_done()

    def _process_update_event(self, tinyurl_and_target):
        if self.control_event.is_set():
            print(f'sta je ovdje:    {tinyurl_and_target}')
        for tinyurl, domain in tinyurl_and_target.items():
            if domain == 'delay':
                print('***************')
            self.tinyurl_target_mapping[tinyurl] = domain
        self.shared_queue.task_done()
        logger.info('Done processing, added new and updated url for service!')

    def start_heartbeat_service(self, active: bool = False):
        self.last_sweep = time.time()
        self.active = active
        logger.info(f'Ping interval is set to {self.delay} seconds!')
        logger.info(f'Using {MAX_THREADS} threads for this service!')
        while True:
            if self.active:
                self.run_heartbeat_service()
            else:
                logger.info('Live logger turned off!')
                while not self.control_event.is_set():
                    time.sleep(5)
                self._consume_all_control()
