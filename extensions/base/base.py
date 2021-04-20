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

import logging
from src.discord.message import DiscordMessage
from src.api import formatter
from src.i18n import rc_formatters

_ = rc_formatters.gettext

logger = logging.getLogger("extensions.base")


class abusefilter():
	def __init__(self, api):
		super().__init__(api)

	@formatter.embed(event="edit", mode="embed")
	def embed_edit(self, change: dict) -> DiscordMessage:
		return DiscordMessage()

	@formatter.compact(event="edit", mode="embed")
	def compact_edit(self, change: dict):
		return DiscordMessage()