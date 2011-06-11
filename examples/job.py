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

"""A command line utility for interacting with Splunk search jobs."""

# All job commands operate on search 'specifiers' (spec). A search specifier
# is either a search-id (sid) or the index of the search job in the list of
# jobs, eg: @0 would specify the frist job in the list, @1 the second, and so
# on.

from pprint import pprint # UNDONE

import sys

from splunk.client import connect

from utils.cmdopts import cmdline, error, parse

def output(stream):
    """Write the contents of the given stream to stdout."""
    while True:
        content = stream.read(1024)
        if len(content) == 0: break
        sys.stdout.write(content)

class Program:
    def __init__(self, service):
        self.service = service

    def cancel(self, argv):
        self.foreach(argv, lambda job: job.cancel())

    def create(self, argv):
        """Create a search job."""

        if len(argv) == 0: 
            error("Command requires an index name", 2)

        name = argv[0]

        if self.service.indexes.contains(name):
            print "Index '%s' already exists" % name
            return

        # Read item metadata and construct command line parser rules that 
        # correspond to each editable field.

        # Request editable fields
        itemmeta = self.service.indexes.itemmeta()
        fields = itemmeta['eai:attributes'].optionalFields

        # Build parser rules
        rules = dict([(field, {'flags': ["--%s" % field]}) for field in fields])

        # Parse the argument vector
        opts = cmdline(argv, rules)

        # Execute the edit request
        self.service.indexes.create(name, **opts.kwargs)

    def events(self, argv):
        opts = cmdline(argv, {})
        self.foreach(opts.args, lambda job: output(job.events()))

    def finalize(self, argv):
        self.foreach(argv, lambda job: job.finalize())

    def foreach(self, argv, func):
        """Apply the function to each job specified in the argument vector."""
        opts = cmdline(argv)
        if len(opts.args) == 0:
            error("Command requires a search-id (sid)", 2)
        for sid in opts.args:
            job = self.lookup(sid)
            if job is None:
                error("Search job '%s' does not exist" % sid, 2)
            func(job)

    def list(self, argv):
        """List all current search jobs if no jobs specified, otherwise
           list the properties of the specified jobs."""

        def read(job):
            for key, value in job.read().iteritems(): 
                # Ignore some fields that make the output hard to read and
                # that are available via other commands.
                if key in ["performance"]: continue
                print "%s: %s" % (key, value)

        if len(argv) == 0:
            index = 0
            for job in self.service.jobs:
                print "@%d : %s" % (index, job.sid)
                index += 1
            return

        self.foreach(argv, read)

    def preview(self, argv):
        opts = cmdline(argv, {})
        self.foreach(opts.args, lambda job: output(job.preview()))

    def results(self, argv):
        opts = cmdline(argv, {})
        self.foreach(opts.args, lambda job: output(job.results()))

    def sid(self, spec):
        """Convert the given search specifier into a serch-id (sid)."""
        if spec.startswith('@'):
            index = int(spec[1:])
            sids = self.service.jobs.list()
            if index < len(sids):
                return sids[index]
        return spec # Assume it was already a valid sid
        
    def lookup(self, spec):
        """Lookup search job by search specifier."""
        return self.service.jobs[self.sid(spec)]

    def pause(self, argv):
        self.foreach(argv, lambda job: job.pause())

    def perf(self, argv):
        self.foreach(argv, lambda job: pprint(job['performance']))

    def run(self, argv):
        """Dispatch the given command & args."""
        command = argv[0]
        handlers = { 
            'cancel': self.cancel,
            'create': self.create,
            'events': self.events,
            'finalize': self.finalize,
            'list': self.list,
            'pause': self.pause,
            'preview': self.preview,
            'results': self.results,
            'searchlog': self.searchlog,
            'perf': self.perf,
            'status': self.status,
            'timeline': self.timeline,
            'touch': self.touch,
            'unpause': self.unpause,
            'update': self.update,
        }
        handler = handlers.get(command, None)
        if handler is None:
            error("Unrecognized command: %s" % command, 2)
        handler(argv[1:])

    def searchlog(self, argv):
        opts = cmdline(argv, {})
        self.foreach(opts.args, lambda job: output(job.searchlog()))

    def status(self, argv):
        pass # UNDONE

    def timeline(self, argv):
        opts = cmdline(argv, {})
        self.foreach(opts.args, lambda job: output(job.timeline()))

    def touch(self, argv):
        self.foreach(argv, lambda job: job.touch())

    def unpause(self, argv):
        self.foreach(argv, lambda job: job.unpause())

    def update(self, argv):
        """Update a search job according to the given argument vector."""

        if len(argv) == 0: 
            error("Command requires an index name", 2)
        name = argv[0]
        if not self.service.indexes.contains(name):
            error("Index '%s' does not exist" % name, 2)
        index = self.service.indexes[name]

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
    usage = "usage: %prog [options] <command> [<args>]"

    argv = sys.argv[1:]

    # Locate the command
    index = next((i for i, v in enumerate(argv) if not v.startswith('-')), -1)

    if index == -1: # No command
        options = argv
        command = ["list"]
    else:
        options = argv[:index]
        command = argv[index:]

    opts = parse(options, {}, ".splunkrc", usage=usage)
    service = connect(**opts.kwargs)
    program = Program(service)
    program.run(command)

if __name__ == "__main__":
    main()

