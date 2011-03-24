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

import getopt
from os import path
import sys
import unittest
from xml.etree.ElementTree import XML

# Add parent to the Python path so we can find 'splunk', et al.
sys.path.insert(0, path.dirname(path.dirname(path.abspath(__file__))))

import splunk

# UNDONE: Unify command line processing
from tools.cmdline import error, loadif, merge, record

ATOM = "http://www.w3.org/2005/Atom"
AUTHOR = "{%s}author" % ATOM
ENTRY = "{%s}entry" % ATOM
FEED = "{%s}feed" % ATOM
ID = "{%s}id" % ATOM
TITLE = "{%s}title" % ATOM

host = "localhost"
port = 8089
username = ""
password = ""
namespace = None

def connect():
    global host, port, username, password, namespace
    return splunk.connect("%s:%s" % (host, port), username, password, namespace)

class PackageTestCase(unittest.TestCase):
    def test_names(self):
        names = dir(splunk)

class ProtocolTestCase(unittest.TestCase):
    def setUp(self):
        self.cn = connect()

    def tearDown(self):
        self.cn.close()

    def test(self):
        paths = ["/services"]
        for path in paths:
            body = self.cn.get(path).body
            root = XML(body)
            self.assertTrue(root.tag == FEED)
            self.assertTrue(root.find(AUTHOR) is not None)
            self.assertTrue(root.find(ID) is not None)
            self.assertTrue(root.find(TITLE) is not None)
            self.assertTrue(root.findall(ENTRY) is not None)

class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.cn = connect()

    def tearDown(self):
        self.cn.close()

    def test_info(self):
        info = self.cn.info()
        keys = [
            "build", "cpu_arch", "guid", "isFree", "isTrial", "licenseKeys",
            "licenseSignature", "licenseState", "master_guid", "mode", 
            "os_build", "os_name", "os_version", "serverName", "version" ]
        for key in keys: self.assertTrue(info.has_key(key))

    def test_users(self):
        users = self.cn.users
        roles = self.cn.roles
        for user in users.values():
            for role in user.roles:
                self.assertTrue(role in roles.keys())

    def test_roles(self):
        roles = self.cn.roles
        capabilities = self.cn.capabilities()
        for role in roles.values():
            for capability in role.capabilities:
                self.assertTrue(capability in capabilities)

# UNDONE: Generalize and move to cmdline.py
def getopts(argv):
    opts = {}
    opts = merge(opts, parse(loadif(path.expanduser("~/.splunkrc"))))
    opts = merge(opts, parse(argv))
    opts = merge(opts, parse(loadif(opts.get("config", None))))
    return record(opts)

# UNDONE: Generalize and move to cmdline.py
def parse(argv):
    try:
        rules = [
            "config=", 
            "host=", 
            "password=", 
            "port=", 
            "username="
        ]
        kwargs, args = getopt.gnu_getopt(argv, "", rules)
    except getopt.GetoptError as e:
        error(e.msg) # UNDONE: Use same error messages as below
        usage(2)
    opts = {'args': args, 'kwargs': {}}
    for k, v in kwargs:
        assert k.startswith("--")
        k = k[2:]
        opts["kwargs"][k] = v
    return opts

def main(argv):
    kwargs = getopts(argv).kwargs
    global host, port, username, password, namespace
    host = kwargs.get("host", host)
    port = kwargs.get("port", port)
    username = kwargs.get("username", "")
    password = kwargs.get("password", "")
    namespace = kwargs.get("namespace", None)
    unittest.main()

if __name__ == "__main__":
    main(sys.argv[1:])

