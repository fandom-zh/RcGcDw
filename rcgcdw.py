#!/usr/bin/python
# -*- coding: utf-8 -*-

import time, logging, json, requests, datetime, re, gettext, math, random, os.path
from bs4 import BeautifulSoup
from collections import defaultdict
from urllib.parse import quote_plus
#logging.warning('Watch out!')
#DEBUG, INFO, WARNING, ERROR, CRITICAL
with open("settings.json") as sfile:
	settings = json.load(sfile)
	if settings["limitrefetch"] < settings["limit"] and settings["limitrefetch"]!=-1:
		settings["limitrefetch"] = settings["limit"]
logging.basicConfig(level=settings["verbose_level"])
if settings["limitrefetch"] != -1 and os.path.exists("lastchange.txt") == False:
	with open("lastchange.txt", 'w') as sfile:
		sfile.write("")
logging.info("Current settings: {settings}".format(settings=settings))
if settings["lang"] != "en" or settings["lang"] == "":
	lang = gettext.translation('rcgcdw', localedir='locale', languages=[settings["lang"]])
	lang.install()
else:
	_ = lambda s: s


def send(message, name, avatar):
	try:
		req = requests.post(settings["webhookURL"], data={"content": message, "avatar_url": avatar, "username": name}, timeout=10)
	except:
		pass
	
def safe_read(request, *keys):
	if request is None:
		return None
	try:
		request = request.json()
		for item in keys:
			request = request[item]
	except KeyError:
		logging.warning("Failure while extracting data from request on key {key} in {change}".format(key=item, change=request))
		return None
	except ValueError:
		logging.warning("Failure while extracting data from request in {change}".format(key=item, change=request))
		return None
	return request
	
