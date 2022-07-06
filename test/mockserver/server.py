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
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import urllib.parse
import requests

response_jsons: dict[str, dict] = {}

class EndOfContent(Exception):
    pass

def load_response(name: str):
    with open("data/response_{}.json".format(name), "r") as response_file:
        response_json: dict = json.loads(response_file.read())
        response_jsons[name] = response_json


def get_response(name: str):
    return response_jsons.get(name)


[load_response(x) for x in ["recentchanges", "recentchanges2", "init", "error", "siteinfo", "image", "userinfo"]]


messages_collector = []
askedfor = False

# Return server response based on some output from Minecraft Wiki
class MockServerRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global askedfor
        # We assume testing will be for API endpoint only since RcGcDw doesn't do requests to other URLs so no need to check main path
        # For simplicity, return a dictionary of query arguments, we assume duplicate keys will not appear
        query = {k: y for (k, y) in urllib.parse.parse_qsl(self.path.split("?")[1])}
        if query.get("action") == "query":
            # Regular pooled query for recentchanges
            if query.get("list") == "recentchanges":
                self.send_essentials_ok()
                if askedfor is False:
                    # Limit amount of events accordingly to required amount just in case
                    response_jsons["recentchanges"]["query"]["recentchanges"] = get_response("recentchanges")["query"]["recentchanges"][0:int(query.get("rclimit", 20))]
                    response_content = json.dumps(get_response("recentchanges"))
                    askedfor = True
                else:
                    response_jsons["recentchanges2"]["query"]["recentchanges"] = get_response("recentchanges2")["query"]["recentchanges"][0:int(query.get("rclimit", 20))]
                    response_content = json.dumps(get_response("recentchanges2"))
                self.wfile.write(response_content.encode('utf-8'))
            # Init info
            elif query.get("list") == "tags" and query.get("meta") == "allmessages|siteinfo":
                self.send_essentials_ok()
                response_content = json.dumps(get_response("init"))
                self.wfile.write(response_content.encode('utf-8'))
            elif query.get("meta") == "siteinfo":
                self.send_essentials_ok()
                response_content = json.dumps(get_response("siteinfo"))
                self.wfile.write(response_content.encode('utf-8'))
            elif query.get("prop") == "imageinfo|revisions":
                self.send_essentials_ok()
                response_content = json.dumps(get_response("image"))
                self.wfile.write(response_content.encode('utf-8'))
            elif query.get("list") == "usercontribs":
                self.send_essentials_ok()
                response_content = json.dumps(get_response("userinfo"))
                self.wfile.write(response_content.encode('utf-8'))
            else:
                self.send_response(400)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                response_content = json.dumps(get_response("error"))
                self.wfile.write(response_content.encode('utf-8'))
        elif query.get("action") == "compare":
            self.send_essentials_ok()
            name = "diff{}{}".format(query.get("fromrev"), query.get("torev"))
            load_response(name)
            response_content = json.dumps(get_response(name))
            self.wfile.write(response_content.encode('utf-8'))

    def do_POST(self):
        self.read_ok_collect(method="POST")

    def do_PATCH(self):
        self.read_ok_collect(method="PATCH")

    def do_DELETE(self):
        self.read_ok_collect(method="DELETE")

    def read_ok_collect(self, method: str):
        content_length = int(self.headers['Content-Length'])
        patch_data = self.rfile.read(content_length)
        if patch_data:
            messages_collector.append(json.loads(patch_data.decode('utf-8')))
        else:
            messages_collector.append(method + self.path)
        self.send_essentials_ok()
        self.wfile.write(json.dumps({"id": len(messages_collector)}).encode('utf-8'))

    def send_essentials_ok(self):
        self.send_response(requests.codes.ok)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()


def start_mock_server(port, config):
    mock_server = HTTPServer(('localhost', port), MockServerRequestHandler)
    try:
        print("Server started successfully at http://localhost:{}".format(port))
        while 1:
            if (len(messages_collector) < 13 and config.config == 1) or (len(messages_collector) < 11 and config.config == 2):
                mock_server.handle_request()
            else:
                raise EndOfContent
    except KeyboardInterrupt:
        print("Shutting down...")
    except EndOfContent:
        with open("results/results{}.json".format(config.config), "r") as proper_results:
            if proper_results.read() == json.dumps(messages_collector):
                print("Results are correct!")
            else:
                print("Results are incorrect, saving failed results to resultsfailed{}.json".format(config.config))
                with open("results/resultsfailed{}.json".format(config.config), "w") as file_to_write:
                    file_to_write.write(json.dumps(messages_collector))
