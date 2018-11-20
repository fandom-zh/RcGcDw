## Overview ##
Recent changes Gamepedia compatible Discord webhook is a project made from earlier recent changes module of FriskBot. It has been remade as independent script for public usage.    
Presentation on how it looks on the Discord can be found [on the wiki](https://gitlab.com/piotrex43/RcGcDw/wikis/Presentation).

### Dependencies ###
* **Python 3.6>**
* requests 2.18.4>
* beautifulsoup 4.6.0>
* schedule 0.5.0>
* lxml 4.2.1>

### Features ###
* Fetch recent changes from Gamepedia wiki and send them to Discord channel using a webhook
* Send day overview, that lists how active was the wiki this day
* Can support multiple languages
* Re-sends edits after down-time

### settings.json ###
[Explanation for settings](https://gitlab.com/piotrex43/RcGcDw/wikis/settings.json)    

### How to use ###
[Refer to the guide on the wiki](https://gitlab.com/piotrex43/RcGcDw/wikis/Guide)

#### Free (?) hosting ####
If you want I can host the script for you for free. Just [contact me](https://minecraft.gamepedia.com/User:Frisk#Contact). If you want to go with this option, be aware that this is far from the best option, I host all of the scripts on my Raspberry PI, it can go down at any moment, I try to keep every script running, but obviously sometimes it's just not possible. So, choosing this option, don't expect 100% uptime. The only requirement if you want to go with this option, is that the wiki is somewhat active.

### Credits ###
* I'd like to thank Minecraft Wiki English Discord server community, most notably Jack McKalling for input on how the script should work, especially formatting and what information should be there.
* MarkusRost for enormous help with pointing out bugs and space for improvements. 

Translators: 
* MarkusRost for German translation
* JSBM for French translation
* Eduaddad for Brazilian Portuguese translation
* BabylonAS for Russian translation

### Support ###
The script does have [its own channel](https://discord.gg/pFDZrnE) on MarkusRost's Discord server. All updates will be announced there. If you need help feel free to hop there.    
"A message "Unable to process the event" appeared on my channel, what does it mean" - it means there is some kind of action that does not have a template in the script, please [create a ticket](https://gitlab.com/piotrex43/RcGcDw/issues/new?issue%5Bassignee_id%5D=&issue%5Bmilestone_id%5D=) with information on what wiki this error ocurred and when.    

### Performance ###
Script seem to use about 10-17MB of RAM and negligible amount of CPU when fetching changes.    

### License ###
Everything except the locale directory is under GNU Affero General Public License v3.0 license. The translations are used with allowance of translators, and all rights to them are owned by their respective authors.

### Currently running on ###
There are several Discord server, the script is already running on, you can join them and see it working.     
[Conan Exiles](https://discord.gg/5252dZh)    
[Minecraft Wiki English](https://discord.gg/fGdE5ZE)    
[Minecraft Wiki (DE)](https://discord.gg/F75vfpd) (on a hidden channel)    
[Minecraft Wiki Polska](https://discord.gg/9ZCcTnT)    
[Minecraft Wiki FR](https://discord.gg/PSK48k7) (temporarily)    
Minecraft Wiki BR    
Survived By Wiki    

