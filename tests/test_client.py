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
from time import sleep
import unittest

import splunk

from utils import parse

opts = None # Command line options

class PackageTestCase(unittest.TestCase):
    def test_names(self):
        names = dir(splunk)

# When an event is submitted to an index it takes a while before the event
# is registered by the index's totalEventCount.
def wait_event_count(index, count, secs):
    """Wait up to the given number of secs for the given index's
       totalEventCount to reach the given value."""
    done = False
    while not done and secs > 0:
        sleep(1)
        secs -= 1 # Approximate
        done = index['totalEventCount'] == count

class ServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.service = splunk.client.Service(**opts.kwargs)
        self.service.login()

    def tearDown(self):
        pass

    def test_apps(self):
        for app in self.service.apps: app.read()

        self.service.apps.delete('sdk-tests')
        self.assertTrue('sdk-tests' not in self.service.apps.list())

        self.service.apps.create('sdk-tests')
        self.assertTrue('sdk-tests' in self.service.apps.list())

        testapp = self.service.apps['sdk-tests']
        self.assertTrue(testapp['author'] != "Splunk")
        testapp.update(author="Splunk")
        self.assertTrue(testapp['author'] == "Splunk")

        self.service.apps.delete('sdk-tests')
        self.assertTrue('sdk-tests' not in self.service.apps.list())

    def test_confs(self):
        for conf in self.service.confs:
            for stanza in conf: stanza.read()

        self.assertTrue(self.service.confs.contains('props'))
        props = self.service.confs['props']

        stanza = props.create('sdk-tests')
        self.assertTrue(props.contains('sdk-tests'))
        self.assertEqual(stanza.name,'sdk-tests')
        self.assertTrue('maxDist' in stanza.read().keys())
        value = int(stanza['maxDist'])
        stanza.update(maxDist = value+1)
        self.assertEqual(stanza['maxDist'], str(value+1))
        stanza['maxDist'] = value
        self.assertEqual(stanza['maxDist'], str(value))

        props.delete('sdk-tests')
        self.assertFalse(props.contains('sdk-tests')) 

    def test_info(self):
        info = self.service.info
        keys = [
            "build", "cpu_arch", "guid", "isFree", "isTrial", "licenseKeys",
            "licenseSignature", "licenseState", "master_guid", "mode", 
            "os_build", "os_name", "os_version", "serverName", "version" ]
        for key in keys: self.assertTrue(key in info.keys())

    def test_indexes(self):
        for index in self.service.indexes: index.read()

        if not "sdk-tests" in self.service.indexes.list():
            self.service.indexes.create("sdk-tests")
        self.assertTrue("sdk-tests" in self.service.indexes())

        # Scan indexes and make sure the entities look familiar
        attrs = [
            'maxRunningProcessGroups', 'thawedPath', 'quarantineFutureSecs',
            'isInternal', 'maxHotBuckets', 'disabled', 'homePath',
            'compressRawdata', 'maxWarmDBCount', 'frozenTimePeriodInSecs',
            'memPoolMB', 'maxHotSpanSecs', 'minTime', 'blockSignatureDatabase',
            'serviceMetaPeriod', 'coldToFrozenDir', 'quarantinePastSecs',
            'maxConcurrentOptimizes', 'maxMetaEntries', 'minRawFileSyncSecs',
            'maxMemMB', 'maxTime', 'partialServiceMetaPeriod', 'maxHotIdleSecs',
            'coldToFrozenScript', 'thawedPath_expanded', 'coldPath_expanded',
            'defaultDatabase', 'throttleCheckPeriod', 'totalEventCount',
            'enableRealtimeSearch', 'indexThreads', 'maxDataSize',
            'currentDBSizeMB', 'homePath_expanded', 'blockSignSize',
            'syncMeta', 'assureUTF8', 'rotatePeriodInSecs', 'sync',
            'suppressBannerList', 'rawChunkSizeBytes', 'coldPath',
            'maxTotalDataSizeMB'
        ]
        for index in self.service.indexes:
            entity = index.read()
            for attr in attrs: self.assertTrue(attr in entity.keys())

        index = self.service.indexes['sdk-tests']

        entity = index.read()
        self.assertEqual(index['disabled'], entity.disabled)

        index.disable()
        self.assertEqual(index['disabled'], '1')

        index.enable()
        self.assertEqual(index['disabled'], '0')
            
        index.clean()
        self.assertEqual(index['totalEventCount'], '0')

        cn = index.attach()
        cn.write("Hello World!")
        cn.close()
        wait_event_count(index, '1', 30)
        self.assertEqual(index['totalEventCount'], '1')

        index.submit("Hello again!!")
        wait_event_count(index, '2', 30)
        self.assertEqual(index['totalEventCount'], '2')

        index.upload(path.abspath(__file__))
        wait_event_count(index, '3', 30)
        self.assertEqual(index['totalEventCount'], '3')

        index.clean()
        self.assertEqual(index['totalEventCount'], '0')

    def test_indexes_metadata(self):
        metadata = self.service.indexes.itemmeta()
        self.assertTrue(metadata.has_key('eai:acl'))
        self.assertTrue(metadata.has_key('eai:attributes'))
        for index in self.service.indexes:
            metadata = index.readmeta()
            self.assertTrue(metadata.has_key('eai:acl'))
            self.assertTrue(metadata.has_key('eai:attributes'))

    def runjob(self, query, secs):
        """Create a job to run the given search and wait up to (approximately)
           the given number of seconds for it to complete.""" 
        job = self.service.jobs.create(query)
        done = False
        while not done and secs > 0:
            sleep(1)
            secs -= 1 # Approximate
            done = bool(job['isDone'])
        return job

    def test_jobs(self):
        for job in self.service.jobs: job.read()

        if not "sdk-tests" in self.service.indexes():
            self.service.indexes.create("sdk-tests")

        # Make sure we can create a job
        job = self.service.jobs.create("search index=sdk-tests")
        self.assertTrue(job.sid in self.service.jobs())

        # Scan jobs and make sure the entities look familiar
        attrs = [
            'cursorTime', 'delegate', 'diskUsage', 'dispatchState',
            'doneProgress', 'dropCount', 'earliestTime', 'eventAvailableCount',
            'eventCount', 'eventFieldCount', 'eventIsStreaming',
            'eventIsTruncated', 'eventSearch', 'eventSorting', 'isDone',
            'isFailed', 'isFinalized', 'isPaused', 'isPreviewEnabled',
            'isRealTimeSearch', 'isRemoteTimeline', 'isSaved', 'isSavedSearch',
            'isZombie', 'keywords', 'label', 'latestTime', 'messages',
            'numPreviews', 'priority', 'remoteSearch', 'reportSearch',
            'resultCount', 'resultIsStreaming', 'resultPreviewCount',
            'runDuration', 'scanCount', 'searchProviders', 'sid',
            'statusBuckets', 'ttl'
        ]
        for job in self.service.jobs:
            entity = job.read()
            for attr in attrs: self.assertTrue(attr in entity.keys())

        # Make sure we can cancel the job
        job.cancel()
        self.assertTrue(job.sid not in self.service.jobs())

        # Search for non-existant data
        job = self.runjob("search index=sdk-tests TERM_DOES_NOT_EXIST", 10)
        self.assertTrue(bool(job['isDone']))
        self.assertTrue(int(job['eventCount']) == 0)

        # UNDONE: Need to submit test data and test searches for actual 
        # results Check various formats, timeline, searchlog, etc. Check 
        # events and results for both streaming and non-streaming searches. 
        # UNDONE: Need to at least create a realtime search.

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
    opts = parse(argv, {}, ".splunkrc")
    unittest.main()

if __name__ == "__main__":
    main(sys.argv[1:])
