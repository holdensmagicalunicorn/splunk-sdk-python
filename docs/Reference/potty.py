#!/usr/bin/env python
#
# Copyright 2011 Splunk, Inc.
#

from pprint import pprint # UNDONE

import sys

DEFAULT_DEFAULT = "None"
DEFAULT_DATATYPE = "string"
DEFAULT_DESCRIPTION = "DESCRIPTION"
DEFAULT_REQUIRED = "True"
DEFAULT_SUMMARY = "SUMMARY"

def error(message, exitCode = None):
    sys.stderr.write(message)
    sys.stderr.write('\n')
    if exitCode is not None: sys.exit(exitCode)

class LineReader:
    """A sequence of file lines, with 1-line lookahead."""
    def __init__(self, file):
        self.file = file
        self.next = None # 1-line pushback
        self.lineno = 0

    def read(self):
        if self.next is not None:
            line, self.next = self.next, None
            return line
        self.lineno += 1
        return self.file.readline()

    def peek(self):
        if self.next is None:
            self.next = self.read()
        return self.next

KEYS = ["msgctxt", "msgid", "msgstr"]
class ItemReader:
    """Parses a .po/pot file into a sequence of entry items."""
    def __init__(self, file):
        self.reader = LineReader(file)

    def read(self):
        while True:
            line = self.reader.read()
            if len(line) == 0: 
                return None # EOF
            if line.startswith('#'): 
                continue # Ignore comments
            line = line.strip()
            if len(line) == 0: 
                continue # Ignore whitespace

            key = None
            for item in KEYS:
                if line.startswith(item):
                    key = item
                    line = line[len(key):]
                    break
            if key is None: self.syntax(line)

            # Scan remainder of line for value
            line = line.strip()
            if not line.startswith('"') or not line.endswith('"'):
                self.syntax("expected string literal: '%s'" % line)

            value = line.strip('"')

            # NOTE: This code assumes that .po/.pot files do not allow
            # newlines inside of a string literal.

            # Check subsequent lines for string linteral continuations
            while True:
                line = self.reader.peek().strip()
                if not line.startswith('"'): 
                    break
                if not line.endswith('"'):
                    self.syntax("newline in string literal")
                value += line.strip('"')
                self.reader.read() # Consume the line

            return key, value

    def syntax(self, message):
        """Print syntax error message and exit."""
        error("Syntax error (line %d): %s" % (self.reader.lineno, message), 2)

class EntryReader:
    """Gathers entry items into A sequence of .po/.pot file entries."""
    def __init__(self, file):
        self.reader = ItemReader(file)

    def read(self):
        result = None
        while True:
            item = self.reader.read()
            if item is None: break
            k,v = item
            if result is None: result = {}
            assert not result.has_key(k)
            result[k] = v
            if k == "msgstr": break
        return result

METHODS = ["GET", "POST", "DELETE"]
def crack_entry(msgctxt, value):
    """Process a parsed .po/pot entry and return an endpoint 'info' fragment."""

    # The .po/.pot entry 'triples' encode information about an endpoint or
    # one of its constituents (method, param or return). This routime
    # craks the encoding of the triple and returns the info fragment in
    # a slightly more digestible form.

    # The msgctxt encodes both the 'object' kind, and instance data and the
    # value argument is a dict of property values affiliated with that object,
    # as: <method>? <path>([?:]<value>)?

    method = None
    for item in METHODS:
        if msgctxt.startswith(item):
            method = item
            msgctxt = msgctxt[len(item):].strip()
            break

    # If there is no method, then its an endpoint-level fragment
    if method is None:
        return {
            'kind': "endpoint",
            'path': msgctxt,
            'info': value,
        }

    # Is it parameter info framgne?
    delim = msgctxt.find('?')
    if delim != -1:
        path = msgctxt[:delim]
        name = msgctxt[delim+1:]
        return {
            'kind': "param",
            'path': path,
            'method': method,
            'name': name,
            'info': value,
        }

    # Is it return info fragment?
    delim = msgctxt.find(':')
    if delim != -1:
        path = msgctxt[:delim]
        code = msgctxt[delim+1:]
        return {
            'kind': "return",
            'path': path,
            'method': method,
            'status': code,
            'info': value,
        }

    # If there is no param name or return code, then its a method-level
    # fragment
    return {
        'kind': "method",
        'path': msgctxt,
        'method': method,
        'info': value,
    }

