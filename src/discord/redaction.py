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

import logging
import json
from typing import List, Union

from src.configloader import settings
from src.discord.message import DiscordMessageMetadata, DiscordMessageRaw
from src.discord.queue import send_to_discord, messagequeue
from src.fileio.database import db_cursor, db_connection
from src.i18n import redaction as redaction_translation

logger = logging.getLogger("rcgcdw.discord.redaction")  # TODO Figure out why does this logger do not work
_ = redaction_translation.gettext
#ngettext = redaction_translation.ngettext


def delete_messages(matching_data: dict):
	"""Delete messages that match given data"""
	sql_conditions = ""
	for key, value in matching_data.items():
		sql_conditions += "{} = ? AND".format(key)
	else:
		sql_conditions = sql_conditions[0:-4]  # remove last AND statement
	to_delete = db_cursor.execute("SELECT msg_id FROM event WHERE {CON}".format(CON=sql_conditions), list(matching_data.values()))
	if len(messagequeue) > 0:
		messagequeue.delete_all_with_matching_metadata(**matching_data)
	msg_to_remove = []
	logger.debug("Deleting messages for data: {}".format(matching_data))
	for message in to_delete:
		webhook_url = "{main_webhook}/messages/{message_id}".format(main_webhook=settings["webhookURL"], message_id=message[0])
		msg_to_remove.append(message[0])
		logger.debug("Removing following message: {}".format(message[0]))
		send_to_discord(None, DiscordMessageMetadata("DELETE", webhook_url=webhook_url))
	for msg in msg_to_remove:
		db_cursor.execute("DELETE FROM messages WHERE message_id = ?", (msg,))
	db_connection.commit()


def redact_messages(ids, entry_type: int, to_censor: dict):  # : Union[List[Union[str, int]], set[Union[int, str]]]
	"""Redact past Discord messages

	ids: list of ints
	entry_type: int - 0 for revdel, 1 for logdel
	to_censor: dict - logparams of message parts to censor"""
	for event_id in ids:
		if entry_type == 0:
			message = db_cursor.execute("SELECT content, message_id FROM messages INNER JOIN event ON event.msg_id = messages.message_id WHERE event.revid = ?;", (event_id, ))
		else:
			message = db_cursor.execute(
				"SELECT content, message_id FROM messages INNER JOIN event ON event.msg_id = messages.message_id WHERE event.logid = ?;",
				(event_id,))
		if settings["appearance"]["mode"] == "embed":
			if message is not None:
				row = message.fetchone()
				try:
					message = json.loads(row[0])
					new_embed = message["embeds"][0]
				except ValueError:
					logger.error("Couldn't loads JSON for message data. What happened? Data: {}".format(row[0]))
					return
				except TypeError:
					logger.error("Couldn't find entry in the database for RevDel to censor information. This is probably because the script has been recently restarted or cache cleared.")
					return
				if "user" in to_censor and "url" in new_embed["author"]:
					new_embed["author"]["name"] = _("hidden")
					new_embed["author"].pop("url")
				if "action" in to_censor and "url" in new_embed:
					new_embed["title"] = _("~~hidden~~")
					new_embed.pop("url")
				if "content" in to_censor and "fields" in new_embed:
					new_embed.pop("fields")
				if "comment" in to_censor:
					new_embed["description"] = _("~~hidden~~")
				message["embeds"][0] = new_embed
				db_cursor.execute("UPDATE messages SET content = ? WHERE message_id = ?;", (json.dumps(message), row[1],))
				db_connection.commit()
				logger.debug(message)
				send_to_discord(DiscordMessageRaw(message, settings["webhookURL"]+"/messages/"+str(row[1])), DiscordMessageMetadata("PATCH"))
			else:
				logger.debug("Could not find message in the database.")


def find_middle_next(ids: List[str], pageid: int) -> set:
	"""To address #235 RcGcDw should now remove diffs in next revs relative to redacted revs to protect information in revs that revert revdeleted information.

	:arg ids - list
	:arg pageid - int

	:return list"""
	ids = [int(x) for x in ids]
	result = set()
	ids.sort()  # Just to be sure, sort the list to make sure it's always sorted
	messages = db_cursor.execute("SELECT revid FROM event WHERE pageid = ? AND revid >= ? ORDER BY revid", (pageid, ids[0],))
	all_in_page = [x[0] for x in messages.fetchall()]
	for id in ids:
		try:
			result.add(all_in_page[all_in_page.index(id)+1])
		except (KeyError, ValueError):
			logger.debug(f"Value {id} not in {all_in_page} or no value after that.")
	return result - set(ids)
