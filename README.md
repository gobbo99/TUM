## TUM - Tinyurl manager

## Overview
 This package contains modern CLI for managing, generating, analyzing and automating everything concerning your tinyurls and their end target destination. 
 
It features interactive ***Heartbeat*** service which serves as a validator that regularly performs checks on your tinyurls. 

 It has very customized and tailored API which makes it a very powerful tool even if you don't use Tum CLI. 

### Prerequisites

Python 3+ - python 3 and above mandatory

Gnome/xfce-4 terminal for heartbeat service[Optional]

### Installation

***
In your directory where you cloned this repository do this:

```sudo apt install python3``` - Install python3 with apt

```pip install -r requirements.txt``` - Install python dependencies

***
### Configuration

Path for base configuration file is ***./config/config.ini***

Path for your tokens file by default is ***./config/tokens.txt***

Optionally place fallback urls in ***./config/fallback_urls.txt***

Everything regarding configuration is in ***./config/config.ini***

### CLI


*Available commands:*
_____________________________________________________________________________________
`new <url>`      - Create a new TinyURL redirect URL

`select <id>`    - Select a TinyURL instance by its ID

`update <url>`   - Update the redirect for the selected TinyURL

`delete <id>`    - Delete a TinyURL with the selected ID

`current`        - Display the currently selected TinyURL instance(selector for update and delete commands)
_____________________________________________________________________________________
`delay <sec>`    - Change the pinging interval (e.g., 'delay 5s' or 'delay 1m')

`ping`           - Ping sweep all TinyURLs and check their status

`stop`           - Stop ping checking service

`start`          - Start ping checking service

`token <id>`     - Select a token by ID

`tokens`         - List available tokens
_____________________________________________________________________________________
`info`           - Display full information on active TinyURLs

`list`           - List all active TinyURLs and other information

`clear`          - Clear the screen

`help`           - Display this menu

`exit`           - Exit the program
_____________________________________________________________________________________
**[id] - [tinyurl id] - prompt**

### CLI interface
![cli.png](cli.png)
### Logo reader terminal
![log_read.png](log_read.png)

If you have any questions, feel free to message me
