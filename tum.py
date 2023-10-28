import sys
import re
import logging
import time

from datetime import datetime
from pathlib import Path
from subprocess import Popen
from multiprocessing import Process, Lock, Manager

from tinyurl import TinyUrl
from utility import *
from consts import HELPER as helper
from exceptions.tinyurl_exceptions import TinyUrlCreationError, InputException
from services.heartbeat import status_service
import settings

TINY_URL_AUTH_TOKENS = settings.TINY_URL_AUTH_TOKENS


class TinyUrlManager:
    def __init__(self):
        self.selected_by_id = None
        self.selected_tinyurl = None
        self.selected_token = TINY_URL_AUTH_TOKENS[0]
        self.tinyurls = []
        self.id_tinyurl_mapping = {}       # {tinyurl_id: tinyurl}
        self.tinyurl_process_mapping = {}  # {tinyurl_id: process_object}
        self.processes = []
        self.manager = Manager()
        self.shared_data = self.manager.dict()
        self.shared_data['ping_interval'] = int(settings.PING_INTERVAL)
        self.lock = Lock()

    def handle_input(self, user_input):
        user_input = re.split(r"\s+", user_input)
        command = user_input[0]

        if len(user_input) > 1 and command == 'new':
            try:
                url = user_input[1]
                tiny_url = TinyUrl(self.selected_token)
            except (IndexError, ValueError, AttributeError):
                raise InputException(' '.join(user_input))
            try:
                tiny_url.create_redirect_url(url)
            except TinyUrlCreationError as e:
                raise TinyUrlCreationError(e.message, e.status_code)
            if self.tinyurls:
                last_id = max(self.id_tinyurl_mapping.keys())
                next_id = last_id + 1
            else:
                next_id = 1

            tiny_url.id = next_id
            print(f'{green}Tinyurl({tiny_url.id}) created!')

            self.selected_by_id = next_id
            self.id_tinyurl_mapping.update({next_id: tiny_url})

            self.tinyurls.append(tiny_url)
            self.selected_tinyurl = tiny_url
            self.shared_data[tiny_url.id] = tiny_url.redirect_url_short

            new_process = Process(target=status_service, args=(self.selected_tinyurl, self.lock, self.shared_data,))  # Update new_process value
            new_process.daemon = True
            new_process.start()

            self.processes.append(new_process)
            self.tinyurl_process_mapping[tiny_url.id] = new_process

        elif command == 'select':
            try:
                num = re.search(r'\d+', user_input[1])
                num = int(num.group())
                if num not in self.id_tinyurl_mapping.keys():
                    print(f'{red}Tinyurl({num}) is invalid!')
                    self.print_short()
                else:
                    self.selected_tinyurl = self.id_tinyurl_mapping[num]

            except (IndexError, ValueError, AttributeError):
                raise InputException(' '.join(user_input))

        elif command == 'delete' or command == 'del':
            try:
                id_to_delete = re.search(r'\d+', user_input[1]).group()
                if id_to_delete in self.id_tinyurl_mapping.keys():
                    process_to_terminate = self.tinyurl_process_mapping[id_to_delete]
                    self.tinyurl_process_mapping.pop(id_to_delete)
                    process_to_terminate.terminate()
                    process_to_terminate.join()
                    self.processes.remove(process_to_terminate)

                    deleted_tinyurl = self.id_tinyurl_mapping[id_to_delete]
                    print(f'{bgreen}Tinyurl ({deleted_tinyurl.id}) deleted!')
                    logging.warning(f'Tinyurl ({deleted_tinyurl.id}) deleted!')
                    logging.warning(f'Linked daemon shut down!')
                    self.id_tinyurl_mapping.pop(id_to_delete)                             #  {id: tinyurl_object}

                    if self.selected_tinyurl.id == id_to_delete:
                        print(f'{byellow}Tinyurl ({id_to_delete}) unselected!')
                        self.selected_tinyurl = None
                    self.tinyurls.remove(deleted_tinyurl)
                else:
                    print(f"{red}Tinyurl({id_to_delete}) doesn't exist!")
                    self.print_short()

            except (IndexError, ValueError, AttributeError):
                    raise InputException(' '.join(user_input))

        elif command == 'update':
            try:
                url = user_input[1]
            except (IndexError, ValueError, AttributeError):
                raise InputException(' '.join(user_input))

            if self.selected_tinyurl:
                tinyurl_to_update = self.id_tinyurl_mapping[self.selected_tinyurl.id]
                if tinyurl_to_update.update_redirect(url):
                    print(f'{red}Tinyurl ({self.selected_tinyurl.id}) not updated!')
                else:
                    new_redirect = tinyurl_to_update.redirect_url_short
                    with self.lock:
                        self.shared_data[tinyurl_to_update.id] = new_redirect
                        for tinyurl in self.tinyurls:
                            tinyurl.redirect_url_short = self.shared_data[tinyurl.id]
            else:
                print(f'{red}TinyUrl not selected!')
                self.print_short()

        elif command == 'current':
            self.synchronize_data()
            if self.selected_tinyurl.__str__() == 'None':
                print(f'{red}No tinyurl is selected!')
            else:
                print(self.selected_tinyurl.__str__())

        elif command == 'info':
            self.synchronize_data()
            self.print_all()
            print(f'{bcyan}_______________________')
            print(f"Pinging interval is {self.shared_data['ping_interval']}s")

        elif command == 'list':
            self.synchronize_data()
            self.print_short()
            print(f'{bcyan}_______________________')
            print(f"Pinging interval is {self.shared_data['ping_interval']}s")

        elif command == 'tokens':
            for i, token in enumerate(TINY_URL_AUTH_TOKENS):
                print(f'{yellow}{i + 1}. - {token}')
            print(f'Current token:\n{TINY_URL_AUTH_TOKENS.index(self.selected_token) + 1}. - {byellow}{self.selected_token}')

        elif command == 'next':
            token_index = (self.selected_token.index(self.selected_token) + 1) % len(TINY_URL_AUTH_TOKENS)
            self.selected_token = TINY_URL_AUTH_TOKENS[token_index]
            print(f'{byellow}Token changed to:\n{yellow}{token_index + 1}. - {self.selected_token}')

        elif command == 'ping':
            try:
                num = re.search(r'\d+', user_input[1])
                seconds = int(num.group())
                with self.lock:
                    self.shared_data['ping_interval'] = seconds
                print(f'{green}Pinging interval changed to {seconds} seconds!')
                logging.warning(f'Pinging interval changed to {seconds} seconds!')
            except (IndexError, ValueError, AttributeError):
                raise InputException(' '.join(user_input))

        elif command == 'exit':
            slow_print(f'{bred}Shutting down running processes...', 0.04)
            for process in self.processes:
                process.terminate()
                process.join()
            slow_print(f'{bwhite}Thank you for using TUM!{bred}\u2665', 0.05)
            return -1
        elif command == 'help':
            print(helper)
        else:
            handle_invalid_input(' '.join(user_input))

    def print_all(self):
        for tinyurl in self.tinyurls:
            print(f'{yellow}{tinyurl}')

    def print_short(self):
        for i, tinyurl in enumerate(self.tinyurls):
            if len(tinyurl.redirect_url_short) > 32:
                temp = tinyurl.redirect_url_short.split('//', 1)[-1]
                domain = temp.split['/'][0]
                print(f'{yellow}{i + 1}.) {tinyurl.tinyurl} -->  {domain}')
            else:
                print(f'{yellow}{i + 1}.) {tinyurl.tinyurl} -->  {tinyurl.redirect_url_short} ')

    def synchronize_data(self):
        for tinyurl in self.tinyurls:
            tinyurl.redirect_url_short = self.shared_data[tinyurl.id]

    def run(self):
        slow_print(helper, 0.003)
        while True:
            try:
                user_input = input(f'\n{byellow}> {reset}').strip()
                self.handle_input(user_input)
            except InputException as e:
                handle_invalid_input(e.message)
            except TinyUrlCreationError as e:
                print(f'{red}{e}')
            except KeyboardInterrupt:
                for process in self.processes:
                    process.terminate()
                    process.join()
                cursor_up = '\x1b[1A'
                erase_line = '\x1b[2K'
                sys.stdout.write(cursor_up + erase_line)
                print(f'\n{bwhite}Thank you for using TUM!{bred}\u2665')
                break

