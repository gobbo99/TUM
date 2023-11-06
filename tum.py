import os
import random
import subprocess
import sys
import re
import logging
import time
from typing import Dict, List, Any, Tuple, Optional
import datetime
from pathlib import Path
import threading
from queue import Queue
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, ALL_COMPLETED


from tinyurl import TinyUrl
from api.apiclient import ApiClient
from utility import *
from consts import menu, cursor_up, erase_line
from exceptions.tinyurl_exceptions import TinyUrlCreationError, TinyUrlUpdateError, InputException, NetworkError, \
    RequestError
from services.heartbeat import status_service
from services.heartbeat_2 import HeartbeatService
import logconfig
import settings

SUCCESS = 25
logger = logging.getLogger('')
logging.addLevelName(SUCCESS, 'SUCCESS')
logger.setLevel(logging.INFO)
ping_check_event = threading.Event()


class TinyUrlManager:
    def __init__(self, shared_queue: Queue, app_config: dict = None):
        self.selected_id: int = None
        self.auth_tokens: [] = None  # identical to authclients
        self.id_tinyurl_mapping = {}
        self.shared_queue = shared_queue
        self.ping_interval = settings.PING_INTERVAL
        if app_config:
            data = {
                'delay': app_config['delay'],
            }
            self.shared_queue.put(data)
            self.fallback_urls = get_valid_urls(app_config['fallback_urls'])
            self.auth_tokens = app_config['auth_tokens']
        else:
            data = {
                'delay': self.ping_interval,
            }
            self.shared_queue.put(data)
            self.fallback_urls = get_valid_urls(settings.TUNNELING_SERVICE_URLS)
            self.auth_tokens = settings.AUTH_TOKENS

        self.api_client = ApiClient(self.auth_tokens, fallback_urls=self.fallback_urls)
        self.token_id = 1

    def run(self):
        slow_print(f'{byellow}TUM[{settings.VERSION}] {cyan}\u2665{reset}', 0.04)
        slow_print('__________', 0.04)
        print(menu)
        self.create_from_list(settings.TUNNELING_SERVICE_URLS)
        while True:
            try:
                user_input = input(f'\n{bwhite}>{byellow} ').strip()
                if self.handle_user_input(user_input):
                    break
            except InputException as e:
                handle_invalid_input(e)
            except TinyUrlCreationError as e:
                print(e)
            except TinyUrlUpdateError as e:
                print(e)
            except NetworkError as e:
                print(e)
            except RequestError as e:
                print(e)
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

        if command == 'new':
            try:
                url = user_input[1]
            except (IndexError, ValueError, AttributeError):
                raise InputException(' '.join(user_input))

            url = f'https://{url}' if not urllib.parse.urlparse(url).scheme else url

            try:
                new_tinyurl = self.create_tinyurl(url)
            except (TinyUrlCreationError, RequestError, NetworkError) as e:
                raise e

            print(f'{green}Tinyurl({new_tinyurl.id}) created!')

            self.id_tinyurl_mapping.update({new_tinyurl.id: new_tinyurl})
            self.selected_id = new_tinyurl.id
            """
            with self.lock:
                self.shared_data[new_tinyurl.id] = f'{new_tinyurl.final_url};{new_tinyurl.domain}'

            new_process = Process(target=status_service, args=(new_tinyurl, self.lock, self.shared_data,))
            new_process.daemon = True
            new_process.start()
            self.id_process_mapping[new_tinyurl.id] = new_process
            """

        elif command == 'select':
            try:
                num = re.search(r'\d+', user_input[1])
                num = int(num.group())
                if num not in self.id_tinyurl_mapping.keys():
                    print(f'{red}Tinyurl({num}) is invalid!')
                    print(f'{yellow}Available tinyurls:\n')
                    self.print_short()
                else:
                    self.selected_id = num
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

                    if self.selected_id == num:
                        print(f'{byellow}Tinyurl ({num}) unselected!')
                        self.selected_id = None
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
            if not self.selected_id:
                print(f'{red}TinyUrl not selected!')
                self.print_short()
                return 0

            url = f'https://{url}' if not urllib.parse.urlparse(url).scheme else url

            try:
                self.update_tinyurl(url)
                print(f'{green}Tinyurl({self.selected_id}) updated!')
            except (RequestError, NetworkError, TinyUrlUpdateError) as e:
                raise e

        elif command == 'current':
            self.synchronize_data()
            selected_tinyurl = self.id_tinyurl_mapping[self.selected_id]
            if selected_tinyurl.__str__() == 'None':
                print(f'{red}No tinyurl is selected!')
            else:
                print(selected_tinyurl.__str__())

        elif command == 'info':
            self.synchronize_data()
            self.print_all()
            print(f'{green}_______________________')
            print(f"Pinging interval is {self.ping_interval} seconds")

        elif command == 'list' or command == 'l':
            self.synchronize_data()
            self.print_short()
            print(f'{green}_______________________')
            print(f"Pinging interval is {self.ping_interval} seconds")

        elif command == 'tokens':
            self.print_tokens()

        elif command == 'token':
            try:
                num = re.search(r'\d+', user_input[1])
                token_id = int(num.group())
                if not self.auth_tokens[token_id - 1]:
                    print(f'{red}Token ({token_id}) is invalid!')
                    print(f'{byellow}Available tokens:')
                    self.print_tokens()
                else:
                    self.token_id = token_id
                    self.api_client.token_index_selected = token_id - 1
                    print(f'{bwhite}Token changed to:\n{yellow}{self.auth_tokens[token_id - 1]}')
            except (IndexError, ValueError, AttributeError) as e:
                raise InputException(' '.join(user_input))

        elif command == 'delay':
            try:
                match = re.search(r'(\d+)(.*$)?', user_input[1])
                num, unit = match.groups()
                num = int(num)
                if unit in ['m', 'min', 'minutes']:
                    num = num * 60
                if unit in ['h', 'hrs', 'hours']:
                    num = num * 3600
                self.shared_queue.put({'delay': num})
                self.ping_interval = num
                print(f'{green}Pinging interval changed to {num} seconds!')
            except (IndexError, ValueError, AttributeError):
                specific = f'{white}Correct format: {byellow}[ delay <seconds> or delay <minutes>m]'
                raise InputException(' '.join(user_input), specific)

        elif command == 'ping':
            logger.info('Ping sweeping all urls...')
            with Spinner(text='Ping sweeping all urls...\n', spinner_type='bouncing_ball', color='cyan', delay=0.05):
                ping_check_event.set()
                time.sleep(5)
            print(cursor_up + erase_line)
            print('\033[2A')

        elif command == 'help':
            print(menu)

        elif command == 'exit':
            exit_text = f"Thank you for using TUM!\n[TUM version 1.1]".encode('utf-8')
            animations = ['waves', 'decrypt', 'blackhole', 'burn']
            command = f'tte {random.choice(animations)}'
            subprocess.run(command, input=exit_text, shell=True)

        elif command == 'clear' or command == 'cls':
            os.system('clear')  # Unix

        else:
            handle_invalid_input(' '.join(user_input))

    @Spinner(text='Sending request to create...', spinner_type='bouncing_ball', color='cyan', delay=0.05)
    def create_tinyurl(self, url: str, urls: [] = None):
        new_id = self.get_next_available_id()
        try:
            new_tinyurl = TinyUrl(new_id)
            new_tinyurl.instantiate_tinyurl(url, self.api_client)
            self.id_tinyurl_mapping[new_tinyurl.id] = new_tinyurl
            queue_data = {'new': {'url': new_tinyurl.tinyurl, 'target': new_tinyurl.domain}}
            self.shared_queue.put(queue_data)
            return new_tinyurl
        except (TinyUrlCreationError, RequestError, NetworkError, ValueError) as e:
            print('eeeeeeeeeeeeeee')
            raise e

    @Spinner(text='Sending request to update...', spinner_type='bouncing_ball', color='cyan', delay=0.05)
    def update_tinyurl(self, url: str):
        try:
            updated_tinyurl: TinyUrl = self.id_tinyurl_mapping[self.selected_id]
            updated_tinyurl.update_redirect(url, self.api_client)
            url_info = f'{updated_tinyurl.final_url};{updated_tinyurl.domain}'

        except (TinyUrlUpdateError, RequestError, NetworkError) as e:
            raise e

    def delete_tinyurl(self, id):
        pass

    def create_from_list(self, urls: List[str]):
        results = []
        with ThreadPoolExecutor(max_workers=6) as executor:  # Adjust max_workers as needed
            futures = [executor.submit(self.create_tinyurl, url) for url in urls]
            wait(futures, return_when=ALL_COMPLETED)
        for future in as_completed(futures):
            try:
                result = future.result()
                results.append(result)  # Store the result in the list
                for result in results:
                    print(result.tinyurl)
            except Exception as e:
                pass  # Ignore exceptions

            # Handle exceptions





    def print_all(self):
        for tinyurl in self.id_tinyurl_mapping.values():
            print(f'{yellow}{tinyurl}')

    def print_short(self):
        for tinyurl in self.id_tinyurl_mapping.values():
            if len(tinyurl.final_url) > 32:
                extra_len = len(tinyurl.tinyurl.split('.')[-1])
                extra_space = (5 - extra_len) * ' '
                print(f'{yellow}{tinyurl.id}. {tinyurl.tinyurl}{extra_space}  -->  http://{tinyurl.domain}/...')
            else:
                extra_len = len(tinyurl.tinyurl.split('.')[-1])
                extra_space = (5 - extra_len) * ' '
                print(f'{yellow}{tinyurl.id}. {tinyurl.tinyurl}{extra_space}{extra_space}  -->  {tinyurl.final_url} ')

    def print_tokens(self):
        for index, token in enumerate(self.auth_tokens):
            print(f'{white}{index + 1}. - {token}')
        print(f'\n{bwhite}Current token:\n{green}{self.api_client.auth_tokens[self.token_id - 1]}')

    def synchronize_data(self):
        pass

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

        if id_for_deletion == self.selected_id:
            self.selected_id = None

        with self.lock:
            self.shared_data.pop(id_for_deletion)
            self.shared_data['delete_by_id'] = None


