# -*- coding: utf-8 -*-

# Recent changes Goat compatible Discord webhook is a project for using a webhook as recent changes page from MediaWiki.
# Copyright (C) 2018 Frisk

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import json, logging, sys, re, time, random, math
from html.parser import HTMLParser
from urllib.parse import urlparse, urlunparse
import requests
from collections import defaultdict
from configloader import settings
import gettext

# Initialize translation

t = gettext.translation('misc', localedir='locale', languages=[settings["lang"]])
_ = t.gettext

# Create a custom logger

misc_logger = logging.getLogger("rcgcdw.misc")

data_template = {"rcid": 99999999999, "discussion_id": 0,
                 "daily_overview": {"edits": None, "new_files": None, "admin_actions": None, "bytes_changed": None,
                                    "new_articles": None, "unique_editors": None, "day_score": None, "days_tracked": 0}}

WIKI_API_PATH: str = ""
WIKI_ARTICLE_PATH: str = ""
WIKI_SCRIPT_PATH: str = ""
WIKI_JUST_DOMAIN: str = ""

class DataFile:
	"""Data class which instance of is shared by multiple modules to remain consistent and do not cause too many IO operations."""
	def __init__(self):
		self.data = self.load_datafile()

	@staticmethod
	def generate_datafile():
		"""Generate a data.json file from a template."""
		try:
			with open("data.json", 'w') as data:
				data.write(json.dumps(data_template, indent=4))
		except PermissionError:
			misc_logger.critical("Could not create a data file (no permissions). No way to store last edit.")
			sys.exit(1)

	def load_datafile(self) -> dict:
		"""Read a data.json file and return a dictionary with contents
		:rtype: dict
		"""
		try:
			with open("data.json") as data:
				return json.loads(data.read())
		except FileNotFoundError:
			self.generate_datafile()
			misc_logger.info("The data file could not be found. Generating a new one...")
			return data_template

	def save_datafile(self):
		"""Overwrites the data.json file with given dictionary"""
		try:
			with open("data.json", "w") as data_file:
				data_file.write(json.dumps(self.data, indent=4))
		except PermissionError:
			misc_logger.critical("Could not modify a data file (no permissions). No way to store last edit.")
			sys.exit(1)


class MessageQueue:
	"""Message queue class for undelivered messages"""
	def __init__(self):
		self._queue = []

	def __repr__(self):
		return self._queue

	def __len__(self):
		return len(self._queue)

	def __iter__(self):
		return iter(self._queue)

	def clear(self):
		self._queue.clear()

	def add_message(self, message):
		self._queue.append(message)

	def cut_messages(self, item_num):
		self._queue = self._queue[item_num:]

	def resend_msgs(self):
		if self._queue:
			misc_logger.info(
				"{} messages waiting to be delivered to Discord due to Discord throwing errors/no connection to Discord servers.".format(
					len(self._queue)))
			for num, item in enumerate(self._queue):
				misc_logger.debug(
					"Trying to send a message to Discord from the queue with id of {} and content {}".format(str(num),
					                                                                                         str(item)))
				if send_to_discord_webhook(item) < 2:
					misc_logger.debug("Sending message succeeded")
					time.sleep(2.5)
				else:
					misc_logger.debug("Sending message failed")
					break
			else:
				self.clear()
				misc_logger.debug("Queue emptied, all messages delivered")
			self.cut_messages(num)
			misc_logger.debug(self._queue)

messagequeue = MessageQueue()
datafile = DataFile()

def weighted_average(value, weight, new_value):
	"""Calculates weighted average of value number with weight weight and new_value with weight 1"""
	return round(((value * weight) + new_value) / (weight + 1), 2)


def link_formatter(link):
	"""Formats a link to not embed it"""
	return "<" + re.sub(r"([)])", "\\\\\\1", link).replace(" ", "_") + ">"

def escape_formatting(data):
	"""Escape Discord formatting"""
	return re.sub(r"([`_*~<>{}@/|\\])", "\\\\\\1", data, 0)

