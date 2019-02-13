#!/usr/bin/python
# -*- coding: utf-8 -*-

# Recent changes Gamepedia compatible Discord webhook is a project for using a webhook as recent changes page from MediaWiki.
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

# WARNING! SHITTY CODE AHEAD. ENTER ONLY IF YOU ARE SURE YOU CAN TAKE IT
# You have been warned

import time, logging, json, requests, datetime, re, gettext, math, random, os.path, schedule, sys
from bs4 import BeautifulSoup
from collections import defaultdict, Counter
from urllib.parse import quote_plus
from html.parser import HTMLParser

if __name__ != "__main__":
	logging.critical("The file is being executed as a module. Please execute the script using the console.")
	sys.exit(1)

TESTING = True if "--test" in sys.argv else False

try:
	with open("settings.json") as sfile:
		settings = json.load(sfile)
		if settings["limitrefetch"] < settings["limit"] and settings["limitrefetch"] != -1:
			settings["limitrefetch"] = settings["limit"]
except FileNotFoundError:
	logging.critical("No config file could be found. Please make sure settings.json is in the directory.")
	sys.exit(1)

logged_in = False
logging.basicConfig(level=settings["verbose_level"])
if settings["limitrefetch"] != -1 and os.path.exists("lastchange.txt") == False:
	with open("lastchange.txt", 'w') as sfile:
		sfile.write("99999999999")
logging.debug("Current settings: {settings}".format(settings=settings))
try:
	lang = gettext.translation('rcgcdw', localedir='locale', languages=[settings["lang"]])
except FileNotFoundError:
	logging.critical("No language files have been found. Make sure locale folder is located in the directory.")
	sys.exit(1)

lang.install()
ngettext = lang.ngettext


class MWError(Exception):
	pass


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
					self.recent_href = "https://{wiki}.gamepedia.com".format(wiki=settings["wiki"]) + self.recent_href
				self.recent_href = self.recent_href.replace(")", "\\)")

	def handle_data(self, data):
		if self.recent_href:
			self.new_string = self.new_string + "[{}]({})".format(data, self.recent_href)
			self.recent_href = ""
		else:
			self.new_string = self.new_string + data

	def handle_comment(self, data):
		self.new_string = self.new_string + data

	def handle_endtag(self, tag):
		logging.debug(self.new_string)


LinkParser = LinkParser()


def send(message, name, avatar):
	dictionary_creator = {}
	dictionary_creator["content"] = message
	if name:
		dictionary_creator["username"] = name
	if avatar:
		dictionary_creator["avatar_url"] = avatar
	send_to_discord(dictionary_creator)


def safe_read(request, *keys):
	if request is None:
		return None
	try:
		request = request.json()
		for item in keys:
			request = request[item]
	except KeyError:
		logging.warning(
			"Failure while extracting data from request on key {key} in {change}".format(key=item, change=request))
		return None
	except ValueError:
		logging.warning("Failure while extracting data from request in {change}".format(change=request))
		return None
	return request


def send_to_discord_webhook(data):
	header = settings["header"]
	if "content" not in data:
		header['Content-Type'] = 'application/json'
	else:
		header['Content-Type'] = 'application/x-www-form-urlencoded'
	try:
		result = requests.post(settings["webhookURL"], data=data,
		                       headers=header, timeout=10)
	except requests.exceptions.Timeout:
		logging.warning("Timeouted while sending data to the webhook.")
		return 3
	except requests.exceptions.ConnectionError:
		logging.warning("Connection error while sending the data to a webhook")
		return 3
	else:
		return handle_discord_http(result.status_code, data, result)


def send_to_discord(data):
	if recent_changes.unsent_messages:
		recent_changes.unsent_messages.append(data)
	else:
		code = send_to_discord_webhook(data)
		if code == 3:
			recent_changes.unsent_messages.append(data)
		elif code == 2:
			time.sleep(5.0)
			recent_changes.unsent_messages.append(data)
		elif code < 2:
			time.sleep(2.5)
			pass


