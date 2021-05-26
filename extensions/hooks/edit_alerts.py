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
#         "edit_alerts": [
#             {
#                 "content": "DISCORD MARKDOWN TEXT",
#                 "allowed_mentions": {
#                     "users": ["USERID"],
#                     "roles": ["ROLEID"]
#                 },
#                 "requirements": [
#                     {
#                         "action": [
#                             "edit",
#                             "delete/delete",
#                             "delete"
#                         ],
#                         "user": [
#                             "USERNAME",
#                             "@__anon__",
#                             "@__user__"
#                         ],
#                         "title": [
#                             "PAGETITLE"
#                         ],
#                         "tags": [
#                             ["EDIT TAG", "AND EDIT TAG"],
#                             ["OR EDIT TAG"]
#                         ],
#                         "categories": [
#                             {
#                                 "added": [
#                                     ["CATEGORY", "AND CATEGORY"],
#                                     ["OR CATEGORY"]
#                                 ],
#                                 "removed": [
#                                     ["CATEGORY", "AND CATEGORY"],
#                                     ["OR CATEGORY"]
#                                 ]
#                             }
#                         ]
#                     }
#                 ]
#             }
#         ]
#     }
# }
edit_alerts = settings.get("hooks", {}).get("edit_alerts", [])

@post_hook
def edit_alerts_hook(message, metadata, context, change):
    for alert in edit_alerts:
        for requirement in alert.get("requirements", []):
            reqAction = requirement.get("action", [])
            if reqAction and context.event not in reqAction and context.event.split('/', 1)[0] not in reqAction:
                continue
            reqUser = requirement.get("user", [])
            if reqUser and change["user"] not in reqUser and ("@__anon__" if "anon" in change else "@__user__") not in reqUser:
                continue
            reqTitle = requirement.get("title", [])
            if reqTitle and change["title"] not in reqTitle:
                continue
            if requirement.get("tags", []):
                for reqTags in requirement.get("tags", []):
                    for reqTag in reqTags:
                        if reqTag not in change.get("tags", []):
                            break
                    else:
                        break
                else:
                    continue
            if requirement.get("categories", []):
                for reqCats in requirement.get("categories", []):
                    if reqCats.get("added", []):
                        for addedCats in reqCats.get("added", []):
                            for addedCat in addedCats:
                                if addedCat not in context.categories.new:
                                    break
                            else:
                                break
                        else:
                            continue
                    if reqCats.get("removed", []):
                        for removedCats in reqCats.get("removed", []):
                            for removedCat in removedCats:
                                if removedCat not in context.categories.removed:
                                    break
                            else:
                                break
                        else:
                            continue
                    break
                else:
                    continue
            break
        else:
            continue
        message.webhook_object["content"] = (message.webhook_object.get("content", "") or "") + alert["content"]
        allowed_mentions = message.webhook_object["allowed_mentions"]
        if alert.get("allowed_mentions", {}).get("users", []):
            if not allowed_mentions.get("users", []):
                allowed_mentions["users"] = []
            allowed_mentions["users"].extend(alert["allowed_mentions"]["users"])
        if alert.get("allowed_mentions", {}).get("roles", []):
            if not allowed_mentions.get("roles", []):
                allowed_mentions["roles"] = []
            allowed_mentions["roles"].extend(alert["allowed_mentions"]["roles"])
