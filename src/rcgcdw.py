#!/usr/bin/python
# -*- coding: utf-8 -*-

# Recent changes Goat compatible Discord webhook is a project for using a webhook as recent changes page from MediaWiki.
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

import time, logging.config, requests, datetime, gettext, math, os.path, schedule, sys

import src.misc
from collections import defaultdict, Counter
from src.configloader import settings
from src.misc import add_to_dict, datafile, \
	WIKI_API_PATH, create_article_path, send_to_discord, \
	DiscordMessage
from src.rc import recent_changes
from src.exceptions import MWError
from src.i18n import ngettext, lang

_ = lang.gettext

if settings["fandom_discussions"]["enabled"]:
	import src.discussions

TESTING = True if "--test" in sys.argv else False  # debug mode, pipeline testing

# Prepare logging

logging.config.dictConfig(settings["logging"])
logger = logging.getLogger("rcgcdw")
logger.debug("Current settings: {settings}".format(settings=settings))

storage = datafile.data

# Remove previous data holding file if exists and limitfetch allows

if settings["limitrefetch"] != -1 and os.path.exists("lastchange.txt") is True:
	with open("lastchange.txt", 'r') as sfile:
		logger.info("Converting old lastchange.txt file into new data storage data.json...")
		storage["rcid"] = int(sfile.read().strip())
		datafile.save_datafile()
		os.remove("lastchange.txt")


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
				request = recent_changes.handle_mw_errors(request)
				rc = request['query']['recentchanges']
				continuearg = request["continue"]["rccontinue"] if "continue" in request else None
			except ValueError:
				logger.warning("ValueError in fetching changes")
				recent_changes.downtime_controller()
				complete = 2
			except KeyError:
				logger.warning("Wiki returned %s" % (request))
				complete = 2
			except MWError:
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
		edits_avg = src.misc.weighted_average(storage["daily_overview"]["edits"], weight, edits)
		edits = _("{value} (avg. {avg})").format(value=edits, avg=edits_avg)
		files_avg = src.misc.weighted_average(storage["daily_overview"]["new_files"], weight, files)
		files = _("{value} (avg. {avg})").format(value=files, avg=files_avg)
		admin_avg = src.misc.weighted_average(storage["daily_overview"]["admin_actions"], weight, admin)
		admin = _("{value} (avg. {avg})").format(value=admin, avg=admin_avg)
		changed_bytes_avg = src.misc.weighted_average(storage["daily_overview"]["bytes_changed"], weight, changed_bytes)
		changed_bytes = _("{value} (avg. {avg})").format(value=changed_bytes, avg=changed_bytes_avg)
		new_articles_avg = src.misc.weighted_average(storage["daily_overview"]["new_articles"], weight, new_articles)
		new_articles = _("{value} (avg. {avg})").format(value=new_articles, avg=new_articles_avg)
		unique_contributors_avg = src.misc.weighted_average(storage["daily_overview"]["unique_editors"], weight, unique_contributors)
		unique_contributors = _("{value} (avg. {avg})").format(value=unique_contributors, avg=unique_contributors_avg)
		day_score_avg = src.misc.weighted_average(storage["daily_overview"]["day_score"], weight, day_score)
		day_score = _("{value} (avg. {avg})").format(value=day_score, avg=day_score_avg)
		storage["daily_overview"].update({"edits": edits_avg, "new_files": files_avg, "admin_actions": admin_avg, "bytes_changed": changed_bytes_avg,
		             "new_articles": new_articles_avg, "unique_editors": unique_contributors_avg, "day_score": day_score_avg})
	storage["daily_overview"]["days_tracked"] += 1
	datafile.save_datafile()
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
		embed = DiscordMessage("embed", "daily_overview", settings["webhookURL"])
		embed["title"] = _("Daily overview")
		embed["url"] = create_article_path("Special:Statistics")
		embed.set_author(settings["wikiname"], create_article_path(""),
		                 icon_url=settings["appearance"]["embed"]["daily_overview"]["icon"])
		if not result[0]:
			if not settings["send_empty_overview"]:
				return  # no changes in this day
			else:
				embed["description"] = _("No activity")
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
				embed.add_field(name, value, inline=True)
		embed.finish_embed()
		send_to_discord(embed)
	else:
		logger.debug("function requesting changes for day overview returned with error code")



# Log in and download wiki information
try:
	if settings["wiki_bot_login"] and settings["wiki_bot_password"]:
		recent_changes.log_in()
	time.sleep(2.0)
	recent_changes.init_info()
except requests.exceptions.ConnectionError:
	logger.critical("A connection can't be established with the wiki. Exiting...")
	sys.exit(1)
time.sleep(3.0)  # this timeout is to prevent timeouts. It seems Fandom does not like our ~2-3 request in under a second
if settings["rc_enabled"]:
	logger.info("Script started! Fetching newest changes...")
	recent_changes.fetch(amount=settings["limitrefetch"] if settings["limitrefetch"] != -1 else settings["limit"])
	schedule.every(settings["cooldown"]).seconds.do(recent_changes.fetch)
	if settings["overview"]:
		try:
			overview_time = time.strptime(settings["overview_time"], '%H:%M')
			schedule.every().day.at("{}:{}".format(str(overview_time.tm_hour).zfill(2),
			                                       str(overview_time.tm_min).zfill(2))).do(day_overview)
			del overview_time
		except schedule.ScheduleValueError:
			logger.error("Invalid time format! Currently: {}:{}".format(
				time.strptime(settings["overview_time"], '%H:%M').tm_hour,
				time.strptime(settings["overview_time"], '%H:%M').tm_min))
		except ValueError:
			logger.error("Invalid time format! Currentely: {}. Note: It needs to be in HH:MM format.".format(
				settings["overview_time"]))
	schedule.every().day.at("00:00").do(recent_changes.clear_cache)
else:
	logger.info("Script started! RC is disabled however, this means no recent changes will be sent :c")

if 1 == 2: # additional translation strings in unreachable code
	print(_("director"), _("bot"), _("editor"), _("directors"), _("sysop"), _("bureaucrat"), _("reviewer"),
	      _("autoreview"), _("autopatrol"), _("wiki_guardian"), ngettext("second", "seconds", 1), ngettext("minute", "minutes", 1), ngettext("hour", "hours", 1), ngettext("day", "days", 1), ngettext("week", "weeks", 1), ngettext("month", "months",1), ngettext("year", "years", 1), ngettext("millennium", "millennia", 1), ngettext("decade", "decades", 1), ngettext("century", "centuries", 1))
# noinspection PyUnreachableCode


if TESTING:
	logger.debug("DEBUGGING ")
	recent_changes.recent_id -= 5
	recent_changes.file_id -= 5
	recent_changes.ids = [1]
	recent_changes.fetch(amount=5)
	day_overview()
	import src.discussions
	src.discussions.fetch_discussions()
	sys.exit(0)

while 1: 
	time.sleep(1.0)
	schedule.run_pending()
