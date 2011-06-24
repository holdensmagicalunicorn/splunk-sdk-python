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

"""A command line that will list out Splunk confs, or if given a conf name
   will list the contents of the given conf."""

# UNDONE: Add support for a conf 'path' to list out contents of individual
# stanza, or key value.
# UNDONE: Support for adding and deleting stanzas
# UNDONE: Extra credit points for support for modifying key/value pairs

import sys

import splunk

from utils import error, parse

def main(argv):
    usage = 'usage: %prog [options] [conf]'
    opts = parse(argv, {}, ".splunkrc", usage=usage)
    service = splunk.client.connect(**opts.kwargs)

    count = len(opts.args)
    if count > 1: error("Requires at most one conf", 2)

    if count == 0:
        # List out the available confs
        for conf in service.confs: 
            print conf.name
    else:
        # Print out detail on the requested conf
        name = opts.args[0]
        conf = service.confs[name]
        for stanza in conf:
            print "[%s]" % stanza.name
            entity = stanza.read()
            for k, v in entity.iteritems():
                print "%s = %s" % (k, v)
            print

if __name__ == "__main__":
    main(sys.argv[1:])

