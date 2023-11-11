import concurrent.futures
import os
import signal
from concurrent.futures import wait, ALL_COMPLETED, FIRST_COMPLETED
import random
from subprocess import Popen
import logging
import atexit
from threading import Event, Thread
from queue import Queue, Empty, Full
import time
from urllib.parse import urlparse
from typing import Optional

import requests
from requests.exceptions import RequestException, HTTPError, Timeout

import utility
from api.apiclient import ApiClient
from utility.url_tools import get_final_domain
from exceptions.tinyurl_exceptions import *
import settings

SUCCESS = 25
logger = logging.getLogger('live')
MAX_THREADS = settings.MAX_THREADS
INTERVAL = settings.PING_INTERVAL


class HeartbeatService:
    def __init__(self, shared_queue: Queue, control_event: Event, feedback_event: Event,
                 api_client: ApiClient = None, tinyurl_target_list: dict = {}):
        self.control_event = control_event
        self.feedback_event = feedback_event
        self.shared_queue = shared_queue
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=MAX_THREADS)
        self.queue_data = {}
        self.last_sweep = time.time()
        self.api_client = api_client
        self.delay = INTERVAL
        self.tinyurl_target_mapping = tinyurl_target_list
        self.errors = {}
        self.preview_errors = {}
        self.terminate = False

    def _consumer_thread(self):
        while True:
            self.control_event.wait()
            try:
                self._get_next_item()
                self.control_event.clear()
            except Exception:
                print('Exception consumer heatbeat')
            if self.terminate:
                break

    def run_heartbeat_service(self):
        """
        Initial loop is a sleeper that only checks for control event
        :return:
        """
        self.feedback_event.clear()
        while True:
            while time.time() - self.last_sweep < float(self.delay):
                time.sleep(1)

            self._ping_sweep_thread_pool()  # Here errors are assigned if any
            self._fix_errors_thread_pool()

            if self.queue_data:
                self._enqueue_data()

    def ping_check(self, tinyurl, verbose=False):
        try:
            if verbose:
                logger.info(f'Ping checking {tinyurl} if it redirects to'
                            f' {self.tinyurl_target_mapping[tinyurl]}')
            response = requests.head(tinyurl, timeout=3, allow_redirects=True)

            response_domain = get_final_domain(response.url)
            intended_domain = self.tinyurl_target_mapping[tinyurl]

            if 'tinyurl' in response_domain.split('.'):
                self.preview_errors[tinyurl] = 'https://' + intended_domain \
                    if not urlparse(intended_domain).scheme else intended_domain
            elif response_domain != intended_domain:
                self.errors[tinyurl] = 'https://' + intended_domain if not urlparse(intended_domain).scheme else intended_domain
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

    def _ping_sweep_thread_pool(self):
        futures = [self.executor.submit(self.ping_check, url, False) for url in self.tinyurl_target_mapping.keys()]
        _, not_completed = wait(futures, return_when=ALL_COMPLETED, timeout=60)
        self.last_sweep = time.time()
        if not_completed:
            logger.info(f'Timeout 60 seconds, not all tasks completed!')

        if not self.errors and not self.preview_errors:
            logger.log(SUCCESS, f"{green}All redirects point to the right domain!")
        else:
            if self.errors:
                logger.warning(f'Tinyurls with errors: {self.errors.keys()}')
            elif self.preview_errors:
                logger.warning(f'Tinyurls with errors: {self.preview_errors.keys()}')

    def _fix_errors_thread_pool(self):
        error_urls = {}  # url: True/False,  True to skip self-update to fix preview
        for url_fix in self.errors:
            error_urls[url_fix] = True
        for url_fix in self.preview_errors:
            error_urls[url_fix] = False
        if error_urls:
            futures = [self.executor.submit(self.fix_tinyurl_redirect, url, flag,) for url, flag in error_urls.items()]
            _, not_completed = wait(futures, return_when=ALL_COMPLETED, timeout=60)
            if not_completed:
                logger.debug(f'Not all tasks completed for fix_tinyurl_redirect!!!')
            else:
                logger.debug('DEBUG: all futures for preview fix completed!')

    def fix_tinyurl_redirect(self, tinyurl, flag=False):
        """
        First attempting to self-update with same redirect by sending request 3 times and checking destination.
        After these attempts use alternate urls from fallback list and update redirect to them.

        :param flag:
        :param tinyurl:
        :return:
        """

        logger.info(f'Fixing tinyurl {tinyurl}...')
        alias = tinyurl.split('/')[-1]
        target_url = self.tinyurl_target_mapping[tinyurl]
        if not flag:
            try:
                data = self.api_client.update_tinyurl_redirect_service(alias, target_url, retry=3)
                self.tinyurl_target_mapping[tinyurl] = get_final_domain(data['url'])
                if self.ping_check(tinyurl):
                    self.preview_errors.pop(tinyurl, None)
                    self.errors.pop(tinyurl, None)
            except (TinyUrlUpdateError, NetworkError, HTTPError, RequestError, ValueError) as e:
                pass
        attempts = 0
        if self.api_client.tunneling_service.tunneler:
            while attempts < self.api_client.tunneling_service.length:
                try:
                    logger.log(SUCCESS, f'Attempting to update {tinyurl} redirect to'
                                        f' {self.api_client.tunneling_service.tunneler}...')
                    data = self.api_client.update_tinyurl_redirect_service(alias,
                                                                           self.api_client.tunneling_service.tunneler,
                                                                           retry=1, timeout=3)
                    full_url = 'https://' + data['url'] if not urlparse(data['url']).scheme else data['url']
                    target_domain = get_final_domain(data['url'])
                    self.tinyurl_target_mapping[tinyurl] = target_domain
                    self.preview_errors.pop(tinyurl, None)
                    self.errors.pop(tinyurl, None)
                    logger.log(SUCCESS, f'{tinyurl} redirect successfully updated from {target_url} to {full_url}')
                    self.queue_data[alias] = {'domain': target_domain, 'full_url': full_url}
                    break
                except (TinyUrlUpdateError, NetworkError, RequestError, ValueError) as e:
                    time.sleep(random.uniform(2, 6))
                    logger.warning(e)
                    attempts += 1
                    self.api_client.tunneling_service.cycle_next()

    def _consume_all(self):
        while True:
            try:
                data = self.shared_queue.get_nowait()
                self._process_data(data)
                self.shared_queue.task_done()
            except Empty:
                break

    def _get_next_item(self):
        try:
            item = self.shared_queue.get()
            self._process_data(item)
            self.shared_queue.task_done()
        except Empty:
            pass

    def _enqueue_data(self):
        while self.control_event.is_set():
            time.sleep(0.1)
        try:
            self.shared_queue.join()
            self.shared_queue.put(self.queue_data)
            self.feedback_event.set()
            self.shared_queue.join()
            self.queue_data.clear()
        except Full:
            print('Error, queue full!')

    def _process_data(self, data):
        for key, value in data.items():
            if key == 'update':
                self.tinyurl_target_mapping.update(value)
            elif key == 'delay':
                self.delay = value
                logger.info(f'Pinging interval changed to: {self.delay} seconds!')
            elif key == 'threads':
                self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=value)
            elif key == 'exit':
                self.terminate = True
            elif key == 'ping':
                self.last_sweep = time.time() - 10000
            else:
                logger.error(f'Unknown data received in queue!{data}')

    """
    def _store_update_data(self, data):
        if len(data) != 1:
            logging.error(f'Error, store_update_data received unknown data: {data}')
            print(f'Error, store_update_data received unknown data: {data}')
        for tinyurl, domain in data.items():
            self.to_be_processed[tinyurl] = domain
    """

    def load_list(self, tinyurl_target: dict):
        self.tinyurl_target_mapping.update(tinyurl_target)

    def _start_terminal_logger(self):
        terminal = settings.TERMINAL_EMULATOR
        path = settings.LOGS_PATH + '/.tum_logs/temp'
        if terminal == 'gnome':
            utility.package_installer.install_gnome_terminal()
            self.process = Popen(['gnome-terminal', '--disable-factory', '--', 'tail', '-f', f'{path}'],
                                 preexec_fn=os.setpgrp)
        else:
            utility.package_installer.install_xfce4_terminal()
            self.process = Popen(['xfce4-terminal', '--disable-server', '--execute', 'tail', '-f', f'{path}'],
                                 preexec_fn=os.setpgrp)
        self.pid = self.process.pid
        time.sleep(1)

    def start_heartbeat_service(self):
        consumer_thread = Thread(target=self._consumer_thread)
        heartbeat_thread = Thread(target=self.run_heartbeat_service, daemon=True)
        self._start_terminal_logger()
        logger.info('Live logger turned on!')
        logger.info(f'Ping interval is set to {self.delay} seconds!')
        logger.info(f'Using {MAX_THREADS} threads for this service!')
        consumer_thread.start()
        heartbeat_thread.start()
        consumer_thread.join()
        self.kill_terminal_process(self.pid)

    @staticmethod
    def kill_terminal_process(pid):
        logger.info('Live logger turned off! Shutting down...')
        time.sleep(0.5)
        os.killpg(pid, signal.SIGINT)
