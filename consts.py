from utility.ansi_colors import bwhite, byellow, yellow

menu = f"""
{byellow}SYNOPSIS:
{bwhite}new <url>      - {yellow}Create a new TinyURL redirect URL
{bwhite}select <id>    - {yellow}Select a TinyURL instance by its ID
{bwhite}update <url>   - {yellow}Update the redirect for the selected TinyURL
{bwhite}delete <id>    - {yellow}Delete a TinyURL with the selected ID
{bwhite}delay <sec>    - {yellow}Change the pinging interval (e.g., 'delay 5 sec' or 'delay 1 min')
{bwhite}token <id>     - {yellow}Select a token by ID
{bwhite}ping           - {yellow}Ping sweep all TinyURLs and check their status
{bwhite}current        - {yellow}Display the currently selected TinyURL instance
{bwhite}info           - {yellow}Display full information on active TinyURLs
{bwhite}list           - {yellow}List all active TinyURLs and other information
{bwhite}tokens         - {yellow}List available tokens
{bwhite}help           - {yellow}Display this menu
{bwhite}clear          - {yellow}Clear the screen
{bwhite}exit           - {yellow}Exit the program
"""

cursor_up = '\x1b[1A'
erase_line = '\x1b[2K'

