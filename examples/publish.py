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

"""Publishes events to a named index. The first command argument must be
   the name of the target index and each additional argument will be
   published to the index as a separate event. If no event arguments
   are provided, the event data will be read from stdin."""

import sys

from splunk.binding import *

import tools.cmdopts as cmdopts

def main(argv):
    usage = 'usage: %prog [options] <index> [<events>]'
    parser = cmdopts.parser(usage=usage)
    opts = parser.loadrc(".splunkrc").parse(argv).result
    if len(opts.args) == 0: parser.error("Index name rquired")

    index = opts.args[0]
    events = opts.args[1:] if len(opts.args) > 1 else [sys.stdin.read()]
    context = connect(**opts.kwargs)
    for event in events: publish(context, index, event)

def publish(context, index, data):
    path = "receivers/simple?index=%s" % index
    message = { 'method': "POST", 'body': data }
    response = context.request(path, message)
    if response.status != 200:
        sys.stderr.write("HTTP Error: %d (%s)" % (
            response.status, response.reason))

if __name__ == "__main__":
    main(sys.argv[1:])
