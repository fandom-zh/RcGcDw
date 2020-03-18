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

import time, logging.config, json, requests, datetime, re, gettext, math, random, os.path, schedule, sys, ipaddress, base64
from html.parser import HTMLParser

import misc
from bs4 import BeautifulSoup
from collections import defaultdict, Counter
from urllib.parse import quote_plus, urlparse, urlunparse
from configloader import settings
from misc import link_formatter, ContentParser, safe_read, handle_discord_http, add_to_dict, misc_logger

if __name__ != "__main__":  # return if called as a module
	logging.critical("The file is being executed as a module. Please execute the script using the console.")
	sys.exit(1)

TESTING = True if "--test" in sys.argv else False  # debug mode, pipeline testing

# Prepare logging

logging.config.dictConfig(settings["logging"])
logger = logging.getLogger("rcgcdw")
logger.debug("Current settings: {settings}".format(settings=settings))

# Setup translation

try:
	lang = gettext.translation('rcgcdw', localedir='locale', languages=[settings["lang"]])
except FileNotFoundError:
	logger.critical("No language files have been found. Make sure locale folder is located in the directory.")
	sys.exit(1)

lang.install()
ngettext = lang.ngettext

storage = misc.load_datafile()

# Remove previous data holding file if exists and limitfetch allows

if settings["limitrefetch"] != -1 and os.path.exists("lastchange.txt") is True:
	with open("lastchange.txt", 'r') as sfile:
		logger.info("Converting old lastchange.txt file into new data storage data.json...")
		storage["rcid"] = int(sfile.read().strip())
		misc.save_datafile(storage)
		os.remove("lastchange.txt")

# A few initial vars

logged_in = False
supported_logs = ["protect/protect", "protect/modify", "protect/unprotect", "upload/overwrite", "upload/upload", "delete/delete", "delete/delete_redir", "delete/restore", "delete/revision", "delete/event", "import/upload", "import/interwiki", "merge/merge", "move/move", "move/move_redir", "protect/move_prot", "block/block", "block/unblock", "block/reblock", "rights/rights", "rights/autopromote", "abusefilter/modify", "abusefilter/create", "interwiki/iw_add", "interwiki/iw_edit", "interwiki/iw_delete", "curseprofile/comment-created", "curseprofile/comment-edited", "curseprofile/comment-deleted", "curseprofile/comment-purged", "curseprofile/profile-edited", "curseprofile/comment-replied", "contentmodel/change", "sprite/sprite", "sprite/sheet", "sprite/slice", "managetags/create", "managetags/delete", "managetags/activate", "managetags/deactivate", "tag/update", "cargo/createtable", "cargo/deletetable", "cargo/recreatetable", "cargo/replacetable", "upload/revert"]
profile_fields = {"profile-location": _("Location"), "profile-aboutme": _("About me"), "profile-link-google": _("Google link"), "profile-link-facebook":_("Facebook link"), "profile-link-twitter": _("Twitter link"), "profile-link-reddit": _("Reddit link"), "profile-link-twitch": _("Twitch link"), "profile-link-psn": _("PSN link"), "profile-link-vk": _("VK link"), "profile-link-xbl": _("XBL link"), "profile-link-steam": _("Steam link"), "profile-link-discord": _("Discord handle"), "profile-link-battlenet": _("Battle.net handle")}
WIKI_API_PATH: str = ""
WIKI_ARTICLE_PATH: str = ""
WIKI_SCRIPT_PATH: str = ""
WIKI_JUST_DOMAIN: str = ""


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
			self.new_string = self.new_string + "[{}](<{}>)".format(data, self.recent_href)
			self.recent_href = ""
		else:
			self.new_string = self.new_string + data

	def handle_comment(self, data):
		self.new_string = self.new_string + data

	def handle_endtag(self, tag):
		logger.debug(self.new_string)


LinkParser = LinkParser()

class MWError(Exception):
	pass

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
		logger.critical("wiki_url is not specified in the settings. Please provide the wiki url in the settings and start the script again.")
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
		logger.critical("Could not verify wikis paths. Please make sure you have given the proper wiki URL in settings.json.")
		sys.exit(1)

def create_article_path(article: str) -> str:
	"""Takes the string and creates an URL with it as the article name"""
	return WIKI_ARTICLE_PATH.replace("$1", article)

def send(message, name, avatar):
	dictionary_creator = {"content": message}
	if name:
		dictionary_creator["username"] = name
	if avatar:
		dictionary_creator["avatar_url"] = avatar
	send_to_discord(dictionary_creator)


def profile_field_name(name, embed):
	try:
		return profile_fields[name]
	except KeyError:
		if embed:
			return _("Unknown")
		else:
			return _("unknown")

def send_to_discord_webhook(data):
	header = settings["header"]
	if isinstance(data, str):
		header['Content-Type'] = 'application/json'
	else:
		header['Content-Type'] = 'application/x-www-form-urlencoded'
	try:
		result = requests.post(settings["webhookURL"], data=data,
		                       headers=header, timeout=10)
	except requests.exceptions.Timeout:
		logger.warning("Timeouted while sending data to the webhook.")
		return 3
	except requests.exceptions.ConnectionError:
		logger.warning("Connection error while sending the data to a webhook")
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
			time.sleep(2.0)
			pass


def pull_comment(comment_id):
	try:
		comment = recent_changes.handle_mw_errors(recent_changes.safe_request("{wiki}?action=comment&do=getRaw&comment_id={comment}&format=json".format(wiki=WIKI_API_PATH, comment=comment_id)).json())["text"]
		logger.debug("Got the following comment from the API: {}".format(comment))
	except MWError:
		pass
	except (TypeError, AttributeError):
		logger.exception("Could not resolve the comment text.")
	except KeyError:
		logger.exception("CurseProfile extension API did not respond with a valid comment content.")
	else:
		if len(comment) > 1000:
			comment = comment[0:1000] + "…"
		return comment
	return ""


