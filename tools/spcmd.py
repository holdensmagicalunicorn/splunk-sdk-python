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

# This tool basically provides a little sugar on top of the Python interactive
# command interpreter. It establishes a "default" connection and makes the
# properties of that connection ambient. It also picks up known local variables
# and passes those values as options to various commands. For example, you can
# set the default output_mode for a session by simply setting a local variable
# 'output_mode' to a legal output_mode value.

# UNDONE: Banner!
# UNDONE: Attempt to re-login on a 401 (Unauthorized) in case session expired
# UNDONE: usage() is not defined (!) 
# UNDONE: Implement command completion 
# UNDONE: Ambient args for other methods

"""An interactive command shell for Splunk.""" 

from code import compile_command, InteractiveInterpreter
from os import path
import readline # Activate readline editing
import sys

import splunk
import cmdopts

# Ambient search arguments
_search_args = [
    "earliest_time",
    "enable_lookups",
    "exec_mode",
    "id",
    "latest_time",
    "max_count",
    "max_time",
    "namespace",
    "now",
    "output_mode",
    "reload_macros",
    "rf",
    "search_mode",
    "spawn_process",
    "status_buckets",
    "time_format",
    "timeout",  
]

class Session(InteractiveInterpreter):
    def __init__(self, **kwargs):
        self.cn = splunk.api.connect(**kwargs)
        locals = {
            'cn': self.cn,
            'connect': splunk.connect,
            'load': self.load,
            'search': self.search,
        }
        InteractiveInterpreter.__init__(self, locals)

    def load(self, filename):
        exec open(filename).read() in self.locals, self.locals

    # Run the interactive interpreter
    def run(self):
        print "%s connected to %s" % (self.cn.username, self.cn.host)
        while True:
            try:
                input = raw_input("> ")
            except EOFError:
                print "\n\nThanks for using Splunk>.\n"
                return

            if input is None: 
                return

            if len(input) == 0:
                continue # Ignore

            try:
                # Gather up lines until we have a fragment that compiles
                while True:
                    co = compile_command(input)
                    if co is not None: break
                    input = input + '\n' + raw_input(". ") # Keep trying
            except SyntaxError, e:
                self.showsyntaxerror()
                continue
            except Exception, e:
                print "Error: %s" % e
                continue

            self.runcode(co)

    def search(self, query, **kwargs):
        if not query.startswith("search"):
            query = "search %s" % query

        # Do a quick syntax check on the search query
        try:
            self.cn.parse(query)
        except splunk.SyntaxError, e:
            return e
            
        # Pick up ambient search args from environment
        ambient = {}
        for arg in _search_args:
            value = self.locals.get(arg, None)
            if value is not None:
                ambient[arg] = value

        # Override ambient args with any passed explicitly
        ambient.update(kwargs)

        try:
            return self.cn.search(query, **ambient)
        except Exception, e:
            return e


# Additional cmdopts parser rules
rules = {
    "interactive": {
        'flags': ["-i", "--interactive"], 
        'action': "store_true",
        'help': "Enter interactive mode",
    }
}

def main():
    opts = cmdopts.parser(rules).loadrc(".splunkrc").parse(sys.argv[1:]).result

    # Connect and initialize the command session
    session = Session(**opts.kwargs)

    # Load any non-option args as script files
    for arg in opts.args: session.load(arg)

    # Enter interactive mode if specified, or if no non option args supplied
    if opts.kwargs.has_key("interactive") or len(opts.args) == 0:
        session.run()

if __name__ == "__main__":
    main()

