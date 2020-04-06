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
from configloader import settings
from misc import datafile, WIKI_SCRIPT_PATH, send_to_discord
from session import session

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


def embed_formatter(post):
	"""Embed formatter for Fandom discussions."""
	embed = defaultdict(dict)
	data = {"embeds": []}
	embed["author"]["name"] = post["createdBy"]["name"]
	embed["author"]["icon_url"] = post["createdBy"]["avatarUrl"]
	embed["author"]["url"] = "{wikiurl}f/u/{creatorId}".format(wikiurl=WIKI_SCRIPT_PATH, creatorId=post["creatorId"])
	if post["isReply"]:
		embed["title"] = _("Replied to \"{title}\"").format(title=post["_embedded"]["thread"][0]["title"])
		embed["url"] = "{wikiurl}f/p/{threadId}/r/{postId}".format(wikiurl=WIKI_SCRIPT_PATH, threadId=post["threadId"], postId=post["id"])
	else:
		embed["title"] = _("Created \"{title}\"").format(title=post["title"])
		embed["url"] = "{wikiurl}f/p/{threadId}".format(wikiurl=WIKI_SCRIPT_PATH, threadId=post["threadId"])
	if settings["fandom_discussions"]["appearance"]["embed"]["show_content"]:
		embed["description"] = post["rawContent"] if len(post["rawContent"]) < 2000 else post["rawContent"][0:2000] + "…"
	embed["footer"]["text"] = post["forumName"]
	embed["timestamp"] = datetime.datetime.fromtimestamp(post["creationDate"]["epochSecond"], tz=datetime.timezone.utc).isoformat()
	data["embeds"].append(dict(embed))
	data['avatar_url'] = settings["avatars"]["embed"]
	data['allowed_mentions'] = {'parse': []}
	formatted_embed = json.dumps(data, indent=4)
	send_to_discord(formatted_embed)


def compact_formatter(post):
	"""Compact formatter for Fandom discussions."""
	message = None
	if not post["isReply"]:
		message = _("[{author}](<{url}f/u/{creatorId}>) created [{title}](<{url}f/p/{threadId}>) in {forumName}").format(
			author=post["createdBy"]["name"], url=WIKI_SCRIPT_PATH, creatorId=post["creatorId"], title=post["title"], threadId=post["threadId"], forumName=post["forumName"])
	else:
		message = _("[{author}](<{url}f/u/{creatorId}>) created a [reply](<{url}f/p/{threadId}/r/{postId}>) to [{title}](<{url}f/p/{threadId}>) in {forumName}").format(
			author=post["createdBy"]["name"], url=WIKI_SCRIPT_PATH, creatorId=post["creatorId"], threadId=post["threadId"], postId=post["id"], title=post["_embedded"]["thread"][0]["title"], forumName=post["forumName"]
		)
	send_to_discord(json.dumps({'content': message, 'allowed_mentions': {'parse': []}}))


def fetch_discussions():
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
						formatter(post)
				if int(post["id"]) > storage["discussion_id"]:
					storage["discussion_id"] = int(post["id"])
					datafile.save_datafile()

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