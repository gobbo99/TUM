import configparser
from pathlib import Path

from utility.file_manipulation import read_data_from_file

home_dir = str(Path.home())
VERSION = '1.0'

try:
    config_file = configparser.ConfigParser(allow_no_value=True)
    config_file.read('./config/config.ini')

    LOGS_PATH = config_file.get('Path', 'logs_path').strip()
    TOKENS_PATH = config_file.get('Path', 'auth_tokens_path').strip()
    FALLBACK_URLS_PATH = config_file.get('Path', 'fallback_urls_path').strip()
    TOKENS_SEPERATOR = config_file['Path']['auth_tokens_seperator'].strip().replace('__NEWLINE__', '\n')
    FALLBACK_URLS_SEPERATOR = config_file['Path']['fallback_urls_seperator'].strip().replace('__NEWLINE__', '\n')
    PING_INTERVAL = config_file['Options'].getint('ping_interval') or 60
    TERMINAL_EMULATOR = (config_file['Options'].get('terminal_emulator') or 'gnome')

    AUTH_TOKENS = read_data_from_file(TOKENS_PATH, TOKENS_SEPERATOR)
    TUNNELING_SERVICE_URLS = read_data_from_file(FALLBACK_URLS_PATH, FALLBACK_URLS_SEPERATOR)

    if not LOGS_PATH or LOGS_PATH == '~':
        LOGS_PATH = home_dir

except Exception as e:
    print('Configure config.ini file properly. More information in README.md!')
    exit(1)
