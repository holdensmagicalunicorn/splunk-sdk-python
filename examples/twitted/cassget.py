#!/usr/bin/env python
#
# Copyright 2011 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# UNDONE: A note on debugging - eg: "cat test.csv | ./cassget.py" and use
# of the Logger class.

from pprint import pprint # UNDONE

import csv
import sys

import pycassa

# Tees output to a logfile for debugging
class Logger:
    def __init__(self, filename):
        self.log = open(filename, 'w')

    def flush(self):
        self.log.flush()

    def write(self, message):
        self.log.write(message)
        sys.stdout.write(message)

output = sys.stdout # Logger("log")

# Statuses lookup fields, with optional output field name
sfields = {
    'retweeted_status_id': None,
    'retweeted': None,
    'source': "status_source",
}

# Users lookup fields, with optional output field names
ufields = {
    'created_at': "user_created_at",
    'followers_count': "user_followers_count",
    'friends_count': "user_friends_count",
    'name': "user_name",
    'screen_name': "user_screen_name",
    'statuses_count': "user_statuses_count",
    'verified': "user_verified",
}

def main(argv):
    pool = pycassa.connect("twitter", ["localhost:9160"])
    statuses = pycassa.ColumnFamily(pool, "Statuses")
    users = pycassa.ColumnFamily(pool, "Users")

    # UNDONE: Skipping header values for now
    for line in sys.stdin:
        if line == '\n': break

    reader = csv.DictReader(sys.stdin)
    header = reader.fieldnames

    # Extend the resultset with additional status & user fields
    for fname in sfields.keys():
        header.append(sfields.get(fname, fname))
    for fname in ufields.keys():
        header.append(ufields.get(fname, fname))

    writer = csv.DictWriter(output, header)
    writer.writer.writerow(header)
    for item in reader:
        # Join record with status details
        status = statuses.get(str(item['id']), columns=sfields)
        for source in sfields.keys(): 
            target = sfields.get(source, source)
            item[target] = status.get(source, None)

        # Join record with user details
        user = users.get(str(item['user_id']), columns=ufields)
        for source in ufields.keys(): 
            target = ufields.get(source, source)
            item[target] = user.get(source, None)

        # Output the extended record
        writer.writerow(item)

if __name__ == "__main__":
    try: 
        main(sys.argv)
    except:
        import traceback
        traceback.print_exc(file=output)
    # output.flush()

