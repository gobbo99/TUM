import os
import configparser

env_data = {}

if os.path.exists('.env'):
    with open('.env', 'r') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                env_data[key] = value
else:
    print('.env file not found')

PING_INTERVAL = env_data['PING_DELAY'] or 30

config_file = configparser.ConfigParser()
config_file.read('config.ini')
AUTH_TOKENS_PATH = config_file['Path']['auth_tokens_path']
FALLBACK_URLS_PATH = config_file['Path']['fallback_urls_path']
LOGS_PATH = config_file['Path']['logs_path']

with open(f'{AUTH_TOKENS_PATH}/tokens.txt', 'r') as f:
    token_data = f.read()

try:
    with open(f'{FALLBACK_URLS_PATH}/fallback_urls.txt', 'r') as f:
        alternate_urls = f.read()
except (FileNotFoundError, EOFError):
    alternate_urls = ''

if LOGS_PATH:
    LOGS_PATH.rstrip('/\\')

TINY_URL_AUTH_TOKENS = token_data.splitlines()
TUNNELING_SERVICES_URLS = alternate_urls.splitlines()


