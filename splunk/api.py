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

# UNDONE: APIs need to take a port in addition to hostname
# UNDONE: Review exception types
# UNDONE: Async requests (open, close, jobs, search .. get, post, ..)
# UNDONE: Handle paging on collections
# UNDONE: Parse results more incrimentally (sax?) .. at least for collection
#   results we can define an iterator and yield collection members more 
#   incrimentally.
# UNDONE: Review all response handlers for consistent use of data utilities

import urllib
from xml.etree import ElementTree
from xml.etree.ElementTree import XML

import splunk.data as data
import splunk.http as http
from splunk.util import record, Record
from splunk.wire import default, xname

# Full resource paths
_path = record({
    'login': "/services/auth/login",
})

# Resource path suffixes
_suffix = record({
    'admin_capabilities': "admin/capabilities",
    'apps_local': "apps/local",
    'admin_directory': "admin/directory",
    'saved_eventtypes': "saved/eventtypes",
    'search_commands': "search/commands",
    'search_fields': "search/fields",
    'search_job': "search/jobs/%s",
    'search_job_control': "search/jobs/%s/control",
    'search_jobs': "search/jobs",
    'search_parser': "search/parser"
})

# Ensure that this is a syntactically valid Splunk namespace.
# The namespace must be of the form <username>:<appname> where both username
# and appname must be at least one character, must not contain a colon (':'),
# and may be a wildcard ('*').
def _check_namespace(namespace):
    if len(namespace) < 3 or namespace.count(':') != 1:
        raise SplunkError("Invalid namespace: '%s'" % namespace)

# Check the response code in the given response message and raise an HTTPError
# as appropriate.
def _check_response(response):
    if response.status >= 400:
        raise HTTPError(response.status, response.reason)

# Combine the given host & path to create a fully-formed URL.
def _mkurl(host, path):
    # Append default port to host if port is not already provided
    if not ':' in host: host = host + ':' + default.port
    return "%s://%s%s" % (default.scheme, host, path)

# Construct a resource path using the given path suffix and optional namespace
def _mkpath(suffix, namespace = None):
    if namespace is None: 
        return "/services/%s" % suffix
    username, appname = namespace.split(':')
    if username == "*": username = '-'
    if appname == "*": appname = '-'
    return "/servicesNS/%s/%s/%s" % (username, appname, suffix)

def login(host, username, password):
    """Login at the given host using given credentials and return sessionKey"""
    url = _mkurl(host, _path.login)
    response = http.post(url, username=username, password=password)
    _check_response(response)
    return XML(response.body).findtext("./sessionKey")

