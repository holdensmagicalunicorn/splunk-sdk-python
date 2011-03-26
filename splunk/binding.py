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

# UNDONE: Figure out how to support methods on collection items

"""Low-level bindings to the Splunk REST API."""

from xml.etree.ElementTree import XML

import splunk.http as http
from splunk.util import record
from splunk.wire import default

__all__ = [
    "login",
    "connect",
]

# UNDONE: Parameterize scheme?
def mkurl(host, path):
    # Append default port to host if port is not already provided
    if not ':' in host: host = host + ':' + default.port
    return "%s://%s%s" % (default.scheme, host, path)

class Context:
    def __init__(self, host, username, password, namespace = None):
        self.host = host
        self.username = username
        self.password = password
        self.namespace = namespace
        self.token = None

    # Shared per-context request headers
    def _headers(self):
        return [("Authorization", self.token)]

    def bind(self, path, method = "GET"):
        fn = {
            'get': self.get,
            'delete': self.delete,
            'post': self.post }.get(method.lower(), None) 
        if fn is None: raise ValueError, "Unknown method '%s'" % method
        path = self.fullpath(path)
        return lambda **kwargs: fn(path, **kwargs)

    def delete(self, path, **kwargs):
        return http.delete(self.url(path), self._headers(), **kwargs)

    def get(self, path, **kwargs):
        return http.get(self.url(path), self._headers(), **kwargs)

    def post(self, path, **kwargs):
        return http.post(self.url(path), self._headers(), **kwargs)

    def login(self):
        response = login(self.host, self.username, self.password)
        if response.status >= 400:
            raise HTTPError(response.status, response.reason)
        # assert response.status == 200
        sessionKey = XML(response.body).findtext("./sessionKey")
        self.token = "Splunk %s" % sessionKey
        return self

    def fullpath(self, path):
        """If the given path is a fragment, qualify with a prefix corresponding
           to the binding context's namespace."""
        if path.startswith('/'): return path
        if self.namespace is None: return "/services/%s" % path
        username, appname = self.namespace.split(':')
        if username == "*": username = '-'
        if appname == "*": appname = '-'
        return "/servicesNS/%s/%s/%s" % (username, appname, path)

    # Convet the given path into a fully qualified URL. If the path is
    # relative, first convert into a full path by adding namespace segments
    # if the context is namespace qualified, and then prefix with host, port
    # and scheme.
    def url(self, path):
        return mkurl(self.host, self.fullpath(path))

def connect(host, username, password):
    """Establishes an authenticated context with the given host."""
    return Context(host, username, password).login() 

def login(host, username, password):
    """Issues a 'raw' login request and returns response message."""
    url = mkurl(host, "/services/auth/login")
    return http.post(url, username=username, password=password)

class Endpoint:
    """Defines an endpoint by affiliating a resource kind with a path and 
       provides a binder that instantiates a resource protocol for interacting
       with the endpoint."""
    def __init__(self, path, kind, *args):
        self.bind = lambda cx: kind(path, cx, *args)

    def __call__(self, cx):
        return self.bind(cx)

class Resource: 
    """An abstract resource protocol."""
    pass

class Collection(Resource):
    """Implements the protocol for interacting with a collection resource."""
    def __init__(self, path, cx, verbs = ["get", "item", "create", "delete"]):
        itempath = "%s/%%s" % path
        if "get" in verbs:
            self.get = lambda **kwargs: cx.get(path, **kwargs)
        if "item" in verbs:
            self.item = lambda key, **kwargs: cx.get(itempath % key, **kwargs)
        if "create" in verbs:
            self.create = lambda **kwargs: cx.post(path, **kwargs)
        if "delete" in verbs:
            self.delete = lambda key, **kwargs: cx.delete(itempath % key)

#
# Endpoints
#

# alerts

# create: ['name']
apps = Endpoint("apps/local", Collection)

# apps/appinstall
# apps/apptemplates

# authentication/auth-tokens
# authentication/changepassword
# authentication/current-context
# authentication/httpauth-tokens
# authentication/providers
# authentication/providers/{name}
# authorization/checkCapability

commands = Endpoint("data/commands", Collection)

# UNDONE: create => 404 .. figure out why?
capabilities = Endpoint(
    "authorization/capabilities", Collection, ["get", "create", "delete"])

# configs

# deployment/...

# create: ['name', 'search']
eventtypes = Endpoint("saved/eventtypes", Collection)

# NOTE: No delete!
indexes = Endpoint("data/indexes", Collection, ["get", "item", "create"])

# data/inputs

# data/props/extractions[/{name}]?
# data/props/fieldaliases
# data/props/lookups
# data/props/sourcetype-rename
# data/transforms/extractions[/{name}]?
# data/transforms/lookups[/{name}]?

# licenser/groups[/{name}]?
# licenser/licenses[/{hash}]?
# licenser/localslave
# licenser/localslave/license
# licenser/messages
# licenser/pools[/{name}]?
# licenser/slaves[/{guid}]?
# licenser/stacks[/{name}]?
# masterlm

# data/outputs..

# messages

objects = Endpoint("/services/admin/directory", Collection, ["get", "item"])

# properties[/{file_name}[/{stanza_name}[/{key_name}]?]?]?

# receivers/simple
# receivers/stream

roles = Endpoint("authorization/roles", Collection)

# saved/searches/{name}
# saved/searches/{name}/acknowledge
# saved/searches/{name}/dispatch
# saved/searches/{name}/history
# saved/searches/{name}/scheduled_times
# saved/searches/{name}/suppress

# scheduled
# scheduled/views

# search/distributed
# search/distributed/config
# search/distributed/config/distributedSearch
# search/distributed/peers

# search/fields
# search/fields/{name}
# search/fields/{name}/tags

# search/jobs/export

# search/jobs
# search/jobs/{sid}
# search/jobs/{sid}/control
# search/jobs/{sid}/events
# search/jobs/{sid}/results
# search/jobs/{sid}/results_preview
# search/jobs/{sid}/search.log
# search/jobs/{sid}/summary
# search/jobs/{sid}/timeline

# search/parser

# search/tags[/{name}]?

# search/timeparser

# search/typeahead

# server
# server/control
# server/control/restart

# server/info
# server/logger
# server/settings

users = Endpoint("authentication/users", Collection)

