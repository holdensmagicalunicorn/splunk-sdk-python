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
    def startUp(self):
        # Ignore result, it might already exist
        os.system("python index.py create sdk-tests > __stdout__")

    def tearDown(self):
        os.remove("__stdout__")

    def test_binding1(self):
        result = os.system("python binding1.py > __stdout__")
        self.assertEquals(result, 0)

    def test_index(self):
        commands = [
            "python index.py --help > __stdout__",
            "python index.py > __stdout__",
            "python index.py list > __stdout__",
            "python index.py list sdk-tests > __stdout__",
            "python index.py disable sdk-tests > __stdout__",
            "python index.py enable sdk-tests > __stdout__",
            "python index.py clean sdk-tests > __stdout__",
        ]
        for command in commands: self.assertEquals(os.system(command), 0)

    def test_info(self):
        result = os.system("python info.py > __stdout__")
        self.assertEquals(result, 0)

    def test_job(self):
        commands = [
            "python job.py --help > __stdout__",
            "python job.py > __stdout__",
            "python job.py list > __stdout__",
            "python job.py list @0 > __stdout__",
        ]
        for command in commands: self.assertEquals(os.system(command), 0)
        
    def test_search(self):
        commands = [
            "python search.py --help > __stdout__",
            "python search.py 'search * | head 10' > __stdout__",
            "python search.py 'search * | stats count' --output_mode='csv' > __stdout__"
        ]
        for command in commands: self.assertEquals(os.system(command), 0)

    def test_spcmd(self):
        result = os.system("python spcmd.py --help > __stdout__")
        self.assertEquals(result, 0)

    def test_spurl(self):
        result = os.system("python spurl.py > __stdout__")
        self.assertEquals(result, 0)

        result = os.system("python spurl.py --help > __stdout__")
        self.assertEquals(result, 0)

        result = os.system("python spurl.py /services > __stdout__")
        self.assertEquals(result, 0)

    def test_submit(self):
        result = os.system("python submit.py --help > __stdout__")
        self.assertEquals(result, 0)

    def test_upload(self):
        commands = [
            "python upload.py --help > __stdout__",
            "python upload.py --index=sdk-tests ./upload.py > __stdout__"
        ]
        for command in commands: self.assertEquals(os.system(command), 0)
        
def main():
    os.chdir("../examples")
    unittest.main()

if __name__ == "__main__":
    main()
