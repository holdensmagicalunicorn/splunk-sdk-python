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
import time
import xml.dom.minidom

# splunk support files
import tools.cmdopts as cmdopts
import splunk.binding as binding
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

def trace(string):
    """ trace something to the log file, if debug is on """
    if DEBUG:
        FD.write(string + "\n")
        FD.flush()

##
## The full atom RFC can be found here -- for reference
##
## http://tools.ietf.org/html/rfc4287
##

def convert_xml_to_atom(xml_text):
    """ splunk specific XML to Atom coverter """

    ##
    ## Requires elements of <feed>:
    ## id:      Identifies the feed using a universally unique and permanent 
    ##          URI. If you have a long-term, renewable lease on your Internet
    ##          domain name, then use your website's address.
    ##          <id>http://host-name:8086</id>
    ## title:   Contains a human readable title for the feed. 
    ##          <title>Splunk event report</title>
    ## updated: Indicates the last time the feed was modified significantly.
    ##          <updated>2003-12-13T18:30:02Z</updated>
    ##

    ## Recommended elements of <feed>:
    ## author:  Names one author of the feed. 
    ##          <author>
    ##            <name>Splunk</name>
    ##          </author>
    ## link:    Identifies a related Web page. 
    ##          The type of relation is defined by the rel attribute. 
    ##          A feed is limited to one alternate per type and hreflang. 
    ##          A feed should contain a link back to the feed itself.
    ##          <link rel="self" href="/feed" />
    ##

    ## Optional elements of <feed>:
    ## category:Specifies a category that the feed belongs to. 
    ##          A feed may have multiple category elements.
    ##          <category term="sports"/>
    ## contributor: Names one contributor to the feed. 
    ##          An feed may have multiple contributor elements. 
    ##          <contributor>
    ##            <name>Jane Doe</name>
    ##          </contributor>
    ## generator: Identifies the software used to generate the feed, 
    ##          for debugging and other purposes. 
    ##          Both the uri and version attributes are optional.
    ##          <generator uri="/myblog.php" version="1.0">
    ##            Example Toolkit
    ##          </generator>
    ## icon:    Identifies a small image which provides iconic visual 
    ##          identification for the feed. Icons should be square.
    ##          <icon>/icon.jpg</icon>
    ## logo:    Identifies a larger image which provides visual identification 
    ##          for the feed. Images should be twice as wide as they are tall.
    ##          <logo>/logo.jpg</logo>
    ## rights:  Conveys information about rights, e.g. copyrights, held in 
    ##          and over the feed.
    ##          <rights type="html">
    ##            &amp;copy; 2005 John Doe
    ##          </rights>
    ## subtitle:Contains a human-readable description or subtitle of the feed. 
    ##          <subtitle>all your examples are belong to us</subtitle>`
    ##

    ## ****************************************************************

    ## Required elements of <entry>
    ## id:      Identifies the entry using a universally unique and 
    ##          permanent URI. Two entries in a feed can have the same value 
    ##          for id if they represent the same entry at different 
    ##          points in time.
    ##          <id>http://host-name:8086/xxx/yyyy</id>
    ## title:   Contains a human readable title for the entry.
    ##          <title>Splunk powered nanomites scour your IT</title>
    ## updated	Indicates the last time the entry was modified.
    ##          <updated>2003-12-13T18:30:02-05:00</updated>
    ##

    ## Recommended elements of <entry>
    ## author	Names one author of the entry.
    ##          <author>
    ##            <name>Splunk</name>
    ##          </author>
    ## content: Contains or links to the complete content of the entry. 
    ##          Content must be provided if there is no alternate link, 
    ##          and should be provided if there is no summary. 
    ##          <content>all the relevant information of this entry </content>
    ## link:    Identifies a related Web page. The type of relation is defined 
    ##          by the rel attribute. An entry is limited to one alternate per 
    ##          type and hreflang. An entry must contain an alternate link if 
    ##          there is no content element.
    ##          <link rel="alternate" href="/blog/1234"/>
    ## summary: Conveys a short summary, abstract, or excerpt of the entry. 
    ##          Summary should be provided if there either is no content 
    ##          provided for the entry, or that content is not inline 
    ##          (i.e., contains a src attribute), or if the content is encoded 
    ##          in base64.
    ##          <summary>Some text.</summary>
    ##

    ## Optional elements of <entry>
    ## category:Specifies a category that the entry belongs to. An entry may 
    ##          have multiple category elements.
    ##          <category term="data"/>
    ## contributor:Names one contributor to the entry. An entry may have 
    ##          multiple contributor elements. 
    ##          <contributor>
    ##            <name>Monty Python</name>
    ##          </contributor>
    ## published:Contains the time of the initial creation or 
    ##          first availability of the entry.
    ##          <published>2003-12-13T09:17:51-08:00</published>
    ## source:  If an entry is copied from one feed into another feed ...
    ##          <source>
    ##            <id>http://example.org/</id>
    ##            <title>Fourty-Two</title>
    ##            <updated>2003-12-13T18:30:02Z</updated>
    ##            <rights> &amp;copy 2011 Splunk, Inc.</rights>
    ##          </source>
    ## rights:  Conveys information about rights, e.g. copyrights, held in 
    ##          and over the feed.
    ##          <rights type="html">
    ##            &amp;copy; 2005 Monty Python
    ##          </rights>

    return xml_text

