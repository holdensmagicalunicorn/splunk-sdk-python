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

"""A command line utility for executing searches against the export endpoint."""

import sys

import splunk

from utils import cmdopts

RULES = {
    "earliest_time": { 'flags': ["--earliest_time"] },
    "latest_time": { 'flags': ["--latest_time"] },
    "output_mode": { 'flags': ["--output_mode"] },
    "f": {'flags': ["--f"] },
    # UNDONE: Add additional export/search arguments
}

def main(argv):
    usage = 'usage: %prog [options] "query"'
    opts = cmdopts.parse(argv, RULES, ".splunkrc", usage=usage)

    if len(opts.args) != 1:
        cmdopts.error("Single query argument required", 2)

    context = splunk.binding.connect(**opts.kwargs)

    # Extract search options
    kwargs = {}
    for key in RULES.keys():
        if opts.kwargs.has_key(key):
            kwargs[key] = opts.kwargs[key]

    query = opts.args[0]

    # UNDONE: Call the parser here to syntax check the query

    # Execute the query
    result = context.get('search/jobs/export', search=query, **kwargs)
    if result.status != 200:
        print "HTTP %d (%s)" % (result.status, result.reason)
        return

    while True:
        content = result.body.read(1024)
        if len(content) == 0: break
        sys.stdout.write(content)

if __name__ == "__main__":
    main(sys.argv[1:])

#    opts = parse(sys.argv, None, ".splunkrc")
#    service = connect(**opts.kwargs)
#    job = service.jobs.create("search index=twitter *")
#    try:
#        while True:
#            sleep(2)
#            status = job.read('isDone', 'doneProgress')
#            pprint(status)
#            if status.isDone == '1':
#                break
#    except Exception:
#        job.cancel()
    
