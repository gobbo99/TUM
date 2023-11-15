import os
import random
import re
import subprocess
import sys
import time
from queue import Queue, Empty
from threading import Thread, Event
from urllib.parse import urlparse

from exceptions.tinyurl_exceptions import TinyUrlCreationError, TinyUrlUpdateError, InputException
from services.heartbeat import HeartbeatService
from spinner_utilities.spinner import Spinner
from .tum import TinyUrlManager
from utility.ansi_codes import AnsiCodes, slow_print

menu = f"""
{AnsiCodes.BYELLOW}SYNOPSIS:
_____________________________________________________________________________________
{AnsiCodes.BWHITE}new <url>      - {AnsiCodes.YELLOW}Create a new TinyURL redirect URL
{AnsiCodes.BWHITE}select <id>    - {AnsiCodes.YELLOW}Select a TinyURL instance by its ID
{AnsiCodes.BWHITE}update <url>   - {AnsiCodes.YELLOW}Update the redirect for the selected TinyURL
{AnsiCodes.BWHITE}delete <id>    - {AnsiCodes.YELLOW}Delete a TinyURL with the selected ID
{AnsiCodes.BWHITE}current        - {AnsiCodes.YELLOW}Display the currently selected TinyURL instance
_____________________________________________________________________________________
{AnsiCodes.BWHITE}delay <sec>    - {AnsiCodes.YELLOW}Change the pinging interval (e.g., 'delay 5 s' or 'delay 1 m')
{AnsiCodes.BWHITE}ping           - {AnsiCodes.YELLOW}Ping sweep all TinyURLs and check their status
{AnsiCodes.BWHITE}stop           - {AnsiCodes.YELLOW}Stop ping checking service
{AnsiCodes.BWHITE}start          - {AnsiCodes.YELLOW}Start ping checking service
{AnsiCodes.BWHITE}token <id>     - {AnsiCodes.YELLOW}Select a token by ID
{AnsiCodes.BWHITE}tokens         - {AnsiCodes.YELLOW}List available tokens
_____________________________________________________________________________________
{AnsiCodes.BWHITE}info           - {AnsiCodes.YELLOW}Display full information on active TinyURLs
{AnsiCodes.BWHITE}list           - {AnsiCodes.YELLOW}List all active TinyURLs and other information
{AnsiCodes.BWHITE}clear          - {AnsiCodes.YELLOW}Clear the screen
{AnsiCodes.BWHITE}help           - {AnsiCodes.YELLOW}Display this menu
{AnsiCodes.BWHITE}exit           - {AnsiCodes.YELLOW}Exit the program
_____________________________________________________________________________________
{AnsiCodes.BYELLOW}[id] {AnsiCodes.BWHITE} - {AnsiCodes.YELLOW}[tinyurl id] - prompt
"""

service_threads = []
service_active = True
app_config = None