def webhook_formatter(action, STATIC, **params):
	logging.debug("Received things: {thing}".format(thing=params))
	colornumber = None if isinstance(STATIC["color"], str) else STATIC["color"]
	data = {"embeds": []}
	embed = defaultdict(dict)
	if STATIC["ipaction"]:
		author_url = "https://{wiki}.gamepedia.com/Special:Contributions/{user}".format(wiki=settings["wiki"],
		                                                                                user=params["user"])
		logging.debug("current user: {} with cache of IPs: {}".format(params["user"], recent_changes.map_ips.keys()))
		if params["user"] not in list(recent_changes.map_ips.keys()):
			contibs = safe_read(recent_changes.safe_request(
				"https://{wiki}.gamepedia.com/api.php?action=query&format=json&list=usercontribs&uclimit=max&ucuser={user}&ucstart={timestamp}&ucprop=".format(
					wiki=settings["wiki"], user=params["user"], timestamp=STATIC["timestamp"])), "query", "usercontribs")
			if contibs is None:
				logging.warning(
					"WARNING: Something went wrong when checking amount of contributions for given IP address")
				params["user"] = params["user"] + "(?)"
			else:
				recent_changes.map_ips[params["user"]] = len(contibs)
				logging.debug("1Current params user {} and state of map_ips {}".format(params["user"], recent_changes.map_ips))
				params["user"] = "{author} ({contribs})".format(author=params["user"], contribs=len(contibs))
		else:
			logging.debug(
				"2Current params user {} and state of map_ips {}".format(params["user"], recent_changes.map_ips))
			if action in ("edit", "new"):
				recent_changes.map_ips[params["user"]] += 1
			params["user"] = "{author} ({amount})".format(author=params["user"],
			                                              amount=recent_changes.map_ips[params["user"]])
	else:
		author_url = "https://{wiki}.gamepedia.com/User:{user}".format(wiki=settings["wiki"],
		                                                               user=params["user"].replace(" ", "_"))
	if action in ("edit", "new"):  # edit or new page
		editsize = params["size"]
		if editsize > 0:
			if editsize > 6032:
				colornumber = 65280
			else:
				colornumber = 35840 + (math.floor(editsize / 52)) * 256
		elif editsize < 0:
			if editsize < -6032:
				colornumber = 16711680
			else:
				colornumber = 9175040 + (math.floor((editsize * -1) / (52))) * 65536
		elif editsize == 0:
			colornumber = 8750469
		link = "https://{wiki}.gamepedia.com/index.php?title={article}&curid={pageid}&diff={diff}&oldid={oldrev}".format(
			wiki=settings["wiki"], pageid=params["pageid"], diff=params["diff"], oldrev=params["oldrev"],
			article=params["title"].replace(" ", "_"))
		embed["title"] = "{redirect}{article} ({new}{minor}{editsize})".format(redirect="⤷ " if STATIC["redirect"] else "",article=params["title"], editsize="+" + str(
			editsize) if editsize > 0 else editsize, new=_("(N!) ") if action == "new" else "",
		                                                             minor=_("m ") if action == "edit" and params[
			                                                             "minor"] else "")
	elif action in ("upload/overwrite", "upload/upload"):  # sending files
		license = None
		urls = safe_read(recent_changes.safe_request(
			"https://{wiki}.gamepedia.com/api.php?action=query&format=json&prop=imageinfo&list=&meta=&titles={filename}&iiprop=timestamp%7Curl&iilimit=2".format(
				wiki=settings["wiki"], filename=params["title"])), "query", "pages")
		undolink = ""
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"],
		                                                       article=params["title"].replace(" ", "_"))
		additional_info_retrieved = False
		if urls is not None:
			logging.debug(urls)
			if "-1" not in urls:  # page removed before we asked for it
				img_info = next(iter(urls.values()))["imageinfo"]
				embed["image"]["url"] = img_info[0]["url"] + "?version=" + "".join([x for x in img_info[0]["timestamp"] if x.isdigit()]) # prevent image from being cached
				additional_info_retrieved = True
		else:
			pass
		if params["overwrite"]:
			if additional_info_retrieved:
				article_encoded = params["title"].replace(" ", "_").replace(')', '\)')
				img_timestamp = [x for x in img_info[1]["timestamp"] if x.isdigit()]
				undolink = "https://{wiki}.gamepedia.com/index.php?title={filename}&action=revert&oldimage={timestamp}%21{filenamewon}".format(
					wiki=settings["wiki"], filename=article_encoded, timestamp="".join(img_timestamp),
					filenamewon=article_encoded.split(":", 1)[1])
				embed["fields"] = [{"name": _("Options"), "value": _("([preview]({link}) | [undo]({undolink}))").format(
					link=embed["image"]["url"], undolink=undolink)}]
			embed["title"] = _("Uploaded a new version of {name}").format(name=params["title"])
		else:
			embed["title"] = _("Uploaded {name}").format(name=params["title"])
			article_content = safe_read(recent_changes.safe_request(
				"https://{wiki}.gamepedia.com/api.php?action=query&format=json&prop=revisions&titles={article}&rvprop=content".format(
					wiki=settings["wiki"], article=quote_plus(params["title"], safe=''))), "query", "pages")
			if article_content is None:
				logging.warning("Something went wrong when getting license for the image")
				return 0
			if "-1" not in article_content:
				content = list(article_content.values())[0]['revisions'][0]['*']
				try:
					matches = re.search(re.compile(settings["license_regex"], re.IGNORECASE), content)
					if matches is not None:
						license = matches.group("license")
					else:
						if re.search(re.compile(settings["license_regex_detect"], re.IGNORECASE), content) is None:
							license = _("**No license!**")
						else:
							license = "?"
				except IndexError:
					logging.error(
						"Given regex for the license detection is incorrect. It does not have a capturing group called \"license\" specified. Please fix license_regex value in the config!")
					license = "?"
				except re.error:
					logging.error(
						"Given regex for the license detection is incorrect. Please fix license_regex or license_regex_detect values in the config!")
					license = "?"
			if additional_info_retrieved:
				embed["fields"] = [
					{"name": _("Options"), "value": _("([preview]({link}))").format(link=embed["image"]["url"])}]
			params["desc"] = _("{desc}\nLicense: {license}").format(desc=params["desc"],
			                                                        license=license if license is not None else "?")
	elif action == "delete/delete":
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"],
		                                                       article=params["title"].replace(" ", "_"))
		embed["title"] = _("Deleted page {article}").format(article=params["title"])
	elif action == "delete/delete_redir":
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"],
		                                                       article=params["title"].replace(" ", "_"))
		embed["title"] = _("Deleted redirect {article} by overwriting").format(article=params["title"])
	elif action == "move/move":
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"],
		                                                       article=params["target"].replace(" ", "_"))
		params["desc"] = "{supress}. {desc}".format(desc=params["desc"],
		                                            supress=_("No redirect has been made") if params[
			                                                                                      "supress"] == True else _(
			                                            "A redirect has been made"))
		embed["title"] = _("Moved {redirect}{article} to {target}").format(redirect="⤷ " if STATIC["redirect"] else "", article=params["title"], target=params["target"])
	elif action == "move/move_redir":
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"],
		                                                       article=params["target"].replace(" ", "_"))
		embed["title"] = _("Moved {redirect}{article} to {title} over redirect").format(redirect="⤷ " if STATIC["redirect"] else "", article=params["title"],
		                                                                      title=params["target"])
	elif action == "protect/move_prot":
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"],
		                                                       article=params["title"].replace(" ", "_"))
		embed["title"] = _("Moved protection settings from {redirect}{article} to {title}").format(redirect="⤷ " if STATIC["redirect"] else "", article=params["title"],
		                                                                                 title=params["target"])
	elif action == "block/block":
		link = "https://{wiki}.gamepedia.com/{user}".format(wiki=settings["wiki"],
		                                                    user=params["blocked_user"].replace(" ", "_").replace(')',
		                                                                                                          '\)'))
		user = params["blocked_user"].split(':')[1]
		block_time = _("infinity and beyond") if params["duration"] == "infinite" else params["duration"]
		embed["title"] = _("Blocked {blocked_user} for {time}").format(blocked_user=user, time=block_time)
	elif action == "block/reblock":
		link = "https://{wiki}.gamepedia.com/{user}".format(wiki=settings["wiki"],
		                                                    user=params["blocked_user"].replace(" ", "_").replace(')',
		                                                                                                          '\)'))
		user = params["blocked_user"].split(':')[1]
		embed["title"] = _("Changed block settings for {blocked_user}").format(blocked_user=user)
	elif action == "block/unblock":
		link = "https://{wiki}.gamepedia.com/{user}".format(wiki=settings["wiki"],
		                                                    user=params["blocked_user"].replace(" ", "_").replace(')',
		                                                                                                          '\)'))
		user = params["blocked_user"].split(':')[1]
		embed["title"] = _("Unblocked {blocked_user}").format(blocked_user=user)
	elif action == "curseprofile/comment-created":
		link = "https://{wiki}.gamepedia.com/Special:CommentPermalink/{commentid}".format(wiki=settings["wiki"],
		                                                                                  commentid=params["commentid"])
		# link = "https://{wiki}.gamepedia.com/UserProfile:{target}".format(wiki=settings["wiki"], target=params["target"].replace(" ", "_").replace(')', '\)')) old way of linking
		embed["title"] = _("Left a comment on {target}'s profile").format(target=params["target"]) if params[
			                                                                                              "target"] != \
		                                                                                              params[
			                                                                                              "user"] else _(
			"Left a comment on their own profile")
	elif action == "curseprofile/comment-replied":
		# link = "https://{wiki}.gamepedia.com/UserProfile:{target}".format(wiki=settings["wiki"], target=params["target"].replace(" ", "_").replace(')', '\)'))
		link = "https://{wiki}.gamepedia.com/Special:CommentPermalink/{commentid}".format(wiki=settings["wiki"],
		                                                                                  commentid=params["commentid"])
		embed["title"] = _("Replied to a comment on {target}'s profile").format(target=params["target"]) if params[
			                                                                                                    "target"] != \
		                                                                                                    params[
			                                                                                                    "user"] else _(
			"Replied to a comment on their own profile")
	elif action == "curseprofile/comment-edited":
		# link = "https://{wiki}.gamepedia.com/UserProfile:{target}".format(wiki=settings["wiki"], target=params["target"].replace(" ", "_").replace(')', '\)'))
		link = "https://{wiki}.gamepedia.com/Special:CommentPermalink/{commentid}".format(wiki=settings["wiki"],
		                                                                                  commentid=params["commentid"])
		embed["title"] = _("Edited a comment on {target}'s profile").format(target=params["target"]) if params[
			                                                                                                "target"] != \
		                                                                                                params[
			                                                                                                "user"] else _(
			"Edited a comment on their own profile")
	elif action == "curseprofile/profile-edited":
		link = "https://{wiki}.gamepedia.com/UserProfile:{target}".format(wiki=settings["wiki"],
		                                                                  target=params["target"].replace(" ",
		                                                                                                  "_").replace(
			                                                                  ')', '\)'))
		if params["field"] == "profile-location":
			field = _("Location")
		elif params["field"] == "profile-aboutme":
			field = _("About me")
		elif params["field"] == "profile-link-google":
			field = _("Google link")
		elif params["field"] == "profile-link-facebook":
			field = _("Facebook link")
		elif params["field"] == "profile-link-twitter":
			field = _("Twitter link")
		elif params["field"] == "profile-link-reddit":
			field = _("Reddit link")
		elif params["field"] == "profile-link-twitch":
			field = _("Twitch link")
		elif params["field"] == "profile-link-psn":
			field = _("PSN link")
		elif params["field"] == "profile-link-vk":
			field = _("VK link")
		elif params["field"] == "profile-link-xbl":
			field = _("XVL link")
		elif params["field"] == "profile-link-steam":
			field = _("Steam link")
		else:
			field = _("Unknown")
		embed["title"] = _("Edited {target}'s profile").format(target=params["target"]) if params["user"] != params[
			"target"] else _("Edited their own profile")
		params["desc"] = _("{field} field changed to: {desc}").format(field=field, desc=params["desc"])
	elif action == "curseprofile/comment-deleted":
		link = "https://{wiki}.gamepedia.com/Special:CommentPermalink/{commentid}".format(wiki=settings["wiki"],
		                                                                                  commentid=params["commentid"])
		# link = "https://{wiki}.gamepedia.com/UserProfile:{target}".format(wiki=settings["wiki"], target=params["target"].replace(" ", "_").replace(')', '\)'))
		embed["title"] = _("Deleted a comment on {target}'s profile").format(target=params["target"])
	elif action in ("rights/rights", "rights/autopromote"):
		link = "https://{wiki}.gamepedia.com/User:".format(wiki=settings["wiki"]) + params["title"].split(":")[1].replace(" ", "_")
		if action == "rights/rights":
			embed["title"] = _("Changed group membership for {target}").format(target=params["title"].split(":")[1])
		else:
			params["user"] = _("System")
			author_url = ""
			embed["title"] = _("{target} got autopromoted to a new usergroup").format(
				target=params["title"].split(":")[1])
		if len(params["old_groups"]) < len(params["new_groups"]):
			embed["thumbnail"]["url"] = "https://i.imgur.com/WnGhF5g.gif"
		old_groups = []
		new_groups = []
		for name in params["old_groups"]:
			old_groups.append(_(name))
		for name in params["new_groups"]:
			new_groups.append(_(name))
		if len(old_groups) == 0:
			old_groups = [_("none")]
		if len(new_groups) == 0:
			new_groups = [_("none")]
		reason = ": {desc}".format(desc=params["desc"]) if params["desc"] != _("No description provided") else ""
		params["desc"] = _("Groups changed from {old_groups} to {new_groups}{reason}").format(
			old_groups=", ".join(old_groups), new_groups=', '.join(new_groups), reason=reason)
	elif action == "protect/protect":
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"],
		                                                       article=params["title"].replace(" ", "_"))
		embed["title"] = _("Protected {target}").format(target=params["title"])
		params["desc"] = "{settings}{cascade} | {reason}".format(settings=params["settings"],
		                                                         cascade=_(" [cascading]") if params["cascade"] else "",
		                                                         reason=params["desc"])
	elif action == "protect/modify":
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"],
		                                                       article=params["title"].replace(" ", "_"))
		embed["title"] = _("Changed protection level for {article}").format(article=params["title"])
		params["desc"] = "{settings}{cascade} | {reason}".format(settings=params["settings"],
		                                                         cascade=_(" [cascading]") if params["cascade"] else "",
		                                                         reason=params["desc"])
	elif action == "protect/unprotect":
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"],
		                                                       article=params["title"].replace(" ", "_"))
		embed["title"] = _("Removed protection from {article}").format(article=params["title"])
	elif action == "delete/revision":
		amount = len(params["amount"])
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"],
		                                                       article=params["title"].replace(" ", "_"))
		embed["title"] = ngettext("Changed visibility of revision on page {article} ",
		                          "Changed visibility of {amount} revisions on page {article} ", amount).format(
			article=params["title"], amount=amount)
	elif action == "import/upload":
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"],
		                                                       article=params["title"].replace(" ", "_"))
		embed["title"] = ngettext("Imported {article} with {count} revision",
		                          "Imported {article} with {count} revisions", params["amount"]).format(
			article=params["title"], count=params["amount"])
	elif action == "delete/restore":
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"],
		                                                       article=params["title"].replace(" ", "_"))
		embed["title"] = _("Restored {article}").format(article=params["title"])
	elif action == "delete/event":
		link = "https://{wiki}.gamepedia.com/Special:RecentChanges".format(wiki=settings["wiki"])
		embed["title"] = _("Changed visibility of log events")
	elif action == "import/interwiki":
		link = "https://{wiki}.gamepedia.com/Special:RecentChanges".format(wiki=settings["wiki"])
		embed["title"] = _("Imported interwiki")
	elif action == "abusefilter/modify":
		link = "https://{wiki}.gamepedia.com/Special:AbuseFilter/history/{number}/diff/prev/{historyid}".format(wiki=settings["wiki"], number=params["filternr"], historyid=params["historyid"])
		embed["title"] = _("Edited abuse filter number {number}").format(number=params["filternr"])
	elif action == "abusefilter/create":
		link = "https://{wiki}.gamepedia.com/Special:AbuseFilter/{number}".format(wiki=settings["wiki"], number=params["filternr"])
		embed["title"] = _("Created abuse filter number {number}").format(number=params["filternr"])
	elif action == "merge/merge":
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"],
		                                                       article=params["title"].replace(" ", "_"))
		embed["title"] = _("Merged revision histories of {article} into {dest}").format(article=params["title"],
		                                                                                dest=params["destination"])
	elif action == "interwiki/iw_add":
		link = "https://{wiki}.gamepedia.com/Special:Interwiki".format(wiki=settings["wiki"])
		embed["title"] = _("Added an entry to the interwiki table")
		params["desc"] = _("Prefix: {prefix}, website: {website} | {desc}").format(desc=params["desc"],
		                                                                           prefix=params["prefix"],
		                                                                           website=params["website"])
	elif action == "interwiki/iw_edit":
		link = "https://{wiki}.gamepedia.com/Special:Interwiki".format(wiki=settings["wiki"])
		embed["title"] = _("Edited an entry in interwiki table")
		params["desc"] = _("Prefix: {prefix}, website: {website} | {desc}").format(desc=params["desc"],
		                                                                           prefix=params["prefix"],
		                                                                           website=params["website"])
	elif action == "interwiki/iw_delete":
		link = "https://{wiki}.gamepedia.com/Special:Interwiki".format(wiki=settings["wiki"])
		embed["title"] = _("Deleted an entry in interwiki table")
		params["desc"] = _("Prefix: {prefix} | {desc}").format(desc=params["desc"], prefix=params["prefix"])
	elif action == "contentmodel/change":
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"],
		                                                       article=params["title"].replace(" ", "_"))
		embed["title"] = _("Changed the content model of the page {article}").format(article=params["title"])
		params["desc"] = _("Model changed from {old} to {new}: {reason}").format(old=params["oldmodel"],
		                                                                         new=params["newmodel"],
		                                                                         reason=params["desc"])
	elif action == "sprite/sprite":
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"],
		                                                       article=params["title"].replace(" ", "_"))
		embed["title"] = _("Edited the sprite for {article}").format(article=params["title"])
	elif action == "sprite/sheet":
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"],
		                                                       article=params["title"].replace(" ", "_"))
		embed["title"] = _("Created the sprite sheet for {article}").format(article=params["title"])
	elif action == "sprite/slice":
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"],
		                                                       article=params["title"].replace(" ", "_"))
		embed["title"] = _("Edited the slice for {article}").format(article=params["title"])
	elif action == "managetags/create":
		link = "https://{wiki}.gamepedia.com/Special:Tags".format(wiki=settings["wiki"])
		embed["title"] = _("Created a tag \"{tag}\"").format(tag=params["additional"]["tag"])
		recent_changes.init_info()
	elif action == "managetags/delete":
		link = "https://{wiki}.gamepedia.com/Special:Tags".format(wiki=settings["wiki"])
		embed["title"] = _("Deleted a tag \"{tag}\"").format(tag=params["additional"]["tag"])
		recent_changes.init_info()
	elif action == "managetags/activate":
		link = "https://{wiki}.gamepedia.com/Special:Tags".format(wiki=settings["wiki"])
		embed["title"] = _("Activated a tag \"{tag}\"").format(tag=params["additional"]["tag"])
	elif action == "managetags/deactivate":
		link = "https://{wiki}.gamepedia.com/Special:Tags".format(wiki=settings["wiki"])
		embed["title"] = _("Deactivated a tag \"{tag}\"").format(tag=params["additional"]["tag"])
	elif action == "suppressed":
		link = "https://{wiki}.gamepedia.com/".format(wiki=settings["wiki"])
		embed["title"] = _("Action has been hidden by administration.")
	else:
		logging.warning("No entry for {event} with params: {params}".format(event=action, params=params))
	embed["author"]["name"] = params["user"]
	embed["author"]["url"] = author_url
	embed["author"]["icon_url"] = STATIC["icon"]
	embed["url"] = link
	if "desc" not in params:
		params["desc"] = ""
	embed["description"] = params["desc"]
	embed["color"] = random.randrange(1, 16777215) if colornumber is None else math.floor(colornumber)
	embed["timestamp"] = STATIC["timestamp"]
	if STATIC["tags"]:
		tag_displayname = []
		if "fields" not in embed:
			embed["fields"] = []
		for tag in STATIC["tags"]:
			if tag in recent_changes.tags:
				tag_displayname.append(recent_changes.tags[tag])
			else:
				tag_displayname.append(tag)
		embed["fields"].append({"name": _("Tags"), "value": ", ".join(tag_displayname)})
	logging.debug("Current params in edit action: {}".format(params))
	if "changed_categories" in STATIC and STATIC["changed_categories"] is not None and not (len(STATIC["changed_categories"]["new"]) == 0 and len(STATIC["changed_categories"]["removed"]) == 0):
		if "fields" not in embed:
			embed["fields"] = []
		# embed["fields"].append({"name": _("Changed categories"), "value": ", ".join(params["new_categories"][0:15]) + ("" if (len(params["new_categories"]) < 15) else _(" and {} more").format(len(params["new_categories"])-14))})
		new_cat = (_("**Added**: ") + ", ".join(STATIC["changed_categories"]["new"][0:16]) + ("\n" if len(STATIC["changed_categories"]["new"])<=15 else _(" and {} more\n").format(len(STATIC["changed_categories"]["new"])-15) ) ) if STATIC["changed_categories"]["new"] else ""
		del_cat = (_("**Removed**: ") + ", ".join(STATIC["changed_categories"]["removed"][0:16]) + ("" if len(STATIC["changed_categories"]["removed"])<=15 else _(" and {} more").format(len(STATIC["changed_categories"]["removed"])-15) ) ) if STATIC["changed_categories"]["removed"] else ""
		embed["fields"].append({"name": _("Changed categories"), "value": new_cat + del_cat})
	data["embeds"].append(dict(embed))
	data['avatar_url'] = settings["avatars"]["embed"]
	formatted_embed = json.dumps(data, indent=4)
	send_to_discord(formatted_embed)


