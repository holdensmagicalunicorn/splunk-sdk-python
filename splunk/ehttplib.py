# ehttplib.py -- extensions for httplib
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
#

#
# this module is an amalgam and adaption of openly availble sources from the 
# internet.
# 
# proxy: httplib2 
# ssl cert: cookbook sample by Marcelo Fernandez
#

"""Extend base python httplib with proxy and SSL certificates."""

import socket
import httplib
import ssl

#from string import split, join

class Connection:
    """Generic TCP connection wrapper."""

    def __init__(self, server):
        self.socket = None
        self.server = server

    def establish(self):
        if self.socket == None:
            sckt = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server = (self.server[0], int(self.server[1]))
            sckt.connect(server)
            self.socket = sckt
        return self.socket

class HttpProxy(Connection):
    """HTTP proxy connection that tunnels using TCP/IP socket."""
    def __init__(self, server, proxy):
        Connection.__init__(self, server)
        self.proxy = proxy

    def establish(self):
        tmp = self.server
        self.server = self.proxy
        try:
            Connection.establish(self)
        finally:
            self.server = tmp

        self.socket.sendall(("CONNECT " +
                             self.server[0] + ":" + 
                             str(self.server[1]) + 
                             " HTTP/1.1\r\n" + 
                             "Host: " + 
                             self.server[0] + 
                             "\r\n\r\n").encode())
        # We read the response until we get the string "\r\n\r\n"
        resp = self.socket.recv(1)
        while resp.find("\r\n\r\n".encode()) == -1:
            resp = resp + self.socket.recv(1)

        # We just need the first line to check if the connection
        # was successful
        statusline = resp.splitlines()[0].split(" ".encode(), 2)
        if statusline[0] not in ("HTTP/1.0".encode(), "HTTP/1.1".encode()):
            self.socket.close()
            self.socket = None

        # return the socket
        return self.socket

class HTTPConnection(httplib.HTTPConnection):
    """Class to make a HTTP connection with support for proxy."""

    def __init__(self, host, port, key_file=None, 
                                   cert_file=None, 
                                   ca_file=None, 
                                   timeout=None,
                                   strict=None,
                                   proxy=None):
        httplib.HTTPConnection.__init__(self, host, port, strict)
        self.proxy = proxy
        self.key_file = key_file
        self.cert_file = cert_file
        self.ca_file = ca_file
        self.timeout = timeout

    def connect(self):
        """Connect using a proxy, or not."""

        # Since this is HTTP (not HTTPS) don't concern ourselves
        # with the cert files, etc. We are only interested in 
        # whether or not we need to use a proxy
        if self.proxy:
            conn = HttpProxy((self.host, self.port), self.proxy)
            conn.establish()
            sock = conn.socket
        else:
            sock = socket.create_connection((self.host, self.port), 
                                            self.timeout)

        self.sock = ssl.wrap_socket(sock, self.key_file, 
                                    self.cert_file, 
                                    cert_reqs=ssl.CERT_NONE)

class HTTPSConnection(httplib.HTTPSConnection):
    """Class to make a HTTPS connection, with support for full 
        client-based SSL Authentication or proxy."""

    def __init__(self, host, port, key_file=None, 
                                   cert_file=None, 
                                   ca_file=None, 
                                   timeout=None,
                                   strict=None,
                                   proxy=None):
        httplib.HTTPSConnection.__init__(self, host, port,
                                         key_file, 
                                         cert_file,
                                         strict)
        self.proxy = proxy
        self.key_file = key_file
        self.cert_file = cert_file
        self.ca_file = ca_file
        self.timeout = timeout

    def connect(self):
        """Connect to a host on a given (SSL) port.
            If ca_file is pointing somewhere, use it to check SSL 
            Certificate."""

        if self.proxy:
            conn = HttpProxy((self.host, self.port), self.proxy)
            conn.establish()
            sock = conn.socket
        else:
            sock = socket.create_connection((self.host, self.port), 
                                            self.timeout)

        # If there's no CA File, don't force Server Certificate Check
        if self.ca_file:
            self.sock = ssl.wrap_socket(sock, self.key_file, 
                                        self.cert_file, 
                                        ca_certs=self.ca_file, 
                                        cert_reqs=ssl.CERT_REQUIRED)
        else:
            self.sock = ssl.wrap_socket(sock, self.key_file, 
                                        self.cert_file, 
                                        cert_reqs=ssl.CERT_NONE)
