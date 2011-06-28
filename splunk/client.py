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
# The purpose of this module is to provide a friendlier domain interface to 
# various Splunk endpoints. The approach here is to leverage the binding
# layer to capture endpoint context and provide objects and methods that
# offer simplified access their corresponding endpoints. The design avoids
# caching resource state. From the perspective of this module, the 'policy'
# for caching resource state belongs in the application or a higher level
# framework, and its the purpose of this module to provide simplified
# access to that resource state.
#
# A side note, the objects below that provide helper methods for updating eg:
# Entity state, are written so that they may be used in a fluent style.
#

# UNDONE: Cases below where we need to pass schema to data.load (eg: Collection)
# UNDONE: Check status needs to attempt to retrive error message from the
#  the resonse body. Eg: a call to index.disable on the defaultDatabase will
#  return a 404 (which is a little misleading) but the response body contains
#  a message indicating that disable cant be called on the default database.
# UNDONE: Consider Entity.delete (if entity has 'remove' link?)

"""Client layer layer asbtract aggregrate splunk objects, 
    relies on binding layer."""

from time import sleep
from urllib import urlencode, quote_plus

from splunk.binding import Context, HTTPError
import splunk.data as data
from splunk.data import record

__all__ = [
    "connect",
    "Service"
]

PATH_APPS = "apps/local"
PATH_APP = "apps/local/%s"

PATH_CONFS = "properties"
PATH_CONF = "admin/conf-%s"
PATH_STANZA = "admin/conf-%s/%s"

def _path_stanza(conf, stanza):
    """ utility to fill out the stanza for config URL """
    return PATH_STANZA % (conf, quote_plus(stanza))

PATH_INDEXES = "data/indexes"
PATH_INDEX = "data/indexes/%s"

PATH_JOBS = "search/jobs"
PATH_JOB = "search/jobs/%s"

def check_status(response, *args):
    """Checks that the given HTTP response is one of the expected values."""
    if response.status not in args:
        raise HTTPError(response.status, response.reason)

# kwargs: scheme, host, port, username, password, namespace
def connect(**kwargs):
    """Establishes an authenticated connection to the specified service."""
    return Service(**kwargs).login()

# Response utilities
def load(response):
    return data.load(response.body.read())

class Service(Context):
    """Service class."""
    def __init__(self, **kwargs):
        Context.__init__(self, **kwargs)

    @property
    def apps(self):
        """Return the collection of applications."""
        return Collection(self, PATH_APPS, "apps",
            item=lambda service, name: 
                Entity(service, PATH_APP % name, name),
            ctor=lambda service, name, **kwargs:
                service.post(PATH_APPS, name=name, **kwargs),
            dtor=lambda service, name: service.delete(PATH_APP % name))

    @property
    def confs(self):
        """Return the collection of configs."""
        return Collection(self, PATH_CONFS, "confs",
            item=lambda service, conf: 
                Collection(service, PATH_CONF % conf, conf,
                    item=lambda service, stanza:
                        Entity(service, _path_stanza(conf, stanza), stanza),
                    ctor=lambda service, stanza, **kwargs:
                        service.post(PATH_CONF % conf, name=stanza, **kwargs),
                    dtor=lambda service, stanza:
                        service.delete(_path_stanza(conf, stanza))))

    @property
    def indexes(self):
        """Return the collection of indexes."""
        return Collection(self, PATH_INDEXES, "indexes",
            item=lambda service, name: 
                Index(service, name),
            ctor=lambda service, name, **kwargs:
                service.post(PATH_INDEXES, name=name, **kwargs))

    @property
    def info(self):
        """Get the server information."""
        response = self.get("server/info")
        check_status(response, 200)
        return _filter_content(load(response).entry.content)

    @property
    def jobs(self):
        """Return Jobs through Service."""
        return Jobs(self)

    # kwargs: enable_lookups, reload_macros, parse_only, output_mode
    def parse(self, query, **kwargs):
        """Test a search query through the parser."""
        return self.get("search/parser", q=query, **kwargs)

    def restart(self):
        """Restart the service."""
        return self.get("server/control/restart")

    @property
    def settings(self):
        """Return the server settings entity."""
        return Entity(self, "server/settings")