def crack_entries(entries):
    infos = []
    for msgctxt, value in entries.iteritems():
        if len(msgctxt) == 0: continue # Ignore entries missing a context
        infos.append(crack_entry(msgctxt, value))
    return infos

def emit(endpoints):
    paths = sorted(endpoints.keys())
    for path in paths:
        print "# %s" % path
        endpoint = endpoints[path]
        summary = endpoint.get('summary', DEFAULT_SUMMARY)
        print summary

        methods = endpoints[path].get('methods', None)
        if methods is None: continue
        for methodname in sorted(methods.keys()):
            print "## %s" % methodname

            method = methods[methodname]
            print method.get('summary', DEFAULT_SUMMARY)

            params = method.get('params', None)
            if params is not None:
                print "### Parameters"
                for name in sorted(params.keys()):
                    info = params[name]
                    datatype= info.get('datatype', DEFAULT_DATATYPE)
                    default = info.get('default', DEFAULT_DEFAULT)
                    required = info.get('required', DEFAULT_REQUIRED)
                    summary = info.get('summary', DEFAULT_SUMMARY)
                    print "    * %s, %s, %s, %s, %s" % (
                        name, datatype, default, required, summary)

            returns = method.get('returns', None)
            if returns is not None:
                print "### Returns"
                for code in sorted(returns.keys()):
                    info = returns[code]
                    summary = info.get('summary', DEFAULT_SUMMARY)
                    print "    * %s, %s" % (code, summary)

            print method.get('description', DEFAULT_DESCRIPTION)

def emitwm(endpoints):
    """Emit content in Wiki Markup format, suitable for MediaWiki."""

    paths = sorted(endpoints.keys())
    for path in paths:
        print "== %s ==" % path
        endpoint = endpoints[path]

        print endpoint.get('summary', DEFAULT_SUMMARY)

        methods = endpoints[path].get('methods', None)
        if methods is None: continue

        for methodname in sorted(methods.keys()):
            print "=== %s %s ===" % (methodname, path)

            method = methods[methodname]
            print method.get('summary', DEFAULT_SUMMARY)

            params = method.get('params', None)
            print "==== Parameters ===="
            if params is None:
                print "None"
                print
            else:
                print "{| border=1 cellpadding=5 cellspacing=0"
                print "|- bgcolor=\"D9EAED\""
                print "! Name !! Type !! Required !! Description"
                for paramname in sorted(params.keys()):
                    info = params[paramname]
                    datatype= info.get('datatype', DEFAULT_DATATYPE)
                    default = info.get('default', DEFAULT_DEFAULT)
                    required = info.get('required', DEFAULT_REQUIRED)
                    summary = info.get('summary', DEFAULT_SUMMARY)
                    print "|-"
                    print "| '''%s''' || %s || %s || %s " % (
                        paramname, datatype, required, summary)
                print "|}"

            returns = method.get('returns', None)
            print "==== Response ===="
            if returns is None:
                print "None"
                print
            else:
                print "{| border=1 cellpadding=5 cellspacing=0"
                print "|- bgcolor=\"D9EAED\""
                print "! Status Code !! Description"
                for code in sorted(returns.keys()):
                    info = returns[code]
                    summary = info.get('summary', DEFAULT_SUMMARY)
                    print "|-"
                    print "| '''%s''' || %s" % (code, summary)
                print "|}"

            print method.get('description', DEFAULT_DESCRIPTION)

