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

import ipaddress
import math
import re
import time
import logging
import datetime
import json
from urllib.parse import quote_plus, quote

from bs4 import BeautifulSoup

from src.configloader import settings
from src.misc import WIKI_SCRIPT_PATH, safe_read, \
	WIKI_API_PATH, ContentParser, profile_field_name, LinkParser, AUTO_SUPPRESSION_ENABLED
from src.api.util import link_formatter, create_article_path
from src.discord.queue import send_to_discord
from src.discord.message import DiscordMessage, DiscordMessageMetadata

if AUTO_SUPPRESSION_ENABLED:
	from src.discord.redaction import delete_messages, redact_messages

from src.i18n import rc_formatters
#from src.rc import recent_changes, pull_comment
_ = rc_formatters.gettext
ngettext = rc_formatters.ngettext

logger = logging.getLogger("rcgcdw.rc_formatters")
#from src.rcgcdw import recent_changes, ngettext, logger, profile_field_name, LinkParser, pull_comment
abusefilter_results = {"": _("None"), "warn": _("Warning issued"), "block": _("**Blocked user**"), "tag": _("Tagged the edit"), "disallow": _("Disallowed the action"), "rangeblock": _("**IP range blocked**"), "throttle": _("Throttled actions"), "blockautopromote": _("Removed autoconfirmed group"), "degroup": _("**Removed from privileged groups**")}
abusefilter_actions = {"edit": _("Edit"), "upload": _("Upload"), "move": _("Move"), "stashupload": _("Stash upload"), "delete": _("Deletion"), "createaccount": _("Account creation"), "autocreateaccount": _("Auto account creation")}

LinkParser = LinkParser()

def format_user(change, recent_changes, action):
	if "anon" in change:
		author_url = create_article_path("Special:Contributions/{user}".format(
			user=change["user"].replace(" ", "_")))  # Replace here needed in case of #75
		logger.debug("current user: {} with cache of IPs: {}".format(change["user"], recent_changes.map_ips.keys()))
		if change["user"] not in list(recent_changes.map_ips.keys()):
			contibs = safe_read(recent_changes._safe_request(
				"{wiki}?action=query&format=json&list=usercontribs&uclimit=max&ucuser={user}&ucstart={timestamp}&ucprop=".format(
					wiki=WIKI_API_PATH, user=change["user"], timestamp=change["timestamp"])), "query", "usercontribs")
			if contibs is None:
				logger.warning(
					"WARNING: Something went wrong when checking amount of contributions for given IP address")
				if settings.get("hide_ips", False):
					change["user"] = _("Unregistered user")
				change["user"] = change["user"] + "(?)"
			else:
				recent_changes.map_ips[change["user"]] = len(contibs)
				logger.debug(
					"Current params user {} and state of map_ips {}".format(change["user"], recent_changes.map_ips))
				if settings.get("hide_ips", False):
					change["user"] = _("Unregistered user")
				change["user"] = "{author} ({contribs})".format(author=change["user"], contribs=len(contibs))
		else:
			logger.debug(
				"Current params user {} and state of map_ips {}".format(change["user"], recent_changes.map_ips))
			if action in ("edit", "new"):
				recent_changes.map_ips[change["user"]] += 1
			change["user"] = "{author} ({amount})".format(author=change["user"] if settings.get("hide_ips", False) is False else _("Unregistered user"),
			                                              amount=recent_changes.map_ips[change["user"]])
	else:
		author_url = create_article_path("User:{}".format(change["user"].replace(" ", "_")))
	return change["user"], author_url


def abuse_filter_format_user(change):
	author = change["user"]
	if settings.get("hide_ips", False):
		try:
			ipaddress.ip_address(change["user"])
		except ValueError:
			pass
		else:
			author = _("Unregistered user")
	return author


def compact_abuselog_formatter(change, recent_changes):
	action = "abuselog/{}".format(change["result"])
	author_url = link_formatter(create_article_path("User:{user}".format(user=change["user"])))
	author = abuse_filter_format_user(change)
	message = _("[{author}]({author_url}) triggered *{abuse_filter}*, performing the action \"{action}\" on *[{target}]({target_url})* - action taken: {result}.").format(
		author=author, author_url=author_url, abuse_filter=change["filter"],
		action=abusefilter_actions.get(change["action"], _("Unknown")), target=change.get("title", _("Unknown")),
		target_url=link_formatter(create_article_path(change.get("title", _("Unknown")))),
		result=abusefilter_results.get(change["result"], _("Unknown")))
	send_to_discord(DiscordMessage("compact", action, settings["webhookURL"], content=message), meta=DiscordMessageMetadata("POST"))