class TumCLI(TinyUrlManager):

    def __init__(self, shared_queue: Queue, control_event: Event, feedback_event: Event, config):
        super().__init__(shared_queue, control_event, feedback_event, app_config=config)

    def handle_user_input(self):
        global service_active
        global service_threads
        user_input = input(make_prompt(self.selected_id))
        parsed_input = re.split(r"\s+", user_input)
        command = parsed_input[0]
        if command == 'new':
            try:
                url = parsed_input[1]
            except (IndexError, ValueError, AttributeError):
                raise InputException(' '.join(parsed_input))

            url = f'https://{url}' if not urlparse(url).scheme else url
            new_tinyurl = self.create_tinyurl(url)

            print(f'{AnsiCodes.GREEN}Tinyurl({new_tinyurl.id}) created!')

            self.id_tinyurl_mapping.update({new_tinyurl.id: new_tinyurl})
            self.selected_id = new_tinyurl.id

        elif command == 'select':
            try:
                num = re.search(r'\d+', parsed_input[1])
                num = int(num.group())
                if num not in self.id_tinyurl_mapping.keys():
                    print(f'{AnsiCodes.RED}Tinyurl({num}) is invalid!')
                    print(f'{AnsiCodes.YELLOW}Available tinyurls:\n')
                    self.print_short()
                else:
                    self.selected_id = num
                    print(f'{AnsiCodes.GREEN}Tinyurl({num}) selected!')

            except (IndexError, ValueError, AttributeError):
                raise InputException(' '.join(parsed_input))

        elif command == 'delete' or command == 'del':
            try:
                num = re.search(r'\d+', parsed_input[1])
                num = int(num.group())
                if num in self.id_tinyurl_mapping.keys():
                    self.control_event.set()
                    self.shared_queue.put({'delete': self.id_tinyurl_mapping[num].tinyurl})
                    self.id_tinyurl_mapping.pop(num)
                    print(f'{AnsiCodes.RED}Tinyurl [{num}] deleted from the system!')
                    self.selected_id = None if self.selected_id == num else self.selected_id
                else:
                    print(f"{AnsiCodes.RED}Tinyurl[{num}] is invalid!\n")
                    self.print_short()

            except (IndexError, ValueError, AttributeError):
                raise InputException(' '.join(parsed_input))

        elif command == 'update':
            url = parsed_input[1]
            if not self.selected_id:
                print(f'{AnsiCodes.RED}TinyUrl not selected!')
                self.print_short()
                return True
            url = f'https://{url}' if not urlparse(url).scheme else url
            self.update_tinyurl(url)
            print(f'{AnsiCodes.GREEN}Tinyurl[{self.selected_id}] updated!')

        elif command == 'current':
            if not self.selected_id:
                print(f'{AnsiCodes.RED}Tinyurl is not selected!')
            else:
                selected_tinyurl = self.id_tinyurl_mapping[self.selected_id]
                print(selected_tinyurl)

        elif command == 'info':
            self.print_all()
            print(f'{AnsiCodes.GREEN}_______________________')
            print(f"Pinging interval is {self.ping_interval} seconds")

        elif command == 'list' or command == 'l':
            self.print_short()
            print(f'{AnsiCodes.GREEN}_______________________')
            print(f"Pinging interval is {self.ping_interval} seconds")

        elif command == 'tokens':
            self.print_tokens()

        elif command == 'token':
            try:
                num = re.search(r'\d+', parsed_input[1])
                token_id = int(num.group())
                if not self.auth_tokens[token_id - 1]:
                    print(f'{AnsiCodes.RED}Token ({token_id}) is invalid!')
                    print(f'{AnsiCodes.BYELLOW}Available tokens:')
                    self.print_tokens()
                else:
                    self.token_id = token_id
                    self.api_client.switch_auth_token(token_id)
                    print(f'{AnsiCodes.WHITE}Token changed to:\n{token_id}. - {AnsiCodes.GREEN}'
                          f'{self.auth_tokens[token_id - 1]}')
            except (IndexError, ValueError, AttributeError):
                raise InputException(' '.join(parsed_input))

        elif command == 'delay':
            if service_active:
                try:
                    match = re.search(r'(\d+)(.*$)?', parsed_input[1])
                    num, unit = match.groups()
                    num = int(num)
                    if unit in ['m', 'min', 'minutes']:
                        num = num * 60
                    if unit in ['h', 'hrs', 'hours']:
                        num = num * 3600
                    with Spinner(text='Changing delay...', spinner_type='star_spinner', color='cyan', delay=0.04):
                        self.control_event.set()
                        self.shared_queue.put({'delay': num})
                        time.sleep(1)
                    self.ping_interval = num
                    print(f'{AnsiCodes.GREEN}Pinging interval changed to {num} seconds!', flush=False)
                except (IndexError, ValueError, AttributeError):
                    specific = f'{AnsiCodes.WHITE}Correct format: {AnsiCodes.BYELLOW}[ delay <seconds> or delay <minutes>m]'
                    raise InputException(' '.join(parsed_input), specific)
            else:
                print(f'{AnsiCodes.RED}Service inactive!')

        elif command == 'ping':
            if service_active:
                with Spinner(text='Ping sweeping all urls...', spinner_type='bouncing_ball', color='cyan', delay=0.03):
                    self.control_event.set()
                    self.shared_queue.put({'ping': 0})
                    time.sleep(2)
                print(f'{AnsiCodes.GREEN}Ping sweeping done. See logs!')
            else:
                print(f'{AnsiCodes.RED}Service inactive!')

        elif command == 'stop':
            if service_active:
                with Spinner(text='Stopping pinging service...', spinner_type='star_spinner', color='red', delay=0.04):
                    self.control_event.set()
                    self.shared_queue.put({'exit': True})
                    self.shared_queue.join()
                    time.sleep(2)
                print(f'{AnsiCodes.RED}Heartbeat service stopped!')
                service_active = False
            else:
                print(f'{AnsiCodes.RED}Service inactive!')

        elif command == 'start':
            if not service_active:
                with Spinner(text='Starting pinging service...', spinner_type='star_spinner', color='green', delay=0.04):
                    load_data = {}
                    for key, value in self.id_tinyurl_mapping.items():
                        load_data.update({key: {value.tinyurl: value.domain}})
                    heartbeat = HeartbeatService(self.shared_queue, self.control_event, self.feedback_event,
                                                 self.api_client, load_data=load_data, config=app_config)
                    t1 = Thread(target=heartbeat.start_heartbeat_service, daemon=True)
                    t2 = Thread(target=self.listen_for_feedback_event, daemon=True)
                    t1.start()
                    t2.start()
                    service_threads = [t1, t2]
                    time.sleep(2)
                service_active = True
                print(f'{AnsiCodes.GREEN}Heartbeat service started!')
            else:
                print(f'{AnsiCodes.RED}Service already running!')

        elif command == 'help':
            print(menu)

        elif command == 'exit':
            exit_text = f"Thank you for using TUM!\u2665\n[TUM version 2.0]".encode('utf-8')
            animations = ['waves', 'decrypt', 'blackhole', 'burn']
            command = f'tte {random.choice(animations)}'
            subprocess.run(command, input=exit_text, shell=True)
            if service_active:
                self.control_event.set()
                self.shared_queue.put({'exit': True})
                self.shared_queue.join()
                time.sleep(1)
            return False

        elif command == 'clear' or command == 'cls':
            os.system('clear')  # Unix

        else:
            handle_invalid_input(' '.join(parsed_input))

        return True

    """
    Thread that monitors and processes external data from service that runs as t3.
    If feedback event is set  
    """
    def listen_for_feedback_event(self):
        while True:
            self.feedback_event.wait()
            self.feedback_event.clear()
            try:
                data = self.shared_queue.get()
                self.shared_queue.task_done()
                result = self.process_item(data)
                if result:
                    print(f'{AnsiCodes.RED + AnsiCodes.erase_line(2)}\rTinyurl[{result}] deleted by heartbeat service!'
                          , flush=True)
                    print(make_prompt(self.selected_id), end='')
                    if self.selected_id == result:
                        self.selected_id = None

            except Empty:
                print('Error fetching service data!')

    def take_user_input(self):
        slow_print(f'{AnsiCodes.BYELLOW}TUM[2.0] {AnsiCodes.CYAN}\u2665{AnsiCodes.RESET}', 0.04)
        slow_print('__________', 0.04)
        print(menu, end='')
        keep_running = True
        while keep_running:
            try:
                if service_active:
                    self.shared_queue.join()
                keep_running = self.handle_user_input()
            except InputException as e:
                handle_invalid_input(e)
            except KeyboardInterrupt:
                self.handle_keyboard_interrupt()
                break
            except (TinyUrlUpdateError, TinyUrlCreationError) as e:
                print(e)
            except Exception as e:
                print(e)

    @Spinner(text='Shutting down...', spinner_type='star_spinner', color='cyan', delay=0.03)
    def handle_keyboard_interrupt(self):
        sys.stdout.write(AnsiCodes.move_cursor_up(1) + AnsiCodes.erase_line(2))
        print(f'\n{AnsiCodes.BWHITE}Thank you for using TUM!{AnsiCodes.CYAN}\u2665\n{AnsiCodes.BYELLOW}[TUM version 2.0]')
        if service_active:
            self.control_event.set()
            self.shared_queue.put({'exit': True})
            self.shared_queue.join()
        time.sleep(1)  # Still needs time to process shutdown


