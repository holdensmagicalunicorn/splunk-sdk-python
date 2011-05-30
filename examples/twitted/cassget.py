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

def main(argv):
    pool = pycassa.connect("twitter", ["localhost:9160"])
    users = pycassa.ColumnFamily(pool, "Users")

    # UNDONE: Skipping header values for now
    for line in sys.stdin:
        if line == '\n': break

    reader = csv.DictReader(sys.stdin)
    header = reader.fieldnames
    header.append("screen_name")
    
    writer = csv.DictWriter(output, header)
    writer.writer.writerow(header)
    for item in reader:
        user_id = item['user_id']
        details = users.get(str(user_id), columns=['screen_name'])
        item['screen_name'] = details['screen_name']
        writer.writerow(item)

if __name__ == "__main__":
    try: 
        main(sys.argv)
    except:
        import traceback
        traceback.print_exc(file=output)
    output.flush()

