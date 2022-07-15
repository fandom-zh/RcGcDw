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

import logging, requests
from typing import Optional

from src.configloader import settings

#from src.discussion_formatters import embed_formatter, compact_formatter
from src.misc import datafile, prepare_paths, run_hooks
from src.discord.queue import messagequeue, send_to_discord
from src.discord.message import DiscordMessageMetadata, DiscordMessage
from src.session import session
from src.exceptions import ArticleCommentError, NoFormatter
from src.api.util import default_message
from src.api.context import Context
from src.api.hooks import formatter_hooks, pre_hooks, post_hooks



# Create a custom logger

discussion_logger = logging.getLogger("rcgcdw.disc")

# Create a variable in datafile if it doesn't exist yet (in files <1.10)

if "discussion_id" not in datafile.data:
	datafile["discussion_id"] = 0
	datafile.save_datafile()

storage = datafile

global client

# setup a few things first so we don't have to do expensive nested get operations every time
fetch_url = "{wiki}wikia.php?controller=DiscussionPost&method=getPosts&sortDirection=descending&sortKey=creation_date&limit={limit}&includeCounters=false".format(wiki=settings["fandom_discussions"]["wiki_url"], limit=settings["fandom_discussions"]["limit"])
domain = prepare_paths(settings["fandom_discussions"]["wiki_url"], dry=True)  # Shutdown if the path for discussions is wrong
display_mode = settings.get("fandom_discussions", {}).get("appearance", {}).get("mode", "embed")
webhook_url = settings.get("fandom_discussions", {}).get("webhookURL", settings.get("webhookURL"))


def inject_client(client_obj):
	"""Function to avoid circular import issues"""
	global client
	client = client_obj
	client.schedule(fetch_discussions, every=settings["fandom_discussions"]["cooldown"])


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
			discussion_logger.warning("Wiki returned %s" % (request.json()))
			return None
		else:
			if request_json:
				comment_pages: dict = {}
				comment_events: list = [post["forumId"] for post in request_json if post["_embedded"]["thread"][0]["containerType"] == "ARTICLE_COMMENT" and int(post["id"]) > storage["discussion_id"]]
				if comment_events:
					comment_pages: requests.Response = safe_request(
						"{wiki}wikia.php?controller=FeedsAndPosts&method=getArticleNamesAndUsernames&stablePageIds={pages}&format=json".format(
							wiki=settings["fandom_discussions"]["wiki_url"], pages=",".join(comment_events)
						))
					if comment_pages:
						try:
							comment_pages: dict = comment_pages.json()["articleNames"]
						except ValueError:
							discussion_logger.warning("ValueError in fetching discussions")
							return None
						except KeyError:
							discussion_logger.warning("Wiki returned %s" % (request_json.json()))
							return None
					else:
						return None
				for post in request_json:
					if int(post["id"]) > storage["discussion_id"]:
						try:
							discussion_logger.debug(f"Sending discussion post with ID {post['id']}")
							parse_discussion_post(post, comment_pages)
						except ArticleCommentError:
							return None
				if int(post["id"]) > storage["discussion_id"]:
					storage["discussion_id"] = int(post["id"])
					datafile.save_datafile()


def parse_discussion_post(post, comment_pages):
	"""Initial post recognition & handling"""
	global client
	post_type = post["_embedded"]["thread"][0]["containerType"]
	context = Context(display_mode, "discussion", webhook_url, client)
	# Filter posts by forum
	if post_type == "FORUM" and settings["fandom_discussions"].get("show_forums", []):
		if not post["forumName"] in settings["fandom_discussions"]["show_forums"]:
			discussion_logger.debug(f"Ignoring post as it's from {post['forumName']}.")
			return
	comment_page = None
	if post_type == "ARTICLE_COMMENT":
		try:
			comment_page = {**comment_pages[post["forumId"]], "fullUrl": domain + comment_pages[post["forumId"]]["relativeUrl"]}
		except KeyError:
			discussion_logger.error("Could not parse paths for article comment, here is the content of comment_pages: {}, ignoring...".format(comment_pages))
			raise ArticleCommentError
	event_type = f"discussion/{post_type.lower()}"
	context.event = event_type
	context.set_comment_page(comment_page)
	run_hooks(pre_hooks, context, post)
	try:
		discord_message = default_message(event_type, formatter_hooks)(context, post)
	except NoFormatter:
		return
	except:
		if settings.get("error_tolerance", 1) > 0:
			discord_message: Optional[DiscordMessage] = None  # It's handled by send_to_discord, we still want other code to run
		else:
			raise
	metadata = DiscordMessageMetadata("POST")
	run_hooks(post_hooks, discord_message, metadata, context, post)
	discord_message.finish_embed()
	send_to_discord(discord_message, metadata)


def safe_request(url) -> Optional[requests.Response]:
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