class Endpoint:
    """ base endpoint class """
    def __init__(self, service, path):
        self.service = service
        self.path = path

    def get(self, relpath="", **kwargs):
        """Perform get on a basic endpoint."""
        response = self.service.get("%s/%s" % (self.path, relpath), **kwargs)
        check_status(response, 200)
        return response

    def post(self, relpath="", **kwargs):
        """Perform post to a basic endpoint."""
        response = self.service.post("%s/%s" % (self.path, relpath), **kwargs)
        check_status(response, 200, 201)
        return response

class Collection(Endpoint):
    """A generic implementation of the Splunk collection protocol."""

    def __init__(self, service, path, name=None, 
                 item=None, ctor=None, dtor=None):
        Endpoint.__init__(self, service, path)
        if name is not None: 
            self.name = name
        self.item = item # Item accessor
        self.ctor = ctor # Item constructor
        self.dtor = dtor # Item desteructor

    def __call__(self):
        return self.list()

    def __getitem__(self, key):
        if self.item is None: 
            raise NotSupportedError
        if not self.contains(key): 
            raise KeyError, key
        return self.item(self.service, key)

    def __iter__(self):
        # Don't invoke __getitem__ below, we don't need the extra round-trip
        # to validate that the key exists, because we just checked.
        for name in self.list(): 
            yield self.item(self.service, name)

    def contains(self, name):
        return name in self.list()

    def create(self, name, **kwargs):
        """Create a collection."""
        if self.ctor is None: 
            raise NotSupportedError
        self.ctor(self.service, name, **kwargs)
        return self[name]

    def delete(self, name):
        """Delete a specfic collection by name."""
        if self.dtor is None: 
            raise NotSupportedError
        self.dtor(self.service, name)
        return self

    def itemmeta(self):
        """Returns metadata for members of the collection."""
        response = self.get("/_new")
        content = load(response).entry.content
        return record({
            'eai:acl': content['eai:acl'],
            'eai:attributes': content['eai:attributes']
        })

    def list(self):
        """Returns a list of collection keys."""
        response = self.get(count=-1)
        entry = load(response).get('entry', None)
        if entry is None: 
            return []
        if not isinstance(entry, list): 
            entry = [entry] # UNDONE
        return [item.title for item in entry]

def _filter_content(content, *args):
    if len(args) > 0: # We have filter args
        result = record({})
        for key in args: 
            result[key] = content[key]
    else:
        # Eliminate some noise by default
        result = content
        if result.has_key('eai:acl'):
            del result['eai:acl']
        if result.has_key('eai:attributes'):
            del result['eai:attributes']
        if result.has_key('type'):
            del result['type']
    return result

class Entity(Endpoint):
    """A generic implementation of the Splunk 'entity' protocol."""

    def __init__(self, service, path, name=None):
        Endpoint.__init__(self, service, path)
        if name is not None: 
            self.name = name
        # UNDONE: The following should be derived by reading entity links
        self.delete = lambda: self.service.delete(self.path)
        self.disable = lambda: self.post("disable")
        self.enable = lambda: self.post("enable")
        self.reload = lambda: self.post("_reload")

    def __call__(self):
        return self.read()

    def __getitem__(self, key):
        return self.read()[key]

    def __setitem__(self, key, value):
        self.update(**{ key: value })

    def read(self, *args):
        """Read and return the current entity value, optionally returning
           only the requested fields, if specified."""
        response = self.get()
        content = load(response).entry.content
        return _filter_content(content, *args)

    def readmeta(self):
        """Return the entity's metadata."""
        return self.read('eai:acl', 'eai:attributes')

    def update(self, **kwargs):
        """Update Entity."""
        self.post(**kwargs)
        return self

