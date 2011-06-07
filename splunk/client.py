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

# The purpose of this module is to provide a friendlier domain interface to 
# various Splunk endpoints. The approach here is to leverage the binding layer
# to capture endpoint context and provide objects and methods that offer
# simplified access their corresponding endpoints. The design specifically
# avoids caching resource state. From the pov of this module, the 'policy' for
# caching and refreshing resource state belongs in the application or a higher
# level framework, and its the purpose of this module to provide simplified
# access to that resource state.
#
# A side note, the objects below that provide helper methods for updating eg:
# Entity state, are written in a fluent style.

from pprint import pprint # UNDONE

# UNDONE: Cases below where we need to pass schema to data.load (eg: Collection)
# UNDONE: Check status needs to attempt to retrive error message from the
#  the resonse body. Eg: a call to index.disable on the defaultDatabase will
#  return a 404 (which is a little misleading) but the response body contains
#  a message indicating that disable cant be called on the default database.

# NOTES
# =====
#
# Layer 1 -- Entity.read => content, Collection.list => keys
# Layer ' -- get, put, post, delete
# Layer 0 -- request
#
# Service
#
#   * status
#   * login
#   * logout
#   * settings/info
#   * restart
#
#   * Licensing
#   * Monitoring
#   * Deployment
#
# Access Control - users, roles, capabilities ..
#
# Knowledge (conf)
#   * Stanza?
#
# Index
# Input(s)
# Output(s)
#
# Search
#   * parse
#   * jobs
#   * search (export)
#   * saved
#
# Applications
#   * ..

from time import sleep

import splunk.binding as binding
from splunk.binding import Context, HTTPError
import splunk.data as data
from splunk.data import record

__all__ = [
    "Service"
]

# XML Namespaces
# "http://www.w3.org/2005/Atom",
# "http://dev.splunk.com/ns/rest",
# "http://a9.com/-/spec/opensearch/1.1",

PATH_INDEX = "data/indexes/%s"
PATH_INDEXES = "data/indexes"

# Ensure that this is a syntactically valid Splunk namespace.
# The namespace must be of the form <username>:<appname> where both username
# and appname must be at least one character, must not contain a colon (':'),
# and may be a wildcard ('*').
def _check_namespace(namespace):
    if len(namespace) < 3 or namespace.count(':') != 1:
        raise SplunkError("Invalid namespace: '%s'" % namespace)

# Combine the given host & path to create a fully-formed URL.
def _mkurl(host, path):
    # Append default port to host if port is not already provided
    if not ':' in host: host = host + ':' + binding.DEFAULT_PORT
    return "%s://%s%s" % (binding.DEFAULT_SCHEME, host, path)

# Construct a resource path using the given path suffix and optional namespace
def _mkpath(suffix, namespace = None):
    if namespace is None: 
        return "/services/%s" % suffix
    username, appname = namespace.split(':')
    if username == "*": username = '-'
    if appname == "*": appname = '-'
    return "/servicesNS/%s/%s/%s" % (username, appname, suffix)

def check_status(response, *args):
    """Checks that the given HTTP response is one of the expected values."""
    if response.status not in args:
        raise HTTPError(response.status, response.reason)

# Response utilities
def load(response):
    return data.load(response.body.read())

class Service(Context):
    def __init__(self, **kwargs):
        Context.__init__(self, **kwargs)

    @property
    def indexes(self):
        return Indexes(self)

class Endpoint:
    def __init__(self, service, path):
        self.service = service
        self.path = path
        self.get = service.bind(path, "get")
        self.post = service.bind(path, "post")

    def invoke(self, action, **kwargs):
        """Invoke a custom action on the Endpoint."""
        response = self.service.post(self.path + '/' + action, **kwargs)
        check_status(response, 200)
        return self

# UNDONE: Common create & delete options?
class Collection(Endpoint):
    def __init__(self, service, path):
        Endpoint.__init__(self, service, path)

    def __getitem__(self, key):
        pass # Abstract

    def itemmeta(self):
        """Returns collection item metadata."""
        response = self.service.get(self.path + "/_new")
        check_status(response, 200)
        content = load(response).entry.content
        return record({
            'eai:acl': content['eai:acl'],
            'eai:attributes': content['eai:attributes']
        })

    def list(self): # UNDONE: keys?
        pass # Abstract

class Entity(Endpoint):
    """Abstract base class that implements the Splunk 'entity' protocol."""

    def __init__(self, service, path):
        Endpoint.__init__(self, service, path)
        # UNDONE: The following should be derived by reading entity links
        self.delete = lambda: self.service.delete(self.path)
        self.disable = lambda: self.invoke("disable")
        self.enable = lambda: self.invoke("enable")
        self.reload = lambda: self.invoke("_reload")

    def __getitem__(self, key):
        return self.read()[key]

    def __setitem__(self, key, value):
        self.update(key=value)

    def read(self, *args):
        """Read and return the current entity value, optionally returning
           only the requested fields, if specified."""
        response = self.get()
        check_status(response, 200)
        content = load(response).entry.content
        if len(args) > 0: # We have filter args
            result = record({})
            for key in args: result[key] = content[key]
        else:
            # Eliminate some noise by default
            result = content
            del result['eai:acl']
            del result['eai:attributes']
            del result['type']
        return result

    def readmeta(self):
        """Return the entity's metadata."""
        return self.read('eai:acl', 'eai:attributes')

    def update(self, **kwargs):
        response = self.service.post(self.path, **kwargs)
        check_status(response, 200)
        return self

# UNDONE: Index should not have a delete method (currently inherited)
class Index(Entity):
    def __init__(self, service, name):
        Entity.__init__(self, service, PATH_INDEX % name)
        self.name = name
        self.roll_hot_buckets = lambda: self.invoke("roll-hot-buckets")

    def clean(self):
        """Delete the contents of the index."""
        saved = self.read('maxTotalDataSizeMB', 'frozenTimePeriodInSecs')
        self.update(maxTotalDataSizeMB=1, frozenTimePeriodInSecs=1)
        self.roll_hot_buckets()
        while True: # Wait until event count goes to zero
            sleep(1)
            if self['totalEventCount'] == '0': break
        self.update(**saved)

class Indexes(Collection):
    def __init__(self, service):
        Collection.__init__(self, service, PATH_INDEXES)

    def __getitem__(self, key):
        return Index(self.service, key)

    def __iter__(self):
        names = self.list()
        for name in names: yield Index(self.service, name)

    def contains(self, name):
        """Answers if an index with the given name exists."""
        return name in self.list()

    def create(self, name, **kwargs):
        response = self.post(name=name, **kwargs)
        check_status(response, 201)
        return Index(self.service, name)

    def list(self):
        """Returns a list of index names."""
        response = self.get(count=-1)
        check_status(response, 200)
        entry = load(response).entry
        if not isinstance(entry, list): entry = [entry] # UNDONE
        return [item.title for item in entry]

