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

"""Tail a realtime search and prints results to stdout."""

from pprint import pprint
import sys
import time

import splunk.client as client
import splunk.data as data
import splunk.results as results

import utils

def main():
    usage = "usage: follow.py <search>"
    opts = utils.parse(sys.argv[1:], {}, ".splunkrc", usage=usage)

    if len(opts.args) != 1:
        utils.error("Search expression required", 2)
    search = opts.args[0]

    service = client.connect(**opts.kwargs)

    job = service.jobs.create(
        search, 
        earliest_time="rt", 
        latest_time="rt", 
        search_mode="realtime")

    offset = 0 # Tracks the next offset we are looking for
    try:
        while True:
            count = int(job['eventCount'])
            if count <= offset:
                time.sleep(1)
                continue
            stream = job.events(offset=offset)
            reader = results.ResultsReader(stream)
            while True:
                kind = reader.read()
                if kind == None: break
                if kind == results.RESULT:
                    event = reader.value
                    current = int(event['$offset'])
                    assert current == offset # We expect them in order
                    offset = offset + 1
                    pprint(event)
    except KeyboardInterrupt:
        print "\nInterrupted."
    finally:
        job.cancel()

if __name__ == "__main__":
    main()