def compact_formatter(action, change, parsed_comment, categories):
	if action != "suppressed":
		author_url = link_formatter(create_article_path("User:{user}".format( user=change["user"])))
		author = change["user"]
	parsed_comment = "" if parsed_comment is None else " *("+parsed_comment+")*"
	if action in ["edit", "new"]:
		edit_link = link_formatter("{wiki}index.php?title={article}&curid={pageid}&diff={diff}&oldid={oldrev}".format(
			wiki=WIKI_SCRIPT_PATH, pageid=change["pageid"], diff=change["revid"], oldrev=change["old_revid"],
			article=change["title"]))
		edit_size = change["newlen"] - change["oldlen"]
		if edit_size > 0:
			sign = "+"
		else:
			sign = ""
		if change["title"].startswith("MediaWiki:Tag-"):  # Refresh tag list when tag display name is edited
			recent_changes.init_info()
		if action == "edit":
			content = _("[{author}]({author_url}) edited [{article}]({edit_link}){comment} ({sign}{edit_size})").format(author=author, author_url=author_url, article=change["title"], edit_link=edit_link, comment=parsed_comment, edit_size=edit_size, sign=sign)
		else:
			content = _("[{author}]({author_url}) created [{article}]({edit_link}){comment} ({sign}{edit_size})").format(author=author, author_url=author_url, article=change["title"], edit_link=edit_link, comment=parsed_comment, edit_size=edit_size, sign=sign)
	elif action =="upload/upload":
		file_link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) uploaded [{file}]({file_link}){comment}").format(author=author,
		                                                                                    author_url=author_url,
		                                                                                    file=change["title"],
		                                                                                    file_link=file_link,
		                                                                                    comment=parsed_comment)
	elif action == "upload/revert":
		file_link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) reverted a version of [{file}]({file_link}){comment}").format(
			author=author, author_url=author_url, file=change["title"], file_link=file_link, comment=parsed_comment)
	elif action == "upload/overwrite":
		file_link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) uploaded a new version of [{file}]({file_link}){comment}").format(author=author, author_url=author_url, file=change["title"], file_link=file_link, comment=parsed_comment)
	elif action == "delete/delete":
		page_link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) deleted [{page}]({page_link}){comment}").format(author=author, author_url=author_url, page=change["title"], page_link=page_link,
		                                                  comment=parsed_comment)
	elif action == "delete/delete_redir":
		page_link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) deleted redirect by overwriting [{page}]({page_link}){comment}").format(author=author, author_url=author_url, page=change["title"], page_link=page_link,
		                                                   comment=parsed_comment)
	elif action == "move/move":
		link = link_formatter(create_article_path(change["logparams"]['target_title']))
		redirect_status = _("without making a redirect") if "suppressredirect" in change["logparams"] else _("with a redirect")
		content = _("[{author}]({author_url}) moved {redirect}*{article}* to [{target}]({target_url}) {made_a_redirect}{comment}").format(author=author, author_url=author_url, redirect="⤷ " if "redirect" in change else "", article=change["title"],
			target=change["logparams"]['target_title'], target_url=link, comment=parsed_comment, made_a_redirect=redirect_status)
	elif action == "move/move_redir":
		link = link_formatter(create_article_path(change["logparams"]["target_title"]))
		redirect_status = _("without making a redirect") if "suppressredirect" in change["logparams"] else _(
			"with a redirect")
		content = _("[{author}]({author_url}) moved {redirect}*{article}* over redirect to [{target}]({target_url}) {made_a_redirect}{comment}").format(author=author, author_url=author_url, redirect="⤷ " if "redirect" in change else "", article=change["title"],
			target=change["logparams"]['target_title'], target_url=link, comment=parsed_comment, made_a_redirect=redirect_status)
	elif action == "protect/move_prot":
		link = link_formatter(create_article_path(change["logparams"]["oldtitle_title"]))
		content = _(
			"[{author}]({author_url}) moved protection settings from {redirect}*{article}* to [{target}]({target_url}){comment}").format(author=author, author_url=author_url, redirect="⤷ " if "redirect" in change else "", article=change["logparams"]["oldtitle_title"],
			target=change["title"], target_url=link, comment=parsed_comment)
	elif action == "block/block":
		user = change["title"].split(':')[1]
		restriction_description = ""
		try:
			ipaddress.ip_address(user)
			link = link_formatter(create_article_path("Special:Contributions/{user}".format(user=user)))
		except ValueError:
			link = link_formatter(create_article_path(change["title"]))
		if change["logparams"]["duration"] == "infinite":
			block_time = _("infinity and beyond")
		else:
			english_length = re.sub(r"(\d+)", "", change["logparams"][
				"duration"])  # note that translation won't work for millenia and century yet
			english_length_num = re.sub(r"(\D+)", "", change["logparams"]["duration"])
			try:
				english_length = english_length.rstrip("s").strip()
				block_time = "{num} {translated_length}".format(num=english_length_num,
				                                                translated_length=ngettext(english_length,
				                                                                           english_length + "s",
				                                                                           int(english_length_num)))
			except AttributeError:
				logger.error("Could not strip s from the block event, seems like the regex didn't work?")
				return
			if "sitewide" not in change["logparams"]:
				restriction_description = ""
				if change["logparams"]["restrictions"]["pages"]:
					restriction_description = _(" on pages: ")
					for page in change["logparams"]["restrictions"]["pages"]:
						restricted_pages = ["*{page}*".format(page=i["page_title"]) for i in change["logparams"]["restrictions"]["pages"]]
					restriction_description = restriction_description + ", ".join(restricted_pages)
				if change["logparams"]["restrictions"]["namespaces"]:
					namespaces = []
					if restriction_description:
						restriction_description = restriction_description + _(" and namespaces: ")
					else:
						restriction_description = _(" on namespaces: ")
					for namespace in change["logparams"]["restrictions"]["namespaces"]:
						if str(namespace) in recent_changes.namespaces:  # if we have cached namespace name for given namespace number, add its name to the list
							namespaces.append("*{ns}*".format(ns=recent_changes.namespaces[str(namespace)]["*"]))
						else:
							namespaces.append("*{ns}*".format(ns=namespace))
					restriction_description = restriction_description + ", ".join(namespaces)
				restriction_description = restriction_description + "."
				if len(restriction_description) > 1020:
					logger.debug(restriction_description)
					restriction_description = restriction_description[:1020] + "…"
		content = _(
			"[{author}]({author_url}) blocked [{user}]({user_url}) for {time}{restriction_desc}{comment}").format(author=author, author_url=author_url, user=user, time=block_time, user_url=link, restriction_desc=restriction_description, comment=parsed_comment)
	elif action == "block/reblock":
		link = link_formatter(create_article_path(change["title"]))
		user = change["title"].split(':')[1]
		content = _("[{author}]({author_url}) changed block settings for [{blocked_user}]({user_url}){comment}").format(author=author, author_url=author_url, blocked_user=user, user_url=link, comment=parsed_comment)
	elif action == "block/unblock":
		link = link_formatter(create_article_path(change["title"]))
		user = change["title"].split(':')[1]
		content = _("[{author}]({author_url}) unblocked [{blocked_user}]({user_url}){comment}").format(author=author, author_url=author_url, blocked_user=user, user_url=link, comment=parsed_comment)
	elif action == "curseprofile/comment-created":
		link = link_formatter(create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"])))
		content = _("[{author}]({author_url}) left a [comment]({comment}) on {target} profile").format(author=author, author_url=author_url, comment=link, target=change["title"].split(':')[1]+"'s" if change["title"].split(':')[1] != change["user"] else _("their own profile"))
	elif action == "curseprofile/comment-replied":
		link = link_formatter(create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"])))
		content = _("[{author}]({author_url}) replied to a [comment]({comment}) on {target} profile").format(author=author,
		                                                                                               author_url=author_url,
		                                                                                               comment=link,
		                                                                                               target=change["title"].split(':')[1] if change["title"].split(':')[1] !=change["user"] else _("their own"))
	elif action == "curseprofile/comment-edited":
		link = link_formatter(create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"])))
		content = _("[{author}]({author_url}) edited a [comment]({comment}) on {target} profile").format(author=author,
		                                                                                               author_url=author_url,
		                                                                                               comment=link,
		                                                                                               target=change["title"].split(':')[1] if change["title"].split(':')[1] !=change["user"] else _("their own"))
	elif action == "curseprofile/comment-purged":
		link = link_formatter(create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"])))
		content = _("[{author}]({author_url}) purged a comment on {target} profile").format(author=author,
		                                                                                     author_url=author_url,
		                                                                                     target=
		                                                                                     change["title"].split(':')[
			                                                                                     1] if
		                                                                                     change["title"].split(':')[
			                                                                                     1] != change[
			                                                                                     "user"] else _(
			                                                                                     "their own"))
	elif action == "curseprofile/comment-deleted":
		content = _("[{author}]({author_url}) deleted a comment on {target} profile").format(author=author,
		                                                                                    author_url=author_url,
		                                                                                     target=change["title"].split(':')[1] if change["title"].split(':')[1] !=change["user"] else _("their own"))

	elif action == "curseprofile/profile-edited":
		link = link_formatter(create_article_path("UserProfile:{user}".format(user=change["title"].split(":")[1])))
		target = _("[{target}]({target_url})'s").format(target=change["title"].split(':')[1], target_url=link) if change["title"].split(':')[1] != author else _("[their own]({target_url})").format(target_url=link)
		content = _("[{author}]({author_url}) edited the {field} on {target} profile. *({desc})*").format(author=author,
		                                                                        author_url=author_url,
		                                                                        target=target,
		                                                                        field=profile_field_name(change["logparams"]['4:section'], False),
		                                                                        desc=BeautifulSoup(change["parsedcomment"], "lxml").get_text())
	elif action in ("rights/rights", "rights/autopromote"):
		link = link_formatter(create_article_path("User:{user}".format(user=change["title"].split(":")[1])))
		old_groups = []
		new_groups = []
		for name in change["logparams"]["oldgroups"]:
			old_groups.append(_(name))
		for name in change["logparams"]["newgroups"]:
			new_groups.append(_(name))
		if len(old_groups) == 0:
			old_groups = [_("none")]
		if len(new_groups) == 0:
			new_groups = [_("none")]

		if action == "rights/rights":
			content = "[{author}]({author_url}) changed group membership for [{target}]({target_url}) from {old_groups} to {new_groups}{comment}".format(author=author, author_url=author_url, target=change["title"].split(":")[1], target_url=link, old_groups=", ".join(old_groups), new_groups=', '.join(new_groups), comment=parsed_comment)
		else:
			content = "{author} autopromoted [{target}]({target_url}) from {old_groups} to {new_groups}{comment}".format(
				author=_("System"), author_url=author_url, target=change["title"].split(":")[1], target_url=link,
				old_groups=", ".join(old_groups), new_groups=', '.join(new_groups),
				comment=parsed_comment)
	elif action == "protect/protect":
		link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) protected [{article}]({article_url}) with the following settings: {settings}{comment}").format(author=author, author_url=author_url,
		                                                                                                                                     article=change["title"], article_url=link,
		                                                                                                                                     settings=change["logparams"]["description"]+_(" [cascading]") if "cascade" in change["logparams"] else "",
		                                                                                                                                     comment=parsed_comment)
	elif action == "protect/modify":
		link = link_formatter(create_article_path(change["title"]))
		content = _(
			"[{author}]({author_url}) modified protection settings of [{article}]({article_url}) to: {settings}{comment}").format(
			author=author, author_url=author_url,
			article=change["title"], article_url=link,
			settings=change["logparams"]["description"] + _(" [cascading]") if "cascade" in change["logparams"] else "",
			comment=parsed_comment)
	elif action == "protect/unprotect":
		link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) removed protection from [{article}]({article_url}){comment}").format(author=author, author_url=author_url, article=change["title"], article_url=link, comment=parsed_comment)
	elif action == "delete/revision":
		amount = len(change["logparams"]["ids"])
		link = link_formatter(create_article_path(change["title"]))
		content = ngettext("[{author}]({author_url}) changed visibility of revision on page [{article}]({article_url}){comment}",
		                          "[{author}]({author_url}) changed visibility of {amount} revisions on page [{article}]({article_url}){comment}", amount).format(author=author, author_url=author_url,
			article=change["title"], article_url=link, amount=amount, comment=parsed_comment)
	elif action == "import/upload":
		link = link_formatter(create_article_path(change["title"]))
		content = ngettext("[{author}]({author_url}) imported [{article}]({article_url}) with {count} revision{comment}",
		                          "[{author}]({author_url}) imported [{article}]({article_url}) with {count} revisions{comment}", change["logparams"]["count"]).format(
			author=author, author_url=author_url, article=change["title"], article_url=link, count=change["logparams"]["count"], comment=parsed_comment)
	elif action == "delete/restore":
		link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) restored [{article}]({article_url}){comment}").format(author=author, author_url=author_url, article=change["title"], article_url=link, comment=parsed_comment)
	elif action == "delete/event":
		content = _("[{author}]({author_url}) changed visibility of log events{comment}").format(author=author, author_url=author_url, comment=parsed_comment)
	elif action == "import/interwiki":
		content = _("[{author}]({author_url}) imported interwiki{comment}").format(author=author, author_url=author_url, comment=parsed_comment)
	elif action == "abusefilter/modify":
		link = link_formatter(create_article_path("Special:AbuseFilter/history/{number}/diff/prev/{historyid}".format(number=change["logparams"]['newId'], historyid=change["logparams"]["historyId"])))
		content = _("[{author}]({author_url}) edited abuse filter [number {number}]({filter_url})").format(author=author, author_url=author_url, number=change["logparams"]['newId'], filter_url=link)
	elif action == "abusefilter/create":
		link = link_formatter(create_article_path("Special:AbuseFilter/{number}".format(number=change["logparams"]['newId'])))
		content = _("[{author}]({author_url}) created abuse filter [number {number}]({filter_url})").format(author=author, author_url=author_url, number=change["logparams"]['newId'], filter_url=link)
	elif action == "merge/merge":
		link = link_formatter(create_article_path(change["title"]))
		link_dest = link_formatter(create_article_path(change["logparams"]["dest_title"]))
		content = _("[{author}]({author_url}) merged revision histories of [{article}]({article_url}) into [{dest}]({dest_url}){comment}").format(author=author, author_url=author_url, article=change["title"], article_url=link, dest_url=link_dest,
		                                                                                dest=change["logparams"]["dest_title"], comment=parsed_comment)
	elif action == "interwiki/iw_add":
		link = link_formatter(create_article_path("Special:Interwiki"))
		content = _("[{author}]({author_url}) added an entry to the [interwiki table]({table_url}) pointing to {website} with {prefix} prefix").format(author=author, author_url=author_url, desc=parsed_comment,
		                                                                           prefix=change["logparams"]['0'],
		                                                                           website=change["logparams"]['1'],
		                                                                            table_url=link)
	elif action == "interwiki/iw_edit":
		link = link_formatter(create_article_path("Special:Interwiki"))
		content = _("[{author}]({author_url}) edited an entry in [interwiki table]({table_url}) pointing to {website} with {prefix} prefix").format(author=author, author_url=author_url, desc=parsed_comment,
		                                                                           prefix=change["logparams"]['0'],
		                                                                           website=change["logparams"]['1'],
		                                                                            table_url=link)
	elif action == "interwiki/iw_delete":
		link = link_formatter(create_article_path("Special:Interwiki"))
		content = _("[{author}]({author_url}) deleted an entry in [interwiki table]({table_url})").format(author=author, author_url=author_url, table_url=link)
	elif action == "contentmodel/change":
		link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) changed the content model of the page [{article}]({article_url}) from {old} to {new}{comment}").format(author=author, author_url=author_url, article=change["title"], article_url=link, old=change["logparams"]["oldmodel"],
		                                                                         new=change["logparams"]["newmodel"], comment=parsed_comment)
	elif action == "sprite/sprite":
		link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) edited the sprite for [{article}]({article_url})").format(author=author, author_url=author_url, article=change["title"], article_url=link)
	elif action == "sprite/sheet":
		link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) created the sprite sheet for [{article}]({article_url})").format(author=author, author_url=author_url, article=change["title"], article_url=link)
	elif action == "sprite/slice":
		link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) edited the slice for [{article}]({article_url})").format(author=author, author_url=author_url, article=change["title"], article_url=link)
	elif action == "cargo/createtable":
		LinkParser.feed(change["logparams"]["0"])
		table = LinkParser.new_string
		LinkParser.new_string = ""
		content = _("[{author}]({author_url}) created the Cargo table \"{table}\"").format(author=author, author_url=author_url, table=table)
	elif action == "cargo/deletetable":
		content = _("[{author}]({author_url}) deleted the Cargo table \"{table}\"").format(author=author, author_url=author_url, table=change["logparams"]["0"])
	elif action == "cargo/recreatetable":
		LinkParser.feed(change["logparams"]["0"])
		table = LinkParser.new_string
		LinkParser.new_string = ""
		content = _("[{author}]({author_url}) recreated the Cargo table \"{table}\"").format(author=author, author_url=author_url, table=table)
	elif action == "cargo/replacetable":
		LinkParser.feed(change["logparams"]["0"])
		table = LinkParser.new_string
		LinkParser.new_string = ""
		content = _("[{author}]({author_url}) replaced the Cargo table \"{table}\"").format(author=author, author_url=author_url, table=table)
	elif action == "managetags/create":
		link = link_formatter(create_article_path("Special:Tags"))
		content = _("[{author}]({author_url}) created a [tag]({tag_url}) \"{tag}\"").format(author=author, author_url=author_url, tag=change["logparams"]["tag"], tag_url=link)
		recent_changes.init_info()
	elif action == "managetags/delete":
		link = link_formatter(create_article_path("Special:Tags"))
		content = _("[{author}]({author_url}) deleted a [tag]({tag_url}) \"{tag}\"").format(author=author, author_url=author_url, tag=change["logparams"]["tag"], tag_url=link)
		recent_changes.init_info()
	elif action == "managetags/activate":
		link = link_formatter(create_article_path("Special:Tags"))
		content = _("[{author}]({author_url}) activated a [tag]({tag_url}) \"{tag}\"").format(author=author, author_url=author_url, tag=change["logparams"]["tag"], tag_url=link)
	elif action == "managetags/deactivate":
		link = link_formatter(create_article_path("Special:Tags"))
		content = _("[{author}]({author_url}) deactivated a [tag]({tag_url}) \"{tag}\"").format(author=author, author_url=author_url, tag=change["logparams"]["tag"], tag_url=link)
	elif action == "suppressed":
		content = _("An action has been hidden by administration.")
	send_to_discord({'content': content})