class Index(Entity):
    """Index class access to specific operations."""
    def __init__(self, service, name):
        Entity.__init__(self, service, PATH_INDEX % name, name)
        self.roll_hot_buckets = lambda: self.post("roll-hot-buckets")

    def attach(self, host=None, source=None, sourcetype=None):
        """Opens a stream for writing events to the index."""
        args = { 'index': self.name }
        if host is not None: 
            args['host'] = host
        if source is not None: 
            args['source'] = source
        if sourcetype is not None: 
            args['sourcetype'] = sourcetype
        path = "receivers/stream?%s" % urlencode(args)
        conn = self.service.connect()
        conn.write("POST %s HTTP/1.1\r\n" % self.service.fullpath(path))
        conn.write("Host: %s:%s\r\n" % (self.service.host, self.service.port))
        conn.write("Accept-Encoding: identity\r\n")
        conn.write("Authorization: %s\r\n" % self.service.token)
        conn.write("X-Splunk-Input-Mode: Streaming\r\n")
        conn.write("\r\n")
        return conn

    def clean(self):
        """Delete the contents of the index."""
        saved = self.read('maxTotalDataSizeMB', 'frozenTimePeriodInSecs')
        self.update(maxTotalDataSizeMB=1, frozenTimePeriodInSecs=1)
        self.roll_hot_buckets()
        while True: # Wait until event count goes to zero
            sleep(1)
            if self['totalEventCount'] == '0': 
                break
        self.update(**saved)

    def submit(self, event, host=None, source=None, sourcetype=None):
        """Submits an event to the index via HTTP POST."""
        args = { 'index': self.name }
        if host is not None: 
            args['host'] = host
        if source is not None: 
            args['source'] = source
        if sourcetype is not None: 
            args['sourcetype'] = sourcetype
        path = "receivers/simple?%s" % urlencode(args)
        message = { 'method': "POST", 'body': event }
        response = self.service.request(path, message)
        check_status(response, 200)

    # kwargs: host, host_regex, host_segment, rename-source, sourcetype
    def upload(self, filename, **kwargs):
        """Uploads a file to the index using the 'oneshot' input. The file
           must be accessible from the server."""
        kwargs['index'] = self.name
        path = 'data/inputs/oneshot'
        response = self.service.post(path, name=filename, **kwargs)
        check_status(response, 201)

# The Splunk Job is not an enity, but we are able to make the interface look
# a lot like one.
class Job(Endpoint): 
    """Job class access to specific operations."""
    def __init__(self, service, sid):
        Endpoint.__init__(self, service, PATH_JOB % sid)
        self.sid = sid

    def __call__(self):
        return self.read()

    def __getitem__(self, key):
        return self.read()[key]

    def __setitem__(self, key, value):
        self.update(**{ key: value })

    def cancel(self):
        """Cancel job."""
        self.post("control", action="cancel")
        return self

    def disable_preview(self):
        """Set job disable preview."""
        self.post("control", action="disablepreview")
        return self

    def events(self, **kwargs):
        """Get job events."""
        return self.get("events", **kwargs).body

    def enable_preview(self):
        """Set job enable preview."""
        self.post("control", action="enablepreview")
        return self

    def finalize(self):
        """Finalize job."""
        self.post("control", action="finalize")
        return self

    def pause(self):
        """Pause job."""
        self.post("control", action="pause")
        return self

    def preview(self, **kwargs):
        """Get job preview data."""
        return self.get("results_preview", **kwargs).body

    def read(self, *args):
        """Read and return the jobs entity value."""
        response = self.get()
        content = load(response).content
        return _filter_content(content, *args)

    def results(self, **kwargs):
        """Get job results."""
        return self.get("results", **kwargs).body

    def searchlog(self, **kwargs):
        """Get job search log."""
        return self.get("search.log", **kwargs).body

    def setpriority(self, value):
        """Set job priority."""
        self.post('control', action="setpriority", priority=value)
        return self

    def summary(self, **kwargs):
        """Get job summary."""
        return self.get("summary", **kwargs).body

    def timeline(self, **kwargs):
        """Get job timeline."""
        return self.get("timeline", **kwargs).body

    def touch(self,):
        """Update job via touch."""
        self.post("control", action="touch")
        return self

    def setttl(self, value):
        """Set job ttl."""
        self.post("control", action="setttl", ttl=value)

    def unpause(self):
        """Unpause job."""
        self.post("control", action="unpause")
        return self

    def update(self, **kwargs):
        """Update job."""
        self.post(**kwargs)
        return self

class Jobs(Collection):
    """Jobs class."""
    def __init__(self, service):
        Collection.__init__(self, service, PATH_JOBS, "jobs",
            item=lambda service, sid: Job(service, sid))

    def create(self, query, **kwargs):
        response = self.post(search=query, **kwargs)
        sid = load(response).sid
        return Job(self.service, sid)

    def list(self):
        response = self.get()
        entry = load(response).entry
        if not isinstance(entry, list): 
            entry = [entry] # UNDONE
        return [item.content.sid for item in entry]

class SplunkError(Exception): 
    pass

class NotSupportedError(Exception): 
    pass

