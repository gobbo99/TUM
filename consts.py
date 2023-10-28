from utility.ansi_colors import bwhite, byellow, yellow

BASE_URL = "https://api.tinyurl.com"

HELPER = f'\n{bwhite}SYNOPSIS: \n' \
             f'{byellow}new <url> <token_index> - {yellow}Create new redirect to selected url(without http/s part)\n' \
             f'{byellow}select <id> - {yellow}Select tinyurl instance by their id(use list to see all)\n' \
             f'{byellow}update <url> - {yellow}Update redirect for selected tinyurl\n' \
             f'{byellow}delete <id> - {yellow}Delete tinyurl with selected id\n' \
             f'{byellow}ping <seconds> - {yellow}Change pinging interval for every tinyurl service\n' \
             f'{byellow}current - {yellow}Display currently selected tinyurl instance\n' \
             f'{byellow}info - {yellow}Display full information on active Tinyurls\n' \
             f'{byellow}list - {yellow}List all active tinyurls and other info\n' \
             f'{byellow}tokens - {yellow}List available tokens\n' \
             f'{byellow}next- {yellow}Use next token on list\n' \
             f'{byellow}help - {yellow}Display this menu\n' \
             f'{byellow}exit - {yellow}Very fancy exit'
