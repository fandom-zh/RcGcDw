from src.configloader import settings
from src.misc import send_to_discord
import logging
logger = logging.getLogger("rcgcdw.message_redaction")
import sqlite3


def create_schema():
	logger.info("Creating database schema...")
	db_cursor.executescript(
	"""BEGIN TRANSACTION;
	CREATE TABLE IF NOT EXISTS "messages" (
		"message_id"	TEXT,
		"content"	TEXT
	);
	CREATE TABLE IF NOT EXISTS "event" (
		"pageid"	INTEGER,
		"revid"	INTEGER,
		"logid"	INTEGER,
		"msg_id"	TEXT NOT NULL,
		FOREIGN KEY("msg_id") REFERENCES "messages"("message_id") ON DELETE CASCADE
	);
	COMMIT;""")
	logger.info("Database schema has been recreated.")


def create_connection() -> (sqlite3.Connection, sqlite3.Cursor):
	_db_connection = sqlite3.connect(settings['auto_suppression'].get("db_location", ':memory:'))
	_db_connection.row_factory = sqlite3.Row
	_db_cursor = db_connection.cursor()
	return _db_connection, _db_cursor


def check_tables():
	rep = db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages';")
	if not rep.fetchone():
		create_schema()


def add_entry(pageid: int, revid: int, logid: int, message):
	db_cursor.execute("INSERT INTO messages (message_id, content) VALUES (?, ?)", (message.get("message_id"), message))
	db_cursor.execute("INSERT INTO event (pageid, revid, logid, msg_id) VALUES (?, ?, ?, ?)", (pageid, revid, logid, message.get("message_id")))


def delete_messages(pageid: int):
	to_delete = db_cursor.execute("SELECT msg_id FROM event WHERE pageid = ?", (pageid))
	for message in to_delete:
		webhook_url = "{main_webhook}/messages/{message_id}".format(main_webhook=settings["webhookURL"], message_id=message[0])
		send_to_discord(None, {"request_type": "DELETE", "webhook_url": webhook_url})
	db_cursor.executemany("DELETE FROM messages WHERE message_id = ?", list_of_messageids)


def redact_messages(rev_ids: list, to_censor: dict):
	raise NotImplemented


db_connection, db_cursor = create_connection()
check_tables()
