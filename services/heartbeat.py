import logging
import time

from tenacity import retry, wait, stop_after_attempt
import requests
from requests.exceptions import TooManyRedirects
from requests.exceptions import RequestException
from requests.exceptions import ConnectionError

import settings
import tunneling
from utility import url_tools
from exceptions.tinyurl_exceptions import TinyUrlPreviewException, NetworkException


def status_service(tinyurl, lock, shared_data):
    while True:
        tinyurl.redirect_url_short = shared_data[tinyurl.id].split(';')[1]
        try:
            ping_check(tinyurl, shared_data)
        except TinyUrlPreviewException:
            logging.warning(f'Preview page is blocking Tinyurl({tinyurl.id}) for {tinyurl.redirect_url_short}!')
            logging.info(f'Updating redirect to alternate url {tinyurl.alternate_tunnel}...')
            is_updated = tinyurl.update_redirect_service()
            if is_updated:
                with lock:
                    shared_data[tinyurl.id] = f'{tinyurl.redirect_url_long};{tinyurl.redirect_url_short}'
            else:
                logging.warning(f'Tried updating with all alternate redirect URL but failed for tinyurl ({tinyurl.id})!')
                delete_service(tinyurl, lock, shared_data)
                break
        except NetworkException:
            delete_service(tinyurl, lock, shared_data)
            break
        finally:
            time.sleep(shared_data['ping_interval'])


def ping_check(tinyurl, shared_data):
    retry = 3
    while retry != 0:
        try:
            tinyurl.redirect_url_short = shared_data[tinyurl.id].split(';')[1]
            response = requests.head(tinyurl.tinyurl, allow_redirects=True)
            if 'tiny' in response.url:
                raise TinyUrlPreviewException()
            if url_tools.get_short_domain(response.url) == tinyurl.redirect_url_short:
                logging.info(f'Tinyurl({tinyurl.id}) - {tinyurl.tinyurl}  -->  {tinyurl.redirect_url_short}')
            else:
                retry -= 1
                logging.warning(f'Tinyurl ({tinyurl.id}) - {tinyurl.tinyurl}  -->  {response.url}. Expected {tinyurl.redirect_url_short}!')
            return
        except Exception:
            retry -= 1
            time.sleep(shared_data['ping_interval'])
            continue
    raise NetworkException


def delete_service(tinyurl, lock, shared_data):
    logging.warning(f'Tinyurl({tinyurl.id}) purged!')
    with lock:
        shared_data['for_deletion'] = tinyurl.id

