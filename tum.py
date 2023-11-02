import os
import sys
import re
import logging
import time

from datetime import datetime
from pathlib import Path
from multiprocessing import Process, Lock, Manager

from tinyurl import TinyUrl
from utility import *
from consts import menu, cursor_up, erase_line
from exceptions.tinyurl_exceptions import TinyUrlCreationError, TinyUrlUpdateError, InputException
from services.heartbeat import status_service
import logconfig
import settings

test = ['EYp9ninnX7AVa3Wi7g4lP82JOLSZh27LQuJIWA5ODYV9HcyUG3FIosSIdJXw', 'G1ePGvH2SlLOpFIj8AgR6Ngvtw5HngBA9Py7h0N0BhxsIgUfndMOeG1NSBUr']

logger = logging.getLogger('')
SUCCESS = 25


class TinyUrlManager:
    def __init__(self, app_config:dict):  #  test del
        self.selected_tinyurl:TinyUrl = None
        self.auth_tokens:[] = None
        self.fallback_urls:[] = None
        self.id_tinyurl_mapping = {}
        self.id_process_mapping = {}
        self.manager = Manager()
        self.lock = self.manager.Lock()
        self.shared_data = self.manager.dict()

        if app_config:
            self.shared_data.update({
                'ping_interval': app_config['ping_interval'],
                'ping_sweep': False,
                'for_deletion': False,

            })
            self.fallback_urls = app_config['fallback_urls']
            self.auth_tokens = app_config['auth_tokens']
        else:
            self.shared_data.update({
                'ping_interval': app_config['ping_interval'],
                'ping_sweep': False,
                'for_deletion': False,
            })
            self.fallback_urls = settings.TUNNELING_SERVICE_URLS
            self.auth_tokens = settings.AUTH_TOKENS

        self.token_index = 0   #  won-t need for package verison

    def run(self):
        global test
        print(menu)
        while True:
            try:
                user_input = input(f'\n{byellow}> ').strip()
                if self.handle_user_input(user_input):
                    break
            except InputException as e:
                handle_invalid_input(e.message)
            except TinyUrlCreationError as e:
                print(f'{red}{e.message}')
            except TinyUrlUpdateError as e:
                print(f'{red}{e}')
            except KeyboardInterrupt:
                for process in self.id_process_mapping.values():
                    process.terminate()
                    process.join()
                sys.stdout.write(cursor_up + erase_line)
                print(f'\n{bwhite}Thank you for using TUM!{bred}\u2665\n{byellow}[TUM version 1.0]')
                return 0

    def handle_user_input(self, user_input):
        user_input = re.split(r"\s+", user_input)
        command = user_input[0]

        if len(user_input) > 1 and command == 'new':
            try:
                url = user_input[1]
                new_id = self.get_next_available_id()
                print(new_id)
                tiny_url = TinyUrl(self.auth_tokens[self.token_index], self.fallback_urls, new_id)

            except (IndexError, ValueError, AttributeError):
                raise InputException(' '.join(user_input))

            try:
                tiny_url.create_redirect_url(url)
            except TinyUrlCreationError as e:
                raise e

            print(f'{green}Tinyurl({tiny_url.id}) created!')

            self.id_tinyurl_mapping.update({tiny_url.id: tiny_url})
            self.selected_tinyurl = tiny_url

            with self.lock:
                self.shared_data[tiny_url.id] = f'{tiny_url.redirect_url_long};{tiny_url.redirect_url_short}'

            new_process = Process(target=status_service, args=(self.selected_tinyurl, self.lock, self.shared_data,))
            new_process.daemon = True
            new_process.start()
            self.id_process_mapping[tiny_url.id] = new_process

        elif command == 'select':
            try:
                num = re.search(r'\d+', user_input[1])
                num = int(num.group())
                if num not in self.id_tinyurl_mapping.keys():
                    print(f'{red}Tinyurl({num}) is invalid!')
                    print(f'{yellow}Available tinyurls:\n')
                    self.print_short()
                else:
                    self.selected_tinyurl = self.id_tinyurl_mapping[num]
                    print(f'{green}Tinyurl({num}) selected!')

            except (IndexError, ValueError, AttributeError):
                raise InputException(' '.join(user_input))

        elif command == 'delete' or command == 'del':
            try:
                num = re.search(r'\d+', user_input[1])
                num = int(num.group())
                if num in self.id_tinyurl_mapping.keys():
                    process_to_terminate = self.id_process_mapping[num]
                    process_to_terminate.terminate()
                    process_to_terminate.join()
                    self.id_process_mapping.pop(num)

                    print(f'{bgreen}Tinyurl ({num}) deleted!')
                    logger.info(f'Tinyurl ({num}) deleted!')
                    self.id_tinyurl_mapping.pop(num)

                    if self.selected_tinyurl.id == num:
                        print(f'{byellow}Tinyurl ({num}) unselected!')
                        self.selected_tinyurl = None
                else:
                    print(f"{red}Tinyurl({num}) is invalid!\n")
                    self.print_short()

            except (IndexError, ValueError, AttributeError):
                    raise InputException(' '.join(user_input))

        elif command == 'update':
            try:
                url = user_input[1]
            except (IndexError, ValueError, AttributeError):
                raise InputException(' '.join(user_input))
            if not self.selected_tinyurl:
                print(f'{red}TinyUrl not selected!')
                self.print_short()
                return 0
            try:
                self.id_tinyurl_mapping[self.selected_tinyurl.id].update_redirect(url)
                updated_tinyurl = self.id_tinyurl_mapping[self.selected_tinyurl.id]
                updated_redirect = f'{updated_tinyurl.redirect_url_long};{updated_tinyurl.redirect_url_short}'
                with self.lock:
                    self.shared_data[updated_tinyurl.id] = updated_redirect
                print(f'{green}Tinyurl({self.selected_tinyurl.id}) updated!')
            except TinyUrlUpdateError as e:
                raise TinyUrlUpdateError(e.message, e.status_code)

        elif command == 'current':
            self.synchronize_data()
            if self.selected_tinyurl.__str__() == 'None':
                print(f'{red}No tinyurl is selected!')
            else:
                print(self.selected_tinyurl.__str__())

        elif command == 'info':
            self.synchronize_data()
            self.print_all()
            print(f'{green}_______________________')
            print(f"Pinging interval is {self.shared_data['ping_interval']}s")

        elif command == 'list' or command == 'l':
            self.synchronize_data()
            self.print_short()
            print(f'{green}_______________________')
            print(f"Pinging interval is {self.shared_data['ping_interval']}s")

        elif command == 'tokens':
            for i, token in enumerate(self.auth_tokens):
                print(f'{yellow}{i + 1}. - {token}')
            print(f'Current token:\n{self.auth_tokens.index(self.token_index) + 1}. - {byellow}{self.token_index}')

        elif command == 'next':
            token_index = (self.auth_tokens.index(self.token_index) + 1) % len(self.auth_tokens)
            self.token_index = self.auth_tokens[token_index]
            print(f'{bwhite}Token changed to:\n{yellow}{token_index + 1}. - {self.token_index}')

        elif command == 'delay':
            try:
                match = re.search(r'(\d+)(.*$)?', user_input[1])
                num, unit = match.groups()
                num = int(num)
                if unit == 'm':
                    num = num * 60
                with self.lock:
                    self.shared_data['ping_interval'] = num
                print(f'{green}Pinging interval changed to {num} seconds!')
                logger.info(f'Pinging interval changed to {num} seconds!')
            except (IndexError, ValueError, AttributeError):
                print(f'{red}[ delay <seconds> or delay <minutes>m]')
                raise InputException(' '.join(user_input))

        elif command == 'ping':
            logger.info('Ping sweeping all urls...')
            print(f'{bgreen}\nPing sweeping in progress...')
            with self.lock:
                self.shared_data['ping_sweep'] = True
                time.sleep(5)
                self.shared_data['ping_sweep'] = False
            cursor_up = '\x1b[1A'
            erase_line = '\x1b[2K'
            print(cursor_up + erase_line)
            print('\033[2A')

        elif command == 'help':
            print(menu)

        elif command == 'exit':
            for process in self.id_process_mapping.values():
                process.terminate()
                process.join()
            slow_print(f'{bwhite}Thank you for using TUM!{bred}\u2665', 0.05)
            time.sleep(0.05)
            print(f'{byellow}[TUM version 1.0]')
            return -1

        elif command == 'clear' or command == 'cls':
            os.system('clear')  # Unix
        else:
            handle_invalid_input(' '.join(user_input))

    def print_all(self):
        for tinyurl in self.id_tinyurl_mapping.values():
            print(f'{yellow}{tinyurl}')

    def print_short(self):
        for tinyurl in self.id_tinyurl_mapping.values():
            if len(tinyurl.redirect_url_long) > 32:
                print(f'{yellow}{tinyurl.id}. {tinyurl.tinyurl} -->  http://{tinyurl.redirect_url_short}/...')
            else:
                print(f'{yellow}{tinyurl.id}. {tinyurl.tinyurl} -->  {tinyurl.redirect_url_long} ')

    def synchronize_data(self):
        if self.shared_data['for_deletion']:
            self.purge_inactive_tinyurl(self.shared_data['for_deletion'])
        for tinyurl in self.id_tinyurl_mapping.values():
            tinyurl.redirect_url_long = self.shared_data[tinyurl.id].split(';')[0]
            tinyurl.redirect_url_short = self.shared_data[tinyurl.id].split(';')[1]

    def get_next_available_id(self):
        if self.id_tinyurl_mapping.keys():
            last_id = max(self.id_tinyurl_mapping.keys())
            assigned_id = last_id + 1
        else:
            assigned_id = 1

        return assigned_id

    def purge_inactive_tinyurl(self, id_for_deletion):
        process_to_terminate = self.id_process_mapping[id_for_deletion]
        process_to_terminate.terminate()
        process_to_terminate.join()

        self.id_tinyurl_mapping.pop(id_for_deletion)

        if self.selected_tinyurl.id == id_for_deletion:
            self.selected_tinyurl = None

        with self.lock:
            self.shared_data.pop(id_for_deletion)
            self.shared_data['for_deletion'] = None


