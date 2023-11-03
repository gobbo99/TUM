import random
import string
import re
from urllib.parse import urlparse


def generate_string_5_30(length=5):
    random_string = ''.join(random.sample(string.ascii_letters, length))
    return random_string


def check_format_vadility():
    pass


def get_short_domain(url):
    return '.'.join(url.split('//')[-1].split('/')[0].split('.')[-2:])


"""
get_final_domain returns <2lvl-domain>.<tld>
"""


def get_final_domain(url):
    parsed_url = urlparse(url)
    domain_parts = re.split(r'\.|/', parsed_url.netloc)  # Split by dots and slashes
    final_domain = ".".join(domain_parts[-2:])  # Join the last two parts
    return final_domain

"""
def add_https(*urls, url=None):
    full_urls = []
    if url:
        if not url.startswith('http'):
            return 'https://' + url
        return url
    else:
        for url in urls:
            if not url.startswith('http'):
                full_urls.append('https://' + url)
            else:
                full_urls.append(url)
        return full_urls
"""