def handle_invalid_input(input):
    print(f'{red}\nInvalid input: {reset}{input}')
    print(helper)


def create_log_file():
    created_at = datetime.now().strftime('%c') + '.txt'
    logs_path = Path(settings.LOGS_PATH)

    if not logs_path:
        home_dir = Path.home()
        log_dir = home_dir / '.tum.log'
        log_dir.mkdir(parents=True, exist_ok=True)
        final_path = log_dir / created_at
        final_path.touch()
    else:
        log_dir = logs_path / '.tum.log'
        log_dir.mkdir(parents=True, exist_ok=True)
        final_path = logs_path / created_at
        final_path.touch()

    return final_path


#  Initialize console, file, queue handlers
def initialize_loggers():
    log_format = "%(custom_time)s - %(levelname)s - %(message)s"
    formatter = ColoredFormatter(log_format)
    logger = logging.getLogger('')
    logger.setLevel(logging.INFO)

    # File Handler
    read_path = create_log_file()
    file_handler = logging.FileHandler(read_path)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    process = Popen(['gnome-terminal', '--', 'tail', '-f', read_path])

    return process, file_handler


if __name__ == '__main__':
    process, file_handler = initialize_loggers()
    tinyurl_manager = TinyUrlManager()
    while tinyurl_manager.run() == 0:
        continue
    file_handler.close()