class Connection:
    def __enter__(self):
        return self.open()

    def __del__(self):
        self.close()

    def __exit__(self, type, value, traceback):
        self.close()

    def __init__(self, host, username, password, namespace = None):
        self._server = None
        self.token = None # The session (aka authn) token
        self.host = host
        self.username = username
        self.password = password
        self.namespace = namespace

    # Idempotent
    def close(self):
        self.token = None
        return self

    def isclosed(self):
        return self.token is None

    def isopen(self):
        return self.token is not None

    def login(self):
        self.token = "Splunk " + login(self.host, self.username, self.password)
        return self

    # Idempotent
    def open(self):
        self.login()
        return self

    def _checked_get(self, path, **kwargs):
        response = self.get(path, **kwargs)
        _check_response(response)
        return response

    def _checked_post(self, path, **kwargs):
        response = self.post(path, **kwargs)
        _check_response(response)
        return response

    # Returns request headers for this connection
    def _headers(self):
        return [("Authorization", self.token)]

    def get(self, path, timeout = None, **kwargs):
        url = _mkurl(self.host, path)
        return http.get(url, self._headers(), timeout, **kwargs)

    def post(self, path, timeout = None, **kwargs):
        url = _mkurl(self.host, path)
        return http.post(url, self._headers(), timeout, **kwargs)

    def put(self, path):
        pass # UNDONE

    def apps(self, **kwargs):
        """Returns a list of installed applications."""
        path = _mkpath(_suffix.apps_local, self.namespace)
        response = self._checked_get(path, **kwargs)
        return _parse_apps(response.body)

    def capabilities(self, **kwargs):
        path = _mkpath(_suffix.admin_capabilities)
        response = self._checked_get(path, **kwargs)
        return data.load(response.body, "%s/%s" % (xname.entry, xname.content))

    def commands(self, **kwargs):
        """Returns a list of search commands."""
        path = _mkpath(_suffix.search_commands, self.namespace)
        response = self._checked_get(path, **kwargs)
        return _parse_commands(response.body)

    def directory(self, **kwargs):
        """Returns a directory listing of objects visible to the user."""
        path = _mkpath(_suffix.admin_directory, self.namespace)
        response = self._checked_get(path, **kwargs)
        return _parse_directory(response.body)

    def eventtypes(self, **kwargs):
        """Returns a list of eventtypes."""
        path = _mkpath(_suffix.saved_eventtypes, self.namespace)
        response = self._checked_get(path, **kwargs)
        return _parse_eventtypes(response.body)

    def fields(self, **kwargs):
        """Returns a list of search fields."""
        path = _mkpath(_suffix.search_fields, self.namespace)
        response = self._checked_get(path, **kwargs)
        return _parse_fields(response.body)

    def job(self, id, **kwargs):
        """Returns detail on the given job id."""
        path = _mkpath(_suffix.search_job % id, self.namespace)
        response = self._checked_get(path, **kwargs)
        return data.load(response.body, xname.content)

    def jobids(self, **kwargs):
        """Returns ids of all search jobs."""
        return [job.sid for job in self.jobs(**kwargs)]

    # UNDONE: The following should return job ids, or job objects
    def jobs(self, id = None, **kwargs):
        """Returns detail on the given job id, or detail on all active search
           jobs if no id is provided."""
        if id is not None: return self.job(id)
        path = _mkpath(_suffix.search_jobs, self.namespace)
        response = self._checked_get(path, **kwargs)
        return data.load(response.body, "%s/%s" % (xname.entry, xname.content))

    def parse(self, query):
        path = _mkpath(_suffix.search_parser)
        response = self.get(path, q=query)
        if response.status == 200:
            return data.load(response.body)
        messages = _parse_messages(response.body) # Grab error messages
        message = "Syntax error"
        if len(messages) > 0: 
            message = messages[0].get("$text", message)
        raise SyntaxError(message)

    def search(self, query, **kwargs):
        """Execute the given search query."""
        kwargs["search"] = query
        path = _mkpath(_suffix.search_jobs, self.namespace)
        response = self.post(path, **kwargs)
        if response.status == 200: # oneshot
            return response.body
        if response.status == 201: # Created
            return XML(response.body).findtext("sid").strip()
        raise HTTPError(response.status, response.reason)

    def server(self):
        if self._server == None:
            self._server = Server(self)
        return self._server

    def status(self):
        return "closed" if self.token is None else "open"

def connect(host, username, password, namespace = None):
    """Create and open a connection to the given host"""
    return Connection(host, username, password, namespace).open()

# Convert the given job response message to a job state value
def _jobstate(message):
    if response.isDone:
        return "done"
    if response.isPaused:
        return "paused"
    if response.error is not None:
        return "failed"
    return "running"

