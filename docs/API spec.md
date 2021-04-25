## About
This is a specification for RcGcDw API extending formatters and allowing to add additional pre and post processing hooks for message contents.

### Pre-processing hook
A class allowing to change the message content and/or execute additional actions each time given event gets read. This type of hook executes before a formatter.

### Formatters
Formatters allow to specify how does a Discord message look like depending on message mode (embed, compact) and type of the event that had happened on the wiki (new, edit etc).
If formatter for given event is not registered, the script will look for formatter for event "generic" and if this is also not found it will throw a wartning.

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
from src.api.context import Context
from src.api.util import create_article_path, link_formatter
from src.i18n import rc_formatters

_ = rc_formatters.gettext

logger = logging.getLogger("extensions.abusefilter")

class abusefilter():
  def __init__(self, api):
    super().__init__(api)
		
  @formatter.embed(event="abuselog/modify", mode="embed")
  def embed_modify(self, ctx: Context, change: dict) -> DiscordMessage:
    embed = DiscordMessage(ctx.message_type, ctx.event, webhook_url=ctx.webhook_url)
    embed.set_link(create_article_path("Special:AbuseFilter/history/{number}/diff/prev/{historyid}".format(number=change["logparams"]['newId'], historyid=change["logparams"]["historyId"])))
    embed["title"] = _("Edited abuse filter number {number}").format(number=change["logparams"]['newId'])
    return embed
		
  @formatter.compact(event="abuselog/modify")
  def embed_modify(self, ctx: Context, change: dict) -> DiscordMessage:
    link = link_formatter(create_article_path("Special:AbuseFilter/history/{number}/diff/prev/{historyid}".format(number=change["logparams"]['newId'], historyid=change["logparams"]["historyId"])))
    content = _("[{author}]({author_url}) edited abuse filter [number {number}]({filter_url})").format(author=author, author_url=author_url, number=change["logparams"]['newId'], filter_url=link)
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