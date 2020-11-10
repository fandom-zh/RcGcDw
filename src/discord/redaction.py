import logging

from src.configloader import settings
from src.discord.message import DiscordMessageMetadata
from src.discord.queue import send_to_discord, messagequeue
from src.fileio.database import db_cursor, db_connection

logger = logging.getLogger("rcgcdw.discord.redaction")


def delete_messages(pageid: int):
	"""Delete messages that match that pageid"""
	logger.debug(type(pageid))
	to_delete = db_cursor.execute("SELECT msg_id FROM event WHERE pageid = ?", (pageid,))
	if len(messagequeue) > 0:
		messagequeue.delete_all_with_matching_metadata(pageid=pageid)
	msg_to_remove = []
	logger.debug("Deleting messages for pageid: {}".format(pageid))
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
	raise NotImplemented