# A Splunk search job
class Job:
    def __init__(self, cn, id):
        self._cn = cn
        self._id = id
        self.age = 0
        self.ttl = 0
        self.progress = 0.0
        self.state = "none"
        self.updated = None

    def _control(self, action):
        path = _mkpath(_suffix.search_job_control % self.id, self._cn.namespace)
        return self._post(path, action=action)

    # Retrieve the status of the current job
    def _get(self, path):
        path = _mkpath(_suffix.search_job % self.id, self._cn.namespace)
        return self._cn._checked_get(path)
    
    # Issue a post against the current job
    def _post(self, path, **kwargs):
        return self._cn._checked_post(path, **kwargs)

    # Refresh the state of the job object with the given response message
    def _update(self, message = None):
        if message is None: 
            message = data.load(self._get(self._path)) # UNDONE
        # UNDONE: check and make sure the id matches
        self.state = self._jobstate(message)
        self.age = data.runDuration
        self.progress = data.doneProgress
        date.updated = now() # UNDONE

    def cancel(self):
        self._control("cancel")

    def pause(self):
        self._control("pause")

    def refresh(self):
        self._update()

    def touch(self):
        self._control("touch")

    def resume(self):
        self._control("unpause")

    def finalize(self):
        self._control("finalize")

class Server(Record):
    def __init__(self, cn):
        self._cn = cn
        self.refresh();

    def _get(self):
        response = self._cn.get("/services/server/info")
        info = _parse_content(response.body)

        self['build'] = info.build
        self['cpu'] = info.cpu_arch
        self['guid'] = info.guid
        #self['master_guid'] = info.master_guid
        self['mode'] = info.mode
        self['name'] = info.serverName
        self['version'] = info.version

        self['license'] = record({
            'isfree': info.isFree,
            'istrial': info.isTrial,
            'keys': info.licenseKeys,
            'signature': info.licenseSignature,
            'state': info.licenseState,
        })

        self['os'] = record({
            'build': info.os_build,
            'name': info.os_name,
            'version': info.os_version,
        })

    def _getcapabilities(self):
        response = self._cn.get("/services/admin/capabilities")
        body = data.load(response.body)
        return body.entry.content.capabilities

    # Returns the entry element from the response body of a GET request to 
    # the givne path.
    def _getentry(self, path):
        response = self._cn.get(path, count=-1)
        body = data.load(response.body)
        return body.entry if isinstance(body.entry, list) else [body.entry]

    # UNDONE: Naming of role members
    def _getroles(self):
        items = self._getentry("/services/admin/roles")
        roles = {}
        for item in items:
            name = item.title
            data = item.content
            roles[name] = record({
                'name': name,
                'capabilities': data.capabilities,
                'defaultapp': data.defaultApp,
                'imported_capabilities': data.imported_capabilities,
                'improted_roles': data.imported_roles,
                'imported_rtSrchJobsQuota': data.imported_rtSrchJobsQuota,
                'imported_srchDiskQuota': data.imported_srchDiskQuota,
                'imported_srchFilter': data.imported_srchFilter,
                'imported_srchIndexesAllowed': data.imported_srchIndexesAllowed,
                'imported_srchIndexesDefault': data.imported_srchIndexesDefault,
                'imported_srchJobsQuota': data.imported_srchJobsQuota,
                'imported_srchTimeWin': data.imported_srchTimeWin,
                'rtSrchJobsQuota': data.rtSrchJobsQuota,
                'srchDiskQuota': data.srchDiskQuota,
                'srchFilter': data.srchFilter,
                'srchIndexesAllowed': data.srchIndexesAllowed,
                'srchIndexesDefault': data.srchIndexesDefault,
                'srchJobsQuota': data.srchJobsQuota,
                'srchTimeWin': data.srchTimeWin,
            })
        return roles

    def _getusers(self):
        items = self._getentry("/services/admin/users")
        users = {}
        for item in items:
            name = item.title
            data = item.content
            users[name] = record({
                'name': name,
                'email': data.email,
                'password': data.password,
                'realname': data.realname,
                'roles': data.roles,
                'defaultapp': data.defaultApp,
            })
        return users
    
    def capabilities(self):
        if self._capabilities == None: 
            self._capabilities = self._getcapabilities()
        return self._capabilities

    def refresh(self): 
        self._capabilities = None
        self._roles = None
        self._users = None
        self._get()

    def roles(self):
        if self._roles == None: 
            self._roles = self._getroles()
        return self._roles

    def restart(self):
        pass # UNDONE

    def users(self):
        if self._users == None:
            self._users = self._getusers()
        return self._users

