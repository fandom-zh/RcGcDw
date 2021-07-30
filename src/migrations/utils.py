import requests
import logging
import json

discussion_logger = logging.getLogger("rcgcdw.migrations.utils")


def return_example_file(force=False) -> dict:
	try:
		if force:
			raise FileNotFoundError
		with open('settings.json.example', 'r', encoding="utf-8") as example_file:
			return json.loads(example_file.read())
	except FileNotFoundError:
		try:
			f = requests.get("https://gitlab.com/piotrex43/RcGcDw/-/raw/master/settings.json.example")
		except:
			raise
	return json.loads(f.text)

