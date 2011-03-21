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

from pprint import pprint # UNDONE

import getopt
from os import path
import sys
import urllib

from cmdline import default, error, loadif, merge, record
import splunk
import splunk.http as http

# UNDONE: Generalize and move to cmdline.py
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

# UNDONE: Generalize and move to cmdline.py
# Parse the given argument list
def parse(argv):
    try:
        sargs = "p:u:h?"
        largs = ["config=", "host=", "method=", "password=", "port=", "username=", "help"]
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
            
def login(**kwargs):
    host = kwargs.get("host", default.host)
    username = kwargs.get("username", "")
    password = kwargs.get("password", "")
    return splunk.login(host, username, password)

# Invoke the url using the given opts parameters
def invoke(path, **kwargs):
    sessionKey = login(**kwargs)
    message = {
        "method": kwargs.get("method", "GET"),
        "headers": [("Authorization", "Splunk " + sessionKey)]
    }
    host = kwargs.get("host", default.host)
    port = kwargs.get("port", default.port)
    url = "%s://%s:%s%s" % (default.scheme, host, port, path)
    return http.request(url, message)

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
    #from pprint import pprint
    #pprint(response)
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

def run():
    opts = getopts(sys.argv[1:])
    if opts.has_key("help"): help(0)
    for arg in opts.args: 
        print_response(invoke(arg, **opts.kwargs))

def main():
    import socket
    run()
    return
    try:
        run()
    except (socket.error, splunk.HTTPError), e:
        error(e, 2)

if __name__ == "__main__":
    main()

