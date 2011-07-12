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

# UNDONE: Add tests that use the path argument
# UNDONE: Add tests that use the XNAME versions of dict & list

import os
import sys
import time

from utils import parse
#import splunk.data as data

opts = None # Command line options

PROXYPORT=8080

def test_proxy():

    # start a tiny-proxy.py server, and run all our tests via shell
    os.system("python proxy-server/tiny-proxy.py -d -p %d" % PROXYPORT)
    time.sleep(1)
    # git PID, and cleanup file
    fd = open("./proxypid", "r")
    pid = fd.read()
    fd.close()
    os.remove("./proxypid")

    # run binding test using proxy server
    os.system("python test_binding.py --proxyhost=127.0.0.1 --proxyport=%d" % PROXYPORT)

    # kill proxy server and remove its log
    os.system("kill -9 %s" % pid)
    os.remove("./proxy.log")


def main(argv):
    global opts
    opts = parse(argv, {}, ".splunkrc")
    test_proxy()

if __name__ == "__main__":
    main(sys.argv[1:])