def compact_formatter(action, change, parsed_comment, categories, recent_changes):
	request_metadata = DiscordMessageMetadata("POST", rev_id=change.get("revid", None), log_id=change.get("logid", None), page_id=change.get("pageid", None))
	if action != "suppressed":
		author_url = link_formatter(create_article_path("User:{user}".format(user=change["user"])))
		if "anon" in change:
			change["user"] = _("Unregistered user")
			author = change["user"]
		else:
			author = change["user"]
	parsed_comment = "" if parsed_comment is None else " *("+parsed_comment+")*"
	if action in ["edit", "new"]:
		edit_link = link_formatter("{wiki}index.php?title={article}&curid={pageid}&diff={diff}&oldid={oldrev}".format(
			wiki=WIKI_SCRIPT_PATH, pageid=change["pageid"], diff=change["revid"], oldrev=change["old_revid"],
			article=change["title"]))
		logger.debug(edit_link)
		edit_size = change["newlen"] - change["oldlen"]
		sign = ""
		if edit_size > 0:
			sign = "+"
		bold = ""
		if abs(edit_size) > 500:
			bold = "**"
		if change["title"].startswith("MediaWiki:Tag-"):
			pass
		if action == "edit":
			content = _("[{author}]({author_url}) edited [{article}]({edit_link}){comment} {bold}({sign}{edit_size}){bold}").format(author=author, author_url=author_url, article=change["title"], edit_link=edit_link, comment=parsed_comment, edit_size=edit_size, sign=sign, bold=bold)
		else:
			content = _("[{author}]({author_url}) created [{article}]({edit_link}){comment} {bold}({sign}{edit_size}){bold}").format(author=author, author_url=author_url, article=change["title"], edit_link=edit_link, comment=parsed_comment, edit_size=edit_size, sign=sign, bold=bold)
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
		if AUTO_SUPPRESSION_ENABLED:
			delete_messages(dict(pageid=change.get("pageid")))
	elif action == "delete/delete_redir":
		page_link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) deleted redirect by overwriting [{page}]({page_link}){comment}").format(author=author, author_url=author_url, page=change["title"], page_link=page_link,
		                                                   comment=parsed_comment)
		if AUTO_SUPPRESSION_ENABLED:
			delete_messages(dict(pageid=change.get("pageid")))
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
		user = change["title"].split(':', 1)[1]
		restriction_description = ""
		try:
			ipaddress.ip_address(user)
			link = link_formatter(create_article_path("Special:Contributions/{user}".format(user=user)))
		except ValueError:
			link = link_formatter(create_article_path(change["title"]))
		if change["logparams"]["duration"] in ["infinite", "indefinite", "infinity", "never"]:
			block_time = _("for infinity and beyond")
		else:
			english_length = re.sub(r"(\d+)", "", change["logparams"][
				"duration"])  # note that translation won't work for millenia and century yet
			english_length_num = re.sub(r"(\D+)", "", change["logparams"]["duration"])
			try:
				if "@" in english_length:
					raise ValueError
				english_length = english_length.rstrip("s").strip()
				block_time = _("for {num} {translated_length}").format(num=english_length_num,
				                                                translated_length=ngettext(english_length,
				                                                                           english_length + "s",
				                                                                           int(english_length_num)))
			except (AttributeError, ValueError):
				date_time_obj = datetime.datetime.strptime(change["logparams"]["expiry"], '%Y-%m-%dT%H:%M:%SZ')
				block_time = _("until {}").format(date_time_obj.strftime("%Y-%m-%d %H:%M:%S UTC"))
			if "sitewide" not in change["logparams"]:
				if "restrictions" in change["logparams"]:
					if "pages" in change["logparams"]["restrictions"] and change["logparams"]["restrictions"]["pages"]:
						restriction_description = _(" on pages: ")
						for page in change["logparams"]["restrictions"]["pages"]:
							restricted_pages = ["*{page}*".format(page=i["page_title"]) for i in change["logparams"]["restrictions"]["pages"]]
						restriction_description = restriction_description + ", ".join(restricted_pages)
					if "namespaces" in change["logparams"]["restrictions"] and change["logparams"]["restrictions"]["namespaces"]:
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
			"[{author}]({author_url}) blocked [{user}]({user_url}) {time}{restriction_desc}{comment}").format(author=author, author_url=author_url, user=user, time=block_time, user_url=link, restriction_desc=restriction_description, comment=parsed_comment)
	elif action == "block/reblock":
		link = link_formatter(create_article_path(change["title"]))
		user = change["title"].split(':', 1)[1]
		content = _("[{author}]({author_url}) changed block settings for [{blocked_user}]({user_url}){comment}").format(author=author, author_url=author_url, blocked_user=user, user_url=link, comment=parsed_comment)
	elif action == "block/unblock":
		link = link_formatter(create_article_path(change["title"]))
		user = change["title"].split(':', 1)[1]
		content = _("[{author}]({author_url}) unblocked [{blocked_user}]({user_url}){comment}").format(author=author, author_url=author_url, blocked_user=user, user_url=link, comment=parsed_comment)
	elif action == "curseprofile/comment-created":
		link = link_formatter(create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"])))
		target_user = change["title"].split(':', 1)[1]
		if target_user != author:
			content = _("[{author}]({author_url}) left a [comment]({comment}) on {target}'s profile".format(author=author, author_url=author_url, comment=link, target=target_user))
		else:
			content = _("[{author}]({author_url}) left a [comment]({comment}) on their own profile".format(author=author, author_url=author_url, comment=link))
	elif action == "curseprofile/comment-replied":
		link = link_formatter(create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"])))
		target_user = change["title"].split(':', 1)[1]
		if target_user != author:
			content = _(
				"[{author}]({author_url}) replied to a [comment]({comment}) on {target}'s profile".format(author=author,
				                                                                                    author_url=author_url,
				                                                                                    comment=link,
				                                                                                    target=target_user))
		else:
			content = _(
				"[{author}]({author_url}) replied to a [comment]({comment}) on their own profile".format(author=author,
				                                                                                   comment=link,
				                                                                                   author_url=author_url))
	elif action == "curseprofile/comment-edited":
		link = link_formatter(create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"])))
		target_user = change["title"].split(':', 1)[1]
		if target_user != author:
			content = _(
				"[{author}]({author_url}) edited a [comment]({comment}) on {target}'s profile".format(author=author,
				                                                                                          author_url=author_url,
				                                                                                          comment=link,
				                                                                                          target=target_user))
		else:
			content = _(
				"[{author}]({author_url}) edited a [comment]({comment}) on their own profile".format(author=author,
				                                                                                         comment=link,
				                                                                                         author_url=author_url))
	elif action == "curseprofile/comment-purged":
		target_user = change["title"].split(':', 1)[1]
		if target_user != author:
			content = _("[{author}]({author_url}) purged a comment on {target}'s profile".format(author=author, author_url=author_url,target=target_user))
		else:
			content = _("[{author}]({author_url}) purged a comment on their own profile".format(author=author, author_url=author_url))
	elif action == "curseprofile/comment-deleted":
		if "4:comment_id" in change["logparams"]:
			link = link_formatter(create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"])))
		else:
			link = link_formatter(create_article_path(change["title"]))
		target_user = change["title"].split(':', 1)[1]
		if target_user != author:
			content = _("[{author}]({author_url}) deleted a [comment]({comment}) on {target}'s profile".format(author=author,author_url=author_url, comment=link, target=target_user))
		else:
			content = _("[{author}]({author_url}) deleted a [comment]({comment}) on their own profile".format(author=author, author_url=author_url, comment=link))
	elif action == "curseprofile/profile-edited":
		target_user = change["title"].split(':', 1)[1]
		link = link_formatter(create_article_path("UserProfile:{user}".format(user=target_user)))
		if target_user != author:
			content = _("[{author}]({author_url}) edited the {field} on [{target}]({target_url})'s profile. *({desc})*").format(author=author,
				                                                                author_url=author_url,
				                                                                target=target_user,
				                                                                target_url=link,
				                                                                field=profile_field_name(change["logparams"]['4:section'], False),
				                                                                desc=BeautifulSoup(change["parsedcomment"], "lxml").get_text())
		else:
			content = _("[{author}]({author_url}) edited the {field} on [their own]({target_url}) profile. *({desc})*").format(
				author=author,
				author_url=author_url,
				target_url=link,
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
			content = _("[{author}]({author_url}) changed group membership for [{target}]({target_url}) from {old_groups} to {new_groups}{comment}").format(author=author, author_url=author_url, target=change["title"].split(":")[1], target_url=link, old_groups=", ".join(old_groups), new_groups=', '.join(new_groups), comment=parsed_comment)
		else:
			content = _("{author} autopromoted [{target}]({target_url}) from {old_groups} to {new_groups}{comment}").format(
				author=_("System"), author_url=author_url, target=change["title"].split(":")[1], target_url=link,
				old_groups=", ".join(old_groups), new_groups=', '.join(new_groups),
				comment=parsed_comment)
	elif action == "protect/protect":
		link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) protected [{article}]({article_url}) with the following settings: {settings}{comment}").format(author=author, author_url=author_url,
		                                                                                                                                     article=change["title"], article_url=link,
		                                                                                                                                     settings=change["logparams"].get("description", "")+(_(" [cascading]") if "cascade" in change["logparams"] else ""),
		                                                                                                                                     comment=parsed_comment)
	elif action == "protect/modify":
		link = link_formatter(create_article_path(change["title"]))
		content = _(
			"[{author}]({author_url}) modified protection settings of [{article}]({article_url}) to: {settings}{comment}").format(
			author=author, author_url=author_url,
			article=change["title"], article_url=link,
			settings=change["logparams"].get("description", "") + (_(" [cascading]") if "cascade" in change["logparams"] else ""),
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
		if AUTO_SUPPRESSION_ENABLED:
			try:
				logparams = change["logparams"]
				pageid = change["pageid"]
			except KeyError:
				pass
			else:
				delete_messages(dict(pageid=pageid))
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
		if AUTO_SUPPRESSION_ENABLED:
			try:
				logparams = change["logparams"]
			except KeyError:
				pass
			else:
				for revid in logparams.get("ids", []):
					delete_messages(dict(revid=revid))
	elif action == "import/interwiki":
		link = link_formatter(create_article_path(change["title"]))
		source_link = link_formatter(create_article_path(change["logparams"]["interwiki_title"]))
		content = ngettext("[{author}]({author_url}) imported [{article}]({article_url}) with {count} revision from [{source}]({source_url}){comment}",
		                          "[{author}]({author_url}) imported [{article}]({article_url}) with {count} revisions from [{source}]({source_url}){comment}", change["logparams"]["count"]).format(
			author=author, author_url=author_url, article=change["title"], article_url=link, count=change["logparams"]["count"], source=change["logparams"]["interwiki_title"], source_url=source_link, comment=parsed_comment)
	elif action == "abusefilter/modify":
		link = link_formatter(create_article_path("Special:AbuseFilter/history/{number}/diff/prev/{historyid}".format(number=change["logparams"]['newId'], historyid=change["logparams"]["historyId"])))
		content = _("[{author}]({author_url}) edited abuse filter [number {number}]({filter_url})").format(author=author, author_url=author_url, number=change["logparams"]['newId'], filter_url=link)
	elif action == "abusefilter/create":
		link = link_formatter(
			create_article_path("Special:AbuseFilter/{number}".format(number=change["logparams"]['newId'])))
		content = _("[{author}]({author_url}) created abuse filter [number {number}]({filter_url})").format(author=author, author_url=author_url, number=change["logparams"]['newId'], filter_url=link)
	elif action == "merge/merge":
		link = link_formatter(create_article_path(change["title"]))
		link_dest = link_formatter(create_article_path(change["logparams"]["dest_title"]))
		content = _("[{author}]({author_url}) merged revision histories of [{article}]({article_url}) into [{dest}]({dest_url}){comment}").format(author=author, author_url=author_url, article=change["title"], article_url=link, dest_url=link_dest,
		                                                                                dest=change["logparams"]["dest_title"], comment=parsed_comment)
	elif action == "newusers/autocreate":
		content = _("Account [{author}]({author_url}) was created automatically").format(author=author, author_url=author_url)
	elif action == "newusers/create":
		content = _("Account [{author}]({author_url}) was created").format(author=author, author_url=author_url)
	elif action == "newusers/create2":
		link = link_formatter(create_article_path(change["title"]))
		content = _("Account [{article}]({article_url}) was created by [{author}]({author_url}){comment}").format(article=change["title"], article_url=link, author=author, author_url=author_url, comment=parsed_comment)
	elif action == "newusers/byemail":
		link = link_formatter(create_article_path(change["title"]))
		content = _("Account [{article}]({article_url}) was created by [{author}]({author_url}) and password was sent by email{comment}").format(article=change["title"], article_url=link, author=author, author_url=author_url, comment=parsed_comment)
	elif action == "newusers/newusers":
		content = _("Account [{author}]({author_url}) was created").format(author=author, author_url=author_url)
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
	elif action == "contentmodel/new":
		link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) created the page [{article}]({article_url}) using a non-default content model {new}{comment}").format(author=author, author_url=author_url, article=change["title"], article_url=link, new=change["logparams"]["newmodel"], comment=parsed_comment)
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
		link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) created the [tag]({tag_url}) \"{tag}\"{comment}").format(author=author, author_url=author_url, tag=change["logparams"]["tag"], tag_url=link, comment=parsed_comment)
		recent_changes.init_info()
	elif action == "managetags/delete":
		link = link_formatter(create_article_path(change["title"]))
		if change["logparams"]["count"] == 0:
			content = _("[{author}]({author_url}) deleted the [tag]({tag_url}) \"{tag}\"{comment}").format(author=author, author_url=author_url, tag=change["logparams"]["tag"], tag_url=link, comment=parsed_comment)
		else:
			content = ngettext("[{author}]({author_url}) deleted the [tag]({tag_url}) \"{tag}\" and removed it from {count} revision or log entry{comment}",
		                       "[{author}]({author_url}) deleted the [tag]({tag_url}) \"{tag}\" and removed it from {count} revisions and/or log entries{comment}",
		                       change["logparams"]["count"]).format(author=author, author_url=author_url, tag=change["logparams"]["tag"], tag_url=link, count=change["logparams"]["count"], comment=parsed_comment)
		recent_changes.init_info()
	elif action == "managetags/activate":
		link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) activated the [tag]({tag_url}) \"{tag}\"{comment}").format(author=author, author_url=author_url, tag=change["logparams"]["tag"], tag_url=link, comment=parsed_comment)
	elif action == "managetags/deactivate":
		link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) deactivated the [tag]({tag_url}) \"{tag}\"{comment}").format(author=author, author_url=author_url, tag=change["logparams"]["tag"], tag_url=link, comment=parsed_comment)
	elif action == "managewiki/settings":  # Miraheze's ManageWiki extension https://github.com/miraheze/ManageWiki
		content = _("[{author}]({author_url}) changed wiki settings{reason}".format(author=author, author_url=author_url, reason=parsed_comment))
	elif action == "managewiki/delete":
		content = _("[{author}]({author_url}) deleted a wiki *{wiki_name}*{comment}").format(author=author, author_url=author_url,
		                                                                                              wiki_name=change["logparams"].get("wiki", _("Unknown")), comment=parsed_comment)
	elif action == "managewiki/lock":
		content = _("[{author}]({author_url}) locked a wiki *{wiki_name}*{comment}").format(
			author=author, author_url=author_url, wiki_name=change["logparams"].get("wiki", _("Unknown")), comment=parsed_comment)
	elif action == "managewiki/namespaces":
		content = _("[{author}]({author_url}) modified namespace *{namespace_name}* on *{wiki_name}*{comment}").format(
			author=author, author_url=author_url, namespace_name=change["logparams"].get("namespace", _("Unknown")),
		    wiki_name=change["logparams"].get("wiki", _("Unknown")), comment=parsed_comment)
	elif action == "managewiki/namespaces-delete":
		content = _(
			"[{author}]({author_url}) deleted a namespace *{namespace_name}* on *{wiki_name}*{comment}").format(
			author=author, author_url=author_url,
			namespace_name=change["logparams"].get("namespace", _("Unknown")),
			wiki_name=change["logparams"].get("wiki", _("Unknown")), comment=parsed_comment)
	elif action == "managewiki/rights":
		group_name = change["title"].split("/permissions/", 1)[1]
		content = _("[{author}]({author_url}) modified user group *{group_name}*{comment}").format(
			author=author, author_url=author_url, group_name=group_name, comment=parsed_comment
		)
	elif action == "managewiki/undelete":
		content = _("[{author}]({author_url}) undeleted a wiki *{wiki_name}*{comment}").format(
			author=author, author_url=author_url, wiki_name=change["logparams"].get("wiki", _("Unknown")), comment=parsed_comment
		)
	elif action == "managewiki/unlock":
		content = _("[{author}]({author_url}) unlocked a wiki *{wiki_name}*{comment}").format(
			author=author, author_url=author_url, wiki_name=change["logparams"].get("wiki", _("Unknown")),
			comment=parsed_comment
		)
	elif action == "datadump/generate":
		content = _("[{author}]({author_url}) generated *{file}* dump{comment}").format(
			author=author, author_url=author_url, file=change["logparams"]["filename"],
			comment=parsed_comment
		)
	elif action == "datadump/delete":
		content = _("[{author}]({author_url}) deleted *{file}* dump{comment}").format(
			author=author, author_url=author_url, file=change["logparams"]["filename"],
			comment=parsed_comment
		)
	elif action == "pagetranslation/mark":
		link = create_article_path(change["title"])
		if "?" in link:
			link = link + "&oldid={}".format(change["logparams"]["revision"])
		else:
			link = link + "?oldid={}".format(change["logparams"]["revision"])
		link = link_formatter(link)
		content = _("[{author}]({author_url}) marked [{article}]({article_url}) for translation{comment}").format(
			author=author, author_url=author_url,
			article=change["title"], article_url=link,
			comment=parsed_comment
		)
	elif action == "pagetranslation/unmark":
		link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) removed [{article}]({article_url}) from the translation system{comment}").format(
			author=author, author_url=author_url,
			article=change["title"], article_url=link,
			comment=parsed_comment
		)
	elif action == "pagetranslation/moveok":
		link = link_formatter(create_article_path(change["logparams"]["target"]))
		content = _("[{author}]({author_url}) completed moving translation pages from *{article}* to [{target}]({target_url}){comment}").format(
			author=author, author_url=author_url,
			article=change["title"], target=change["logparams"]["target"], target_url=link,
			comment=parsed_comment
		)
	elif action == "pagetranslation/movenok":
		link = link_formatter(create_article_path(change["title"]))
		target_url = link_formatter(create_article_path(change["logparams"]["target"]))
		content = _("[{author}]({author_url}) encountered a problem while moving [{article}]({article_url}) to [{target}]({target_url}){comment}").format(
			author=author, author_url=author_url,
			article=change["title"], article_url=link,
			target=change["logparams"]["target"], target_url=target_url,
			comment=parsed_comment
		)
	elif action == "pagetranslation/deletefok":
		link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) completed deletion of translatable page [{article}]({article_url}){comment}").format(
			author=author, author_url=author_url,
			article=change["title"], article_url=link,
			comment=parsed_comment
		)
	elif action == "pagetranslation/deletefnok":
		link = link_formatter(create_article_path(change["title"]))
		target_url = link_formatter(create_article_path(change["logparams"]["target"]))
		content = _("[{author}]({author_url}) failed to delete [{article}]({article_url}) which belongs to translatable page [{target}]({target_url}){comment}").format(
			author=author, author_url=author_url,
			article=change["title"], article_url=link,
			target=change["logparams"]["target"], target_url=target_url,
			comment=parsed_comment
		)
	elif action == "pagetranslation/deletelok":
		link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) completed deletion of translation page [{article}]({article_url}){comment}").format(
			author=author, author_url=author_url,
			article=change["title"], article_url=link,
			comment=parsed_comment
		)
	elif action == "pagetranslation/deletelnok":
		link = link_formatter(create_article_path(change["title"]))
		target_url = link_formatter(create_article_path(change["logparams"]["target"]))
		content = _("[{author}]({author_url}) failed to delete [{article}]({article_url}) which belongs to translation page [{target}]({target_url}){comment}").format(
			author=author, author_url=author_url,
			article=change["title"], article_url=link,
			target=change["logparams"]["target"], target_url=target_url,
			comment=parsed_comment
		)
	elif action == "pagetranslation/encourage":
		link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) encouraged translation of [{article}]({article_url}){comment}").format(
			author=author, author_url=author_url,
			article=change["title"], article_url=link,
			comment=parsed_comment
		)
	elif action == "pagetranslation/discourage":
		link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) discouraged translation of [{article}]({article_url}){comment}").format(
			author=author, author_url=author_url,
			article=change["title"], article_url=link,
			comment=parsed_comment
		)
	elif action == "pagetranslation/prioritylanguages":
		link = link_formatter(create_article_path(change["title"]))
		if "languages" in change["logparams"]:
			languages = "`, `".join(change["logparams"]["languages"].split(","))
			if change["logparams"]["force"] == "on":
				content = _("[{author}]({author_url}) limited languages for [{article}]({article_url}) to `{languages}`{comment}").format(
					author=author, author_url=author_url,
					article=change["title"], article_url=link,
					languages=languages, comment=parsed_comment
				)
			else:
				content = _("[{author}]({author_url}) set the priority languages for [{article}]({article_url}) to `{languages}`{comment}").format(
					author=author, author_url=author_url,
					article=change["title"], article_url=link,
					languages=languages, comment=parsed_comment
				)
		else:
			content = _("[{author}]({author_url}) removed priority languages from [{article}]({article_url}){comment}").format(
				author=author, author_url=author_url,
				article=change["title"], article_url=link,
				comment=parsed_comment
			)
	elif action == "pagetranslation/associate":
		link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) added translatable page [{article}]({article_url}) to aggregate group \"{group}\"{comment}").format(
			author=author, author_url=author_url,
			article=change["title"], article_url=link,
			group=change["logparams"]["aggregategroup"], comment=parsed_comment
		)
	elif action == "pagetranslation/dissociate":
		link = link_formatter(create_article_path(change["title"]))
		content = _("[{author}]({author_url}) removed translatable page [{article}]({article_url}) from aggregate group \"{group}\"{comment}").format(
			author=author, author_url=author_url,
			article=change["title"], article_url=link,
			group=change["logparams"]["aggregategroup"], comment=parsed_comment
		)
	elif action == "translationreview/message":
		link = create_article_path(change["title"])
		if "?" in link:
			link = link + "&oldid={}".format(change["logparams"]["revision"])
		else:
			link = link + "?oldid={}".format(change["logparams"]["revision"])
		link = link_formatter(link)
		content = _("[{author}]({author_url}) reviewed translation [{article}]({article_url}){comment}").format(
			author=author, author_url=author_url,
			article=change["title"], article_url=link,
			comment=parsed_comment
		)
	elif action == "translationreview/group":
		link = link_formatter(create_article_path(change["title"]))
		if "old-state" in change["logparams"]:
			content = _("[{author}]({author_url}) changed the state of `{language}` translations of [{article}]({article_url}) from `{old_state}` to `{new_state}`{comment}").format(
				author=author, author_url=author_url, language=change["logparams"]["language"],
				article=change["logparams"]["group-label"], article_url=link,
				old_state=change["logparams"]["old-state"], new_state=change["logparams"]["new-state"],
				comment=parsed_comment
			)
		else:
			content = _("[{author}]({author_url}) changed the state of `{language}` translations of [{article}]({article_url}) to `{new_state}`{comment}").format(
				author=author, author_url=author_url, language=change["logparams"]["language"],
				article=change["logparams"]["group-label"], article_url=link,
				new_state=change["logparams"]["new-state"], comment=parsed_comment
			)
	elif action == "pagelang/pagelang":
		link = link_formatter(create_article_path(change["title"]))
		old_lang = "`{}`".format(change["logparams"]["oldlanguage"])
		if change["logparams"]["oldlanguage"][-5:] == "[def]":
			old_lang = "`{}` {}".format(change["logparams"]["oldlanguage"][:-5], _("(default)"))
		new_lang = "`{}`".format(change["logparams"]["newlanguage"])
		if change["logparams"]["newlanguage"][-5:] == "[def]":
			new_lang = "`{}` {}".format(change["logparams"]["oldlanguage"][:-5], _("(default)"))
		content = _("[{author}]({author_url}) changed the language of [{article}]({article_url}) from {old_lang} to {new_lang}{comment}").format(
			author=author, author_url=author_url,
			article=change["title"], article_url=link,
			old_lang=old_lang, new_lang=new_lang, comment=parsed_comment
		)
	elif action == "renameuser/renameuser":
		link = link_formatter(create_article_path("User:"+change["logparams"]["newuser"]))
		edits = change["logparams"]["edits"]
		if edits > 0:
			content = ngettext("[{author}]({author_url}) renamed user *{old_name}* with {edits} edit to [{new_name}]({link}){comment}",
			                          "[{author}]({author_url}) renamed user *{old_name}* with {edits} edits to [{new_name}]({link}){comment}", edits).format(
				author=author, author_url=author_url, old_name=change["logparams"]["olduser"], edits=edits, new_name=change["logparams"]["newuser"], link=link, comment=parsed_comment
			)
		else:
			content = _("[{author}]({author_url}) renamed user *{old_name}* to [{new_name}]({link}){comment}").format(
				author=author, author_url=author_url, old_name=change["logparams"]["olduser"], new_name=change["logparams"]["newuser"], link=link, comment=parsed_comment
			)
	elif action == "suppressed":
		content = _("An action has been hidden by administration.")
	else:
		logger.warning("No entry for {event} with params: {params}".format(event=action, params=change))
		if not settings.get("support", None):
			return
		else:
			content = _(
				"Unknown event `{event}` by [{author}]({author_url}), report it on the [support server](<{support}>).").format(
				event=action, author=author, author_url=author_url, support=settings["support"])
			action = "unknown"
	send_to_discord(DiscordMessage("compact", action, settings["webhookURL"], content=content), meta=request_metadata)

