#!/usr/bin/env python
#
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

# UNDONE: Skip spam
# UNDONE: Skip deleted messages?

from pprint import pprint # UNDONE

import hashlib
import imaplib
import re
import sys

import tools.cmdopts as cmdopts

rules = {
    "email_protocol": { 'flags': ["--email:protocol"] },
    "email_address":  { 'flags': ["--email:address"]  },
    "email_username": { 'flags': ["--email:username"] },
    "email_password": { 'flags': ["--email:password"] },
}

def error(message, exit_code = None):
    sys.stderr.write("Error: %s\n" % message)
    if exit_code is not None: sys.exit(exit_code)

class Email:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.connection = imaplib.IMAP4_SSL("imap.gmail.com", 993)

    def close(self):
        self.connection.close()
        return self

    # imaplib's fetch returns message data in a bizarre format. The response
    # consists of a list of "response parts" and the details of the parts list
    # depend on the requested message parts passed to fetch. For the request 
    # below, (RFC822 FLAGS) where we are requesting the entire message and 
    # corresponding flags, the response consists of alternating parts, where 
    # the part is first a tuple (pair) consisting of (response info, message) 
    # followed by a part consisting of a string containing the message flags. 
    # The response info contains the message UID and count of header bytes. 
    # This wrapper routine exists to sanitize the fetched results into a nice, 
    # simple, list of dicts.
    def fetch(self, ids):
        if len(ids) == 0: return []
        ids = ','.join(ids)
        status, response = self.connection.fetch(ids, "(RFC822 FLAGS)")
        if status != "OK": raise Exception, response
        count = len(response)
        assert count % 2 == 0
        result = []
        for i in xrange(0, count-1, 2):
            info, data = response[i]
            flags = response[i+1]
            regex = r"(?P<uid>[0-9]+) \(RFC822 \{(?P<bytes>[0-9]+)"
            match = re.match(regex, info)
            assert match is not None
            uid = int(match.group('uid'))
            bytes = int(match.group('bytes'))
            result.append({
                'uid': uid,
                'hsize': bytes,
                'flags': list(imaplib.ParseFlags(flags)),
                'message': data,
                'hash': hashlib.md5(data).hexdigest(),
            })
            # UNDONE: Investigate using eg: SHA for the hash
        return result

    # The imaplib response consists of a list of strings containing
    # mailbox flags and name formatted as shown in the following example:
    #     ['(\\HasNoChildren) "/" "Deleted Messages"',
    #      '(\\HasNoChildren) "/" "Drafts"',
    #      '(\\HasNoChildren) "/" "INBOX"',
    #      ...
    # We dont need the flags, so we parse the result into a simple list
    # of mailbox names.
    def list(self):
        status, response = self.connection.list()
        if status != 'OK': raise Exception, response
        return [item.split(' "/" ')[1].strip('"') for item in response]

    def login(self):
        status, _ = self.connection.login(self.username, self.password)
        if status != 'OK': raise Exception, response
        return self

    def logout(self):
        status, _ = self.connection.logout()
        if status != 'OK': raise Exception, response
        return self

    def search(self, *args):
        status, response = self.connection.search(None, *args)
        if status != 'OK': raise Exception, response
        return response

    def select(self, mailbox):
        status, response = self.connection.select(mailbox)
        if status != 'OK': raise Exception, response
        return self
        
# Fetch the contents of the given mailbox and publish to Splunk.
# UNDONE: Don't reindex mesasges - consider hashing the header and checking
# for the existence for that hash in Splunk before downloading entire message.
# Need to do a little investigation on the probability of hash collisions given
# typical email message header size & content.
def process(email, mailbox):
    email.select(mailbox)
    ids = email.search(None, "UNDELETED")
    ids = ids[0].split()
    print "Processing %s (%d)" % (mailbox, len(ids))
    for id in ids:
        messages = email.fetch([id])
        for message in messages:
            publish(message)
    if len(ids) > 0: print
    email.close() # Close currently selected mailbox

# Publish the given email message to Splunk
def publish(message):
    pprint(message['message'][:72])

def main(argv):
    opts = cmdopts.parser(rules).loadrc(".splunkrc").parse(argv).result
    username = opts.kwargs.get("email_username", None)
    if username is None: error("No email username provided", 2)
    password = opts.kwargs.get("email_password", None)
    if password is None: error("No email password provided", 2)

    email = Email(username, password).login()
    for mailbox in email.list(): 
        process(email, mailbox)
    email.logout()

if __name__ == "__main__":
    main(sys.argv[1:])
