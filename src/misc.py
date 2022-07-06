# -*- coding: utf-8 -*-

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
import base64
import json, logging, sys, re, platform
from html.parser import HTMLParser
from urllib.parse import urlparse, urlunparse
import requests

from src.configloader import settings
import src.api.util
from src.discord.message import DiscordMessage, DiscordMessageMetadata
from src.discord.queue import messagequeue, send_to_discord
from src.exceptions import MediaWikiError
from src.i18n import misc

_ = misc.gettext

# Create a custom logger

misc_logger = logging.getLogger("rcgcdw.misc")

data_template = {"rcid": None, "discussion_id": 0, "abuse_log_id": None,
                 "daily_overview": {"edits": None, "new_files": None, "admin_actions": None, "bytes_changed": None,
                                    "new_articles": None, "unique_editors": None, "day_score": None, "days_tracked": 0}}

WIKI_API_PATH: str = ""
WIKI_ARTICLE_PATH: str = ""
WIKI_SCRIPT_PATH: str = ""
WIKI_JUST_DOMAIN: str = ""

profile_fields = {"profile-location": _("Location"), "profile-aboutme": _("About me"), "profile-link-google": _("Google link"), "profile-link-facebook":_("Facebook link"), "profile-link-twitter": _("Twitter link"), "profile-link-reddit": _("Reddit link"), "profile-link-twitch": _("Twitch link"), "profile-link-psn": _("PSN link"), "profile-link-vk": _("VK link"), "profile-link-xbl": _("XBL link"), "profile-link-steam": _("Steam link"), "profile-link-discord": _("Discord handle"), "profile-link-battlenet": _("Battle.net handle")}


class DataFile:
	"""Data class which instance of is shared by multiple modules to remain consistent and do not cause too many IO operations."""
	def __init__(self):
		self.data_filename: str = settings.get("datafile_path", "data.json")
		self.data: dict = self.load_datafile()
		misc_logger.debug("Current contents of {} {}".format(self.data_filename, self.data))
		self.changed: bool = False

	def generate_datafile(self):
		"""Generate a data.json file from a template."""
		try:
			with open(self.data_filename, 'w', encoding="utf-8") as data:
				data.write(json.dumps(data_template, indent=4))
		except PermissionError:
			misc_logger.critical("Could not create a data file (no permissions). No way to store last edit.")
			sys.exit(1)

	def load_datafile(self) -> dict:
		"""Read a data.json file and return a dictionary with contents
		:rtype: dict
		"""
		try:
			with open(self.data_filename, encoding="utf-8") as data:
				return json.loads(data.read())
		except FileNotFoundError:
			self.generate_datafile()
			misc_logger.info("The data file could not be found. Generating a new one...")
			return data_template

	def save_datafile(self):
		"""Overwrites the data.json file with given dictionary"""
		if self.changed is False:  # don't cause unnecessary write operations
			return
		try:
			with open(self.data_filename, "w", encoding="utf-8") as data_file:
				data_file.write(json.dumps(self.data, indent=4))
			self.changed = False
			misc_logger.debug("Saving the database succeeded.")
		except PermissionError:
			misc_logger.critical("Could not modify a data file (no permissions). No way to store last edit.")
			sys.exit(1)
		except OSError as e:
			if settings.get("error_tolerance", 1) > 1:
				if platform.system() == "Windows":
					if "Invalid argument: '" + self.data_filename + "'" in str(e):
						misc_logger.error("Saving the data file failed due to Invalid argument exception, we've seen it "
										  "before in issue #209, if you know the reason for it happening please reopen the "
										  "issue with explanation, for now we are going to just ignore it.")  #  Reference #209
						return
			raise

	def __setitem__(self, instance, value):
		if self.data[instance] != value:
			self.data[instance] = value
			self.changed = True

	def __getitem__(self, item):
		try:
			return self.data[item]
		except KeyError:  # if such value doesn't exist, set to and return none
			self.__setitem__(item, None)
			self.save_datafile()
			return None


datafile = DataFile()


def weighted_average(value, weight, new_value):
	"""Calculates weighted average of value number with weight weight and new_value with weight 1"""
	return round(((value * weight) + new_value) / (weight + 1), 2)


def class_searcher(attribs: list) -> str:
	"""Function to return classes of given element in HTMLParser on handle_starttag

	:returns a string with all of the classes of element
	"""
	for attr in attribs:
		if attr[0] == "class":
			return attr[1]
	return ""


