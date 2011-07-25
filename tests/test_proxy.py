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
import subprocess

from utils import parse
#import splunk.data as data

opts = None # Command line options

PROXYPORT=8080

def test_proxy():

    if os.name == "nt":
        cwd = os.getcwd()
    else:
        cwd = os.getenv('PWD')

    pidfile = os.path.join(cwd, "proxypid")

    # start a tiny-proxy.py server, and run all our tests via shell
    script = os.path.join(cwd, "tiny-proxy.py")
    os.system("python %s -d -p %d" % (script, PROXYPORT))
    time.sleep(r21)

    # git PID, and cleanup file
    fd = open(pidfile, "r")
    pid = fd.read()
    fd.close()
    os.remove(pidfile)

    # run binding test using proxy server
    os.system("python test_binding.py --proxyhost=127.0.0.1 --proxyport=%d" % PROXYPORT)

    # kill proxy server and remove its log

    if os.name == "nt":
        subprocess.Popen("taskkill /PID %s /t /f" % pid, shell=True)
    else:
        os.system("kill -9 %s" % pid)

    time.sleep(2)
    logname = os.path.join(cwd, "proxy.log")
    os.remove(logname)


def main(argv):
    global opts
    opts = parse(argv, {}, ".splunkrc")
    test_proxy()

if __name__ == "__main__":
    main(sys.argv[1:])
