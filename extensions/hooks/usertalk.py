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

from src.api.hook import post_hook
from src.configloader import settings

# {
#     "hooks": {
#         "usertalk": {
#             "USERNAME": "USERID"
#         }
#     }
# }
discord_users = settings.get("hooks", {}).get("usertalk", {})

@post_hook
def example_post_hook(message, metadata, context, change):
    if discord_users and change["ns"] in [2, 3, 202] and not "/" in change["title"]:
        username = change["title"].split(':', 1)[1]
        if discord_users.get(username, "") and username != change["user"]:
            message.webhook_object["content"] = (message.webhook_object.get("content", "") or "") + " <@{}>".format(discord_users[username])
            if message.webhook_object["allowed_mentions"].get("users", []):
                message.webhook_object["allowed_mentions"]["users"].append(discord_users[username])
            else:
                message.webhook_object["allowed_mentions"]["users"] = [discord_users[username]]
