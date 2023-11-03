import logging
import time
from urllib.parse import urlparse

import requests

from utility import url_tools, get_final_domain
from exceptions.tinyurl_exceptions import TinyUrlPreviewException, RequestError


logger = logging.getLogger('')
SUCCESS = 25


def status_service(tinyurl, lock, shared_data):  #  work on exception handling
    while True:
        try:
            ping_check(tinyurl, shared_data)
            if shared_data['ping_sweep']:
                time.sleep(5)
            elapsed = time.time()
            while not shared_data['ping_sweep'] and time.time() - elapsed < shared_data['ping_interval']:
                time.sleep(2)

        except TinyUrlPreviewException as e:
            logger.warning(e.message)
            is_updated = tinyurl.update_redirect_service()
            if is_updated:
                with lock:
                    shared_data[tinyurl.id] = f'{tinyurl.final_url};{tinyurl.domain}'
            else:
                logger.error(f'Tried updating with all alternate redirect URL but failed for tinyurl ({tinyurl.id})!')
                notify_deletion(tinyurl, lock, shared_data)
                return 0

        except RequestError as e:
            logger.error(e)
            is_updated = tinyurl.update_redirect_service()
            if is_updated:
                with lock:
                    shared_data[tinyurl.id] = f'{tinyurl.final_url};{tinyurl.domain}'
            else:
                notify_deletion(tinyurl, lock, shared_data)
                return 0


def ping_check(tinyurl, shared_data):
    while True:
        try:
            tinyurl.domain = shared_data[tinyurl.id].split(';')[1]
            tinyurl.final_url = shared_data[tinyurl.id].split(';')[0]
            response = requests.head(tinyurl.tinyurl, allow_redirects=True)
            if 'tiny' in response.url:
                raise TinyUrlPreviewException(tinyurl.id, tinyurl.final_url)
            if get_final_domain(response.url) == tinyurl.domain:
                logger.log(SUCCESS, f'Tinyurl({tinyurl.id}) - {tinyurl.tinyurl}  -->  {tinyurl.domain}/')
            else:
                logger.error(f'Tinyurl({tinyurl.id}) - {tinyurl.tinyurl} Wrong redirect domain! -->  {response.url}. Expected domain: {tinyurl.domain}!')
            return 0

        except Exception:
            raise RequestError(tinyurl.final_url)


def notify_deletion(tinyurl, lock, shared_data):
    logger.warning(f'Tinyurl({tinyurl.id}) purged!')
    with lock:
        shared_data['delete_by_id'] = tinyurl.id