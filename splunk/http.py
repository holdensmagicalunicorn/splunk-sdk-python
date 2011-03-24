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

"""A simple http client library."""

import httplib
import urllib

from util import record

#
# // HTTP request message
# request {
#     method? : str = "GET",
#     headers? : [(str,str)*],
#     body? : str,
# }
#
# // HTTP response message
# response {
#     status : int,
#     reason : str,
#     headers : [(str,str)*],
#     body : str|file,
# }
#

debug = False # UNDONE

def _connect(scheme, host, port, timeout = None):
    kwargs = {}
    if timeout is not None: kwargs["timeout"] = timeout
    if scheme == "http":
        return httplib.HTTPConnection(host, port, None, **kwargs)
    if scheme == "https":
        return httplib.HTTPSConnection(host, port, None, **kwargs)
    return None # UNDONE: Raise an invalid scheme exception

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

# Split the given url into (scheme, host, port, path)
def _spliturl(url):
    scheme, part = url.split(':', 1)
    host, path = urllib.splithost(part)
    host, port = urllib.splitnport(host, 80)
    return scheme, host, port, path

def delete(url, headers = [], timeout = None, **kwargs):
    if kwargs: url = url + '?' + urllib.urlencode(kwargs)
    message = {
        'method': "DELETE",
        'headers': headers,
    }
    return request(url, message, timeout)

def get(url, headers = [], timeout = None, **kwargs):
    if kwargs: url = url + '?' + urllib.urlencode(kwargs)
    return request(url, { "headers": headers }, timeout)

# UNDONE: The following doesn't support file upload
def post(url, headers = [], timeout = None, **kwargs):
    headers.append(("Content-Type", "application/x-www-form-urlencoded")),
    message = {
        "method": "POST",
        "headers": headers,
        "body": urllib.urlencode(kwargs)
    }
    return request(url, message, timeout)

def put(url, **kwargs):
    pass # UNDONE

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
    connection = _connect(scheme, host, port, timeout)
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
        "body": response.read() 
    })
    if debug: _print_response(response)
    return response

