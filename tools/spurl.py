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

"""A simple command line interface for the Splunk REST APIs."""

# UNDONE: Support for POST
# UNDONE: Generalize & share cmdline processor 

import getopt
from os import path
import sys

try:
    import splunk
except ImportError:
    sys.path.insert(0, path.dirname(path.dirname(path.abspath(__file__))))
    import splunk

import cmdopts

# Retrieve the content-type from the given response message
def contentType(response):
    for k, v in response.headers:
        if k.lower() == "content-type":
            return v
    return None

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

def main():
    opts = cmdopts.parser().loadrc(".splunkrc").parse(sys.argv[1:]).result
    for arg in opts.args: 
        print_response(invoke(arg, **opts.kwargs))

if __name__ == "__main__":
    main()

