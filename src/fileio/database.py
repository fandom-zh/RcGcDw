import sqlite3
import logging
from src.configloader import settings

logger = logging.getLogger("rcgcdw.fileio.database")


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
	_db_cursor = _db_connection.cursor()
	logger.debug("Database connection created")
	return _db_connection, _db_cursor


def check_tables():
	"""Check if tables exist, if not, create schema"""
	rep = db_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages';")
	if not rep.fetchone():
		logger.debug("No schema detected, creating schema!")
		create_schema()


def add_entry(pageid: int, revid: int, logid: int, message):
	"""Add an edit or log entry to the DB"""
	db_cursor.execute("INSERT INTO messages (message_id, content) VALUES (?, ?)", (message.get("id"), str(message)))
	db_cursor.execute("INSERT INTO event (pageid, revid, logid, msg_id) VALUES (?, ?, ?, ?)", (pageid, revid, logid, message.get("id")))
	logger.debug("Adding an entry to the database (pageid: {}, revid: {}, logid: {}, message: {})".format(pageid, revid, logid, message))
	db_connection.commit()

db_connection, db_cursor = create_connection()
check_tables()
