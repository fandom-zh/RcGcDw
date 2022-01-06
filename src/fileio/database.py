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

import sqlite3
import logging
from src.configloader import settings

logger = logging.getLogger("rcgcdw.fileio.database")


def catch_db_OperationalError(func):
	def catcher(*args, **kwargs):
		global db_connection, db_cursor
		try:
			func(*args, **kwargs)
		except sqlite3.OperationalError:
			if settings.get("error_tolerance", 0) > 1:
				logger.error("SQL database has been damaged during operation. This can indicate it has been deleted "
							"during runtime or damaged in some way. If it wasn't purposeful you may want to take a look "
							"at your disk state. In the meantime, RcGcDw will attempt to recover by re-creating empty database.")
				db_connection, db_cursor = create_connection()
				check_tables()
				func(*args, **kwargs)
			else:
				raise
		return func

	return catcher


def create_schema():
	"""Creates a SQLite database schema"""
	logger.info("Creating database schema...")
	db_cursor.executescript(
	"""BEGIN TRANSACTION;
	CREATE TABLE IF NOT EXISTS "messages" (
		"message_id"	TEXT,
		"content"	TEXT,
		PRIMARY KEY("message_id")
	);
	CREATE TABLE IF NOT EXISTS "event" (
		"pageid"	INTEGER,
		"revid"	INTEGER,
		"logid"	INTEGER,
		"msg_id"	TEXT NOT NULL,
		PRIMARY KEY("msg_id"),
		FOREIGN KEY("msg_id") REFERENCES "messages"("message_id") ON DELETE CASCADE
	);
	COMMIT;""")
	logger.info("Database schema has been recreated.")


def create_connection() -> (sqlite3.Connection, sqlite3.Cursor):
	"""Creates a connection to the database"""
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


@catch_db_OperationalError
def add_entry(pageid: int, revid: int, logid: int, message, message_id: str):
	"""Add an edit or log entry to the DB
	:param message:
	:param logid:
	:param revid:
	:param pageid:
	:param message_id:
	"""
	db_cursor.execute("INSERT INTO messages (message_id, content) VALUES (?, ?)", (message_id, message))
	db_cursor.execute("INSERT INTO event (pageid, revid, logid, msg_id) VALUES (?, ?, ?, ?)",
					  (pageid, revid, logid, message_id))
	logger.debug(
		"Adding an entry to the database (pageid: {}, revid: {}, logid: {}, message: {})".format(pageid, revid, logid,
																								 message))
	db_connection.commit()


@catch_db_OperationalError
def clean_entries():
	"""Cleans entries that are 50+"""
	cleanup = db_cursor.execute(
		"SELECT message_id FROM messages WHERE message_id NOT IN (SELECT message_id FROM messages ORDER BY message_id desc LIMIT 50);")
	for row in cleanup:
		db_cursor.execute("DELETE FROM messages WHERE message_id = ?", (row[0],))
	cleanup = db_cursor.execute(
		"SELECT msg_id FROM event WHERE msg_id NOT IN (SELECT msg_id FROM event ORDER BY msg_id desc LIMIT 50);")
	for row in cleanup:
		db_cursor.execute("DELETE FROM event WHERE msg_id = ?", (row[0],))
	db_connection.commit()


db_connection, db_cursor = create_connection()
check_tables()
