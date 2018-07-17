## Overview ##
Recent changes Gamepedia compatible Discord webhook is a project made from earlier recent changes module of FriskBot. It has been remade as independent script for public usage. 

### Dependencies ###
* **Python 3.6>**
* requests 2.18.4>
* beautifulsoup 4.6.0>
* lxml 4.2.1>
* schedule 0.5.0>

### Features ###
* Fetch recent changes from Gamepedia wiki and send them to Discord channel using a webhook
* Send day overview, that lists how active was the wiki this day
* Can support multiple languages
* Re-sends edits after down-time

### settings.json ###
[Explanation for settings](/Settings.json)    

### How to use ###
Make sure you have installed all of dependencies and **filled settings.json properly**. You can also use `pip install -r requirements.txt` to install dependencies automatically. If you are using Raspberry Pi you won't have newest Python version installed, you can use [this guide](https://gist.github.com/dschep/24aa61672a2092246eaca2824400d37f).
When you are sure everything is fine, go to root directory with all of script files and use `python rcgcdw.py` or `python3 rcgcdw.py`command to run the script. 
Here is how you can setup the script in just few commands on a Linux distribution.
```bash
$ git clone https://gitlab.com/piotrex43/RcGcDw.git
$ cd RcGcDw
$ pip3 install -r requirements.txt
$ nano config.json.example
$ mv config.json.example config.json
$ python3 rcgcdw.py
```

#### Free (?) hosting ####
If you want I can host the script for you for free. Just [contact me](https://minecraft.gamepedia.com/User:Frisk#Contact). If you want to go with this option, be aware that this is far from the best option, I host all of the scripts on my Raspberry PI, it can go down at any moment, I try to keep every script running, but obviously sometimes it's just not possible. So, choosing this option, don't expect 100% uptime. The only requirement if you want to go with this option, is that the wiki is somewhat active.

### Credits ###
* I'd like to thank Minecraft Wiki English Discord server community, most notably Jack McKalling for input on how the script should work, especially formatting and what information should be there.
* MarkusRost for enormous help with pointing out bugs and space for improvements. 

Translators: 
* MarkusRost for German translation
* JSBM for French translation

### Other ###
Script seem to use about 10-17MB of RAM and negligible amount of CPU when fetching changes.    
Script does not log bot actions by default.    
"I GoT "Unable to process the event" mESSage!!! WHaT HApND?" - it means there is some kind of action that does not have a template in the script, please [create a ticket](https://gitlab.com/piotrex43/RcGcDw/issues/new?issue%5Bassignee_id%5D=&issue%5Bmilestone_id%5D=) with information on what wiki this error ocurred and when.    
[Here](https://imgur.com/a/ACOMyak) are screenshots of how few embeds look like.

### License ###
Everything except the locale directory is under GNU Affero General Public License v3.0 license. The translations are used with allowance of translators, and all rights to them are owned by their respective authors.

### Currently running on ###
There are several Discord server, the script is already running on, you can join them and see it working.     
[Conan Exiles](https://discord.gg/5252dZh)    
[Minecraft Wiki English](https://discord.gg/fGdE5ZE)    
[Minecraft Wiki (DE)](https://discord.gg/F75vfpd) (on a hidden channel)    
[Minecraft Wiki Polska](https://discord.gg/9ZCcTnT)    
[Minecraft Wiki FR](https://discord.gg/PSK48k7) (temporarily)    

