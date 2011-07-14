#!/usr/bin/env python
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

import SimpleHTTPServer
import SocketServer
import urllib2
import sys

from socket import SOL_SOCKET, SO_REUSEADDR

PORT = 8080

class RedirectHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def do_GET(self):
        redirect_url, headers = self.get_url_and_headers()

        # Append the GET parameters to the URL
        redirect_url += self.path

        # Make sure we replace any instance of // with /
        redirect_url.replace("//", "/")

        self.make_request(redirect_url, "GET", None, headers)
    
    def do_POST(self):
        redirect_url, headers = self.get_url_and_headers()

        length = int(self.headers.getheader('content-length'))
        data = self.rfile.read(length)

        self.make_request(redirect_url, "POST", data, headers)

    def do_DELETE(self):
        redirect_url, headers = self.get_url_and_headers()

        self.make_request(redirect_url, "DELETE", "", headers)

    def do_OPTIONS(self):
            
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "*")
        self.send_header("Access-Control-Allow-Headers", "X-Redirect-URL, Authorization")
        self.end_headers()

        return

    def get_url_and_headers(self):
        headers = {}
        for header_name in self.headers.keys():
            headers[header_name] = self.headers.getheader(header_name)

        redirect_url = headers["x-redirect-url"]
        del headers["x-redirect-url"]

        return (redirect_url, headers)

    def make_request(self, url, method, data, headers):
        msg_url = url.replace("%", "%%")
        self.log_message("%s: %s" % (method, msg_url))

        try:
            # Make the request
            request = urllib2.Request(url, data, headers)
            request.get_method = lambda: method
            response = urllib2.urlopen(request)

            # We were successful, so send the response code
            self.send_response(response.code, message=response.msg)
            for key, value in dict(response.headers).iteritems():
                # Optionally log the headers
                self.log_message("%s: %s" % (key, value))

                self.send_header(key, value)
            
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "*")
            self.send_header("Access-Control-Allow-Headers", "X-Redirect-URL, Authorization")

            # We are done with the headers
            self.end_headers()

            # Copy the response to the output
            self.copyfile(response, self.wfile)
        except urllib2.HTTPError as e:
            for key, value in dict(e.hdrs).iteritems():
                self.log_message("%s: %s" % (key, value))

            print e.fp.read()

            # We had an error, so send it
            self.send_error(e.code, message=e.msg)
        
def serve(port = PORT):
    Handler = RedirectHandler
    
    httpd = SocketServer.TCPServer(("", PORT), Handler)
    httpd.socket.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    
    print "API Explorer -- Port: %s" % port
    
    httpd.serve_forever()

def main(argv):
    if (len(argv) > 0):
        port = argv[0]
        serve(port = PORT)
    else:
        serve()

    serve(port)
        
if __name__ == "__main__":
    main(sys.argv[1:])