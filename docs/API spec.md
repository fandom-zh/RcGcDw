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
api object exposes various data which allows to extend the usefulness of what can be then sent to Discord. It also contains
common functions that can be used to interact with the script and the wiki.

### Client
**Path**: `src.api.client.Client`    
_Client is a class containing most of usable methods and communication layer with the core functionality._    
Client consists of the following fields:    
- WIKI_API_PATH - string - URL path leading to API (`WIKI_DOMAIN/api.php`)
- WIKI_ARTICLE_PATH - string - URL path leading to article path (`WIKI_DOMAIN/articlepath`)
- WIKI_SCRIPT_PATH - string - URL path leading to script path of the wiki (`WIKI_DOMAIN/`)
- WIKI_JUST_DOMAIN - string - URL path leading just to the wiki domain (`WIKI_DOMAIN`)
- content_parser - class - a reference to HTMLParser implementation that parses edit diffs
- tags - dict - a container storing all [tags](https://www.mediawiki.org/wiki/Manual:Tags) the wiki has configured
- namespaces - dict - a dictionary of [namespaces](https://www.mediawiki.org/wiki/Manual:Namespace) on the wiki
- LinkParser - class - a class of LinkParser which is usually used to parse parsed_comment from events including turning URLs into Markdown links    
Client consists of the following methods:
- refresh_internal_data() - requests namespaces, tags and MediaWiki messages to be retrieved and updated in internal storage
- parse_links(text: str) - parses links using LinkParser object
- pull_curseprofile_comment(comment_id: Union[str, int]) - allows to retrieve CurseProfile comment from wikis originated from Gamepedia
- make_api_request(params: Union[str, OrderedDict], *json_path: str, timeout: int = 10, allow_redirects: bool = False) - allows to make a request to the wiki with parameters specified in params argument, json_path additionally allows to provide a list of strings that will be iterated over and json path of the result of this iteration returned. Timeout in float (seconds) can be added to limit the time for response, allow_redirects can be set to disallow or allow redirects
- get_formatters() - returns a dictionary of all formatters in format of `{'eventtype': func}`
- get_ipmapper() - returns ip mapper which tracks edit counts of IP editors

### Context
**Path**: `src.api.context.Context`    
_Context is a class which objects of are only used as first argument of formatter definitions._   
Context can consist of the following fields:
- client - Client object
- webhook_url - string - webhook url for given formatter
- message_type - string - can be either `embed` or `compact`
- categories - {"new": set(), "removed": set()} - each set containing strings of added or removed categories for given page
- parsedcomment - string - contains escaped and Markdown parsed summary (parsed_comment) of a log/edit action 
- event - string - action called, should be the same as formatter event action
- comment_page - dict - containing `fullUrl` and `article` with strings both to full article url and its name

### Language support



### Formatter event types
Formatters can be added based on their "event type". Event type is determined by `type` property for events in Recent Changes MediaWiki API. However in case of log events this becomes not enough and log events are chosen by "logtype/logaction" combination (for example `upload/overwrite`).
There are also additional made up cases like a single event type of "abuselog" for all abuselog related events and "discussion/discussiontype" for Fandom's Discussion technology integration.


## Example formatter

```python

import logging
from src.discord.message import DiscordMessage
from src.api import formatter
from src.api.context import Context
from src.api.util import create_article_path, clean_link
from src.i18n import formatters_i18n

_ = formatters_i18n.gettext

logger = logging.getLogger("extensions.abusefilter")


@formatter.embed(event="abuselog/modify", mode="embed")
def embed_modify(ctx: Context, change: dict) -> DiscordMessage:
 embed = DiscordMessage(ctx.message_type, ctx.event, webhook_url=ctx.webhook_url)
 embed.set_link(create_article_path(
  "Special:AbuseFilter/history/{number}/diff/prev/{historyid}".format(number=change["logparams"]['newId'],
                                                                      historyid=change["logparams"][
                                                                       "historyId"])))
 embed["title"] = _("Edited abuse filter number {number}").format(number=change["logparams"]['newId'])
 return embed


@formatter.compact(event="abuselog/modify")
def embed_modify(ctx: Context, change: dict) -> DiscordMessage:
 link = clean_link(create_article_path(
  "Special:AbuseFilter/history/{number}/diff/prev/{historyid}".format(number=change["logparams"]['newId'],
                                                                      historyid=change["logparams"][
                                                                       "historyId"])))
 content = _("[{author}]({author_url}) edited abuse filter [number {number}]({filter_url})").format(author=author,
                                                                                                    author_url=author_url,
                                                                                                    number=change[
                                                                                                     "logparams"][
                                                                                                     'newId'],
                                                                                                    filter_url=link)
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

[]: https://www.mediawiki.org/wiki/Manual:Tagstags

[https://www.mediawiki.org/wiki/Manual:Namespace]: https://www.mediawiki.org/wiki/Manual:Namespace