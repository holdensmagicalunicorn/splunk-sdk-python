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

    # create a splunk real-time job
    job = service.jobs.create("search index=%s %s" % (iname, squery), 
                              earliest_time="rt", 
                              latest_time="rt", 
                              search_mode="realtime")

    # start at real-time offset 0.
    last_offset = 0
    try:

        # go until we hit a control-c to exit
        while True:
            # get results from our last offset
            results = job.events(offset=last_offset)
            data = results.read()
            if len(data) > 0:
                try:
                    # get the offset number buried in the XML
                    dxml = xml.dom.minidom.parseString(data)
                    offsets = dxml.getElementsByTagName("result")
                    if len(offsets) > 0:
                        last = offsets[-1]
                        if last.hasAttributes():
                            last_offset = int(last.getAttribute(
                                             str(last.attributes.keys()[0])))
                except xml.parsers.expat.ExpatError:
                    print "WARNING: failed to parse XML"

                # use the reader class to extract the event data
                reader = splunk.results.ResultsReader(StringIO.StringIO(data))
                while True:
                    kind = reader.read()
                    if kind == None:
                        break
                    if kind == splunk.results.RESULT:
                        print reader.value['_raw'].firstChild.nodeValue

                # make our last offset one more than we recieved
                last_offset = last_offset + 1
            time.sleep(1)
    except KeyboardInterrupt:
        print
        print "Keyboard interrupt  ... exiting"
    except:
        print
        print "got an unexpected exception ... exiting"

    print "canceling job: %s" % job.sid
    job.cancel()

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


