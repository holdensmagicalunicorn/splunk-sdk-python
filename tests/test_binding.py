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

# UNDONE: Test splunk namespace against baseline
# UNDONE: Test splunk.data loader

from pprint import pprint # UNDONE

from os import path
import sys
import unittest
import uuid
from xml.etree import ElementTree
from xml.etree.ElementTree import XML
from _ssl import SSLError

import splunk
from splunk.binding import *
import splunk.data as data

from utils import parse

# splunkd endpoint paths
PATH_USERS = "authentication/users"

# XML Namespaces
NAMESPACE_ATOM = "http://www.w3.org/2005/Atom"
NAMESPACE_REST = "http://dev.splunk.com/ns/rest"
NAMESPACE_OPENSEARCH = "http://a9.com/-/spec/opensearch/1.1"

# XML Extended Name Fragments
XNAMEF_ATOM = "{%s}%%s" % NAMESPACE_ATOM
XNAMEF_REST = "{%s}%%s" % NAMESPACE_REST
XNAMEF_OPENSEARCH = "{%s}%%s" % NAMESPACE_OPENSEARCH

# XML Extended Names
XNAME_FEED = XNAMEF_ATOM % "feed"
XNAME_TITLE = XNAMEF_ATOM % "title"
XNAME_ENTRY = XNAMEF_ATOM % "entry"

opts = None # Command line options

def entry_titles(text):
    """Returns list of atom entry titles from the given atom text."""
    entry = data.load(text).feed.entry
    if not isinstance(entry, list): entry = [entry]
    return [item.title for item in entry]

def uname():
    """Creates a unique name."""
    return str(uuid.uuid1())

class DummyHttp(splunk.binding.HttpBase):

    def request(self, url, message, **kwargs):
        return "%s:%s:%s" % (
            message["method"] if message.has_key('method') else "GET",
            url,
            message["body"] if message.has_key('body') else None)

class PluggableHttpTestCase(unittest.TestCase):
    def setUp(self):
        http = DummyHttp()
        self.context = splunk.binding.Context(http = http)
        self.dummy_url = "/DUMMY_URL"

    def test_get(self):
        expected_response = "%s:%s:%s" % (
            "GET", 
            self.context.url(self.dummy_url), 
            None)

        self.assertEqual(
            self.context.get(self.dummy_url), 
            expected_response)

    def test_post(self):
        expected_response = "%s:%s:%s" % (
            "POST", 
            self.context.url(self.dummy_url), 
            "foo=1")
            
        self.assertEqual(
            self.context.post(self.dummy_url, foo = 1), 
            expected_response)

    def test_delete(self):
        expected_response = "%s:%s:%s" % (
            "DELETE", 
            self.context.url(self.dummy_url), 
            None)
            
        self.assertEqual(
            self.context.delete(self.dummy_url), 
            expected_response)

    def test_request(self):
        expected_response = "%s:%s:%s" % (
            "GET", 
            self.context.url(self.dummy_url), 
            "")
            
        self.assertEqual(
            self.context.request(self.dummy_url, {}), 
            expected_response)

# UNDONE: Finish testing package namespaces
class PackageTestCase(unittest.TestCase):
    def test_names(self):
        import splunk
        names = dir(splunk)

        import splunk.binding
        # ...

class CaCertNegativeTest(unittest.TestCase):
    def setUp(self):
        global opts
        opts.kwargs['ca_file'] = 'cacert.bad.pem'
        try:
            self.context = connect(**opts.kwargs)
            response = self.context.get("/services")
        except SSLError:
            # expect an SSL exception
            return
        # should not get here
        self.assertTrue(False)

    def tearDown(self):
        pass

    def test(self):
        pass

class CaCertPositiveTest(unittest.TestCase):
    def setUp(self):
        global opts
        opts.kwargs['ca_file'] = 'cacert.pem'
        self.context = connect(**opts.kwargs)
        response = self.context.get("/services")
        self.assertEqual(response.status, 200)

    def tearDown(self):
        pass

    def test(self):
        pass


# Verify that the protocol looks like what we expect
ATOM = "http://www.w3.org/2005/Atom"
AUTHOR = "{%s}author" % ATOM
ENTRY = "{%s}entry" % ATOM
FEED = "{%s}feed" % ATOM
ID = "{%s}id" % ATOM
TITLE = "{%s}title" % ATOM

class ProtocolTestCase(unittest.TestCase):
    def setUp(self):
        global opts
        self.context = connect(**opts.kwargs)

    def tearDown(self):
        pass

    def test(self):
        paths = ["/services"]
        for path in paths:
            body = self.context.get(path).body.read()
            root = XML(body)
            self.assertTrue(root.tag == FEED)
            self.assertTrue(root.find(AUTHOR) is not None)
            self.assertTrue(root.find(ID) is not None)
            self.assertTrue(root.find(TITLE) is not None)
            self.assertTrue(root.findall(ENTRY) is not None)

    
