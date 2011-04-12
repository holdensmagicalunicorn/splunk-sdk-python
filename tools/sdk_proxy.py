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
import urllib
import xml.dom.minidom

# splunk support files
import tools.cmdopts as cmdopts
from splunk.binding import connect

DEBUG = True

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

try:
    __file__
except NameError:
    __file__ = '?'


FD = None
if DEBUG:
    FD = open('./sdk_proxy.debug', 'w')

def fix_xml(xml_text):
    """ fixup broken XML """

    ## this function detcts broken XML and fixes it up.
    ## using emprical evidence, fix up things we have 
    ## seen before as broken XML

    xml_decl = "<?xml version='1.0' encoding='UTF-8'?>"
    result_preview = "<results preview='0'>"
    outer_wrapper_start = "<splunk_outer_wrapper>"
    outer_wrapper_end = "</splunk_outer_wrapper>"

    # if unchanged will return original
    fixed_xml = xml_text

    ## 1. does it parse?
    try:
        xml.dom.minidom.parseString(xml_text)
    except xml.parsers.expat.ExpatError:
        # got exception, so look for multi-result-previews
        index = xml_text.find(result_preview)
        if index > 0:
            next_index = xml_text.find(result_preview, index+1)
            if next_index > 0:
                # build outer wrapper
                fixed_xml = xml_decl
                fixed_xml += outer_wrapper_start
                fixed_xml += xml_text.replace(xml_decl, "", 1)
                fixed_xml += outer_wrapper_end

    ## 2. <next condition> [TBD]

    return fixed_xml

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
        FD.write("Context data:\n%s\n" % debugdata)

    ## extract some basic HTTP/WSGI info
    endpoint = environ["PATH_INFO"]
    query = environ["QUERY_STRING"]
    operation = environ["REQUEST_METHOD"]    # GET, POST, PUT, etc 

    ## perform idempotent login/connect -- get login creds from ~/.splunkrc
    opts = cmdopts.parser().loadrc(".splunkrc").parse(sys.argv[1:]).result
    connection = connect(**opts.kwargs)

    ## here we can/should/must look up the endpoint and decide what operation 
    ## needs to be done -- for now we simply "get" (wkcfix)

    ## sanitize query, and issue
    ## this is a little awkward, browsers and BI apps seem to sanitize the 
    ## query string(s) which doesn't get accepted by splunkd. So we unquote
    ## the original and rebuild it the way we would like to see it.
    if query:
        query = urllib.unquote(query)
        query = urllib.quote_plus(query)
        query = query.replace("%3D", "=", 1)
        final = endpoint + "?" + query
    else:
        final = endpoint
    data = connection.get(final) # output mode? (wkcfix: brad to investigate sdk support)

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

    if DEBUG:
        FD.write("http request %s to %s\n" % (operation, final))
        FD.write("Return data body:\n")
        FD.write(data["body"] + "\n")
        FD.flush()

    body = fix_xml(data["body"])

    return [body]

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
