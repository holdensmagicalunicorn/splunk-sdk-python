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

"""An interactive command shell for Splunk.""" 

from code import compile_command, InteractiveInterpreter
import getopt
from os import path
import readline # Activate readline editing
import sys

try:
    import splunk
except ImportError:
    sys.path.insert(0, path.dirname(path.dirname(path.abspath(__file__))))
    import splunk

from cmdline import default, error, loadif, merge, record

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

def _connect(**kwargs):
    host = kwargs.get("host", default.host)
    port = kwargs.get("port", default.port)
    username = kwargs.get("username", "")
    password = kwargs.get("password", "")
    namespace = kwargs.get("namespace", None)
    return splunk.connect("%s:%s" % (host, port), username, password, namespace)

# UNDONE: Generalize and move to cmdline.py
def getopts(argv):
    opts = {}
    opts = merge(opts, parse(loadif(path.expanduser("~/.splunkrc"))))
    opts = merge(opts, parse(argv))
    opts = merge(opts, parse(loadif(opts.get("config", None))))
    return record(opts)

# UNDONE: Generalize and move to cmdline.py
def parse(argv):
    try:
        rules = [
            "config=", 
            "host=", 
            "interactive",
            "password=", 
            "port=", 
            "username=", 
            "help"]
        kwargs, args = getopt.gnu_getopt(argv, "", rules)
    except getopt.GetoptError as e:
        error(e.msg) # UNDONE: Use same error messages as below
        usage(2)
    opts = {'args': args, 'kwargs': {}}
    for k, v in kwargs:
        assert k.startswith("--")
        k = k[2:]
        opts["kwargs"][k] = v
    return opts

class Session(InteractiveInterpreter):
    def __init__(self, **kwargs):
        self.cn = _connect(**kwargs)
        locals = {
            'cn': self.cn,
            'connect': _connect,
            'load': self.load,
            'search': self.search,
        }
        InteractiveInterpreter.__init__(self, locals)

    # Load the given file into the interpreter
    def load(self, filename):
        self.runcode("exec open('%s')" % filename)

    # Run the interactive interpreter
    def run(self):
        print "%s connected to %s" % (self.cn.username, self.cn.host)
        while True:
            input = raw_input("> ")

            if input is None: 
                return

            if len(input) == 0:
                continue # Ignore

            try:
                # Gather up lines until we have a fragment that compiles
                while True:
                    co = compile_command(input)
                    if co is not None: break
                    input = input + ' ' + raw_input(". ") # Keep trying
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

def main():
    opts = getopts(sys.argv[1:])

    # Connect and initialize the command session
    session = Session(**opts.kwargs)

    # Load any non-option args as script files
    for arg in opts.args: 
        session.load(arg)

    # Enter interactive mode if specified, or if no non option args supplied
    if opts.kwargs.has_key("interactive") or len(opts.args) == 0:
        session.run()

if __name__ == "__main__":
    main()

