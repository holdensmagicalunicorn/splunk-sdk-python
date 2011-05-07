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

from pprint import pprint # UNDONE

from imaplib import IMAP4_SSL
import sys

def main():
    cn = IMAP4_SSL("imap.gmail.com", 993)
    cn.login("<username>", "<password>")
    status, content = cn.list()
    mailboxes = [item.split(' "/" ')[1].strip('"') for item in content]
    for item in mailboxes: 
        status, content = cn.select(item)
        if status != "OK": continue
        print "%s (%s)" % (item, content[0])
    cn.close()
    cn.logout()

if __name__ == "__main__":
    main()
    
