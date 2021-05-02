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
from src.discord.message import DiscordMessage
from src.configloader import settings
import src.misc
import logging
from src.i18n import rc_formatters

_ = rc_formatters.gettext

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
	return re.sub(r"([`_*~:<>{}@|\\])", "\\\\\\1", text, 0).replace('//', "/\\/").replace('](', "]\\(")


def sanitize_to_url(text: str) -> str:  # TODO ) replaces needed?
	"""Formats a string in a way where it can be safely added to a URL without breaking MediaWiki URL schema"""
	return quote(text, " /:").replace(' ', "_").replace(")", "%29")


def parse_mediawiki_changes(ctx: Context, content: str, embed: DiscordMessage) -> None:
	"""Parses MediaWiki changes and adds them to embed as fields "Added" and "Removed" """
	edit_diff = ctx.client.content_parser()
	edit_diff.feed(content)
	if edit_diff.small_prev_del:
		if edit_diff.small_prev_del.replace("~~", "").isspace():
			edit_diff.small_prev_del = _('__Only whitespace__')
		else:
			edit_diff.small_prev_del = edit_diff.small_prev_del.replace("~~~~", "")
	if edit_diff.small_prev_ins:
		if edit_diff.small_prev_ins.replace("**", "").isspace():
			edit_diff.small_prev_ins = _('__Only whitespace__')
		else:
			edit_diff.small_prev_ins = edit_diff.small_prev_ins.replace("****", "")
	logger.debug("Changed content: {}".format(edit_diff.small_prev_ins))
	if edit_diff.small_prev_del and not ctx.event == "new":
		embed.add_field(_("Removed"), "{data}".format(data=edit_diff.small_prev_del), inline=True)
	if edit_diff.small_prev_ins:
		embed.add_field(_("Added"), "{data}".format(data=edit_diff.small_prev_ins), inline=True)


def create_article_path(article: str) -> str:
	"""Takes the string and creates an URL with it as the article name"""
	return src.misc.WIKI_ARTICLE_PATH.replace("$1", article)


def compact_author(ctx: Context, change: dict) -> (Optional[str], Optional[str]):
	"""Returns link to the author and the author itself respecting the settings"""
	author, author_url = None, None
	if ctx.event != "suppressed":
		author_url = clean_link(create_article_path("User:{user}".format(user=change["user"])))  # TODO Sanitize user in here and in embed_helper
		if "anon" in change:
			change["user"] = _("Unregistered user")
			author = change["user"]
		else:
			author = change["user"]
	return author, author_url


def embed_helper(ctx: Context, message: DiscordMessage, change: dict) -> None:
	"""Helps in preparing common edit/log fields for events. Passed arguments automatically become saturated with needed data.

	Currently handles: setting usernames"""
	# TODO Repurpose it so change['user'] stays the same
	if "anon" in change:
		author_url = create_article_path("Special:Contributions/{user}".format(
			user=change["user"].replace(" ", "_")))  # Replace here needed in case of #75
		ip_mapper = ctx.client.get_ipmapper()
		logger.debug("current user: {} with cache of IPs: {}".format(change["user"], ip_mapper.keys()))
		if change["user"] not in list(ip_mapper.keys()):
			contibs = ctx.client.make_api_request(
				"{wiki}?action=query&format=json&list=usercontribs&uclimit=max&ucuser={user}&ucstart={timestamp}&ucprop=".format(
					wiki=ctx.client.WIKI_API_PATH, user=change["user"], timestamp=change["timestamp"]), "query",
				"usercontribs")
			if contibs is None:
				logger.warning(
					"WARNING: Something went wrong when checking amount of contributions for given IP address")
				if settings.get("hide_ips", False):
					change["user"] = _("Unregistered user")
				change["user"] = change["user"] + "(?)"
			else:
				ip_mapper[change["user"]] = len(contibs)
				logger.debug(
					"Current params user {} and state of map_ips {}".format(change["user"], ip_mapper))
				if settings.get("hide_ips", False):
					change["user"] = _("Unregistered user")
				change["user"] = "{author} ({contribs})".format(author=change["user"], contribs=len(contibs))
		else:
			logger.debug(
				"Current params user {} and state of map_ips {}".format(change["user"], ip_mapper))
			if ctx.event in ("edit", "new"):
				ip_mapper[change["user"]] += 1
			change["user"] = "{author} ({amount})".format(
				author=change["user"] if settings.get("hide_ips", False) is False else _("Unregistered user"),
				amount=ip_mapper[change["user"]])
	else:
		author_url = create_article_path("User:{}".format(change["user"].replace(" ", "_")))
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
		message.add_field(_("Tags"), ", ".join(tag_displayname))
	if ctx.categories is not None and not (len(ctx.categories["new"]) == 0 and len(ctx.categorie["removed"]) == 0):
		new_cat = (_("**Added**: ") + ", ".join(list(ctx.categories["new"])[0:16]) + ("\n" if len(ctx.categories["new"])<=15 else _(" and {} more\n").format(len(ctx.categories["new"])-15))) if ctx.categories["new"] else ""
		del_cat = (_("**Removed**: ") + ", ".join(list(ctx.categories["removed"])[0:16]) + ("" if len(ctx.categories["removed"])<=15 else _(" and {} more").format(len(ctx.categories["removed"])-15))) if ctx.categories["removed"] else ""
		message.add_field(_("Changed categories"), new_cat + del_cat)
	message.set_author(change["user"], author_url)
