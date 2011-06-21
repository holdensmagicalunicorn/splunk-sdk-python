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
from time import sleep
import unittest
from xml.etree.ElementTree import XML

import splunk

from utils import cmdopts

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

    def test_info(self):
        info = self.service.info
        keys = [
            "build", "cpu_arch", "guid", "isFree", "isTrial", "licenseKeys",
            "licenseSignature", "licenseState", "master_guid", "mode", 
            "os_build", "os_name", "os_version", "serverName", "version" ]
        for key in keys: self.assertTrue(key in info.keys())

    def test_indexes(self):
        if not "sdk-examples" in self.service.indexes.list():
            self.service.indexes.create("sdk-examples")

        index = self.service.indexes['sdk-examples']

        entity = index.read()
        self.assertEqual(index['disabled'], entity.disabled)

        index.disable()
        self.assertEqual(index['disabled'], '1')

        index.enable()
        self.assertEqual(index['disabled'], '0')
            
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

    def test_parse(self):
        response = self.service.parse("search *")
        self.assertEqual(response.status, 200)

        response = self.service.parse("search index=twitter status_count=* | stats count(status_source) as count by status_source | sort -count | head 20")
        self.assertEqual(response.status, 200)

        response = self.service.parse("xyzzy")
        self.assertEqual(response.status, 400)

    def test_restart(self):
        response = self.service.restart()
        self.assertEqual(response.status, 200)

        sleep(5) # Wait for server to notice restart

        retry = 10
        restarted = False
        while retry > 0:
            retry -= 1
            try:
                self.service.login() # Awake yet?
                response = self.service.get('server')
                self.assertEqual(response.status, 200)
                restarted = True
                break
            except:
                sleep(5)
        self.assertTrue(restarted)

    #def test_roles(self):
    #    roles = self.cn.roles
    #    capabilities = self.cn.capabilities()
    #    for role in roles.values():
    #        for capability in role.capabilities:
    #            self.assertTrue(capability in capabilities)

    #def test_users(self):
    #    users = self.cn.users
    #    roles = self.cn.roles
    #    for user in users.values():
    #        for role in user.roles:
    #            self.assertTrue(role in roles.keys())

    def test_settings(self):
        settings = self.service.settings.read()
        keys = [
            "SPLUNK_DB", "SPLUNK_HOME", "enableSplunkWebSSL", "host",
            "httpport", "mgmtHostPort", "minFreeSpace", "pass4SymmKey",
            "serverName", "sessionTimeout", "startwebserver", "trustedIP"
        ]
        for key in keys: self.assertTrue(key in settings.keys())
        

def main(argv):
    global opts
    opts = cmdopts.parse(argv, {}, ".splunkrc")
    unittest.main()

if __name__ == "__main__":
    main(sys.argv[1:])
