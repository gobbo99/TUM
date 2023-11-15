import configparser
from pathlib import Path

from utility.file_manipulation import read_data_from_file

home_dir = str(Path.home())
VERSION = '2.0'
#  todo: make class out of it, can change states


def load_config():
    config_file = configparser.ConfigParser(allow_no_value=True)
    config_file.read('./config.ini')

    #  PATH
    logs_path = config_file.get('Path', 'logs_path').strip()
    tokens_path = config_file.get('Path', 'auth_tokens_path').strip()
    fallback_urls_path = config_file.get('Path', 'fallback_urls_path').strip()
    tokens_seperator = config_file['Path']['auth_tokens_seperator'].strip().replace('__NEWLINE__', '\n')
    fallback_urls_seperator = config_file['Path']['fallback_urls_seperator'].strip().replace('__NEWLINE__', '\n')

    #  OPTIONS
    ping_interval = config_file['Options'].getint('ping_interval') or 60
    max_threads = config_file['Options'].getint('max_threads') or 4
    terminal_emulator = (config_file['Options'].get('terminal_emulator') or 'gnome')
    use_log = config_file['Options'].get('logger').strip() or 'no'
    use_logger = False if use_log == 'no' else True

    auth_tokens = read_data_from_file(tokens_path, tokens_seperator, allow_empty=False)
    fallback_urls = read_data_from_file(fallback_urls_path, fallback_urls_seperator)

    if not logs_path or logs_path == '~':
        logs_path = home_dir

    return {
        'logs_path': logs_path,
        'ping_interval': ping_interval,
        'max_threads': max_threads,
        'terminal_emulator': terminal_emulator,
        'use_logger': use_logger,
        'auth_tokens': auth_tokens,
        'fallback_urls': fallback_urls
    }
