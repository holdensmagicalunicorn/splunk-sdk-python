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

import difflib
import os
import unittest

def assertMultiLineEqual(test, first, second, msg=None):
    """Assert that two multi-line strings are equal."""
    test.assertTrue(isinstance(first, basestring), 
        'First argument is not a string')
    test.assertTrue(isinstance(second, basestring), 
        'Second argument is not a string')

    if first != second:
        test.fail("Multiline strings are not equal: %s" % msg)

# Rudimentary sanity check for each of the examples
class ExamplesTestCase(unittest.TestCase):
    def setUp(self):
        # Ignore result, it might already exist
        os.system("python index.py create sdk-tests > __stdout__")
        os.system("python index.py create sdk-tests-two > __stdout__")

    def tearDown(self):
        # Ignore exceptions when trying to remove this file
        try:
            os.remove("__stdout__")
        except: pass

    def test_binding1(self):
        result = os.system("python binding1.py > __stdout__")
        self.assertEquals(result, 0)

    def test_conf(self):
        commands = [
            "python conf.py --help > __stdout__",
            "python conf.py > __stdout__",
            "python conf.py viewstates > __stdout__",
            'python conf.py --namespace="admin:search" viewstates > __stdout__',
            "python conf.py create server SDK-STANZA",
            "python conf.py create server SDK-STANZA testkey=testvalue",
            "python conf.py delete server SDK-STANZA"
        ]
        for command in commands: self.assertEquals(os.system(command), 0)

    def test_async(self):
        result = os.system("python async/async.py sync > __stdout__")
        self.assertEquals(result, 0)

        try:
            # Only try running the async version of the test if eventlet
            # is present on the system
            import eventlet
            result = os.system("python async/async.py async > __stdout__")
            self.assertEquals(result, 0)
        except:
            pass

    def test_follow(self):
        result = os.system("python follow.py --help > __stdout__")
        self.assertEquals(result, 0)

    def test_index(self):
        commands = [
            "python index.py --help > __stdout__",
            "python index.py > __stdout__",
            "python index.py list > __stdout__",
            "python index.py list sdk-tests-two > __stdout__",
            "python index.py disable sdk-tests-two > __stdout__",
            "python index.py enable sdk-tests-two > __stdout__",
            "python index.py clean sdk-tests-two > __stdout__",
        ]
        for command in commands: self.assertEquals(os.system(command), 0)

    def test_info(self):
        result = os.system("python info.py > __stdout__")
        self.assertEquals(result, 0)

    def test_inputs(self):
        commands = [
            "python inputs.py --help > __stdout__",
            "python inputs.py > __stdout__",
        ]
        for command in commands: self.assertEquals(os.system(command), 0)
        
    def test_job(self):
        commands = [
            "python job.py --help > __stdout__",
            "python job.py > __stdout__",
            "python job.py list > __stdout__",
            "python job.py list @0 > __stdout__",
        ]
        for command in commands: self.assertEquals(os.system(command), 0)
        
    def test_loggers(self):
        commands = [
            "python loggers.py --help > __stdout__",
            "python loggers.py > __stdout__",
        ]
        for command in commands: self.assertEquals(os.system(command), 0)

    def test_oneshot(self):
        result = os.system("python oneshot.py 'search * | head 10' > __stdout__")
        self.assertEquals(result, 0)
        
    def test_search(self):
        commands = [
            "python search.py --help > __stdout__",
            'python search.py "search * | head 10" > __stdout__',
            'python search.py "search * | head 10 | stats count" --output_mode="csv" > __stdout__'
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
        # note: test must run on machine where splunkd runs,
        # or a failure is expected
        commands = [
            "python upload.py --help > __stdout__",
            "python upload.py --index=sdk-tests ./upload.py > __stdout__"
        ]
        for command in commands: self.assertEquals(os.system(command), 0)

    # The following tests are for the custom_search examples. The way
    # the tests work mirrors how Splunk would invoke them: they pipe in
    # a known good input file into the custom search python file, and then
    # compare the resulting output file to a known good one.
    def test_custom_search(self):
        def test_custom_search_command(command_path, known_input_path, known_output_path):
            import tempfile
            CUSTOM_SEARCH_OUTPUT = "../tests/temp_custom_search.out";

            # Create and open the temp output file fo writing
            temp_output_file = open(CUSTOM_SEARCH_OUTPUT, 'w')

            # Execute the command
            command = "python %s < %s > %s" % (command_path, known_input_path, temp_output_file.name)
            os.system(command)

            # Flush the temp output file and close it
            temp_output_file.flush()
            temp_output_file.close()

            # Open the temp output file for reading
            temp_output_file = open(CUSTOM_SEARCH_OUTPUT, 'r')

            # Read in the contents of the known output and temp output
            known_output_file = open(known_output_path, 'r')
            known_output_contents = known_output_file.read()
            temp_output_contents = temp_output_file.read()

            # Ensure they are the same
            msg = "%s != %s" % (temp_output_file.name, known_output_file.name)
            assertMultiLineEqual(self, known_output_contents, temp_output_contents, msg)

            # Close the temp output file, and delete it
            temp_output_file.close()
            os.remove(CUSTOM_SEARCH_OUTPUT)

        custom_searches = [
            { 
                "path": "custom_search/bin/usercount.py",
                "known_input_path": "../tests/custom_search/usercount.in",
                "known_output_path": "../tests/custom_search/usercount.out"
            },
            { 
                "path": "twitted/twitted/bin/hashtags.py",
                "known_input_path": "../tests/custom_search/hashtags.in",
                "known_output_path": "../tests/custom_search/hashtags.out"
            },
            { 
                "path": "twitted/twitted/bin/tophashtags.py",
                "known_input_path": "../tests/custom_search/tophashtags.in",
                "known_output_path": "../tests/custom_search/tophashtags.out"
            }
        ]

        for custom_search in custom_searches:
            path = custom_search["path"]
            input = custom_search["known_input_path"]
            output = custom_search["known_output_path"]
            test_custom_search_command(path, input, output)
 
def main():
    os.chdir("../examples")
    unittest.main()

if __name__ == "__main__":
    main()
