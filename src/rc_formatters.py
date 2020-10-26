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
from src.misc import link_formatter, create_article_path, WIKI_SCRIPT_PATH, send_to_discord, DiscordMessage, safe_read, \
	WIKI_API_PATH, ContentParser, profile_field_name, LinkParser
from src.message_redaction import delete_messages, redact_messages
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
			contibs = safe_read(recent_changes.safe_request(
				"{wiki}?action=query&format=json&list=usercontribs&uclimit=max&ucuser={user}&ucstart={timestamp}&ucprop=".format(
					wiki=WIKI_API_PATH, user=change["user"], timestamp=change["timestamp"])), "query", "usercontribs")
			if contibs is None:
				logger.warning(
					"WARNING: Something went wrong when checking amount of contributions for given IP address")
				change["user"] = change["user"] + "(?)"
			else:
				recent_changes.map_ips[change["user"]] = len(contibs)
				logger.debug(
					"Current params user {} and state of map_ips {}".format(change["user"], recent_changes.map_ips))
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
	return change["user"], author_url

def compact_abuselog_formatter(change, recent_changes):
	action = "abuselog/{}".format(change["result"])
	author_url = link_formatter(create_article_path("User:{user}".format(user=change["user"])))
	author = change["user"]
	message = _("[{author}]({author_url}) triggered *{abuse_filter}*, performing the action \"{action}\" on *[{target}]({target_url})* - action taken: {result}.").format(
		author=author, author_url=author_url, abuse_filter=change["filter"],
		action=abusefilter_actions.get(change["action"], _("Unknown")), target=change.get("title", _("Unknown")),
		target_url=create_article_path(change.get("title", _("Unknown"))),
		result=abusefilter_results.get(change["result"], _("Unknown")))
	send_to_discord(DiscordMessage("compact", action, settings["webhookURL"], content=message), meta={"request_type": "POST"})


