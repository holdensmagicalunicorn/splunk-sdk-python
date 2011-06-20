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
#   * jobs
#
#   * export
#   * parse
#
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
    "connect",
    "Service"
]

# XML Namespaces
# "http://www.w3.org/2005/Atom",
# "http://dev.splunk.com/ns/rest",
# "http://a9.com/-/spec/opensearch/1.1",

PATH_INDEX = "data/indexes/%s"
PATH_INDEXES = "data/indexes"

PATH_JOB = "search/jobs/%s"
PATH_JOBS = "search/jobs"

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

# kwargs: scheme, host, port, username, password, namespace
def connect(**kwargs):
    """Establishes an authenticated connection to the specified service."""
    return Service(**kwargs).login()

# Response utilities
def load(response):
    return data.load(response.body.read())

class Service(Context):
    def __init__(self, **kwargs):
        Context.__init__(self, **kwargs)

    @property
    def indexes(self):
        return Indexes(self)

    @property
    def info(self):
        response = self.get("server/info")
        check_status(response, 200)
        return _filter_content(load(response).entry.content)

    @property
    def jobs(self):
        return Jobs(self)

    @property
    def settings(self):
        return Entity(self, "server/settings")

class Endpoint:
    def __init__(self, service, path):
        self.service = service
        self.path = path

    def get(self, relpath="", **kwargs):
        response = self.service.get("%s/%s" % (self.path, relpath), **kwargs)
        check_status(response, 200)
        return response

    def post(self, relpath="", **kwargs):
        response = self.service.post("%s/%s" % (self.path, relpath), **kwargs)
        check_status(response, 200, 201)
        return response

# UNDONE: Common create & delete options?
class Collection(Endpoint):
    def __init__(self, service, path):
        Endpoint.__init__(self, service, path)

    def __getitem__(self, key):
        pass # Abstract

    def itemmeta(self):
        """Returns collection item metadata."""
        response = self.get("/_new")
        content = load(response).entry.content
        return record({
            'eai:acl': content['eai:acl'],
            'eai:attributes': content['eai:attributes']
        })

    def list(self): # UNDONE: keys?
        pass # Abstract

def _filter_content(content, *args):
    if len(args) > 0: # We have filter args
        result = record({})
        for key in args: result[key] = content[key]
    else:
        # Eliminate some noise by default
        result = content
        if result.has_key('eai:acl'):
            del result['eai:acl']
        if result.has_key('eai:attributes'):
            del result['eai:attributes']
        if result.has_key('type'):
            del result['type']
    return result

class Entity(Endpoint):
    """Abstract base class that implements the Splunk 'entity' protocol."""

    def __init__(self, service, path):
        Endpoint.__init__(self, service, path)
        # UNDONE: The following should be derived by reading entity links
        self.delete = lambda: self.service.delete(self.path)
        self.disable = lambda: self.post("disable")
        self.enable = lambda: self.post("enable")
        self.reload = lambda: self.post("_reload")

    def __getitem__(self, key):
        return self.read()[key]

    def __setitem__(self, key, value):
        self.update(key=value)

    def read(self, *args):
        """Read and return the current entity value, optionally returning
           only the requested fields, if specified."""
        response = self.get()
        content = load(response).entry.content
        return _filter_content(content, *args)

    def readmeta(self):
        """Return the entity's metadata."""
        return self.read('eai:acl', 'eai:attributes')

    def update(self, **kwargs):
        self.post(**kwargs)
        return self

# UNDONE: Index should not have a delete method (currently inherited)
class Index(Entity):
    def __init__(self, service, name):
        Entity.__init__(self, service, PATH_INDEX % name)
        self.name = name
        self.roll_hot_buckets = lambda: self.post("roll-hot-buckets")

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

    def __getitem__(self, name):
        return Index(self.service, name)

    def __iter__(self):
        names = self.list()
        for name in names: yield Index(self.service, name)

    def contains(self, name):
        """Answers if an index with the given name exists."""
        return name in self.list()

    def create(self, name, **kwargs):
        response = self.post(name=name, **kwargs)
        return Index(self.service, name)

    def list(self):
        """Returns a list of index names."""
        response = self.get(count=-1)
        entry = load(response).entry
        if not isinstance(entry, list): entry = [entry] # UNDONE
        return [item.title for item in entry]

# The Splunk Job is not an enity, but we are able to make the interface look
# a lot like one.
class Job(Endpoint): 
    def __init__(self, service, sid):
        Endpoint.__init__(self, service, PATH_JOB % sid)
        self.sid = sid

    def __getitem__(self, key):
        return self.read()[key]

    def __setitem__(self, key, value):
        self.update(key=value)

    def cancel(self):
        self.post("control", action="cancel")
        return self

    def disable_preview(self):
        self.post("control", action="disablepreview")
        return self

    def events(self, **kwargs):
        return self.get("events", **kwargs).body

    def enable_preview(self):
        self.post("control", action="enablepreview")
        return self

    def finalize(self):
        self.post("control", action="finalize")
        return self

    def pause(self):
        self.post("control", action="pause")
        return self

    def preview(self, **kwargs):
        return self.get("results_preview", **kwargs).body

    def read(self, *args):
        """Read and return the jobs entity value."""
        response = self.get()
        content = load(response).content
        return _filter_content(content, *args)

    def results(self, **kwargs):
        return self.get("results", **kwargs).body

    def searchlog(self, **kwargs):
        return self.get("search.log", **kwargs).body

    def setpriority(self, value):
        self.post('control', action="setpriority", priority=value)
        return self

    def summary(self, **kwargs):
        return self.get("summary", **kwargs).body

    def timeline(self, **kwargs):
        return self.get("timeline", **kwargs).body

    def touch(self,):
        self.post("control", action="touch")
        return self

    def setttl(self, value):
        self.post("control", action="setttl", ttl=value)

    def unpause(self):
        self.post("control", action="unpause")
        return self

class Jobs(Collection):
    def __init__(self, service):
        Collection.__init__(self, service, PATH_JOBS)

    def __getitem__(self, sid):
        return Job(self.service, sid)

    def __iter__(self):
        sids = self.list()
        for sid in sids: yield Job(self.service, sid)

    def contains(self, sid):
        return sid in self.list()

    def create(self, query, **kwargs):
        response = self.post(search=query, **kwargs)
        sid = load(response).sid
        return Job(self.service, sid)

    def list(self):
        response = self.get()
        entry = load(response).entry
        if not isinstance(entry, list): entry = [entry] # UNDONE
        return [item.content.sid for item in entry]
    
class SplunkError(Exception): 
    pass

