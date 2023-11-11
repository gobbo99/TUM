import datetime
import logging
import os
import random
import re
import subprocess
import sys
import time
import urllib
from pathlib import Path
from threading import Thread, Event
from typing import Tuple, List
from queue import Queue, Empty

import click

import logconfig
import settings
from utility.spinner import Spinner
from consts import menu
from exceptions.tinyurl_exceptions import TinyUrlCreationError, TinyUrlUpdateError, RequestError, NetworkError, \
    InputException
from services.heartbeat import HeartbeatService
from tum import TinyUrlManager
from utility.ansi_codes import green, red, cyan, byellow, bgreen, yellow, white, bwhite, bred, reset, slow_print, \
    cursor_up, erase_line

SUCCESS = 25
logging.addLevelName(SUCCESS, 'SUCCESS')
logger = logging.getLogger('live')
logger.setLevel(logging.INFO)
service_threads = []
service = None


class TumCLI(TinyUrlManager):
    def __init__(self, shared_queue: Queue, control_event: Event, feedback_event: Event):
        super().__init__(shared_queue=shared_queue, control_event=control_event, feedback_event=feedback_event)

    def handle_user_input(self, threads):
        prompt = f'{bwhite}\n>{byellow} '
        parsed_input = input(prompt)
        parsed_input = re.split(r"\s+", parsed_input)
        command = parsed_input[0]
        if command == 'new':
            try:
                url = parsed_input[1]
            except (IndexError, ValueError, AttributeError):
                raise InputException(' '.join(parsed_input))

            url = f'https://{url}' if not urllib.parse.urlparse(url).scheme else url
            new_tinyurl = self.create_tinyurl(url)

            print(f'{green}Tinyurl({new_tinyurl.id}) created!')

            self.id_tinyurl_mapping.update({new_tinyurl.id: new_tinyurl})
            self.selected_id = new_tinyurl.id

        elif command == 'select':
            try:
                num = re.search(r'\d+', parsed_input[1])
                num = int(num.group())
                if num not in self.id_tinyurl_mapping.keys():
                    print(f'{red}Tinyurl({num}) is invalid!')
                    print(f'{yellow}Available tinyurls:\n')
                    self.print_short()
                else:
                    self.selected_id = num
                    print(f'{green}Tinyurl({num}) selected!')

            except (IndexError, ValueError, AttributeError):
                raise InputException(' '.join(parsed_input))

        elif command == 'delete' or command == 'del':
            try:
                num = re.search(r'\d+', parsed_input[1])
                num = int(num.group())
                if num in self.id_tinyurl_mapping.keys():
                    self.id_tinyurl_mapping.pop(num)

                    if self.selected_id == num:
                        print(f'{byellow}Tinyurl ({num}) unselected!')
                        self.selected_id = None
                else:
                    print(f"{red}Tinyurl({num}) is invalid!\n")
                    self.print_short()

            except (IndexError, ValueError, AttributeError):
                raise InputException(' '.join(parsed_input))

        elif command == 'update':
            url = parsed_input[1]

            if not self.selected_id:
                print(f'{red}TinyUrl not selected!')
                self.print_short()
                return True

            url = f'https://{url}' if not urllib.parse.urlparse(url).scheme else url

            self.update_tinyurl(url)
            print(f'{green}Tinyurl({self.selected_id}) updated!')

        elif command == 'current':
            if not self.selected_id:
                print(f'{red}No tinyurl is selected!')
            else:
                selected_tinyurl = self.id_tinyurl_mapping[self.selected_id]
                print(selected_tinyurl)

        elif command == 'info':
            self.print_all()
            print(f'{green}_______________________')
            print(f"Pinging interval is {self.ping_interval} seconds")

        elif command == 'list' or command == 'l':
            self.print_short()
            print(f'{green}_______________________')
            print(f"Pinging interval is {self.ping_interval} seconds")

        elif command == 'tokens':
            self.print_tokens()

        elif command == 'token':
            try:
                num = re.search(r'\d+', parsed_input[1])
                token_id = int(num.group())
                if not self.auth_tokens[token_id - 1]:
                    print(f'{red}Token ({token_id}) is invalid!')
                    print(f'{byellow}Available tokens:')
                    self.print_tokens()
                else:
                    self.token_id = token_id
                    self.api_client.token_index_selected = token_id - 1
                    print(f'{bwhite}Token changed to:\n{green}{self.auth_tokens[token_id - 1]}')
            except (IndexError, ValueError, AttributeError) as e:
                raise InputException(' '.join(parsed_input))

        elif command == 'delay':
            try:
                match = re.search(r'(\d+)(.*$)?', parsed_input[1])
                num, unit = match.groups()
                num = int(num)
                if unit in ['m', 'min', 'minutes']:
                    num = num * 60
                if unit in ['h', 'hrs', 'hours']:
                    num = num * 3600
                with Spinner(text='Changing delay...', spinner_type='pulse_horizontal', color='cyan', delay=0.04):
                    self.shared_queue.join()
                    self.control_event.set()
                    self.shared_queue.put({'delay': num})
                    self.shared_queue.join()
                self.ping_interval = num
                print(f'{green}Pinging interval changed to {num} seconds!')
            except (IndexError, ValueError, AttributeError):
                specific = f'{white}Correct format: {byellow}[ delay <seconds> or delay <minutes>m]'
                raise InputException(' '.join(parsed_input), specific)

        elif command == 'ping':
            with Spinner(text='Ping sweeping all urls...', spinner_type='pulse_horizontal', color='cyan', delay=0.04):
                self.shared_queue.join()
                self.control_event.set()
                self.shared_queue.put({'ping': 0})
                self.shared_queue.join()
                time.sleep(2)

        elif command == 'stop':
            with Spinner(text='Stopping pinging service...', spinner_type='pulse_horizontal', color='cyan', delay=0.04):
                self.shared_queue.join()
                self.control_event.set()
                self.shared_queue.put({'exit': True})
                time.sleep(2)
            threads.clear()
            print(f'{green}Heartbeat service stopped!')

        elif command == 'start':
            tinyurl_target = {tinyurl.tinyurl: tinyurl.domain for tinyurl in self.id_tinyurl_mapping.values()}
            heartbeat = HeartbeatService(self.shared_queue, self.control_event, self.feedback_event, self.api_client,
                                         tinyurl_target_list=tinyurl_target)
            t1 = Thread(target=heartbeat.start_heartbeat_service(), daemon=True)
            t2 = Thread(target=self.listen_for_event(), daemon=True)
            global service_threads
            service_threads = [t1, t2]
            return True

        elif command == 'help':
            print(menu)

        elif command == 'exit':
            exit_text = f"Thank you for using TUM!\n[TUM version 1.1]".encode('utf-8')
            animations = ['waves', 'decrypt', 'blackhole', 'burn']
            command = f'tte {random.choice(animations)}'
            subprocess.run(command, input=exit_text, shell=True)
            return False

        elif command == 'clear' or command == 'cls':
            os.system('clear')  # Unix

        else:
            handle_invalid_input(' '.join(parsed_input))
        return True

    """
    Thread that monitors and processes external data from servicd that runs as t3.
    If feedback event is set  
    """
    def listen_for_event(self):
        while True:
            self.feedback_event.wait()
            try:
                self.process_item()
            except Empty:
                print('Error fetching service data!')
            finally:
                self.feedback_event.clear()

    def user_interface(self, service_threads):
        slow_print(f'{byellow}TUM[{settings.VERSION}] {cyan}\u2665{reset}', 0.04)
        slow_print('__________', 0.04)
        print(menu)
        keep_running = True
        while keep_running:
            try:
                self.shared_queue.join()
                keep_running = self.handle_user_input(service_threads)
            except InputException as e:
                handle_invalid_input(e)
            except KeyboardInterrupt:
                sys.stdout.write(cursor_up + erase_line)
                print(f'\n{bwhite}Thank you for using TUM!{bred}\u2665\n{byellow}[TUM version 1.0]')
                break
            except (TinyUrlUpdateError, TinyUrlCreationError) as e:
                print(e)
            except Exception as e:
                print(e)


