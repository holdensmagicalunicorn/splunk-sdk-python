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

"""A command line interface for the Splunk REST APIs."""

# UNDONE: Support for POST
# UNDONE: Support for scheme parameter
# UNDONE: Generalize & share cmdline processor 

import getopt
from os import path
import sys

try:
    import splunk
except ImportError:
    sys.path.insert(0, path.dirname(path.dirname(path.abspath(__file__))))
    import splunk

from cmdline import default, error, loadif, merge, record

# Loads opts from .splunkrc, then orverrides with command line, then
# overrides with any config file specified on the command line.
def getopts(argv):
    opts = {}
    opts = merge(opts, parse(loadif(path.expanduser("~/.splunkrc"))))
    opts = merge(opts, parse(argv))
    opts = merge(opts, parse(loadif(opts.get("config", None))))
    return record(opts)

# Retrieve the content-type from the given response message
def contentType(response):
    for k, v in response.headers:
        if k.lower() == "content-type":
            return v
    return None

def help(exitCode = None):
    print "Usage: spurl [options...] <path>"
    print "Options:"
    print "    --config=<filename>      Configuration file"
    print "    --host=<hostname>        Specify hostname"
    print " -m|--method=<method>        HTTP method, default=GET"
    print " -p|--password=<password>    Specify password (required)"
    print "    --port=<port#>           Specify port number, default=8089"
    print " -u|--username=<username>    Specify username (required)"
    if not exitCode is None: sys.exit(exitCode)

# Parse the given argument list
def parse(argv):
    try:
        sargs = "p:u:h?"
        largs = [
            "config=", 
            "host=", 
            "method=", 
            "password=", 
            "port=", 
            "username=", 
            "help" ]
        kwargs, args = getopt.gnu_getopt(argv, sargs, largs)
    except getopt.GetoptError as e:
        error(e.msg)
        usage(2)

    opts = {'args': args, 'kwargs': {}}
    for k, v in kwargs:
        if k == "-?" or k == "-h": 
            k == "help"
        elif k == "-u":
            k == "username"
        elif k == "-p":
            k == "password"
        else:
            assert k.startswith("--")
            k = k[2:]
        opts["kwargs"][k] = v

    return opts
            
# Invoke the url using the given opts parameters
def invoke(path, **kwargs):
    message = { "method": kwargs.get("method", "GET"), }
    return splunk.connect(**kwargs).request(path, message)

# Answer if the content typ eof the given message is text/plain
def istext(response):
    type = contentType(response)
    return type and type.find("text/plain") != -1

# Answer if the content type of the given message is text/xml
def isxml(response):
    type = contentType(response)
    return type and type.find("text/xml") != -1

def print_response(response):
    if response.status != 200:
        print "%d %s" % (response.status, response.reason)
        return
    if isxml(response):
        print_xml(response.body)
    elif istext(response):
        print response.body

def print_xml(value):
    from xml.etree import ElementTree
    root = ElementTree.XML(value)
    print ElementTree.tostring(root)

def usage(exitCode = None):
    print "Usage: spurl [--config=<filename>]"
    print "             [--host=<hostname>] [--port=<port#>]"
    print "             [-u|--username=<username>] [-p|--password=<password>]"
    print "             [-m|--method=<method>]"
    print "             <path>"
    if not exitCode is None: sys.exit(exitCode)

def main():
    opts = getopts(sys.argv[1:])
    if opts.has_key("help"): help(0)
    for arg in opts.args: 
        print_response(invoke(arg, **opts.kwargs))

if __name__ == "__main__":
    main()

