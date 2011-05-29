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

"""A command line utility for interacting with Splunk indexes."""

# UNDONE: Improve command line help to show individual commands

import sys
from time import sleep

from splunk.binding import *
import splunk.data as data
from splunk.data import record

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
        self.path = PATH_INDEXES_ITEM % name
        self._item = context.bind(self.path, "get")
        self._edit = context.bind(self.path, "post")
        self._disable = context.bind(self.path + "/disable", "post")
        self._enable = context.bind(self.path + "/enable", "post")

    def __call__(self, *args):
        content = body(self.item()).entry.content
        if len(args) > 0: # We have filter args
            result = record({})
            for key in args: result[key] = content[key]
        else:
            # Eliminate some noise by default
            result = content
            del result['eai:acl']
            del result['eai:attributes']
            del result['type']
        return result

    def _roll_hot_buckets(self):
        response = context.post(self.path + "/roll-hot-buckets")
        check_status(response, 200)
        return response
        
    def clear(self):
        if not self.exists(): return
        saved = self('maxTotalDataSizeMB', 'frozenTimePeriodInSecs')
        self.edit(maxTotalDataSizeMB=1, frozenTimePeriodInSecs=1)
        self._roll_hot_buckets()
        while True: # Wait until event count goes to zero
            sleep(1)
            if self('totalEventCount').totalEventCount == '0': break
        self.edit(**saved)

    def create(self):
        response = self.context.post("data/indexes", name=self.name)
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
    for field in fields: 
        rules[field] = { 'flags': ["--%s" % field] }

    # Parse the argument vector
    opts = cmdopts.Parser(rules).parse(argv).result

    # Execute the edit request
    response = index.edit(**opts.kwargs)
    check_status(response, 200)

def list(argv):
    """List the indexes that are available via the given binding context."""
    global context

    if len(argv) != 0: parser.error("Invalid command line")
    for item in indexes(context): print item

def publish(argv):
    """Publish the given data value to the given index."""

    if len(argv) != 2:  
        parser.error("Command requires an index name and data to publish")
    
    name = argv[0]
    data = argv[1]

    path = "receivers/simple?index=%s" % name
    message = { 'method': "POST", 'body': data }
    response = context.request(path, message)
    check_status(response, 200)
    
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
        #appargv = [] if cmdix == 0 else argv[:cmdix]
        appargv = argv[:cmdix]
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
    commands = { 
        'clear': lambda argv: verb("clear", argv),
        'create': lambda argv: verb("create", argv),
        'disable': lambda argv: verb("disable", argv),
        'enable': lambda argv: verb("enable", argv),
        'edit': edit,
        'list': list,
        'print': lambda argv: verb("print", argv),
        'publish': publish
    }

    if command not in commands.keys():
        parser.error("Unrecognized command: %s" % command)

    commands[command](cmdargv)

if __name__ == "__main__":
    main()

