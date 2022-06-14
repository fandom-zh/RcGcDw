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

def add_mention(message, userid):
    """This function adds a mention for the userid"""
    message.webhook_object["content"] = (message.webhook_object.get("content", "") or "") + " <@{}>".format(userid)
    if message.webhook_object["allowed_mentions"].get("users", []):
        if userid not in message.webhook_object["allowed_mentions"]["users"]:
            message.webhook_object["allowed_mentions"]["users"].append(userid)
    else:
        message.webhook_object["allowed_mentions"]["users"] = [userid]

@post_hook
def usertalk_hook(message, metadata, context, change):
    if not discord_users:
        return
    if context.feed_type in ["recentchanges", "abuselog"] and change["ns"] in [2, 3, 202, 1200] and "/" not in change["title"]:
        username = change["title"].split(':', 1)[1]
        if discord_users.get(username, "") and username != change["user"]:
            add_mention(message, discord_users[username])
    elif context.feed_type == "discussion" and context.event == "discussion/wall" and change["forumName"].endswith(' Message Wall'):
        username = change["forumName"][:-13]
        author = None
        if change["creatorIp"]:
            author = change["creatorIp"][1:]
        elif change["createdBy"]["name"]:
            author = change["createdBy"]["name"]
        if discord_users.get(username, "") and username != author:
            add_mention(message, discord_users[username])