def fix_indeces(xml_text, idstring):
    """ fixup identical ids to conform with Atom spec """

    #
    # splunk returns multiple <entry> components all with
    # the same index (<id>). Make them unique
    #

    rawtext = idstring.lstrip("<id>").rstrip("</id>")
    count = 0

    while xml_text.find(idstring) != -1:
        insert = "<id>http:/" + rawtext + "-" + str(count) + "</id>"
        xml_text = xml_text.replace(idstring, insert, 1)
        count = count + 1

    return xml_text

def fixup_to_msft_schema(fixed_xml):
    """ transform the splunk schema to msft schema """

    #
    # for powerpivot/excel parsing and interpretation
    # add in the microsoft schema and then munge the named multi-key
    # elements to individually named elements
    #

    ## add msft schema to splunk schema (namespace)
    fixed_xml = fixed_xml.replace(
    'xmlns:s="http://dev.splunk.com/ns/rest"', 
    'xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices" \
     xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata" \
     xmlns:s="http://dev.splunk.com"', 1)

    ## replace s:dict with m:properties
    fixed_xml = fixed_xml.replace("<s:dict>", "<m:properties>")
    fixed_xml = fixed_xml.replace("</s:dict>", "</m:properties>")

    ## change the keys to elements
    try:
        doc = xml.dom.minidom.parseString(fixed_xml)
    except xml.parsers.expat.ExpatError:
        trace("Error: xml failed to parse via xml.dom.minidom")
        return fixed_xml

    ## get all keys within m:properties
    ## replace keys with d:<name> entities
    allprops = doc.getElementsByTagName("m:properties")
    for prop in allprops:
        newlist = []
        children = prop.childNodes
        for child in children:
            if child.attributes != None and child.firstChild != None:
                name = str(child.getAttribute("name"))
                value = str(child.firstChild.nodeValue)
                newelement = doc.createElement("d:"+name)
                newtext = doc.createTextNode(value)
                newelement.appendChild(newtext)
                newlist.append(newelement)
        while len(prop.childNodes) != 0:
            prop.removeChild(prop.childNodes[0])
        for child in newlist:
            newtext = doc.createTextNode("\n")
            prop.appendChild(newtext)
            prop.appendChild(child)
    
    fixed_xml = str(doc.toxml())

    return fixed_xml

def fix_xml(xml_text):
    """ fixup broken XML """

    ## this function detects broken XML and fixes it up.
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
                fixed_xml = xml_decl + "\n"
                fixed_xml += outer_wrapper_start
                fixed_xml += xml_text.replace(xml_decl, "", 1)
                fixed_xml += outer_wrapper_end

    ## 2. <id></id> must be unique within a feed, AND be a complete
    #     URL (i.e. partial URL is insufficent)
    #
    #     <id>/services/search/jobs/1303147485.159</id>
    #     changes to:
    #     <id>http://DNSname/services/search/jobs/1303147485.159</id>
    #
    #     and that there cannot be multiple id's with the same value
    #
    #     <id>http://DNSname/services/search/jobs/1303147485.159</id>
    #     changes to (add -[Number])
    #     <id>http://DNSname/services/search/jobs/1303147485.159-1</id>
    #
    #     So says the Atom 1.0 verifiers
    
    index = fixed_xml.find("<id>")
    if index != -1:
        # extract id string
        eol = fixed_xml.find("\n", index)
        idstring = fixed_xml[index:eol]
    
        # get the number of occurances
        occurances = fixed_xml.count(idstring)
    
        if occurances > 1:
            fixed_xml = fix_indeces(fixed_xml, idstring)
    
    ## 3. comvert s:* to d:* and m:*

    fixed_xml = fixup_to_msft_schema(fixed_xml)

    ## 4. <test condition> [TBD]

    return fixed_xml

