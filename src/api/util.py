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
from __future__ import annotations
import re
from urllib.parse import quote
from typing import Optional, Callable, TYPE_CHECKING

from src.exceptions import ServerError, MediaWikiError
from src.discord.message import DiscordMessage
from src.configloader import settings
import src.misc
import logging
from src.i18n import formatters_i18n

_ = formatters_i18n.gettext

if TYPE_CHECKING:
	from src.api.context import Context

logger = logging.getLogger("src.api.util")


def default_message(event: str, formatter_hooks: dict) -> Callable:
	"""Returns a method of a formatter responsible for the event or None if such does not exist."""
	return formatter_hooks.get(event, formatter_hooks.get("generic", formatter_hooks["no_formatter"]))


def clean_link(link: str) -> str:
	"""Adds <> around the link to prevent its embedding"""
	return "<" + link.replace(" ", "_") + ">"


def sanitize_to_markdown(text: str) -> str:
	"""Sanitizes given text to escape markdown formatting. It is used in values that will be visible on Discord in messages"""
	return re.sub(r"([`_*~:<>{}@|\\])", "\\\\\\1", text).replace('//', "/\\/").replace('](', "]\\(")


def sanitize_to_url(text: str) -> str:  # TODO ) replaces needed?
	"""Formats a string in a way where it can be safely added to a URL without breaking MediaWiki URL schema"""
	return quote(text, " /:").replace(' ', "_").replace(")", "%29")


def parse_mediawiki_changes(ctx: Context, content: str, embed: DiscordMessage) -> None:
	"""Parses MediaWiki changes and adds them to embed as fields "Added" and "Removed" """
	edit_diff = ctx.client.content_parser()
	edit_diff.feed(content)
	if edit_diff.small_prev_del:
		if edit_diff.small_prev_del.replace("~~", "").replace("__", "").isspace():
			edit_diff.small_prev_del = _('__Only whitespace__')
		else:
			edit_diff.small_prev_del = edit_diff.small_prev_del.replace("~~~~", "").replace("____", "")
	if edit_diff.small_prev_ins:
		if edit_diff.small_prev_ins.replace("**", "").replace("__", "").isspace():
			edit_diff.small_prev_ins = _('__Only whitespace__')
		else:
			edit_diff.small_prev_ins = edit_diff.small_prev_ins.replace("****", "").replace("____", "")
	logger.debug("Changed content: {}".format(edit_diff.small_prev_ins))
	if edit_diff.small_prev_del and not ctx.event == "new":
		embed.add_field(_("Removed"), "{data}".format(data=edit_diff.small_prev_del), inline=True)
	if edit_diff.small_prev_ins:
		embed.add_field(_("Added"), "{data}".format(data=edit_diff.small_prev_ins), inline=True)


def create_article_path(article: str) -> str:
	"""Takes the string and creates an URL with it as the article name"""
	return src.misc.WIKI_ARTICLE_PATH.replace("$1", article)


def compact_summary(ctx: Context) -> str:
	"""Creates a comment for compact formatters"""
	if ctx.parsedcomment:
		return " *({})*".format(ctx.parsedcomment)
	return ""

def compact_author(ctx: Context, change: dict) -> (Optional[str], Optional[str]):
	"""Returns link to the author and the author itself respecting the settings"""
	author, author_url = None, None
	if ctx.event != "suppressed":
		author_url = clean_link(create_article_path("User:{user}".format(user=sanitize_to_url(change["user"]))))
		if "anon" in change:
			if settings.get("hide_ips", False):
				author = _("Unregistered user")
			else:
				author = change["user"]
		else:
			author = change["user"]
	return author, author_url


def embed_helper(ctx: Context, message: DiscordMessage, change: dict, set_user=True, set_edit_meta=True, set_desc=True) -> None:
	"""Helps in preparing common edit/log fields for events. Passed arguments automatically become saturated with needed data.
	All automatic setups can be disabled by setting relevant variable to False

	Currently handles:
	setting usernames (handles according to settings, specific options set in the settings: hide_ips)
	adding category fields (if there are any specified categories in the edit)
	adding tags (if the log is tagged anyhow)
	setting default description (to ctx.parsedcomment)"""
	if set_user:
		author = None
		if "anon" in change:
			author_url = create_article_path("Special:Contributions/{user}".format(user=sanitize_to_url(change["user"])))
			ip_mapper = ctx.client.get_ipmapper()
			logger.debug("current user: {} with cache of IPs: {}".format(change["user"], ip_mapper.keys()))
			if change["user"] not in list(ip_mapper.keys()):
				try:
					contibs = ctx.client.make_api_request(
						"?action=query&format=json&list=usercontribs&uclimit=max&ucuser={user}&ucstart={timestamp}&ucprop=".format(
							user=sanitize_to_url(change["user"]), timestamp=change["timestamp"]), "query",
						"usercontribs")
				except (ServerError, MediaWikiError):
					logger.warning("WARNING: Something went wrong when checking amount of contributions for given IP address")
					if settings.get("hide_ips", False):
						author = _("Unregistered user")
					else:
						author = change["user"] + "(?)"
				else:
					ip_mapper[change["user"]] = len(contibs)
					logger.debug("Current params user {} and state of map_ips {}".format(change["user"], ip_mapper))
					if settings.get("hide_ips", False):
						author = _("Unregistered user")
					else:
						author = "{author} ({contribs})".format(author=change["user"], contribs=len(contibs))
			else:
				logger.debug("Current params user {} and state of map_ips {}".format(change["user"], ip_mapper))
				if ctx.event in ("edit", "new"):
					ip_mapper[change["user"]] += 1
				author = "{author} ({amount})".format(
					author=change["user"] if settings.get("hide_ips", False) is False else _("Unregistered user"),
					amount=ip_mapper[change["user"]])
		else:
			author_url = create_article_path("User:{}".format(sanitize_to_url(change["user"])))
			author = change["user"]
		message.set_author(author, author_url)
	if set_edit_meta:
		if settings["appearance"]["embed"]["show_footer"]:
			message["timestamp"] = change["timestamp"]
		if "tags" in change and change["tags"]:
			tag_displayname = []
			for tag in change["tags"]:
				if tag in ctx.client.tags:
					if ctx.client.tags[tag] is None:
						continue  # Ignore hidden tags
					else:
						tag_displayname.append(ctx.client.tags[tag])
				else:
					tag_displayname.append(tag)
			if tag_displayname:
				message.add_field(formatters_i18n.pgettext("recent changes Tags", "Tags"), ", ".join(tag_displayname))
		if ctx.categories is not None and not (len(ctx.categories["new"]) == 0 and len(ctx.categories["removed"]) == 0):
			new_cat = (_("**Added**: ") + ", ".join(list(ctx.categories["new"])[0:16]) + (
				"\n" if len(ctx.categories["new"]) <= 15 else _(" and {} more\n").format(
					len(ctx.categories["new"]) - 15))) if ctx.categories["new"] else ""
			del_cat = (_("**Removed**: ") + ", ".join(list(ctx.categories["removed"])[0:16]) + (
				"" if len(ctx.categories["removed"]) <= 15 else _(" and {} more").format(
					len(ctx.categories["removed"]) - 15))) if ctx.categories["removed"] else ""
			message.add_field(_("Changed categories"), new_cat + del_cat)
	if set_desc:
		message["description"] = ctx.parsedcomment
