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

if TYPE_CHECKING:
	from src.api.context import Context

logger = logging.getLogger("src.api.util")

def default_message(event: str, formatter_hooks: dict) -> Callable:
	"""Returns a method of a formatter responsible for the event or None if such does not exist."""
	return formatter_hooks.get(event, formatter_hooks.get("generic", formatter_hooks["no_formatter"]))


def link_formatter(link: str) -> str:
	"""Formats a link to not embed it"""
	return "<" + quote(link.replace(" ", "_"), "/:?=&") + ">"


def escape_formatting(data: str) -> str:
	"""Escape Discord formatting"""
	return re.sub(r"([`_*~<>{}@/|\\])", "\\\\\\1", data, 0)


def create_article_path(article: str) -> str:
	"""Takes the string and creates an URL with it as the article name"""
	return src.misc.WIKI_ARTICLE_PATH.replace("$1", article)


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
	message.set_author(change["user"], author_url)
