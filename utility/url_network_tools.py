from urllib.parse import urlparse

import requests
from requests.exceptions import *

from utility.url_tools import get_final_domain


def is_resource_available(url):
    try:
        response = requests.head(url)
        if urlparse(response.url).netloc == urlparse(url).netloc:
            return True
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        raise e
    except Exception:
        raise requests.exceptions.RequestException


def get_valid_urls(urls):
    valid_urls = []
    full_urls = [f'https://{url}' if not urlparse(url).scheme else url for url in urls]
    for url in full_urls:
        if is_resource_available(url):
            valid_urls.append(url)
        else:
            print(f'URL: {url} is not available. Discounted from list!')
    return valid_urls


def check_redirect_url(url, target_url):
    try:
        response = requests.head(url, timeout=5, allow_redirects=True)
        response_domain = get_final_domain(response.url)
        target_domain = get_final_domain(target_url)
        if response_domain == target_domain:
            return url
    except (HTTPError, Timeout, RequestException, ConnectionError):
        return