def handle_discord_http(code, formatted_embed, result):
	if 300 > code > 199:  # message went through
		return 0
	elif code == 400:  # HTTP BAD REQUEST result.status_code, data, result, header
		logging.error(
			"Following message has been rejected by Discord, please submit a bug on our bugtracker adding it:")
		logging.error(formatted_embed)
		logging.error(result.text)
		return 1
	elif code == 401 or code == 404:  # HTTP UNAUTHORIZED AND NOT FOUND
		logging.error("Webhook URL is invalid or no longer in use, please replace it with proper one.")
		sys.exit(1)
	elif code == 429:
		logging.error("We are sending too many requests to the Discord, slowing down...")
		return 2
	elif 499 < code < 600:
		logging.error(
			"Discord have trouble processing the event, and because the HTTP code returned is {} it means we blame them.".format(
				code))
		return 3


def first_pass(
		change, changed_categories):  # I've decided to split the embed formatter and change handler, maybe it's more messy this way, I don't know
	if ("actionhidden" in change or "suppressed" in change) and "suppressed" not in settings["ignored"]:
		webhook_formatter("suppressed",
		                  {"timestamp": change["timestamp"], "color": settings["appearance"]["suppressed"]["color"],
		                   "icon": settings["appearance"]["suppressed"]["icon"]}, user=change["user"])
		return
	if "commenthidden" not in change:
		LinkParser.feed(change["parsedcomment"])
		# parsedcomment = (BeautifulSoup(change["parsedcomment"], "lxml")).get_text()
		parsedcomment = LinkParser.new_string
		LinkParser.new_string = ""
	else:
		parsedcomment = _("~~hidden~~")
	logging.debug(change)
	STATIC_VARS = {"timestamp": change["timestamp"], "tags": change["tags"], "redirect": (True if "redirect" in change else False), "ipaction": (True if "anon" in change else False), "changed_categories": changed_categories}
	if not parsedcomment:
		parsedcomment = _("No description provided")
	parsedcomment = re.sub(r"(`|_|\*|~|<|>|{|})", "\\\\\\1", parsedcomment, 0)
	if change["type"] == "edit" and "edit" not in settings["ignored"]:
		logging.debug("List of categories in first_pass: {}".format(changed_categories))
		if "userhidden" in change:
			change["user"] = _("hidden")
		STATIC_VARS = {**STATIC_VARS, **{"color": settings["appearance"]["edit"]["color"],
						  "icon": settings["appearance"]["edit"]["icon"]}}
		webhook_formatter("edit", STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,
		                  oldrev=change["old_revid"], pageid=change["pageid"], diff=change["revid"],
		                  size=change["newlen"] - change["oldlen"], minor=True if "minor" in change else False)
	elif change["type"] == "log":
		combination = "{logtype}/{logaction}".format(logtype=change["logtype"], logaction=change["logaction"])
		if combination in settings["ignored"]:
			return
		logging.debug("combination is {}".format(combination))
		try:
			STATIC_VARS = {**STATIC_VARS, **{"color": settings["appearance"][combination]["color"],
			                                 "icon": settings["appearance"][combination]["icon"]}}
		except KeyError:
			STATIC_VARS = {**STATIC_VARS, **{"color": "", "icon": ""}}
			logging.error("No value in the settings has been given for {}".format(combination))
		if combination == "protect/protect":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,
			                  settings=change["logparams"]["description"], cascade=True if "cascade" in change["logparams"] else False)
		elif combination == "protect/modify":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,
			                  settings=change["logparams"]["description"], cascade=True if "cascade" in change["logparams"] else False)
		elif combination == "protect/unprotect":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment)
		elif combination == "upload/overwrite":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,
			                  overwrite=True)
		elif combination == "upload/upload":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,
			                  overwrite=False)
		elif combination == "delete/delete":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment)
		elif combination == "delete/delete_redir":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment)
		elif combination == "delete/restore":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment)
		elif combination == "delete/revision":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,
			                  amount=change["logparams"]["ids"])
		elif combination == "delete/event":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], desc=parsedcomment)
		elif combination == "import/upload":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,
			                  amount=change["logparams"]["count"])
		elif combination == "import/interwiki":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], desc=parsedcomment)
		elif combination == "merge/merge":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,
			                  destination=change["logparams"]["dest_title"])
		elif combination == "move/move":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,
			                  supress=True if "suppressredirect" in change["logparams"] else False,
			                  target=change["logparams"]['target_title'])
		elif combination == "move/move_redir":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,
			                  target=change["logparams"]["target_title"])
		elif combination == "protect/move_prot":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["logparams"]["oldtitle_title"], desc=parsedcomment,
			                  target=change["title"])
		elif combination == "block/block":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], blocked_user=change["title"],
			                  desc=parsedcomment, duration=change["logparams"]["duration"])
		elif combination == "block/unblock":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], blocked_user=change["title"],
			                  desc=parsedcomment)
		elif combination == "block/reblock":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], blocked_user=change["title"],
			                  desc=parsedcomment)
		elif combination == "rights/rights":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,
			                  old_groups=change["logparams"]["oldgroups"], new_groups=change["logparams"]["newgroups"])
		elif combination == "rights/autopromote":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,
			                  old_groups=change["logparams"]["oldgroups"], new_groups=change["logparams"]["newgroups"])
		elif combination == "abusefilter/modify":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], desc=parsedcomment,
			                  filternr=change["logparams"]['newId'], historyid=change["logparams"]["historyId"])
		elif combination == "abusefilter/create":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], desc=parsedcomment,
			                  filternr=change["logparams"]['newId'])
		elif combination == "interwiki/iw_add":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], desc=parsedcomment,
			                  prefix=change["logparams"]['0'], website=change["logparams"]['1'])
		elif combination == "interwiki/iw_edit":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], desc=parsedcomment,
			                  prefix=change["logparams"]['0'], website=change["logparams"]['1'])
		elif combination == "interwiki/iw_delete":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], desc=parsedcomment,
			                  prefix=change["logparams"]['0'])
		elif combination == "curseprofile/comment-created":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], target=change["title"].split(':')[1],
			                  commentid=change["logparams"]["4:comment_id"])
		elif combination == "curseprofile/comment-edited":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], target=change["title"].split(':')[1],
			                  commentid=change["logparams"]["4:comment_id"])
		elif combination == "curseprofile/comment-deleted":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], target=change["title"].split(':')[1],
			                  commentid=change["logparams"]["4:comment_id"])
		elif combination == "curseprofile/profile-edited":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], target=change["title"].split(':')[1],
			                  field=change["logparams"]['4:section'], desc=change["parsedcomment"])
		elif combination == "curseprofile/comment-replied":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], target=change["title"].split(':')[1],
			                  commentid=change["logparams"]["4:comment_id"])
		elif combination == "contentmodel/change":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,
			                  oldmodel=change["logparams"]["oldmodel"], newmodel=change["logparams"]["newmodel"])
		elif combination == "sprite/sprite":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment)
		elif combination == "sprite/sheet":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment)
		elif combination == "sprite/slice":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment)
		elif combination == "managetags/create":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,
			                  additional=change["logparams"])
		elif combination == "managetags/delete":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,
			                  additional=change["logparams"])
		elif combination == "managetags/activate":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,
			                  additional=change["logparams"])
		elif combination == "managetags/deactivate":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,
			                  additional=change["logparams"])
		elif combination == "tag/update":
			webhook_formatter(combination, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment)
		else:
			logging.warning("No entry matches given change!")
			logging.warning("Entry: {}".format(change))
			send(_("Unable to process the event"), _("error"), settings["avatars"]["no_event"])
			return
	# elif change["type"] == "external":  # not sure what happens then, but it's listed as possible type
	# 	logging.warning("External event happened, ignoring.")
	# 	print(change)
	# 	return
	elif change["type"] == "new" and "new" not in settings["ignored"]:  # new page
		STATIC_VARS = {**STATIC_VARS, **{"color": settings["appearance"]["new"]["color"],
		                                 "icon": settings["appearance"]["new"]["icon"]}}
		webhook_formatter("new", STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,
		                  oldrev=change["old_revid"], pageid=change["pageid"], diff=change["revid"],
		                  size=change["newlen"])
	elif change["type"] == "categorize":
		return
	else:
		logging.warning("This event is not implemented in the bot.")
		logging.debug("Cannot process event {}".format(change))
		return


