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

# UNDONE: Support for _new endpoints (metadata)
# UNDONE: Validate Context.get|post|delete path args are paths and not urls
# UNDONE: HTTP POST does not support file upload
# UNDONE: self.namespace should default to actual string and not None

"""Low-level bindings to the Splunk REST API."""

# UNDONE: Can we retrieve the sessionKey without instantiating this? regex?
from xml.etree.ElementTree import XML

__all__ = [
    "Collection",
    "connect",
    "Context",
    "Entity",
    "HTTPError",
    "login",
]

DEFAULT_HOST = "localhost"
DEFAULT_PORT = "8089"
DEFAULT_SCHEME = "https"

# kwargs: scheme, host, port
def prefix(**kwargs):
    scheme = kwargs.get("scheme", DEFAULT_SCHEME)
    host = kwargs.get("host", DEFAULT_HOST)
    port = kwargs.get("port", DEFAULT_PORT)
    return "%s://%s:%s" % (scheme, host, port)

class Context:
    # kwargs: scheme, host, port, username, password, namespace
    def __init__(self, **kwargs):
        self.scheme = kwargs.get("scheme", DEFAULT_SCHEME)
        self.host = kwargs.get("host", DEFAULT_HOST)
        self.port = kwargs.get("port", DEFAULT_PORT)
        self.username = kwargs.get("username", "")
        self.password = kwargs.get("password", "")
        self.namespace = kwargs.get("namespace", None)
        self.prefix = prefix(**kwargs)
        self.token = None

    # Shared per-context request headers
    def _headers(self):
        return [("Authorization", self.token)]

    def bind(self, path, method = "get"):
        fn = {
            'get': self.get,
            'delete': self.delete,
            'post': self.post 
        }.get(method.lower(), None) 
        if fn is None: raise ValueError, "Unknown method '%s'" % method
        path = self.fullpath(path)
        if path.find('{') == -1:
            return lambda **kwargs: fn(path, **kwargs)
        # UNDONE: Need some better error checking on the path format string,
        # eg: check that all replacements are positional and that the number 
        # of given args matches the number of expected replacements.
        return lambda *args, **kwargs: fn(path.format(*args), **kwargs)

    def delete(self, path, **kwargs):
        return http.delete(self.url(path), self._headers(), **kwargs)

    def get(self, path, **kwargs):
        return http.get(self.url(path), self._headers(), **kwargs)

    def post(self, path, **kwargs):
        return http.post(self.url(path), self._headers(), **kwargs)

    def request(self, path, message):
        return http.request(
            self.url(path), {
                'method': message.get("method", "GET"),
                'headers': message.get("headers", []) + self._headers(),
                'body': message.get("body", "")})

    def login(self):
        response = http.post(
            self.url("/services/auth/login"),
            username=self.username, 
            password=self.password)
        if response.status >= 400:
            raise HTTPError(response.status, response.reason)
        # assert response.status == 200
        body = response.body.read()
        sessionKey = XML(body).findtext("./sessionKey")
        self.token = "Splunk %s" % sessionKey
        return self

    def fullpath(self, path):
        """If the given path is a fragment, qualify with segments corresponding
           to the binding context's namespace."""
        if path.startswith('/'): return path
        if self.namespace is None: return "/services/%s" % path
        username, appname = self.namespace.split(':')
        if username == "*": username = '-'
        if appname == "*": appname = '-'
        return "/servicesNS/%s/%s/%s" % (username, appname, path)

    # Convet the given path into a fully qualified URL by first qualifying
    # the given path with namespace segments if necessarry and then prefixing
    # with the scheme, host and port.
    def url(self, path):
        return self.prefix + self.fullpath(path)

# kwargs: scheme, host, port, username, password, namespace
def connect(**kwargs):
    """Establishes an authenticated context with the given host."""
    return Context(**kwargs).login() 

# kwargs: scheme, host, port, username, password
def login(**kwargs):
    """Issues a login request and returns the response message."""
    return http.post(
        prefix(**kwargs) + "/services/auth/login",
        username=kwargs.get("username", ""),
        password=kwargs.get("password", ""))

class Entity:
    """Implements the protocol for interacting with 'entity' resources."""
    def __init__(self, context, path, verbs = "get,update"):
        if "get" in verbs:
            self.get = context.bind(path, "get")
        if "udapte" in verbs:
            self.get = context.bind(path, "post")

    def __call__(self, *args, **kwargs):
        return self.get(*args, **kwargs)

