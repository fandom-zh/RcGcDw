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

import argparse
import json

import server
import pathlib
import shutil
import sys
import time

parser = argparse.ArgumentParser(description="Test RcGcDw with mocked data")
parser.add_argument("--config", type=int, default=1, help="Number of config to use while testing the mocked server (default=1). Number corresponds to files in configs/settings#.json")
parser.add_argument("--ignore-config", action='store_false', help="Ignore lack of existing config.json")
parser.add_argument("--no-client", action='store_true', help="Skip starting the client")
command_args = parser.parse_args()

# Backup old settings.json and copy from configs/settingsX.json to proper relative location
if not command_args.no_client:
    new_settings = pathlib.Path(__file__).parent.absolute().joinpath("configs/settings{}.json".format(command_args.config))
    old_config = pathlib.Path(__file__).parent.resolve().parent.resolve().parent.resolve().joinpath("settings.json")  # Should be root of RcGcDw
    if not old_config.exists() and command_args.ignore_config:
        print("Cannot find currently used settings.json! Exiting to prevent potential damage.")
        sys.exit(2)
    backup_filename = pathlib.Path(__file__).parent.resolve().parent.resolve().parent.resolve().joinpath("settings.json.{}.bak".format(int(time.time())))
    if backup_filename.exists():
        print("Backup file under same name exists! Exiting.")
        sys.exit(3)
    shutil.move(old_config, backup_filename)
    shutil.copy(new_settings, old_config)
    # revert data file to some low number
    with open(pathlib.Path(__file__).parent.resolve().parent.resolve().parent.resolve().joinpath("data.json"), "r") as data_file:
        data_file_data = json.loads(data_file.read())
        data_file_data["rcid"] = 5
    with open(pathlib.Path(__file__).parent.resolve().parent.resolve().parent.resolve().joinpath("data.json"), "w") as data_file:
        data_file.write(json.dumps(data_file_data, indent=4))

# Start mock server
server.start_mock_server(8080, command_args)

# Revert file changes
if not command_args.no_client:
    shutil.copy(backup_filename, old_config)