def day_overview_request():
	logging.info("Fetching daily overview... This may take up to 30 seconds!")
	timestamp = (datetime.datetime.utcnow() - datetime.timedelta(hours=24)).isoformat(timespec='milliseconds')
	logging.debug("timestamp is {}".format(timestamp))
	complete = False
	result = []
	passes = 0
	continuearg = ""
	while not complete and passes < 10:
		request = recent_changes.safe_request(
			"https://{wiki}.gamepedia.com/api.php?action=query&format=json&list=recentchanges&rcend={timestamp}Z&rcprop=title%7Ctimestamp%7Csizes%7Cloginfo%7Cuser&rcshow=!bot&rclimit=500&rctype=edit%7Cnew%7Clog{continuearg}".format(
				wiki=settings["wiki"], timestamp=timestamp, continuearg=continuearg))
		if request:
			try:
				request = request.json()
				rc = request['query']['recentchanges']
				continuearg = request["continue"]["rccontinue"] if "continue" in request else None
			except ValueError:
				logging.warning("ValueError in fetching changes")
				recent_changes.downtime_controller()
				complete = 2
			except KeyError:
				logging.warning("Wiki returned %s" % (request.json()))
				complete = 2
			else:
				result += rc
				if continuearg:
					continuearg = "&rccontinue={}".format(continuearg)
					passes += 1
					logging.debug(
						"continuing requesting next pages of recent changes with {} passes and continuearg being {}".format(
							passes, continuearg))
					time.sleep(3.0)
				else:
					complete = 1
		else:
			complete = 2
	if passes == 10:
		logging.debug("quit the loop because there been too many passes")
	return (result, complete)


