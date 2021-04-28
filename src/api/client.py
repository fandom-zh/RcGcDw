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
import src.misc
from typing import Union
from collections import OrderedDict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
	from src.wiki import Wiki


class Client:
	"""
		A client for interacting with RcGcDw when creating formatters or hooks.
	"""
	def __init__(self, hooks, wiki):
		self._formatters = hooks
		self.__recent_changes: Wiki = wiki
		self.WIKI_API_PATH = src.misc.WIKI_API_PATH
		self.WIKI_ARTICLE_PATH = src.misc.WIKI_ARTICLE_PATH
		self.WIKI_SCRIPT_PATH = src.misc.WIKI_SCRIPT_PATH
		self.WIKI_JUST_DOMAIN = src.misc.WIKI_JUST_DOMAIN
		self.content_parser = src.misc.ContentParser
		self.tags = self.__recent_changes.tags
		#self.make_api_request: src.rc.wiki.__recent_changes.api_request = self.__recent_changes.api_request

	def refresh_internal_data(self):
		"""Refreshes internal storage data for wiki tags and MediaWiki messages."""
		self.__recent_changes.init_info()

	def make_api_request(self, params: Union[str, OrderedDict], *json_path: str, timeout: int = 10, allow_redirects: bool = False):
		"""Method to GET request data from the wiki's API with error handling including recognition of MediaWiki errors.

				Parameters:

					params (str, OrderedDict): a string or collections.OrderedDict object containing query parameters
					json_path (str): *args taking strings as values. After request is parsed as json it will extract data from given json path
					timeout (int, float) (default=10): int or float limiting time required for receiving a full response from a server before returning TimeoutError
					allow_redirects (bool) (default=False): switches whether the request should follow redirects or not

				Returns:

					request_content (dict): a dict resulting from json extraction of HTTP GET request with given json_path
					OR
					One of the following exceptions:
					ServerError: When connection with the wiki failed due to server error
					ClientError: When connection with the wiki failed due to client error
					KeyError: When json_path contained keys that weren't found in response JSON response
					BadRequest: When params argument is of wrong type
					MediaWikiError: When MediaWiki returns an error
				"""
		return self.__recent_changes.api_request(params, *json_path, timeout=timeout, allow_redirects=allow_redirects)

	def get_formatters(self):
		return self._formatters


	def get_ipmapper(self) -> dict:
		"""Returns a dict mapping IPs with amount of their edits"""
		return self.__recent_changes.map_ips