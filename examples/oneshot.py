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

"""A command line utility for executing oneshot Splunk searches."""

import sys, utils, socket, StringIO
from splunk.client import connect
import splunk.results as results
from pprint import pprint

def pretty(response):
    reader = results.ResultsReader(response)
    while True:
        kind = reader.read()
        if kind == None: break
        if kind == results.RESULT:
            event = reader.value
            pprint(event)

def main():
    usage = "usage: oneshot.py <search>"

    argv = sys.argv[1:]

    opts = utils.parse(argv, {}, ".splunkrc", usage=usage)
    opts.kwargs["namespace"] = "*:*"
    service = connect(**opts.kwargs)

    socket.setdefaulttimeout(None)

    response = service.jobs.create(opts.args, exec_mode="oneshot")

    pretty(response)

if __name__ == "__main__":
    main()