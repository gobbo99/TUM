import sys

import config
from tinyurl.tum_cli import initialize
from logconfig.loggers import initialize_loggers

if __name__ == '__main__':
    try:
        config = config.load_config()
        initialize_loggers(config)
    except Exception:
        print('Configure config.ini file properly. More information in README.md!')
        sys.exit(-1)
    tum_cli = initialize(config=config)
    try:
        tum_cli.take_user_input()
    except KeyboardInterrupt:
        tum_cli.handle_keyboard_interrupt()