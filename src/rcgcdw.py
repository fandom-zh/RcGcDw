#!/usr/bin/python
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

# WARNING! SHITTY CODE AHEAD. ENTER ONLY IF YOU ARE SURE YOU CAN TAKE IT
# You have been warned

import time, logging.config, requests, datetime, math, os.path, sys, importlib

import src.misc
import src.configloader
from collections import defaultdict, Counter, OrderedDict
from src.argparser import command_args
from typing import Optional
import src.api.client
from src.api.context import Context
from src.api.hooks import formatter_hooks, pre_hooks, post_hooks
from src.misc import add_to_dict, datafile, run_hooks
from src.api.util import create_article_path, default_message
from src.discord.queue import send_to_discord
from src.discord.message import DiscordMessage, DiscordMessageMetadata
from src.exceptions import ServerError, MediaWikiError, NoFormatter
from src.i18n import rcgcdw
from src.wiki import Wiki

settings = src.configloader.settings
_ = rcgcdw.gettext
ngettext = rcgcdw.ngettext

TESTING = command_args.test  # debug mode, pipeline testing
AUTO_SUPPRESSION_ENABLED = settings.get("auto_suppression", {"enabled": False}).get("enabled")

if AUTO_SUPPRESSION_ENABLED:
	from src.discord.redaction import delete_messages, redact_messages, find_middle_next
# Prepare logging

logging.config.dictConfig(settings["logging"])
logger = logging.getLogger("rcgcdw")
logger.debug("Current settings: {settings}".format(settings=settings))


def load_extensions():
	"""Loads all of the extensions, can be a local import because all we need is them to register"""
	try:
		importlib.import_module(settings.get('extensions_dir', 'extensions'), 'extensions')
	except ImportError:
		logger.critical("No extensions module found. What's going on?")
		logger.exception("Error:")
		sys.exit(1)

storage = datafile

# Remove previous data holding file if exists and limitfetch allows

if settings["limitrefetch"] != -1 and os.path.exists("lastchange.txt") is True:
	with open("lastchange.txt", 'r', encoding="utf-8") as sfile:
		logger.info("Converting old lastchange.txt file into new data storage data.json...")
		storage["rcid"] = int(sfile.read().strip())
		datafile.save_datafile()
		os.remove("lastchange.txt")


def no_formatter(ctx: Context, change: dict) -> None:
	logger.warning(f"There is no formatter specified for {ctx.event}! Ignoring event.")
	raise NoFormatter

formatter_hooks["no_formatter"] = no_formatter

def day_overview_request() -> list:
	"""Make requests for changes in last 24h"""
	logger.info("Fetching daily overview... This may take up to 30 seconds!")
	timestamp = (datetime.datetime.utcnow() - datetime.timedelta(hours=24)).isoformat(timespec='milliseconds')
	result = []
	passes = 0
	continuearg: Optional[str] = None
	while passes < 10:
		params = OrderedDict(dict(action="query", format="json", list="recentchanges", rcend=timestamp,
								  rcprop="title|timestamp|sizes|loginfo|user", rcshow="!bot", rclimit="max",
								  rctype="edit|new|log", rccontinue=continuearg))
		request = wiki.retried_api_request(params)
		result += request['query']['recentchanges']
		if "continue" in request:
			continuearg = request["continue"].get("rccontinue", None)
		else:
			return result
		passes += 1
		logger.debug(
			"continuing requesting next pages of recent changes with {} passes and continuearg being {}".format(
				passes, continuearg))
		time.sleep(3.0)
	logger.debug("quit the loop because there been too many passes")
	return result


def daily_overview_sync(data: dict) -> dict:
	weight = storage["daily_overview"]["days_tracked"]
	if weight == 0:
		storage["daily_overview"].update(data)
		data_output = {k: str(v) for k, v in data.items()}
	else:
		data_output = {}
		for data_point, value in data.items():
			new_average = src.misc.weighted_average(storage["daily_overview"][data_point], weight, value)
			data_output[data_point] = _("{value} (avg. {avg})").format(value=value, avg=new_average)
			storage["daily_overview"][data_point] = new_average
	storage["daily_overview"]["days_tracked"] += 1
	datafile.save_datafile()
	return data_output


