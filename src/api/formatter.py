# This file is part of Recent changes Goat compatible Discord webhook (RcGcDw).

# RcGcDw is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# RcGcDw is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with RcGcDw.  If not, see <http://www.gnu.org/licenses/>.
import src.api.hooks
import logging
from src.configloader import settings
from src.exceptions import FormatterBreaksAPISpec
from src.discord.message import DiscordMessage
from typing import Optional, Callable

logger = logging.getLogger("src.api.formatter")


def _register_formatter(func, kwargs, formatter_type: str, action_type=None):
	"""
	Registers a formatter inside of src.rcgcdw.formatter_hooks
	"""
	try:
		_, action = func.__name__.split("_", 1)
		etype = func.__module__
		action_type = f"{etype}/{action}"
	except ValueError:
		raise
	action_type = kwargs.get("event", action_type)
	if action_type is None:
		raise FormatterBreaksAPISpec("event type")
	if settings["appearance"]["mode"] == formatter_type:
		for act in [action_type] + kwargs.get("aliases", []):  # Make action_type string a list and merge with aliases
			if act in src.api.hooks.formatter_hooks:
				logger.warning(f"Action {act} is already defined inside of "
				               f"{src.api.hooks.formatter_hooks[act].__module__}! "
				               f"Overwriting it with one from {func.__module__}")
			src.api.hooks.formatter_hooks[act] = func


def embed(**kwargs):
	"""
	Decorator to register a formatter are return a function

	:key event: Event string
	:key mode: Discord Message mode
	:key aliases: Allows to register multiple events under same function
	:return:
	"""

	def decorator_cont(func: Callable[[dict], DiscordMessage]):
		_register_formatter(func, kwargs, "embed")
		return func

	return decorator_cont


def compact(**kwargs):
	"""
	Decorator to register a formatter are return a function

	:key event: Event string
	:key mode: Discord Message mode
	:key aliases: Allows to register multiple events under same function
	:return:
	"""

	def decorator_cont(func: Callable[[dict], DiscordMessage]):
		_register_formatter(func, kwargs, "compact")
		return func

	return decorator_cont