def compact_formatter(action, change, parsed_comment, categories, recent_changes):
	if action != "suppressed":
		author_url = link_formatter(create_article_path("User:{user}".format(user=change["user"])))
		author = change["user"]
	parsed_comment = "" if parsed_comment is None else " *("+parsed_comment+")*"
	if action in ["edit", "new"]:
		edit_link = link_formatter("{wiki}index.php?title={article}&curid={pageid}&diff={diff}&oldid={oldrev}".format(
			wiki=WIKI_SCRIPT_PATH, pageid=change["pageid"], diff=change["revid"], oldrev=change["old_revid"],
			article=change["title"]))
		logger.debug(edit_link)
		edit_size = change["newlen"] - change["oldlen"]
		if edit_size > 0:
			sign = "+"
		else:
			sign = ""
		if change["title"].startswith("MediaWiki:Tag-"):
			pass
		if action == "edit":
			content = "📝 "+_("[{author}]({author_url}) edited [{article}]({edit_link}){comment} ({sign}{edit_size})").format(author=author, author_url=author_url, article=change["title"], edit_link=edit_link, comment=parsed_comment, edit_size=edit_size, sign=sign)
		else:
			content = "🆕 "+_("[{author}]({author_url}) created [{article}]({edit_link}){comment} ({sign}{edit_size})").format(author=author, author_url=author_url, article=change["title"], edit_link=edit_link, comment=parsed_comment, edit_size=edit_size, sign=sign)
	elif action =="upload/upload":
		file_link = link_formatter(create_article_path(change["title"]))
		content = "🖼️ "+_("[{author}]({author_url}) uploaded [{file}]({file_link}){comment}").format(author=author,
		                                                                                    author_url=author_url,
		                                                                                    file=change["title"],
		                                                                                    file_link=file_link,
		                                                                                    comment=parsed_comment)
	elif action == "upload/revert":
		file_link = link_formatter(create_article_path(change["title"]))
		content = "⏮️ "+_("[{author}]({author_url}) reverted a version of [{file}]({file_link}){comment}").format(
			author=author, author_url=author_url, file=change["title"], file_link=file_link, comment=parsed_comment)
	elif action == "upload/overwrite":
		file_link = link_formatter(create_article_path(change["title"]))
		content = "🖼️ "+_("[{author}]({author_url}) uploaded a new version of [{file}]({file_link}){comment}").format(author=author, author_url=author_url, file=change["title"], file_link=file_link, comment=parsed_comment)
	elif action == "delete/delete":
		page_link = link_formatter(create_article_path(change["title"]))
		content = "🗑️ "+_("[{author}]({author_url}) deleted [{page}]({page_link}){comment}").format(author=author, author_url=author_url, page=change["title"], page_link=page_link,
		                                                  comment=parsed_comment)
	elif action == "delete/delete_redir":
		page_link = link_formatter(create_article_path(change["title"]))
		content = "🗑️ "+_("[{author}]({author_url}) deleted redirect by overwriting [{page}]({page_link}){comment}").format(author=author, author_url=author_url, page=change["title"], page_link=page_link,
		                                                   comment=parsed_comment)
	elif action == "move/move":
		link = link_formatter(create_article_path(change["logparams"]['target_title']))
		redirect_status = _("without making a redirect") if "suppressredirect" in change["logparams"] else _("with a redirect")
		content = "📨 "+_("[{author}]({author_url}) moved {redirect}*{article}* to [{target}]({target_url}) {made_a_redirect}{comment}").format(author=author, author_url=author_url, redirect="⤷ " if "redirect" in change else "", article=change["title"],
			target=change["logparams"]['target_title'], target_url=link, comment=parsed_comment, made_a_redirect=redirect_status)
	elif action == "move/move_redir":
		link = link_formatter(create_article_path(change["logparams"]["target_title"]))
		redirect_status = _("without making a redirect") if "suppressredirect" in change["logparams"] else _(
			"with a redirect")
		content = "📨 "+_("[{author}]({author_url}) moved {redirect}*{article}* over redirect to [{target}]({target_url}) {made_a_redirect}{comment}").format(author=author, author_url=author_url, redirect="⤷ " if "redirect" in change else "", article=change["title"],
			target=change["logparams"]['target_title'], target_url=link, comment=parsed_comment, made_a_redirect=redirect_status)
	elif action == "protect/move_prot":
		link = link_formatter(create_article_path(change["logparams"]["oldtitle_title"]))
		content = "🔏 "+_(
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
		if change["logparams"]["duration"] in ["infinite", "infinity", "indefinite", "never"]:
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
				restriction_description = ""
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
		content = "🚫 "+_(
			"[{author}]({author_url}) blocked [{user}]({user_url}) {time}{restriction_desc}{comment}").format(author=author, author_url=author_url, user=user, time=block_time, user_url=link, restriction_desc=restriction_description, comment=parsed_comment)
	elif action == "block/reblock":
		link = link_formatter(create_article_path(change["title"]))
		user = change["title"].split(':', 1)[1]
		content = "🚫 "+_("[{author}]({author_url}) changed block settings for [{blocked_user}]({user_url}){comment}").format(author=author, author_url=author_url, blocked_user=user, user_url=link, comment=parsed_comment)
	elif action == "block/unblock":
		link = link_formatter(create_article_path(change["title"]))
		user = change["title"].split(':', 1)[1]
		content = "✅ "+_("[{author}]({author_url}) unblocked [{blocked_user}]({user_url}){comment}").format(author=author, author_url=author_url, blocked_user=user, user_url=link, comment=parsed_comment)
	elif action == "curseprofile/comment-created":
		link = link_formatter(create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"])))
		content = "✉️ "+_("[{author}]({author_url}) left a [comment]({comment}) on {target} profile").format(author=author, author_url=author_url, comment=link, target=change["title"].split(':')[1]+"'s" if change["title"].split(':')[1] != change["user"] else _("their own profile"))
	elif action == "curseprofile/comment-replied":
		link = link_formatter(create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"])))
		content = "📩 "+_("[{author}]({author_url}) replied to a [comment]({comment}) on {target} profile").format(author=author,
		                                                                                               author_url=author_url,
		                                                                                               comment=link,
		                                                                                               target=change["title"].split(':')[1] if change["title"].split(':')[1] !=change["user"] else _("their own"))
	elif action == "curseprofile/comment-edited":
		link = link_formatter(create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"])))
		content = "📧 "+_("[{author}]({author_url}) edited a [comment]({comment}) on {target} profile").format(author=author,
		                                                                                               author_url=author_url,
		                                                                                               comment=link,
		                                                                                               target=change["title"].split(':')[1] if change["title"].split(':')[1] !=change["user"] else _("their own"))
	elif action == "curseprofile/comment-purged":
		link = link_formatter(create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"])))
		content = "👁️ "+_("[{author}]({author_url}) purged a comment on {target} profile").format(author=author,
		                                                                                     author_url=author_url,
		                                                                                     target=
		                                                                                     change["title"].split(':')[
			                                                                                     1] if
		                                                                                     change["title"].split(':')[
			                                                                                     1] != change[
			                                                                                     "user"] else _(
			                                                                                     "their own"))
	elif action == "curseprofile/comment-deleted":
		content = "🗑️ "+_("[{author}]({author_url}) deleted a comment on {target} profile").format(author=author,
		                                                                                    author_url=author_url,
		                                                                                     target=change["title"].split(':')[1] if change["title"].split(':')[1] !=change["user"] else _("their own"))

	elif action == "curseprofile/profile-edited":
		link = link_formatter(create_article_path("UserProfile:{user}".format(user=change["title"].split(":")[1])))
		target = _("[{target}]({target_url})'s").format(target=change["title"].split(':')[1], target_url=link) if change["title"].split(':')[1] != author else _("[their own]({target_url})").format(target_url=link)
		content = "📌 "+_("[{author}]({author_url}) edited the {field} on {target} profile. *({desc})*").format(author=author,
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
			content = "🏅 "+_("[{author}]({author_url}) changed group membership for [{target}]({target_url}) from {old_groups} to {new_groups}{comment}").format(author=author, author_url=author_url, target=change["title"].split(":")[1], target_url=link, old_groups=", ".join(old_groups), new_groups=', '.join(new_groups), comment=parsed_comment)
		else:
			content = "🏅 "+_("{author} autopromoted [{target}]({target_url}) from {old_groups} to {new_groups}{comment}").format(
				author=_("System"), author_url=author_url, target=change["title"].split(":")[1], target_url=link,
				old_groups=", ".join(old_groups), new_groups=', '.join(new_groups),
				comment=parsed_comment)
	elif action == "protect/protect":
		link = link_formatter(create_article_path(change["title"]))
		content = "🔒 "+_("[{author}]({author_url}) protected [{article}]({article_url}) with the following settings: {settings}{comment}").format(author=author, author_url=author_url,
		                                                                                                                                     article=change["title"], article_url=link,
		                                                                                                                                     settings=change["logparams"]["description"]+_(" [cascading]") if "cascade" in change["logparams"] else "",
		                                                                                                                                     comment=parsed_comment)
	elif action == "protect/modify":
		link = link_formatter(create_article_path(change["title"]))
		content = "🔐 "+_(
			"[{author}]({author_url}) modified protection settings of [{article}]({article_url}) to: {settings}{comment}").format(
			author=author, author_url=author_url,
			article=change["title"], article_url=link,
			settings=change["logparams"]["description"] + _(" [cascading]") if "cascade" in change["logparams"] else "",
			comment=parsed_comment)
	elif action == "protect/unprotect":
		link = link_formatter(create_article_path(change["title"]))
		content = "🔓 "+_("[{author}]({author_url}) removed protection from [{article}]({article_url}){comment}").format(author=author, author_url=author_url, article=change["title"], article_url=link, comment=parsed_comment)
	elif action == "delete/revision":
		amount = len(change["logparams"]["ids"])
		link = link_formatter(create_article_path(change["title"]))
		content = "👁️ "+ngettext("[{author}]({author_url}) changed visibility of revision on page [{article}]({article_url}){comment}",
		                          "[{author}]({author_url}) changed visibility of {amount} revisions on page [{article}]({article_url}){comment}", amount).format(author=author, author_url=author_url,
			article=change["title"], article_url=link, amount=amount, comment=parsed_comment)
	elif action == "import/upload":
		link = link_formatter(create_article_path(change["title"]))
		content = "📥 "+ngettext("[{author}]({author_url}) imported [{article}]({article_url}) with {count} revision{comment}",
		                          "[{author}]({author_url}) imported [{article}]({article_url}) with {count} revisions{comment}", change["logparams"]["count"]).format(
			author=author, author_url=author_url, article=change["title"], article_url=link, count=change["logparams"]["count"], comment=parsed_comment)
	elif action == "delete/restore":
		link = link_formatter(create_article_path(change["title"]))
		content = "♻️ "+_("[{author}]({author_url}) restored [{article}]({article_url}){comment}").format(author=author, author_url=author_url, article=change["title"], article_url=link, comment=parsed_comment)
	elif action == "delete/event":
		content = "👁️ "+_("[{author}]({author_url}) changed visibility of log events{comment}").format(author=author, author_url=author_url, comment=parsed_comment)
	elif action == "import/interwiki":
		content = "📥 "+_("[{author}]({author_url}) imported interwiki{comment}").format(author=author, author_url=author_url, comment=parsed_comment)
	elif action == "abusefilter/modify":
		link = link_formatter(create_article_path("Special:AbuseFilter/history/{number}/diff/prev/{historyid}".format(number=change["logparams"]['newId'], historyid=change["logparams"]["historyId"])))
		content = "🔍 "+_("[{author}]({author_url}) edited abuse filter [number {number}]({filter_url})").format(author=author, author_url=author_url, number=change["logparams"]['newId'], filter_url=link)
	elif action == "abusefilter/create":
		link = link_formatter(
			create_article_path("Special:AbuseFilter/{number}".format(number=change["logparams"]['newId'])))
		content = "🔍 "+_("[{author}]({author_url}) created abuse filter [number {number}]({filter_url})").format(author=author, author_url=author_url, number=change["logparams"]['newId'], filter_url=link)
	elif action == "merge/merge":
		link = link_formatter(create_article_path(change["title"]))
		link_dest = link_formatter(create_article_path(change["logparams"]["dest_title"]))
		content = "🖇️ "+_("[{author}]({author_url}) merged revision histories of [{article}]({article_url}) into [{dest}]({dest_url}){comment}").format(author=author, author_url=author_url, article=change["title"], article_url=link, dest_url=link_dest,
		                                                                                dest=change["logparams"]["dest_title"], comment=parsed_comment)
	elif action == "newusers/autocreate":
		link = link_formatter(create_article_path(change["title"]))
		content = "🗿 "+_("Account [{author}]({author_url}) was created automatically").format(author=author, author_url=author_url)
	elif action == "newusers/create":
		link = link_formatter(create_article_path(change["title"]))
		content = "🗿 "+_("Account [{author}]({author_url}) was created").format(author=author, author_url=author_url)
	elif action == "newusers/create2":
		link = link_formatter(create_article_path(change["title"]))
		content = "🗿 "+_("Account [{article}]({article_url}) was created by [{author}]({author_url}){comment}").format(article=change["title"], article_url=link, author=author, author_url=author_url, comment=parsed_comment)
	elif action == "newusers/byemail":
		link = link_formatter(create_article_path(change["title"]))
		content = "🗿 "+_("Account [{article}]({article_url}) was created by [{author}]({author_url}) and password was sent by email{comment}").format(article=change["title"], article_url=link, author=author, author_url=author_url, comment=parsed_comment)
	elif action == "newusers/newusers":
		link = author_url
		content = "🗿 "+_("Account [{author}]({author_url}) was created").format(author=author, author_url=author_url)
	elif action == "interwiki/iw_add":
		link = link_formatter(create_article_path("Special:Interwiki"))
		content = "🔗 "+_("[{author}]({author_url}) added an entry to the [interwiki table]({table_url}) pointing to {website} with {prefix} prefix").format(author=author, author_url=author_url, desc=parsed_comment,
		                                                                           prefix=change["logparams"]['0'],
		                                                                           website=change["logparams"]['1'],
		                                                                            table_url=link)
	elif action == "interwiki/iw_edit":
		link = link_formatter(create_article_path("Special:Interwiki"))
		content = "🔗 "+_("[{author}]({author_url}) edited an entry in [interwiki table]({table_url}) pointing to {website} with {prefix} prefix").format(author=author, author_url=author_url, desc=parsed_comment,
		                                                                           prefix=change["logparams"]['0'],
		                                                                           website=change["logparams"]['1'],
		                                                                            table_url=link)
	elif action == "interwiki/iw_delete":
		link = link_formatter(create_article_path("Special:Interwiki"))
		content = "🔗 "+_("[{author}]({author_url}) deleted an entry in [interwiki table]({table_url})").format(author=author, author_url=author_url, table_url=link)
	elif action == "contentmodel/change":
		link = link_formatter(create_article_path(change["title"]))
		content = "📋 "+_("[{author}]({author_url}) changed the content model of the page [{article}]({article_url}) from {old} to {new}{comment}").format(author=author, author_url=author_url, article=change["title"], article_url=link, old=change["logparams"]["oldmodel"],
		                                                                         new=change["logparams"]["newmodel"], comment=parsed_comment)
	elif action == "sprite/sprite":
		link = link_formatter(create_article_path(change["title"]))
		content = "🪟 "+_("[{author}]({author_url}) edited the sprite for [{article}]({article_url})").format(author=author, author_url=author_url, article=change["title"], article_url=link)
	elif action == "sprite/sheet":
		link = link_formatter(create_article_path(change["title"]))
		content = "🪟 "+_("[{author}]({author_url}) created the sprite sheet for [{article}]({article_url})").format(author=author, author_url=author_url, article=change["title"], article_url=link)
	elif action == "sprite/slice":
		link = link_formatter(create_article_path(change["title"]))
		content = "🪟 "+_("[{author}]({author_url}) edited the slice for [{article}]({article_url})").format(author=author, author_url=author_url, article=change["title"], article_url=link)
	elif action == "cargo/createtable":
		LinkParser.feed(change["logparams"]["0"])
		table = LinkParser.new_string
		LinkParser.new_string = ""
		content = "📦 "+_("[{author}]({author_url}) created the Cargo table \"{table}\"").format(author=author, author_url=author_url, table=table)
	elif action == "cargo/deletetable":
		content = "📦 "+_("[{author}]({author_url}) deleted the Cargo table \"{table}\"").format(author=author, author_url=author_url, table=change["logparams"]["0"])
	elif action == "cargo/recreatetable":
		LinkParser.feed(change["logparams"]["0"])
		table = LinkParser.new_string
		LinkParser.new_string = ""
		content = "📦 "+_("[{author}]({author_url}) recreated the Cargo table \"{table}\"").format(author=author, author_url=author_url, table=table)
	elif action == "cargo/replacetable":
		LinkParser.feed(change["logparams"]["0"])
		table = LinkParser.new_string
		LinkParser.new_string = ""
		content = "📦 "+_("[{author}]({author_url}) replaced the Cargo table \"{table}\"").format(author=author, author_url=author_url, table=table)
	elif action == "managetags/create":
		link = link_formatter(create_article_path("Special:Tags"))
		content = "🏷️ "+_("[{author}]({author_url}) created a [tag]({tag_url}) \"{tag}\"").format(author=author, author_url=author_url, tag=change["logparams"]["tag"], tag_url=link)
		recent_changes.init_info()
	elif action == "managetags/delete":
		link = link_formatter(create_article_path("Special:Tags"))
		content = "🏷️ "+_("[{author}]({author_url}) deleted a [tag]({tag_url}) \"{tag}\"").format(author=author, author_url=author_url, tag=change["logparams"]["tag"], tag_url=link)
		recent_changes.init_info()
	elif action == "managetags/activate":
		link = link_formatter(create_article_path("Special:Tags"))
		content = "🏷️ "+_("[{author}]({author_url}) activated a [tag]({tag_url}) \"{tag}\"").format(author=author, author_url=author_url, tag=change["logparams"]["tag"], tag_url=link)
	elif action == "managetags/deactivate":
		link = link_formatter(create_article_path("Special:Tags"))
		content = "🏷️ "+_("[{author}]({author_url}) deactivated a [tag]({tag_url}) \"{tag}\"").format(author=author, author_url=author_url, tag=change["logparams"]["tag"], tag_url=link)
	elif action == "managewiki/settings":  # Miraheze's ManageWiki extension https://github.com/miraheze/ManageWiki
		content = "⚙️ "+_("[{author}]({author_url}) changed wiki settings ({reason})".format(author=author, author_url=author_url, reason=parsed_comment))
	elif action == "managewiki/delete":
		content = "🗑️ "+_("[{author}]({author_url}) deleted a wiki *{wiki_name}* ({comment})").format(author=author, author_url=author_url,
		                                                                                              wiki_name=change["logparams"].get("wiki", {"wiki": _("Unknown")}), comment=parsed_comment)
	elif action == "managewiki/lock":
		content = "🔒 "+_("[{author}]({author_url}) locked a wiki *{wiki_name}* ({comment})").format(
			author=author, author_url=author_url, wiki_name=change["logparams"].get("wiki", {"wiki": _("Unknown")}), comment=parsed_comment)
	elif action == "managewiki/namespaces":
		content = "📦 "+_("[{author}]({author_url}) modified a namespace *{namespace_name}* on *{wiki_name}* ({comment})").format(
			author=author, author_url=author_url, namespace_name=change["logparams"].get("namespace", {"namespace": _("Unknown")}),
		    wiki_name=change["logparams"].get("wiki", {"wiki": _("Unknown")}), comment=parsed_comment)
	elif action == "managewiki/namespaces-delete":
		content = "🗑️ " + _(
			"[{author}]({author_url}) deleted a namespace *{namespace_name}* on *{wiki_name}* ({comment})").format(
			author=author, author_url=author_url,
			namespace_name=change["logparams"].get("namespace", {"namespace": _("Unknown")}),
			wiki_name=change["logparams"].get("wiki", {"wiki": _("Unknown")}), comment=parsed_comment)
	elif action == "managewiki/rights":
		content = "🏅 " + _("[{author}]({author_url}) modified user group *{group_name}* ({comment})").format(
			author=author, author_url=author_url, group_name=change["title"][32:], comment=parsed_comment
		)
	elif action == "managewiki/undelete":
		content = "🏅 " + _("[{author}]({author_url}) restored a wiki *{wiki_name}* ({comment})").format(
			author=author, author_url=author_url, wiki_name=change["logparams"].get("wiki", {"wiki": _("Unknown")}), comment=parsed_comment
		)
	elif action == "managewiki/unlock":
		content = "🏅 " + _("[{author}]({author_url}) unlocked a wiki *{wiki_name}* ({comment})").format(
			author=author, author_url=author_url, wiki_name=change["logparams"].get("wiki", {"wiki": _("Unknown")}),
			comment=parsed_comment
		)
	elif action == "suppressed":
		content = "👁️ "+_("An action has been hidden by administration.")
	else:
		logger.warning("No entry for {event} with params: {params}".format(event=action, params=change))
		if not settings.get("support", None):
			return
		else:
			content = "❓ "+_(
				"Unknown event `{event}` by [{author}]({author_url}), report it on the [support server](<{support}>).").format(
				event=action, author=author, author_url=author_url, support=settings["support"])
	send_to_discord(DiscordMessage("compact", action, settings["webhookURL"], content=content), meta={"request_type": "POST"})

def embed_abuselog_formatter(change, recent_changes):
	action = "abuselog/{}".format(change["result"])
	embed = DiscordMessage("embed", action, settings["webhookURL"])
	raw_username = change["user"]
	change["user"], author_url = format_user(change, recent_changes, action)
	embed["title"] = _("{user} triggered \"{abuse_filter}\"").format(user=raw_username, abuse_filter=change["filter"])
	embed.add_field(_("Performed"), abusefilter_actions.get(change["action"], _("Unknown")))
	embed.add_field(_("Action taken"), abusefilter_results.get(change["result"], _("Unknown")))
	embed.add_field(_("Title"), change.get("title", _("Unknown")))
	embed.finish_embed()
	send_to_discord(embed, meta={"request_type": "POST"})


def embed_formatter(action, change, parsed_comment, categories, recent_changes):
	embed = DiscordMessage("embed", action, settings["webhookURL"])
	if parsed_comment is None:
		parsed_comment = _("No description provided")
	if action != "suppressed":
		change["user"], author_url = format_user(change, recent_changes, action)
		embed.set_author(change["user"], author_url)
	if action in ("edit", "new"):  # edit or new page
		editsize = change["newlen"] - change["oldlen"]
		if editsize > 0:
			if editsize > 6032:
				embed["color"] = 65280
			else:
				embed["color"] = 35840 + (math.floor(editsize / 52)) * 256
		elif editsize < 0:
			if editsize < -6032:
				embed["color"] = 16711680
			else:
				embed["color"] = 9175040 + (math.floor((editsize * -1) / 52)) * 65536
		elif editsize == 0:
			embed["color"] = 8750469
		if change["title"].startswith("MediaWiki:Tag-"):  # Refresh tag list when tag display name is edited
			recent_changes.init_info()
		link = "{wiki}index.php?title={article}&curid={pageid}&diff={diff}&oldid={oldrev}".format(
			wiki=WIKI_SCRIPT_PATH, pageid=change["pageid"], diff=change["revid"], oldrev=change["old_revid"],
			article=change["title"])
		embed["title"] = "{redirect}{article} ({new}{minor}{bot}{space}{editsize})".format(redirect="⤷ " if "redirect" in change else "", article=change["title"], editsize="+" + str(
			editsize) if editsize > 0 else editsize, new=_("(N!) ") if action == "new" else "",
		                                                             minor=_("m") if action == "edit" and "minor" in change else "", bot=_('b') if "bot" in change else "", space=" " if "bot" in change or (action == "edit" and "minor" in change) or action == "new" else "")
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
					embed.add_field(_("Removed"), "{data}".format(data=EditDiff.small_prev_del), inline=True)
				if EditDiff.small_prev_ins:
					embed.add_field(_("Added"), "{data}".format(data=EditDiff.small_prev_ins), inline=True)
			else:
				logger.warning("Unable to download data on the edit content!")
	elif action in ("upload/overwrite", "upload/upload", "upload/revert"):  # sending files
		license = None
		urls = safe_read(recent_changes.safe_request(
			"{wiki}?action=query&format=json&prop=imageinfo&list=&meta=&titles={filename}&iiprop=timestamp%7Curl%7Carchivename&iilimit=5".format(
				wiki=WIKI_API_PATH, filename=change["title"])), "query", "pages")
		link = create_article_path(change["title"])
		additional_info_retrieved = False
		if urls is not None:
			logger.debug(urls)
			if "-1" not in urls:  # image still exists and not removed
				try:
					img_info = next(iter(urls.values()))["imageinfo"]
					for num, revision in enumerate(img_info):
						if revision["timestamp"] == change["logparams"]["img_timestamp"]:  # find the correct revision corresponding for this log entry
							image_direct_url = "{rev}?{cache}".format(rev=revision["url"], cache=int(time.time()*5))  # cachebusting
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
					embed.add_field(_("Options"), _("([preview]({link}) | [undo]({undolink}))").format(
						link=image_direct_url, undolink=undolink))
				if settings["appearance"]["embed"]["embed_images"]:
					embed["image"]["url"] = image_direct_url
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
				embed.add_field(_("Options"), _("([preview]({link}))").format(link=image_direct_url))
				if settings["appearance"]["embed"]["embed_images"]:
					embed["image"]["url"] = image_direct_url
	elif action == "delete/delete":
		link = create_article_path(change["title"])
		embed["title"] = _("Deleted page {article}").format(article=change["title"])
	elif action == "delete/delete_redir":
		link = create_article_path(change["title"])
		embed["title"] = _("Deleted redirect {article} by overwriting").format(article=change["title"])
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
			link = create_article_path(change["title"].replace(')', '\)'))
		if change["logparams"]["duration"] in ["infinite", "infinity"]:
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
				date_time_obj = datetime.datetime.strptime(change["logparams"]["expiry"], '%Y-%m-%dT%H:%M:%SZ')
				block_time = _("until {}").format(date_time_obj.strftime("%Y-%m-%d %H:%M:%S UTC"))
		if "sitewide" not in change["logparams"]:
			restriction_description = ""
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
		link = create_article_path(change["title"].replace(')', '\)'))
		user = change["title"].split(':', 1)[1]
		embed["title"] = _("Changed block settings for {blocked_user}").format(blocked_user=user)
	elif action == "block/unblock":
		link = create_article_path(change["title"].replace(')', '\)'))
		user = change["title"].split(':', 1)[1]
		embed["title"] = _("Unblocked {blocked_user}").format(blocked_user=user)
	elif action == "curseprofile/comment-created":
		if settings["appearance"]["embed"]["show_edit_changes"]:
			parsed_comment = recent_changes.pull_comment(change["logparams"]["4:comment_id"])
		link = create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"]))
		embed["title"] = _("Left a comment on {target}'s profile").format(target=change["title"].split(':')[1]) if change["title"].split(':')[1] != \
		                                                                                              change["user"] else _(
			"Left a comment on their own profile")
	elif action == "curseprofile/comment-replied":
		if settings["appearance"]["embed"]["show_edit_changes"]:
			parsed_comment = recent_changes.pull_comment(change["logparams"]["4:comment_id"])
		link = create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"]))
		embed["title"] = _("Replied to a comment on {target}'s profile").format(target=change["title"].split(':')[1]) if change["title"].split(':')[1] != \
		                                                                                                    change["user"] else _(
			"Replied to a comment on their own profile")
	elif action == "curseprofile/comment-edited":
		if settings["appearance"]["embed"]["show_edit_changes"]:
			parsed_comment = recent_changes.pull_comment(change["logparams"]["4:comment_id"])
		link = create_article_path("Special:CommentPermalink/{commentid}".format(commentid=change["logparams"]["4:comment_id"]))
		embed["title"] = _("Edited a comment on {target}'s profile").format(target=change["title"].split(':')[1]) if change["title"].split(':')[1] != \
		                                                                                                change["user"] else _(
			"Edited a comment on their own profile")
	elif action == "curseprofile/profile-edited":
		link = create_article_path("UserProfile:{target}".format(target=change["title"].split(':')[1].replace(')', '\)')))
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
		link = create_article_path("User:{}".format(change["title"].split(":")[1]))
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
		link = create_article_path(change["title"])
		embed["title"] = _("Protected {target}").format(target=change["title"])
		parsed_comment = "{settings}{cascade} | {reason}".format(settings=change["logparams"]["description"],
		                                                         cascade=_(" [cascading]") if "cascade" in change["logparams"] else "",
		                                                         reason=parsed_comment)
	elif action == "protect/modify":
		link = create_article_path(change["title"])
		embed["title"] = _("Changed protection level for {article}").format(article=change["title"])
		parsed_comment = "{settings}{cascade} | {reason}".format(settings=change["logparams"]["description"],
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
	elif action == "import/interwiki":
		link = create_article_path("Special:RecentChanges")
		embed["title"] = _("Imported interwiki")
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
	elif action == "managewiki/settings":  # Miraheze's ManageWiki extension https://github.com/miraheze/ManageWiki
		link = create_article_path("")
		embed["title"] = _("Changed wiki settings")
		if change["logparams"].get("changes", ""):
			embed.add_field("Setting", change["logparams"].get("changes"))
	elif action == "managewiki/delete":
		embed["title"] = _("Deleted a \"{wiki}\" wiki".format(wiki=change["logparams"].get("wiki", {"wiki": _("Unknown")})))
		link = create_article_path("")
	elif action == "managewiki/lock":
		embed["title"] = _(
			"Locked a \"{wiki}\" wiki".format(wiki=change["logparams"].get("wiki", {"wiki": _("Unknown")})))
		link = create_article_path("")
	elif action == "managewiki/namespaces":
		embed["title"] = _(
			"Modified a \"{namespace_name}\" namespace".format(namespace_name=change["logparams"].get("namespace", {"namespace": _("Unknown")})))
		link = create_article_path("")
		embed.add_field(_('Wiki'), change["logparams"].get("wiki", {"wiki": _("Unknown")}))
	elif action == "managewiki/namespaces-delete":
		embed["title"] = _(
			"Deleted a \"{namespace_name}\" namespace".format(
				namespace_name=change["logparams"].get("namespace", {"namespace": _("Unknown")})))
		link = create_article_path("")
		embed.add_field(_('Wiki'), change["logparams"].get("wiki", {"wiki": _("Unknown")}))
	elif action == "managewiki/rights":
		embed["title"] = _(
			"Modified \"{usergroup_name}\" usergroup".format(usergroup_name=change["title"][32:]))
		link = create_article_path("")
	elif action == "managewiki/undelete":
		embed["title"] = _(
			"Restored a \"{wiki}\" wiki".format(wiki=change["logparams"].get("wiki", {"wiki": _("Unknown")})))
		link = create_article_path("")
	elif action == "managewiki/unlock":
		embed["title"] = _(
			"Unlocked a \"{wiki}\" wiki".format(wiki=change["logparams"].get("wiki", {"wiki": _("Unknown")})))
		link = create_article_path("")
	elif action == "suppressed":
		link = create_article_path("")
		embed["title"] = _("Action has been hidden by administration")
		embed["author"]["name"] = _("Unknown")
	else:
		logger.warning("No entry for {event} with params: {params}".format(event=action, params=change))
		link = create_article_path("Special:RecentChanges")
		embed["title"] = _("Unknown event `{event}`").format(event=action)
		embed["color"] = 0
		if settings.get("support", None):
			change_params = "[```json\n{params}\n```]({support})".format(params=json.dumps(change, indent=2),
			                                                             support=settings["support"])
			if len(change_params) > 1000:
				embed.add_field(_("Report this on the support server"), settings["support"])
			else:
				embed.add_field(_("Report this on the support server"), change_params)
	embed["author"]["icon_url"] = settings["appearance"]["embed"][action]["icon"]
	embed["url"] = quote(link.replace(" ", "_"), "/:?")
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
	logger.debug("Current params in edit action: {}".format(change))
	if categories is not None and not (len(categories["new"]) == 0 and len(categories["removed"]) == 0):
		new_cat = (_("**Added**: ") + ", ".join(list(categories["new"])[0:16]) + ("\n" if len(categories["new"])<=15 else _(" and {} more\n").format(len(categories["new"])-15))) if categories["new"] else ""
		del_cat = (_("**Removed**: ") + ", ".join(list(categories["removed"])[0:16]) + ("" if len(categories["removed"])<=15 else _(" and {} more").format(len(categories["removed"])-15))) if categories["removed"] else ""
		embed.add_field(_("Changed categories"), new_cat + del_cat)
	embed.finish_embed()
	send_to_discord(embed, meta={"request_type": "POST"})