def day_overview():
	try:
		result = day_overview_request()
	except (ServerError, MediaWikiError):
		logger.error("Couldn't complete Daily Overview as requests for changes resulted in errors.")
	else:
		activity = defaultdict(dict)
		hours = defaultdict(dict)
		articles = defaultdict(dict)
		edits = files = admin = changed_bytes = new_articles = 0
		active_articles = []
		embed = DiscordMessage("embed", "daily_overview", settings["webhookURL"])
		embed["title"] = _("Daily overview")
		embed["url"] = create_article_path("Special:Statistics")
		embed.set_author(settings["wikiname"], create_article_path(""))
		if not result:
			if not settings["send_empty_overview"]:
				return  # no changes in this day
			else:
				embed["description"] = _("No activity")
		else:
			for item in result:
				if "actionhidden" in item or "suppressed" in item or "userhidden" in item:
					continue  # while such actions have type value (edit/new/log) many other values are hidden and therefore can crash with key error, let's not process such events
				activity = add_to_dict(activity, item["user"])
				hours = add_to_dict(hours, datetime.datetime.strptime(item["timestamp"], "%Y-%m-%dT%H:%M:%SZ").hour)
				if item["type"] == "edit":
					edits += 1
					changed_bytes += item["newlen"] - item["oldlen"]
					if (wiki.namespaces is not None and "content" in wiki.namespaces.get(str(item["ns"]), {})) or item["ns"] == 0:
						articles = add_to_dict(articles, item["title"])
				elif item["type"] == "new":
					if "content" in (wiki.namespaces is not None and wiki.namespaces.get(str(item["ns"]), {})) or item["ns"] == 0:
						new_articles += 1
					changed_bytes += item["newlen"]
				elif item["type"] == "log":
					files = files + 1 if item["logtype"] == item["logaction"] == "upload" else files
					admin = admin + 1 if item["logtype"] in ["delete", "merge", "block", "protect", "import", "rights",
															 "abusefilter", "interwiki", "managetags"] else admin
			overall = round(new_articles + edits * 0.1 + files * 0.3 + admin * 0.1 + math.fabs(changed_bytes * 0.001), 2)
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
				active_users = active_hours = [_("But nobody came")]  # a reference to my favorite game of all the time, sorry ^_^
				usramount = houramount = ""
			if not active_articles:
				active_articles = [_("But nobody came")]
			messages = daily_overview_sync({"edits": edits, "new_files": files, "admin_actions": admin, "bytes_changed":
				changed_bytes, "new_articles": new_articles, "unique_editors": len(activity), "day_score": overall})
			fields = (
			(ngettext("Most active user", "Most active users", len(active_users)), ', '.join(active_users)),
			(ngettext("Most edited article", "Most edited articles", len(active_articles)), ', '.join(active_articles)),
			(_("Edits made"), messages["edits"]), (_("New files"), messages["new_files"]),
			(_("Admin actions"), messages["admin_actions"]), (_("Bytes changed"), messages["bytes_changed"]),
			(_("New articles"), messages["new_articles"]), (_("Unique contributors"), messages["unique_editors"]),
			(ngettext("Most active hour", "Most active hours", len(active_hours)), ', '.join(active_hours) + houramount),
			(_("Day score"), messages["day_score"])
			)
			for name, value in fields:
				embed.add_field(name, value, inline=True)
		embed.finish_embed()
		send_to_discord(embed, meta=DiscordMessageMetadata("POST"))


def rc_processor(change, changed_categories):
	"""Prepares essential information for both embed and compact message format."""
	from src.misc import LinkParser
	LinkParser = LinkParser()
	metadata = DiscordMessageMetadata("POST", rev_id=change.get("revid", None), log_id=change.get("logid", None),
	                       page_id=change.get("pageid", None))
	logger.debug(change)
	context = Context(settings["appearance"]["mode"], "recentchanges", settings["webhookURL"], client)
	if ("actionhidden" in change or "suppressed" in change) and "suppressed" not in settings["ignored"]:  # if event is hidden using suppression
		context.event = "suppressed"
		run_hooks(pre_hooks, context, change)
		try:
			discord_message: Optional[DiscordMessage] = default_message("suppressed", formatter_hooks)(context, change)
		except NoFormatter:
			return
		except:
			if settings.get("error_tolerance", 1) > 0:
				discord_message: Optional[
					DiscordMessage] = None  # It's handled by send_to_discord, we still want other code to run
			else:
				raise
	else:
		if "commenthidden" not in change:
			LinkParser.feed(change.get("parsedcomment", ""))
			parsed_comment = LinkParser.new_string
		else:
			parsed_comment = _("~~hidden~~")
		if not parsed_comment and context.message_type == "embed" and settings["appearance"].get("embed", {}).get("show_no_description_provided", True):
			parsed_comment = _("No description provided")
		context.set_parsedcomment(parsed_comment)
		if "userhidden" in change:
			change["user"] = _("hidden")
		if change.get("ns", -1) in settings.get("ignored_namespaces", ()):
			return
		if change["type"] in ["edit", "new"]:
			logger.debug("List of categories in essential_info: {}".format(changed_categories))
			identification_string = change["type"]
			context.set_categories(changed_categories)
		elif change["type"] == "categorize":
			return
		elif change["type"] == "log":
			identification_string = "{logtype}/{logaction}".format(logtype=change["logtype"], logaction=change["logaction"])
		else:
			identification_string = change.get("type", "unknown")  # If event doesn't have a type
		if identification_string in settings["ignored"]:
			return
		context.event = identification_string
		run_hooks(pre_hooks, context, change)
		try:
			discord_message: Optional[DiscordMessage] = default_message(identification_string, formatter_hooks)(context, change)
		except:
			if settings.get("error_tolerance", 1) > 0:
				discord_message: Optional[DiscordMessage] = None  # It's handled by send_to_discord, we still want other code to run
			else:
				raise
		if identification_string in ("delete/delete", "delete/delete_redir") and AUTO_SUPPRESSION_ENABLED:  # TODO Move it into a hook?
			delete_messages(dict(pageid=change.get("pageid")))
		elif identification_string == "delete/event" and AUTO_SUPPRESSION_ENABLED:
			logparams = change.get('logparams', {"ids": []})
			if settings["appearance"]["mode"] == "embed":
				redact_messages(logparams.get("ids", []), 1, logparams.get("new", {}))
			else:
				for logid in logparams.get("ids", []):
					delete_messages(dict(logid=logid))
		elif identification_string == "delete/revision" and AUTO_SUPPRESSION_ENABLED:
			logparams = change.get('logparams', {"ids": []})
			if logparams.get("type", "") in ("revision", "logging", "oldimage"):
				if settings["appearance"]["mode"] == "embed":
					redact_messages(logparams.get("ids", []), 0, logparams.get("new", {}))
					if "content" in logparams.get("new", {}) and settings.get("appearance", {}).get("embed", {}).get("show_edit_changes", False):  # Also redact revisions in the middle and next ones in case of content (diffs leak)
						redact_messages(find_middle_next(logparams.get("ids", []), change.get("pageid", -1)), 0, {"content": ""})
				else:
					for revid in logparams.get("ids", []):
						delete_messages(dict(revid=revid))
	run_hooks(post_hooks, discord_message, metadata, context, change)
	if discord_message:
		discord_message.finish_embed()
	send_to_discord(discord_message, metadata)