def debug_connect(environ):
    """ optionally print some debug info on connection by client """

    # conditionally generate debug printing
    debugdata = DEBUG_TEMPLATE % {
      'python_version': sys.version,
      'platform': sys.platform,
      'abs_path': os.path.abspath('.'),
      'filename': __file__,
      'python_path': repr(sys.path),
      'wsgi_env': '\n'.join([ROW_DATA % item for item in environ.items()]),
    }

    trace("Context data:\n%s\n" % debugdata)

def wait_for_search(context, url):
    """ when POSTing, wait for a finished splunk response """

    trace("wait_for_search: %s, %s" % (context, url))

    ## if posting, wait on the object to be finished
    while True:
        data = context.get(url)
        pxml = xml.dom.minidom.parseString(data.body.read())
        for key in pxml.getElementsByTagName("s:key"):
            if key.getAttribute("name") == "isDone":
                if key.firstChild.nodeValue == "1":
                    return
        time.sleep(1)

def post_query(context, endpoint, query):
    """ post a query, wait for response """

    trace("post_query : %s, %s, %s" % (context, endpoint, query))

    # remove double search
    query = query.replace("search=", "", 1)

    sid_xml_text = context.post(endpoint, search=query).body.read()
    sid_xml = xml.dom.minidom.parseString(sid_xml_text)
    sid = str(sid_xml.getElementsByTagName("sid")[0].firstChild.nodeValue)

    endpoint = endpoint + "/" + sid
    wait_for_search(context, endpoint)

    # search has completed, get the data and return
    endpoint = endpoint + "/results"
    return context.get(endpoint, output_mode="atom")

def application(environ, start_response):
    """ The splunk proxy processor """

    debug_connect(environ)

    ## extract some basic HTTP/WSGI info
    endpoint = environ["PATH_INFO"]
    query = environ["QUERY_STRING"]

    ## perform idempotent login/connect -- get login creds from ~/.splunkrc
    connection = connect(**(cmdopts.parser().loadrc(".splunkrc")
                            .parse(sys.argv[1:]).result).kwargs)
    # get lower level context
    context = binding.connect( host=connection.host, 
                               username=connection.username,
                               password=connection.password)

    ##
    ## here we can/should/must look up the endpoint and decide what operation
    ## needs to be done -- for now we simply "get" for basic urls, and 
    ## look for a special "search" in the query (if present) and build a job 
    ## out of it.
    ## 
    ## in particular, we want to look for:
    ##
    ## /services/search/jobs
    
    ## sanitize query, and issue
    ##
    ## this is a little awkward, browsers and BI apps seem to sanitize the 
    ## query string(s) which doesn't get accepted by splunkd. So we unquote
    ## the original and rebuild it the way we would like to see it.
    if query:
        query = urllib.unquote(query)
        ## wkcfix -- break out ? <something> = and use <something> 
        ## as keyword, not "search"?

        if endpoint == "/services/search/jobs":
            data = post_query(context, endpoint, query)
            # fixup query results 
            body = fix_xml(body)
        else:
            data = context.get(endpoint, search=query) 
    else:
        data = context.get(endpoint) 

    ## extract the status and headers from the splunk operation 
    status = str(data["status"]) + " " + data["reason"]
    headers = data["headers"]

    body = data.body.read()

    trace("Return data body:\n")
    trace(body + "\n")

    ## clean hop-by-hop from headers (described in section 13.5.1 of RFC2616),
    ## and adjust the header length if modified by fix_xml()
    for thing in headers:
        if thing[0] == "connection":
            headers.remove(thing)
        if thing[0] == "content-length":
            headers.remove(thing)
            headers.insert(0, ("content-length", str(len(body))))

    ## start the response (retransmit the status and headers)
    start_response(status, headers)

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
