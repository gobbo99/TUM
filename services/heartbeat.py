import logging
import time

import requests

from utility import url_tools
from exceptions.tinyurl_exceptions import TinyUrlPreviewException, NetworkException


logger = logging.getLogger('')
SUCCESS = 25

def status_service(tinyurl, lock, shared_data):  #  work on exception handlin
    while True:
        try:
            ping_check(tinyurl, shared_data)
            if shared_data['ping_sweep']:
                time.sleep(5)

        except TinyUrlPreviewException as e:
            logger.warning(e.message)
            is_updated = tinyurl.update_redirect_service()
            if is_updated:
                with lock:
                    shared_data[tinyurl.id] = f'{tinyurl.redirect_url_long};{tinyurl.redirect_url_short}'
            else:
                logger.error(f'Tried updating with all alternate redirect URL but failed for tinyurl ({tinyurl.id})!')
                delete_service(tinyurl, lock, shared_data)
                return 0

        except NetworkException:
            is_updated = tinyurl.update_redirect_service()
            if is_updated:
                pass
            else:
                delete_service(tinyurl, lock, shared_data)
                return 0
        elapsed = time.time()
        while not shared_data['ping_sweep'] and time.time() - elapsed < shared_data['ping_interval']:
            time.sleep(2)


def ping_check(tinyurl, shared_data):
    retry = 5
    while retry != 0:
        try:
            tinyurl.redirect_url_short = shared_data[tinyurl.id].split(';')[1]
            response = requests.head(tinyurl.tinyurl, allow_redirects=True)
            if 'tiny' in response.url:
                raise TinyUrlPreviewException(tinyurl.id, tinyurl.redirect_url_short)
            if url_tools.get_short_domain(response.url) == tinyurl.redirect_url_short:
                logger.log(SUCCESS, f'Tinyurl({tinyurl.id}) - {tinyurl.tinyurl}  -->  {tinyurl.redirect_url_short}')
            else:
                retry -= 1
                logger.error(f'Tinyurl ({tinyurl.id}) - {tinyurl.tinyurl}  -->  {response.url}. Expected {tinyurl.redirect_url_short}!')
            return

        except NetworkException:
            retry -= 1
            continue


def delete_service(tinyurl, lock, shared_data):
    logger.warning(f'Tinyurl({tinyurl.id}) purged!')
    with lock:
        shared_data['for_deletion'] = tinyurl.id