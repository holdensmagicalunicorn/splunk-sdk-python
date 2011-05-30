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

"""This utility reads the Twitter 'spritzer' and writes status results 
   to Cassandra while teeing off a portion of the stream to Splunk for
   indexing."""

# UNDONE: The code below isnt particularly robust - eg: 
#   * It doesn't handle resetting the twitter HTTP connection or the Splunk
#     TCP connection
#   * Doesn't handle failure to write to Splunk or Cassandra (no transaction)
#   * Need some way to validate contents of database against contents of the 
#     index.

# UNDONE: Inestigate alternatives to pycassa

# UNDONE: Command line args - credentials, Splunk port, Cassandra port ...
# UNDONE: Dynamically construct line-breaking rule for twitter events
# UNDONE: Is there a better way to store bools in Cassandra?

from pprint import pprint # UNDONE

import json
import pycurl
import socket
import sys

import pycassa
from pycassa.system_manager import SystemManager
from pycassa.system_manager import ASCII_TYPE, INT_TYPE, LONG_TYPE, UTF8_TYPE

#
# Simple curl command to read from the Twitter 'gardenhose'
#
#   curl http://stream.twitter.com/1/statuses/sample.json -u<user>:<pw>
#

TWITTER_STREAM = "http://stream.twitter.com/1/statuses/sample.json"
TWITTER_LOGIN  = "http://api.twitter.com/1/account/verify_credentials.json"

SPLUNK_HOST = "localhost"
SPLUNK_PORT = 9001

CASSANDRA_HOSTPORT = "localhost:9160"
CASSANDRA_KEYSPACE = "twitter"

cassandra = None    # The cassandra service
splunk = None       # The splunk ingest socket

# UNDONE: Validate schema if it already exists
# UNDONE: Need a better wrapping: system/keyspace/column_family
class Cassandra:
    def __init__(self, hostport):
        self.hostport = hostport
        self.system = SystemManager(hostport)

    def _ensure_column_family(self, kname, cfname, cols = None):
        cfams = self.system.get_keyspace_column_families(kname)
        if cfname not in cfams.keys():
            self.system.create_column_family(
                kname, cfname,
                comparator_type = ASCII_TYPE,           # Column names
                default_validation_class = UTF8_TYPE)  # Default column value
        if cols is not None:
            for cname, ctype in cols.iteritems():
                self.system.alter_column(kname, cfname, cname, ctype)

    def column_family(self, kname, cfname):
        pool = pycassa.connect(kname, [self.hostport])
        return pycassa.ColumnFamily(pool, cfname)

    def ensure_schema(self, kname, cfams):
        # UNDONE: Parameterize replication_factor
        if kname not in self.system.list_keyspaces():
            self.system.create_keyspace(kname, replication_factor=1)
        if cfams is not None:
            for cfname, cols in cfams.iteritems():
                self._ensure_column_family(kname, cfname, cols)

class Twitter:
    def __init__(self, username, password):
        self.buffer = ""
        #self.userid = None
        self.username = username
        self.password = password
        self.connection = pycurl.Curl()

    def login(self):
        userpwd = "%s:%s" % (self.username, self.password)
        self.connection.setopt(pycurl.USERPWD, userpwd)
        # UNDONE: Must use OAuth to access REST API, even validating creds
        #import StringIO
        #self.connection.setopt(pycurl.URL, TWITTER_LOGIN_URL)
        #result = StringIO.StringIO()
        #self.connection.setopt(pycurl.WRITEFUNCTION, result.write)
        #self.connection.perform()
        #data = json.loads(result.getvalue())
        #pprint(data)
        return self

    def connect(self, onreceive):
        self.login()
        self.connection.setopt(pycurl.URL, TWITTER_STREAM)
        self.connection.setopt(pycurl.WRITEFUNCTION, onreceive)
        self.connection.perform()

#
# Pipe {id, user_id, created_at, text} => Splunk
#
# Pipe entire tweet response (aka status) into Cassandra, with some light 
# normalization of the status data:
#
#   Status is split into two parts, Status & User. Status.user is replaced
#   with Status.user_id (id pulled from user field). Status is inserted into
#   the Statuses ColumnFamily and User is inserted into the Users ColumnFamily.
#   In effect, the status data is very lightly normalized before inserting into
#   Cassandra.
#
buffer = ""
def onreceive(data):
    global buffer

    buffer += data

    if not buffer.endswith("\r\n"): return

    buffer.strip()
    result = json.loads(buffer)
    buffer = ""

    # UNDONE: Ignoring delete messages for now
    if result.has_key('delete'): return

    isstatus = \
        result.has_key('id') and \
        result.has_key('user') and \
        result.has_key('text') and \
        result.has_key('created_at')

    # Ignore if we dont recognize the result as a status message
    if not isstatus: return

    # Store status record (lightly normalized) in Cassandra
    write_status(result)

    # Write status summary to Splunk for indexing
    index_status(result)

