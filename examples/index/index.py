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

"""A sample command line utility for interacting with Splunk indexes."""

# UNDONE: Improve command line help to show individual commands

from pprint import pprint # UNDONE

import sys

import splunk.data as data
from splunk.binding import *

import tools.cmdopts as cmdopts

PATH_INDEXES = "data/indexes"
PATH_INDEXES_ITEM = "data/indexes/%s"

context = None  # Global binding context
parser = None   # Global command parser, global for error reporting

def check_status(response, expected):
    """Checks the given HTTP response for the expected status value."""
    if response.status != expected:
        raise HTTPError(response.status, response.reason)

def body(response):
    return data.load(response.body.read())

def indexes(context):
    """Returns a list of indexes available at the given binding context."""
    response = context.get(PATH_INDEXES)
    check_status(response, 200)
    body = response.body.read()
    content = data.load(body).entry
    return sorted([item.title for item in content])

class Index:
    """Provides a friendly interface to a Splunk index."""
    def __init__(self, context, name):
        self.context = context
        self.name = name
        itempath = PATH_INDEXES_ITEM % name
        self._item = context.bind(itempath, "get")
        self._edit = context.bind(itempath, "post")
        self._disable = context.bind(itempath + "/disable", "post")
        self._enable = context.bind(itempath + "/enable", "post")

    def __call__(self):
        result = body(self.item()).entry.content
        del result['eai:acl'] # Noise ..
        del result['eai:attributes']
        del result['type']
        return result
        
    def clear(self):
        self.ensure()
        # UNDONE: Clear the index

    def create(self):
        response = self.post(name=self.name)
        check_status(response, 201)
        return response

    def delete(self):
        assert False # It's not possible to delete an index!

    def disable(self):
        response = self._disable()
        check_status(response, 200)
        return response

    def enable(self):
        response = self._enable()
        check_status(response, 200)
        return response

    def edit(self, **kwargs):
        response = self._edit(**kwargs)
        check_status(response, 200)
        return response

    def ensure(self):
        if not self.exists(): self.create()

    def exists(self):
        return self._item().status == 200

    def item(self):
        response = self._item()
        check_status(response, 200)
        return response

def verb(command, argv):
    """Executes a simple command verb against a named index."""
    global context, parser

    if len(argv) == 0: parser.error("Command requires an index name")
    if len(argv) > 1: parser.error("Invalid command line")

    name = argv[0]
    index = Index(context, name)
    { 'clear': index.clear,
      'create': index.create,
      'disable': index.disable,
      'enable': index.enable,
      'print': lambda: show(index),
    }[command]()

def edit(argv):
    global context, parser

    if len(argv) == 0: parser.error("Command requires an index name")

    name = argv[0]
    index = Index(context, name)

    # Ping the index for a list of editable fields, and then build a set of
    # command parser rules that we can use to build a parser to parse the
    # field values from the command argument vector.

    # Request editable fields
    content = body(index.item()).entry.content
    fields = content['eai:attributes'].optionalFields

    # Build parser rules
    rules = {}
    for field in fields: rules[field] = { 'flags': ["--%s" % field] }

    # Parse the argument vector
    opts = cmdopts.Parser(rules).parse(argv).result

    # Execute the edit request
    response = index.edit(**opts.kwargs)

def list(argv):
    """List the indexes that are available via the given binding context."""
    global context

    if len(argv) != 0: parser.error("Invalid command line")
    for item in indexes(context): print item
    
def show(index):
    """Print the given indexes property values."""
    if not index.exists():
        print "Index '%s' does not exist" % index.name
        return
    value = index()
    keys = sorted(value.keys())
    for key in keys: print "%s: %s" % (key, value[key])

def main():
    import sys
    usage = "usage: %prog [options] <command> [command options]"

    # Split the command line into 3 parts, the apps arguments, the command
    # and the arguments to the command. The app arguments are used to
    # establish the biding context and the command arguments are command
    # specific.

    argv = sys.argv[1:]

    # Find the index of the command argument (the first non-kwarg)
    cmdix = -1
    for i in xrange(len(argv)):
        if not argv[i].startswith('-'):
            cmdix = i
            break

    if cmdix == -1: # No command
        appargv = argv
        command = "list"
        cmdargv = []
    else:
        appargv = argv[1:cmdix-1]
        command = argv[cmdix]
        cmdargv = argv[cmdix+1:]

    # Parse app args
    global parser
    parser = cmdopts.parser(usage=usage)
    opts = parser.loadrc(".splunkrc").parse(appargv).result

    # Establish the binding context
    global context
    context = connect(**opts.kwargs)

    # Dispatch the command
    { 'clear': lambda argv: verb("clear", argv),
      'create': lambda argv: verb("create", argv),
      'disable': lambda argv: verb("disable", argv),
      'enable': lambda argv: verb("enable", argv),
      'edit': edit,
      'list': list,
      'print': lambda argv: verb("print", argv),
    }[command](cmdargv)

if __name__ == "__main__":
    main()

