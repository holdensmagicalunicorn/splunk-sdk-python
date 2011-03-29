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

"""Quick and dirty tool to inspect the signature of Splunk endponts."""

from os import path
import sys

try:
    import splunk
except ImportError:
    sys.path.insert(0, path.dirname(path.dirname(path.abspath(__file__))))
    import splunk
import splunk.binding as binding
import splunk.data as data

from cmdline import default, error, loadif, merge, record

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

# Return the link with rel='create'
def find_create(links):
    for link in links:
        if link.rel == "create": return link
    return None

# Attempt to retrieve the eai:attributes metadata from the given response body
def find_fields(cx, body):
    body = data.load(body)
    entry = body.get("entry", None)
    if entry is None: return None
    content = entry.get("content", None)
    if content is None: return None
    attributes = content.get("eai:attributes", None)
    if attributes is None: return None
    fields = []
    required = attributes.get("requiredFields", None)
    if required is not None:
        for field in required: fields.append(field)
    #optional = attributes.get("optionalFields", None)
    #if optional is not None:
    #    for field in optional: fields.append(field + '?')
    if len(fields) == 0: return None
    return fields

def probe(cx, path):
    response = cx.get(path)
    if response.status != 200:
        return ["fail:%d (%s)" % (response.status, response.reason)]
    sig = ["get"]
    body = data.load(response.body)
    if body.has_key('link'):
        links = body.link
        if not isinstance(links, list): links = [links] # Normalize schema
        create = find_create(links)
        if create is not None:
            verb = "create"
            response = cx.get(create.href)
            if response.status == 200: # Check in case link lied
                fields = find_fields(cx, response.body)
                if fields is not None:
                    verb = "%s:%s" % (verb, ','.join(fields))
                sig.append(verb)
    return sig

def load(cx, filename):
    import csv
    file = open(filename, 'r')
    reader = csv.reader(file, delimiter=',') 
    for row in reader:
        path = row[0]
        if path.startswith('#'): continue
        sig = ["unknown"]
        if path.find('{') == -1:
            sig = probe(cx, path)
        print '"%s", "%s"' % (path, ';'.join(sig))

def main():
    opts = getopts(sys.argv[1:])
    host = opts.kwargs.get("host", default.host)
    port = opts.kwargs.get("port", default.port)
    username = opts.kwargs.get("username", "")
    password = opts.kwargs.get("password", "")
    cx = binding.connect("%s:%s" % (host, port), username, password)
    for arg in opts.args: load(cx, arg)

if __name__ == "__main__":
    main()
