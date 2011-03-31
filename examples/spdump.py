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

"""Given a hostname (and credentials), print out a simple report on the state
   of the system. This example shows how to access and enumerate numerious
   system properties and resources."""

from os import path
from pprint import pprint
import sys
import textwrap

try:
    import splunk
except ImportError:
    sys.path.insert(0, path.dirname(path.dirname(path.abspath(__file__))))
    import splunk
import splunk.binding as binding
import splunk.data as data

from tools.cmdline import default, error, loadif, merge, record

class HTTPError(Exception): pass

class Writer:
    def __init__(self, out = sys.stdout):
        self.out = out
        self.wrapper = textwrap.TextWrapper() 
        self.indent(0)

    def indent(self, level):
        indent = "    "*level
        self.wrapper.initial_indent = indent
        self.wrapper.subsequent_indent = indent

    def write(self, text):
        self.out.write(self.wrapper.fill(text))

    def writeln(self, text):
        self.write(text)
        self.out.write('\n')

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

def check_response(response):
    if response.status != 200:
        raise HTTPError, "%d (%s)" % (response.status, response.reason)

# Load an entity resource from the given path
def load_entity(cx, path):
    response = cx.get(path)
    check_response(response)
    value = data.load(response.body)
    entry = value.get("entry", None)
    assert entry is not None
    return entry
    
# Load a collection resource from the given path
def load_collection(cx, path):
    response = cx.get(path)
    check_response(response)
    value = data.load(response.body)
    entry = value.get("entry", None)
    if entry is None: return None
    return entry if isinstance(entry, list) else [entry] # Normalize

def print_apps(cx):
    out = Writer()
    out.writeln("Apps")
    entry = load_collection(cx, 'apps/local')
    if entry is None: return
    for item in entry:
        out.indent(1)
        content = item.content
        out.writeln("%s (%s)" % (content.label, item.title))
        out.indent(2)
        author = content.get("author", None)
        if author is not None:
            out.writeln("author: %s" % author)
        version = content.get("version", None)
        if version is not None:
            out.writeln("version: %s" % version)
        description = content.get("description", None)
        if description is not None:
            out.writeln("description: %s" % description)

def print_collection(cx, title, path):
    out = Writer()
    out.writeln(title)
    entry = load_collection(cx, path)
    if entry is None: return
    for item in entry:
        out.indent(1)
        out.writeln(item.title)
        out.indent(2)
        print_content(out, item.content)

def print_commands(cx):
    print_collection(cx, "Commands", "data/commands")

# Shared routine to print content element
def print_content(out, content):
    for key in sorted(content.keys()):
        if key in ['eai:acl', 'type']: continue # Elide
        out.writeln("%s: %s" % (key, content[key]))

def print_eventtypes(cx):
    print_collection(cx, "Eventtypes", "saved/eventtypes")

def print_extractions(cx):
    print_collection(cx, "Extractions (props)", "data/props/extractions")
    print
    print_collection(cx, "Extractions (transforms)", "data/transforms/extractions")

def print_info(cx):
    content = load_entity(cx, 'server/info').content
    out = Writer()
    out.writeln(cx.host)
    out.indent(1)
    out.writeln("serverName: %s" % content.serverName)
    out.writeln("version: %s" % content.version)
    out.writeln("build: %s" % content.build)
    out.writeln("cpu_arch: %s" % content.cpu_arch)
    out.writeln("os_name: %s" % content.os_name)
    out.writeln("os_version: %s" % content.os_version)
    out.writeln("os_build: %s" % content.os_build)

def print_indexes(cx):
    print_collection(cx, "Indexes", "data/indexes")

def print_inputs(cx):
    out = Writer()
    out.writeln("Inputs")
    inputs = {
        'monitor': "data/inputs/monitor",
        'script': "data/inputs/script",
        'tcp/cooked': "data/inputs/tcp/cooked",
        'tcp/raw': "data/inputs/tcp/raw",
        'udp': "data/inputs/udp",
    }
    for input, path in inputs.iteritems():
        entry = load_collection(cx, path)
        if entry is None: continue
        for item in entry:
            out.indent(1)
            out.writeln(item.title)
            out.indent(2)
            out.writeln("kind: %s" % input)
            print_content(out, item.content)

def print_lookups(cx):
    print_collection(cx, "Lookups (props)", "data/props/lookups")
    print
    print_collection(cx, "Lookups (transforms)", "data/transforms/lookups")

def print_users(cx):
    print "Users"
    entry = load_collection(cx, 'authentication/users')
    if entry is None: return
    for item in entry:
        content = item.content
        print "    %s (%s)" % (item.title, content.realname)
        print "        email: %s" % content.email
        print "        roles: %s" % '; '.join(content.roles)

def report(cx):
    print_info(cx)
    print
    print_users(cx)
    print
    print_apps(cx)
    print
    print_indexes(cx)
    print
    print_inputs(cx)
    print
    print_commands(cx)
    print
    print_eventtypes(cx)
    print
    print_extractions(cx)
    print
    print_lookups(cx)
    #print_searches(cx)

def main():
    opts = getopts(sys.argv[1:])
    host = opts.kwargs.get("host", default.host)
    port = opts.kwargs.get("port", default.port)
    username = opts.kwargs.get("username", "")
    password = opts.kwargs.get("password", "")
    report(binding.connect("%s:%s" % (host, port), username, password))

if __name__ == "__main__":
   main() 
