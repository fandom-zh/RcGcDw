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
import re
from urllib.parse import quote
from typing import Optional, Callable
from src.discord.message import DiscordMessage
from src.configloader import settings
import src.misc


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