def embed_formatter(action, change, parsed_comment, categories):
	data = {"embeds": []}
	embed = defaultdict(dict)
	colornumber = None
	if parsed_comment is None:
		parsed_comment = _("No description provided")
	if action != "suppressed":
		if "anon" in change:
			author_url = create_article_path("Special:Contributions/{user}".format(user=change["user"].replace(" ", "_")))  # Replace here needed in case of #75
			logger.debug("current user: {} with cache of IPs: {}".format(change["user"], recent_changes.map_ips.keys()))
			if change["user"] not in list(recent_changes.map_ips.keys()):
				contibs = safe_read(recent_changes.safe_request(
					"{wiki}?action=query&format=json&list=usercontribs&uclimit=max&ucuser={user}&ucstart={timestamp}&ucprop=".format(
						wiki=WIKI_API_PATH, user=change["user"], timestamp=change["timestamp"])), "query", "usercontribs")
				if contibs is None:
					logger.warning(
						"WARNING: Something went wrong when checking amount of contributions for given IP address")
					change["user"] = change["user"] + "(?)"
				else:
					recent_changes.map_ips[change["user"]] = len(contibs)
					logger.debug("Current params user {} and state of map_ips {}".format(change["user"], recent_changes.map_ips))
					change["user"] = "{author} ({contribs})".format(author=change["user"], contribs=len(contibs))
			else:
				logger.debug(
					"Current params user {} and state of map_ips {}".format(change["user"], recent_changes.map_ips))
				if action in ("edit", "new"):
					recent_changes.map_ips[change["user"]] += 1
				change["user"] = "{author} ({amount})".format(author=change["user"],
				                                              amount=recent_changes.map_ips[change["user"]])
		else:
			author_url = create_article_path("User:{}".format(change["user"].replace(" ", "_")))
		embed["author"]["name"] = change["user"]
		embed["author"]["url"] = author_url
	if action in ("edit", "new"):  # edit or new page
		editsize = change["newlen"] - change["oldlen"]
		if editsize > 0:
			if editsize > 6032:
				colornumber = 65280
			else:
				colornumber = 35840 + (math.floor(editsize / 52)) * 256
		elif editsize < 0:
			if editsize < -6032:
				colornumber = 16711680
			else:
				colornumber = 9175040 + (math.floor((editsize * -1) / 52)) * 65536
		elif editsize == 0:
			colornumber = 8750469
		if change["title"].startswith("MediaWiki:Tag-"):  # Refresh tag list when tag display name is edited
			recent_changes.init_info()
		link = "{wiki}index.php?title={article}&curid={pageid}&diff={diff}&oldid={oldrev}".format(
			wiki=WIKI_SCRIPT_PATH, pageid=change["pageid"], diff=change["revid"], oldrev=change["old_revid"],
			article=change["title"].replace(" ", "_"))
		embed["title"] = "{redirect}{article} ({new}{minor}{bot} {editsize})".format(redirect="⤷ " if "redirect" in change else "", article=change["title"], editsize="+" + str(
			editsize) if editsize > 0 else editsize, new=_("(N!) ") if action == "new" else "",
		                                                             minor=_("m") if action == "edit" and "minor" in change else "", bot=_('b') if "bot" in change else "")
		if settings["appearance"]["embed"]["show_edit_changes"]:
			if action == "new":
				changed_content = safe_read(recent_changes.safe_request(
				"{wiki}?action=compare&format=json&fromtext=&torev={diff}&topst=1&prop=diff".format(
					wiki=WIKI_API_PATH, diff=change["revid"]
				)), "compare", "*")
			else:
				changed_content = safe_read(recent_changes.safe_request(
					"{wiki}?action=compare&format=json&fromrev={oldrev}&torev={diff}&topst=1&prop=diff".format(
						wiki=WIKI_API_PATH, diff=change["revid"],oldrev=change["old_revid"]
					)), "compare", "*")
			if changed_content:
				if "fields" not in embed:
					embed["fields"] = []
				EditDiff = ContentParser()
				EditDiff.feed(changed_content)
				if EditDiff.small_prev_del:
					if EditDiff.small_prev_del.replace("~~", "").isspace():
						EditDiff.small_prev_del = _('__Only whitespace__')
					else:
						EditDiff.small_prev_del = EditDiff.small_prev_del.replace("~~~~", "")
				if EditDiff.small_prev_ins:
					if EditDiff.small_prev_ins.replace("**", "").isspace():
						EditDiff.small_prev_ins = _('__Only whitespace__')
					else:
						EditDiff.small_prev_ins = EditDiff.small_prev_ins.replace("****", "")
				logger.debug("Changed content: {}".format(EditDiff.small_prev_ins))
				if EditDiff.small_prev_del and not action == "new":
					embed["fields"].append(
						{"name": _("Removed"), "value": "{data}".format(data=EditDiff.small_prev_del), "inline": True})
				if EditDiff.small_prev_ins:
					embed["fields"].append(
						{"name": _("Added"), "value": "{data}".format(data=EditDiff.small_prev_ins), "inline": True})
			else:
				logger.warning("Unable to download data on the edit content!")
	elif action in ("upload/overwrite", "upload/upload", "upload/revert"):  # sending files
		license = None
		urls = safe_read(recent_changes.safe_request(
			"{wiki}?action=query&format=json&prop=imageinfo&list=&meta=&titles={filename}&iiprop=timestamp%7Curl%7Carchivename&iilimit=5".format(
				wiki=WIKI_API_PATH, filename=change["title"])), "query", "pages")
		link = create_article_path(change["title"].replace(" ", "_"))
		additional_info_retrieved = False
		if urls is not None:
			logger.debug(urls)
			if "-1" not in urls:  # image still exists and not removed
				try:
					img_info = next(iter(urls.values()))["imageinfo"]
					for num, revision in enumerate(img_info):
						if revision["timestamp"] == change["logparams"]["img_timestamp"]:  # find the correct revision corresponding for this log entry
							embed["image"]["url"] = "{rev}?{cache}".format(rev=revision["url"], cache=int(time.time()*5))  # cachebusting
							additional_info_retrieved = True
							break
				except KeyError:
					logger.warning("Wiki did not respond with extended information about file. The preview will not be shown.")
		else:
			logger.warning("Request for additional image information have failed. The preview will not be shown.")
		if action in ("upload/overwrite", "upload/revert"):
			if additional_info_retrieved:
				article_encoded = change["title"].replace(" ", "_").replace(')', '\)')
				try:
					revision = img_info[num+1]
				except IndexError:
					logger.exception("Could not analize the information about the image (does it have only one version when expected more in overwrite?) which resulted in no Options field: {}".format(img_info))
				else:
					undolink = "{wiki}index.php?title={filename}&action=revert&oldimage={archiveid}".format(
						wiki=WIKI_SCRIPT_PATH, filename=article_encoded, archiveid=revision["archivename"])
					embed["fields"] = [{"name": _("Options"), "value": _("([preview]({link}) | [undo]({undolink}))").format(
						link=embed["image"]["url"], undolink=undolink)}]
			if action == "upload/overwrite":
				embed["title"] = _("Uploaded a new version of {name}").format(name=change["title"])
			elif action == "upload/revert":
				embed["title"] = _("Reverted a version of {name}").format(name=change["title"])
		else:
			embed["title"] = _("Uploaded {name}").format(name=change["title"])
			if settings["license_detection"]:
				article_content = safe_read(recent_changes.safe_request(
					"{wiki}?action=query&format=json&prop=revisions&titles={article}&rvprop=content".format(
						wiki=WIKI_API_PATH, article=quote_plus(change["title"], safe=''))), "query", "pages")
				if article_content is None:
					logger.warning("Something went wrong when getting license for the image")
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
						logger.error(
							"Given regex for the license detection is incorrect. It does not have a capturing group called \"license\" specified. Please fix license_regex value in the config!")
						license = "?"
					except re.error:
						logger.error(
							"Given regex for the license detection is incorrect. Please fix license_regex or license_regex_detect values in the config!")
						license = "?"
			if license is not None:
				parsed_comment += _("\nLicense: {}").format(license)
			if additional_info_retrieved:
				embed["fields"] = [
					{"name": _("Options"), "value": _("([preview]({link}))").format(link=embed["image"]["url"])}]

	elif action == "delete/delete":
		link = create_article_path(change["title"].replace(" ", "_"))
		embed["title"] = _("Deleted page {article}").format(article=change["title"])
	elif action == "delete/delete_redir":
		link = create_article_path(change["title"].replace(" ", "_"))
		embed["title"] = _("Deleted redirect {article} by overwriting").format(article=change["title"])
	elif action == "move/move":
		link = create_article_path(change["logparams"]['target_title'].replace(" ", "_"))
		parsed_comment = "{supress}. {desc}".format(desc=parsed_comment,
		                                            supress=_("No redirect has been made") if "suppressredirect" in change["logparams"] else _(
			                                            "A redirect has been made"))
		embed["title"] = _("Moved {redirect}{article} to {target}").format(redirect="⤷ " if "redirect" in change else "", article=change["title"], target=change["logparams"]['target_title'])
	elif action == "move/move_redir":
		link = create_article_path(change["logparams"]["target_title"].replace(" ", "_"))
		embed["title"] = _("Moved {redirect}{article} to {title} over redirect").format(redirect="⤷ " if "redirect" in change else "", article=change["title"],
		                                                                      title=change["logparams"]["target_title"])
	elif action == "protect/move_prot":
		link = create_article_path(change["logparams"]["oldtitle_title"].replace(" ", "_"))
		embed["title"] = _("Moved protection settings from {redirect}{article} to {title}").format(redirect="⤷ " if "redirect" in change else "", article=change["logparams"]["oldtitle_title"],
		                                                                                 title=change["title"])
	elif action == "block/block":
		user = change["title"].split(':')[1]
		try:
			ipaddress.ip_address(user)
			link = create_article_path("Special:Contributions/{user}".format(user=user))
		except ValueError:
			link = create_article_path(change["title"].replace(" ", "_").replace(')', '\)'))
		if change["logparams"]["duration"] == "infinite":
			block_time = _("infinity and beyond")
		else:
			english_length = re.sub(r"(\d+)", "", change["logparams"]["duration"]) #note that translation won't work for millenia and century yet
			english_length_num = re.sub(r"(\D+)", "", change["logparams"]["duration"])
			try:
				english_length = english_length.rstrip("s").strip()
				block_time = "{num} {translated_length}".format(num=english_length_num, translated_length=ngettext(english_length, english_length + "s", int(english_length_num)))
			except AttributeError:
				logger.error("Could not strip s from the block event, seems like the regex didn't work?")
				return
		if "sitewide" not in change["logparams"]:
			restriction_description = ""
			if change["logparams"]["restrictions"]["pages"]:
				restriction_description = _("Blocked from editing the following pages: ")
				for page in change["logparams"]["restrictions"]["pages"]:
					restricted_pages = ["*"+i["page_title"]+"*" for i in change["logparams"]["restrictions"]["pages"]]
				restriction_description = restriction_description + ", ".join(restricted_pages)
			if change["logparams"]["restrictions"]["namespaces"]:
				namespaces = []
				if restriction_description:
					restriction_description = restriction_description + _(" and namespaces: ")
				else:
					restriction_description = _("Blocked from editing pages on following namespaces: ")
				for namespace in change["logparams"]["restrictions"]["namespaces"]:
					if str(namespace) in recent_changes.namespaces:  # if we have cached namespace name for given namespace number, add its name to the list
						namespaces.append("*{ns}*".format(ns=recent_changes.namespaces[str(namespace)]["*"]))
					else:
						namespaces.append("*{ns}*".format(ns=namespace))
				restriction_description = restriction_description + ", ".join(namespaces)
			restriction_description = restriction_description + "."
			if len(restriction_description) > 1020:
				logger.debug(restriction_description)
				restriction_description = restriction_description[:1020]+"…"
			if "fields" not in embed:
				embed["fields"] = []
			embed["fields"].append(
				{"name": _("Partial block details"), "value": restriction_description, "inline": True})
		embed["title"] = _("Blocked {blocked_user} for {time}").format(blocked_user=user, time=block_time)
	elif action == "block/reblock":
		link = create_article_path(change["title"].replace(" ", "_").replace(')', '\)'))
		user = change["title"].split(':')[1]
		embed["title"] = _("Changed block settings for {blocked_user}").format(blocked_user=user)
	elif action == "block/unblock":
		link = create_article_path(change["title"].replace(" ", "_").replace(')', '\)'))
		user = change["title"].split(':')[1]
		embed["title"] = _("Unblocked {blocked_user}").format(blocked_user=user)
	elif action == "curseprofile/comment-created":
		if settings["appearance"]["embed"]["show_edit_changes"]:
			parsed_comment = pull_comment(change["logparams"]["4:comment_id"])
		link = create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"]))
		embed["title"] = _("Left a comment on {target}'s profile").format(target=change["title"].split(':')[1]) if change["title"].split(':')[1] != \
		                                                                                              change["user"] else _(
			"Left a comment on their own profile")
	elif action == "curseprofile/comment-replied":
		if settings["appearance"]["embed"]["show_edit_changes"]:
			parsed_comment = pull_comment(change["logparams"]["4:comment_id"])
		link = create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"]))
		embed["title"] = _("Replied to a comment on {target}'s profile").format(target=change["title"].split(':')[1]) if change["title"].split(':')[1] != \
		                                                                                                    change["user"] else _(
			"Replied to a comment on their own profile")
	elif action == "curseprofile/comment-edited":
		if settings["appearance"]["embed"]["show_edit_changes"]:
			parsed_comment = pull_comment(change["logparams"]["4:comment_id"])
		link = create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"]))
		embed["title"] = _("Edited a comment on {target}'s profile").format(target=change["title"].split(':')[1]) if change["title"].split(':')[1] != \
		                                                                                                change["user"] else _(
			"Edited a comment on their own profile")
	elif action == "curseprofile/profile-edited":
		link = create_article_path("UserProfile:{target}".format(target=change["title"].split(':')[1].replace(" ", "_").replace(')', '\)')))
		embed["title"] = _("Edited {target}'s profile").format(target=change["title"].split(':')[1]) if change["user"] != change["title"].split(':')[1] else _("Edited their own profile")
		if not change["parsedcomment"]:  # If the field is empty
			parsed_comment = _("Cleared the {field} field").format(field=profile_field_name(change["logparams"]['4:section'], True))
		else:
			parsed_comment = _("{field} field changed to: {desc}").format(field=profile_field_name(change["logparams"]['4:section'], True), desc=BeautifulSoup(change["parsedcomment"], "lxml").get_text())
	elif action == "curseprofile/comment-purged":
		link = create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"]))
		embed["title"] = _("Purged a comment on {target}'s profile").format(target=change["title"].split(':')[1])
	elif action == "curseprofile/comment-deleted":
		if "4:comment_id" in change["logparams"]:
			link = create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"]))
		else:
			link = create_article_path(change["title"])
		embed["title"] = _("Deleted a comment on {target}'s profile").format(target=change["title"].split(':')[1])
	elif action in ("rights/rights", "rights/autopromote"):
		link = create_article_path("User:{}".format(change["title"].split(":")[1].replace(" ", "_")))
		if action == "rights/rights":
			embed["title"] = _("Changed group membership for {target}").format(target=change["title"].split(":")[1])
		else:
			change["user"] = _("System")
			author_url = ""
			embed["title"] = _("{target} got autopromoted to a new usergroup").format(
				target=change["title"].split(":")[1])
		if len(change["logparams"]["oldgroups"]) < len(change["logparams"]["newgroups"]):
			embed["thumbnail"]["url"] = "https://i.imgur.com/WnGhF5g.gif"
		old_groups = []
		new_groups = []
		for name in change["logparams"]["oldgroups"]:
			old_groups.append(_(name))
		for name in change["logparams"]["newgroups"]:
			new_groups.append(_(name))
		if len(old_groups) == 0:
			old_groups = [_("none")]
		if len(new_groups) == 0:
			new_groups = [_("none")]
		reason = ": {desc}".format(desc=parsed_comment) if parsed_comment != _("No description provided") else ""
		parsed_comment = _("Groups changed from {old_groups} to {new_groups}{reason}").format(
			old_groups=", ".join(old_groups), new_groups=', '.join(new_groups), reason=reason)
	elif action == "protect/protect":
		link = create_article_path(change["title"].replace(" ", "_"))
		embed["title"] = _("Protected {target}").format(target=change["title"])
		parsed_comment = "{settings}{cascade} | {reason}".format(settings=change["logparams"]["description"],
		                                                         cascade=_(" [cascading]") if "cascade" in change["logparams"] else "",
		                                                         reason=parsed_comment)
	elif action == "protect/modify":
		link = create_article_path(change["title"].replace(" ", "_"))
		embed["title"] = _("Changed protection level for {article}").format(article=change["title"])
		parsed_comment = "{settings}{cascade} | {reason}".format(settings=change["logparams"]["description"],
		                                                         cascade=_(" [cascading]") if "cascade" in change["logparams"] else "",
		                                                         reason=parsed_comment)
	elif action == "protect/unprotect":
		link = create_article_path(change["title"].replace(" ", "_"))
		embed["title"] = _("Removed protection from {article}").format(article=change["title"])
	elif action == "delete/revision":
		amount = len(change["logparams"]["ids"])
		link = create_article_path(change["title"].replace(" ", "_"))
		embed["title"] = ngettext("Changed visibility of revision on page {article} ",
		                          "Changed visibility of {amount} revisions on page {article} ", amount).format(
			article=change["title"], amount=amount)
	elif action == "import/upload":
		link = create_article_path(change["title"].replace(" ", "_"))
		embed["title"] = ngettext("Imported {article} with {count} revision",
		                          "Imported {article} with {count} revisions", change["logparams"]["count"]).format(
			article=change["title"], count=change["logparams"]["count"])
	elif action == "delete/restore":
		link = create_article_path(change["title"].replace(" ", "_"))
		embed["title"] = _("Restored {article}").format(article=change["title"])
	elif action == "delete/event":
		link = create_article_path("Special:RecentChanges")
		embed["title"] = _("Changed visibility of log events")
	elif action == "import/interwiki":
		link = create_article_path("Special:RecentChanges")
		embed["title"] = _("Imported interwiki")
	elif action == "abusefilter/modify":
		link = create_article_path("Special:AbuseFilter/history/{number}/diff/prev/{historyid}".format(number=change["logparams"]['newId'], historyid=change["logparams"]["historyId"]))
		embed["title"] = _("Edited abuse filter number {number}").format(number=change["logparams"]['newId'])
	elif action == "abusefilter/create":
		link = create_article_path("Special:AbuseFilter/{number}".format( number=change["logparams"]['newId']))
		embed["title"] = _("Created abuse filter number {number}").format(number=change["logparams"]['newId'])
	elif action == "merge/merge":
		link = create_article_path(change["title"].replace(" ", "_"))
		embed["title"] = _("Merged revision histories of {article} into {dest}").format(article=change["title"],
		                                                                                dest=change["logparams"]["dest_title"])
	elif action == "interwiki/iw_add":
		link = create_article_path("Special:Interwiki")
		embed["title"] = _("Added an entry to the interwiki table")
		parsed_comment = _("Prefix: {prefix}, website: {website} | {desc}").format(desc=parsed_comment,
		                                                                           prefix=change["logparams"]['0'],
		                                                                           website=change["logparams"]['1'])
	elif action == "interwiki/iw_edit":
		link = create_article_path("Special:Interwiki")
		embed["title"] = _("Edited an entry in interwiki table")
		parsed_comment = _("Prefix: {prefix}, website: {website} | {desc}").format(desc=parsed_comment,
		                                                                           prefix=change["logparams"]['0'],
		                                                                           website=change["logparams"]['1'])
	elif action == "interwiki/iw_delete":
		link = create_article_path("Special:Interwiki")
		embed["title"] = _("Deleted an entry in interwiki table")
		parsed_comment = _("Prefix: {prefix} | {desc}").format(desc=parsed_comment, prefix=change["logparams"]['0'])
	elif action == "contentmodel/change":
		link = create_article_path(change["title"].replace(" ", "_"))
		embed["title"] = _("Changed the content model of the page {article}").format(article=change["title"])
		parsed_comment = _("Model changed from {old} to {new}: {reason}").format(old=change["logparams"]["oldmodel"],
		                                                                         new=change["logparams"]["newmodel"],
		                                                                         reason=parsed_comment)
	elif action == "sprite/sprite":
		link = create_article_path(change["title"].replace(" ", "_"))
		embed["title"] = _("Edited the sprite for {article}").format(article=change["title"])
	elif action == "sprite/sheet":
		link = create_article_path(change["title"].replace(" ", "_"))
		embed["title"] = _("Created the sprite sheet for {article}").format(article=change["title"])
	elif action == "sprite/slice":
		link = create_article_path(change["title"].replace(" ", "_"))
		embed["title"] = _("Edited the slice for {article}").format(article=change["title"])
	elif action == "cargo/createtable":
		LinkParser.feed(change["logparams"]["0"])
		table = re.search(r"\[(.*?)\]\(<(.*?)>\)", LinkParser.new_string)
		LinkParser.new_string = ""
		link = table.group(2)
		embed["title"] = _("Created the Cargo table \"{table}\"").format(table=table.group(1))
		parsed_comment = None
	elif action == "cargo/deletetable":
		link = create_article_path("Special:CargoTables")
		embed["title"] = _("Deleted the Cargo table \"{table}\"").format(table=change["logparams"]["0"])
		parsed_comment = None
	elif action == "cargo/recreatetable":
		LinkParser.feed(change["logparams"]["0"])
		table = re.search(r"\[(.*?)\]\(<(.*?)>\)", LinkParser.new_string)
		LinkParser.new_string = ""
		link = table.group(2)
		embed["title"] = _("Recreated the Cargo table \"{table}\"").format(table=table.group(1))
		parsed_comment = None
	elif action == "cargo/replacetable":
		LinkParser.feed(change["logparams"]["0"])
		table = re.search(r"\[(.*?)\]\(<(.*?)>\)", LinkParser.new_string)
		LinkParser.new_string = ""
		link = table.group(2)
		embed["title"] = _("Replaced the Cargo table \"{table}\"").format(table=table.group(1))
		parsed_comment = None
	elif action == "managetags/create":
		link = create_article_path("Special:Tags")
		embed["title"] = _("Created a tag \"{tag}\"").format(tag=change["logparams"]["tag"])
		recent_changes.init_info()
	elif action == "managetags/delete":
		link = create_article_path("Special:Tags")
		embed["title"] = _("Deleted a tag \"{tag}\"").format(tag=change["logparams"]["tag"])
		recent_changes.init_info()
	elif action == "managetags/activate":
		link = create_article_path("Special:Tags")
		embed["title"] = _("Activated a tag \"{tag}\"").format(tag=change["logparams"]["tag"])
	elif action == "managetags/deactivate":
		link = create_article_path("Special:Tags")
		embed["title"] = _("Deactivated a tag \"{tag}\"").format(tag=change["logparams"]["tag"])
	elif action == "suppressed":
		link = create_article_path("")
		embed["title"] = _("Action has been hidden by administration.")
		embed["author"]["name"] = _("Unknown")
	else:
		logger.warning("No entry for {event} with params: {params}".format(event=action, params=change))
	embed["author"]["icon_url"] = settings["appearance"]["embed"][action]["icon"]
	embed["url"] = link
	if parsed_comment is not None:
		embed["description"] = parsed_comment
	if colornumber is None:
		if settings["appearance"]["embed"][action]["color"] is None:
			embed["color"] = random.randrange(1, 16777215)
		else:
			embed["color"] = settings["appearance"]["embed"][action]["color"]
	else:
		embed["color"] = math.floor(colornumber)
	embed["timestamp"] = change["timestamp"]
	if "tags" in change and change["tags"]:
		tag_displayname = []
		if "fields" not in embed:
			embed["fields"] = []
		for tag in change["tags"]:
			if tag in recent_changes.tags:
				if recent_changes.tags[tag] is None:
					continue  # Ignore hidden tags
				else:
					tag_displayname.append(recent_changes.tags[tag])
			else:
				tag_displayname.append(tag)
		embed["fields"].append({"name": _("Tags"), "value": ", ".join(tag_displayname)})
	logger.debug("Current params in edit action: {}".format(change))
	if categories is not None and not (len(categories["new"]) == 0 and len(categories["removed"]) == 0):
		if "fields" not in embed:
			embed["fields"] = []
		new_cat = (_("**Added**: ") + ", ".join(list(categories["new"])[0:16]) + ("\n" if len(categories["new"])<=15 else _(" and {} more\n").format(len(categories["new"])-15))) if categories["new"] else ""
		del_cat = (_("**Removed**: ") + ", ".join(list(categories["removed"])[0:16]) + ("" if len(categories["removed"])<=15 else _(" and {} more").format(len(categories["removed"])-15))) if categories["removed"] else ""
		embed["fields"].append({"name": _("Changed categories"), "value": new_cat + del_cat})
	data["embeds"].append(dict(embed))
	data['avatar_url'] = settings["avatars"]["embed"]
	formatted_embed = json.dumps(data, indent=4)
	send_to_discord(formatted_embed)


