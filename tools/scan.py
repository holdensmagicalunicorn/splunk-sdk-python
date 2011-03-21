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

# Scans the Splunk API "atom space" starting at the seed URLs given on the 
# comamnd line and traversing all link ref elements to build a transitive 
# closure of all 'ref' types and corresponding URLs reachable from the seeds.

from httplib import BadStatusLine
from os import path
import sys
from xml.etree import ElementTree
from xml.etree.ElementTree import XML

try:
    import splunk
except ImportError:
    sys.path.insert(0, path.dirname(path.dirname(path.abspath(__file__))))
    import splunk
from splunk.wire import xname

from cmdline import default, error, loadif, merge, record

_blacklist = [
    "/services/streams/search",     # Times out
    "/services/streams/rtsearch",   # Times out
]

# UNDONE: Should be able to share the following (aka move to cmdline.py)
def getopts(argv):
    from os import path
    opts = {}
    opts = merge(opts, parse(loadif(path.expanduser("~/.splunkrc"))))
    opts = merge(opts, parse(argv))
    return record(opts)

# UNDONE: Should be able to share long form arg parsing (aka move to cmdline.py)
def parse(argv):
    import getopt
    try:
        largs = ["host=", "password=", "port=", "username="]
        kwargs, args = getopt.gnu_getopt(argv, "", largs)
    except getopt.GetoptError as e:
        error(e.msg)
        usage(2)
    opts = {'args': args, 'kwargs': {}}
    for k, v in kwargs:
        assert k.startswith("--")
        k = k[2:]
        opts["kwargs"][k] = v
    return opts

# Print the given args as a valid csv encoded row of values.
def write_row(file, *args):
    count = len(args)
    for i in range(count):
        arg = str(args[i])
        for bad in "'\",": arg = arg.replace(bad, '_')
        file.write(arg)
        if i < count-1: file.write(', ')
    file.write('\n')

class Program:
    def __init__(self, argv):
        opts = getopts(argv[1:])
        self.host = opts.kwargs.get("host", default.host)
        self.port = opts.kwargs.get("port", default.port)
        self.username = opts.kwargs.get("username", "")
        self.password = opts.kwargs.get("password", "")
        self._nextid = 1
        self._paths = {}    # path => id for known paths
        self._ids = {}      # id => path for known paths
        self._pending = []  # ids of pending paths
        self._rels = {}     # Relationships between paths
        self._reltypes = [] # Known relationship types
        self._results = {}  # Results of scanning known paths
        self._visited = []  # ids of visited paths
        self.paths(*opts.args)

    def connect(self):
        self._cn = splunk.connect(self.host, self.username, self.password)

    def getpath(self, id):
        return self._ids[id]

    def getid(self, path):
        """Returns the id of the given path."""
        return self._paths[path]

    def isknown(self, path):
        return self._paths.has_key(path)

    def ispending(self, id):
        return id in self._pending

    def isvisited(self, id):
        return id in self._visited

    def learn(self, path):
        """Add the given path to the list of known paths."""
        assert not self.isknown(path)
        id = self._nextid
        self._nextid += 1
        self._ids[id] = path
        self._paths[path] = id
        return id

    def next(self):
        """Retrieve the id of the next pending path to scan."""
        if len(self._pending) == 0: return None
        return self._pending.pop()

    def paths(self, *args):
        """Consider the given paths and queue up any unknown for a scan."""
        for path in args:
            if not self.isknown(path):
                id = self.learn(path)    # We've learned about a new path
                self._pending.append(id) # .. and queue it for scanning

    def report(self):
        with open("scan.rels.csv", "w") as file:
            self.report_rels(file)
        with open("scan.reltypes.csv", "w") as file:
            self.report_reltypes(file)
        with open("scan.results.csv", "w") as file:
            self.report_results(file)

    def report_rels(self, file):
        write_row(file, "From", "Relationship", "To")
        for id, path in self._ids.iteritems():
            rels = self._rels.get(id, None)
            if rels is None: continue
            for item in rels:
                rel = item["rel"]
                refid = item["ref"]
                href = self.getpath(refid)
                write_row(file, path, rel, href)

    def report_reltypes(self, file):
        write_row(file, "Relationship")
        for reltype in self._reltypes:
            write_row(file, reltype)

    def report_results(self, file):
        write_row(file, "Id", "Endpoint", "Status", "Message")
        for id, path in self._ids.iteritems():
            results = self._results.get(id, None)
            if results is None: continue # Might have been eg: blacklisted
            write_row(file, id, path, results["status"], results["message"])

    def run(self):
        self.connect()
        self.scan()
        self.report()

    def scan(self):
        while True:
            id = self.next()
            if id is None: break # Done
            assert not self.isvisited(id)

            path = self.getpath(id)
            if path in _blacklist: continue

            self.visited(id)
            status, result = self.scanit(path)
            message = result.reason if status != -1 else result

            print "%s => %s %s" % (path, status, message)

            # Record results of the scan
            self._results[id] = {
                'status': status,
                'message': message,
            }

            # If the response body is XML, then scan it for information about
            # the endpoint and for additional candidate paths.
            if status != 200: continue
            try:
                root = XML(result.body)
            except: continue # Not XML

            # Examine all links in the response for candidates to learn
            links = root.findall(".//" + xname.link)
            self.paths(*[link.attrib["href"] for link in links])

            # Examine all top level links and record relationships to current
            links = root.findall(xname.link)
            if links is None or len(links) == 0: continue
            self._rels[id] = []
            for link in links:
                rel = link.attrib["rel"]
                # Keep track of all known relationship types
                if not rel in self._reltypes: self._reltypes.append(rel)
                href = link.attrib["href"]
                refid = self.getid(href)
                self._rels[id].append({'rel': rel, 'ref': refid })

    def scanit(self, path):
        """Scan the given path and return the response message."""
        import socket, time
        logins = 1
        retries = 5
        while True:
            try:
                response = self._cn.get(path)
                status = response.status
                # Its possible a previous scan reset the session, so if we see
                # an authorization error, login and try again.
                if status == 401 and logins > 0:
                    logins -= 1
                    self._cn.login()
                    continue
                return status, response
            except socket.error, e:
                # Connection reset or connection refused may mean that we have
                # rebooted the server by scanning a control endpoint, so sleep
                # for a while to give the server some time to finish rebooting.
                if e.errno in [54, 61] and retries > 0:
                    retries -= 1
                    time.sleep(10)
                    continue 
                return -1, e
            except BadStatusLine, e:
                # I occasionally see a BadStatusLine error from httplib even
                # though I dont have the 'strict' option set on the connection 
                # and I lamely theorize it's due to the server going down mid
                # response .. (ie, I need to track this down for real).
                if retries > 0:
                    retries -= 1
                    time.sleep(10)
                    continue 
            except Exception, e:
                return -1, repr(e)

    def visited(self, id):
        assert id not in self._visited
        self._visited.append(id)

def main(argv):
    Program(argv).run()

if __name__ == "__main__":
    import sys
    main(sys.argv)

