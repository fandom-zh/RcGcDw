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
from typing import Tuple

from src.discord.queue import MessageQueue
from src.discord.message import DiscordMessage, DiscordMessageMetadata


def create_dummy(id: int = 0, **kwargs) -> Tuple[DiscordMessage, DiscordMessageMetadata]:
    dm = DiscordMessage(event_type="log/{}".format(id), message_type="embed", webhook_url="https://example.com/")
    dmm = DiscordMessageMetadata("POST", log_id=kwargs.get("log_id", int(id)*10), page_id=kwargs.get("page_id", int(id)),
                                 rev_id=kwargs.get("rev_id", int(id)*10), webhook_url=kwargs.get("webhook_url", "https://example.com/"))
    return dm, dmm


class TestQueue(unittest.TestCase):
    def test_add_message(self):
        queue = MessageQueue()
        for _ in range(100):
            queue.add_message(create_dummy())
        self.assertEqual(len(queue), 100)

    def test_cut_messages(self):
        queue = MessageQueue()
        for num in range(100):
            queue.add_message(create_dummy(id=num))
        queue.cut_messages(10)
        self.assertEqual(list(queue)[0][1].page_id, 10)

    def test_compare_message_to_dict(self):
        queue = MessageQueue()
        passing = [create_dummy(id=103, page_id=3928, rev_id=228848), create_dummy(id=108, page_id=3928, rev_id=228853)]
        failing = [create_dummy(id=105, page_id=39, rev_id=2288), create_dummy(id=110, page_id=392, rev_id=228)]
        for msg in passing:
            with self.subTest():
                self.assertTrue(queue.compare_message_to_dict(msg[1], {"page_id": 3928}))
        for msg in failing:
            with self.subTest():
                self.assertFalse(queue.compare_message_to_dict(msg[1], {"page_id": 3928}))

    def test_delete_all_with_matching_metadata(self):
        queue = MessageQueue()
        queue.add_message(create_dummy(id=103, page_id=500, rev_id=228844))
        for num in range(100):
            queue.add_message(create_dummy(id=num))
        queue.add_message(create_dummy(id=105, page_id=3923, rev_id=228848))
        queue_correct = MessageQueue()
        for num in range(100):
            queue_correct.add_message(create_dummy(id=num))
        queue_correct.add_message(create_dummy(id=105, page_id=3923, rev_id=228848))
        queue.delete_all_with_matching_metadata(page_id=500)
        self.assertEqual(len(queue), len(queue_correct))  # Could be better but I'm running out of time
