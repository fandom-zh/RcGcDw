import logging

from src.configloader import settings
from src.discord.message import DiscordMessageMetadata, DiscordMessage
from src.discord.queue import send_to_discord, messagequeue
from src.fileio.database import db_cursor, db_connection

logger = logging.getLogger("rcgcdw.discord.redaction")


def delete_messages(matching_data: dict):
	"""Delete messages that match given data"""
	sql_conditions = ""
	args = []
	for data in matching_data.items():
		sql_conditions += "? = ? AND"
		args.extend(data)
	else:
		sql_conditions = sql_conditions[0:-4]  # remove last AND statement
	to_delete = db_cursor.execute("SELECT msg_id FROM event WHERE {CON}".format(CON=sql_conditions), args)
	if len(messagequeue) > 0:
		messagequeue.delete_all_with_matching_metadata(**matching_data)
	msg_to_remove = []
	logger.debug("Deleting messages for data: {}".format(matching_data))
	for message in to_delete:
		webhook_url = "{main_webhook}/messages/{message_id}".format(main_webhook=settings["webhookURL"], message_id=message[0])
		msg_to_remove.append(message[0])
		logger.debug("Removing following message: {}".format(message[0]))
		send_to_discord(None, DiscordMessageMetadata("DELETE", webhook_url=webhook_url))
		db_cursor.execute("DELETE FROM messages WHERE message_id = ?", (message[0],))
	db_connection.commit()


def redact_messages(ids: list, entry_type: int, to_censor: dict):
	"""Redact past Discord messages

	ids: list of ints
	entry_type: int - 0 for revdel, 1 for logdel
	to_censor: dict - logparams of message parts to censor"""
	for event_id in ids:
		if entry_type == 0:  # TODO check if queries are proper
			message = db_cursor.execute("SELECT content FROM messages INNER JOIN event ON event.msg_id = messages.message_id WHERE event.revid = ?;", event_id)
		else:
			message = db_cursor.execute(
				"SELECT content FROM messages INNER JOIN event ON event.msg_id = messages.message_id WHERE event.logid = ?;",
				event_id)
		if settings["appearance"]["mode"] == "embed":
			if message is not None:
				message = message.fetchone()
				new_embed = message["embeds"][0]
				if "user" in to_censor:
					new_embed["author"]["name"] = _("Removed")
					del new_embed["author"]["url"]
				if "action" in to_censor:
					new_embed["title"] = _("Removed")
					del new_embed["url"]
				if "comment" in to_censor:
					new_embed["description"] = _("Removed")
				message["embeds"][0] = new_embed
				# TODO somehow send nly important data as PATCH?
				send_to_discord()

	raise NotImplemented
