## About
This is a specification for RcGcDw API extending formatters and allowing to add additional pre and post processing hooks for message contents.  
This document assumes you have at least a basic understanding of Python, concept of classes, objects and decorators. 

### Pre-processing hook
A class allowing to change the raw event values obtained for a change via query.recentchanges endpoint on the wiki and/or execute additional actions each time given event gets read. This type of hook executes before a formatter.

### Formatters
Formatters allow specifying how does a Discord message look like depending on message mode (embed, compact) and type of the event that had happened on the wiki (new, edit etc).
If formatter for given event is not registered, the script will look for formatter for event "generic" and if this is also not found it will throw a warning.

### Post-processing hook
A class allowing to change the message content and/or execute additional actions after message has been processed by the formatter. This type of hook executes after a formatter.

## File structure
Directory with extensions is specified by setting `extensions_dir` in settings.json.    
The directory with hooks and formatters needs to be below root directory (directory in which start.py is located) and every directory inside it needs to be a Python package importing its child packages and modules.

.  
├── extensions   
│   ├── base   
│   │   ├── abusefilter.py  
│   │   ├── my_formatters.py  
│   │   ├── \_\_init\_\_.py  
│   ├── hooks  
│   │   ├── my_hooks.py  
│   │   ├── \_\_init\_\_.py  
│   ├── \_\_init\_\_.py  
├── start.py  

## API
api object exposes various data which allows to extend the usefulness of what can be then sent to Discord. It also contains
common functions that can be used to interact with the script and the wiki.