class Collection:
    """Implements the protocol for interacting with a collection resource."""
    def __init__(self, context, path, verbs = "get,item,create,delete"):
        verbs = verbs.split(',')
        itempath = "%s/{0}" % path
        if "get" in verbs:
            self.get = context.bind(path, "get")
        if "item" in verbs:
            self.item = context.bind(itempath, "get")
        if "create" in verbs:
            self.create = context.bind(path, "post")
        if "delete" in verbs:
            self.delete = context.bind(itempath, "delete")

    def __call__(self, *args, **kwargs):
        return self.get(*args, **kwargs)

#
# The HTTP interface below, used by the Splunk binding layer, abstracts the 
# unerlying HTTP library using request & response 'messages' which are dicts
# with the following structure:
#
#   # HTTP request message (all keys optional)
#   request {
#       method? : str = "GET",
#       headers? : [(str, str)*],
#       body? : str,
#   }
#
#   # HTTP response message (all keys present)
#   response {
#       status : int,
#       reason : str,
#       headers : [(str, str)*],
#       body : file,
#   }
#

# UNDONE: Make sure timeout arg works!
# UNDONE: Consider moving timeout arg into kwargs
# UNDONE: Make body a file instead of str

import httplib
import urllib

from util import record

debug = False # UNDONE

def _print_request(method, url, head, body):
    from pprint import pprint # UNDONE
    print "** %s %s" % (method, url)
    pprint(head)
    print body

def _print_response(response):
    from pprint import pprint # UNDONE
    print "=> %d %s" % (response.status, response.reason)
    pprint(response.headers)
    print response.body

def _spliturl(url):
    """Split the given url into (scheme, host, port, path)."""
    scheme, part = url.split(':', 1)
    host, path = urllib.splithost(part)
    host, port = urllib.splitnport(host, 80)
    return scheme, host, port, path

# Encode the given kwargs as a query string. This wrapper will also encode 
# a list value as a sequence of assignemnts to the corresponding arg name, 
# for example an argument such as 'foo=[1,2,3]' will be encoded as
# 'foo=1&foo=2&foo=3'. 
def encode(**kwargs):
    items = []
    for k, v in kwargs.iteritems():
        if isinstance(v, list):
            items.extend([(k, item) for item in v])
        else:
            items.append((k, v))
    return urllib.urlencode(items)

class http:
    """HTTP interface used by the Splunk binding layer."""

    @staticmethod
    def connect(scheme, host, port, timeout = None):
        """Returns an HTTP connection object corresponding to the given scheme,
           host and port."""
        kwargs = {}
        if timeout is not None: kwargs["timeout"] = timeout
        if scheme == "http":
            return httplib.HTTPConnection(host, port, None, **kwargs)
        if scheme == "https":
            return httplib.HTTPSConnection(host, port, None, **kwargs)
        return None # UNDONE: Raise an invalid scheme exception

    @staticmethod
    def delete(url, headers = [], timeout = None, **kwargs):
        if kwargs: url = url + '?' + encode(**kwargs)
        message = {
            'method': "DELETE",
            'headers': headers,
        }
        return http.request(url, message, timeout)

    @staticmethod
    def get(url, headers = [], timeout = None, **kwargs):
        if kwargs: url = url + '?' + encode(**kwargs)
        return http.request(url, { "headers": headers }, timeout)

    @staticmethod
    def post(url, headers = [], timeout = None, **kwargs):
        # UNDONE: The following doesn't support file upload
        headers.append(("Content-Type", "application/x-www-form-urlencoded")),
        message = {
            "method": "POST",
            "headers": headers,
            "body": encode(**kwargs)
        }
        return http.request(url, message, timeout)

    @staticmethod
    def request(url, message, timeout = None):
        scheme, host, port, path = _spliturl(url)
        body = message.get("body", "")
        head = { 
            "Content-Length": len(body),
            "Host": host,
            "User-Agent": "http.py/1.0",
            "Accept": "*/*",
        } # defaults
        for k, v in message["headers"]: head[k] = v
        method = message.get("method", "GET")
        if debug: _print_request(method, url, head, body)
        connection = http.connect(scheme, host, port, timeout)
        try:
            connection.request(method, path, body, head)
            if timeout is not None: connection.sock.settimeout(timeout)
            response = connection.getresponse()
        finally:
            connection.close()
        response = record({
            "status": response.status,
            "reason": response.reason,
            "headers": response.getheaders(),
            "body": ResponseReader(response),
        })
        if debug: _print_response(response)
        return response

# UNDONE: Complete implementation of file-like object
class ResponseReader:
    def __init__(self, response):
        self._response = response

    def __str__(self):
        return self.read()

    def read(self, size = None):
        return self._response.read(size)

class HTTPError(Exception):
    def __init__(self, status, reason):
        Exception.__init__(self, "HTTP %d %s" % (status, reason)) 
        self.reason = reason
        self.status = status
