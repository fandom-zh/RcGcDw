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


class RequirementNotMet(Exception):
    """Exception raised when the requirement is not met and another requirement must be processed"""
    pass


def check_group_requirements(change_data: list, settings_data: list):
    """This function resolves group discussions and raises RequirementNotMet when requirement is not met"""
    if settings_data:
        for required_group in settings_data:
            # test all items in required_group are in change_data (one group fulfills the requirement) return the function
            if all([required_item in change_data for required_item in required_group]):
                return
        raise RequirementNotMet



@post_hook
def edit_alerts_hook(message, metadata, context, change):
    # For every alert in edit_alerts, they can have different functions and so on
    for alert in edit_alerts:
        # For every requirement, if one of the requirements passes the alert gets executed
        for requirement in alert.get("requirements", []):
            try:
                req_action = requirement.get("action", [])
                # If current action isn't in config for this requirement AND current event type is not in the requirements in settings skip this requirement
                if req_action and context.event not in req_action and context.event.split('/', 1)[0] not in req_action:
                    raise RequirementNotMet
                req_user = requirement.get("user", [])
                # If current user is not in config AND checkings for anon and user fail
                if req_user and change["user"] not in req_user and ("@__anon__" if "anon" in change else "@__user__") not in req_user:
                    raise RequirementNotMet
                req_title = requirement.get("title", [])
                if req_title and change["title"] not in req_title:
                    raise RequirementNotMet
                check_group_requirements(change.get("tags", []), requirement.get("tags", []))
                if requirement.get("categories", []):
                    for req_cats in requirement.get("categories", []):
                        try:
                            check_group_requirements(context.categories.new, reqCats.get("added", []))
                            check_group_requirements(context.categories.removed, reqCats.get("removed", []))
                        except RequirementNotMet:
                            continue
                        else:
                            break
                    else:
                        raise RequirementNotMet
            except RequirementNotMet:
                continue
            else:
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
