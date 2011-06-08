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

# UNDONE: Improve command line help to show the following commands:
#
#     clean [<index>]+
#     create <index> [options]
#     disable [<index>]+
#     enable [<index>]+
#     list [<index>]*
#     reload [<index>]+
#     update <index> [options]
#
# UNDONE: Implement a delete command: clean, remove stanzas from indexes.conf,
#  restart server, delete db files.

from pprint import pprint # UNDONE

import sys

import splunk
from splunk.client import Service

from utils.cmdopts import cmdline, error, parse

service = None

def clean(argv):
    foreach(argv, lambda index: index.clean())

def create(argv):
    """Create an index according to the given argument vector."""

    if len(argv) == 0: 
        error("Command requires an index name", 2)

    name = argv[0]

    if service.indexes.contains(name):
        print "Index '%s' already exists" % name
        return

    # Read item metadata and construct command line parser rules that 
    # correspond to each editable field.

    # Request editable fields
    fields = service.indexes.itemmeta()['eai:attributes'].optionalFields

    # Build parser rules
    rules = dict([(field, {'flags': ["--%s" % field]}) for field in fields])

    # Parse the argument vector
    opts = cmdline(argv, rules)

    # Execute the edit request
    service.indexes.create(name, **opts.kwargs)

def disable(argv):
    foreach(argv, lambda index: index.disable())

def enable(argv):
    foreach(argv, lambda index: index.enable())

def list(argv):
    """List available indexes if no names provided, otherwise list the
       properties of the named indexes."""
    if len(argv) == 0:
        for index in service.indexes:
            count = index['totalEventCount']
            print "%s (%s)" % (index.name, count)
    else:
        foreach(argv, read)

def read(index):
    """List the properties of the given index."""
    print index.name
    for k,v in index.read().iteritems(): 
        print "    %s: %s" % (k,v)

def reload(argv):
    foreach(argv, lambda index: index.reload())

def foreach(argv, fn):
    """Apply the given function to each index named in the argument vector."""
    opts = cmdline(argv)
    if len(opts.args) == 0:
        error("Command requires an index name", 2)
    for name in opts.args:
        if not service.indexes.contains(name):
            error("Index '%s' does not exist" % name, 2)
        index = service.indexes[name]
        fn(index)

def update(argv):
    """Update an index according to the given argument vector."""

    if len(argv) == 0: 
        error("Command requires an index name", 2)
    name = argv[0]
    if not service.indexes.contains(name):
        error("Index '%s' does not exist" % name, 2)
    index = service.indexes[name]

    # Read entity metadata and construct command line parser rules that 
    # correspond to each editable field.

    # Request editable fields
    fields = index.readmeta()['eai:attributes'].optionalFields

    # Build parser rules
    rules = dict([(field, {'flags': ["--%s" % field]}) for field in fields])

    # Parse the argument vector
    opts = cmdline(argv, rules)

    # Execute the edit request
    index.update(**opts.kwargs)

def main():
    import sys
    usage = "usage: %prog [options] <command> [<args>]"

    # Split the command line into 3 parts, the apps arguments, the command
    # and the arguments to the command. The app arguments are used to
    # establish the binding context and the command arguments are command
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
        appargv = argv[:cmdix]
        command = argv[cmdix]
        cmdargv = argv[cmdix+1:]

    opts = parse(appargv, {}, ".splunkrc", usage=usage)

    global service
    service = Service(**opts.kwargs)
    service.login()

    # Dispatch the command
    commands = { 
        'clean': clean,
        'create': create,
        'disable': disable,
        'enable': enable,
        'list': list,
        'reload': reload,
        'update': update,
    }
    if command not in commands.keys():
        error("Unrecognized command: %s" % command, 2)
    commands[command](cmdargv)

if __name__ == "__main__":
    main()