def embed_abuselog_formatter(change, recent_changes):
	action = "abuselog/{}".format(change["result"])
	embed = DiscordMessage("embed", action, settings["webhookURL"])
	author = abuse_filter_format_user(change)
	embed["title"] = _("{user} triggered \"{abuse_filter}\"").format(user=author, abuse_filter=change["filter"])
	embed.add_field(_("Performed"), abusefilter_actions.get(change["action"], _("Unknown")))
	embed.add_field(_("Action taken"), abusefilter_results.get(change["result"], _("Unknown")))
	embed.add_field(_("Title"), change.get("title", _("Unknown")))
	embed.finish_embed()
	send_to_discord(embed, meta=DiscordMessageMetadata("POST"))


def embed_formatter(action, change, parsed_comment, categories, recent_changes):
	embed = DiscordMessage("embed", action, settings["webhookURL"])
	request_metadata = DiscordMessageMetadata("POST", rev_id=change.get("revid", None), log_id=change.get("logid", None), page_id=change.get("pageid", None))
	if parsed_comment is None:
		parsed_comment = _("No description provided")
	if action != "suppressed":
		change["user"], author_url = format_user(change, recent_changes, action)
		embed.set_author(change["user"], author_url)
	if action in ("edit", "new"):  # edit or new page

	elif action in ("upload/overwrite", "upload/upload", "upload/revert"):  # sending files

	elif action == "delete/delete":

	elif action == "delete/delete_redir":
		link = create_article_path(change["title"])
		embed["title"] = _("Deleted redirect {article} by overwriting").format(article=change["title"])
		if AUTO_SUPPRESSION_ENABLED:
			delete_messages(dict(pageid=change.get("pageid")))
	elif action == "move/move":
		link = create_article_path(change["logparams"]['target_title'])
		parsed_comment = "{supress}. {desc}".format(desc=parsed_comment,
		                                            supress=_("No redirect has been made") if "suppressredirect" in change["logparams"] else _(
			                                            "A redirect has been made"))
		embed["title"] = _("Moved {redirect}{article} to {target}").format(redirect="⤷ " if "redirect" in change else "", article=change["title"], target=change["logparams"]['target_title'])
	elif action == "move/move_redir":
		link = create_article_path(change["logparams"]["target_title"])
		embed["title"] = _("Moved {redirect}{article} to {title} over redirect").format(redirect="⤷ " if "redirect" in change else "", article=change["title"],
		                                                                      title=change["logparams"]["target_title"])
	elif action == "protect/move_prot":
		link = create_article_path(change["logparams"]["oldtitle_title"])
		embed["title"] = _("Moved protection settings from {redirect}{article} to {title}").format(redirect="⤷ " if "redirect" in change else "", article=change["logparams"]["oldtitle_title"],
		                                                                                 title=change["title"])
	elif action == "block/block":
		user = change["title"].split(':', 1)[1]
		try:
			ipaddress.ip_address(user)
			link = create_article_path("Special:Contributions/{user}".format(user=user))
		except ValueError:
			link = create_article_path(change["title"])
		if change["logparams"]["duration"] in ["infinite", "indefinite", "infinity", "never"]:
			block_time = _("for infinity and beyond")
		else:
			english_length = re.sub(r"(\d+)", "", change["logparams"]["duration"])  # note that translation won't work for millenia and century yet
			english_length_num = re.sub(r"(\D+)", "", change["logparams"]["duration"])
			try:
				if "@" in english_length:
					raise ValueError
				english_length = english_length.rstrip("s").strip()
				block_time = _("for {num} {translated_length}").format(num=english_length_num, translated_length=ngettext(english_length, english_length + "s", int(english_length_num)))
			except (AttributeError, ValueError):
				if "expiry" in change["logparams"]:
					date_time_obj = datetime.datetime.strptime(change["logparams"]["expiry"], '%Y-%m-%dT%H:%M:%SZ')
					block_time = _("until {}").format(date_time_obj.strftime("%Y-%m-%d %H:%M:%S UTC"))
				else:
					block_time = _("unknown expiry time")  # THIS IS HERE JUST TEMPORARY AS A HOT FIX TO #157, will be changed with release of 1.13
		if "sitewide" not in change["logparams"]:
			restriction_description = ""
			if "restrictions" in change["logparams"]:
				if "pages" in change["logparams"]["restrictions"] and change["logparams"]["restrictions"]["pages"]:
					restriction_description = _("Blocked from editing the following pages: ")
					for page in change["logparams"]["restrictions"]["pages"]:
						restricted_pages = ["*"+i["page_title"]+"*" for i in change["logparams"]["restrictions"]["pages"]]
					restriction_description = restriction_description + ", ".join(restricted_pages)
				if "namespaces" in change["logparams"]["restrictions"] and change["logparams"]["restrictions"]["namespaces"]:
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
				embed.add_field(_("Partial block details"), restriction_description, inline=True)
		embed["title"] = _("Blocked {blocked_user} {time}").format(blocked_user=user, time=block_time)
	elif action == "block/reblock":
		link = create_article_path(change["title"])
		user = change["title"].split(':', 1)[1]
		embed["title"] = _("Changed block settings for {blocked_user}").format(blocked_user=user)
	elif action == "block/unblock":
		link = create_article_path(change["title"])
		user = change["title"].split(':', 1)[1]
		embed["title"] = _("Unblocked {blocked_user}").format(blocked_user=user)
	elif action == "curseprofile/comment-created":
		if settings["appearance"]["embed"]["show_edit_changes"]:
			parsed_comment = recent_changes.pull_comment(change["logparams"]["4:comment_id"])
		link = create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"]))
		target_user = change["title"].split(':', 1)[1]
		if target_user != change["user"]:
			embed["title"] = _("Left a comment on {target}'s profile").format(target=target_user)
		else:
			embed["title"] = _("Left a comment on their own profile")
	elif action == "curseprofile/comment-replied":
		if settings["appearance"]["embed"]["show_edit_changes"]:
			parsed_comment = recent_changes.pull_comment(change["logparams"]["4:comment_id"])
		link = create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"]))
		target_user = change["title"].split(':', 1)[1]
		if target_user != change["user"]:
			embed["title"] = _("Replied to a comment on {target}'s profile").format(target=target_user)
		else:
			embed["title"] = _("Replied to a comment on their own profile")
	elif action == "curseprofile/comment-edited":
		if settings["appearance"]["embed"]["show_edit_changes"]:
			parsed_comment = recent_changes.pull_comment(change["logparams"]["4:comment_id"])
		link = create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"]))
		target_user = change["title"].split(':', 1)[1]
		if target_user != change["user"]:
			embed["title"] = _("Edited a comment on {target}'s profile").format(target=target_user)
		else:
			embed["title"] = _("Edited a comment on their own profile")
	elif action == "curseprofile/profile-edited":
		target_user = change["title"].split(':', 1)[1]
		link = create_article_path("UserProfile:{target}".format(target=target_user))
		if target_user != change["user"]:
			embed["title"] = _("Edited {target}'s profile").format(target=target_user)
		else:
			embed["title"] = _("Edited their own profile")
		if not change["parsedcomment"]:  # If the field is empty
			parsed_comment = _("Cleared the {field} field").format(field=profile_field_name(change["logparams"]['4:section'], True))
		else:
			parsed_comment = _("{field} field changed to: {desc}").format(field=profile_field_name(change["logparams"]['4:section'], True), desc=BeautifulSoup(change["parsedcomment"], "lxml").get_text())
	elif action == "curseprofile/comment-purged":
		link = create_article_path(change["title"])
		target_user = change["title"].split(':', 1)[1]
		if target_user != change["user"]:
			embed["title"] = _("Purged a comment on {target}'s profile").format(target=target_user)
		else:
			embed["title"] = _("Purged a comment on their own profile")
	elif action == "curseprofile/comment-deleted":
		if "4:comment_id" in change["logparams"]:
			link = create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"]))
		else:
			link = create_article_path(change["title"])
		target_user = change["title"].split(':', 1)[1]
		if target_user != change["user"]:
			embed["title"] = _("Deleted a comment on {target}'s profile").format(target=target_user)
		else:
			embed["title"] = _("Deleted a comment on their own profile")
	elif action in ("rights/rights", "rights/autopromote"):
		link = create_article_path("User:{}".format(change["title"].split(":")[1]))
		if action == "rights/rights":
			embed["title"] = _("Changed group membership for {target}").format(target=change["title"].split(":")[1])
		else:
			author_url = ""
			embed.set_author(_("System"), author_url)
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
		link = create_article_path(change["title"])
		embed["title"] = _("Protected {target}").format(target=change["title"])
		parsed_comment = "{settings}{cascade} | {reason}".format(settings=change["logparams"].get("description", ""),
		                                                         cascade=_(" [cascading]") if "cascade" in change["logparams"] else "",
		                                                         reason=parsed_comment)
	elif action == "protect/modify":
		link = create_article_path(change["title"])
		embed["title"] = _("Changed protection level for {article}").format(article=change["title"])
		parsed_comment = "{settings}{cascade} | {reason}".format(settings=change["logparams"].get("description", ""),
		                                                         cascade=_(" [cascading]") if "cascade" in change["logparams"] else "",
		                                                         reason=parsed_comment)
	elif action == "protect/unprotect":
		link = create_article_path(change["title"])
		embed["title"] = _("Removed protection from {article}").format(article=change["title"])
	elif action == "delete/revision":
		amount = len(change["logparams"]["ids"])
		link = create_article_path(change["title"])
		embed["title"] = ngettext("Changed visibility of revision on page {article} ",
		                          "Changed visibility of {amount} revisions on page {article} ", amount).format(
			article=change["title"], amount=amount)
		if AUTO_SUPPRESSION_ENABLED:
			try:
				logparams = change["logparams"]
			except KeyError:
				pass
			else:
				redact_messages(logparams.get("ids", []), 0, logparams.get("new", {}))
	elif action == "import/upload":
		link = create_article_path(change["title"])
		embed["title"] = ngettext("Imported {article} with {count} revision",
		                          "Imported {article} with {count} revisions", change["logparams"]["count"]).format(
			article=change["title"], count=change["logparams"]["count"])
	elif action == "delete/restore":
		link = create_article_path(change["title"])
		embed["title"] = _("Restored {article}").format(article=change["title"])
	elif action == "delete/event":
		link = create_article_path("Special:RecentChanges")
		embed["title"] = _("Changed visibility of log events")
		if AUTO_SUPPRESSION_ENABLED:
			try:
				logparams = change["logparams"]
			except KeyError:
				pass
			else:
				redact_messages(logparams.get("ids", []), 1, logparams.get("new", {}))
	elif action == "import/interwiki":
		link = create_article_path(change["title"])
		embed["title"] = ngettext("Imported {article} with {count} revision from \"{source}\"",
		                          "Imported {article} with {count} revisions from \"{source}\"", change["logparams"]["count"]).format(
			article=change["title"], count=change["logparams"]["count"], source=change["logparams"]["interwiki_title"])
	elif action == "abusefilter/modify":
		link = create_article_path("Special:AbuseFilter/history/{number}/diff/prev/{historyid}".format(number=change["logparams"]['newId'], historyid=change["logparams"]["historyId"]))
		embed["title"] = _("Edited abuse filter number {number}").format(number=change["logparams"]['newId'])
	elif action == "abusefilter/create":
		link = create_article_path("Special:AbuseFilter/{number}".format(number=change["logparams"]['newId']))
		embed["title"] = _("Created abuse filter number {number}").format(number=change["logparams"]['newId'])
	elif action == "merge/merge":
		link = create_article_path(change["title"])
		embed["title"] = _("Merged revision histories of {article} into {dest}").format(article=change["title"],
		                                                                                dest=change["logparams"]["dest_title"])
	elif action == "newusers/autocreate":
		link = create_article_path(change["title"])
		embed["title"] = _("Created account automatically")
	elif action == "newusers/create":
		link = create_article_path(change["title"])
		embed["title"] = _("Created account")
	elif action == "newusers/create2":
		link = create_article_path(change["title"])
		embed["title"] = _("Created account {article}").format(article=change["title"])
	elif action == "newusers/byemail":
		link = create_article_path(change["title"])
		embed["title"] = _("Created account {article} and password was sent by email").format(article=change["title"])
	elif action == "newusers/newusers":
		link = author_url
		embed["title"] = _("Created account")
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
		link = create_article_path(change["title"])
		embed["title"] = _("Changed the content model of the page {article}").format(article=change["title"])
		parsed_comment = _("Model changed from {old} to {new}: {reason}").format(old=change["logparams"]["oldmodel"],
		                                                                         new=change["logparams"]["newmodel"],
		                                                                         reason=parsed_comment)
	elif action == "contentmodel/new":
		link = create_article_path(change["title"])
		embed["title"] = _("Created the page {article} using a non-default content model").format(article=change["title"])
		parsed_comment = _("Created with model {new}: {reason}").format(new=change["logparams"]["newmodel"], reason=parsed_comment)
	elif action == "sprite/sprite":
		link = create_article_path(change["title"])
		embed["title"] = _("Edited the sprite for {article}").format(article=change["title"])
	elif action == "sprite/sheet":
		link = create_article_path(change["title"])
		embed["title"] = _("Created the sprite sheet for {article}").format(article=change["title"])
	elif action == "sprite/slice":
		link = create_article_path(change["title"])
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
		link = create_article_path(change["title"])
		embed["title"] = _("Created the tag \"{tag}\"").format(tag=change["logparams"]["tag"])
		recent_changes.init_info()
	elif action == "managetags/delete":
		link = create_article_path(change["title"])
		embed["title"] = _("Deleted the tag \"{tag}\"").format(tag=change["logparams"]["tag"])
		if change["logparams"]["count"] > 0:
			embed.add_field(_('Removed from'), ngettext("{} revision or log entry", "{} revisions and/or log entries", change["logparams"]["count"]).format(change["logparams"]["count"]))
		recent_changes.init_info()
	elif action == "managetags/activate":
		link = create_article_path(change["title"])
		embed["title"] = _("Activated the tag \"{tag}\"").format(tag=change["logparams"]["tag"])
	elif action == "managetags/deactivate":
		link = create_article_path(change["title"])
		embed["title"] = _("Deactivated the tag \"{tag}\"").format(tag=change["logparams"]["tag"])
	elif action == "managewiki/settings":  # Miraheze's ManageWiki extension https://github.com/miraheze/ManageWiki
		link = create_article_path(change["title"])
		embed["title"] = _("Changed wiki settings")
		if change["logparams"].get("changes", ""):
			embed.add_field("Setting", change["logparams"].get("changes"))
	elif action == "managewiki/delete":
		embed["title"] = _("Deleted a \"{wiki}\" wiki").format(wiki=change["logparams"].get("wiki", _("Unknown")))
		link = create_article_path(change["title"])
	elif action == "managewiki/lock":
		embed["title"] = _("Locked a \"{wiki}\" wiki").format(wiki=change["logparams"].get("wiki", _("Unknown")))
		link = create_article_path(change["title"])
	elif action == "managewiki/namespaces":
		embed["title"] = _("Modified \"{namespace_name}\" namespace").format(namespace_name=change["logparams"].get("namespace", _("Unknown")))
		link = create_article_path(change["title"])
		embed.add_field(_('Wiki'), change["logparams"].get("wiki", _("Unknown")))
	elif action == "managewiki/namespaces-delete":
		embed["title"] = _("Deleted a \"{namespace_name}\" namespace").format(
				namespace_name=change["logparams"].get("namespace", _("Unknown")))
		link = create_article_path(change["title"])
		embed.add_field(_('Wiki'), change["logparams"].get("wiki", _("Unknown")))
	elif action == "managewiki/rights":
		group_name = change["title"].split("/permissions/", 1)[1]
		embed["title"] = _("Modified \"{usergroup_name}\" usergroup").format(usergroup_name=group_name)
		link = create_article_path(change["title"])
	elif action == "managewiki/undelete":
		embed["title"] = _("Undeleted a \"{wiki}\" wiki").format(wiki=change["logparams"].get("wiki", _("Unknown")))
		link = create_article_path(change["title"])
	elif action == "managewiki/unlock":
		embed["title"] = _("Unlocked a \"{wiki}\" wiki").format(wiki=change["logparams"].get("wiki", _("Unknown")))
		link = create_article_path(change["title"])
	elif action == "datadump/generate":
		embed["title"] = _("Generated {file} dump").format(file=change["logparams"]["filename"])
		link = create_article_path(change["title"])
	elif action == "datadump/delete":
		embed["title"] = _("Deleted {file} dump").format(file=change["logparams"]["filename"])
		link = create_article_path(change["title"])
	elif action == "pagetranslation/mark":
		link = create_article_path(change["title"])
		if "?" in link:
			link = link + "&oldid={}".format(change["logparams"]["revision"])
		else:
			link = link + "?oldid={}".format(change["logparams"]["revision"])
		embed["title"] = _("Marked \"{article}\" for translation").format(article=change["title"])
	elif action == "pagetranslation/unmark":
		link = create_article_path(change["title"])
		embed["title"] = _("Removed \"{article}\" from the translation system").format(article=change["title"])
	elif action == "pagetranslation/moveok":
		link = create_article_path(change["logparams"]["target"])
		embed["title"] = _("Completed moving translation pages from \"{article}\" to \"{target}\"").format(article=change["title"], target=change["logparams"]["target"])
	elif action == "pagetranslation/movenok":
		link = create_article_path(change["title"])
		embed["title"] = _("Encountered a problem while moving \"{article}\" to \"{target}\"").format(article=change["title"], target=change["logparams"]["target"])
	elif action == "pagetranslation/deletefok":
		link = create_article_path(change["title"])
		embed["title"] = _("Completed deletion of translatable page \"{article}\"").format(article=change["title"])
	elif action == "pagetranslation/deletefnok":
		link = create_article_path(change["title"])
		embed["title"] = _("Failed to delete \"{article}\" which belongs to translatable page \"{target}\"").format(article=change["title"], target=change["logparams"]["target"])
	elif action == "pagetranslation/deletelok":
		link = create_article_path(change["title"])
		embed["title"] = _("Completed deletion of translation page \"{article}\"").format(article=change["title"])
	elif action == "pagetranslation/deletelnok":
		link = create_article_path(change["title"])
		embed["title"] = _("Failed to delete \"{article}\" which belongs to translation page \"{target}\"").format(article=change["title"], target=change["logparams"]["target"])
	elif action == "pagetranslation/encourage":
		link = create_article_path(change["title"])
		embed["title"] = _("Encouraged translation of \"{article}\"").format(article=change["title"])
	elif action == "pagetranslation/discourage":
		link = create_article_path(change["title"])
		embed["title"] = _("Discouraged translation of \"{article}\"").format(article=change["title"])
	elif action == "pagetranslation/prioritylanguages":
		link = create_article_path(change["title"])
		if "languages" in change["logparams"]:
			languages = "`, `".join(change["logparams"]["languages"].split(","))
			if change["logparams"]["force"] == "on":
				embed["title"] = _("Limited languages for \"{article}\" to `{languages}`").format(article=change["title"], languages=languages)
			else:
				embed["title"] = _("Priority languages for \"{article}\" set to `{languages}`").format(article=change["title"], languages=languages)
		else:
			embed["title"] = _("Removed priority languages from \"{article}\"").format(article=change["title"])
	elif action == "pagetranslation/associate":
		link = create_article_path(change["title"])
		embed["title"] = _("Added translatable page \"{article}\" to aggregate group \"{group}\"").format(article=change["title"], group=change["logparams"]["aggregategroup"])
	elif action == "pagetranslation/dissociate":
		link = create_article_path(change["title"])
		embed["title"] = _("Removed translatable page \"{article}\" from aggregate group \"{group}\"").format(article=change["title"], group=change["logparams"]["aggregategroup"])
	elif action == "translationreview/message":
		link = create_article_path(change["title"])
		if "?" in link:
			link = link + "&oldid={}".format(change["logparams"]["revision"])
		else:
			link = link + "?oldid={}".format(change["logparams"]["revision"])
		embed["title"] = _("Reviewed translation \"{article}\"").format(article=change["title"])
	elif action == "translationreview/group":
		link = create_article_path(change["title"])
		embed["title"] = _("Changed the state of `{language}` translations of \"{article}\"").format(language=change["logparams"]["language"], article=change["title"])
		if "old-state" in change["logparams"]:
			embed.add_field(_("Old state"), change["logparams"]["old-state"], inline=True)
		embed.add_field(_("New state"), change["logparams"]["new-state"], inline=True)
	elif action == "pagelang/pagelang":
		link = create_article_path(change["title"])
		old_lang = "`{}`".format(change["logparams"]["oldlanguage"])
		if change["logparams"]["oldlanguage"][-5:] == "[def]":
			old_lang = "`{}` {}".format(change["logparams"]["oldlanguage"][:-5], _("(default)"))
		new_lang = "`{}`".format(change["logparams"]["newlanguage"])
		if change["logparams"]["newlanguage"][-5:] == "[def]":
			new_lang = "`{}` {}".format(change["logparams"]["oldlanguage"][:-5], _("(default)"))
		embed["title"] = _("Changed the language of \"{article}\"").format(article=change["title"])
		embed.add_field(_("Old language"), old_lang, inline=True)
		embed.add_field(_("New language"), new_lang, inline=True)
	elif action == "renameuser/renameuser":
		edits = change["logparams"]["edits"]
		if edits > 0:
			embed["title"] = ngettext("Renamed user \"{old_name}\" with {edits} edit to \"{new_name}\"", "Renamed user \"{old_name}\" with {edits} edits to \"{new_name}\"", edits).format(old_name=change["logparams"]["olduser"], edits=edits, new_name=change["logparams"]["newuser"])
		else:
			embed["title"] = _("Renamed user \"{old_name}\" to \"{new_name}\"").format(old_name=change["logparams"]["olduser"], new_name=change["logparams"]["newuser"])
		link = create_article_path("User:"+change["logparams"]["newuser"])
	elif action == "suppressed":
		link = create_article_path("")
		embed["title"] = _("Action has been hidden by administration")
		embed["author"]["name"] = _("Unknown")
	else:
		logger.warning("No entry for {event} with params: {params}".format(event=action, params=change))
		link = create_article_path("Special:RecentChanges")
		embed["title"] = _("Unknown event `{event}`").format(event=action)
		embed.event_type = "unknown"
		if settings.get("support", None):
			change_params = "[```json\n{params}\n```]({support})".format(params=json.dumps(change, indent=2),
			                                                             support=settings["support"])
			if len(change_params) > 1000:
				embed.add_field(_("Report this on the support server"), settings["support"])
			else:
				embed.add_field(_("Report this on the support server"), change_params)
	embed["url"] = quote(link.replace(" ", "_"), "/:?=&")
	if parsed_comment is not None:
		embed["description"] = parsed_comment
	if settings["appearance"]["embed"]["show_footer"]:
		embed["timestamp"] = change["timestamp"]
	if "tags" in change and change["tags"]:
		tag_displayname = []
		for tag in change["tags"]:
			if tag in recent_changes.tags:
				if recent_changes.tags[tag] is None:
					continue  # Ignore hidden tags
				else:
					tag_displayname.append(recent_changes.tags[tag])
			else:
				tag_displayname.append(tag)
		embed.add_field(_("Tags"), ", ".join(tag_displayname))
	if len(embed["title"]) > 254:
		embed["title"] = embed["title"][0:253]+"…"
	logger.debug("Current params in edit action: {}".format(change))
	if categories is not None and not (len(categories["new"]) == 0 and len(categories["removed"]) == 0):
		new_cat = (_("**Added**: ") + ", ".join(list(categories["new"])[0:16]) + ("\n" if len(categories["new"])<=15 else _(" and {} more\n").format(len(categories["new"])-15))) if categories["new"] else ""
		del_cat = (_("**Removed**: ") + ", ".join(list(categories["removed"])[0:16]) + ("" if len(categories["removed"])<=15 else _(" and {} more").format(len(categories["removed"])-15))) if categories["removed"] else ""
		embed.add_field(_("Changed categories"), new_cat + del_cat)
	embed.finish_embed()
	send_to_discord(embed, meta=request_metadata)
