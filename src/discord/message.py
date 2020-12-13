import json
import math
import random
from collections import defaultdict

from src.configloader import settings


class DiscordMessage:
	"""A class defining a typical Discord JSON representation of webhook payload."""
	def __init__(self, message_type: str, event_type: str, webhook_url: str, content=None):
		self.webhook_object = dict(allowed_mentions={"parse": []}, avatar_url=settings["avatars"].get(message_type, ""))
		self.webhook_url = webhook_url

		if message_type == "embed":
			self.__setup_embed()
		elif message_type == "compact":
			if settings["event_appearance"].get(event_type, {"emoji": None})["emoji"]:
				content = settings["event_appearance"][event_type]["emoji"] + " " + content
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
			if settings["event_appearance"].get(self.event_type, {"color": None})["color"] is None:
				self.embed["color"] = random.randrange(1, 16777215)
			else:
				self.embed["color"] = settings["event_appearance"][self.event_type]["color"]
		else:
			self.embed["color"] = math.floor(self.embed["color"])
		if not self.embed["author"]["icon_url"] and settings["event_appearance"].get(self.event_type, {"icon": None})["icon"]:
			self.embed["author"]["icon_url"] = settings["event_appearance"][self.event_type]["icon"]

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


class DiscordMessageRaw(DiscordMessage):
	def __init__(self, content: dict, webhook_url: str):
		self.webhook_object = content
		self.webhook_url = webhook_url

class DiscordMessageMetadata:
	def __init__(self, method, log_id = None, page_id = None, rev_id = None, webhook_url = None, new_data = None):
		self.method = method
		self.page_id = page_id
		self.log_id = log_id
		self.rev_id = rev_id
		self.webhook_url = webhook_url
		self.new_data = new_data

	def dump_ids(self) -> (int, int, int):
		return self.page_id, self.rev_id, self.log_id