def add_to_dict(dictionary, key):
	if key in dictionary:
		dictionary[key] += 1
	else:
		dictionary[key] = 1
	return dictionary


def day_overview():  # time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(time.time()))
	# (datetime.datetime.utcnow()+datetime.timedelta(hours=0)).isoformat(timespec='milliseconds')+'Z'
	result = day_overview_request()
	if result[1] == 1:
		activity = defaultdict(dict)
		hours = defaultdict(dict)
		articles = defaultdict(dict)
		edits = 0
		files = 0
		admin = 0
		changed_bytes = 0
		new_articles = 0
		active_articles = []
		if not result[0] and not settings["send_empty_overview"]:
			return  # no changes in this day
		for item in result[0]:
			if "actionhidden" in item or "suppressed" in item or "userhidden" in item:
				continue  # while such actions have type value (edit/new/log) many other values are hidden and therefore can crash with key error, let's not process such events
			activity = add_to_dict(activity, item["user"])
			hours = add_to_dict(hours, datetime.datetime.strptime(item["timestamp"], "%Y-%m-%dT%H:%M:%SZ").hour)
			if item["type"] == "edit":
				edits += 1
				changed_bytes += item["newlen"] - item["oldlen"]
				if item["ns"] == 0:
					articles = add_to_dict(articles, item["title"])
			if item["type"] == "new":
				if item["ns"] == 0:
					new_articles += 1
				changed_bytes += item["newlen"]
			if item["type"] == "log":
				files = files + 1 if item["logtype"] == item["logaction"] == "upload" else files
				admin = admin + 1 if item["logtype"] in ["delete", "merge", "block", "protect", "import", "rights",
				                                         "abusefilter", "interwiki", "managetags"] else admin
		overall = round(new_articles + edits * 0.1 + files * 0.3 + admin * 0.1 + math.fabs(changed_bytes * 0.001), 2)
		embed = defaultdict(dict)
		embed["title"] = _("Daily overview")
		embed["url"] = "https://{wiki}.gamepedia.com/Special:Statistics".format(wiki=settings["wiki"])
		embed["color"] = settings["appearance"]["daily_overview"]["color"]
		embed["author"]["icon_url"] = settings["appearance"]["daily_overview"]["icon"]
		embed["author"]["name"] = settings["wikiname"]
		embed["author"]["url"] = "https://{wiki}.gamepedia.com/".format(wiki=settings["wiki"])
		if activity:
			#v = activity.values()
			active_users = []
			for user, numberu in Counter(activity).most_common(3):  # find most active users
				active_users.append(user + ngettext(" ({} action)", " ({} actions)", numberu).format(numberu))
			# the_one = random.choice(active_users)
			#v = articles.values()
			for article, numbere in Counter(articles).most_common(3):  # find most active users
				active_articles.append(article + ngettext(" ({} edit)", " ({} edits)", numbere).format(numbere))
			v = hours.values()
			active_hours = []
			for hour, numberh in Counter(hours).most_common(list(v).count(max(v))):  # find most active hours
				active_hours.append(str(hour))
			houramount = ngettext(" UTC ({} action)", " UTC ({} actions)", numberh).format(numberh)
		else:
			active_users = [_("But nobody came")]  # a reference to my favorite game of all the time, sorry ^_^
			active_hours = [_("But nobody came")]
			usramount = ""
			houramount = ""
		if not active_articles:
			active_articles = [_("But nobody came")]
		embed["fields"] = []
		fields = (
		(ngettext("Most active user", "Most active users", len(active_users)), ', '.join(active_users)),
		(ngettext("Most edited article", "Most edited articles", len(active_articles)), ', '.join(active_articles)),
		(_("Edits made"), edits), (_("New files"), files), (_("Admin actions"), admin),
		(_("Bytes changed"), changed_bytes), (_("New articles"), new_articles),
		(_("Unique contributors"), str(len(activity))),
		(ngettext("Most active hour", "Most active hours", len(active_hours)), ', '.join(active_hours) + houramount),
		(_("Day score"), str(overall)))
		for name, value in fields:
			embed["fields"].append({"name": name, "value": value})
		data = {"embeds": [dict(embed)]}
		formatted_embed = json.dumps(data, indent=4)
		send_to_discord(formatted_embed)
	else:
		logging.debug("function requesting changes for day overview returned with error code")