def essential_info(change, changed_categories):
	"""Prepares essential information for both embed and compact message format."""
	logger.debug(change)
	if ("actionhidden" in change or "suppressed" in change) and "suppressed" not in settings["ignored"]:  # if event is hidden using suppression
		appearance_mode("suppressed", change, "", changed_categories)
		return
	if "commenthidden" not in change:
		LinkParser.feed(change["parsedcomment"])
		parsed_comment = LinkParser.new_string
		LinkParser.new_string = ""
		parsed_comment = re.sub(r"(`|_|\*|~|{|}|\|\|)", "\\\\\\1", parsed_comment, 0)
	else:
		parsed_comment = _("~~hidden~~")
	if not parsed_comment:
		parsed_comment = None
	if change["type"] in ["edit", "new"]:
		logger.debug("List of categories in essential_info: {}".format(changed_categories))
		if "userhidden" in change:
			change["user"] = _("hidden")
		identification_string = change["type"]
	elif change["type"] == "log":
		identification_string = "{logtype}/{logaction}".format(logtype=change["logtype"], logaction=change["logaction"])
		if identification_string not in supported_logs:
			logger.warning(
				"This event is not implemented in the script. Please make an issue on the tracker attaching the following info: wiki url, time, and this information: {}".format(
					change))
			return
	elif change["type"] == "categorize":
		return
	else:
		logger.warning("This event is not implemented in the script. Please make an issue on the tracker attaching the following info: wiki url, time, and this information: {}".format(change))
		return
	if identification_string in settings["ignored"]:
		return
	appearance_mode(identification_string, change, parsed_comment, changed_categories)