def handle_invalid_input(input):   #  move
    print(f'{red}\nInvalid input: {reset}{input}')
    print(menu)


def create_log_file():
    created_at = datetime.now().strftime('%c') + '.txt'
    logs_path = Path(settings.LOGS_PATH)
    log_dir = logs_path / '.tum_logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    final_path = log_dir / created_at
    final_path.touch()
    print(f"{white}Logs are saved in {log_dir}\n\n")
    slow_print(f'{byellow}TUM[{settings.VERSION}] {bred}\u2665{reset}', 0.04)
    slow_print('__________', 0.04)
    return final_path, log_dir / 'temp'


#  Initialize console, file, queue handlers
def initialize_loggers():   #   move
    log_format = "%(custom_time)s - %(levelname)s - %(message)s"
    color_formatter = logconfig.ColoredFormatter(log_format)
    debug_formatter = logconfig.DebugFormatter(log_format)
    logging.addLevelName(SUCCESS, 'SUCCESS')
    logger.setLevel(logging.DEBUG)  #  debug//

    #  File Handler
    full_path, temp_file = create_log_file()
    file_handler = logging.FileHandler(full_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(debug_formatter)

    #  Live feed handler
    temp_handler = logconfig.LiveFeedHandler(formatter=color_formatter, path=temp_file)
    temp_handler.setLevel(logging.INFO)
    temp_handler.setFormatter(color_formatter)

    logger.addHandler(file_handler)
    logger.addHandler(temp_handler)


if __name__ == '__main__':
    initialize_loggers()
    tinyurl_manager = TinyUrlManager({'ping_interval': 69, 'auth_tokens': test, 'fallback_urls': ['index.hr', 'ufc.com']})
    tinyurl_manager.run()
    