class ContentParser(HTMLParser):
	more = _("\n__And more__")
	current_tag = ""
	small_prev_ins = ""
	small_prev_del = ""
	ins_length = len(more)
	del_length = len(more)
	added = False

	def handle_starttag(self, tagname, attribs):
		if tagname == "ins" or tagname == "del":
			self.current_tag = tagname
		if tagname == "td" and 'diff-addedline' in attribs[0]:
			self.current_tag = tagname + "a"
		if tagname == "td" and 'diff-deletedline' in attribs[0]:
			self.current_tag = tagname + "d"
		if tagname == "td" and 'diff-marker' in attribs[0]:
			self.added = True

	def handle_data(self, data):
		data = re.sub(r"([`_*~<>{}@/|\\])", "\\\\\\1", data, 0)
		if self.current_tag == "ins" and self.ins_length <= 1000:
			self.ins_length += len("**" + data + '**')
			if self.ins_length <= 1000:
				self.small_prev_ins = self.small_prev_ins + "**" + data + '**'
			else:
				self.small_prev_ins = self.small_prev_ins + self.more
		if self.current_tag == "del" and self.del_length <= 1000:
			self.del_length += len("~~" + data + '~~')
			if self.del_length <= 1000:
				self.small_prev_del = self.small_prev_del + "~~" + data + '~~'
			else:
				self.small_prev_del = self.small_prev_del + self.more
		if (self.current_tag == "afterins" or self.current_tag == "tda") and self.ins_length <= 1000:
			self.ins_length += len(data)
			if self.ins_length <= 1000:
				self.small_prev_ins = self.small_prev_ins + data
			else:
				self.small_prev_ins = self.small_prev_ins + self.more
		if (self.current_tag == "afterdel" or self.current_tag == "tdd") and self.del_length <= 1000:
			self.del_length += len(data)
			if self.del_length <= 1000:
				self.small_prev_del = self.small_prev_del + data
			else:
				self.small_prev_del = self.small_prev_del + self.more
		if self.added:
			if data == '+' and self.ins_length <= 1000:
				self.ins_length += 1
				if self.ins_length <= 1000:
					self.small_prev_ins = self.small_prev_ins + '\n'
				else:
					self.small_prev_ins = self.small_prev_ins + self.more
			if data == '−' and self.del_length <= 1000:
				self.del_length += 1
				if self.del_length <= 1000:
					self.small_prev_del = self.small_prev_del + '\n'
				else:
					self.small_prev_del = self.small_prev_del + self.more
			self.added = False

	def handle_endtag(self, tagname):
		if tagname == "ins":
			self.current_tag = "afterins"
		elif tagname == "del":
			self.current_tag = "afterdel"
		else:
			self.current_tag = ""


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


def handle_discord_http(code, formatted_embed, result):
	if 300 > code > 199:  # message went through
		return 0
	elif code == 400:  # HTTP BAD REQUEST result.status_code, data, result, header
		misc_logger.error(
			"Following message has been rejected by Discord, please submit a bug on our bugtracker adding it:")
		misc_logger.error(formatted_embed)
		misc_logger.error(result.text)
		return 1
	elif code == 401 or code == 404:  # HTTP UNAUTHORIZED AND NOT FOUND
		misc_logger.error("Webhook URL is invalid or no longer in use, please replace it with proper one.")
		sys.exit(1)
	elif code == 429:
		misc_logger.error("We are sending too many requests to the Discord, slowing down...")
		return 2
	elif 499 < code < 600:
		misc_logger.error(
			"Discord have trouble processing the event, and because the HTTP code returned is {} it means we blame them.".format(
				code))
		return 3


def add_to_dict(dictionary, key):
	if key in dictionary:
		dictionary[key] += 1
	else:
		dictionary[key] = 1
	return dictionary

def prepare_paths():
	global WIKI_API_PATH
	global WIKI_ARTICLE_PATH
	global WIKI_SCRIPT_PATH
	global WIKI_JUST_DOMAIN
	"""Set the URL paths for article namespace and script namespace
	WIKI_API_PATH will be: WIKI_DOMAIN/api.php
	WIKI_ARTICLE_PATH will be: WIKI_DOMAIN/articlepath/$1 where $1 is the replaced string
	WIKI_SCRIPT_PATH will be: WIKI_DOMAIN/
	WIKI_JUST_DOMAIN will be: WIKI_DOMAIN"""
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
		parsed_url = urlparse(settings["wiki_url"])
	except KeyError:
		misc_logger.critical("wiki_url is not specified in the settings. Please provide the wiki url in the settings and start the script again.")
		sys.exit(1)
	for url_scheme in (settings["wiki_url"], settings["wiki_url"].split("wiki")[0], urlunparse((*parsed_url[0:2], "", "", "", ""))):  # check different combinations, it's supposed to be idiot-proof
		tested = quick_try_url(url_scheme + "/api.php?action=query&format=json&meta=siteinfo")
		if tested:
			WIKI_API_PATH = urlunparse((*parsed_url[0:2], "", "", "", "")) + tested.json()["query"]["general"]["scriptpath"] + "/api.php"
			WIKI_SCRIPT_PATH = urlunparse((*parsed_url[0:2], "", "", "", "")) + tested.json()["query"]["general"]["scriptpath"] + "/"
			WIKI_ARTICLE_PATH = urlunparse((*parsed_url[0:2], "", "", "", "")) + tested.json()["query"]["general"]["articlepath"]
			WIKI_JUST_DOMAIN = urlunparse((*parsed_url[0:2], "", "", "", ""))
			break
	else:
		misc_logger.critical("Could not verify wikis paths. Please make sure you have given the proper wiki URL in settings.json and your Internet connection is working.")
		sys.exit(1)


