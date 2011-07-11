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

""" Test valid and invalid CA certificates """

##from os import path
import sys
import unittest
from _ssl import SSLError

from splunk.binding import *
from utils import parse

OPTS = None # Command line options

class CaCertNegativeTest(unittest.TestCase):
    def setUp(self):
        global OPTS
        OPTS.kwargs['ca_file'] = 'cacert.bad.pem'
        try:
            self.context = connect(**OPTS.kwargs)
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
        global OPTS
        OPTS.kwargs['ca_file'] = 'cacert.pem'
        self.context = connect(**OPTS.kwargs)
        response = self.context.get("/services")
        self.assertEqual(response.status, 200)

    def tearDown(self):
        pass

    def test(self):
        pass

def main(argv):
    global OPTS
    OPTS = parse(argv, {}, ".splunkrc")
    unittest.main()

if __name__ == "__main__":
    main(sys.argv[1:])