### Formatter
**Path**: `src.api.formatter`  
_Formatter module implements two decorators: `embed` and `compact`. Both of them can take the following keyword arguments:_
- `event` - string - event type for formatter, in case the event is a [log event](https://www.mediawiki.org/wiki/Manual:Log_actions) it's constructed by taking log_type and combining it with log_action with / character in between (for example `upload/overwrite`). If the event however is not a log event but action like edit, the type will consist only of `type` value.
- `aliases` - list[str] - list of strings containing all the events given event should alias for, it helps in case you want the same function be used for multiple event types.

Both `event` and `aliases` arguments are optional in formatters. However, every formatter needs to have some kind of event specified. If it's not specified in the decorator, a fallback method will be used which constructs event type in format `{func.__module__}/{func.__name__.split("_", 1)[1]}`, in other terms taking the name of the file in which formatter is defined as first part and entire function name after first _ character as second part. Note that this fallback works only for log events.
There are also additional, made up event types that are special cases, they are listed below:  
- `abuselog` – reserved for AbuseFilter filter logs
- `discussion/{post_type.lower()}` – reserved for Fandom's Discussion/Feeds integration
- `suppressed` – reserved for logs that were [suppressed](https://www.mediawiki.org/wiki/Special:MyLanguage/Help:RevisionDelete) and cannot be read by the script

Formatter decorator registers a Python function and calls it each time a specific event is being processed from the wiki. Function is then called with Context and change arguments where context is [Context object](#Context) and change is a dict object containing the body of a change.  
Every formatter **must** return a DiscordMessage object.

#### Usage

```python
from src.discord.message import DiscordMessage
from src.api import formatter
from src.i18n import formatters_i18n
from src.api.context import Context
from src.api.util import embed_helper, compact_author, create_article_path, sanitize_to_markdown, sanitize_to_url, \
    clean_link

#  Setup translation function which is used to translate english strings to other languages
_ = formatters_i18n.gettext

#  Call a decorator and register embed_sprite_sprite function for all sprite/sprite events 
@formatter.embed(event="sprite/sprite")
def embed_sprite_sprite(ctx: Context, change: dict) -> DiscordMessage:
    #  Create DiscordMessage object which constructs Discord embed content
    embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
    #  embed_helper function can be used to automatically populate DiscordMessage object with some common useful information such as setting author name/url, adding fields for tags/categories, or setting default description
    embed_helper(ctx, embed, change)
    embed["url"] = create_article_path(sanitize_to_url(change["title"]))
    embed["title"] = _("Edited the sprite for {article}").format(article=sanitize_to_markdown(change["title"]))
    #  return populated DiscordMessage object
    return embed


@formatter.compact(event="sprite/sprite")
def compact_sprite_sprite(ctx: Context, change: dict) -> DiscordMessage:
    author, author_url = compact_author(ctx, change)
    link = clean_link(create_article_path(sanitize_to_url(change["title"])))
    content = _("[{author}]({author_url}) edited the sprite for [{article}]({article_url})").format(author=author,
                                                                                                    author_url=author_url,
                                                                                                    article=sanitize_to_markdown(change[
                                                                                                        "title"]),
                                                                                                    article_url=link)
    return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)
```

### Client
**Path**: `src.api.client.Client`    
_Client is a class containing most of usable methods and communication layer with the core functionality._    
Client consists of the following fields:    
- `WIKI_API_PATH` - string - URL path leading to API (`WIKI_DOMAIN/api.php`)
- `WIKI_ARTICLE_PATH` - string - URL path leading to article path (`WIKI_DOMAIN/articlepath`)
- `WIKI_SCRIPT_PATH` - string - URL path leading to script path of the wiki (`WIKI_DOMAIN/`)
- `WIKI_JUST_DOMAIN` - string - URL path leading just to the wiki domain (`WIKI_DOMAIN`)
- `content_parser` - class - a reference to HTMLParser implementation that parses edit diffs
- `tags` - dict - a container storing all [tags](https://www.mediawiki.org/wiki/Manual:Tags) the wiki has configured
- `namespaces` - dict - a dictionary of [namespaces](https://www.mediawiki.org/wiki/Manual:Namespace) on the wiki
- `LinkParser` - class - a class of LinkParser which is usually used to parse parsed_comment from events including turning URLs into Markdown links    
Client consists of the following methods:
- `refresh_internal_data()` - requests namespaces, tags and MediaWiki messages to be retrieved and updated in internal storage
- `parse_links(text: str)` - parses links using LinkParser object
- `pull_curseprofile_comment(comment_id: Union[str, int])` - allows retrieving CurseProfile comment from wikis originated from Gamepedia
- `make_api_request(params: Union[str, OrderedDict], *json_path: str, timeout: int = 10, allow_redirects: bool = False)` - allows to make a request to the wiki with parameters specified in params argument, json_path additionally allows to provide a list of strings that will be iterated over and json path of the result of this iteration returned. Timeout in float (seconds) can be added to limit the time for response, allow_redirects can be set to disallow or allow redirects
- `get_formatters()` - returns a dictionary of all formatters in format of `{'eventtype': func}`
- `get_ipmapper()` - returns ip mapper which tracks edit counts of IP editors
- `schedule(function: Callable, *args, every: float, at: str, priority=5, **kwargs)` – schedules a periodic task that executes *function*. Either every or at should be defined. *every* is float amount of seconds every which tasks should be ran, *at* should be HH:MM formatted time at which task should be ran. Function returns sched event, but only for first execution.

### Context
**Path**: `src.api.context.Context`    
_Context is a class which objects of are only used as first argument of formatter definitions._   
Context can consist of the following fields:
- `client` - [Client](#Client) object
- `webhook_url` - string - webhook url for given formatter
- `message_type` - string - can be either `embed` or `compact`
- `feed_type` - string - type of the feed, can be either `recentchanges`, `abuselog` or `discussion`
- `event` - string - action called, should be the same as formatter event action
- `categories` - {"new": set(), "removed": set()} - each set containing strings of added or removed categories for given page
- `parsedcomment` - string - contains escaped and Markdown parsed summary (parsed_comment) of a log/edit action 
- `comment_page` - dict - containing `fullUrl` and `article` with strings both to full article url and its name

### Util
**Path**: `src.api.util`
_Util is a module with a few common functions that can be useful for generating Discord messages, parsing changes in formatting and more._    
Util provides the following functionalities:
- `clean_link(link: str)` – returns a string wrapped with <> brackets, so the link given as a string doesn't embed in Discord
- `sanitize_to_markdown(text: str)` – returns a string with Discord Markdown characters escaped
- `sanitize_to_url(text: str)` – returns a string that should be safe to be part of URL with special characters either escaped or encoded
- `parse_mediawiki_changes(ctx: Context, content: str, embed: DiscordMessage)` – populates embed with two new fields "Added" and "Removed" containing diff of changes within content argument retrieved using action=compare request between two revisions
- `create_article_path(article: str)` – returns a string with URL leading to an article page (basically taking into account wiki's article path)
- `compact_author(ctx: Context, content: dict)` – returns two strings - first containing the name of the author with hide_ips setting taken into account and second a URL leading to author's contribution page, this makes it easier for compact formatters to include author detail in messages
- `embed_helper(ctx: Context, message: DiscordMessage, change: dict, set_user=True, set_edit_meta=True, set_desc=True)` – a function populating the message (Discord embed message) with most essential fields accordingly. Populating includes the following fields: author, author_url, category and tags fields, description

### DiscordMessage
**Path**: `src.discord.message.DiscordMessage`
_DiscordMessage is a class taking care of creation of Discord messages that can be sent via send_to_discord function later on._   
DiscordMessage object when created with message_type == embed will take all assignments and reads using object[key] as ones reading/setting the actual embed object.   
DiscordMessage consists of the following:   
- `__init__(message_type: str, event_type: str, webhook_url: str, content=None)` – constructor which takes message type (can be either `embed` or `compact`), event_type (for example `protect/protect`), webhook_url (full URL of webhook message is intended to be sent to), content optional parameter used in compact messages as main body
- `set_author(name, url, icon_url="")` – a method that can be used to set username, URL to their profile and optionally an icon for the embed
- `add_field(name, value, inline=False)` – a method to add a field with given name and value, optional inline argument can be set if field should be inline
- `set_avatar(url)` – sets avatar for WEBHOOK MESSAGE (not to be confused with actual embed)
- `set_name(name)` – sets name for WEBHOOK MESSAGE
- `set_link(link)` – equivalent to object["link"] = link for embed messages

### Language support
RcGcDw implements i18n with gettext and already exposes Translations instance with its `src.i18` module. formatters_i18n variable is used for instance of all formatters inside base directory. 

### Pre/post hooks
**Path**: `src.api.hook`    
There are two decorator functions available in the module: `pre_hook` and `post_hook`. They don't take arguments and simply register the function as a hook.
Pre-hook functions take the following arguments: `context` ([Context object](#Context)) and `change` (dict object with change).
Post-hook functions take the following arguments: `message` ([Discord message object](#DiscordMessage)), `metadata` ([Discord message metadata](#DiscordMessageMetadata)), `context` ([Context object](#Context)) and `change` (dictionary of main change body)
