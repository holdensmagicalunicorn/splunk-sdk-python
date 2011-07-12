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

# You can run the example both synchronously and using eventlet. Just comment
# and uncomment the relevant parts (marked EVENTLET and SYNCHRONOUS)

import splunk, sys
import urllib
from utils import parse
from time import sleep

# EVENTLET
from eventlet.green import urllib2  

# SYNCHRONOUS
#import urllib2

def _spliturl(url):
    scheme, part = url.split(':', 1)
    host, path = urllib.splithost(part)
    host, port = urllib.splitnport(host, 80)
    return scheme, host, port, path

class Urllib2Http(splunk.binding.HttpBase):
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

        handlers = []
        if (self.proxy):
            proxy = "%s:%s" % self.proxy
            proxy_handler = urllib2.ProxyHandler({"http": proxy, "https": proxy})
            handlers.append(proxy_handler)
        
        opener = urllib2.build_opener(*handlers)

        request = urllib2.Request(url, body, head)
        request.get_method = lambda: method

        response = None
        try:
            response = opener.open(request)
        except Exception as e:
            response = e

        response = self._build_response(
            response.code, 
            response.msg,
            dict(response.headers),
            response)

        return response

opts = None # Command line options
def main(argv):
    global opts

    # Parse the command line args
    opts = parse(argv, {}, ".splunkrc")

    # Create and store the urllib2 HTTP implementation
    http = Urllib2Http()
    opts.kwargs["http"] = http

    # Create the service and log in
    service = splunk.client.Service(**opts.kwargs)
    service.login()

    import eventlet, datetime
    pool = eventlet.GreenPool(8)

    oldtime = datetime.datetime.now()

    def do_search(query):
        job = service.jobs.create(query)

        while job["dispatchState"] != "DONE":

            # EVENTLET
            eventlet.sleep(1)

            # SYNCHRONOUS
            #sleep(1)

        results = job.results()

        return results

    # Many queries
    queries = [
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
        'search sourcetype="top" | head 100',
    ]

    # EVENTLET
    for results in pool.imap(do_search, queries):
        # No need to do anything with the result
        pass

    # SYNCHRONOUS
    #for query in queries:
    #    results = do_search(query)

    newtime = datetime.datetime.now()
    print "Elapsed Time: %s" % (newtime - oldtime)
    

if __name__ == "__main__":
    main(sys.argv[1:])

