# -*- coding: utf-8 -*-

# Recent changes Goat compatible Discord webhook is a project for using a webhook as recent changes page from MediaWiki.
# Copyright (C) 2020 Frisk

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

import logging, gettext, schedule, requests, json, datetime
from collections import defaultdict
from src.configloader import settings
from urllib.parse import quote_plus
from src.misc import datafile, send_to_discord, DiscordMessage, WIKI_SCRIPT_PATH, escape_formatting, messagequeue
from src.session import session

# Initialize translation

t = gettext.translation('discussions', localedir='locale', languages=[settings["lang"]])
_ = t.gettext

# Create a custom logger

discussion_logger = logging.getLogger("rcgcdw.disc")

# Create a variable in datafile if it doesn't exist yet (in files <1.10)

if "discussion_id" not in datafile.data:
	datafile.data["discussion_id"] = 0
	datafile.save_datafile()

storage = datafile.data

fetch_url = "https://services.fandom.com/discussion/{wikiid}/posts?sortDirection=descending&sortKey=creation_date&limit={limit}".format(wikiid=settings["fandom_discussions"]["wiki_id"], limit=settings["fandom_discussions"]["limit"])


def embed_formatter(post, post_type):
	"""Embed formatter for Fandom discussions."""
	embed = DiscordMessage("embed", "discussion", settings["fandom_discussions"]["webhookURL"])
	embed.set_author(post["createdBy"]["name"], "{wikiurl}f/u/{creatorId}".format(
		wikiurl=settings["fandom_discussions"]["wiki_url"], creatorId=post["creatorId"]), icon_url=post["createdBy"]["avatarUrl"])
	discussion_post_type = post["_embedded"]["thread"][0].get("containerType", "FORUM")  # Can be FORUM, ARTICLE_COMMENT or WALL on UCP
	if post_type == "TEXT":
		if post["isReply"]:
			if discussion_post_type == "FORUM":
				embed.event_type = "discussion/forum/reply"
				embed["title"] = _("Replied to \"{title}\"").format(title=post["_embedded"]["thread"][0]["title"])
				embed["url"] = "{wikiurl}f/p/{threadId}/r/{postId}".format(
					wikiurl=settings["fandom_discussions"]["wiki_url"], threadId=post["threadId"], postId=post["id"])
			elif discussion_post_type == "ARTICLE_COMMENT":
				discussion_logger.warning("Article comments are not yet implemented. For reasons see https://gitlab.com/piotrex43/RcGcDw/-/issues/126#note_366480037")
				return
			elif discussion_post_type == "WALL":
				user_wall = _("unknown")  # Fail safe
				embed.event_type = "discussion/wall/reply"
				if post["forumName"].endswith(' Message Wall'):
					user_wall = post["forumName"][:-13]
					embed["url"] = "{wikiurl}wiki/Message_Wall:{user_wall}?threadId={threadid}#{replyId}".format(wikiurl=settings["fandom_discussions"]["wiki_url"], user_wall=quote_plus(user_wall.replace(" ", "_")), threadid=post["threadId"], replyId=post["id"])
				embed["title"] = _("Replied to \"{title}\" on {user}'s Message Wall").format(title=post["_embedded"]["thread"][0]["title"], user=user_wall)
		else:
			if discussion_post_type == "FORUM":
				embed.event_type = "discussion/forum/post"
				embed["title"] = _("Created \"{title}\"").format(title=post["title"])
				embed["url"] = "{wikiurl}f/p/{threadId}".format(wikiurl=settings["fandom_discussions"]["wiki_url"],
				                                                threadId=post["threadId"])
			elif discussion_post_type == "ARTICLE_COMMENT":
				discussion_logger.warning("Article comments are not yet implemented. For reasons see https://gitlab.com/piotrex43/RcGcDw/-/issues/126#note_366480037")
				return
			elif discussion_post_type == "WALL":
				user_wall = _("unknown")  # Fail safe
				embed.event_type = "discussion/wall/post"
				if post["forumName"].endswith(' Message Wall'):
					user_wall = post["forumName"][:-13]
					embed["url"] = "{wikiurl}wiki/Message_Wall:{user_wall}?threadId={threadid}".format(
						wikiurl=settings["fandom_discussions"]["wiki_url"], user_wall=quote_plus(user_wall.replace(" ", "_")),
						threadid=post["threadId"])
				embed["title"] = _("Created \"{title}\" on {user}'s Message Wall").format(title=post["_embedded"]["thread"][0]["title"], user=user_wall)
		if settings["fandom_discussions"]["appearance"]["embed"]["show_content"]:
			if post.get("jsonModel") is not None:
				npost = DiscussionsFromHellParser(post)
				embed["description"] = npost.parse()
				if npost.image_last:
					embed["image"]["url"] = npost.image_last
					embed["description"] = embed["description"].replace(npost.image_last, "")
			else:  # Fallback when model is not available
				embed["description"] = post.get("rawContent", "")
	elif post_type == "POLL":
		embed.event_type = "discussion/forum/poll"
		poll = post["poll"]
		embed["title"] = _("Created a poll titled \"{title}\"").format(title=poll["question"])
		image_type = False
		if poll["answers"][0]["image"] is not None:
			image_type = True
		for num, option in enumerate(poll["answers"]):
			embed.add_field(option["text"] if image_type is True else _("Option {}").format(num+1),
			                option["text"] if image_type is False else _("__[View image]({image_url})__").format(image_url=option["image"]["url"]),
			                inline=True)
	embed["footer"]["text"] = post["forumName"]
	embed["timestamp"] = datetime.datetime.fromtimestamp(post["creationDate"]["epochSecond"], tz=datetime.timezone.utc).isoformat()
	embed.finish_embed()
	send_to_discord(embed)


