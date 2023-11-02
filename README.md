
## Tinyurl manager

## Overview
#### This python package enables you to instantly generate and control many tinyurl links and with randomly generated 8-character alias that goes after domain, e.g : tinyurl.com/4kj95b25

With this python package you are able to generate and control many tinyurl instances and ***ensure that preview page doesn't display*** for all your tinyurls. Tinyurl preview page blocks users from directly accessing your url.

All you need to do is add your tokens to ./config/tokens.txt and you are ready to go!

### Prerequisites

Python 3, Linux Gnome environment

GNOME Linux distro 

### Installation

After you cloned repository do the following:

```sudo apt install python3``` - Install python3

```pip install -r requirements.txt``` - Install required dependencies

```apt install gnome-terminal``` - Install gnome-terminal
***
### Setup
Place your authentication tokens in ***config/tokens.txt*** 

Optionally place alternate urls in ***config/urls.txt***

Complete your run configuration in ***config/config.ini*** 

### How it works


***create_redirect_url()*** - connects to tinyurl api and creates new tinyurl redirect to wanted url

***update_redirect()*** - updates redirect url to fallback url 

***check_status()*** - periodically checks validity of redirect each tinyurl instance

***main_cli()*** - main function that runs continuously

Log file ***'logile.log'*** is created or appended in .logs directory located in parent user home directory

***NOTE***: Not intended for large amount of tinyurl instances. 
If you don't need to manage tinyurl ***delete it with 'delete' command!***

### CLI COMMANDS

 Once you run the script you will have a cli which has following functionality:

***new [url] [token_index]***- create new tinyurl instance that redirects to <url>, <token_index> is ***optional***

***del [id]*** - delete active tinyurl instance by it's assigned id

***select [id]*** - select active tinyurl instance by their id. Useful to manually update redirect. Use 'list' to see all instances.

***update [url]*** - updates redirect url of selected tinyurl instance

***current*** - display information about current tinyurl instance and client info

***list*** - list all created tinyurl instances

***help*** - display cli commands overview

***exit*** - terminate the program, logs are saved in {home_dir}/.logs/logfile.log'
### CLI interface
![cli.png](cli.png)
### Logo reader terminal
![log_read.png](log_read.png)

If you have any questions, feel free to message me