class ContentParser(HTMLParser):
	"""ContentPerser is an implementation of HTMLParser that parses output of action=compare&prop=diff API request
	for two MediaWiki revisions. It extracts the following:
	small_prev_ins - storing up to 1000 characters of added text
	small_prev_del - storing up to 1000 chracters of removed text
	ins_length - storing length of inserted text
	del_length - storing length of deleted text
	"""
	more = _("\n__And more__")
	current_tag = ""
	last_ins = None
	last_del = None
	empty = False
	small_prev_ins = ""
	small_prev_del = ""
	ins_length = len(more)
	del_length = len(more)

	def handle_starttag(self, tagname, attribs):
		if tagname == "ins" or tagname == "del":
			self.current_tag = tagname
		if tagname == "td":
			classes = class_searcher(attribs).split(' ')
			if "diff-addedline" in classes and self.ins_length <= 1000:
				self.current_tag = "tda"
				self.last_ins = ""
			if "diff-deletedline" in classes and self.del_length <= 1000:
				self.current_tag = "tdd"
				self.last_del = ""
			if "diff-empty" in classes:
				self.empty = True

	def handle_data(self, data):
		def escape_formatting(data: str) -> str:
			"""Escape Discord formatting"""
			return re.sub(r"([`_*~<>{}@/|\\])", "\\\\\\1", data)
		data = escape_formatting(data)
		if self.current_tag == "ins" and self.ins_length <= 1000:
			self.ins_length += len("**" + data + "**")
			if self.ins_length <= 1000:
				self.last_ins = self.last_ins + "**" + data + "**"
		if self.current_tag == "del" and self.del_length <= 1000:
			self.del_length += len("~~" + data + "~~")
			if self.del_length <= 1000:
				self.last_del = self.last_del + "~~" + data + "~~"
		if self.current_tag == "tda" and self.ins_length <= 1000:
			self.ins_length += len(data)
			if self.ins_length <= 1000:
				self.last_ins = self.last_ins + data
		if self.current_tag == "tdd" and self.del_length <= 1000:
			self.del_length += len(data)
			if self.del_length <= 1000:
				self.last_del = self.last_del + data

	def handle_endtag(self, tagname):
		if tagname == "ins":
			self.current_tag = "tda"
		elif tagname == "del":
			self.current_tag = "tdd"
		elif tagname == "td":
			self.current_tag = ""
		elif tagname == "tr":
			if self.last_ins is not None:
				self.ins_length += 1
				if self.empty and not self.last_ins.isspace():
					if "**" in self.last_ins:
						self.last_ins = self.last_ins.replace("**", "__")
					self.ins_length += 4
					self.last_ins = "**" + self.last_ins + "**"
				self.small_prev_ins = self.small_prev_ins + "\n" + self.last_ins
				if self.ins_length > 1000:
					self.small_prev_ins = self.small_prev_ins + self.more
				self.last_ins = None
			if self.last_del is not None:
				self.del_length += 1
				if self.empty and not self.last_del.isspace():
					if "~~" in self.last_del:
						self.last_del = self.last_del.replace("~~", "__")
					self.del_length += 4
					self.last_del = "~~" + self.last_del + "~~"
				self.small_prev_del = self.small_prev_del + "\n" + self.last_del
				if self.del_length > 1000:
					self.small_prev_del = self.small_prev_del + self.more
				self.last_del = None
			self.empty = False


def safe_read(request, *keys):
	if request is None:
		return None
	try:
		request = request.json()
		for item in keys:
			request = request[item]
	except KeyError:
		misc_logger.warning(
			"Failure while extracting data from request on key {key} in {change}".format(key=item, change=request))
		return None
	except ValueError:
		misc_logger.warning("Failure while extracting data from request in {change}".format(change=request))
		return None
	return request


def parse_mw_request_info(request_data: dict, url: str):
	"""A function parsing request JSON message from MediaWiki logging all warnings and raising on MediaWiki errors"""
	# any([True for k in request_data.keys() if k in ("error", "errors")])
	errors: list = request_data.get("errors", {})  # Is it ugly? I don't know tbh
	if errors:
		raise MediaWikiError(str(errors))
	warnings: list = request_data.get("warnings", {})
	if warnings:
		for warning in warnings:
			misc_logger.warning("MediaWiki returned the following warning: {code} - {text} on {url}.".format(
				code=warning["code"], text=warning.get("text", warning.get("*", "")), url=url
			))
	return request_data


def add_to_dict(dictionary, key):
	if key in dictionary:
		dictionary[key] += 1
	else:
		dictionary[key] = 1
	return dictionary


