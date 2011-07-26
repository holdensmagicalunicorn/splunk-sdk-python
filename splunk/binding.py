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

# UNDONE: HTTP POST does not support file upload
# UNDONE: Validate Context.get|post|delete path args are paths and not urls
# UNDONE: self.namespace should default to actual string and not None

"""Low-level 'binding' interface to the Splunk REST API."""

from pprint import pprint # debug

import socket
import ssl

# UNDONE: Can we retrieve the sessionKey without instantiating this? regex?
from xml.etree.ElementTree import XML

from splunk.data import record

__all__ = [
    "connect",
    "Context",
    "HTTPError",
]

DEFAULT_HOST = "localhost"
DEFAULT_PORT = "8089"
DEFAULT_SCHEME = "https"

# kwargs: scheme, host, port
def prefix(**kwargs):
    """Generate the 3-tuple prefix."""
    scheme = kwargs.get("scheme", DEFAULT_SCHEME)
    host = kwargs.get("host", DEFAULT_HOST)
    port = kwargs.get("port", DEFAULT_PORT)
    return "%s://%s:%s" % (scheme, host, port)

class Context:
    # kwargs: scheme, host, port, username, password, namespace
    def __init__(self, http = None, **kwargs):
        # We use the default HTTP implementation unless we are 
        # explicitly passed in a new one
        self.http = Http(**kwargs) if http is None else http

        self.token = None
        self.prefix = prefix(**kwargs)
        self.scheme = kwargs.get("scheme", DEFAULT_SCHEME)
        self.host = kwargs.get("host", DEFAULT_HOST)
        self.port = kwargs.get("port", DEFAULT_PORT)
        self.username = kwargs.get("username", "")
        self.password = kwargs.get("password", "")
        self.namespace = kwargs.get("namespace", None)

    # Shared per-context request headers
    def _headers(self):
        return [("Authorization", self.token)]

    def bind(self, path, method = "get"):
        """Returns a lambda that 'captures' the current context and the
           given path and method and that can be used to simplify subsequent
           requests using the context, path & method."""
        func = {
            'get': self.get,
            'delete': self.delete,
            'post': self.post 
        }.get(method.lower(), None) 
        if func is None: 
            raise ValueError, "Unknown method '%s'" % method
        path = self.fullpath(path)
        if path.find('{') == -1:
            return lambda **kwargs: func(path, **kwargs)
        # UNDONE: Need some better error checking on the path format string,
        # eg: check that all replacements are positional and that the number 
        # of given args matches the number of expected replacements.
        return lambda *args, **kwargs: func(path.format(*args), **kwargs)

    def connect(self):
        """Open a connection (socket) to the service (host:port)."""
        cn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cn.connect((self.host, int(self.port)))
        return ssl.wrap_socket(cn) if self.scheme == "https" else cn

    def delete(self, path, **kwargs):
        """Issue a DELETE request to the given path."""
        return self.http.delete(self.url(path), self._headers(), **kwargs)

    def get(self, path, **kwargs):
        """Issue a GET request to the given path."""
        return self.http.get(self.url(path), self._headers(), **kwargs)

    def post(self, path, **kwargs):
        """Issue a POST request to the given path."""
        return self.http.post(self.url(path), self._headers(), **kwargs)

    def request(self, path, message):
        """Issue the given HTTP request message to the given endpoint."""
        return self.http.request(
            self.url(path), {
                'method': message.get("method", "GET"),
                'headers': message.get("headers", []) + self._headers(),
                'body': message.get("body", "")})

    def login(self):
        """Issue a Splunk login request using the context's credentials and
           store the session token for use on subsequent requests."""
        response = self.http.post(
            self.url("/services/auth/login"),
            username=self.username, 
            password=self.password)
        body = response.body.read()
        session = XML(body).findtext("./sessionKey")
        self.token = "Splunk %s" % session
        return self

    def logout(self):
        """Forget the current session token."""
        self.token = None
        return self

    def fullpath(self, path):
        """If the given path is a fragment, qualify with segments corresponding
           to the binding context's namespace."""
        if path.startswith('/'): 
            return path
        if self.namespace is None: 
            return "/services/%s" % path
        username, appname = self.namespace.split(':')
        if username == "*": 
            username = '-'
        if appname == "*": 
            appname = '-'
        return "/servicesNS/%s/%s/%s" % (username, appname, path)

    # Convet the given path into a fully qualified URL by first qualifying
    # the given path with namespace segments if necessarry and then prefixing
    # with the scheme, host and port.
    def url(self, path):
        """Fully qualified URL generation."""
        return self.prefix + self.fullpath(path)

# kwargs: scheme, host, port, username, password, namespace
def connect(**kwargs):
    """Establishes an authenticated context with the given host."""
    return Context(**kwargs).login() 

#
# The HTTP interface used by the Splunk binding layer abstracts the unerlying
# HTTP library using request & response 'messages' which are implemented as
# dictionaries with the following structure:
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

# UNDONE: http.post does not support: file upload, 'raw' body data, streaming,
# multipart/form-data, query args

import splunk.ehttplib as httplib
import urllib

debug = False

def _print_request(method, url, head, body):
    print "** %s %s" % (method, url)
    pprint(head)
    print body

def _print_response(response):
    print "=> %d %s" % (response.status, response.reason)
    pprint(response.headers)
    # UNDONE: Dont consume the body here .. figure out a better way to show
    # contents without consuming body or reading an arbitrary response stream.
    # print response.body

