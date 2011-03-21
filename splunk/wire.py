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

from util import record

default = record({
    'host': "localhost",
    'port': "8089",
    'scheme': "https",
})

# XML Namespaces
namespace = record({
    'atom': "http://www.w3.org/2005/Atom",
    'rest': "http://dev.splunk.com/ns/rest",
    'opensearch': "http://a9.com/-/spec/opensearch/1.1",
})

# Returns an extended name for the given XML namespace & localname
def _xname(namespcae, localname):
    return "{%s}%s" % (namespcae, localname)

xname = record({
    'content': _xname(namespace.atom, "content"),
    'dict': _xname(namespace.rest, "dict"),
    'eaitype': _xname(namespace.rest, "eai:type"),
    'entry': _xname(namespace.atom, "entry"),
    'id': _xname(namespace.atom, "id"),
    'item': _xname(namespace.rest, "item"),
    'key': _xname(namespace.rest, "key"),
    'link': _xname(namespace.atom, "link"),
    'list': _xname(namespace.rest, "list"),
    'title': _xname(namespace.atom, "title"),
})

