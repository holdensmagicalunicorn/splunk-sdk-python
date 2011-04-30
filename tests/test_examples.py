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

import os
import unittest

# Rudimentary sanity check for each of the examples
class ExamplesTestCase(unittest.TestCase):
    def tearDown(self):
        os.remove("__stdout__")

    def test_binding1(self):
        result = os.system("python binding1.py > __stdout__")
        self.assertEquals(result, 0)

    def test_spdump(self):
        result = os.system("python spdump.py > __stdout__")
        self.assertEquals(result, 0)
        
def main():
    os.chdir("../examples")
    unittest.main()

if __name__ == "__main__":
    main()