def webhook_formatter(action, STATIC, **params):
	logging.debug("Received things: {thing}".format(thing=params))
	colornumber = None if isinstance(STATIC["color"], str) else STATIC["color"]
	data = {}
	data["embeds"] = []
	embed = defaultdict(dict)
	if "title" in params:
		article_encoded = params["title"].replace(" ", "_").replace(')', '\)')
	if re.match(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", params["user"]) is not None:
		author_url = "https://{wiki}.gamepedia.com/Special:Contributions/{user}".format(wiki=settings["wiki"], user=params["user"])
		if params["user"] not in list(recent_changes.map_ips.keys()):
			contibs = safe_read(recent_changes.safe_request("https://{wiki}.gamepedia.com/api.php?action=query&format=json&list=usercontribs&uclimit=max&ucuser={user}&ucprop=".format(wiki=settings["wiki"], user=params["user"])), "query", "usercontribs")
			if contibs is None:
				logging.warning("WARNING: Something went wrong when checking amount of contributions for given IP address")
				params["user"] = params["user"] + "(?)"
			else:
				params["user"] = "{author} ({contribs})".format(author=params["user"], contribs=len(contibs))
				recent_changes.map_ips[params["user"]]=len(contibs)
		else:
			recent_changes.map_ips[params["user"]]+=1
			params["user"] = "{author} ({amount})".format(author=params["user"], amount=recent_changes.map_ips[params["user"]])
	else:
		author_url = "https://{wiki}.gamepedia.com/User:{user}".format(wiki=settings["wiki"], user=params["user"].replace(" ", "_"))
	if action in [1, 37]: #edit or new page
		editsize = params["size"]
		print (editsize)
		if editsize > 0:
			if editsize > 6032:
				colornumber = 65280
			else:
				colornumber = 35840 + (math.floor(editsize/(52)))*256
		elif editsize < 0:
			if editsize < -6032:
				colornumber = 16711680
			else:
				colornumber = 9175040 + (math.floor((editsize*-1)/(52)))*65536
		elif editsize == 0:
			colornumber = 8750469
		link = "https://{wiki}.gamepedia.com/index.php?title={article}&curid={pageid}&diff={diff}&oldid={oldrev}".format(wiki=settings["wiki"], pageid=params["pageid"], diff=params["diff"], oldrev=params["oldrev"], article=article_encoded)
		embed["title"] = "{article} ({new}{minor}{editsize})".format(article=params["title"], editsize="+"+str(editsize) if editsize>0 else editsize, new= _("(N!) ") if action == 37 else "", minor=_("m ") if action == 1 and params["minor"] else "")
	elif action == 5: #sending files
		urls = safe_read(recent_changes.safe_request("https://{wiki}.gamepedia.com/api.php?action=query&format=json&prop=imageinfo&list=&meta=&titles={filename}&iiprop=timestamp%7Curl&iilimit=2".format(wiki=settings["wiki"], filename=params["title"])), "query", "pages")
		undolink = ""
		link ="https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		if urls is not None:
			img_info = next(iter(urls.values()))["imageinfo"]
			embed["image"]["url"] = img_info[0]["url"]
		else:
			return
		if params["overwrite"]:
			img_timestamp = [x for x in img_info[1]["timestamp"] if x.isdigit()]
			undolink = "https://{wiki}.gamepedia.com/index.php?title={filename}&action=revert&oldimage={timestamp}%21{filenamewon}".format(wiki=settings["wiki"], filename=article_encoded, timestamp="".join(img_timestamp), filenamewon = article_encoded[5:])
			embed["title"] = _("Uploaded a new version of {name}").format(name=params["title"])
			embed["fields"] = [{"name": _("Options"), "value": _("([preview]({link}) | [undo]({undolink}))").format(link=embed["image"]["url"], undolink=undolink)}]
		else:
			embed["title"] = _("Uploaded {name}").format(name=params["title"])
			article_content = safe_read(recent_changes.safe_request("https://{wiki}.gamepedia.com/api.php?action=query&format=json&prop=revisions&titles={article}&rvprop=content".format(wiki=settings["wiki"], article=quote_plus(params["title"], safe=''))), "query", "pages")
			if article_content is None:
				logging.warning("Something went wrong when getting license for the image")
				return 0
			content = list(article_content.values())[0]['revisions'][0]['*'].lower()
			if "{{license" not in content:
				license = _("**No license!**")
			else:
				matches = re.search(r"\{\{license\ (.*?)\}\}", content)
				if matches is not None:
					license = matches.group(1)
				else:
					license = "?"
			embed["fields"] = [{"name": _("Options"), "value": _("([preview]({link}))").format(link=embed["image"]["url"])}]
			params["desc"] = _("{desc}\nLicense: {license}").format(desc=params["desc"], license=license)
	elif action == 6:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Deleted page {article}").format(article=params["title"])
	elif action == 7:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Deleted redirect {article} by overwriting").format(article=params["title"])
	elif action == 14:
		link = params["targetlink"]
		params["desc"] = "{supress}. {desc}".format(desc=params["desc"], supress=_("No redirect has been made") if params["supress"] == True else _("A redirect has been made"))
		embed["title"] = _("Moved {article} to {target}").format(article = params["title"], target=params["target"])
	elif action == 15:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Moved {article} to {title} over redirect").format(article=params["title"], title=params["target"])
	elif action == 16:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Moved protection settings from {article} to {title}").format(article=params["title"], title=params["target"])
	elif action == 17:
		link = "https://{wiki}.gamepedia.com/{user}".format(wiki=settings["wiki"], user=params["blocked_user"].replace(" ", "_").replace(')', '\)'))
		user = params["blocked_user"].split(':')[1]
		time =_( "infinity and beyond") if params["duration"] == "infinite" else params["duration"] 
		embed["title"] = _("Blocked {blocked_user} for {time}").format(blocked_user=user, time=time)
	elif action == 19:
		link = "https://{wiki}.gamepedia.com/{user}".format(wiki=settings["wiki"], user=params["blocked_user"].replace(" ", "_").replace(')', '\)'))
		user = params["blocked_user"].split(':')[1]
		embed["title"] = _("Changed block settings for {blocked_user}").format(blocked_user=user)
	elif action == 18:
		link = "https://{wiki}.gamepedia.com/{user}".format(wiki=settings["wiki"], user=params["blocked_user"].replace(" ", "_").replace(')', '\)'))
		user = params["blocked_user"].split(':')[1]
		embed["title"] = _("Unblocked {blocked_user}").format(blocked_user=user)
	elif action == 25:
		link = "https://{wiki}.gamepedia.com/UserProfile:{target}".format(wiki=settings["wiki"], target=params["target"].replace(" ", "_").replace(')', '\)'))
		embed["title"] = _("Left a comment on {target}'s profile").format(target=params["target"])
	elif action == 29:
		link = "https://{wiki}.gamepedia.com/UserProfile:{target}".format(wiki=settings["wiki"], target=params["target"].replace(" ", "_").replace(')', '\)'))
		embed["title"] = _("Replied to a comment on {target}'s profile").format(target=params["target"])
	elif action == 26:
		link = "https://{wiki}.gamepedia.com/UserProfile:{target}".format(wiki=settings["wiki"], target=params["target"].replace(" ", "_").replace(')', '\)'))
		embed["title"] = _("Edited a comment on {target}'s profile").format(target=params["target"])
	elif action == 28:
		link = "https://{wiki}.gamepedia.com/UserProfile:{target}".format(wiki=settings["wiki"], target=params["target"].replace(" ", "_").replace(')', '\)'))
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
		embed["title"] = _("Edited {target}'s profile").format(target=params["target"])
		params["desc"] = _("{field} field changed to: {desc}").format(field=field, desc=params["desc"])
	elif action == 27:
		link = "https://{wiki}.gamepedia.com/UserProfile:{target}".format(wiki=settings["wiki"], target=params["target"].replace(" ", "_").replace(')', '\)'))
		embed["title"] = _("Deleted a comment on {target}'s profile").format(target=params["target"])
	elif action == 20:
		link = "https://{wiki}.gamepedia.com/"+params["user"].replace(" ", "_").replace(')', '\)')
		embed["title"] = _("Changed group membership for {target}").format(target=params["user"])
		if params["old_groups"].count(' ') < params["new_groups"].count(' '):
			embed["thumbnail"]["url"] = "https://i.imgur.com/WnGhF5g.gif"
		if len(params["old_groups"]) < 4:
			params["old_groups"] = _("none")
		if len(params["new_groups"]) < 4:
			params["new_groups"] = _("none")
		reason = "| {desc}".format(desc=params["desc"]) if params["desc"]!=_("No description provided") else ""
		params["desc"] = _("Groups changed from {old_groups} to {new_groups} {reason}").format(old_groups=params["old_groups"], new_groups=params["new_groups"], reason=reason)
	elif action == 2:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Protected {target}").format(target=params["title"])
		params["desc"] = params["settings"] + " | " + params["desc"]
	elif action == 3:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Changed protection level for {article}").format(article=params["title"])
		params["desc"] = params["settings"] + " | " + params["desc"]
	elif action == 4:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Removed protection from {article}").format(article=params["title"])
	elif action == 9:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Changed visibility of revision(s) on page {article} ").format(article=params["title"])
	elif action == 11:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Imported {article} with {count} revision(s)").format(article=params["title"], count=params["amount"])
	elif action == 8:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Restored {article}").format(article=params["title"])
	elif action == 10:
		link = "https://{wiki}.gamepedia.com/Special:RecentChanges".format(wiki=settings["wiki"])
		embed["title"] = _("Changed visibility of log events")
	elif action == 12:
		link = "https://{wiki}.gamepedia.com/Special:RecentChanges".format(wiki=settings["wiki"])
		embed["title"] = _("Imported interwiki")
	elif action == 21:
		link = "https://{wiki}.gamepedia.com/Special:RecentChanges".format(wiki=settings["wiki"])
		embed["title"] = _("Edited abuse filter number {number}").format(number=params["filternr"])
	elif action == 13:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Merged revision histories of {article} into {dest}").format(article=params["title"], dest=params["destination"])
	elif action == 22:
		link = "https://{wiki}.gamepedia.com/Special:Interwiki".format(wiki=settings["wiki"])
		embed["title"] = _("Added an entry to the interwiki table")
		params["desc"] =_("Prefix: {prefix}, website: {website} | {desc}").format(desc=params["desc"], prefix=params["prefix"], website=params["website"])
	elif action == 23:
		link = "https://{wiki}.gamepedia.com/Special:Interwiki".format(wiki=settings["wiki"])
		embed["title"] = _("Edited an entry in interwiki table")
		params["desc"] =_("Prefix: {prefix}, website: {website} | {desc}").format(desc=params["desc"], prefix=params["prefix"], website=params["website"])
	elif action == 24:
		link = "https://{wiki}.gamepedia.com/Special:Interwiki".format(wiki=settings["wiki"])
		embed["title"] = _("Deleted an entry in interwiki table")
		params["desc"] =_("Prefix: {prefix} | {desc}").format(desc=params["desc"], prefix=params["prefix"])
	elif action == 30:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Changed the content model of the page {article}").format(article=params["title"])
		params["desc"] = _("Model changed from {old} to {new}: {reason}").format(old=params["oldmodel"], new=params["newmodel"], reason=params["desc"])
	elif action == 31:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Edited the sprite for {article}").format(article=params["title"])
	elif action == 32:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Created the sprite sheet for {article}").format(article=params["title"])
	elif action == 33:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Edited the slice for {article}").format(article=params["title"])
	elif action == 34:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Created a tag \"{tag}\"").format(tag=params["additional"]["tag"])
	elif action == 35:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Deleted a tag \"{tag}\"").format(tag=params["additional"]["tag"])
	elif action == 36:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Activated a tag \"{tag}\"").format(tag=params["additional"]["tag"])
	elif action == 38:
		link = "https://{wiki}.gamepedia.com/{article}".format(wiki=settings["wiki"], article=article_encoded)
		embed["title"] = _("Deactivated a tag \"{tag}\"").format(tag=params["additional"]["tag"])
	else:
		logging.warning("No entry for {event} with params: {params}".format(event=action, params=params))
	embed["author"]["name"] = params["user"]
	embed["author"]["url"] = author_url
	embed["author"]["icon"] = STATIC["icon"]
	embed["url"] = link
	if "desc" not in params:
		params["desc"] = ""
	embed["description"] = params["desc"]
	embed["color"] = random.randrange(1, 16777215) if colornumber is None else math.floor(colornumber)
	embed["timestamp"] = STATIC["timestamp"]
	data["embeds"].append(dict(embed))
	data['avatar_url'] = settings["avatars"]["embed"]
	formatted_embed = json.dumps(data, indent=4)
	headers = {'Content-Type': 'application/json'}
	#logging.debug(data)
	result = requests.post(settings["webhookURL"], data=formatted_embed, headers=headers)
		