def day_overview_request():
	logger.info("Fetching daily overview... This may take up to 30 seconds!")
	timestamp = (datetime.datetime.utcnow() - datetime.timedelta(hours=24)).isoformat(timespec='milliseconds')
	logger.debug("timestamp is {}".format(timestamp))
	complete = False
	result = []
	passes = 0
	continuearg = ""
	while not complete and passes < 10:
		request = recent_changes.safe_request(
			"{wiki}?action=query&format=json&list=recentchanges&rcend={timestamp}Z&rcprop=title%7Ctimestamp%7Csizes%7Cloginfo%7Cuser&rcshow=!bot&rclimit=500&rctype=edit%7Cnew%7Clog{continuearg}".format(
				wiki=WIKI_API_PATH, timestamp=timestamp, continuearg=continuearg))
		if request:
			try:
				request = request.json()
				rc = request['query']['recentchanges']
				continuearg = request["continue"]["rccontinue"] if "continue" in request else None
			except ValueError:
				logger.warning("ValueError in fetching changes")
				recent_changes.downtime_controller()
				complete = 2
			except KeyError:
				logger.warning("Wiki returned %s" % (request.json()))
				complete = 2
			else:
				result += rc
				if continuearg:
					continuearg = "&rccontinue={}".format(continuearg)
					passes += 1
					logger.debug(
						"continuing requesting next pages of recent changes with {} passes and continuearg being {}".format(
							passes, continuearg))
					time.sleep(3.0)
				else:
					complete = 1
		else:
			complete = 2
	if passes == 10:
		logger.debug("quit the loop because there been too many passes")
	return result, complete