def handle_invalid_input(input, specific: str = None):
    print(f'{AnsiCodes.RED}Invalid input: {AnsiCodes.RESET}{input}')
    if specific:
        print(specific)
    print(f"{AnsiCodes.WHITE}Type 'help' to display options!")


def make_prompt(id=None):
    prompt = (f"\n{AnsiCodes.BYELLOW}[{AnsiCodes.BWHITE}{id or 'X'}"
              f"{AnsiCodes.BYELLOW}]{AnsiCodes.WHITE} >{AnsiCodes.WHITE} ")
    return prompt


@Spinner(text='Loading configuration...', spinner_type='pulse_horizontal_long', color='green', delay=0.03)
def initialize(config):
    global service_threads
    global app_config
    app_config = config
    shared_queue = Queue()
    control_event = Event()
    feedback_event = Event()
    tum = TumCLI(shared_queue, control_event, feedback_event, app_config)
    heartbeat = HeartbeatService(shared_queue, control_event, feedback_event, tum.api_client, config=app_config)
    if service_active:
        t1 = Thread(target=tum.listen_for_feedback_event, daemon=True)
        t2 = Thread(target=heartbeat.start_heartbeat_service, daemon=True)
        t1.start()
        t2.start()
    else:
        service_threads = []
    return tum
