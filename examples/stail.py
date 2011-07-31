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

"""An example to tail an index, with optional specific search."""

import sys
import time
import xml.dom.minidom
import StringIO

from splunk.client import connect
from utils import parse
import splunk.results 
import datetime

CLI_RULES = {
   'search': {
        'flags': ["--search"],
        'default': None,
        'help': "Optional search query string"
    }
}

def tail(service, opts):
    """Tail the index and optional search, via splunk real-time search."""

    # index is the only naked argument
    iname = opts.args[0]

    # if user supplied a query string, extract it, else leave blank 
    squery = ""
    if opts.kwargs['search'] is not None:
        squery = opts.kwargs['search']

    fd = open("xx", "w")

    # start at real-time offset 0.
    last_offset = 0
    try:
        # go until we hit a control-c to exit
        while True:
            # tap the export exndpoint
            result = service.get("search/jobs/export",
                              search="search %s index=%s" % (squery, iname),
                              earliest_time="rt", 
                              latest_time="rt", 
                              search_mode="realtime")

            if result.status != 200:
                continue
            # use the reader class to extract the event data
            print result
            reader = splunk.results.ResultsReader(result.body)
            while True:
                kind = reader.read()
                if kind == None:
                    break
                if kind == splunk.results.RESULT:
                    print str(reader.value['_raw'].firstChild.nodeValue)
                    fd.write(str(reader.value))
                    fd.write(str(reader.value['_raw'].firstChild.nodeValue))
                    fd.write("\n")
                    fd.flush()

    except KeyboardInterrupt:
        print
        print "Keyboard interrupt  ... exiting"
    except:
        print 
        print "got an unexpected exception ... exiting"
        print
        raise

    fd.close()

def main():
    """Main program."""

    usage = "usage: %prog INDEX [<args>]"

    argv = sys.argv[1:]

    # parse args, connect and setup 
    opts = parse(argv, CLI_RULES, ".splunkrc", usage=usage)
    service = connect(**opts.kwargs)

    if len(opts.args) == 0:
        print "You must supply at the very least an INDEX"
        sys.exit(1)

    tail(service, opts)

if __name__ == "__main__":
    main()


