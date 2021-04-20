## About
This is a specification for RcGcDw API extending formatters and allowing to add additional pre and post processing hooks for message contents.

### Pre-processing hook
A class allowing to change the message content and/or execute additional actions each time given event gets read. This type of hook executes before a formatter.

### Formatters
Formatters allow to specify how does a Discord message look like depending on message mode (embed, compact) and type of the event that had happened on the wiki (new, edit etc).

### Post-processing hook
A class allowing to change the message content and/or execute additional actions after message has been processed by the formatter. This type of hook executes after a formatter.

## File structure
Directory with extensions should be possible to be changed using settings.json
/
 /src
 /extensions
 /extensions/base
 /extensions/abusefilter
  /extensions/abusefilter/abusefilter.py
 /extensions/managewiki
  /extensions/managewiki/managewiki.py
 /extensions/prehooks/
  /extensions/prehooks/friskyhooks.py
 /extensions/posthooks/

## API
api object exposes various data which allows to extend the usefulness of what can be then sent to Discord.



## Example formatter
```python

import logging
from src.discord.message import DiscordMessage
from src.api import formatter
from src.i18n import rc_formatters

_ = rc_formatters.gettext

logger = logging.getLogger("extensions.abusefilter")

class abusefilter(Formatter):
	def __init__(self, api):
		super().__init__(api)
		
    @formatter.embed(event="abuselog/modify", mode="embed")
	def embed_modify(self, change: dict) -> DiscordMessage:
		return DiscordMessage
		
    @formatter.compact(event="abuselog/modify")
	def compact_modify(self, change: dict) -> DiscordMessage:
		return DiscordMessage

```

## Example hook
```python

logger = logging.getLogger("extensions.abusefilter")

class test1(Hook):
	def __init__(self, api):
		self.api = api
		
	def embed_modify(self, base_msg: DiscordMessage, change: dict) -> DiscordMessage:
		return DiscordMessage
		
	def compact_modify(self, base_msg: DiscordMessage, change: dict) -> DiscordMessage:
		return DiscordMessage

```