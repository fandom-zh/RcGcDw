## Overview ##
Recent changes Gamepedia compatible Discord webhook is a project made from earlier recent changes module of FriskBot. It has been remade as independent script for public usage. 

### Dependencies ###
* **Python 3.6>**
* requests 2.18.4>
* beautifulsoup 4.6.0>
* lxml 4.2.1>

### Features ###
* Fetch recent changes from Gamepedia wiki and send them to Discord channel using a webhook
* Send day overview, that lists how active was the wiki this day
* Customable with many different settings
* Can support multiple languages

### settings.json ###
Explanation for settings:    
`cooldown` – interval for how often changes are retrieved from the wiki (due to used solutions, the real interval is ~1 sec longer)    
`wiki` – wiki prefix the bot is supposed to work with (for example, for English Minecraft Wiki it's minecraft (https://**minecraft**.gamepedia.com) and for Polish Minecraft Wiki minecraft-pl (https://**minecraft-pl**.gamepedia.com    
`lang` – language for the messages, currently available options are: de, en, pl
`header` – it's recommended to leave this value as it is, it's a header the script will use to communicate with Gamepedia. Please note that without it, no communication will be possible.    
`limit` – amount of actions retrieved every `cooldown` amount of seconds. The higher it is the more network data will be used and the data will be processed longer, setting it to higher values is not recommended, but if you want to make sure no edit is omitted (which only happen if there are more actions in last `cooldown` seconds than this value).    
`webhookURL` – webhook URL you can get using channel settings in Discord     
`limitrefetch` – limit of how many changes can be retrieved when refetch happens, cannot be lower than limit. -1 if you want to disable auto-refetch    
`wikiname` – a name of the wiki the bot will work on, required in some messages    
`avatars` – this section makes specific types of messages overwrite the default webhook avatar    
* `connection_failed` – message printed when script fails connection with the wiki several times    
* `no_event` – error message when the event couldn't be recognized by the script    
* `embed` – every embed message showing changes

`verbose_level` – a number (min 0, max 50) identifying the type of messages that will be written into the console. (CRITICAL 50, ERROR 40, WARNING 30, INFO 20, DEBUG 10)    
`show_updown_messages` – bool value, depending on this settings the messages whenever the wiki goes up and down will be sent to the channel

### How to use ###
Make sure you have installed all of dependencies and filled settings.json properly.
When you are sure, use `python rcgcdw.py` command to run the script.

### Credits ###
Translators: 
* MarkusRost for German translation
* Minecraft Wiki English Discord server community, most notably Jack McKalling for input on how the script should work, especially formatting and what information should be there

### Other ###
Script seem to use about 17MB of RAM and negligible amount of CPU when fetching changes.
