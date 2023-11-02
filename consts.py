from utility.ansi_colors import bwhite, byellow, yellow

BASE_URL = "https://api.tinyurl.com"

menu = f'\n{byellow}SYNOPSIS: \n' \
             f'{bwhite}new <url> - {yellow}Create new tinyurl redirect url\n' \
             f'{bwhite}select <id> - {yellow}Select tinyurl instance by their id\n' \
             f'{bwhite}update <url> - {yellow}Update redirect for selected tinyurl\n' \
             f'{bwhite}delete <id> - {yellow}Delete tinyurl with selected id\n' \
             f'{bwhite}delay <seconds> - {yellow}Change pinging interval for every tinyurl service\n' \
             f'{bwhite}ping - {yellow}Ping sweep all tinyurls and check their status\n' \
             f'{bwhite}current - {yellow}Display currently selected tinyurl instance\n' \
             f'{bwhite}info - {yellow}Display full information on active tinyurls\n' \
             f'{bwhite}list - {yellow}List all active tinyurls and other info\n' \
             f'{bwhite}tokens - {yellow}List available tokens\n' \
             f'{bwhite}next- {yellow}Use next token on list\n' \
             f'{bwhite}help - {yellow}Display this menu\n' \
             f'{bwhite}clear - {yellow}Clear screen\n' \
             f'{bwhite}exit - {yellow}Very fancy exit'