class BindingTestCase(unittest.TestCase): # Base class
    def setUp(self):
        global opts
        self.context = connect(**opts.kwargs)

    def tearDown(self):
        pass

    def connect(self, username, password, namespace = None):
        return connect(
            scheme=self.context.scheme,
            host=self.context.host,
            port=self.context.port,
            username=username,
            password=password,
            namespace=namespace)

    def get(self, path, **kwargs):
        response = self.context.get(path, **kwargs)
        self.assertEqual(response.status, 200)
        return response

    def create(self, path, **kwargs):
        status = kwargs.get('status', 201)
        response = self.context.post(path, **kwargs)
        self.assertEqual(response.status, status)
        return response

    def delete(self, path, **kwargs):
        status = kwargs.get('status', 200)
        response = self.context.delete(path, **kwargs)
        self.assertEqual(response.status, status)
        return response

    def update(self, path, **kwargs):
        status = kwargs.get('status', 200)
        response = self.context.post(path, **kwargs)
        self.assertEqual(response.status, status)
        return response

    def test(self):
        # Just check to make sure the service is alive
        self.assertEqual(self.get("/services").status, 200)

    def test_logout(self):
        response = self.context.get("/services")
        self.assertEqual(response.status, 200)

        self.context.logout()
        response = self.context.get("/services")
        self.assertEqual(response.status, 401)

        self.context.login()
        response = self.context.get("/services")
        self.assertEqual(response.status, 200)

class UsersTestCase(BindingTestCase):
    def eqroles(self, username, roles):
        """Answer if the given user is in exactly the given roles."""
        user = self.user(username)
        roles = roles.split(',')
        if len(roles) != len(user.roles): return False
        for role in roles:
            if not role in user.roles: 
                return False
        return True
        
    def create_user(self, username, password, roles):
        self.assertFalse(username in self.users())
        self.create(PATH_USERS, name=username, password=password, roles=roles)
        self.assertTrue(username in self.users())

    def user(self, username):
        """Returns entity value for given user name."""
        response = self.get("%s/%s" % (PATH_USERS, username))
        self.assertEqual(response.status, 200)
        body = response.body.read()
        self.assertEqual(XML(body).tag, XNAME_FEED)
        return data.load(body).feed.entry.content

    def users(self):
        """Returns a list of user names."""
        response = self.get(PATH_USERS)
        self.assertEqual(response.status, 200)
        body = response.body.read()
        self.assertEqual(XML(body).tag, XNAME_FEED)
        return entry_titles(body)

    def test(self):
        self.get(PATH_USERS)
        self.get(PATH_USERS + "/_new")

    def test_create(self):
        username = uname()
        password = "changeme"
        userpath = "%s/%s" % (PATH_USERS, username)

        # Can't create a user without a role
        self.create(
            PATH_USERS, name=username, password=password,
            status=400)

        # Create a test user
        self.create_user(username, password, "user")
        try:
            # Cannot create a duplicate
            self.create(
                PATH_USERS, name=username, password=password, roles="user", 
                status=400) 

            # Connect as test user
            usercx = self.connect(username, password, "%s:-" % username)

            # Make sure the new context works
            response = usercx.get('/services')
            self.assertEquals(response.status, 200)

            # Test user does not have privs to create another user
            response = usercx.post(
                PATH_USERS, name="flimzo", password="dunno", roles="user")
            self.assertEquals(response.status, 404) # UNDONE: Why is this a 404?

            # User cannot delete themselvse ..
            response = usercx.delete(userpath)
            self.assertEquals(response.status, 404) # UNDONE: Why is this a 404?
    
        finally:
            self.delete(userpath)
            self.assertFalse(username in self.users())

    def test_edit(self):
        username = uname()
        password = "changeme"
        userpath = "%s/%s" % (PATH_USERS, username)

        self.create_user(username, password, "user")
        try:
            self.update(userpath, defaultApp="search")
            self.update(userpath, defaultApp=uname(), status=400)
            self.update(userpath, defaultApp="")
            self.update(userpath, realname="Renzo", email="email.me@now.com")
            self.update(userpath, realname="", email="")
        finally:
            self.delete(userpath)
            self.assertFalse(username in self.users())

    def test_password(self):
        username = uname()
        password = "changeme"
        userpath = "%s/%s" % (PATH_USERS, username)

        # Create a test user
        self.create_user(username, password, "user")
        try:
            # Connect as test user
            usercx = self.connect(username, password, "%s:-" % username)

            # User changes their own password
            response = usercx.post(userpath, password="changed")
            self.assertEqual(response.status, 200)

            # Change it again for giggles ..
            response = usercx.post(userpath, password="changeroo")
            self.assertEqual(response.status, 200)

            # Try to connect with original password ..
            self.assertRaises(HTTPError,
                self.connect, username, password, "%s:-" % username)

            # Admin changes it back
            self.update(userpath, password=password)

            # And now we can connect again with original password ..
            self.connect(username, password, "%s:-" % username)

        finally:
            self.delete(userpath)
            self.assertFalse(username in self.users())

    def test_roles(self):
        username = uname()
        password = "changeme"
        userpath = "%s/%s" % (PATH_USERS, username)

        # Create a test user
        self.create_user(username, password, "admin")
        try:
            self.assertTrue(self.eqroles(username, "admin"))

            # Update with multiple roles
            self.update(userpath, roles=["power", "user"])
            self.assertTrue(self.eqroles(username, "power,user"))

            # Set back to a single role
            self.update(userpath, roles="user")
            self.assertTrue(self.eqroles(username, "user"))

            # Fail adding unknown roles
            self.update(userpath, roles="__unknown__", status=400)

        finally:
            self.delete(userpath)
            self.assertTrue(username not in self.users())
        
def main(argv):
    global opts
    opts = parse(argv, {}, ".splunkrc")
    unittest.main()

if __name__ == "__main__":
    main(sys.argv[1:])

