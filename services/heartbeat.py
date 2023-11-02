import logging
import time

import requests

from utility import url_tools
from exceptions.tinyurl_exceptions import TinyUrlPreviewException, NetworkException


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
                    shared_data[tinyurl.id] = f'{tinyurl.redirect_url_long};{tinyurl.redirect_url_short}'
            else:
                logger.error(f'Tried updating with all alternate redirect URL but failed for tinyurl ({tinyurl.id})!')
                notify_deletion(tinyurl, lock, shared_data)
                return 0

        except NetworkException as e:
            logger.error(e)
            is_updated = tinyurl.update_redirect_service()
            if is_updated:
                with lock:
                    shared_data[tinyurl.id] = f'{tinyurl.redirect_url_long};{tinyurl.redirect_url_short}'
            else:
                notify_deletion(tinyurl, lock, shared_data)
                return 0


def ping_check(tinyurl, shared_data):
    while True:
        try:
            tinyurl.redirect_url_short = shared_data[tinyurl.id].split(';')[1]
            tinyurl.redirect_url_long = shared_data[tinyurl.id].split(';')[0]
            response = requests.head(tinyurl.tinyurl, allow_redirects=True)
            if 'tiny' in response.url:
                raise TinyUrlPreviewException(tinyurl.id, tinyurl.redirect_url_short)
            if url_tools.get_short_domain(response.url) in tinyurl.redirect_url_short:
                logger.log(SUCCESS, f'Tinyurl({tinyurl.id}) - {tinyurl.tinyurl}  -->  {tinyurl.redirect_url_short}/')
            else:
                logger.error(f'Tinyurl ({tinyurl.id}) - {tinyurl.tinyurl}  -->  {response.url}. Expected {tinyurl.redirect_url_short}!')
            return 0

        except Exception:
            raise NetworkException(tinyurl.redirect_url_long)


def notify_deletion(tinyurl, lock, shared_data):
    logger.warning(f'Tinyurl({tinyurl.id}) purged!')
    with lock:
        shared_data['for_deletion'] = tinyurl.id