def daily_overview_sync(edits, files, admin, changed_bytes, new_articles, unique_contributors, day_score):
	weight = storage["daily_overview"]["days_tracked"]
	if weight == 0:
		storage["daily_overview"].update({"edits": edits, "new_files": files, "admin_actions": admin, "bytes_changed": changed_bytes, "new_articles": new_articles, "unique_editors": unique_contributors, "day_score": day_score})
		edits, files, admin, changed_bytes, new_articles, unique_contributors, day_score = str(edits), str(files), str(admin), str(changed_bytes), str(new_articles), str(unique_contributors), str(day_score)
	else:
		edits_avg = misc.weighted_average(storage["daily_overview"]["edits"], weight, edits)
		edits = _("{value} (avg. {avg})").format(value=edits, avg=edits_avg)
		files_avg = misc.weighted_average(storage["daily_overview"]["new_files"], weight, files)
		files = _("{value} (avg. {avg})").format(value=files, avg=files_avg)
		admin_avg = misc.weighted_average(storage["daily_overview"]["admin_actions"], weight, admin)
		admin = _("{value} (avg. {avg})").format(value=admin, avg=admin_avg)
		changed_bytes_avg = misc.weighted_average(storage["daily_overview"]["bytes_changed"], weight, changed_bytes)
		changed_bytes = _("{value} (avg. {avg})").format(value=changed_bytes, avg=changed_bytes_avg)
		new_articles_avg = misc.weighted_average(storage["daily_overview"]["new_articles"], weight, new_articles)
		new_articles = _("{value} (avg. {avg})").format(value=new_articles, avg=new_articles_avg)
		unique_contributors_avg = misc.weighted_average(storage["daily_overview"]["unique_editors"], weight, unique_contributors)
		unique_contributors = _("{value} (avg. {avg})").format(value=unique_contributors, avg=unique_contributors_avg)
		day_score_avg = misc.weighted_average(storage["daily_overview"]["day_score"], weight, day_score)
		day_score = _("{value} (avg. {avg})").format(value=day_score, avg=day_score_avg)
		storage["daily_overview"].update({"edits": edits_avg, "new_files": files_avg, "admin_actions": admin_avg, "bytes_changed": changed_bytes_avg,
		             "new_articles": new_articles_avg, "unique_editors": unique_contributors_avg, "day_score": day_score_avg})
	storage["daily_overview"]["days_tracked"] += 1
	misc.save_datafile(storage)
	return edits, files, admin, changed_bytes, new_articles, unique_contributors, day_score