class Recent_Changes_Class(object):
	ids = []
	map_ips = {}
	recent_id = 0
	downtimecredibility = 0
	last_downtime = 0
	tags = {}
	groups = {}
	streak = -1
	unsent_messages = []
	mw_messages = {}
	session = requests.Session()
	session.headers.update(settings["header"])
	if settings["limitrefetch"] != -1:
		with open("lastchange.txt", "r") as record:
			file_content = record.read().strip()
			if file_content:
				file_id = int(file_content)
				logging.debug("File_id is {val}".format(val=file_id))
			else:
				logging.debug("File is empty")
				file_id = 999999999
	else:
		file_id = 999999999  # such value won't cause trouble, and it will make sure no refetch happen

	def handle_mw_errors(self, request):
		if "errors" in request:
			logging.error(request["errors"])
			raise MWError
		return request

	def log_in(self):
		global logged_in
		# session.cookies.clear()
		if '@' not in settings["wiki_bot_login"]:
			logging.error(
				"Please provide proper nickname for login from https://{wiki}.gamepedia.com/Special:BotPasswords".format(
					wiki=settings["wiki"]))
			return
		if len(settings["wiki_bot_password"]) != 32:
			logging.error(
				"Password seems incorrect. It should be 32 characters long! Grab it from https://{wiki}.gamepedia.com/Special:BotPasswords".format(
					wiki=settings["wiki"]))
			return
		logging.info("Trying to log in to https://{wiki}.gamepedia.com...".format(wiki=settings["wiki"]))
		try:
			response = self.handle_mw_errors(
				self.session.post("https://{wiki}.gamepedia.com/api.php".format(wiki=settings["wiki"]),
				                  data={'action': 'query', 'format': 'json', 'utf8': '', 'meta': 'tokens',
				                        'type': 'login'}))
			response = self.handle_mw_errors(
				self.session.post("https://{wiki}.gamepedia.com/api.php".format(wiki=settings["wiki"]),
				                  data={'action': 'login', 'format': 'json', 'utf8': '',
				                        'lgname': settings["wiki_bot_login"],
				                        'lgpassword': settings["wiki_bot_password"],
				                        'lgtoken': response.json()['query']['tokens']['logintoken']}))
		except ValueError:
			logging.error("Logging in have not succeeded")
			return
		except MWError:
			logging.error("Logging in have not succeeded")
			return
		try:
			if response.json()['login']['result'] == "Success":
				logging.info("Logging to the wiki succeeded")
				logged_in = True
			else:
				logging.error("Logging in have not succeeded")
		except:
			logging.error("Logging in have not succeeded")

	def add_cache(self, change):
		self.ids.append(change["rcid"])
		# self.recent_id = change["rcid"]
		if len(self.ids) > settings["limitrefetch"] + 5:
			self.ids.pop(0)

	def fetch(self, amount=settings["limit"]):
		if self.unsent_messages:
			logging.info(
				"{} messages waiting to be delivered to Discord due to Discord throwing errors/no connection to Discord servers.".format(
					len(self.unsent_messages)))
			for num, item in enumerate(self.unsent_messages):
				logging.debug(
					"Trying to send a message to Discord from the queue with id of {} and content {}".format(str(num),
					                                                                                         str(item)))
				if send_to_discord_webhook(item) < 2:
					logging.debug("Sending message succeeded")
					time.sleep(2.5)
				else:
					logging.debug("Sending message failed")
					break
			else:
				self.unsent_messages = []
				logging.debug("Queue emptied, all messages delivered")
			self.unsent_messages = self.unsent_messages[num:]
			logging.debug(self.unsent_messages)
		last_check = self.fetch_changes(amount=amount)
		self.recent_id = last_check if last_check is not None else self.file_id
		if settings["limitrefetch"] != -1 and self.recent_id != self.file_id:
			self.file_id = self.recent_id
			with open("lastchange.txt", "w") as record:
				record.write(str(self.file_id))
		logging.debug("Most recent rcid is: {}".format(self.recent_id))
		return self.recent_id

	def fetch_changes(self, amount, clean=False):
		global logged_in
		if len(self.ids) == 0:
			logging.debug("ids is empty, triggering clean fetch")
			clean = True
		changes = self.safe_request(
			"https://{wiki}.gamepedia.com/api.php?action=query&format=json&list=recentchanges&rcshow=!bot&rcprop=title%7Credirect%7Ctimestamp%7Cids%7Cloginfo%7Cparsedcomment%7Csizes%7Cflags%7Ctags%7Cuser&rclimit={amount}&rctype=edit%7Cnew%7Clog%7Cexternal{categorize}".format(
				wiki=settings["wiki"], amount=amount, categorize="%7Ccategorize" if settings["show_added_categories"] else ""))
		if changes:
			try:
				changes = changes.json()['query']['recentchanges']
				changes.reverse()
			except ValueError:
				logging.warning("ValueError in fetching changes")
				if changes.url == "https://www.gamepedia.com":
					logging.critical(
						"The wiki specified in the settings most probably doesn't exist, got redirected to gamepedia.com")
					sys.exit(1)
				self.downtime_controller()
				return None
			except KeyError:
				logging.warning("Wiki returned %s" % (changes.json()))
				return None
			else:
				if self.downtimecredibility > 0:
					self.downtimecredibility -= 1
					if self.streak > -1:
						self.streak += 1
					if self.streak > 8:
						self.streak = -1
						send(_("Connection to {wiki} seems to be stable now.").format(wiki=settings["wikiname"]),
						     _("Connection status"), settings["avatars"]["connection_restored"])
				# In the first for loop we analize the categorize events and figure if we will need more changes to fetch
				# in order to cover all of the edits
				categorize_events = {}
				new_events = 0
				for change in changes:
					if not (change["rcid"] in self.ids or change["rcid"] < self.recent_id) and not clean:
						new_events += 1
						logging.debug(
							"New event: {}".format(change["rcid"]))
						if new_events == settings["limit"]:
							if amount < 500:
							# call the function again with max limit for more results, ignore the ones in this request
								logging.debug("There were too many new events, requesting max amount of events from the wiki.")
								return self.fetch(amount=5000 if logged_in else 500)
							else:
								logging.debug(
									"There were too many new events, but the limit was high enough we don't care anymore about fetching them all.")
					if change["type"] == "categorize":
						if "commenthidden" not in change:
							cat_title = change["title"].split(':', 1)[1]
							# I so much hate this, blame Markus for making me do this
							if change["revid"] not in categorize_events:
								categorize_events[change["revid"]] = {"new": [], "removed": []}
							comment_to_match = re.sub('<.*?a>', '', change["parsedcomment"])
							if recent_changes.mw_messages["recentchanges-page-added-to-category"].replace("[[:$1]]", "") in comment_to_match:
								categorize_events[change["revid"]]["new"].append(cat_title)
								logging.debug("Matched {} to added category for {}".format(cat_title, change["revid"]))
							elif recent_changes.mw_messages["recentchanges-page-removed-from-category"].replace("[[:$1]]", "") in comment_to_match:
								categorize_events[change["revid"]]["removed"].append(cat_title)
								logging.debug("Matched {} to removed category for {}".format(cat_title, change["revid"]))
							else:
								logging.debug("Unknown match for category change with messages {} and {} and comment_to_match {}".format(recent_changes.mw_messages["recentchanges-page-added-to-category"].replace("[[:$1]]", ""), recent_changes.mw_messages["recentchanges-page-removed-from-category"].replace("[[:$1]]", ""), comment_to_match))
						else:
							logging.debug("Log entry got suppressed, ignoring entry.")
				# if change["revid"] in categorize_events:
						# 	categorize_events[change["revid"]].append(cat_title)
						# else:
						# 	logging.debug("New category '{}' for {}".format(cat_title, change["revid"]))
						# 	categorize_events[change["revid"]] = {cat_title: }
				for change in changes:
					if change["rcid"] in self.ids or change["rcid"] < self.recent_id:
						logging.debug("Change ({}) is in ids or is lower than recent_id {}".format(change["rcid"],
						                                                                           self.recent_id))
						continue
					logging.debug(self.ids)
					logging.debug(self.recent_id)
					self.add_cache(change)
					if clean and not (self.recent_id == 0 and change["rcid"] > self.file_id):
						logging.debug("Rejected {val}".format(val=change["rcid"]))
						continue
					first_pass(change, categorize_events.get(change.get("revid"), None))
				return change["rcid"]

	def safe_request(self, url):
		try:
			request = self.session.get(url, timeout=10)
		except requests.exceptions.Timeout:
			logging.warning("Reached timeout error for request on link {url}".format(url=url))
			self.downtime_controller()
			return None
		except requests.exceptions.ConnectionError:
			logging.warning("Reached connection error for request on link {url}".format(url=url))
			self.downtime_controller()
			return None
		else:
			if 499 < request.status_code < 600:
				self.downtime_controller()
				return None
			return request

	def check_connection(self, looped=False):
		online = 0
		for website in ["https://google.com", "https://instagram.com", "https://steamcommunity.com"]:
			try:
				requests.get(website, timeout=10)
				online += 1
			except requests.exceptions.ConnectionError:
				pass
			except requests.exceptions.Timeout:
				pass
		if online < 1:
			logging.error("Failure when checking Internet connection at {time}".format(
				time=time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())))
			self.downtimecredibility = 0
			if not looped:
				while 1:  # recursed loop, check for connection (every 10 seconds) as long as three services are down, don't do anything else
					if self.check_connection(looped=True):
						recent_changes.fetch(amount=settings["limitrefetch"])
						break
					time.sleep(10)
			return False
		return True

	def downtime_controller(self):
		if not settings["show_updown_messages"]:
			return
		if self.streak > -1:  # reset the streak of successful connections when bad one happens
			self.streak = 0
		if self.downtimecredibility < 60:
			self.downtimecredibility += 15
		else:
			if (
					time.time() - self.last_downtime) > 1800 and self.check_connection():  # check if last downtime happened within 30 minutes, if yes, don't send a message
				send(_("{wiki} seems to be down or unreachable.").format(wiki=settings["wikiname"]),
				     _("Connection status"), settings["avatars"]["connection_failed"])
				self.last_downtime = time.time()
				self.streak = 0

	def clear_cache(self):
		self.map_ips = {}

	def init_info(self):
		startup_info = safe_read(self.safe_request(
			"https://{wiki}.gamepedia.com/api.php?action=query&format=json&uselang=content&list=tags|recentchanges&meta=allmessages&utf8=1&tglimit=max&tgprop=name|displayname&ammessages=recentchanges-page-added-to-category|recentchanges-page-removed-from-category&amenableparser=1&amincludelocal=1".format(
				wiki=settings["wiki"])), "query")
		if startup_info:
			if "tags" in startup_info and "allmessages" in startup_info:
				for tag in startup_info["tags"]:
					self.tags[tag["name"]] = (BeautifulSoup(tag["displayname"], "lxml")).get_text()
				for message in startup_info["allmessages"]:
					self.mw_messages[message["name"]] = message["*"]
			else:
				logging.warning("Could not retrieve initial wiki information. Some features may not work correctly!")
				logging.debug(startup_info)
		else:
			logging.error("Could not retrieve initial wiki information. Possibly internet connection issue?")


