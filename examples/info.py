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

"""Given a hostname (and credentials), print out a simple report showing 
   the state of the system. This example shows how to access various system
   resources."""

# UNDONE: print_info could inculde info on auth providers
# UNDONE: Is it useful to dump configs?

from os import path
import sys
import textwrap

import splunk.binding as binding
import splunk.data as data

import tools.cmdopts as cmdopts

class HTTPError(Exception): pass

class Writer:
    def __init__(self, out = sys.stdout):
        self.out = out
        self.wrapper = textwrap.TextWrapper() 
        self.level(0)

    def level(self, value=None):
        """Set the indent level."""
        if value is None: return self._level
        self._level = value
        indent = "    "*value
        self.wrapper.initial_indent = indent
        self.wrapper.subsequent_indent = indent + "  "

    def indent(self, count):
        """Change the indent level by the given amount."""
        value = self.level()
        value = value + count
        self.level(value)

    def write(self, text):
        self.out.write(self.wrapper.fill(text))

    def writeln(self, text = None):
        if text is not None: self.write(text)
        self.out.write('\n')

# Retrieve the link with the given rel value from the given atom entry
def getlink(item, rel):
    link = item.get('link', None)
    if link is None: return None
    if not isinstance(link, list): link = [link] # Normalize
    for elem in link: 
        if elem.rel == rel: return elem
    return None # Not found

def check_response(response):
    if response.status != 200:
        raise HTTPError, "%d (%s)" % (response.status, response.reason)

def load(cx, path, **kwargs):
    response = cx.get(path, **kwargs)
    check_response(response)
    return data.load(response.body.read())

# Load an entity resource from the given path
def load_entity(cx, path):
    value = load(cx, path)
    entry = value.get("entry", None)
    assert entry is not None
    return entry
    
# Load a collection resource from the given path
def load_collection(cx, path):
    value = load(cx, path, count=-1)
    entry = value.get("entry", None)
    if entry is None: return None
    return entry if isinstance(entry, list) else [entry] # Normalize

def write_alerts(cx, out):
    write_collection(cx, out, "Alerts", "alerts/fired_alerts/-")

def write_apps(cx, out):
    out.writeln("Apps")
    entry = load_collection(cx, 'apps/local')
    if entry is None: return
    out.indent(1)
    for item in entry:
        content = item.content
        out.writeln("%s (%s)" % (content.label, item.title))
        out.indent(1)
        author = content.get("author", None)
        if author is not None:
            out.writeln("author: %s" % author)
        version = content.get("version", None)
        if version is not None:
            out.writeln("version: %s" % version)
        description = content.get("description", None)
        if description is not None:
            out.writeln("description: %s" % description)
        out.indent(-1)
    out.indent(-1)

def write_collection(cx, out, title, path):
    out.writeln(title)
    entry = load_collection(cx, path)
    if entry is None: return
    out.indent(1)
    for item in entry:
        out.writeln(item.title)
        if item.has_key('content'): 
            out.indent(1)
            write_content(out, item.content)
            out.indent(-1)
    out.indent(-1)

# Custom search commands
def write_commands(cx, out):
    write_collection(cx, out, "Commands", "data/commands")

def write_conf(cx, out, heading, file):
    out.writeln(heading)
    out.indent(1)
    entry = load_collection(cx, "properties/%s" % file)
    if entry is None: return
    for item in entry:
        out.writeln(item.title)
        out.indent(1)
        href = getlink(item, 'alternate').href
        write_conf_stanza(cx, out, href)
        out.indent(-1)
    out.indent(-1)

ignore = [ # Keys to ignore
    "SEGMENTATION-all",         # Splunk web specific
    "SEGMENTATION-inner",       # Splunk web specific
    "SEGMENTATION-outer",       # Splunk web specific
    "SEGMENTATION-raw",         # Splunk web specific
    "SEGMENTATION-standard",    # Splunk web specific
]
def write_conf_stanza(cx, out, url):
    entry = load_collection(cx, url)
    for item in entry:
        key = item.title
        if key in ignore: continue
        href = getlink(item, 'alternate').href
        body = cx.get(href).body.read().strip()
        if len(body) != 0: 
            out.writeln("%s = %s" % (key, body))

# Shared routine to print content element
def write_content(out, content):
    for key in sorted(content.keys()):
        if key in ['eai:acl', 'type']: continue # Elide
        out.writeln("%s: %s" % (key, content[key]))

def write_eventtypes(cx, out):
    write_collection(cx, out, "Eventtypes", "saved/eventtypes")

def write_extractions(cx, out):
    write_collection(cx, out, "Extractions (props)", "data/props/extractions")
    out.writeln()
    write_collection(cx, out, "Extractions (transforms)", "data/transforms/extractions")

def write_fields(cx, out):
    out.writeln("Fields")
    entry = load_collection(cx, "search/fields")
    if entry is None: return
    out.indent(1)
    for item in entry:
        fieldname = item.title
        out.writeln(fieldname)
        data = load(cx, "search/fields/%s" % fieldname)
        text = data.content['$text']
        out.indent(1)
        out.writeln(text)
        out.indent(-1)
    out.indent(-1)

def write_fieldaliases(cx, out):
    write_collection(cx, out, "Fieldaliases", "data/props/fieldaliases")

