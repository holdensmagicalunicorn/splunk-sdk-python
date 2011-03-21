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

"""Command line utilities shared by the command line tools."""

# UNDONE: Generalize cmdline parser, including support for required args

from os import path
import sys

# Print the given message to stderr, and optionally exit
def error(message, exitCode = None):
    print >> sys.stderr, "Error: %s" % message
    if not exitCode is None: sys.exit(exitCode)

# Load the given config file. Long form options may omit the leading "--", and
# if so we fix that up here.
def load(filePath):
    argv = []
    try:
        file = open(filePath)
    except:
        error("Unable to open '%s'" % filePath, 2)
    for line in file:
        if line.startswith("#"): continue # Skip comment
        line = line.strip()
        if not line.startswith("-"): line = "--" + line
        argv.append(line)
    return argv

# Load the given config file, if it exists
def loadif(filePath):
    if filePath is None: return ""
    return load(filePath) if path.isfile(filePath) else ""

def merge(config1, config2):
    args1 = config1.get("args", [])
    args2 = config2.get("args", [])
    kwargs1 = config1.get("kwargs", {})
    kwargs2 = config2.get("kwargs", {})
    return record({'args': args1 + args2, 'kwargs': dict(kwargs1, **kwargs2)})

class Record(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError: 
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value

def record(dict = {}): 
    return Record(dict)

default = record({
    'host': "localhost",
    'port': "8089",
    'scheme': "https",
})

