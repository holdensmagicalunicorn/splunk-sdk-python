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

"""Command line utilities shared by command line tools & unit tests."""

from os import path
from optparse import OptionParser
import sys

__all__ = [ "parse", "Parser" ]

def config(option, opt, value, parser):
    assert opt == "--config"
    parser.load(value)

# Print the given message to stderr, and optionally exit
def error(message, exitCode = None):
    print >> sys.stderr, "Error: %s" % message
    if not exitCode is None: sys.exit(exitCode)

class record(dict):
    def __getattr__(self, name):
        try: 
            return self[name] 
        except KeyError: 
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value

# Default Splunk cmdline rules
SPLUNK_RULES = {
    'config': {
        'flags': ["--config"],
        'action': "callback",
        'callback': config,
        'type': "string",
        'nargs': "1",
        'help': "Load options from config file" 
    },
    'scheme': {
        'flags': ["--scheme"],
        'default': "https",
        'help': "Scheme (default 'https')",
    },
    'host': {
        'flags': ["--host"],
        'default': "localhost",
        'help': "Host name (default 'localhost')" 
    },
    'port': { 
        'flags': ["--port"],
        'default': "8089",
        'help': "Port number (default 8089)" 
    },
    'username': {
        'flags': ["--username"],
        'default': None,
        'help': "Username to login with" 
    },
    'password': {
        'flags': ["--password"], 
        'default': None,
        'help': "Password to login with" 
    },
}

class Parser(OptionParser):
    def __init__(self, rules = None, **kwargs):
        OptionParser.__init__(self, **kwargs)
        self.dests = set({})
        self.result = record({ 'args': [], 'kwargs': record() })
        if rules is not None: self.init(rules)

    def init(self, rules):
        """Initialize the parser with the given command rules."""
        # Initialize the option parser
        for dest in rules.keys():
            rule = rules[dest]

            # Assign defaults ourselves here, instead of in the option parser
            # itself in order to allow for multiple calls to parse (dont want
            # subsequent calls to override previous values with default vals).
            if rule.has_key('default'):
                self.result['kwargs'][dest] = rule['default']

            flags = rule['flags']
            kwargs = { 'action': rule.get('action', "store") }
            # NOTE: Don't provision the parser with defaults here, per above.
            for key in ['callback', 'help', 'metavar', 'type']:
                if rule.has_key(key): kwargs[key] = rule[key]
            self.add_option(*flags, dest=dest, **kwargs)

            # Remember the dest vars that we see, so that we can merge results
            self.dests.add(dest)
            
    # Load command options from given 'config' file. Long form options may omit
    # the leading "--", and if so we fix that up here.
    def load(self, filepath):
        argv = []
        try:
            file = open(filepath)
        except:
            error("Unable to open '%s'" % filepath, 2)
        for line in file:
            if line.startswith("#"): continue # Skip comment
            line = line.strip()
            if not line.startswith("-"): line = "--" + line
            argv.append(line)
        self.parse(argv)
        return self

    def loadif(self, filepath):
        """Load the given filepath if it exists, otherwise ignore."""
        if path.isfile(filepath): self.load(filepath)
        return self

    def loadrc(self, filename):
        filepath = path.expanduser("~/%s" % filename) # UNDONE: Windows
        self.loadif(filepath)
        return self

    def parse(self, argv):
        """Parse the given argument vector."""
        kwargs, args = self.parse_args(argv)
        self.result['args'] += args
        # Annoying that parse_args doesn't just return a dict
        for dest in self.dests:
            value = getattr(kwargs, dest)
            if value is not None:
                self.result['kwargs'][dest] = value
        return self

def parse(argv):
    return parser().parse(argv).result

def parser(rules=None, **kwargs):
    """Instantiate a parser with the default rule set and optional extensions
       and overrides."""
    rules = SPLUNK_RULES if rules is None else dict(SPLUNK_RULES, **rules)
    return Parser(rules, **kwargs)
        
if __name__ == "__main__":
    parser = Parser(rules)
    parser.parse(sys.argv[1:])
    from pprint import pprint
    pprint(parser.result)

