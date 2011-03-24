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

# UNDONE: Flatten server onto Service (info, users, roles, caps)
# UNDONE: Editing of entities
# UNDONE: Async operations
# UNDONE: APIs need to take a port in addition to hostname
# UNDONE: Review exception types
# UNDONE: Handle paging on collections
# UNDONE: Parse results more incrimentally (sax?) .. at least for collection
#   results we can define an iterator and yield collection members more 
#   incrimentally.
# UNDONE: Review all response handlers for consistent use of data utilities
# UNDONE: Paramaterize Collection with <get, item, ctor, dtor> functions
# UNDONE: Make collections more data driven
# UNDONE: Figure out how to delay allocation of "service" sub-objects (colls)
# UNDONE: Consider moving all current code into splunk.client
# UNDONE: Consider "Service" (or Session) instead of Connection

#
# Service
#   info : dict
#   users : Collection
#   roles : list
#   capabilities : list
#   commands : Collection
#   applications : Collection
#   indexes : Collection
#   inputs : Collection
#   jobs : Collection*
#
# UNDONE:
#   Service.restart
#   Index.submit(data) aka publish?
#   alerts
#   licenses : CollectionRO
#   fields?
#

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
    'app': "apps/local/%s",
    'apps': "apps/local",
    'capabilities': "admin/capabilities",
    'directory': "admin/directory",
    'index': "data/indexes/%s",
    'indexes': "data/indexes",
    'roles': "admin/roles",
    'saved_eventtypes': "saved/eventtypes",
    'search_commands': "search/commands",
    'search_fields': "search/fields",
    'search_job': "search/jobs/%s",
    'search_job_control': "search/jobs/%s/control",
    'search_jobs': "search/jobs",
    'search_parser': "search/parser",
    'users': "admin/users",
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
        self.applications = Applications(self)
        self.indexes = Indexes(self)
        self.inputs = Inputs(self)
        self.licenses = Licenses(self)
        self.objects = Objects(self)
        self.roles = Roles(self)
        self.users = Users(self)

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

    def open(self): # Idempotent
        self.login()
        return self

    def _checked_delete(self, path, **kwargs):
        response = self.delete(path, **kwargs)
        _check_response(response)
        return response

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

    def delete(self, path, timeout = None, **kwargs):
        url = _mkurl(self.host, path)
        return http.delete(url, self._headers(), timeout, **kwargs)

    def get(self, path, timeout = None, **kwargs):
        url = _mkurl(self.host, path)
        return http.get(url, self._headers(), timeout, **kwargs)

    def post(self, path, timeout = None, **kwargs):
        url = _mkurl(self.host, path)
        return http.post(url, self._headers(), timeout, **kwargs)

    def capabilities(self, **kwargs):
        path = _mkpath(_suffix.capabilities)
        response = self._checked_get(path, **kwargs)
        xpath = "%s/%s" % (xname.entry, xname.content)
        return data.load(response.body, xpath).capabilities

    def commands(self, **kwargs):
        """Returns a list of search commands."""
        path = _mkpath(_suffix.search_commands, self.namespace)
        response = self._checked_get(path, **kwargs)
        return _parse_commands(response.body)

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

    def info(self):
        response = self._checked_get("/services/server/info")
        return _parse_content(response.body)

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

    def restart(self):
        pass # UNDONE

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

class Collection: # Abstract
    def __init__(self, cn):
        self._cn = cn
        self._items = None

    def __call__(self, name = None):
        return self.keys() if name is None else self[name]

    def __getitem__(self, key):
        self.ensure()
        return self._items.__getitem__(key)
        
    def __iter__(self):
        self.ensure()
        return self._items.__iter__()

    def __len__(self):
        self.ensure()
        return self._items.__len__()

    def create(self, **kwargs):
        raise # Abstract

    def delete(self, **kwargs):
        raise # Abstract

    def ensure(self):
        if self._items is None: self.refresh()

    def get(self, name, default = None):
        self.ensure()
        return self._items.get(key, default)

    def has_key(self):
        self.ensure()
        return self._items.has_key()

    def items(self):
        self.ensure()
        return self._items.items()

    def iteritems(self):
        self.ensure()
        return self._items.iteritems()

    def iterkeys(self):
        self.ensure()
        return self._items.iterkeys()

    def itervalues(self):
        self.ensure()
        return self._items.itervalues()

    def keys(self):
        self.ensure()
        return self._items.keys()

    def refresh(self):
        raise # Abstract

    def values(self):
        self.ensure()
        return self._items.values()

