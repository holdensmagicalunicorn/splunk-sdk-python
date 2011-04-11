#!/usr/bin/env python
"""
This software embodies a splunkd proxy that translates communication
between a client application (browser, BI application, etc) and splunkd

 Copyright 2011 Splunk, Inc.

 Licensed under the Apache License, Version 2.0 (the "License"): you may
 not use this file except in compliance with the License. You may obtain
 a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 License for the specific language governing permissions and limitations
 under the License.

This was originally a sample WSGI application:
@copyright: 2008 by MoinMoin:ThomasWaldmann
@license: Python License, see LICENSE.Python for details.

"""

# installation support files
import os.path
import os
import sys

# splunk support files
import splunk
import tools.cmdopts as cmdopts
from splunk.binding import connect

DEBUG_TEMPLATE = """\
  Python: %(python_version)s
  Python Path: %(python_path)s
  Platform: %(platform)s
  Absolute path of this script: %(abs_path)s
  Filename: %(filename)s
  WSGI Environment:
      %(wsgi_env)s
"""
ROW_DATA = "  %s -->> %r"
PORT = 8086
DEBUG = False

try:
    __file__
except NameError:
    __file__ = '?'

def application(environ, start_response):
    """ The splunk proxy processor """

    # conditionally generate debug printing
    if DEBUG:
        debugdata = DEBUG_TEMPLATE % {
          'python_version': sys.version,
          'platform': sys.platform,
          'abs_path': os.path.abspath('.'),
          'filename': __file__,
          'python_path': repr(sys.path),
          'wsgi_env': '\n'.join([ROW_DATA % item for item in environ.items()]),
        }

        ## debug print 
        print "Context data:\n%s" % debugdata

    ## extract some basic HTTP/WSGI info
    endpoint = environ["PATH_INFO"]
    query = environ["QUERY_STRING"]
    #operation = environ["REQUEST_METHOD"]    # GET, POST, PUT, etc (wkcfix)

    ## perform idempotent login/connect -- get login creds from ~/.splunkrc
    opts = cmdopts.parser().loadrc(".splunkrc").parse(sys.argv[1:]).result
    connection = connect(**opts.kwargs)

    ## here we can/should/must look up the endpoint and decide what operation 
    ## needs to be done -- for now we simply "get" (wkcfix)

    ## sanitize query, and issue
    if query:
        final = endpoint + "?" + query
    else:
        final = endpoint
    data = connection.get(final)

    ## extract the status and headers from the splunk operation 
    status = str(data["status"]) + " " + data["reason"]
    headers = data["headers"]

    ## clean hop-by-hop from headers (described in section 13.5.1 of RFC2616)
    for thing in headers:
        if thing[0] == "connection":
            headers.remove(thing)

    ## start the response (retransmit the status and headers)
    start_response(status, headers)

    ## follow with the body of the data
    ## Here is where we can/should/must translate the 
    ## atom/odata format to ... atom (wkcfix)

    return [data["body"]]

if __name__ == '__main__':
    # this script only runs when started directly from a shell
    try:
        # create a simple WSGI server and run the splunk proxy processor
        from wsgiref import simple_server
        print "splunk proxy: connect to http://localhost:%d/..." % PORT
        HTTPD = simple_server.WSGIServer(('', PORT), 
                                         simple_server.WSGIRequestHandler)
        HTTPD.set_app(application)
        HTTPD.serve_forever()
    except ImportError:
        # wsgiref not installed, just output html to stdout
        for content in application({}, lambda status, headers: None):
            print content
