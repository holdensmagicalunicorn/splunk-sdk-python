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

from os import path
import sys
import unittest

# Add parent to the Python path so we can find 'splunk', et al.
sys.path.insert(0, path.dirname(path.dirname(path.abspath(__file__))))

import splunk
import tools.cmdopts as cmdopts

opts = None # Command line options

class PackageTestCase(unittest.TestCase):
    def test_names(self):
        names = dir(splunk)

class BindingTestCase(unittest.TestCase):
    def setUp(self):
        global opts
        self.cx = splunk.connect(**opts.kwargs)

    def tearDown(self):
        pass

    def test(self):
        self.assertEqual(self.cx.get('/services').status, 200)

def main(argv):
    global opts
    opts = cmdopts.parser().loadrc(".splunkrc").parse(argv).result
    unittest.main()

if __name__ == "__main__":
    main(sys.argv[1:])

