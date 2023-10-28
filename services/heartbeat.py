import logging
import time

from tenacity import retry, wait, stop_after_attempt
import requests
from requests.exceptions import TooManyRedirects
from requests.exceptions import RequestException
from requests.exceptions import ConnectionError

import settings
import tunneling
from exceptions.tinyurl_exceptions import TinyUrlPreviewException, TinyUrlUpdateError

tunneling_service = tunneling.TunnelServiceHandler(settings.TUNNELING_SERVICES_URLS)


def status_service(tinyurl, lock, shared_data):
    while True:
        delay = shared_data['ping_interval']
        tinyurl.redirect_url_short = shared_data[tinyurl.id]
        try:
            ping_check(tinyurl)
        except TinyUrlPreviewException:
            logging.warning(f'Preview page is blocking Tinyurl({tinyurl.id}) for {tinyurl.redirect_url_short}!')
            tinyurl.alternate_tunnel = tunneling_service.cycle_next()
            logging.info(f'Updating redirect to alternate url {tinyurl.alternate_tunnel}...')
            try:
                tinyurl.update_redirect(tinyurl.alternate_tunnel)
                with lock:
                    shared_data[tinyurl.id] = tinyurl.redirect_url_short
            except TinyUrlUpdateError as e:
                logging.error(e)
                continue

        except ConnectionError as e:
            error_message = str(e)
            if "Max retries exceeded" in error_message:
                # Handle the specific error message
                logging.warning(f'{tinyurl.url} is an incorrect URL!...{e}')
            elif "Failed to establish a new connection" in error_message:
                # Handle the specific error message
                logging.warning(f'Failed to establish a new connection for Tinyurl({tinyurl.id})...{e}')
                break
            else:
                pass
        except (RequestException, TooManyRedirects) as e:
            logging.warning(f'Error for Tinyurl({tinyurl.id}): {e}')
            break
        except Exception as e:
            logging.warning(f'Connection error for Tinyurl({tinyurl.id})...{e} Please check!')
            break
        finally:
            time.sleep(delay)


@retry(stop=stop_after_attempt(3))
def ping_check(tinyurl):
    try:
        response = requests.head(tinyurl.tinyurl)
        if 'tiny' in response.url:
            raise TinyUrlPreviewException()
        if tinyurl.redirect_url_short.strip('/').split('.')[-2:] == response.url.strip('/').split('//')[-1].split('.')[-2:]:
            logging.info(f'Tinyurl({tinyurl.id}) - {tinyurl.tinyurl}  -->  {tinyurl.redirect_url_short}')
        else:
            logging.warning(f'Tinyurl ({tinyurl.id}) - {tinyurl.tinyurl}  -->  {response.url}. Expected {tinyurl.redirect_url_short}!')

    except TooManyRedirects as e:
        logging.error(f'Too many redirects: {e}')

    except (RequestException, ConnectionError) as e:
        logging.error(f'Network error: {e}')

    except Exception as e:
        logging.error(f'An unexpected error occurred: {e}')