def day_overview():
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
		if not result[0]:
			if not settings["send_empty_overview"]:
				return  # no changes in this day
			else:
				embed = defaultdict(dict)
				embed["title"] = _("Daily overview")
				embed["url"] = create_article_path("Special:Statistics")
				embed["description"] = _("No activity")
				embed["color"] = settings["appearance"]["embed"]["daily_overview"]["color"]
				embed["author"]["icon_url"] = settings["appearance"]["embed"]["daily_overview"]["icon"]
				embed["author"]["name"] = settings["wikiname"]
				embed["author"]["url"] = create_article_path("")
		else:
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
			embed["url"] = create_article_path("Special:Statistics")
			embed["color"] = settings["appearance"]["embed"]["daily_overview"]["color"]
			embed["author"]["icon_url"] = settings["appearance"]["embed"]["daily_overview"]["icon"]
			embed["author"]["name"] = settings["wikiname"]
			embed["author"]["url"] = create_article_path("")
			if activity:
				active_users = []
				for user, numberu in Counter(activity).most_common(3):  # find most active users
					active_users.append(user + ngettext(" ({} action)", " ({} actions)", numberu).format(numberu))
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
			edits, files, admin, changed_bytes, new_articles, unique_contributors, overall = daily_overview_sync(edits, files, admin, changed_bytes, new_articles, len(activity), overall)
			fields = (
			(ngettext("Most active user", "Most active users", len(active_users)), ', '.join(active_users)),
			(ngettext("Most edited article", "Most edited articles", len(active_articles)), ', '.join(active_articles)),
			(_("Edits made"), edits), (_("New files"), files), (_("Admin actions"), admin),
			(_("Bytes changed"), changed_bytes), (_("New articles"), new_articles),
			(_("Unique contributors"), unique_contributors),
			(ngettext("Most active hour", "Most active hours", len(active_hours)), ', '.join(active_hours) + houramount),
			(_("Day score"), overall))
			for name, value in fields:
				embed["fields"].append({"name": name, "value": value, "inline": True})
		data = {"embeds": [dict(embed)]}
		formatted_embed = json.dumps(data, indent=4)
		send_to_discord(formatted_embed)
	else:
		logger.debug("function requesting changes for day overview returned with error code")


