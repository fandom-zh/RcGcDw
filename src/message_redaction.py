from src.configloader import settings
import logging
logger = logging.getLogger("rcgcdw.message_redaction")
import sqlite3


def create_schema(cursor: sqlite3.Cursor):
	logger.info("Creating database schema...")
	cursor.executescript(
	"""BEGIN TRANSACTION;
	CREATE TABLE IF NOT EXISTS "messages" (
		"message_id"	TEXT,
		"content"	INTEGER
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

def create_connection():
	db_connection = sqlite3.connect(settings['auto_suppression'].get("db_location", ':memory:'))
	db_cursor = db_connection.cursor()
	return db_connection, db_cursor

def check_tables(cursor: sqlite3.Cursor):
	rep = cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages';")
	if not rep.fetchone():
		create_schema(cursor)

def add_entry(pageid, revid, logid, message):
