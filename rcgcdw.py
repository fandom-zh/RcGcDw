#!/usr/bin/python
# -*- coding: utf-8 -*-

import time, logging, json, requests, datetime
from bs4 import BeautifulSoup
logging.basicConfig(level=logging.DEBUG)
#logging.warning('Watch out!')
#DEBUG, INFO, WARNING, ERROR, CRITICAL

with open("settings.json") as sfile:
	settings = json.load(sfile)
logging.info("Current settings: {settings}".format(settings=settings))

def send(message, name, avatar):
	req = requests.post(settings["webhookURL"], data={"content": message, "avatar_url": avatar, "username": name}, timeout=10)
	
def webhook_formatter(action, **params):
	
	
def first_pass(change):
	parsedcomment = (BeautifulSoup(change["parsedcomment"], "lxml")).get_text()
	if not parsedcomment:
		parsedcomment = "No description provided"
	if change["type"] == "edit":
		minor = True if "minor" in change else False
		webhook_formatter(1, user=change["user"], change["title"].encode('utf-8'), cparsedcomment, change["old_revid"], change["pageid"], change["revid"], change["timestamp"], change["newlen"]-change["oldlen"], minor)

class recent_changes(object):
	starttime = time.time()
	day = datetime.date.fromtimestamp(time.time()).day
	cache = []
	ids = []
	recent_id = 0
	downtimecredibility = 0
	def add_cache(self, change):
		self.cache.append(change)
		self.ids.append(change["rcid"])
		self.recent_id = change["rcid"]
		if len(self.ids) > settings["limit"]+5:
			self.ids.pop(0)
	def fetch(self):
		self.recent_id = self.fetch_changes()
	def fetch_changes(self, clean=False):
		if len(self.cache) == 0:
			logging.debug("cache is empty, triggering clean fetch")
			clean = True
		changes = safe_request("https://{wiki}.gamepedia.com/api.php?action=query&format=json&list=recentchanges&rcshow=!bot&rcprop=title%7Ctimestamp%7Cids%7Cloginfo%7Cparsedcomment%7Csizes%7Cflags%7Ctags%7Cuser&rclimit={amount}&rctype=edit%7Cnew%7Clog%7Cexternal".format(wiki=settings["wiki"], amount=settings["limit"]))
		if changes:
			try:
				changes = changes.json()['query']['recentchanges']
				changes.reverse()
			except ValueError:
				logging.warning("ValueError in fetching changes")
				self.downtime_controller()
				return None
			except KeyError:
				logging.warning("Wiki returned %s" % (request.json()))
				return None
			else:
				for change in pchanges:
					if change["rcid"] in self.ids:
						continue
					self.add_cache(change)
					if clean:
						continue
					
	def safe_request(self, url):
		try:
			request = requests.get(url, timeout=10, headers=settings["header"])
		except requests.exceptions.Timeout:
			logging.warning("Reached timeout error for request on link {url}")
			self.downtime_controller()
			return None
		except requests.exceptions.ConnectionError:
			logging.warning("Reached connection error for request on link {url}")
			self.downtime_controller()
			return None
		else:
			return request
	def check_connection(self):
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
			logging.error("Failure when checking Internet connection at {time}".format(time=time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())))
			return False
		return True
	def downtime_controller(self):
		if self.downtimecredibility<60:
			self.downtimecredibility+=15
		else:
			if self.check_connection():
				send(_("Minecraft Wiki seems to be down or unreachable."), _("Connection status"), _("https://i.imgur.com/2jWQEt1.png"))
	
recent_changes = recent_changes()
	
while 1:
	time.sleep(settings["cooldown"])
	if (recent_changes.day != datetime.date.fromtimestamp(time.time()).day):
		logging.info("A brand new day! Printing the summary and clearing the cache")
		recent_changes.summary()
		recent_changes.clear_cache()
