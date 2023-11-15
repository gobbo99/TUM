import concurrent.futures
import os
import random
import signal
import time
import logging
from concurrent.futures import wait, ALL_COMPLETED
from queue import Queue, Empty, Full
from subprocess import Popen
from threading import Event, Thread
from urllib.parse import urlparse

import requests
from requests.exceptions import RequestException, HTTPError, Timeout

from api.apiclient import ApiClient
from utility import package_installer
from utility.url_tools import get_final_domain
from utility.ansi_codes import AnsiCodes
from exceptions.tinyurl_exceptions import TinyUrlUpdateError, NetworkError, RequestError

SUCCESS = 25
logger = logging.getLogger('')
app_config = None


class HeartbeatService:

    def __init__(self, shared_queue: Queue, control_event: Event, feedback_event: Event,
                 api_client: ApiClient = None, load_data: dict = None, config: dict = None):
        global app_config
        app_config = config
        self.control_event = control_event
        self.feedback_event = feedback_event
        self.shared_queue = shared_queue
        self.delay = app_config['ping_interval']
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=app_config['ping_interval'])
        self.queue_data = {}
        self.last_sweep = time.time()
        self.api_client = api_client
        self.tinyurl_target_mapping = {}
        self.tinyurl_id_mapping = {}
        if load_data:
            self.tinyurl_target_mapping.update({key: value for _, nested_dict in load_data.items()
                                                for key, value in nested_dict.items()})
            self.tinyurl_id_mapping.update({url: inner_key for inner_key, nested_dict in load_data.items()
                                            for url in nested_dict})
        self.errors = {}
        self.preview_errors = {}
        self.terminate = False

    def _consumer_thread(self):
        self.terminate = False
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
        while True:
            while not self.tinyurl_target_mapping:
                time.sleep(1)

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
            self.errors[tinyurl] = "Request timed out!"
        except RequestException as e:
            self.errors[tinyurl] = f"Request Exception: {e}"
        except ValueError as e:
            raise e

    def _ping_sweep_thread_pool(self):
        futures = [self.executor.submit(self.ping_check, url, False) for url in self.tinyurl_target_mapping]
        wait(futures, return_when=ALL_COMPLETED, timeout=60)
        self.last_sweep = time.time()

        if not self.errors and not self.preview_errors:
            logger.log(SUCCESS, f"{AnsiCodes.GREEN}All redirects point to the right domain!")
        else:
            error_ids = []
            if self.errors:
                error_urls = [url for url in self.errors]
                error_ids.extend(id for id in [self.tinyurl_id_mapping[url] for url in error_urls])
            if self.preview_errors:
                error_urls = [url for url in self.preview_errors]
                error_ids.extend(id for id in [self.tinyurl_id_mapping[url] for url in error_urls])
                error_ids = ','.join(['ID[' + str(id) + ']' for id in error_ids])
                logger.warning(f"Tinyurls with errors: {error_ids}")

    def _fix_errors_thread_pool(self):
        error_urls = {}  # url: True/False,  True to skip self-update to fix preview
        for url_fix in self.errors:
            error_urls[url_fix] = True
        for url_fix in self.preview_errors:
            error_urls[url_fix] = False
        if error_urls:
            futures = [self.executor.submit(self.fix_tinyurl_redirect, url, flag,) for url, flag in error_urls.items()]
            wait(futures, return_when=ALL_COMPLETED, timeout=60)

    def fix_tinyurl_redirect(self, tinyurl, flag=False):
        """
        First attempting to self-update with same redirect by sending request 3 times and checking destination.
        After these attempts use alternate urls from fallback list and update redirect to them.

        :param flag:
        :param tinyurl:
        :return:
        """
        if self.preview_errors:
            logger.info(f'Fixing for Tinyurl [{self.tinyurl_id_mapping[tinyurl]}]...')
        alias = tinyurl.split('/')[-1]
        target_url = self.tinyurl_target_mapping[tinyurl]
        if not flag:
            try:
                data = self.api_client.update_tinyurl_redirect_service(alias, target_url, retry=3)
                self.tinyurl_target_mapping[tinyurl] = get_final_domain(data['url'])
                if self.ping_check(tinyurl):
                    self.preview_errors.pop(tinyurl, None)
                    self.errors.pop(tinyurl, None)
                    return
            except (TinyUrlUpdateError, NetworkError, HTTPError, RequestError, ValueError):
                pass
        attempts = 0
        if self.api_client.tunneling_service.tunneler:
            while attempts < self.api_client.tunneling_service.length:
                try:
                    logger.debug(f'Attempting to update {tinyurl} redirect to'
                                        f' {self.api_client.tunneling_service.tunneler}...')
                    data = self.api_client.update_tinyurl_redirect_service(alias,
                                                                           self.api_client.tunneling_service.tunneler,
                                                                           retry=1, timeout=3)
                    full_url = 'https://' + data['url'] if not urlparse(data['url']).scheme else data['url']
                    target_domain = get_final_domain(data['url'])
                    self.tinyurl_target_mapping[tinyurl] = get_final_domain(data['url'])
                    if self.ping_check(tinyurl):
                        self.preview_errors.pop(tinyurl, None)
                        self.errors.pop(tinyurl, None)
                    self.tinyurl_target_mapping[tinyurl] = target_domain
                    self.preview_errors.pop(tinyurl, None)
                    self.errors.pop(tinyurl, None)
                    logger.log(SUCCESS, f'Tinyurl [{self.tinyurl_id_mapping[tinyurl]}] '
                                        f'updated to new redirect domain: https://{target_domain}')
                    break
                except (TinyUrlUpdateError, NetworkError, RequestError, ValueError) as e:
                    time.sleep(random.uniform(2, 6))
                    logger.warning(e)
                    attempts += 1
                    self.api_client.tunneling_service.cycle_next()
        if self.tinyurl_target_mapping.get(tinyurl):  # Check if it has been deleted by main script
            self.delete_instance(tinyurl)

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
            self.shared_queue.put(self.queue_data)
            self.feedback_event.set()
            self.shared_queue.join()
            self.queue_data.clear()
        except Full:
            print('Error, queue full!')

    def _process_data(self, data):
        for key, value in data.items():
            if key == 'update':
                self.tinyurl_target_mapping.update({value['tinyurl']: value['domain']})
                self.tinyurl_id_mapping[value['tinyurl']] = value['id']
            elif key == 'delete':
                self.tinyurl_target_mapping.pop(value)
                self.tinyurl_id_mapping.pop(value)
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
                logger.error(f'Error! Unknown data received in queue!{data}')

    def load_list(self, tinyurl_target: dict):
        self.tinyurl_target_mapping.update(tinyurl_target)

    def delete_instance(self, tinyurl):
        logger.warning(f'Faulty Tinyurl[{self.tinyurl_id_mapping[tinyurl]}] deleted!')
        deleted_id = self.tinyurl_id_mapping.pop(tinyurl)
        self.tinyurl_target_mapping.pop(tinyurl)
        self.errors.pop(tinyurl, None)
        self.preview_errors.pop(tinyurl, None)
        self.queue_data = {'delete':  deleted_id}
        self._enqueue_data()

    def _start_terminal_logger(self):
        terminal = app_config['terminal_emulator']
        path = app_config['logs_path'] + '/.tum_logs/temp'
        if terminal == 'gnome':
            package_installer.install_gnome_terminal()
            self.process = Popen(['gnome-terminal', '--disable-factory', '--', 'tail', '-f', f'{path}'],
                                 preexec_fn=os.setpgrp)
        else:
            package_installer.install_xfce4_terminal()
            self.process = Popen(['xfce4-terminal', '--disable-server', '--execute', 'tail', '-f', f'{path}'],
                                 preexec_fn=os.setpgrp)
        self.pid = self.process.pid
        time.sleep(1)

    def start_heartbeat_service(self):
        consumer_thread = Thread(target=self._consumer_thread, daemon=True)
        heartbeat_thread = Thread(target=self.run_heartbeat_service, daemon=True)
        self._start_terminal_logger()
        logger.info('\033[?25lLive logger turned on!')
        logger.info(f'Ping interval is set to {self.delay} seconds!')
        consumer_thread.start()
        heartbeat_thread.start()
        consumer_thread.join()
        self.kill_terminal_process(self.pid)

    @staticmethod
    def kill_terminal_process(pid):
        logger.info('Live logger turned off! Shutting down...')
        time.sleep(1)
        os.killpg(pid, signal.SIGINT)