class Applications(Collection):
    def create(self, name, **kwargs):
        path = _mkpath(_suffix.apps, self._cn.namespace)
        self._cn._checked_post(path, name=name, **kwargs)
        self.refresh()

    def delete(self, name):
        path = _mkpath(_suffix.app % name, self._cn.namespace)
        self._cn._checked_delete(path)
        self.refresh()

    def refresh(self):
        path = _mkpath(_suffix.apps, self._cn.namespace)
        response = self._cn._checked_get(path, count=-1)
        self._items = _parse_apps(response.body)

class Indexes(Collection):
    def create(self, name, **kwargs):
        path = _mkpath(_suffix.indexes, self._cn.namespace)
        self._cn._checked_post(path, name=name, **kwargs)
        self.refresh()

    # UNDONE: See http://jira.splunk.com:8080/browse/SPL-35023 for how to 
    # implement!
    def clear(self, name):
        """Clear the named index."""
        raise

    # It's not possible to delete an index
    def delete(self, name):
        raise # UNDONE: IllegalOperationError?

    def refresh(self):
        path = _mkpath(_suffix.indexes, self._cn.namespace)
        response = self._cn._checked_get(path, count=-1)
        self._items = _parse_indexes(response.body)

class Inputs(Collection):
    def create(self): raise

    def delete(self): raise

    # data/inputs/monitor
    # UNDONE: data/inputs/oneshot ?
    # UNDONE: data/inputs/script
    # UNDONE: data/inputs/tcp/raw
    # UNDONE: data/inputs/tcp/cooked
    # UNDONE: data/inputs/tcp/ssl
    # UNDONE: data/inputs/udp
    # UNDONE: data/inputs/win-event-log-collections
    # UNDONE: data/inputs/win-wmi-collections
    def refresh(self):
        path = _mkpath("data/inputs/monitor")
        response = self._cn._checked_get(path, count=-1)
        self._items = _parse_entries(response.body)

class Licenses(Collection):
    def create(self): raise # UNDONE

    def delete(self): raise # UNDONE

    def refresh(self):
        path = _mkpath("licenser/licenses")
        response = self._cn._checked_get(path, count=-1)
        self._items = _parse_entries(response.body)

class Objects(Collection):
    def create(self): raise # UNDONE

    def delete(self): raise # UNDONE

    def refresh(self):
        path = _mkpath(_suffix.directory);
        response = self._cn._checked_get(path, count=-1)
        self._items = _parse_entries(response.body)

class Roles(Collection):
    def create(self): pass # UNDONE

    def delete(self): pass # UNDONE

    def refresh(self):
        path = _mkpath(_suffix.roles);
        response = self._cn._checked_get(path, count=-1)
        self._items = _parse_entries(response.body)
    
class Users(Collection):
    def create(self): pass # UNDONE

    def delete(self): pass # UNDONE

    def refresh(self):
        path = _mkpath(_suffix.users);
        response = self._cn._checked_get(path, count=-1)
        self._items = _parse_entries(response.body)
    
#
# Jobs collection
#

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

#
# Response handlers
#

def _parse_apps(body):
    return _parse_entries(body)

def _parse_indexes(body):
    return _parse_entries(body)

# Parse a generic atom feed into a dict
def _parse_entries(body):
    entries = data.load(body, xname.entry)
    result = {}
    for entry in entries:
        name = entry.title
        value = entry.content
        value['name'] = name
        #del value['type']
        result[name] = value
    return result

def _parse_commands(body):
    entries = XML(body).findall(xname.entry)
    return map(entries, selector({'name': xname.title}))

def _parse_content(body):
    content = XML(body).find("./*/%s" % xname.content)
    return data.load_element(content)
    
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

# /response/messages/msg*
def _parse_messages(body):
    # We expect to see /response/messages/msg*
    msgs = XML(body).findall("messages/msg")
    return map(msgs, _load_leaf)

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
