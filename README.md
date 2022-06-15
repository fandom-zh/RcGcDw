## Overview ##
*Recent changes Goat compatible Discord webhook* is a project created to track changes on MediaWiki wikis directly on Discord.     
**Screenshots** of the script in action can be found [on the wiki](https://gitlab.com/piotrex43/RcGcDw/wikis/Presentation).

### Features ###
* Fetch recent changes from a MediaWiki wiki and/or Discussions from Fandom wikis and send them to a Discord channel using a webhook
* Two appearance modes – embed and compact
* Send daily overviews that show general information about wiki activity
* Supports multiple languages (included EN, PL, BR, RU, FR, UK)
* Re-sends missed edits after start
* Very customizable

### Dependencies ###
* **Python 3.7+**
* requests 2.18.4+
* beautifulsoup 4.6.0+
* lxml 4.2.1+

### settings.json ###
[Explanation for settings](https://gitlab.com/piotrex43/RcGcDw/wikis/settings.json)    

### How to use ###
[Refer to the guide on the wiki](https://gitlab.com/piotrex43/RcGcDw/wikis/Guide).

### Contributors ###
* MarkusRost for enormous help with pointing out bugs, space for improvements and contributing to the code.
* I'd like to thank Minecraft Wiki English Discord server community, most notably Jack McKalling for input on how the script should work, especially formatting and what information should be there.

#### Translators #### 
* MarkusRost – German translation
* JSBM – French translation
* [Eduaddad](https://eduardoaddad.com.br) – Brazilian Portuguese translation
* BabylonAS, Philo and Russian Minecraft Wiki community – Russian translation
* Mak_and_Iv – Ukrainian translation
* Tamara Carvallo – Spanish translation
* Lakejason0 - Simplified Chinese translation

Thank you!

[![Translation status](https://translate.wikibot.de/widgets/rcgcdw/-/multi-auto.svg)](https://translate.wikibot.de/engage/rcgcdw/?utm_source=widget)

### Extensions/compatible programs ###
* [Wiki Utilities](https://github.com/Sidemen19/Wiki-Utilities) – an integration that allows wiki administrators to revert edits, block editors, and delete pages on the wiki by reacting to messages created by RcGcDw/RcGcDb. Author: [Sidemen19](https://github.com/Sidemen19)

### Alternatives ###
There are various alternatives to RcGcDw you may want to consider if for some reason RcGcDw doesn't satisfy your needs:
* [Wiki-Bot](https://wiki.wikibot.de/wiki/Wiki-Bot_Wiki) - while it's not exactly an alternative since Wiki-Bot is running a modified version of RcGcDw in the backend, you can use its rcscript feature to add a webhook for your wiki and have it work similarly to how RcGcDw does without hosting anything on your own,
* [Extension:Discord](https://www.mediawiki.org/wiki/Extension:Discord) - MediaWiki extension to do the same thing,
* [Extension:DiscordNotifications](https://www.mediawiki.org/wiki/Extension:DiscordNotifications) - another MediaWiki extension with the same goal.

### Wiki ###
For more information, check the [wiki](https://gitlab.com/piotrex43/RcGcDw/wikis/Home)! 