#
# Response handlers
#

def _parse_apps(body):
    entries = XML(body).findall(xname.entry)
    return map(entries, selector({'name': xname.title}))

def _parse_commands(body):
    entries = XML(body).findall(xname.entry)
    return map(entries, selector({'name': xname.title}))

def _parse_content(body):
    content = XML(body).find("./*/%s" % xname.content)
    return data.load_element(content)
    
def _parse_directory(body):
    def _findtype(entry): # ElementTree has poor XPath support
        pattern = "%s/%s/%s" % (xname.content, xname.dict, xname.key)
        for element in entry.findall(pattern):
            if element.get("name") == "eai:type":
                return element.text
        return ""
    entries = XML(body).findall(xname.entry)
    return map(entries, selector({'name': xname.title, 'type': _findtype}))

# /response/messages/msg*
def _parse_messages(body):
    # We expect to see /response/messages/msg*
    msgs = XML(body).findall("messages/msg")
    return map(msgs, _load_leaf)

def _parse_eventtypes(body):
    entries = XML(body).findall(xname.entry)
    return map(entries, _parse_eventtype)

# Construct result record by merging entry title with contents (dict)
def _parse_eventtype(entry):
    dict = entry.find(xname.content).find(xname.dict)
    result = _load_dict(dict)
    result["name"] = entry.find(xname.title).text
    return result

def _parse_fields(body):
    entries = XML(body).findall(xname.entry)
    return map(entries, selector({'name': xname.title, 'id': xname.id}))

# Load the contents of the given element into a dict. This routine assumes 
# that the contents are either a string, a <list> or a <dict> element, so this
# can only be called in specific contexts, for example recursively within the 
# content element of a splunk atom <entry> element.
def _load_content(element):
    if element is None:
        return ""
    kids = list(element) 
    count = len(kids) 
    assert count in [0, 1]
    if count == 0: 
        return element.text
    child = kids[0]
    if child.tag == xname.dict: 
        return _load_dict(child)
    if child.tag == xname.list: 
        return _load_list(child)
    assert False # Unexpected
    return None

# Parse a <dict> element and return a Python dict
def _load_dict(element):
    assert element.tag == xname.dict
    keys = element.findall(xname.key)
    result = {}
    for key in keys: result[key.attrib["name"]] = _load_content(key)
    return record(result)

# Load a leaf element into
def _load_leaf(element):
    assert len(list(element)) == 0 # No kids
    result = { '$text': element.text }
    for k, v in element.attrib.items(): result[k] = v
    return result

# Parse a <list> element and return a Python list
def _load_list(element):
    assert element.tag == xname.list
    map(element.findall(xname.item), _load_content)

def map(list, fn): 
    return [fn(item) for item in list] if list is not None else []

# Parse the result from a jobs request into a pythonic form.
def find1(match):
    """Returns a singleton finder for the given match expression"""
    return lambda element: element.find(match)

def findn(match):
    """Returns an 'all" finder for the given match expression"""
    return lambda element: element.findall(match)

def select(element, rules):
    """Returns a record consisting of items selected from the given element 
       using the given rules. A rule may be a simple selection string, or a
       lambda."""
    result = {}
    for name in rules.keys():
        rule = rules[name]
        if isinstance(rule, str):
            result[name] = element.findtext(rule)
        else:
            result[name] = rule(element)
    return record(result)

def selector(rules):
    """Construct a selector based on the given set of selection rules."""
    return lambda element: select(element, rules)

#
# Exceptions
#
    
class SplunkError(Exception):
    pass

class SyntaxError(SplunkError):
    pass

class HTTPError(SplunkError):
    def __init__(self, status, reason):
        SplunkError.__init__(self, "HTTP %d %s" % (status, reason)) 
        self.reason = reason
        self.status = status