CASSANDRA_KEYSPACE = "twitter"
# UNDONE: bools (eg: user.profile_use_background_image) are stored as strings
# UNDONE: No support for SuperColumns
CASSANDRA_SCHEMA = {
    'Statuses': {
        # UNDONE: comparator_type, default_validation_class
        #'favorited': <bool>
        'id': LONG_TYPE,
        'in_reply_to_status': LONG_TYPE,
        'text': UTF8_TYPE,
        #'truncated': <bool>
        'user_id': LONG_TYPE,
    },
    'Users': {
        'favourites_count': INT_TYPE,
        'followers_count': INT_TYPE,
        'friends_count': INT_TYPE,
        'id': LONG_TYPE,
        'list_count': INT_TYPE,
        'statuses_count': INT_TYPE,
    }
}

# Tee off summary of status data for Splunk to index
# UNDONE: Should we also tee off any results from Cassandra insert?
def index_status(status):
    id = status['id']
    user_id = status['user']['id']
    created_at = status['created_at']
    text = status['text'].encode("utf8")
    summary = "id=%d user_id=%d created_at='%s' text=%r\r\n" % (
        id, user_id, created_at, text)
    global splunk
    splunk.send(summary)
    print summary

def tostr(value):
    if isinstance(value, unicode):
        return value.encode("utf8")
    if isinstance(value, list) or isinstance(value, dict):
        return json.dumps(value)
    return str(value)

def torow(value, schema, ignore=[]):
    assert isinstance(value, dict)
    row = {}
    for cname,value in value.iteritems():
        cname = cname.encode("ascii")
        if value is None or value == [] or value == {}: continue
        if cname in ignore: continue
        ctype = schema.get(cname, None)
        value = {
            None: lambda value: tostr(value),
            INT_TYPE: lambda value: int(value),
            LONG_TYPE: lambda value: long(value),
            UTF8_TYPE: lambda value: value.encode("utf8"),
        }[ctype](value)
        row[cname] = value
    return row

def write_status(status):

    # UNDONE: Cassandra 0.6 only supports string row keys, but in 0.7 row
    # keys are binary, which should allow int & long keys, pycassa throws
    # on a now str/unicode key .. so I suspect pycassa is out of date.

    retweeted_status = status.get('retweeted_status', None)
    if retweeted_status is not None:
        write_status(retweeted_status)
        status['retweeted_status_id'] = retweeted_status['id']

    user = status['user']
    schema = CASSANDRA_SCHEMA['Users']
    ignore = ['id', 'id_str']
    row = torow(user, schema, ignore)
    cassandra_users.insert(str(user['id']), row)

    # Grab the idea of the normalized user data
    status['user_id'] = user['id']

    # Flatten entities to simplify storage model slightly
    entities = status.get('entities', None)
    if entities is not None:
        for k,v in entities.iteritems(): status[k] = v

    schema = CASSANDRA_SCHEMA['Statuses']
    ignore = [
        'entities',                 # Flattened
        'id',                       # Key value
        'id_str',                   # Redundant
        'in_reply_to_status_id_str',# Redundant
        'in_reply_to_user_id_str',  # Redundant
        'retweeted_status',         # Normalized
        'user',                     # Normalized
    ]
    row = torow(status, schema, ignore)
    cassandra_statuses.insert(str(status['id']), row)

def main():
    print "Initializing Cassandra .."
    global cassandra, cassandra_statuses, cassandra_users
    cassandra = Cassandra(CASSANDRA_HOSTPORT)
    cassandra.ensure_schema(CASSANDRA_KEYSPACE, CASSANDRA_SCHEMA)
    cassandra_statuses = cassandra.column_family(CASSANDRA_KEYSPACE, "Statuses")
    cassandra_users = cassandra.column_family(CASSANDRA_KEYSPACE, "Users")

    print "Initializing Splunk .."
    global splunk
    # UNDONE: Ensure index exists
    # UNDONE: Ensure TCP input is configured
    # UNDONE: Ensure twitter sourcetype is defined
    splunk = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    splunk.connect((SPLUNK_HOST, SPLUNK_PORT))
    splunk.send("***SPLUNK*** sourcetype=twitter\n") # Initialize stream

    print "Listening .."
    twitter = Twitter("brad_lovering", "ack00Twitter")
    twitter.connect(onreceive)

if __name__ == "__main__":
	main()