def first_pass(change): #I've decided to split the embed formatter and change handler, maybe it's more messy this way, I don't know
	parsedcomment = (BeautifulSoup(change["parsedcomment"], "lxml")).get_text()
	logging.debug(change)
	STATIC_VARS = {"timestamp": change["timestamp"]}
	if not parsedcomment:
		parsedcomment = _("No description provided")
	if change["type"] == "edit":
		STATIC_VARS = {**STATIC_VARS ,**{"color": settings["appearance"]["edit"]["color"], "icon": settings["appearance"]["edit"]["icon"]}}
		webhook_formatter(1,  STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment, oldrev=change["old_revid"], pageid=change["pageid"], diff=change["revid"], size=change["newlen"]-change["oldlen"], minor= True if "minor" in change else False)
	elif change["type"] == "log":
		logtype = change["logtype"]
		logaction = change["logaction"]
		combination = "{logtype}/{logaction}".format(logtype=logtype, logaction=logaction)
		logging.debug("combination is {}".format(combination))
		try:
			settings["appearance"][combination]
		except KeyError:
			STATIC_VARS = {**STATIC_VARS ,**{"color": "", "icon": ""}}
			logging.error("No value in the settings has been given for {}".format(combination))
		STATIC_VARS = {**STATIC_VARS ,**{"color": settings["appearance"][combination]["color"], "icon": settings["appearance"][combination]["icon"]}}
		if logtype=="protect" and logaction=="protect":
			webhook_formatter(2, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment, settings=change["logparams"]["description"])
		elif logtype=="protect" and logaction=="modify":
			webhook_formatter(3, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment, settings=change["logparams"]["description"])
		elif logtype=="protect" and logaction=="unprotect":
			webhook_formatter(4, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="upload" and logaction=="overwrite":
			webhook_formatter(5, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,  overwrite=True)
		elif logtype=="upload":
			webhook_formatter(5, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment,  overwrite=False)
		elif logtype=="delete" and logaction=="delete":
			webhook_formatter(6, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="delete" and logaction=="delete_redir":
			webhook_formatter(7, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="delete" and logaction=="restore":
			webhook_formatter(8, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="delete" and logaction=="revision":
			webhook_formatter(9, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="delete" and logaction=="event":
			webhook_formatter(10, STATIC_VARS, user=change["user"], desc=parsedcomment)
		elif logtype=="import" and logaction=="upload":
			webhook_formatter(11, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment, amount=change["logparams"]["count"])
		elif logtype=="import" and logaction=="interwiki":
			webhook_formatter(12, STATIC_VARS, user=change["user"], desc=parsedcomment)
		elif logtype=="merge" :
			webhook_formatter(13, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment, destination=change["logparams"]["dest_title"])
		elif logtype=="move" and logaction=="move":
			webhook_formatter(14, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment, supress=True if "suppressredirect" in change["logparams"] else False, target=change["logparams"]['target_title'], targetlink="https://{wiki}.gamepedia.com/".format(wiki=settings["wiki"]) + change["logparams"]['target_title'].replace(" ", "_")) #TODO Remove the link making in here
		elif logtype=="move" and logaction=="move_redir":
			webhook_formatter(15, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment, target=change["logparams"]["target_title"])
		elif logtype=="protect" and logaction=="move_prot":
			webhook_formatter(16, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment, target=change["logparams"]["oldtitle_title"])
		elif logtype=="block" and logaction=="block":
			webhook_formatter(17, STATIC_VARS, user=change["user"], blocked_user=change["title"], desc=parsedcomment, duration=change["logparams"]["duration"])
		elif logtype=="block" and logaction=="unblock":
			webhook_formatter(18, STATIC_VARS, user=change["user"], blocked_user=change["title"], desc=parsedcomment)
		elif logtype=="block":
			webhook_formatter(19, STATIC_VARS, user=change["user"], blocked_user=change["title"], desc=parsedcomment)
		elif logtype=="rights":
			webhook_formatter(20, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment, old_groups=' '.join(change["logparams"]["oldgroups"]), new_groups=' '.join(change["logparams"]["newgroups"]))
		elif logtype=="abusefilter":
			webhook_formatter(21, STATIC_VARS, user=change["user"], desc=parsedcomment, filternr=change["logparams"]['1'])
		elif logtype=="interwiki" and logaction=="iw_add":
			webhook_formatter(22, STATIC_VARS, user=change["user"], desc=parsedcomment, prefix=change["logparams"]['0'], website=change["logparams"]['1'])
		elif logtype=="interwiki" and logaction=="iw_edit":
			webhook_formatter(23, STATIC_VARS, user=change["user"], desc=parsedcomment, prefix=change["logparams"]['0'], website=change["logparams"]['1'])
		elif logtype=="interwiki" and logaction=="iw_delete":
			webhook_formatter(24, STATIC_VARS, user=change["user"], desc=parsedcomment, prefix=change["logparams"]['0'])
		elif logtype=="curseprofile" and logaction=="comment-created":
			webhook_formatter(25, STATIC_VARS, user=change["user"], target=change["title"].split(':')[1])
		elif logtype=="curseprofile" and logaction=="comment-edited":
			webhook_formatter(26, STATIC_VARS, user=change["user"], target=change["title"].split(':')[1])
		elif logtype=="curseprofile" and logaction=="comment-deleted":
			webhook_formatter(27, STATIC_VARS, user=change["user"], target=change["title"].split(':')[1])
		elif logtype=="curseprofile" and logaction=="profile-edited":
			webhook_formatter(28, STATIC_VARS, user=change["user"], target=change["title"].split(':')[1], field=change["logparams"]['0'], desc=change["parsedcomment"])
		elif logtype=="curseprofile" and logaction=="comment-replied":
			webhook_formatter(29, STATIC_VARS, user=change["user"], target=change["title"].split(':')[1])
		elif logtype=="contentmodel" and logaction=="change":
			webhook_formatter(30, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment, oldmodel=change["logparams" ]["oldmodel"], newmodel=change["logparams" ]["newmodel"])
		elif logtype=="sprite" and logaction=="sprite":
			webhook_formatter(31, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="sprite" and logaction=="sheet":
			webhook_formatter(32, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="sprite" and logaction=="slice":
			webhook_formatter(33, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment)
		elif logtype=="managetags" and logaction=="create":
			webhook_formatter(34, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment, additional=change["logparams"])
		elif logtype=="managetags" and logaction=="delete":
			webhook_formatter(35, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment, additional=change["logparams"])
		elif logtype=="managetags" and logaction=="activate":
			webhook_formatter(36, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment, additional=change["logparams"])
		elif logtype=="managetags" and logaction=="deactivate":
			webhook_formatter(38, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment, additional=change["logparams"])
		elif logtype=="tag" and logaction=="update":
			webhook_formatter(39, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment)
		else:
			logging.warning("No entry matches given change!")
			print (change)
			send(_("Unable to process the event"), _("error"), settings["avatars"]["no_event"])
			return
	if change["type"] == "external": #not sure what happens then, but it's listed as possible type
		logging.warning("External event happened, ignoring.")
		print (change)
		return
	elif change["type"] == "new": #new page
		STATIC_VARS = {**STATIC_VARS ,**{"color": settings["appearance"]["new"]["color"], "icon": settings["appearance"]["new"]["icon"]}}
		webhook_formatter(37, STATIC_VARS, user=change["user"], title=change["title"], desc=parsedcomment, oldrev=change["old_revid"], pageid=change["pageid"], diff=change["revid"], size=change["newlen"])

class recent_changes(object):
	starttime = time.time()
	day = datetime.date.fromtimestamp(time.time()).day
	ids = []
	map_ips = {}
	recent_id = 0
	downtimecredibility = 0
	last_downtime = 0
	if settings["limitrefetch"] != -1:
		with open("lastchange.txt", "r") as record:
			file_id = int(record.read().strip())
			logging.debug("File_id is {val}".format(val=file_id))
	else:
		file_id = 999999999 #such value won't cause trouble, and it will make sure no refetch happens
	def add_cache(self, change):
		self.ids.append(change["rcid"])
		#self.recent_id = change["rcid"]
		if len(self.ids) > settings["limit"]+5:
			self.ids.pop(0)
	def fetch(self, amount=settings["limit"]):
		last_check = self.fetch_changes(amount=amount)
		self.recent_id = last_check if last_check is not None else self.recent_id
		if settings["limitrefetch"] != -1 and self.recent_id != self.file_id:
			self.file_id = self.recent_id
			with open("lastchange.txt", "w") as record:
				record.write(str(self.file_id))
		logging.debug("Most recent rcid is: {}".format(self.recent_id))
	def fetch_changes(self, amount, clean=False):
		if len(self.ids) == 0:
			logging.debug("ids is empty, triggering clean fetch")
			clean = True
		changes = self.safe_request("https://{wiki}.gamepedia.com/api.php?action=query&format=json&list=recentchanges&rcshow=!bot&rcprop=title%7Ctimestamp%7Cids%7Cloginfo%7Cparsedcomment%7Csizes%7Cflags%7Ctags%7Cuser&rclimit={amount}&rctype=edit%7Cnew%7Clog%7Cexternal".format(wiki=settings["wiki"], amount=amount))
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
				if self.downtimecredibility > 0:
					self.downtimecredibility -= 1
				for change in changes:
					if change["rcid"] in self.ids:
						continue
					self.add_cache(change)
					if clean and not (self.recent_id == 0 and change["rcid"] > self.file_id):
						logging.debug("Rejected {val}".format(val=change["rcid"]))
						continue
					first_pass(change)
					time.sleep(1.0)
				return change["rcid"]
	def safe_request(self, url):
		try:
			request = requests.get(url, timeout=10, headers=settings["header"])
		except requests.exceptions.Timeout:
			logging.warning("Reached timeout error for request on link {url}".format(url=url))
			self.downtime_controller()
			return None
		except requests.exceptions.ConnectionError:
			logging.warning("Reached connection error for request on link {url}".format(url=url))
			self.downtime_controller()
			return None
		else:
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
			logging.error("Failure when checking Internet connection at {time}".format(time=time.strftime("%a, %d %b %Y %H:%M:%S", time.localtime())))
			self.downtimecredibility = 0
			if looped == False:
				while 1: #recursed loop, check for connection (every 10 seconds) as long as three services are down, don't do anything else
					if self.check_connection(looped=True):
						break
					time.sleep(10)
			return False
		return True
	def downtime_controller(self):
		if settings["show_updown_messages"] == False:
			return
		if self.downtimecredibility<60:
			self.downtimecredibility+=15
		else:
			if(time.time() - self.last_downtime)>1800 and self.check_connection(): #check if last downtime happened within 30 minutes, if yes, don't send a message
				send(_("{wiki} seems to be down or unreachable.").format(wiki=settings["wikiname"]), _("Connection status"), settings["avatars"]["connection_failed"])
				self.last_downtime = time.time()
	
recent_changes = recent_changes()
recent_changes.fetch(amount=settings["limitrefetch" ] if settings["limitrefetch"] != -1 else settings["limit"])

if 1 == 2:
	#some translations for later use in different places
	print ([_("{wiki} is back up!"), _("Most active user"), _("Edits made"), _("New files"), _("Admin actions"), _("Unique contributors"), _("Bytes changed"), _("Day score"), _("New articles")])
	
while 1:
	time.sleep(float(settings["cooldown"]))
	recent_changes.fetch()
	if (recent_changes.day != datetime.date.fromtimestamp(time.time()).day):
		logging.info("A brand new day! Printing the summary and clearing the cache")
		#recent_changes.summary()
		#recent_changes.clear_cache()
		recent_changes.day = datetime.date.fromtimestamp(time.time()).day
