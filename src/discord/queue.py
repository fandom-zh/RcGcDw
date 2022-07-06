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

import re
import sys
import time
import logging
from typing import Optional, Union, Tuple

import requests

from src.configloader import settings
from src.discord.message import DiscordMessage, DiscordMessageMetadata, DiscordMessageRaw

AUTO_SUPPRESSION_ENABLED = settings.get("auto_suppression", {"enabled": False}).get("enabled")
if AUTO_SUPPRESSION_ENABLED:
	from src.fileio.database import add_entry as add_message_redaction_entry

rate_limit = 0

logger = logging.getLogger("rcgcdw.discord.queue")

class MessageQueue:
	"""Message queue class for undelivered messages"""
	def __init__(self):
		self._queue: list[Tuple[Union[DiscordMessage, DiscordMessageRaw], DiscordMessageMetadata]] = []

	def __repr__(self):
		return self._queue

	def __len__(self):
		return len(self._queue)

	def __iter__(self):
		return iter(self._queue)

	def clear(self):
		self._queue.clear()

	def add_message(self, message: Tuple[Union[DiscordMessage, DiscordMessageRaw], DiscordMessageMetadata]):
		self._queue.append(message)

	def cut_messages(self, item_num: int):
		self._queue = self._queue[item_num:]

	@staticmethod
	def compare_message_to_dict(metadata: DiscordMessageMetadata, to_match: dict):
		"""Compare DiscordMessageMetadata fields and match them against dictionary"""
		for name, val in to_match.items():
			if getattr(metadata, name, None) != val:
				return False
		return True

	def delete_all_with_matching_metadata(self, **properties):
		"""Deletes all of the messages that have matching metadata properties (useful for message redaction)"""
		for index, item in reversed(list(enumerate(self._queue))):
			if self.compare_message_to_dict(item[1], properties):
				self._queue.pop(index)

	def resend_msgs(self):
		if self._queue:
			logger.info(
				"{} messages waiting to be delivered to Discord due to Discord throwing errors/no connection to Discord servers.".format(
					len(self._queue)))
			for num, item in enumerate(self._queue):
				logger.debug(
					"Trying to send a message to Discord from the queue with id of {} and content {}".format(str(num),
					                                                                                         str(item)))
				if send_to_discord_webhook(item[0], metadata=item[1]) < 2:
					logger.debug("Sending message succeeded")
				else:
					logger.debug("Sending message failed")
					break
			else:
				self.clear()
				logger.debug("Queue emptied, all messages delivered")
			self.cut_messages(num)
			logger.debug(self._queue)


messagequeue = MessageQueue()


def handle_discord_http(code, formatted_embed, result):
	if 300 > code > 199:  # message went through
		return 0
	elif code == 400:  # HTTP BAD REQUEST result.status_code, data, result, header
		logger.error(
			"Following message has been rejected by Discord, please submit a bug on our bugtracker adding it:")
		logger.error(formatted_embed)
		logger.error(result.text)
		return 1
	elif code == 401 or code == 404:  # HTTP UNAUTHORIZED AND NOT FOUND
		if result.request.method == "POST":  # Ignore not found for DELETE and PATCH requests since the message could already be removed by admin
			logger.error("Webhook URL is invalid or no longer in use, please replace it with proper one.")
			sys.exit(1)
		else:
			return 0
	elif code == 429:
		logger.error("We are sending too many requests to the Discord, slowing down...")
		return 2
	elif 499 < code < 600:
		logger.error(
			"Discord have trouble processing the event, and because the HTTP code returned is {} it means we blame them.".format(
				code))
		return 3
	else:
		logger.error("There was an unexpected HTTP code returned from Discord: {}".format(code))
		return 1


def update_ratelimit(request):
	"""Updates rate limit time"""
	global rate_limit
	rate_limit = 0 if int(request.headers.get('x-ratelimit-remaining', "-1")) > 0 else int(request.headers.get(
		'x-ratelimit-reset-after', 0))
	rate_limit += settings.get("discord_message_cooldown", 0)


def send_to_discord_webhook(data: Optional[DiscordMessage], metadata: DiscordMessageMetadata):
	global rate_limit
	header = settings["header"]
	header['Content-Type'] = 'application/json'
	standard_args = dict(headers=header)
	if metadata.method == "POST":
		req = requests.Request("POST", data.webhook_url+"?wait=" + ("true" if AUTO_SUPPRESSION_ENABLED else "false"), data=repr(data), **standard_args)
	elif metadata.method == "DELETE":
		req = requests.Request("DELETE", metadata.webhook_url, **standard_args)
	elif metadata.method == "PATCH":
		req = requests.Request("PATCH", data.webhook_url, data=repr(data), **standard_args)
	try:
		time.sleep(rate_limit)
		rate_limit = 0
		req = req.prepare()
		result = requests.Session().send(req, timeout=10)
		update_ratelimit(result)
		if AUTO_SUPPRESSION_ENABLED and metadata.method == "POST":
			if 199 < result.status_code < 300:  # check if positive error log
				try:
					add_message_redaction_entry(*metadata.dump_ids(), repr(data), result.json().get("id"))
				except ValueError:
					logger.error("Couldn't get json of result of sending Discord message.")
			else:
				pass
	except requests.exceptions.Timeout:
		logger.warning("Timeouted while sending data to the webhook.")
		return 3
	except requests.exceptions.ConnectionError:
		logger.warning("Connection error while sending the data to a webhook")
		return 3
	else:
		return handle_discord_http(result.status_code, data, result)


def send_to_discord(data: Optional[DiscordMessage], meta: DiscordMessageMetadata):
	if data is not None:
		for regex in settings["disallow_regexes"]:
			if data.webhook_object.get("content", None):
				if re.search(re.compile(regex), data.webhook_object["content"]):
					logger.info("Message {} has been rejected due to matching filter ({}).".format(data.webhook_object["content"], regex))
					return  # discard the message without anything
			else:
				for to_check in [data.webhook_object.get("description", ""), data.webhook_object.get("title", ""), *[x["value"] for x in data["fields"]], data.webhook_object.get("author", {"name": ""}).get("name", "")]:
					if re.search(re.compile(regex), to_check):
						logger.info("Message \"{}\" has been rejected due to matching filter ({}).".format(
							to_check, regex))
						return  # discard the message without anything
	if messagequeue:
		messagequeue.add_message((data, meta))
	else:
		code = send_to_discord_webhook(data, metadata=meta)
		if code == 3:
			messagequeue.add_message((data, meta))
		elif code == 2:
			time.sleep(5.0)
			messagequeue.add_message((data, meta))
		elif code is None or code < 2:
			pass