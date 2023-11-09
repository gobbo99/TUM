from utility.ansi_codes import bwhite, byellow, yellow

menu = f"""
{byellow}SYNOPSIS:
_______________________________________________________________________________________________
{bwhite}new <url>      - {yellow}Create a new TinyURL redirect URL
{bwhite}select <id>    - {yellow}Select a TinyURL instance by its ID
{bwhite}update <url>   - {yellow}Update the redirect for the selected TinyURL
{bwhite}delete <id>    - {yellow}Delete a TinyURL with the selected ID
{bwhite}current        - {yellow}Display the currently selected TinyURL instance
_______________________________________________________________________________________________
{bwhite}delay <sec>    - {yellow}Change the pinging interval (e.g., 'delay 5 s' or 'delay 1 m')
{bwhite}ping           - {yellow}Ping sweep all TinyURLs and check their status
{bwhite}stop           - {yellow}Stop ping checking service
{bwhite}start          - {yellow}Start ping checking service
{bwhite}token <id>     - {yellow}Select a token by ID
{bwhite}tokens         - {yellow}List available tokens
_______________________________________________________________________________________________
{bwhite}info           - {yellow}Display full information on active TinyURLs
{bwhite}list           - {yellow}List all active TinyURLs and other information
{bwhite}clear          - {yellow}Clear the screen
{bwhite}help           - {yellow}Display this menu
{bwhite}exit           - {yellow}Exit the program
_______________________________________________________________________________________________
"""