def handle_invalid_input(input, specific: str = None):  # move
    print(f'{red}\nInvalid input: {reset}{input}')
    if specific:
        print(specific)
    print(f"{white}Type 'help' to display options!\n")


def create_log_file():
    created_at = datetime.datetime.now().strftime('%c') + '.txt'
    logs_path = Path(settings.LOGS_PATH)
    log_dir = logs_path / '.tum_logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    final_path = log_dir / created_at
    final_path.touch()
    return final_path, log_dir / 'temp'


#  Initialize console, file, queue handlers
def initialize_loggers():  # move
    log_format = "%(custom_time)s - %(levelname)s - %(message)s"
    color_formatter = logconfig.ColoredFormatter(log_format)
    debug_formatter = logconfig.DebugFormatter(log_format)

    #  File Handler
    full_path, temp_file = create_log_file()
    file_handler = logging.FileHandler(full_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(debug_formatter)

    #  Live feed handler
    temp_handler = logconfig.LiveFeedHandler(color_formatter, temp_file, settings.TERMINAL_EMULATOR)
    temp_handler.setFormatter(color_formatter)

    logger.addHandler(temp_handler)


@Spinner(text='Loading configuration...', spinner_type='pulse_spinner', color='cyan', delay=0.1)
def initialize() -> TinyUrlManager:
    initialize_loggers()
    shared_queue = Queue()
    tum = TinyUrlManager(shared_queue=shared_queue)
    heartbeat = HeartbeatService(tum.api_client, shared_queue, ping_check_event)
    t1 = threading.Thread(target=tum.run)
    t2 = threading.Thread(target=heartbeat.run_heartbeat_service)
    return t1, t2


if __name__ == '__main__':
    tum_thread, heartbeat_thread = initialize()
    tum_thread.start()
    heartbeat_thread.start()
    tum_thread.join()
