import random
import re
import string
from urllib.parse import urlparse


def generate_string_5_30(length=5):
    random_string = ''.join(random.sample(string.ascii_letters, length))
    return random_string


def get_final_domain(url):
    parsed_url = urlparse(url)
    domain_parts = re.split(r'\.|/', parsed_url.netloc)  # Split by dots and slashes
    final_domain = ".".join(domain_parts[-2:])  # Join the last two parts
    return final_domain


def check_format_validity():
    pass