def handle_invalid_input(input, specific: str = None):  # move
    print(f'{red}\nInvalid input: {reset}{input}')
    if specific:
        print(specific)
    print(f"{white}Type 'help' to display options!")


def create_log_file():
    created_at = datetime.datetime.now().strftime('%c') + '.txt'
    logs_path = Path(settings.LOGS_PATH)
    log_dir = logs_path / '.tum_logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    final_path = log_dir / created_at
    final_path.touch()
    return final_path


def initialize_loggers():
    use_logger = settings.LOGGER

    logs_path = Path(settings.LOGS_PATH)
    log_dir = logs_path / '.tum_logs'
    log_dir.mkdir(parents=True, exist_ok=True)

    if use_logger:
        full_path = create_log_file()
        initialize_file_logger(full_path)

    temp_path = log_dir / 'temp'
    temp_path.touch()
    initialize_live_logger(temp_path)


def initialize_live_logger(path):
    color_formatter = logconfig.ColoredFormatter()
    temp_handler = logconfig.LiveFeedHandler(path)
    temp_handler.setFormatter(color_formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(temp_handler)


def initialize_file_logger(path):
    log_format = "%(custom_time)s - %(levelname)s - %(message)s"
    debug_formatter = logconfig.DebugFormatter(log_format)
    file_handler = logging.FileHandler(path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(debug_formatter)
    logger.addHandler(file_handler)


@click.command()
@click.option('--service/--no-service', default=True, required=False)
@Spinner(text='Loading configuration...', spinner_type='pulse_horizontal_long', color='cyan', delay=0.03)
def initialize(service):
    shared_queue = Queue()
    control_event = Event()
    feedback_event = Event()
    tum_cli = TumCLI(shared_queue, control_event, feedback_event)
    heartbeat = HeartbeatService(shared_queue, control_event, feedback_event, tum_cli.api_client)

    if service:
        t1 = Thread(target=tum_cli.listen_for_event, daemon=True)
        t2 = Thread(target=heartbeat.start_heartbeat_service, daemon=True)
        service_threads = [t1, t2]
    else:
        service_threads = []

    t1.start()
    t2.start()

    main_thread = Thread(target=tum_cli.user_interface, args=(service_threads,))

    return main_thread, service_threads


if __name__ == '__main__':
    initialize_loggers()
    user_thread, service_threads = initialize(standalone_mode=False)
    user_thread.start()
    user_thread.join()
