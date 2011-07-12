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
# UNDONE: CONSIDER: __del__ on Context
# UNDONE: CONSIDER: __enter__/__exit__ on Context

"""Low-level bindings to the Splunk REST API."""

from pprint import pprint # debug

import socket
import ssl

# UNDONE: Can we retrieve the sessionKey without instantiating this? regex?
from xml.etree.ElementTree import XML

from splunk.data import record
import splunk.data as data

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
    """Context Class."""
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
        """Define splunk binding, and access methods."""
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
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect((self.host, int(self.port)))
        #return socket.ssl(cn) if self.scheme == "https" else cn
        return ssl.wrap_socket(conn) if self.scheme == "https" else conn

    def delete(self, path, **kwargs):
        """Context layer delete endpoint access."""
        return self.http.delete(self.url(path), self._headers(), **kwargs)

    def get(self, path, **kwargs):
        """Context layer get endpoint access."""
        return self.http.get(self.url(path), self._headers(), **kwargs)

    def post(self, path, **kwargs):
        """Context layer post endpoint access."""
        return self.http.post(self.url(path), self._headers(), **kwargs)

    def request(self, path, message):
        """Context layer common request method."""
        return self.http.request(
            self.url(path), {
                'method': message.get("method", "GET"),
                'headers': message.get("headers", []) + self._headers(),
                'body': message.get("body", "")})

    def login(self):
        """Context layer login."""
        response = self.http.post(
            self.url("/services/auth/login"),
            username=self.username, 
            password=self.password)
        if response.status >= 400:
            raise HTTPError(response)
        # assert response.status == 200
        body = response.body.read()
        session = XML(body).findtext("./sessionKey")
        self.token = "Splunk %s" % session
        return self

    def logout(self):
        """Context layer logout."""
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
# UNDONE: http.post does not support: file upload, 'raw' body data, streaming,
#   multipart/form-data, query args

import splunk.ehttplib as httplib
import urllib

DEBUG = False

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

def _spliturl(url):
    scheme, part = url.split(':', 1)
    host, path = urllib.splithost(part)
    host, port = urllib.splitnport(host, 80)
    return scheme, host, port, path

# Encode the given kwargs as a query string. This wrapper will also encode 
# a list value as a sequence of assignemnts to the corresponding arg name, 
# for example an argument such as 'foo=[1,2,3]' will be encoded as
# 'foo=1&foo=2&foo=3'. 
def encode(**kwargs):
    """Encode variable arguments into HTTP safe strings."""
    items = []
    for key, value in kwargs.iteritems():
        if isinstance(value, list):
            items.extend([(key, item) for item in value])
        else:
            items.append((key, value))
    return urllib.urlencode(items)

# Base HTTP class implementation, containing the vast majority
# of the logic. Base classes merely need to implement
# the request(...) method, and pass the appropriate parameters
# to _build_response, which will construct an SDK-compliant
# response object.
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

    def _build_response(self, status, reason, headers, body):
        return record({
            "status": status, 
            "reason": reason,
            "headers": headers,
            "body": ResponseReader(body),
        })

# The actual implementation of an HTTP class using
# httplib. This class supports proxies, certificate files,
# and socket timeouts.
class Http(HttpBase):
    def request(self, url, message, **kwargs):
        # Add ssl/timeout/proxy information
        kwargs = self._add_info(**kwargs)
        timeout = kwargs['timeout'] if kwargs.has_key('timeout') else None

        scheme, host, port, path = _spliturl(url)
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

        if DEBUG: 
            _print_request(method, url, head, body)
        connection = self.connect(scheme, host, port, timeout = timeout)

        try:
            connection.request(method, path, body, head)
            if timeout is not None: 
                connection.sock.settimeout(timeout)
            response = connection.getresponse()
        finally:
            connection.close()

        response = self._build_response(
            response.status, 
            response.reason,
            response.getheaders(),
            response)

        if DEBUG: 
            _print_response(response)

        return response

# UNDONE: Complete implementation of file-like object
class ResponseReader:
    """Read response."""
    def __init__(self, response):
        self._response = response

    def __str__(self):
        return self.read()

    def read(self, size = None):
        """Response reader."""
        return self._response.read(size)

def extract_error_message(response):
        error = data.load(response.body.read())
        error_msg = ""
        if error.has_key("response"):
            if error["response"].has_key("messages"):
                messages = error["response"]["messages"]
                if messages.has_key("msg"):
                    msg = messages["msg"]
                    msg_type = msg["type"]
                    msg_text = msg["$text"]
                    error_msg = "-- %s: %s" % (msg_type, msg_text)

        return (error, error_msg)

class HTTPError(Exception):
    """HTTP Exception generator."""
    def __init__(self, response):
        # Extract the status, reason and error message
        # from the response
        status = response.status
        reason = response.reason
        error, error_msg = extract_error_message(response)

        message = "HTTP %d %s %s" % (status, reason, error_msg)

        Exception.__init__(self, message) 
        self.reason = reason
        self.status = status
        self.error = error