# Crack the givne url into (scheme, host, port, path)
def spliturl(url):
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
    for key, value in kwargs.iteritems():
        if isinstance(value, list):
            items.extend([(key, item) for item in value])
        else:
            items.append((key, value))
    return urllib.urlencode(items)

# Base HTTP class implementation, containing the vast majority of the logic.
# Base classes merely need to implement the request(...) method, and pass the
# appropriate parameters to _build_response, which will construct an 
# SDK-compliant response object.
class HttpBase(object):    
    def __init__(self, **kwargs):
        # Extract timeout information
        self.timeout = kwargs.get("timeout", None)

        # Extract ssl certs information
        self.key_file = kwargs.get("key_file", None)
        self.cert_file = kwargs.get("cert_file", None)
        self.ca_file = kwargs.get("ca_file", None)

        # Extract proxy information
        if kwargs.get("proxyhost", None) == None:
            self.proxy = None
        else:
            self.proxy = (kwargs.get("proxyhost", None),
                          kwargs.get("proxyport", str(DEFAULT_PORT)))

    def _add_info(self, **kwargs):
        # if already present, use it, otherwise, if self
        # contains a non-None setting, add it in
        if not kwargs.has_key('proxy'):
            if self.proxy:
                kwargs['proxy'] = self.proxy
        if not kwargs.has_key('timeout'):
            if self.timeout:
                kwargs['timeout'] = int(self.timeout)
        if not kwargs.has_key('key_file'):
            if self.key_file:
                kwargs['key_file'] = self.key_file
        if not kwargs.has_key('cert_file'):
            if self.cert_file:
                kwargs['cert_file'] = self.cert_file
        if not kwargs.has_key('ca_file'):
            if self.ca_file:
                kwargs['ca_file'] = self.ca_file

        return kwargs

    def connect(self, scheme, host, port, **kwargs):
        # Add ssl/timeout/proxy information
        kwargs = self._add_info(**kwargs)

        # Connect using the appropriate connection
        if scheme == "http":
            return httplib.HTTPConnection(host, port, **kwargs)
        elif scheme == "https":
            return httplib.HTTPSConnection(host, port, **kwargs)

        return None

    def delete(self, url, headers = None, **kwargs):
        if headers is None: 
            headers = []
        if kwargs: 
            url = url + '?' + encode(**kwargs)
        message = {
            'method': "DELETE",
            'headers': headers,
        }
        return self.request(url, message)

    def get(self, url, headers = None, **kwargs):
        if headers is None: 
            headers = []
        if kwargs: 
            url = url + '?' + encode(**kwargs)
        return self.request(url, { "headers": headers })

    def post(self, url, headers = None, **kwargs):
        if headers is None: 
            headers = []
        headers.append(("Content-Type", "application/x-www-form-urlencoded")),
        message = {
            "method": "POST",
            "headers": headers,
            "body": encode(**kwargs)
        }
        return self.request(url, message)

    def request(self, url, message, *args, **kwargs):
        raise Exception("'request' must be overridden")
        return

    @staticmethod
    def build_response(status, reason, headers, body):
        response = record({
            "status": status, 
            "reason": reason,
            "headers": headers,
            "body": ResponseReader(body),
        })

        # Before we return the response, we first make sure 
        # that it is valid
        if 400 <= response.status:
            raise HTTPError(response) 

        return response

# The actual implementation of an HTTP class using
# httplib. This class supports proxies, certificate files,
# and socket timeouts.
class Http(HttpBase):
    def request(self, url, message, **kwargs):
        # Add ssl/timeout/proxy information
        kwargs = self._add_info(**kwargs)
        timeout = kwargs.get('timeout', None)

        scheme, host, port, path = spliturl(url)
        body = message.get("body", "")
        head = { 
            "Content-Length": str(len(body)),
            "Host": host,
            "User-Agent": "http.py/1.0",
            "Accept": "*/*",
        } # defaults

        for key, value in message["headers"]: 
            head[key] = value

        method = message.get("method", "GET")

        if debug: _print_request(method, url, head, body)

        connection = self.connect(scheme, host, port, timeout = timeout)

        try:
            connection.request(method, path, body, head)
            if timeout is not None: 
                connection.sock.settimeout(timeout)
            response = connection.getresponse()
        finally:
            connection.close()

        response = HttpBase.build_response(
            response.status, 
            response.reason,
            response.getheaders(),
            response)

        if debug: _print_response(response)

        return response

# UNDONE: Complete implementation of file-like object, eg: __iter__
class ResponseReader:
    def __init__(self, response):
        self._response = response

    def __str__(self):
        return self.read()

    def read(self, size = None):
        return self._response.read(size)

# Note: the error response schema supports multiple messages but we only
# return the first, although we do return the body so that an exception 
# handler that wants to read multiple messages can do so.
def read_error_message(response):
    body = response.body.read()
    return body, XML(body).findtext("./messages/msg")

class HTTPError(Exception):
    def __init__(self, response):
        status = response.status
        reason = response.reason
        body, detail = read_error_message(response)
        message = "HTTP %d %s%s" % (
            status, reason, "" if detail is None else " -- %s" % detail)
        Exception.__init__(self, message) 
        self.status = status
        self.reason = reason
        self.headers = response.headers
        self.body = body
