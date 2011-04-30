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

from os import path
import sys
import unittest
from xml.etree.ElementTree import XML

import splunk
import tools.cmdopts as cmdopts

ATOM = "http://www.w3.org/2005/Atom"
AUTHOR = "{%s}author" % ATOM
ENTRY = "{%s}entry" % ATOM
FEED = "{%s}feed" % ATOM
ID = "{%s}id" % ATOM
TITLE = "{%s}title" % ATOM

opts = None # Command line options

class PackageTestCase(unittest.TestCase):
    def test_names(self):
        names = dir(splunk)

class ProtocolTestCase(unittest.TestCase):
    def setUp(self):
        global opts
        self.cn = splunk.client.connect(**opts.kwargs)

    def tearDown(self):
        self.cn.close()

    def test(self):
        paths = ["/services"]
        for path in paths:
            body = self.cn.get(path).body.read()
            root = XML(body)
            self.assertTrue(root.tag == FEED)
            self.assertTrue(root.find(AUTHOR) is not None)
            self.assertTrue(root.find(ID) is not None)
            self.assertTrue(root.find(TITLE) is not None)
            self.assertTrue(root.findall(ENTRY) is not None)

class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        global opts
        self.cn = splunk.client.connect(**opts.kwargs)

    def tearDown(self):
        self.cn.close()

    def test_info(self):
        info = self.cn.info()
        keys = [
            "build", "cpu_arch", "guid", "isFree", "isTrial", "licenseKeys",
            "licenseSignature", "licenseState", "master_guid", "mode", 
            "os_build", "os_name", "os_version", "serverName", "version" ]
        for key in keys: self.assertTrue(info.has_key(key))

    def test_collections(self):
        # Simply invoke and make sure they are there and dont throw
        self.cn.applications()
        self.cn.eventtypes()
        self.cn.indexes()
        self.cn.inputs()
        self.cn.jobs()
        self.cn.licenses()
        self.cn.objects()
        self.cn.roles()
        self.cn.users()

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

def main(argv):
    global opts
    opts = cmdopts.parser().loadrc(".splunkrc").parse(argv).result
    unittest.main()

if __name__ == "__main__":
    main(sys.argv[1:])