def prepare_paths(path: str, dry=False):
	"""Set the URL paths for article namespace and script namespace
	WIKI_API_PATH will be: WIKI_DOMAIN/api.php
	WIKI_ARTICLE_PATH will be: WIKI_DOMAIN/articlepath/$1 where $1 is the replaced string
	WIKI_SCRIPT_PATH will be: WIKI_DOMAIN/
	WIKI_JUST_DOMAIN will be: WIKI_DOMAIN"""
	global WIKI_API_PATH
	global WIKI_ARTICLE_PATH
	global WIKI_SCRIPT_PATH
	global WIKI_JUST_DOMAIN

	def quick_try_url(url):
		"""Quickly test if URL is the proper script path,
		False if it appears invalid
		dictionary when it appears valid"""
		try:
			request = requests.get(url, timeout=5)
			if request.status_code == requests.codes.ok:
				if request.json()["query"]["general"] is not None:
					return request
			return False
		except (KeyError, requests.exceptions.ConnectionError):
			return False
	try:
		parsed_url = urlparse(path)
	except KeyError:
		misc_logger.critical("wiki_url is not specified in the settings. Please provide the wiki url in the settings and start the script again.")
		sys.exit(1)
	for url_scheme in (path, path.split("wiki")[0], urlunparse((*parsed_url[0:2], "", "", "", ""))):  # check different combinations, it's supposed to be idiot-proof
		tested = quick_try_url(url_scheme + "/api.php?action=query&format=json&meta=siteinfo")
		if tested:
			if not dry:
				WIKI_API_PATH = urlunparse((*parsed_url[0:2], "", "", "", "")) + tested.json()["query"]["general"]["scriptpath"] + "/api.php"
				WIKI_SCRIPT_PATH = urlunparse((*parsed_url[0:2], "", "", "", "")) + tested.json()["query"]["general"]["scriptpath"] + "/"
				WIKI_ARTICLE_PATH = urlunparse((*parsed_url[0:2], "", "", "", "")) + tested.json()["query"]["general"]["articlepath"]
				WIKI_JUST_DOMAIN = urlunparse((*parsed_url[0:2], "", "", "", ""))
				break
			return urlunparse((*parsed_url[0:2], "", "", "", ""))

	else:
		misc_logger.critical("Could not verify wikis paths. Please make sure you have given the proper wiki URLs in settings.json ({path} should be script path to your wiki) and your Internet connection is working.".format(path=path))
		sys.exit(1)


prepare_paths(settings["wiki_url"])


def send_simple(msgtype, message, name, avatar):
	discord_msg = DiscordMessage("compact", msgtype, settings["webhookURL"], content=message)
	discord_msg.set_avatar(avatar)
	discord_msg.set_name(name)
	messagequeue.resend_msgs()
	send_to_discord(discord_msg, meta=DiscordMessageMetadata("POST"))


def run_hooks(hooks, *arguments):
	for hook in hooks:
		try:
			hook(*arguments)
		except:
			if settings.get("error_tolerance", 1) > 0:
				misc_logger.exception("On running a pre hook, ignoring pre-hook")
			else:
				raise


def profile_field_name(name, embed):
	try:
		return profile_fields[name]
	except KeyError:
		if embed:
			return _("Unknown")
		else:
			return _("unknown")


class LinkParser(HTMLParser):
	new_string = ""
	recent_href = ""

	def handle_starttag(self, tag, attrs):
		for attr in attrs:
			if attr[0] == 'href':
				self.recent_href = attr[1]
				if self.recent_href.startswith("//"):
					self.recent_href = "https:{rest}".format(rest=self.recent_href)
				elif not self.recent_href.startswith("http"):
					self.recent_href = WIKI_JUST_DOMAIN + self.recent_href
				self.recent_href = self.recent_href.replace(")", "\\)")
			elif attr[0] == 'data-uncrawlable-url':
				self.recent_href = attr[1].encode('ascii')
				self.recent_href = base64.b64decode(self.recent_href)
				self.recent_href = WIKI_JUST_DOMAIN + self.recent_href.decode('ascii')

	def handle_data(self, data):
		if self.recent_href:
			self.new_string = self.new_string + "[{}](<{}>)".format(src.api.util.sanitize_to_markdown(data), self.recent_href)
			self.recent_href = ""
		else:
			self.new_string = self.new_string + src.api.util.sanitize_to_markdown(data)

	def handle_comment(self, data):
		self.new_string = self.new_string + src.api.util.sanitize_to_markdown(data)

	def handle_endtag(self, tag):
		misc_logger.debug(self.new_string)