class Recent_Changes_Class(object):
	def __init__(self):
		self.ids = []
		self.map_ips = {}
		self.recent_id = 0
		self.downtimecredibility = 0
		self.last_downtime = 0
		self.tags = {}
		self.groups = {}
		self.streak = -1
		self.unsent_messages = []
		self.mw_messages = {}
		self.namespaces = None
		self.session = requests.Session()
		self.session.headers.update(settings["header"])
		if settings["limitrefetch"] != -1:
			self.file_id = storage["rcid"]
		else:
			self.file_id = 999999999  # such value won't cause trouble, and it will make sure no refetch happen

	@staticmethod
	def handle_mw_errors(request):
		if "errors" in request:
			logger.error(request["errors"])
			raise MWError
		return request

	def log_in(self):
		global logged_in
		# session.cookies.clear()
		if '@' not in settings["wiki_bot_login"]:
			logger.error(
				"Please provide proper nickname for login from {wiki}Special:BotPasswords".format(
					wiki=WIKI_SCRIPT_PATH))
			return
		if len(settings["wiki_bot_password"]) != 32:
			logger.error(
				"Password seems incorrect. It should be 32 characters long! Grab it from {wiki}Special:BotPasswords".format(
					wiki=WIKI_SCRIPT_PATH))
			return
		logger.info("Trying to log in to {wiki}...".format(wiki=WIKI_SCRIPT_PATH))
		try:
			response = self.handle_mw_errors(
				self.session.post(WIKI_API_PATH,
				                  data={'action': 'query', 'format': 'json', 'utf8': '', 'meta': 'tokens',
				                        'type': 'login'}))
			response = self.handle_mw_errors(
				self.session.post(WIKI_API_PATH,
				                  data={'action': 'login', 'format': 'json', 'utf8': '',
				                        'lgname': settings["wiki_bot_login"],
				                        'lgpassword': settings["wiki_bot_password"],
				                        'lgtoken': response.json()['query']['tokens']['logintoken']}))
		except ValueError:
			logger.error("Logging in have not succeeded")
			return
		except MWError:
			logger.error("Logging in have not succeeded")
			return
		try:
			if response.json()['login']['result'] == "Success":
				logger.info("Successfully logged in")
				logged_in = True
			else:
				logger.error("Logging in have not succeeded")
		except:
			logger.error("Logging in have not succeeded")

	def add_cache(self, change):
		self.ids.append(change["rcid"])
		# self.recent_id = change["rcid"]
		if len(self.ids) > settings["limitrefetch"] + 5:
			self.ids.pop(0)

	def fetch(self, amount=settings["limit"]):
		if self.unsent_messages:
			logger.info(
				"{} messages waiting to be delivered to Discord due to Discord throwing errors/no connection to Discord servers.".format(
					len(self.unsent_messages)))
			for num, item in enumerate(self.unsent_messages):
				logger.debug(
					"Trying to send a message to Discord from the queue with id of {} and content {}".format(str(num),
					                                                                                         str(item)))
				if send_to_discord_webhook(item) < 2:
					logger.debug("Sending message succeeded")
					time.sleep(2.5)
				else:
					logger.debug("Sending message failed")
					break
			else:
				self.unsent_messages = []
				logger.debug("Queue emptied, all messages delivered")
			self.unsent_messages = self.unsent_messages[num:]
			logger.debug(self.unsent_messages)
		last_check = self.fetch_changes(amount=amount)
		# If the request succeeds the last_check will be the last rcid from recentchanges query
		if last_check is not None:
			self.recent_id = last_check
		# Assigns self.recent_id the last rcid if request succeeded, otherwise set the id from the file
		if settings["limitrefetch"] != -1 and self.recent_id != self.file_id and self.recent_id != 0:  # if saving to database is disabled, don't save the recent_id
			self.file_id = self.recent_id
			storage["rcid"] = self.recent_id
			misc.save_datafile(storage)
		logger.debug("Most recent rcid is: {}".format(self.recent_id))
		return self.recent_id

	def fetch_changes(self, amount, clean=False):
		"""Fetches the :amount: of changes from the wiki.
		Returns None on error and int of rcid of latest change if succeeded"""
		global logged_in
		if len(self.ids) == 0:
			logger.debug("ids is empty, triggering clean fetch")
			clean = True
		changes = self.safe_request(
			"{wiki}?action=query&format=json&list=recentchanges{show_bots}&rcprop=title%7Credirect%7Ctimestamp%7Cids%7Cloginfo%7Cparsedcomment%7Csizes%7Cflags%7Ctags%7Cuser&rclimit={amount}&rctype=edit%7Cnew%7Clog%7Cexternal{categorize}".format(
				wiki=WIKI_API_PATH, amount=amount, categorize="%7Ccategorize" if settings["show_added_categories"] else "", show_bots="&rcshow=!bot" if settings["show_bots"] is False else ""))
		if changes:
			try:
				changes = changes.json()['query']['recentchanges']
				changes.reverse()
			except ValueError:
				logger.warning("ValueError in fetching changes")
				logger.warning("Changes URL:" + changes.url)
				self.downtime_controller()
				return None
			except KeyError:
				logger.warning("Wiki returned %s" % (changes.json()))
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
						logger.debug(
							"New event: {}".format(change["rcid"]))
						if new_events == settings["limit"]:
							if amount < 500:
								# call the function again with max limit for more results, ignore the ones in this request
								logger.debug("There were too many new events, requesting max amount of events from the wiki.")
								return self.fetch(amount=5000 if logged_in else 500)
							else:
								logger.debug(
									"There were too many new events, but the limit was high enough we don't care anymore about fetching them all.")
					if change["type"] == "categorize":
						if "commenthidden" not in change:
							if len(recent_changes.mw_messages.keys()) > 0:
								cat_title = change["title"].split(':', 1)[1]
								# I so much hate this, blame Markus for making me do this
								if change["revid"] not in categorize_events:
									categorize_events[change["revid"]] = {"new": set(), "removed": set()}
								comment_to_match = re.sub(r'<.*?a>', '', change["parsedcomment"])
								if recent_changes.mw_messages["recentchanges-page-added-to-category"] in comment_to_match or recent_changes.mw_messages["recentchanges-page-added-to-category-bundled"] in comment_to_match:
									categorize_events[change["revid"]]["new"].add(cat_title)
									logger.debug("Matched {} to added category for {}".format(cat_title, change["revid"]))
								elif recent_changes.mw_messages["recentchanges-page-removed-from-category"] in comment_to_match or recent_changes.mw_messages["recentchanges-page-removed-from-category-bundled"] in comment_to_match:
									categorize_events[change["revid"]]["removed"].add(cat_title)
									logger.debug("Matched {} to removed category for {}".format(cat_title, change["revid"]))
								else:
									logger.debug("Unknown match for category change with messages {}, {}, {}, {} and comment_to_match {}".format(recent_changes.mw_messages["recentchanges-page-added-to-category"], recent_changes.mw_messages["recentchanges-page-removed-from-category"], recent_changes.mw_messages["recentchanges-page-removed-from-category-bundled"], recent_changes.mw_messages["recentchanges-page-added-to-category-bundled"], comment_to_match))
							else:
								logger.warning("Init information not available, could not read category information. Please restart the bot.")
						else:
							logger.debug("Log entry got suppressed, ignoring entry.")
				# if change["revid"] in categorize_events:
						# 	categorize_events[change["revid"]].append(cat_title)
						# else:
						# 	logger.debug("New category '{}' for {}".format(cat_title, change["revid"]))
						# 	categorize_events[change["revid"]] = {cat_title: }
				for change in changes:
					if change["rcid"] in self.ids or change["rcid"] < self.recent_id:
						logger.debug("Change ({}) is in ids or is lower than recent_id {}".format(change["rcid"],
						                                                                           self.recent_id))
						continue
					logger.debug(self.ids)
					logger.debug(self.recent_id)
					self.add_cache(change)
					if clean and not (self.recent_id == 0 and change["rcid"] > self.file_id):
						logger.debug("Rejected {val}".format(val=change["rcid"]))
						continue
					essential_info(change, categorize_events.get(change.get("revid"), None))
				return change["rcid"]

	def safe_request(self, url):
		try:
			request = self.session.get(url, timeout=10, allow_redirects=False)
		except requests.exceptions.Timeout:
			logger.warning("Reached timeout error for request on link {url}".format(url=url))
			self.downtime_controller()
			return None
		except requests.exceptions.ConnectionError:
			logger.warning("Reached connection error for request on link {url}".format(url=url))
			self.downtime_controller()
			return None
		except requests.exceptions.ChunkedEncodingError:
			logger.warning("Detected faulty response from the web server for request on link {url}".format(url=url))
			self.downtime_controller()
			return None
		else:
			if 499 < request.status_code < 600:
				self.downtime_controller()
				return None
			elif request.status_code == 302:
				logger.critical("Redirect detected! Either the wiki given in the script settings (wiki field) is incorrect/the wiki got removed or Gamepedia is giving us the false value. Please provide the real URL to the wiki, current URL redirects to {}".format(request.next.url))
				sys.exit(0)
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
			logger.error("Failure when checking Internet connection at {time}".format(
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
			"{wiki}?action=query&format=json&uselang=content&list=tags&meta=allmessages%7Csiteinfo&utf8=1&tglimit=max&tgprop=displayname&ammessages=recentchanges-page-added-to-category%7Crecentchanges-page-removed-from-category%7Crecentchanges-page-added-to-category-bundled%7Crecentchanges-page-removed-from-category-bundled&amenableparser=1&amincludelocal=1&siprop=namespaces".format(
				wiki=WIKI_API_PATH)), "query")
		if startup_info:
			if "tags" in startup_info and "allmessages" in startup_info:
				for tag in startup_info["tags"]:
					try:
						self.tags[tag["name"]] = (BeautifulSoup(tag["displayname"], "lxml")).get_text()
					except KeyError:
						self.tags[tag["name"]] = None  # Tags with no display name are hidden and should not appear on RC as well
				for message in startup_info["allmessages"]:
					self.mw_messages[message["name"]] = message["*"]
				for key, message in self.mw_messages.items():
					if key.startswith("recentchanges-page-"):
						self.mw_messages[key] = re.sub(r'\[\[.*?\]\]', '', message)
				self.namespaces = startup_info["namespaces"]
				logger.info("Gathered information about the tags and interface messages.")
			else:
				logger.warning("Could not retrieve initial wiki information. Some features may not work correctly!")
				logger.debug(startup_info)
		else:
			logger.error("Could not retrieve initial wiki information. Possibly internet connection issue?")


recent_changes = Recent_Changes_Class()
# Set the proper formatter
if settings["appearance"]["mode"] == "embed":
	appearance_mode = embed_formatter
elif settings["appearance"]["mode"] == "compact":
	appearance_mode = compact_formatter
else:
	logger.critical("Unknown formatter!")
	sys.exit(1)

# Log in and download wiki information
prepare_paths()
try:
	if settings["wiki_bot_login"] and settings["wiki_bot_password"]:
		recent_changes.log_in()
	time.sleep(2.0)
	recent_changes.init_info()
except requests.exceptions.ConnectionError:
	logger.critical("A connection can't be established with the wiki. Exiting...")
	sys.exit(1)
time.sleep(3.0)  # this timeout is to prevent timeouts. It seems Fandom does not like our ~2-3 request in under a second
logger.info("Script started! Fetching newest changes...")
recent_changes.fetch(amount=settings["limitrefetch"] if settings["limitrefetch"] != -1 else settings["limit"])

schedule.every(settings["cooldown"]).seconds.do(recent_changes.fetch)
if 1 == 2: # additional translation strings in unreachable code
	print(_("director"), _("bot"), _("editor"), _("directors"), _("sysop"), _("bureaucrat"), _("reviewer"),
	      _("autoreview"), _("autopatrol"), _("wiki_guardian"), ngettext("second", "seconds", 1), ngettext("minute", "minutes", 1), ngettext("hour", "hours", 1), ngettext("day", "days", 1), ngettext("week", "weeks", 1), ngettext("month", "months",1), ngettext("year", "years", 1), ngettext("millennium", "millennia", 1), ngettext("decade", "decades", 1), ngettext("century", "centuries", 1))

if settings["overview"]:
	try:
		overview_time = time.strptime(settings["overview_time"], '%H:%M')
		schedule.every().day.at("{}:{}".format(str(overview_time.tm_hour).zfill(2),
	                                       str(overview_time.tm_min).zfill(2))).do(day_overview)
		del overview_time
	except schedule.ScheduleValueError:
		logger.error("Invalid time format! Currently: {}:{}".format(time.strptime(settings["overview_time"], '%H:%M').tm_hour,  time.strptime(settings["overview_time"], '%H:%M').tm_min))
	except ValueError:
		logger.error("Invalid time format! Currentely: {}. Note: It needs to be in HH:MM format.".format(settings["overview_time"]))
schedule.every().day.at("00:00").do(recent_changes.clear_cache)

if TESTING:
	logger.debug("DEBUGGING ")
	recent_changes.recent_id -= 5
	recent_changes.file_id -= 5
	recent_changes.ids = [1]
	recent_changes.fetch(amount=5)
	day_overview()
	sys.exit(0)

while 1: 
	time.sleep(1.0)
	schedule.run_pending()