prepare_paths()


def create_article_path(article: str) -> str:
	"""Takes the string and creates an URL with it as the article name"""
	return WIKI_ARTICLE_PATH.replace("$1", article)


def send_simple(msgtype, message, name, avatar):
	discord_msg = DiscordMessage("compact", msgtype, settings["webhookURL"], content=message)
	discord_msg.set_avatar(avatar)
	discord_msg.set_name(name)
	messagequeue.resend_msgs()
	send_to_discord(discord_msg)


def send_to_discord_webhook(data):
	header = settings["header"]
	header['Content-Type'] = 'application/json'
	try:
		result = requests.post(data.webhook_url, data=repr(data),
		                       headers=header, timeout=10)
	except requests.exceptions.Timeout:
		misc_logger.warning("Timeouted while sending data to the webhook.")
		return 3
	except requests.exceptions.ConnectionError:
		misc_logger.warning("Connection error while sending the data to a webhook")
		return 3
	else:
		return handle_discord_http(result.status_code, data, result)


def send_to_discord(data):
	for regex in settings["disallow_regexes"]:
		if data.webhook_object.get("content", None):
			if re.search(re.compile(regex), data.webhook_object["content"]):
				misc_logger.info("Message {} has been rejected due to matching filter ({}).".format(data.webhook_object["content"], regex))
				return  # discard the message without anything
		else:
			for to_check in [data.webhook_object.get("description", ""), data.webhook_object.get("title", ""), *[x["value"] for x in data["fields"]], data.webhook_object.get("author", {"name": ""}).get("name", "")]:
				if re.search(re.compile(regex), to_check):
					misc_logger.info("Message \"{}\" has been rejected due to matching filter ({}).".format(
						to_check, regex))
					return  # discard the message without anything
	if messagequeue:
		messagequeue.add_message(data)
	else:
		code = send_to_discord_webhook(data)
		if code == 3:
			messagequeue.add_message(data)
		elif code == 2:
			time.sleep(5.0)
			messagequeue.add_message(data)
		elif code < 2:
			time.sleep(2.0)
			pass

class DiscordMessage():
	"""A class defining a typical Discord JSON representation of webhook payload."""
	def __init__(self, message_type: str, event_type: str, webhook_url: str, content=None):
		self.webhook_object = dict(allowed_mentions={"parse": []}, avatar_url=settings["avatars"].get(message_type, ""))
		self.webhook_url = webhook_url

		if message_type == "embed":
			self.__setup_embed()
		elif message_type == "compact":
			self.webhook_object["content"] = content

		self.event_type = event_type

	def __setitem__(self, key, value):
		"""Set item is used only in embeds."""
		try:
			self.embed[key] = value
		except NameError:
			raise TypeError("Tried to assign a value when message type is plain message!")

	def __getitem__(self, item):
		return self.embed[item]

	def __repr__(self):
		"""Return the Discord webhook object ready to be sent"""
		return json.dumps(self.webhook_object)

	def __setup_embed(self):
		self.embed = defaultdict(dict)
		if "embeds" not in self.webhook_object:
			self.webhook_object["embeds"] = [self.embed]
		else:
			self.webhook_object["embeds"].append(self.embed)
		self.embed["color"] = None

	def add_embed(self):
		self.finish_embed()
		self.__setup_embed()

	def finish_embed(self):
		if self.embed["color"] is None:
			if settings["appearance"]["embed"].get(self.event_type, {"color": None})["color"] is None:
				self.embed["color"] = random.randrange(1, 16777215)
			else:
				self.embed["color"] = settings["appearance"]["embed"][self.event_type]["color"]
		else:
			self.embed["color"] = math.floor(self.embed["color"])

	def set_author(self, name, url, icon_url=""):
		self.embed["author"]["name"] = name
		self.embed["author"]["url"] = url
		self.embed["author"]["icon_url"] = icon_url

	def add_field(self, name, value, inline=False):
		if "fields" not in self.embed:
			self.embed["fields"] = []
		self.embed["fields"].append(dict(name=name, value=value, inline=inline))

	def set_avatar(self, url):
		self.webhook_object["avatar_url"] = url

	def set_name(self, name):
		self.webhook_object["username"] = name