def compact_formatter(post, post_type):
	"""Compact formatter for Fandom discussions."""
	message = None
	discussion_post_type = post["_embedded"]["thread"][0].get("containerType",
	                                                          "FORUM")  # Can be FORUM, ARTICLE_COMMENT or WALL on UCP
	if post_type == "TEXT":
		if not post["isReply"]:
			if discussion_post_type == "FORUM":
				message = _("[{author}](<{url}f/u/{creatorId}>) created [{title}](<{url}f/p/{threadId}>) in {forumName}").format(
				author=post["createdBy"]["name"], url=settings["fandom_discussions"]["wiki_url"], creatorId=post["creatorId"], title=post["title"], threadId=post["threadId"], forumName=post["forumName"])
			elif discussion_post_type == "ARTICLE_COMMENT":
				discussion_logger.warning("Article comments are not yet implemented. For reasons see https://gitlab.com/piotrex43/RcGcDw/-/issues/126#note_366480037")
				return
			elif discussion_post_type == "WALL":
				user_wall = _("unknown")  # Fail safe
				if post["forumName"].endswith(' Message Wall'):
					user_wall = post["forumName"][:-13]
				message = _("[{author}](<{url}f/u/{creatorId}>) created [{title}](<{wikiurl}wiki/Message_Wall:{user_wall}?threadId={threadid}>) on {user}'s Message Wall").format(
					author=post["createdBy"]["name"], url=settings["fandom_discussions"]["wiki_url"], creatorId=post["creatorId"], title=post["_embedded"]["thread"][0]["title"], user=user_wall,
					wikiurl=settings["fandom_discussions"]["wiki_url"], user_wall=quote_plus(user_wall.replace(" ", "_")), threadid=post["threadId"]
				    )
		else:
			if discussion_post_type == "FORUM":
				message = _("[{author}](<{url}f/u/{creatorId}>) created a [reply](<{url}f/p/{threadId}/r/{postId}>) to [{title}](<{url}f/p/{threadId}>) in {forumName}").format(
				author=post["createdBy"]["name"], url=settings["fandom_discussions"]["wiki_url"], creatorId=post["creatorId"], threadId=post["threadId"], postId=post["id"], title=post["_embedded"]["thread"][0]["title"], forumName=post["forumName"]
				)
			elif discussion_post_type == "ARTICLE_COMMENT":
				discussion_logger.warning("Article comments are not yet implemented. For reasons see https://gitlab.com/piotrex43/RcGcDw/-/issues/126#note_366480037")
				return
			elif discussion_post_type == "WALL":
				user_wall = _("unknown")  # Fail safe
				if post["forumName"].endswith(' Message Wall'):
					user_wall = post["forumName"][:-13]
				message = _(
					"[{author}](<{url}f/u/{creatorId}>) replied to [{title}](<{wikiurl}wiki/Message_Wall:{user_wall}?threadId={threadid}#{replyId}>) on {user}'s Message Wall").format(
						author=post["createdBy"]["name"], url=settings["fandom_discussions"]["wiki_url"], creatorId=post["creatorId"], title=post["_embedded"]["thread"][0]["title"], user=user_wall,
						wikiurl=settings["fandom_discussions"]["wiki_url"], user_wall=quote_plus(user_wall.replace(" ", "_")), threadid=post["threadId"], replyId=post["id"])

	elif post_type == "POLL":
		message = _(
			"[{author}](<{url}f/u/{creatorId}>) created a poll [{title}](<{url}f/p/{threadId}>) in {forumName}").format(
			author=post["createdBy"]["name"], url=settings["fandom_discussions"]["wiki_url"],
			creatorId=post["creatorId"], title=post["title"], threadId=post["threadId"], forumName=post["forumName"])
	send_to_discord(DiscordMessage("compact", "discussion", settings["fandom_discussions"]["webhookURL"], content=message))


def fetch_discussions():
	messagequeue.resend_msgs()
	request = safe_request(fetch_url)
	if request:
		try:
			request_json = request.json()["_embedded"]["doc:posts"]
			request_json.reverse()
		except ValueError:
			discussion_logger.warning("ValueError in fetching discussions")
			return None
		except KeyError:
			discussion_logger.warning("Wiki returned %s" % (request_json.json()))
			return None
		else:
			if request_json:
				for post in request_json:
					if int(post["id"]) > storage["discussion_id"]:
						parse_discussion_post(post)
				if int(post["id"]) > storage["discussion_id"]:
					storage["discussion_id"] = int(post["id"])
					datafile.save_datafile()

