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

import unittest

from src.api.context import Context
from src.discord.message import DiscordMessage, DiscordMessageMetadata
from src.api import formatter
from src.api.hook import pre_hook, post_hook
from src.api.hooks import formatter_hooks, pre_hooks, post_hooks


class ApiTesting(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = formatter_hooks.copy()

    def tearDown(self) -> None:
        formatter_hooks.update(self.temp)

    def test_embed_formatter_registration(self):
        formatter_hooks.clear()

        @formatter.embed(event="test", mode="embed")
        def test_formatter_registration(ctx: Context, change: dict) -> DiscordMessage:
            pass
        self.assertEqual(formatter_hooks["test"], test_formatter_registration)

    def test_compact_formatter_registration(self):
        formatter_hooks.clear()

        @formatter.embed(event="test", mode="compact")
        def test_formatter_registration(ctx: Context, change: dict) -> DiscordMessage:
            pass
        self.assertEqual(formatter_hooks["test"], test_formatter_registration)

    def test_overwrite_formatter_registration_warning(self):
        formatter_hooks.clear()

        @formatter.embed(event="test", mode="compact")
        def test_formatter_registration(ctx: Context, change: dict) -> DiscordMessage:
            pass

        with self.assertLogs("src.api.formatter", level="WARNING"):
            @formatter.embed(event="test", mode="compact")
            def test_other_formatter_registration(ctx: Context, change: dict) -> DiscordMessage:
                pass

    def test_formatter_aliasing(self):
        formatter_hooks.clear()

        @formatter.embed(event="test", mode="compact", aliases=["test2", "test3"])
        def test_formatter_registration(ctx: Context, change: dict) -> DiscordMessage:
            pass
        self.assertEqual(formatter_hooks["test2"], test_formatter_registration)

    def test_pre_hook_registration(self):
        pre_hooks.clear()

        @pre_hook
        def test_prehook(some_data: Context, change: dict):
            pass
        self.assertEqual(pre_hooks[0], test_prehook)

    def test_post_hook_registration(self):
        post_hooks.clear()

        @post_hook
        def test_posthook(message: DiscordMessage, metadata: DiscordMessageMetadata, context: Context, change: dict):
            pass
        self.assertEqual(post_hooks[0], test_posthook)
