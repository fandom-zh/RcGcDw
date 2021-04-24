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

import src.rcgcdw
import src.rc
import src.misc


class Client:
	"""
		A client for interacting with RcGcDw when creating formatters or hooks.
	"""
	def __init__(self):
		self._formatters = src.rcgcdw.formatter_hooks
		self.__recent_changes = src.rc.recent_changes
		self.WIKI_API_PATH = src.misc.WIKI_API_PATH
		self.WIKI_ARTICLE_PATH = src.misc.WIKI_ARTICLE_PATH
		self.WIKI_SCRIPT_PATH = src.misc.WIKI_SCRIPT_PATH
		self.WIKI_JUST_DOMAIN = src.misc.WIKI_JUST_DOMAIN
		self.content_parser = src.misc.ContentParser

	def refresh_internal_data(self):
		"""Refreshes internal storage data for wiki tags and MediaWiki messages."""
		self.__recent_changes.init_info()





client = Client()