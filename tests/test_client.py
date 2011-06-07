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

import sys
import unittest
from xml.etree.ElementTree import XML

import splunk
import tools.cmdopts as cmdopts

opts = None # Command line options

class PackageTestCase(unittest.TestCase):
    def test_names(self):
        names = dir(splunk)

class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        global opts
        self.service = splunk.client.Service(**opts.kwargs)
        self.service.login()

    def tearDown(self):
        pass

    #def test_info(self):
    #    info = self.cn.info()
    #    keys = [
    #        "build", "cpu_arch", "guid", "isFree", "isTrial", "licenseKeys",
    #        "licenseSignature", "licenseState", "master_guid", "mode", 
    #        "os_build", "os_name", "os_version", "serverName", "version" ]
    #    for key in keys: self.assertTrue(info.has_key(key))

    def test_indexes(self):
        if not "sdk-examples" in self.service.indexes.list():
            self.service.indexes.create("sdk-examples")

        index = self.service.indexes['sdk-examples']

        entity = index.read()
        self.assertTrue(index['disabled'] == entity.disabled)

        index.disable()
        self.assertTrue(index['disabled'] == '1')

        index.enable()
        self.assertTrue(index['disabled'] == '0')
            
        # Restore
        index.disable() if entity.disabled else entity.enable()

        index.clean()

    def test_indexes_metadata(self):
        metadata = self.service.indexes.itemmeta()
        self.assertTrue(metadata.has_key('eai:acl'))
        self.assertTrue(metadata.has_key('eai:attributes'))
        for index in self.service.indexes:
            metadata = index.readmeta()
            self.assertTrue(metadata.has_key('eai:acl'))
            self.assertTrue(metadata.has_key('eai:attributes'))

    #def test_users(self):
    #    users = self.cn.users
    #    roles = self.cn.roles
    #    for user in users.values():
    #        for role in user.roles:
    #            self.assertTrue(role in roles.keys())

    #def test_roles(self):
    #    roles = self.cn.roles
    #    capabilities = self.cn.capabilities()
    #    for role in roles.values():
    #        for capability in role.capabilities:
    #            self.assertTrue(capability in capabilities)

def main(argv):
    global opts
    opts = cmdopts.parser().loadrc(".splunkrc").parse(argv).result
    unittest.main()

if __name__ == "__main__":
    main(sys.argv[1:])
