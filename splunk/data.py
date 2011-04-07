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

# UNDONE: Schema: target datatype
# UNDONE: Schema: target default value

from xml.etree import ElementTree
from xml.etree.ElementTree import XML

from wire import xname
from util import record

# Unfortunately, some responses don't use namespaces, eg: /services/search/parse
# so we look for both the extended and local version of the following names.

def isdict(name):
    return name == xname.dict or name == "dict"

def isitem(name):
    return name == xname.item or name == "item"

def iskey(name):
    return name == xname.key or name == "key"

def islist(name):
    return name == xname.list or name == "list"

def hasattrs(element):
    return len(element.attrib) > 0

def localname(xname):
    rcurly = xname.find('}')
    return xname if rcurly == -1 else xname[rcurly+1:]

# Parse a <dict> element and return a Python dict
def load_dict(element, nametable = None):
    value = record()
    children = list(element)
    for child in children:
        assert iskey(child.tag)
        name = child.attrib["name"]
        value[name] = load_value(child, nametable)
    return value

def load_element(element, nametable = None):
    tag = element.tag
    if isdict(tag): return load_dict(element, nametable)
    if islist(tag): return load_list(element, nametable)
    attrs = load_attrs(element)
    value = load_value(element, nametable)
    if attrs is None: return value
    if value is None: return attrs
    # If value is simple, merge into attrs dict using special key
    if isinstance(value, str):
        attrs["$text"] = value
        return attrs
    # Both attrs & value are complex, merge the two dicts
    for k,v in attrs.items():
        #assert not value.has_key(k) # Assume no collisions
        value[k] = v
    return value
    
# Parse a <list> element and return a Python list
def load_list(element, nametable = None):
    assert islist(element.tag)
    value = []
    children = list(element)
    for child in children:
        assert isitem(child.tag)
        value.append(load_value(child, nametable))
    return value

def load_attrs(element):
    if not hasattrs(element): return None
    attrs = record()
    for k, v in element.attrib.items(): attrs[k] = v
    return attrs

def load_value(element, nametable = None):
    children = list(element)
    count = len(children)

    # No children, assume a simple text value
    if count == 0:
        text = element.text
        if text is None: return None
        text = text.strip()
        if len(text) == 0: return None
        return text

    # Look for the special case of a single well-known structure
    if count == 1:
        child = children[0]
        tag = child.tag
        if isdict(tag): return load_dict(child, nametable)
        if islist(tag): return load_list(child, nametable)

    value = record()
    for child in children:
        name = localname(child.tag)
        item = load_element(child, nametable)
        # If we have seen this name before, promote the value to a list
        if value.has_key(name):
            current = value[name]
            if not isinstance(current, list): value[name] = [current]
            value[name].append(item)
        else:
            value[name] = item

    return value

# UNDONE: Nametable
def load(text, path = None):
    if text is None: return None
    text = text.strip()
    if len(text) == 0: return None
    nametable = {
        'namespaces': [],
        'names': {}
    }
    root = XML(text)
    items = [root] if path is None else root.findall(path)
    count = len(items)
    if count == 0: 
        return None
    if count == 1:
        item = items[0]
        return load_value(item, nametable)
        # return { localname(item.tag): value }
    return [ load_value(item, nametable) for item in items ]

if __name__ == "__main__":
    def isxml(text): return text.strip().startswith('<')
    import sys
    from pprint import pprint
    input = sys.stdin.read()
    if isxml(input):
        value = load(input)
        pprint(value)
    else:
        print input
