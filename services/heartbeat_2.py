import logging
import concurrent.futures
import threading
from queue import Queue
import time

import requests
from requests.exceptions import RequestException, HTTPError, Timeout
from urllib.parse import urlparse

from api.apiclient import ApiClient

logger = logging.getLogger('')
SUCCESS = 25


class HeartbeatService:
    def __init__(self, api_client: ApiClient, shared_queue: Queue):
        self.api_client = api_client
        self.shared_queue = shared_queue
        self.urls = ['youtube.com']
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=len(self.urls))
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
        while True:
            start_time = time.time()
            while not self.stop and not self.shared_queue.get('ping_sweep'):
                self.errors = {}  # Reset errors before each check
                futures = [self.executor.submit(self.ping_check, url) for url in self.urls]
                concurrent.futures.wait(futures)
                print("Errors:", self.errors)
                # Add logic to handle errors here, e.g., updating the API client
                # if the errors indicate that a URL is no longer valid.
                # Implement your custom logic as needed.

                # Sleep for 60 seconds (adjust this interval as needed)
                time.sleep(60)

    def load_urls(self, *urls):
        self.urls.extend(urls)
