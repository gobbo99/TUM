
## Tinyurl manager

## Overview
#### This python package enables you to generate and control many tinyurl links under domain 'tinyurl.com' and with randomly generated 8-character alias that goes after domain, e.g : tinyurl.com/4kj95b25

With this python package you are able to generate and control many tinyurl instances and ***ensure that preview page doesn't display*** for all your links.

It features fallback mechanicsm which updates redirect with url from fallback list in fallback_list file. URL Fallback list is necessary because ***Tinyurl regularly adds their own preview page.***

You are able to view realtime logs of tinyurl links health in gnome-terminal that's automatically opened

Configure tokens / auto-redirects however you want in ***settings.py***
### Requirements

Python 3+

GNOME Linux distro 

### Setup

```pip install -r requirements.txt```
```apt install gnome-terminal```

```python3.10 tinyurl.py```

You will configure your application by adding your ***authentication tokens in 'tokens' file*** that you acquire from Tinyurl website and by optionally adding ***fallback urls in 'fallback_list' file***.

Each token or url in these files must be seperated by newline.

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