def parse_discussion_post(post):
	"""Initial post recognition & handling"""
	post_type = post.get("funnel", "TEXT")
	if post_type == "TEXT":
		formatter(post, post_type)
	elif post_type == "POLL":
		formatter(post, post_type)
	else:
		discussion_logger.warning("The type of {} is an unknown discussion post type. Please post an issue on the project page to have it added https://gitlab.com/piotrex43/RcGcDw/-/issues.")

class DiscussionsFromHellParser:
	"""This class converts fairly convoluted Fandom jsonModal of a discussion post into Markdown formatted usable thing. Takes string, returns string.
		Kudos to MarkusRost for allowing me to implement this formatter based on his code in Wiki-Bot."""
	def __init__(self, post):
		self.post = post
		self.jsonModal = json.loads(post.get("jsonModel", "{}"))
		self.markdown_text = ""
		self.item_num = 1
		self.image_last = None

	def parse(self) -> str:
		"""Main parsing logic"""
		self.parse_content(self.jsonModal["content"])
		if len(self.markdown_text) > 2000:
			self.markdown_text = self.markdown_text[0:2000] + "…"
		return self.markdown_text

	def parse_content(self, content, ctype=None):
		self.image_last = None
		for item in content:
			if ctype == "bulletList":
				self.markdown_text += "\t• "
			if ctype == "orderedList":
				self.markdown_text += "\t{num}. ".format(num=self.item_num)
				self.item_num += 1
			if item["type"] == "text":
				if "marks" in item:
					prefix, suffix = self.convert_marks(item["marks"])
					self.markdown_text = "{old}{pre}{text}{suf}".format(old=self.markdown_text, pre=prefix, text=escape_formatting(item["text"]), suf=suffix)
				else:
					if ctype == "code_block":
						self.markdown_text += item["text"]  # ignore formatting on preformatted text which cannot have additional formatting anyways
					else:
						self.markdown_text += escape_formatting(item["text"])
			elif item["type"] == "paragraph":
				if "content" in item:
					self.parse_content(item["content"], item["type"])
				self.markdown_text += "\n"
			elif item["type"] == "openGraph":
				if not item["attrs"]["wasAddedWithInlineLink"]:
					self.markdown_text = "{old}{link}\n".format(old=self.markdown_text, link=item["attrs"]["url"])
			elif item["type"] == "image":
				try:
					discussion_logger.debug(item["attrs"]["id"])
					if item["attrs"]["id"] is not None:
						self.markdown_text = "{old}{img_url}\n".format(old=self.markdown_text, img_url=self.post["_embedded"]["contentImages"][int(item["attrs"]["id"])]["url"])
					self.image_last = self.post["_embedded"]["contentImages"][int(item["attrs"]["id"])]["url"]
				except (IndexError, ValueError):
					discussion_logger.warning("Image {} not found.".format(item["attrs"]["id"]))
				discussion_logger.debug(self.markdown_text)
			elif item["type"] == "code_block":
				self.markdown_text += "```\n"
				if "content" in item:
					self.parse_content(item["content"], item["type"])
				self.markdown_text += "\n```\n"
			elif item["type"] == "bulletList":
				if "content" in item:
					self.parse_content(item["content"], item["type"])
			elif item["type"] == "orderedList":
				self.item_num = 1
				if "content" in item:
					self.parse_content(item["content"], item["type"])
			elif item["type"] == "listItem":
				self.parse_content(item["content"], item["type"])

	def convert_marks(self, marks):
		prefix = ""
		suffix = ""
		for mark in marks:
			if mark["type"] == "mention":
				prefix += "["
				suffix = "]({wiki}f/u/{userid}){suffix}".format(wiki=settings["fandom_discussions"]["wiki_url"], userid=mark["attrs"]["userId"], suffix=suffix)
			elif mark["type"] == "strong":
				prefix += "**"
				suffix = "**{suffix}".format(suffix=suffix)
			elif mark["type"] == "link":
				prefix += "["
				suffix = "]({link}){suffix}".format(link=mark["attrs"]["href"], suffix=suffix)
			elif mark["type"] == "em":
				prefix += "_"
				suffix = "_" + suffix
		return prefix, suffix


def safe_request(url):
	"""Function to assure safety of request, and do not crash the script on exceptions,"""
	try:
		request = session.get(url, timeout=10, allow_redirects=False, headers={"Accept": "application/hal+json"})
	except requests.exceptions.Timeout:
		discussion_logger.warning("Reached timeout error for request on link {url}".format(url=url))
		return None
	except requests.exceptions.ConnectionError:
		discussion_logger.warning("Reached connection error for request on link {url}".format(url=url))
		return None
	except requests.exceptions.ChunkedEncodingError:
		discussion_logger.warning("Detected faulty response from the web server for request on link {url}".format(url=url))
		return None
	else:
		if 499 < request.status_code < 600:
			return None
		return request

formatter = embed_formatter if settings["fandom_discussions"]["appearance"]["mode"] == "embed" else compact_formatter

schedule.every(settings["fandom_discussions"]["cooldown"]).seconds.do(fetch_discussions)