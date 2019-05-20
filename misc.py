# -*- coding: utf-8 -*-

# Recent changes Gamepedia compatible Discord webhook is a project for using a webhook as recent changes page from MediaWiki.
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

import json, logging, sys, re
from html.parser import HTMLParser
from configloader import settings
import gettext

# Initialize translation
t = gettext.translation('misc', localedir='locale', languages=[settings["lang"]])
_ = t.gettext

# Create a custom logger

misc_logger = logging.getLogger("rcgcdw.misc")

data_template = {"rcid": 99999999999,
                 "daily_overview": {"edits": None, "new_files": None, "admin_actions": None, "bytes_changed": None,
                                    "new_articles": None, "unique_editors": None, "day_score": None, "days_tracked": 0}}


def generate_datafile():
	"""Generate a data.json file from a template."""
	try:
		with open("data.json", 'w') as data:
			data.write(json.dumps(data_template, indent=4))
	except PermissionError:
		misc_logger.critical("Could not create a data file (no permissions). No way to store last edit.")
		sys.exit(1)


def load_datafile() -> object:
	"""Read a data.json file and return a dictionary with contents
	:rtype: object
	"""
	try:
		with open("data.json") as data:
			return json.loads(data.read())
	except FileNotFoundError:
		generate_datafile()
		misc_logger.info("The data file could not be found. Generating a new one...")
		return data_template


def save_datafile(data):
	"""Overwrites the data.json file with given dictionary"""
	try:
		with open("data.json", "w") as data_file:
			data_file.write(json.dumps(data, indent=4))
	except PermissionError:
		misc_logger.critical("Could not modify a data file (no permissions). No way to store last edit.")
		sys.exit(1)


def weighted_average(value, weight, new_value):
	"""Calculates weighted average of value number with weight weight and new_value with weight 1"""
	return round(((value * weight) + new_value) / (weight + 1), 2)


def link_formatter(link):
	"""Formats a link to not embed it"""
	return "<" + re.sub(r"([ \)])", "\\\\\\1", link) + ">"


class ContentParser(HTMLParser):
	more = _("\n__And more__")
	current_tag = ""
	small_prev_ins = ""
	small_prev_del = ""
	ins_length = len(more)
	del_length = len(more)
	added = False

	def handle_starttag(self, tagname, attribs):
		if tagname == "ins" or tagname == "del":
			self.current_tag = tagname
		if tagname == "td" and 'diff-addedline' in attribs[0]:
			self.current_tag = tagname + "a"
		if tagname == "td" and 'diff-deletedline' in attribs[0]:
			self.current_tag = tagname + "d"
		if tagname == "td" and 'diff-marker' in attribs[0]:
			self.added = True

	def handle_data(self, data):
		data = re.sub(r"(`|_|\*|~|<|>|{|}|@|/|\|)", "\\\\\\1", data, 0)
		if self.current_tag == "ins" and self.ins_length <= 1000:
			self.ins_length += len("**" + data + '**')
			if self.ins_length <= 1000:
				self.small_prev_ins = self.small_prev_ins + "**" + data + '**'
			else:
				self.small_prev_ins = self.small_prev_ins + self.more
		if self.current_tag == "del" and self.del_length <= 1000:
			self.del_length += len("~~" + data + '~~')
			if self.del_length <= 1000:
				self.small_prev_del = self.small_prev_del + "~~" + data + '~~'
			else:
				self.small_prev_del = self.small_prev_del + self.more
		if (self.current_tag == "afterins" or self.current_tag == "tda") and self.ins_length <= 1000:
			self.ins_length += len(data)
			if self.ins_length <= 1000:
				self.small_prev_ins = self.small_prev_ins + data
			else:
				self.small_prev_ins = self.small_prev_ins + self.more
		if (self.current_tag == "afterdel" or self.current_tag == "tdd") and self.del_length <= 1000:
			self.del_length += len(data)
			if self.del_length <= 1000:
				self.small_prev_del = self.small_prev_del + data
			else:
				self.small_prev_del = self.small_prev_del + self.more
		if self.added:
			if data == '+' and self.ins_length <= 1000:
				self.ins_length += 1
				if self.ins_length <= 1000:
					self.small_prev_ins = self.small_prev_ins + '\n'
				else:
					self.small_prev_ins = self.small_prev_ins + self.more
			if data == '−' and self.del_length <= 1000:
				self.del_length += 1
				if self.del_length <= 1000:
					self.small_prev_del = self.small_prev_del + '\n'
				else:
					self.small_prev_del = self.small_prev_del + self.more
			self.added = False

	def handle_endtag(self, tagname):
		if tagname == "ins":
			self.current_tag = "afterins"
		elif tagname == "del":
			self.current_tag = "afterdel"
		else:
			self.current_tag = ""