# UNDONE: Rewrite the following to build an XML tree using the DOM and
# let the xml library pretty-print the results (and handle escaping, etc).
def emitxml(endpoints):
    print "<endpoints>"
    paths = sorted(endpoints.keys())
    for path in paths:
        print "  <endpoint path='%s'>" % path

        endpoint = endpoints[path]

        summary = endpoint.get('summary', "SUMMARY")
        print "    <summary>%s</summary>" % summary


        print "    <methods>"
        methods = endpoints[path].get('methods', None)
        if methods is not None:
            for methodname in sorted(methods.keys()):
                print "      <method name='%s'>" % methodname

                method = methods[methodname]
                summary = method.get('summary', "SUMMARY")
                print "        <summary>%s</summary>" % summary

                print "        <params>"
                params = method.get('params', None)
                if params is not None:
                    for name in sorted(params.keys()):
                        info = params[name]
                        datatype= info.get('datatype', "string")
                        default = info.get('default', "None")
                        required = info.get('required', "Required")
                        summary = info.get('summary', "<summary>")
                        print "          <param name='%s' datatype='%s' default='%s' rquired='%s'>%s</param>" % (name, datatype, default, required, summary)
                print "        </params>"

                print "        <returns>"
                returns = method.get('returns', None)
                if returns is not None:
                    for code in sorted(returns.keys()):
                        info = returns[code]
                        summary = info.get('summary', "<summary>")
                        print "          <return status='%s'>%s</return>" % (
                            code, summary)

                description = method.get('description', DEFAULT_DESCRIPTION)
                print "        </returns>"
                print "        <description>%s</description>" % description
                print "      </method>"
            print "    </methods>"
        print "  </endpoint>"
    print "</endpoints>"

def ensure(endpoints, *args):
    """Ensure that the key path given in *args exists in the endpoints table."""
    current = endpoints
    for arg in args:
        if not current.has_key(arg):
            current[arg] = {}
        current = current[arg]
        
def load(file):
    """Loads the given .po/.pot file into a map keyed by msgctxt."""
    reader = EntryReader(file)
    entries = {}
    while True:
        entry = reader.read()
        if entry is None: break
        msgctxt = entry.get('msgctxt', "")
        if not entries.has_key(msgctxt):
            entries[msgctxt] = {}
        field = entry['msgid']
        value = entry['msgstr']
        entries[msgctxt][field] = value
    return entries

def merge_info(endpoints, item):
    """Merge the given info fragment into the endpoints table."""
    kind = item['kind']
    path = item['path']
    info = item['info']
    method = item.get('method', None)

    if kind == "endpoint":
        ensure(endpoints, path)
        endpoints[path].update(info)

    elif kind == "method":
        ensure(endpoints, path, "methods", method)
        endpoints[path]['methods'][method].update(info)

    elif kind == "param":
        name = item['name']
        ensure(endpoints, path, "methods", method, "params", name)
        endpoints[path]['methods'][method]['params'][name].update(info)

    elif kind == "return":
        code = item['status']
        ensure(endpoints, path, "methods", method, "returns", code)
        endpoints[path]['methods'][method]['returns'][code].update(info)

    else: assert False # Unexpected

def merge_infos(infos):
    endpoints = {}
    for item in infos: 
        merge_info(endpoints, item)
    return endpoints
      
def process(file):
    # Load a dict of gettext entries, coalesced (keyed) by msgctxt
    entries = load(file)

    # Crack the entry triples into kinded fragments of endpoint information 
    infos = crack_entries(entries)

    # Merge the info fragments into a hierarchical structure rooted at
    # the endpoint path, ie: <path>/methods/<method>/
    endpoints = merge_infos(infos)

    emitwm(endpoints)

def main(argv):
    if len(argv) == 0:
        process(sys.stdin)
        return

    for arg in argv:
        try:
            file = open(arg, 'r')
        except:
            error("Can't open '%s'" % arg, 2)
        process(file)
        
if __name__ == "__main__":
    main(sys.argv[1:])