def abuselog_processing(entry):
	action = "abuselog"
	if action in settings["ignored"]:
		return
	context = Context(settings["appearance"]["mode"], "abuselog", settings["webhookURL"], client)
	context.event = action
	run_hooks(pre_hooks, context, entry)
	try:
		discord_message: Optional[DiscordMessage] = default_message(action, formatter_hooks)(context, entry)
	except NoFormatter:
		return
	except:
		if settings.get("error_tolerance", 1) > 0:
			discord_message: Optional[DiscordMessage] = None  # It's handled by send_to_discord, we still want other code to run
		else:
			raise
	metadata = DiscordMessageMetadata("POST")
	run_hooks(post_hooks, discord_message, metadata, context, entry)
	discord_message.finish_embed()
	send_to_discord(discord_message, metadata)


load_extensions()
# Log in and download wiki information
wiki = Wiki(rc_processor, abuselog_processing)
client = src.api.client.Client(formatter_hooks, wiki)
if settings["fandom_discussions"]["enabled"] or TESTING:
	import src.discussions
	src.discussions.inject_client(client)  # Not the prettiest but gets the job done
try:
	if settings["wiki_bot_login"] and settings["wiki_bot_password"]:
		wiki.log_in()
	time.sleep(2.0)
	wiki.init_info()
except requests.exceptions.ConnectionError:
	logger.critical("A connection can't be established with the wiki. Exiting...")
	sys.exit(1)
time.sleep(3.0)  # this timeout is to prevent timeouts. It seems Fandom does not like our ~2-3 request in under a second
if settings["rc_enabled"]:
	logger.info("Script started! Fetching newest changes...")
	wiki.fetch(amount=settings["limitrefetch"] if settings["limitrefetch"] != -1 else settings["limit"])
	client.schedule(wiki.fetch, every=settings["cooldown"])
	if settings["overview"]:
		try:
			overview_time = time.strptime(settings["overview_time"], '%H:%M')
			client.schedule(day_overview, at="{}:{}".format(str(overview_time.tm_hour).zfill(2), str(overview_time.tm_min).zfill(2)))
			del overview_time
		except ValueError:
			logger.error("Invalid time format! Currentely: {}. Note: It needs to be in HH:MM format.".format(
				settings["overview_time"]))
	client.schedule(wiki.clear_cache, at="00:00")
else:
	logger.info("Script started! RC is disabled however, this means no recent changes will be sent :c")

# noinspection PyUnreachableCode


if TESTING:
	logger.debug("DEBUGGING ")
	storage["rcid"] = 1
	wiki.fetch(amount=5)
	day_overview()
	import src.discussions
	src.discussions.fetch_discussions()
	logger.info("Test has succeeded without premature exceptions.")
	sys.exit(0)

while 1:
	time.sleep(1.0)
	try:
		client.scheduler.run()
	except KeyboardInterrupt:
		logger.info("Shutting down...")
		break
