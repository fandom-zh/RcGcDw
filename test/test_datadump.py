#  This file is part of Recent changes Goat compatible Discord webhook (RcGcDw).
#
#  RcGcDw is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  RcGcDw is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with RcGcDw.  If not, see <http://www.gnu.org/licenses/>.

import importlib
import json
from src.configloader import settings
from src.api.context import Context
from src.api.util import default_message
from src.api.hooks import formatter_hooks
from src.misc import WIKI_SCRIPT_PATH
from test.test_utilities import inject_settings
from unittest.mock import PropertyMock
import unittest


def no_formatter(ctx: Context, change: dict) -> None:
    raise NameError


inject_settings("appearance.mode", "embed")
importlib.import_module(settings.get('extensions_dir', 'extensions'), 'extensions')
formatter_hooks["no_formatter"] = no_formatter
with open("test/data/rc_objects.json", "r") as ob:
    jsons = json.loads(ob.read())
with open("test/data/rc_results.json", "r") as ob:
    results = json.loads(ob.read())


def get_objects(name: str):
    return jsons.get(name), json.dumps(results.get(name))


class TestMWFormatter(unittest.TestCase):
    def test_datadump_embed(self):
        test = default_message("datadump/generate", formatter_hooks)
        ctx = PropertyMock()
        ctx.message_type = "embed"
        ctx.event_type = "datadump/generate"
        ctx.event = "datadump/generate"
        ctx.parsedcomment = ""
        ctx.client.WIKI_SCRIPT_PATH = WIKI_SCRIPT_PATH
        ctx.webhook_url = "https://example.com"
        # ctx.client.return_value = Mock(spec=Client)
        edit_c, results = get_objects("datadump/generate")
        result = repr(test(ctx, edit_c))
        self.assertEqual(results, result)