recent_changes = Recent_Changes_Class()
try:
	if settings["wiki_bot_login"] and settings["wiki_bot_password"]:
		recent_changes.log_in()
	recent_changes.init_info()
except requests.exceptions.ConnectionError:
	logging.critical("A connection can't be established with the wiki. Exiting...")
	sys.exit(1)
time.sleep(1.0)
recent_changes.fetch(amount=settings["limitrefetch"] if settings["limitrefetch"] != -1 else settings["limit"])

schedule.every(settings["cooldown"]).seconds.do(recent_changes.fetch)
if 1 == 2:
	print(_("director"), _("bot"), _("editor"), _("directors"), _("sysop"), _("bureaucrat"), _("reviewer"),
	      _("autoreview"), _("autopatrol"), _("wiki_guardian"))

if settings["overview"]:
	try:
		overview_time=time.strptime(settings["overview_time"], '%H:%M')
		schedule.every().day.at("{}:{}".format(str(overview_time.tm_hour).zfill(2),
	                                       str(overview_time.tm_min).zfill(2))).do(day_overview)
		del overview_time
	except schedule.ScheduleValueError:
		logging.error("Invalid time format! Currently: {}:{}".format(time.strptime(settings["overview_time"], '%H:%M').tm_hour,  time.strptime(settings["overview_time"], '%H:%M').tm_min))
	except ValueError:
		logging.error("Invalid time format! Currentely: {}. Note: It needs to be in HH:MM format.".format(settings["overview_time"]))
schedule.every().day.at("00:00").do(recent_changes.clear_cache)

if TESTING:
	logging.debug("DEBUGGING")
	recent_changes.recent_id -= 5
	recent_changes.file_id -= 5
	recent_changes.ids = [1]
	recent_changes.fetch(amount=5)
	day_overview()
	sys.exit(0)

while 1: 
	time.sleep(1.0)
	schedule.run_pending()
