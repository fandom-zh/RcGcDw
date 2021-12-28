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
import pprint
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import urllib.parse
import requests

response_jsons: dict[str, dict] = {}


def load_response(name: str):
    with open("data/{}.json".format(name), "r") as response_file:
        response_json: dict = json.loads(response_file.read())
        response_jsons[name] = response_json


def get_response(name: str):
    return response_jsons.get(name)


[load_response(x) for x in ["response_recentchanges", "response_recentchanges2", "response_init", "response_error", "response_siteinfo"
                            "response_image", "response_userinfo"]]


messages_collector = []


# Return server response based on some output from Minecraft Wiki
class MockServerRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        # We assume testing will be for API endpoint only since RcGcDw doesn't do requests to other URLs so no need to check main path
        # For simplicity, return a dictionary of query arguments, we assume duplicate keys will not appear
        query = {k: y for (k, y) in urllib.parse.parse_qsl(self.path.split("?")[1])}
        if query.get("action") == "query":
            # Regular pooled query for recentchanges
            if query.get("list") == "recentchanges":
                self.send_essentials_ok()
                if len(messages_collector) == 0:
                    # Limit amount of events accordingly to required amount just in case
                    response_jsons["response_recentchanges"]["query"]["recentchanges"] = get_response("response_recentchanges")["query"]["recentchanges"][0:int(query.get("rclimit", 20))]
                    response_content = json.dumps(get_response("response_recentchanges"))
                else:
                    response_jsons["response_recentchanges2"]["query"]["recentchanges"] = get_response("response_recentchanges2")["query"]["recentchanges"][0:int(query.get("rclimit", 20))]
                    response_content = json.dumps(get_response("response_recentchanges2"))
                self.wfile.write(response_content.encode('utf-8'))
            # Init info
            elif query.get("list") == "tags" and query.get("meta") == "allmessages|siteinfo":
                self.send_essentials_ok()
                response_content = json.dumps(get_response("response_init"))
                self.wfile.write(response_content.encode('utf-8'))
            elif query.get("meta") == "siteinfo":
                self.send_essentials_ok()
                response_content = json.dumps(get_response("response_siteinfo"))
                self.wfile.write(response_content.encode('utf-8'))
            elif query.get("prop") == "imageinfo|revisions":
                self.send_essentials_ok()
                response_content = json.dumps(get_response("response_image"))
                self.wfile.write(response_content.encode('utf-8'))
            elif query.get("list") == "usercontribs":
                self.send_essentials_ok()
                response_content = json.dumps(get_response("response_userinfo"))
                self.wfile.write(response_content.encode('utf-8'))
            else:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                response_content = json.dumps(get_response("response_error"))
                self.wfile.write(response_content.encode('utf-8'))

    def do_POST(self):
        self.read_ok_collect()

    def do_PATCH(self):
        self.read_ok_collect()

    def do_DELETE(self):
        self.read_ok_collect()

    def read_ok_collect(self):
        content_length = int(self.headers['Content-Length'])
        patch_data = self.rfile.read(content_length)
        messages_collector.append(patch_data.decode('utf-8'))
        self.send_essentials_ok()
        self.wfile.write(json.dumps({"id": len(messages_collector)}).encode('utf-8'))

    def send_essentials_ok(self):
        self.send_response(requests.codes.ok)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()


def start_mock_server(port):
    mock_server = HTTPServer(('localhost', port), MockServerRequestHandler)
    try:
        print("Server started successfully at http://localhost:{}".format(port))
        mock_server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down...")
        print(pprint.pprint(messages_collector))
        pass
