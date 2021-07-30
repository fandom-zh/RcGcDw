#  This file is part of Recent changes Goat compatible Discord webhook (RcGcDw).
#
#  RcGcDw is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  RcGcDw is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with RcGcDw.  If not, see <http://www.gnu.org/licenses/>.

import ipaddress
import logging
from src.discord.message import DiscordMessage
from src.api import formatter
from src.i18n import formatters_i18n
from src.api.context import Context
from src.api.util import embed_helper, sanitize_to_url, parse_mediawiki_changes, clean_link, compact_author, \
	create_article_path, sanitize_to_markdown
from src.configloader import settings

_ = formatters_i18n.gettext
ngettext = formatters_i18n.ngettext

abusefilter_results = {"": _("None"), "warn": _("Warning issued"), "block": _("**Blocked user**"), "tag": _("Tagged the edit"), "disallow": _("Disallowed the action"), "rangeblock": _("**IP range blocked**"), "throttle": _("Throttled actions"), "blockautopromote": _("Removed autoconfirmed group"), "degroup": _("**Removed from privileged groups**")}
abusefilter_actions = {"edit": _("Edit"), "upload": _("Upload"), "move": _("Move"), "stashupload": _("Stash upload"), "delete": _("Deletion"), "createaccount": _("Account creation"), "autocreateaccount": _("Auto account creation")}

logger = logging.getLogger("extensions.base")

# AbuseFilter - https://www.mediawiki.org/wiki/Special:MyLanguage/Extension:AbuseFilter
# Processing Abuselog LOG events, separate from RC logs

def abuse_filter_format_user(change):
	author = change["user"]
	if settings.get("hide_ips", False):
		try:
			ipaddress.ip_address(change["user"])
		except ValueError:
			pass
		else:
			author = _("Unregistered user")
	return author


@formatter.embed(event="abuselog")
def embed_abuselog(ctx: Context, change: dict):
	action = "abuselog/{}".format(change["result"])
	embed = DiscordMessage(ctx.message_type, action, ctx.webhook_url)
	author = abuse_filter_format_user(change)
	embed["title"] = _("{user} triggered \"{abuse_filter}\"").format(user=author, abuse_filter=sanitize_to_markdown(change["filter"]))
	embed.add_field(_("Performed"), abusefilter_actions.get(change["action"], _("Unknown")))
	embed.add_field(_("Action taken"), abusefilter_results.get(change["result"], _("Unknown")))
	embed.add_field(_("Title"), sanitize_to_markdown(change.get("title", _("Unknown"))))
	return embed


@formatter.compact(event="abuselog")
def compact_abuselog(ctx: Context, change: dict):
	action = "abuselog/{}".format(change["result"])
	author_url = clean_link(create_article_path("User:{user}".format(user=change["user"])))
	author = abuse_filter_format_user(change)
	message = _("[{author}]({author_url}) triggered *{abuse_filter}*, performing the action \"{action}\" on *[{target}]({target_url})* - action taken: {result}.").format(
		author=author, author_url=author_url, abuse_filter=sanitize_to_markdown(change["filter"]),
		action=abusefilter_actions.get(change["action"], _("Unknown")), target=change.get("title", _("Unknown")),
		target_url=clean_link(create_article_path(sanitize_to_url(change.get("title", _("Unknown"))))),
		result=abusefilter_results.get(change["result"], _("Unknown")))
	return DiscordMessage(ctx.message_type, action, ctx.webhook_url, content=message)

# abusefilter/modify - AbuseFilter filter modification


@formatter.embed(event="abusefilter/modify")
def embed_abuselog_modify(ctx: Context, change: dict):
	embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
	embed_helper(ctx, embed, change)
	embed["url"] = create_article_path(
		"Special:AbuseFilter/history/{number}/diff/prev/{historyid}".format(number=change["logparams"]['newId'],
																			historyid=change["logparams"]["historyId"]))
	embed["title"] = _("Edited abuse filter number {number}").format(number=change["logparams"]['newId'])
	return embed


@formatter.compact(event="abusefilter/modify")
def compact_abuselog_modify(ctx: Context, change: dict):
	author, author_url = compact_author(ctx, change)
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
	return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)

# abusefilter/create - AbuseFilter filter creation


@formatter.embed(event="abusefilter/create")
def embed_abuselog_create(ctx: Context, change: dict):
	embed = DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url)
	embed_helper(ctx, embed, change)
	embed["url"] = create_article_path("Special:AbuseFilter/{number}".format(number=change["logparams"]['newId']))
	embed["title"] = _("Created abuse filter number {number}").format(number=change["logparams"]['newId'])
	return embed

@formatter.compact(event="abusefilter/create")
def compact_abuselog_create(ctx: Context, change: dict):
	author, author_url = compact_author(ctx, change)
	link = clean_link(
		create_article_path("Special:AbuseFilter/{number}".format(number=change["logparams"]['newId'])))
	content = _("[{author}]({author_url}) created abuse filter [number {number}]({filter_url})").format(author=author,
																										author_url=author_url,
																										number=change[
																											"logparams"][
																											'newId'],
																										filter_url=link)
	return DiscordMessage(ctx.message_type, ctx.event, ctx.webhook_url, content=content)
