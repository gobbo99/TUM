from utility.ansi_codes import AnsiCodes

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