def write_jobs(cx, out):
    out.writeln("Jobs")
    entry = load(cx, 'search/jobs').entry
    if entry is None: return
    out.indent(1)
    for item in entry:
        out.writeln(item.title)
        out.indent(1)
        content = item.content
        # Pick a few representative items to display
        out.writeln("sid: %s" % content.sid)
        out.writeln("label: %s" % content.label)
        out.writeln("scanCount %s" % content.scanCount)
        out.writeln("eventCount %s" % content.eventCount)
        out.writeln("resultCount %s" % content.resultCount)
        out.indent(-1)
    out.indent(-1)

def write_outputs(cx, out):
    outputs = {
        'default': "data/outputs/tcp/default",
        'group': "data/outputs/tcp/group",
        'server': "data/outputs/tcp/server",
        'syslog': "data/outputs/tcp/syslog",
    }
    out.writeln("Outputs")
    out.indent(1)
    for output, path in outputs.iteritems():
        write_collection(cx, out, output, path)
    out.indent(-1)

def write_settings(cx, out):
    out.writeln("Settings")
    out.indent(1)
    content = load_entity(cx, 'server/settings').content
    write_content(out, content)
    out.indent(-1)

def write_indexes(cx, out):
    write_collection(cx, out, "Indexes", "data/indexes")

def write_inputs(cx, out):
    inputs = {
        'monitor': "data/inputs/monitor",
        'script': "data/inputs/script",
        'tcp/cooked': "data/inputs/tcp/cooked",
        'tcp/raw': "data/inputs/tcp/raw",
        'udp': "data/inputs/udp",
    }
    out.writeln("Inputs")
    out.indent(1)
    for input, path in inputs.iteritems():
        entry = load_collection(cx, path)
        if entry is None: continue
        for item in entry:
            out.writeln(item.title)
            out.indent(1)
            out.writeln("kind: %s" % input)
            write_content(out, item.content)
            out.indent(-1)
    out.indent(-1)

def write_lookups(cx, out):
    write_collection(cx, out, "Lookups (props)", "data/props/lookups")
    out.writeln()
    write_collection(cx, out, "Lookups (transforms)", "data/transforms/lookups")

def write_messages(cx, out):
    write_collection(cx, out, "Messages", "messages")

# Write out all info related to the Splunk service
def write_service(cx, out):
    content = load_entity(cx, 'server/info').content
    out.indent(1)
    out.writeln("serverName: %s" % content.serverName)
    out.writeln("version: %s" % content.version)
    out.writeln("build: %s" % content.build)
    out.writeln("cpu_arch: %s" % content.cpu_arch)
    out.writeln("os_name: %s" % content.os_name)
    out.writeln("os_version: %s" % content.os_version)
    out.writeln("os_build: %s" % content.os_build)
    out.writeln()
    write_settings(cx, out)
    out.writeln()
    write_service_logs(cx, out)
    out.writeln()
    write_messages(cx, out)
    out.indent(-1)

def write_service_logs(cx, out):
    write_collection(cx, out, "Logs", "server/logger")

# Tags is a collection of collections. Each tag is a collectio of field::value 
# pairs
def write_tags(cx, out):
    out.writeln("Tags")
    entry = load_collection(cx, "search/tags")
    if entry is None: return
    out.indent(1)
    for item in entry:
        tag = item.title
        write_collection(cx, out, tag, "search/tags/%s" % tag)
    out.indent(-1)

def write_users(cx, out):
    out.writeln("Users")
    entry = load_collection(cx, 'authentication/users')
    if entry is None: return
    out.indent(1)
    for item in entry:
        content = item.content
        out.writeln("%s (%s)" % (item.title, content.realname))
        out.indent(1)
        out.writeln("email: %s" % content.email)
        out.writeln("roles: %s" % '; '.join(content.roles))
        out.indent(-1)
    out.indent(-1)

def write_searches(cx, out):
    write_collection(cx, out, "Searches", 'saved/searches')

def write_sourcetype_renames(cx, out):
    write_collection(
        cx, out, "Sourcetype-renames", "data/props/sourcetype-rename")

def dump(cx):
    out = Writer()

    # Server info
    write_service(cx, out)
    out.writeln()

    # Server objects
    write_apps(cx, out)
    out.writeln()
    write_commands(cx, out)
    out.writeln()
    write_eventtypes(cx, out)
    out.writeln()
    write_extractions(cx, out)
    out.writeln()
    write_fields(cx, out)
    out.writeln()
    write_fieldaliases(cx, out)
    out.writeln()
    write_indexes(cx, out)
    out.writeln()
    write_inputs(cx, out)
    out.writeln()
    write_lookups(cx, out)
    out.writeln()
    write_outputs(cx, out)
    out.writeln()
    write_searches(cx, out)
    out.writeln()
    write_sourcetype_renames(cx, out)
    out.writeln()
    write_tags(cx, out)
    out.writeln()
    write_users(cx, out)
    out.writeln()
    
    # Execution state
    write_alerts(cx, out)
    out.writeln()
    write_jobs(cx, out)
    out.writeln()

    write_conf(cx, out, "Inputs (inputs.conf)", "inputs")
    out.writeln()
    write_conf(cx, out, "Indexes (indexes.conf)", "indexes")
    out.writeln()
    write_conf(cx, out, "Properties (props.conf)", "props")
    out.writeln()
    write_conf(cx, out, "Segmenters (segmenters.conf)", "segmenters")
    out.writeln()
    write_conf(cx, out, "Transforms (transforms.conf)", "transforms")
    out.writeln()

def main():
    opts = cmdopts.parser().loadrc(".splunkrc").parse(sys.argv[1:]).result
    dump(binding.connect(**opts.kwargs))

if __name__ == "__main__":
   main() 
