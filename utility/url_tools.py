import random
import string


def generate_unique_string(existing_strings, length=8):
    random_string = ''.join(random.sample(string.ascii_letters, length))
    while random_string in existing_strings:
        random_string = ''.join(random.sample(string.ascii_letters, length))
    return random_string


def check_format_vadility():
    pass


def get_short_domain(url):
    return '.'.join(url.split('//')[-1].split('/')[0].split('.')[-2:])
