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
import sys
import time
import subprocess

from utils import parse

opts = None # Command line options

PROXYPORT=8080
LOGFILE="proxy.log"
KILLFILE="kill.log"

def test_proxy():

    if os.name == "nt":
        cwd = os.getcwd()
    else:
        cwd = os.getenv('PWD')

    pidfile = os.path.join(cwd, "proxypid")

    # start a tiny-proxy.py server, and run all our tests via shell
    script = os.path.join(cwd, "tiny-proxy.py")
    os.system("python %s -d -p %d" % (script, PROXYPORT))
    time.sleep(2)

    # git PID, and cleanup file
    fd = open(pidfile, "r")
    pid = fd.read()
    fd.close()
    os.remove(pidfile)

    # run binding test using proxy server
    os.system("python test_binding.py --proxyhost=127.0.0.1 --proxyport=%d" % \
              PROXYPORT)

    # kill proxy server and remove its log
    if os.name == "nt":
        # redirect text from taskkill to dummy file, and then remove it after 
        # process is dead
        kfile = os.open(KILLFILE, os.O_CREAT)
        subprocess.Popen("taskkill /PID %s /t /f" % pid, shell=True, stdout=kfile)
        time.sleep(3)
        os.close(kfile)
        os.remove(KILLFILE)
    else:
        os.system("kill -9 %s" % pid)
        time.sleep(3)

    os.remove(LOGFILE)

def main(argv):
    global opts
    opts = parse(argv, {}, ".splunkrc")
    test_proxy()

if __name__ == "__main__":
    main(sys.argv[1:])
