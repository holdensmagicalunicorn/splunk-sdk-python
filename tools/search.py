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

"""A simple CLI for executing searches against the export endpoint."""

import sys

import splunk
import cmdopts

rules = {
    "earliest_time": {
        'flags': ["--earliest_time"],
        'help': "",
    },
    "latest_time": {
        'flags': ["--latest_time"],
        'help': "",
    },
    "output_mode": {
        'flags': ["--output_mode"],
        'help': "",
    },
    # UNDONE: Add additional export/search arguments
}

def main(argv):
    usage = 'usage: %prog [options] "query"'
    parser = cmdopts.parser(rules, usage=usage)
    opts = parser.loadrc(".splunkrc").parse(argv).result

    if len(opts.args) != 1:
        parser.error("Single query argument required")

    context = splunk.connect(**opts.kwargs)

    # Extract search options
    kwargs = {}
    for key in rules.keys():
        if opts.kwargs.has_key(key):
            kwargs[key] = opts.kwargs[key]

    query = opts.args[0]
    result = context.get('search/jobs/export', search=query, **kwargs)
    if result.status != 200:
        print "HTTP %d (%s)" % (result.status, result.reason)
        return
    print result.body

if __name__ == "__main__":
    main(sys.argv[1:])
